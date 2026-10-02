#!/usr/bin/env python3
"""CM1 round 5 — judge swap (jev-latest) + 3-cell roster under the r4-winning recipe.
Frozen per proposals/runs/CM1-r5-plan.md. Imports r1 cells, r2 prompts, r3 GEN/flow.

Arm A (TRANSFER): r4 arm-B recipe verbatim (single Seed-2.0-mini, rule-rich batched
gates @0.5, doubted-retry, keyword pinch) with judge swapped to jev-latest.
Arm B (ROSTER): 3 DeepInfra cells x 12 stimuli = 36 ungated drafts, ONE batched
rule-rich judge (72 noul questions), served draft = argmax min(gd,gu) among
gate-passing (tiebreak: lower cell index); no pass -> keyword_router pinch.

Gates: H1 B>=11 KEEP / <=8 KILL; H2 A>=11 TRANSFERS / <=8 TRANSFER_FAILS;
H3 conditional: B>A ROSTER_EARNS (rescued sids booked) | B==A==12 ROSTER_IDLE
(expected under saturation) | B<A ROSTER_HURTS. Cost ledger per arm.
Harness: cell smoke first; <2 survivors -> HARNESS_INVALID, no scoring.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cm1_relay as R1
import cm1_relay_r3 as R3
from cm1_relay import STIMULI, parse_answer, keyword_router
from cm1_relay_r2 import SYS_PROMPT, FORMAT_FEEDBACK

LAB = os.path.dirname(HERE)
OUT_DIR = os.path.join(LAB, "results", "cm1")
OUT_JSON = os.path.join(OUT_DIR, "round_005_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
PINCH = 0.5
CELLS = ["ByteDance/Seed-2.0-mini", "XiaomiMiMo/MiMo-V2.6-Flash",
         "inclusionAI/Ling-3.0-flash"]
JUDGE_MODEL = "jev-latest"


def log(msg):
    print("[cm1r5 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def gen_di_model(messages, model):
    """R3.gen_di with a model parameter (same endpoint/token/format)."""
    with open(R3.DI_TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": model, "messages": messages, "temperature": 0,
               "max_tokens": 200}
    req = R1.urllib.request.Request(
        R3.DI_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + tok,
                 "Content-Type": "application/json"}, method="POST")
    for attempt in (1, 2):
        try:
            with R1.urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read().decode("utf-8"))
            msg = out["choices"][0]["message"].get("content", "") or ""
            return msg, out.get("usage", {})
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("GEN cell %s failed twice: %r" % (model, e))
            time.sleep(2)


def tsafe_batch(state_obj, questions):
    with open(R1.TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": JUDGE_MODEL, "state": state_obj, "questions": questions}
    for attempt in (1, 2):
        t0 = time.time()
        try:
            r = R1.post_json(R1.TSAFE, payload,
                             {"Authorization": "Bearer " + tok,
                              "Content-Type": "application/json"}, 90)
            answers = r["answers"]
            missing = [k for k in questions if k not in answers]
            if missing:
                raise ValueError("batch missing %d answers: %s" % (len(missing), missing[:3]))
            r["_wall_s"] = round(time.time() - t0, 2)
            return r
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("BATCH JUDGE (%s) failed twice: %r" % (JUDGE_MODEL, e))
            log("batch retry after: %r" % e)
            time.sleep(2)


def smoke_cells():
    alive = []
    for model in CELLS:
        ok = False
        for _ in range(2):
            try:
                msg, _u = gen_di_model(
                    [{"role": "user", "content": "Reply with the single word: ok"}], model)
                ok = len(msg) > 0
                break
            except Exception as e:
                log("smoke %s fail: %r" % (model, e))
                time.sleep(2)
        if ok:
            alive.append(model)
        else:
            log("CELL DEAD: %s" % model)
    return alive


CANON = (R1.RULE + "\nAnswer format: exactly one line BOOK:<domain>:<urgency>. "
         "DOMAIN/URGENCY values must be derivable from the report by the rule.")


def gen_draft(report, model):
    """Ungated draft + format retry. Returns (draft_str, ans, tokens_used)."""
    msgs = [{"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": "Report: " + report}]
    draft, u = gen_di_model(msgs, model)
    tin = u.get("prompt_tokens", 0)
    tout = u.get("completion_tokens", 0)
    if parse_answer(draft) == "PARSE_FAIL":
        draft, u = gen_di_model(msgs + [{"role": "assistant", "content": draft},
                                        {"role": "user", "content": FORMAT_FEEDBACK}], model)
        tin += u.get("prompt_tokens", 0)
        tout += u.get("completion_tokens", 0)
    return draft.strip(), msgs, tin, tout


def batch_questions(keys):
    """keys: list of (cell_label, sid). One noul pair per draft."""
    qs = {}
    for cell_label, sid in keys:
        tag = "%s__%s" % (cell_label, sid)
        qs[tag + "_domain_ok"] = {
            "type": "noul",
            "question": "For draft %s (report %s): does the draft answer's DOMAIN follow the rule_canon?" % (tag, sid),
            "instructions": "Answer true only if the draft's domain is what rule_canon yields for that report."}
        qs[tag + "_urgency_ok"] = {
            "type": "noul",
            "question": "For draft %s (report %s): does the draft answer's URGENCY follow the rule_canon?" % (tag, sid),
            "instructions": "Answer true only if the draft's urgency is what rule_canon yields for that report."}
    return qs


def batch_state(items):
    """items: list of dicts with cell_label, sid, report, draft."""
    return {"rule_canon": CANON,
            "reports": [{"sid": "%s__%s" % (it["cell_label"], it["sid"]),
                         "report": it["report"],
                         "draft_answer": it["draft"]} for it in items]}


def judge_and_serve(items, ledger):
    """One batched rule-rich judge over all draft items; returns {sid: served_rec}."""
    keys = [(it["cell_label"], it["sid"]) for it in items]
    resp = tsafe_batch(batch_state(items), batch_questions(keys))
    ledger["jev_in"] += resp.get("usage", {}).get("input_tokens", 0)
    ledger["jev_out"] += resp.get("usage", {}).get("output_tokens", 0)
    ledger["walls"].append(resp["_wall_s"])

    # group gate results by sid
    by_sid = {}
    for it in items:
        tag = "%s__%s" % (it["cell_label"], it["sid"])
        gd = float(resp["answers"][tag + "_domain_ok"]["noul"])
        gu = float(resp["answers"][tag + "_urgency_ok"]["noul"])
        by_sid.setdefault(it["sid"], []).append((min(gd, gu), it["cell_index"], gd, gu, it))

    served = {}
    for sid, cands in by_sid.items():
        cands.sort(key=lambda c: (-c[0], c[1]))  # max min(gd,gu); tie -> lower cell index
        best = cands[0]
        served[sid] = {"best": best, "all": cands}
    return served


def run_recipe_arm(name, cell_models):
    """Rule-rich batched recipe. cell_models: list of model ids (len 1 = transfer arm).
    Returns (recs, ledger, per_sid_gate_detail)."""
    ledger = {"jev_in": 0, "jev_out": 0, "di_in": 0, "di_out": 0, "walls": []}
    items, dead_cells = [], set()
    for sid, report, truth in STIMULI:
        for ci, model in enumerate(cell_models):
            label = "c%d" % ci
            try:
                draft, msgs, tin, tout = gen_draft(report, model)
            except RuntimeError as e:
                log("gen fail %s/%s: %r" % (label, sid, e))
                dead_cells.add(model)
                items.append({"cell_label": label, "cell_index": ci, "sid": sid,
                              "report": report, "truth": truth, "draft": "",
                              "ans": "PARSE_FAIL"})
                continue
            ledger["di_in"] += tin
            ledger["di_out"] += tout
            items.append({"cell_label": label, "cell_index": ci, "sid": sid,
                          "report": report, "truth": truth, "draft": draft,
                          "ans": parse_answer(draft)})
    if dead_cells:
        log("dead cells during gen: %s" % dead_cells)

    served = judge_and_serve(items, ledger)

    recs = []
    for sid, report, truth in STIMULI:
        best = served[sid]["best"]
        score, ci, gd, gu, it = best
        rec = {"sid": sid, "truth": truth, "cells": [c[4]["cell_label"] for c in served[sid]["all"]],
               "gates": [[round(c[2], 3), round(c[3], 3)] for c in served[sid]["all"]],
               "served_from": it["cell_label"]}
        if it["ans"] == "PARSE_FAIL":
            rec["path"] = "FORMAT_PINCHED"
            rec["answer"] = keyword_router(report)
        elif score < PINCH:
            rec["path"] = "DOUBTED_PINCH"
            rec["answer"] = keyword_router(report)
        else:
            rec["path"] = "DRAFT_PASS"
            rec["answer"] = it["ans"]
        rec["correct"] = rec["answer"] == truth
        recs.append(rec)
    correct = sum(r["correct"] for r in recs)
    return recs, ledger, correct


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    log("judge=%s cells=%s" % (JUDGE_MODEL, CELLS))

    alive = smoke_cells()
    if len(alive) < 2:
        out = {"schema": "cm1-round5/1", "verdicts": {"verdict": "HARNESS_INVALID"},
               "reason": "cell smoke survivors %d < 2: %s" % (len(alive), alive),
               "wall_s": round(time.time() - t0, 1)}
        json.dump(out, open(OUT_JSON, "w"), indent=1)
        log("HARNESS_INVALID: %s" % out["reason"])
        return
    roster = alive if len(alive) == 3 else alive
    log("smoke ok: %s" % roster)

    # ---------- Arm A: recipe transfer (single cell, jev-latest) ----------
    a_recs, a_led, ca = run_recipe_arm("A_transfer", [roster[0]])
    a_paths = {}
    for r in a_recs:
        a_paths[r["path"]] = a_paths.get(r["path"], 0) + 1
    a_nouls = [max(g) for r in a_recs for g in r["gates"]
               if r["correct"] and r["path"] == "DRAFT_PASS"]
    a_cal = round(sum(a_nouls) / len(a_nouls), 3) if a_nouls else None
    log("A %d/12 paths=%s jev=%d/%d walls=%s" %
        (ca, a_paths, a_led["jev_in"], a_led["jev_out"], a_led["walls"]))

    # ---------- Arm B: roster ----------
    b_recs, b_led, cb = run_recipe_arm("B_roster", roster)
    b_paths = {}
    for r in b_recs:
        b_paths[r["path"]] = b_paths.get(r["path"], 0) + 1
    b_nouls = [max(g) for r in b_recs for g in r["gates"]
               if r["correct"] and r["path"] == "DRAFT_PASS"]
    b_cal = round(sum(b_nouls) / len(b_nouls), 3) if b_nouls else None
    b_from = {}
    for r in b_recs:
        if r["correct"]:
            b_from[r["served_from"]] = b_from.get(r["served_from"], 0) + 1
    log("B %d/12 paths=%s jev=%d/%d served_from=%s" %
        (cb, b_paths, b_led["jev_in"], b_led["jev_out"], b_from))

    # ---------- frozen verdicts ----------
    h1 = "KEEP" if cb >= 11 else ("KILL" if cb <= 8 else "WEAK_UNRESOLVED")
    h2 = "TRANSFERS" if ca >= 11 else ("TRANSFER_FAILS" if ca <= 8 else "WEAK")
    if cb > ca:
        h3 = "ROSTER_EARNS"
        rescued = [r["sid"] for r, a in zip(b_recs, a_recs)
                   if r["correct"] and not a["correct"]]
    elif cb == ca == 12:
        h3, rescued = "ROSTER_IDLE", []
    elif cb < ca:
        h3, rescued = "ROSTER_HURTS", []
    else:
        h3, rescued = "TIE_BELOW_SATURATION", []
    verdicts = {"H1_roster_recipe": h1, "H2_transfer": h2, "H3_roster": h3,
                "rescued_sids": rescued}
    cost_bar = b_led["jev_in"] <= 3.5 * max(a_led["jev_in"], 1)
    log("verdicts=%s cost_bar_ok=%s" % (json.dumps(verdicts), cost_bar))

    out = {"schema": "cm1-round5/1", "plan": "proposals/runs/CM1-r5-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "judge": JUDGE_MODEL, "cells": CELLS, "alive_cells": roster,
           "pinch": PINCH,
           "factor": "judge swap (jev-latest) + 3-cell roster under r4-winning recipe",
           "correct_A": ca, "A_paths": a_paths, "A_jev": [a_led["jev_in"], a_led["jev_out"]],
           "A_di": [a_led["di_in"], a_led["di_out"]], "A_walls": a_led["walls"],
           "A_cal": a_cal, "armA": a_recs,
           "correct_B": cb, "B_paths": b_paths, "B_jev": [b_led["jev_in"], b_led["jev_out"]],
           "B_di": [b_led["di_in"], b_led["di_out"]], "B_walls": b_led["walls"],
           "B_cal": b_cal, "B_served_from": b_from, "armB": b_recs,
           "cost_bar_ok": cost_bar, "verdicts": verdicts,
           "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({
            "schema": "cm1-round5/1", "created": out["created"],
            "judge": JUDGE_MODEL, "cells": roster,
            "correct_A": ca, "correct_B": cb,
            "A_paths": a_paths, "B_paths": b_paths,
            "A_cal": a_cal, "B_cal": b_cal,
            "A_jev": out["A_jev"], "B_jev": out["B_jev"],
            "verdicts": verdicts}) + "\n")
    log("DONE %.1fs" % out["wall_s"])


if __name__ == "__main__":
    main()
