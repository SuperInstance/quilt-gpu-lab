#!/usr/bin/env python3
"""CM1 round 6 — judge-state chunking A/B/C (frozen per proposals/runs/CM1-r6-plan.md).

Question: is r5's arm-B gate degradation caused by judge-state SIZE, and does
chunking a 36-draft workload into 12-draft judge calls restore quality?

Arms on IDENTICAL draft objects:
  A' monolithic: all 36 roster drafts, ONE 72-question batched judge (r5 arm-B recipe).
  C  chunked:    SAME 36 drafts, 3 x 12-draft chunks, stimulus-major (each chunk
                 = all 3 cells x 4 whole stimuli), identical per-draft questions.
  D  reference:  the 12 Seed drafts, one 24-question call (r5 arm-A replica).

Draft source: reuse r5's stored drafts from round_005_out.json if present
(they are NOT — r5 stored served answers/gates only -> fail-loud per plan) ->
regenerate per the r5 recipe (temp 0, format retry), book draft_source.

Frozen gates (pass = min(gd,gu) >= 0.5, per-draft unit on the 36/12 drafts):
  H1 CHUNK_RESTORES: pr(C)-pr(A') >= +0.20 AND pr(C) >= pr(D)-0.10
  H2 JUDGE_NONDETERMINISTIC: |pr(A')-pr(r5B stored)| >= 0.20  [conflated with
     draft drift when drafts were regenerated - booked with flag]
  H3 CHUNK_NEUTRAL: |pr(C)-pr(A')| < 0.05
  H4 REPLICATE_FAIL: pr(D) < pr(A')
Priority when multiple fire: H2 > H4 > H1 > H3.
Cost gate: sum(C chunk walls) <= 1.5 x A' wall.
Keys read at use-time from /mnt/c/Users/casey/key.txt. Never logged.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cm1_relay as R1
import cm1_relay_r3 as R3
from cm1_relay import STIMULI, parse_answer
from cm1_relay_r2 import SYS_PROMPT, FORMAT_FEEDBACK

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(LAB, "results", "cm1")
R5_JSON = os.path.join(OUT_DIR, "round_005_out.json")
OUT_JSON = os.path.join(OUT_DIR, "round_006_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
KEY_FILE = "/mnt/c/Users/casey/key.txt"
PINCH = 0.5
CELLS = ["ByteDance/Seed-2.0-mini", "XiaomiMiMo/MiMo-V2.6-Flash",
         "inclusionAI/Ling-3.0-flash"]
JUDGE_MODEL = "jev-latest"
DI_URL = R3.DI_URL
TSAFE = R1.TSAFE
CANON = (R1.RULE + "\nAnswer format: exactly one line BOOK:<domain>:<urgency>. "
         "DOMAIN/URGENCY values must be derivable from the report by the rule.")


def log(msg):
    print("[cm1r6 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def read_keys():
    keys = {}
    with open(KEY_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    return keys


def _retry_sleep(e, attempt):
    ra = getattr(e, "headers", {}).get("Retry-After") if isinstance(
        e, urllib.error.HTTPError) else None
    try:
        return max(int(ra), 5)
    except (TypeError, ValueError):
        return 5 * attempt


def gen_di(messages, model, ledger):
    keys = read_keys()  # use-time read
    payload = {"model": model, "messages": messages, "temperature": 0,
               "max_tokens": 200}
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(
                DI_URL, data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": "Bearer " + keys["DEEPINFRA_KEY"],
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read().decode("utf-8"))
            msg = out["choices"][0]["message"].get("content", "") or ""
            u = out.get("usage", {})
            ledger["di_in"] += u.get("prompt_tokens", 0)
            ledger["di_out"] += u.get("completion_tokens", 0)
            return msg
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                s = _retry_sleep(e, attempt); log("429 gen, sleep %ds" % s); time.sleep(s); continue
            if attempt < 3:
                time.sleep(3); continue
            raise RuntimeError("GEN %s failed x3: HTTP %r" % (model, e))
        except Exception as e:
            if attempt == 3:
                raise RuntimeError("GEN %s failed x3: %r" % (model, e))
            time.sleep(3)


def tsafe_batch(state_obj, questions, ledger):
    keys = read_keys()  # use-time read
    payload = {"model": JUDGE_MODEL, "state": state_obj, "questions": questions}
    for attempt in (1, 2, 3):
        t0 = time.time()
        try:
            req = urllib.request.Request(
                TSAFE, data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": "Bearer " + keys["TYPESAFE_AI_KEY"],
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read().decode("utf-8"))
            answers = resp["answers"]
            missing = [k for k in questions if k not in answers]
            if missing:
                raise ValueError("missing %d answers" % len(missing))
            wall = round(time.time() - t0, 2)
            u = resp.get("usage", {})
            ledger["jev_in"] += u.get("input_tokens", 0)
            ledger["jev_out"] += u.get("output_tokens", 0)
            ledger["walls"].append(wall)
            return answers, wall
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                s = _retry_sleep(e, attempt); log("429 judge, sleep %ds" % s); time.sleep(s); continue
            if attempt < 3:
                time.sleep(3); continue
            raise RuntimeError("JUDGE batch failed x3: HTTP %r" % e)
        except Exception as e:
            if attempt == 3:
                raise RuntimeError("JUDGE batch failed x3: %r" % e)
            log("judge retry after: %r" % e)
            time.sleep(3)


def smoke(cells):
    alive = []
    led = {"di_in": 0, "di_out": 0}
    for model in cells:
        ok = False
        for _ in range(2):
            try:
                msg = gen_di([{"role": "user",
                               "content": "Reply with the single word: ok"}], model, led)
                ok = len(msg.strip()) > 0
                break
            except RuntimeError as e:
                log("smoke %s fail: %r" % (model, e))
                time.sleep(2)
        if ok:
            alive.append(model)
        else:
            log("CELL DEAD: %s" % model)
    return alive


def gen_draft(report, model, ledger):
    msgs = [{"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": "Report: " + report}]
    draft = gen_di(msgs, model, ledger)
    if parse_answer(draft) == "PARSE_FAIL":
        draft = gen_di(msgs + [{"role": "assistant", "content": draft},
                               {"role": "user", "content": FORMAT_FEEDBACK}],
                       model, ledger)
    return draft.strip()


def items_from_drafts(draft_map):
    """draft_map: {(cell_index, sid): draft_text} -> judge items list."""
    items = []
    for ci in range(3):
        for sid, report, truth in STIMULI:
            if (ci, sid) in draft_map:
                items.append({"cell_label": "c%d" % ci, "cell_index": ci,
                              "sid": sid, "report": report, "truth": truth,
                              "draft": draft_map[(ci, sid)]})
    return items


def batch_state(items):
    return {"rule_canon": CANON,
            "reports": [{"sid": "%s__%s" % (it["cell_label"], it["sid"]),
                         "report": it["report"],
                         "draft_answer": it["draft"]} for it in items]}


def batch_questions(items):
    qs = {}
    for it in items:
        tag = "%s__%s" % (it["cell_label"], it["sid"])
        qs[tag + "_domain_ok"] = {
            "type": "noul",
            "question": "For draft %s (report %s): does the draft answer's DOMAIN follow the rule_canon?" % (tag, it["sid"]),
            "instructions": "Answer true only if the draft's domain is what rule_canon yields for that report."}
        qs[tag + "_urgency_ok"] = {
            "type": "noul",
            "question": "For draft %s (report %s): does the draft answer's URGENCY follow the rule_canon?" % (tag, it["sid"]),
            "instructions": "Answer true only if the draft's urgency is what rule_canon yields for that report."}
    return qs


def gate_passes(items, answers):
    """{(cell_index, sid): min(gd,gu)}"""
    g = {}
    for it in items:
        tag = "%s__%s" % (it["cell_label"], it["sid"])
        gd = float(answers[tag + "_domain_ok"]["noul"])
        gu = float(answers[tag + "_urgency_ok"]["noul"])
        g[(it["cell_index"], it["sid"])] = min(gd, gu)
    return g


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    led = {"jev_in": 0, "jev_out": 0, "di_in": 0, "di_out": 0, "walls": []}
    log("r6 start: chunking A/B/C, judge=%s" % JUDGE_MODEL)

    # ---- draft source: reuse if stored (r5 stored none) ----
    r5 = json.load(open(R5_JSON))
    drafts_b = {k: v for k, v in r5.items() if k in ("armB_drafts", "drafts")}
    draft_source = None
    if drafts_b:
        draft_source = "reused_r5"
        log("reused r5 drafts")
    else:
        log("r5 stored no draft texts -> regenerate per plan (fail-loud path booked)")

    alive = None
    if draft_source != "reused_r5":
        alive = smoke(CELLS)
        if len(alive) < 3:
            out = {"schema": "cm1-round6/1", "verdicts": {"verdict": "HARNESS_INVALID"},
                   "reason": "cell smoke survivors %d < 3: %s" % (len(alive), alive),
                   "wall_s": round(time.time() - t0, 1)}
            json.dump(out, open(OUT_JSON, "w"), indent=1)
            log("HARNESS_INVALID"); return
        # regenerate 3x12 roster drafts (arm A'/C) + 12 Seed drafts (arm D)
        draft_map = {}
        for ci, model in enumerate(alive):
            for sid, report, _t in STIMULI:
                draft_map[(ci, sid)] = gen_draft(report, model, led)
                time.sleep(0.3)
            log("regen cell c%d (%s) done" % (ci, model))
        seed_map = {(0, it["sid"]): it["draft"] for it in
                    items_from_drafts(draft_map) if it["cell_index"] == 0}

    items36 = items_from_drafts(draft_map)
    items12 = [{"cell_label": "c0", "cell_index": 0, "sid": it["sid"],
                "report": it["report"], "truth": it["truth"], "draft": it["draft"]}
               for it in items36 if it["cell_index"] == 0]
    assert len(items36) == 36 and len(items12) == 12, "draft census %d/%d" % (
        len(items36), len(items12))

    # ---- Arm A': monolithic 36-draft judge ----
    answers_a, wall_a = tsafe_batch(batch_state(items36),
                                    batch_questions(items36), led)
    gates_a = gate_passes(items36, answers_a)
    pr_A = sum(1 for v in gates_a.values() if v >= PINCH) / 36.0
    log("A' monolithic: wall %.2fs pr=%.3f (%d/36 pass)" %
        (wall_a, pr_A, round(pr_A * 36)))
    time.sleep(2)

    # ---- Arm C: 3 x 12-draft chunks, stimulus-major ----
    sid_groups = [[s[0] for s in STIMULI[0:4]],
                  [s[0] for s in STIMULI[4:8]],
                  [s[0] for s in STIMULI[8:12]]]
    gates_c, walls_c, chunk_pr = {}, [], []
    for gi, sids in enumerate(sid_groups):
        chunk = [it for it in items36 if it["sid"] in sids]
        assert len(chunk) == 12, "chunk %d census %d" % (gi, len(chunk))
        answers_c, wall_c = tsafe_batch(batch_state(chunk),
                                        batch_questions(chunk), led)
        g = gate_passes(chunk, answers_c)
        gates_c.update(g)
        walls_c.append(wall_c)
        chunk_pr.append(sum(1 for v in g.values() if v >= PINCH) / 12.0)
        log("C chunk %d (sids %s): wall %.2fs pr=%.3f" %
            (gi, ",".join(sids), wall_c, chunk_pr[-1]))
        time.sleep(2)
    pr_C = sum(1 for v in gates_c.values() if v >= PINCH) / 36.0
    wall_c_sum = round(sum(walls_c), 2)

    # ---- Arm D: 12-draft reference ----
    answers_d, wall_d = tsafe_batch(batch_state(items12),
                                    batch_questions(items12), led)
    gates_d = gate_passes(items12, answers_d)
    pr_D = sum(1 for v in gates_d.values() if v >= PINCH) / 12.0
    log("D reference: wall %.2fs pr=%.3f (%d/12 pass)" %
        (wall_d, pr_D, round(pr_D * 12)))

    # ---- r5 stored reference pass rates (per-draft unit) ----
    r5b_pairs = [g for rec in r5["armB"] for g in rec["gates"]]
    pr_r5B = sum(1 for gd, gu in r5b_pairs if min(gd, gu) >= PINCH) / 36.0
    r5a_pairs = [g for rec in r5["armA"] for g in rec["gates"]]
    pr_r5A = sum(1 for gd, gu in r5a_pairs if min(gd, gu) >= PINCH) / 12.0
    log("r5 stored: pr_r5B=%.3f (%d/36) pr_r5A=%.3f (%d/12)" %
        (pr_r5B, round(pr_r5B * 36), pr_r5A, round(pr_r5A * 12)))

    # ---- frozen verdicts ----
    h1 = (pr_C - pr_A) >= 0.20 and pr_C >= (pr_D - 0.10)
    h2 = abs(pr_A - pr_r5B) >= 0.20
    h3 = abs(pr_C - pr_A) < 0.05
    h4 = pr_D < pr_A
    fired = []
    if h2: fired.append("H2_JUDGE_NONDETERMINISTIC")
    if h4: fired.append("H4_REPLICATE_FAIL")
    if h1: fired.append("H1_CHUNK_RESTORES")
    if h3: fired.append("H3_CHUNK_NEUTRAL")
    headline = fired[0] if fired else "NO_GATE_FIRED"
    cost_bar = wall_c_sum <= 1.5 * wall_a
    log("verdicts fired=%s headline=%s cost_bar_ok=%s" % (fired, headline, cost_bar))

    def fmt_gates(g):
        return {"%s_%s" % (ci, sid): round(v, 3) for (ci, sid), v in sorted(g.items())}

    out = {"schema": "cm1-round6/1", "plan": "proposals/runs/CM1-r6-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "judge": JUDGE_MODEL, "cells": CELLS, "alive_cells": alive,
           "draft_source": draft_source or "regenerated_r5_recipe",
           "factor": "judge-state size: monolithic 36 vs chunked 3x12 vs 12-reference",
           "pinch": PINCH,
           "pass_A_monolithic_36": round(pr_A, 4), "A_wall_s": wall_a,
           "pass_C_chunked_36": round(pr_C, 4), "C_walls_s": walls_c,
           "C_wall_sum_s": wall_c_sum, "C_chunk_pr": [round(p, 4) for p in chunk_pr],
           "pass_D_ref_12": round(pr_D, 4), "D_wall_s": wall_d,
           "r5_stored": {"pass_B_36": round(pr_r5B, 4),
                         "pass_A_12": round(pr_r5A, 4)},
           "gates_A": fmt_gates(gates_a), "gates_C": fmt_gates(gates_c),
           "gates_D": fmt_gates(gates_d),
           "h_fired": fired, "headline": headline,
           "h2_conflated_draft_drift": draft_source != "reused_r5",
           "cost_bar_ok": cost_bar,
           "ledgers": {"jev": [led["jev_in"], led["jev_out"]],
                       "di": [led["di_in"], led["di_out"]],
                       "judge_walls_all": led["walls"]},
           "drafts_regenerated": {"%s_%s" % (ci, sid): d for (ci, sid), d in
                                  sorted(draft_map.items())},
           "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({
            "schema": "cm1-round6/1", "created": out["created"],
            "judge": JUDGE_MODEL, "draft_source": out["draft_source"],
            "pass_A": out["pass_A_monolithic_36"], "pass_C": out["pass_C_chunked_36"],
            "pass_D": out["pass_D_ref_12"], "r5_stored_B": out["r5_stored"]["pass_B_36"],
            "C_walls": walls_c, "A_wall": wall_a, "cost_bar_ok": cost_bar,
            "h_fired": fired, "headline": headline,
            "jev": out["ledgers"]["jev"], "di": out["ledgers"]["di"]}) + "\n")
    log("DONE %.1fs headline=%s" % (out["wall_s"], headline))


if __name__ == "__main__":
    main()
