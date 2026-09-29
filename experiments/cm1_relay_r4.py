#!/usr/bin/env python3
"""CM1 round 4 — rule-blind vs rule-rich batched gates (single factor: gate call pattern).
Frozen per proposals/runs/CM1-r4-plan.md. Imports r1 cells, r2 prompts, r3 GEN/flow.

Pre-registered hypothesis: r3's semantic gates judged drafts WITHOUT the RULE in
state (r3 arm_b built state = 'Report: ... Draft: ...' only), so Jev doubted
correct drafts out of ignorance (9/12 doubted at p=0.5, 12/12 at p=0.7).
Arm A replicates that rule-blind pattern (r3 arm_b @ 0.5, fresh run).
Arm B: rich state (RULE canon + all 12 reports) + ONE batched typesafe call
(24 named noul questions — jev-quilt batching pattern, 80q ~= flat latency).
Predictions: B calibration (mean noul on correct drafts) >> A; B DRAFT_PASS > A;
B judgment wall-time << A; accuracy 12/12 both arms.
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
OUT_JSON = os.path.join(OUT_DIR, "round_004_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
PINCH = 0.5

JTIME = {"a_s": 0.0, "a_calls": 0}
_orig_judge = R3.judge_cell


def timed_judge(state, draft):
    t0 = time.time()
    r = _orig_judge(state, draft)
    JTIME["a_s"] += time.time() - t0
    JTIME["a_calls"] += 1
    return r


R3.judge_cell = timed_judge  # arm_b's global lookup hits this


def log(msg):
    print("[cm1r4 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def tsafe_batch(state_obj, questions):
    with open(R1.TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": "jev-preview", "state": state_obj, "questions": questions}
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
                raise RuntimeError("BATCH JUDGE failed twice: %r" % e)
            log("batch retry after: %r" % e)
            time.sleep(2)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    # ---------- Arm A: r3 arm_b @ 0.5 (rule-blind per-stimulus gates) ----------
    a_recs, ji, jo, di_i, di_o = [], 0, 0, 0, 0
    for sid, report, truth in STIMULI:
        msgs = [{"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content": "Report: " + report}]
        r = R3.arm_b(msgs, report, PINCH)
        r["sid"], r["truth"] = sid, truth
        r["correct"] = r["answer"] == truth
        a_recs.append(r)
        ji += r["jev_in"]; jo += r["jev_out"]
        di_i += r["di_in"]; di_o += r["di_out"]
    ca = sum(r["correct"] for r in a_recs)
    a_paths = {}
    for r in a_recs:
        a_paths[r["path"]] = a_paths.get(r["path"], 0) + 1
    a_nouls = [g[0] for r in a_recs for g in r["gates"] if r["correct"]]
    a_cal = round(sum(a_nouls) / len(a_nouls), 3) if a_nouls else None
    log("A %d/12 paths=%s jev=%d/%d judge_wall=%.1fs/%dcalls cal=%s"
        % (ca, a_paths, ji, jo, JTIME["a_s"], JTIME["a_calls"], a_cal))

    # ---------- Arm B: rule-rich batched gates ----------
    # Generate + format-fix 12 drafts first (ungated gen, same prompts).
    drafts = {}
    b_di_in = b_di_out = 0
    for sid, report, truth in STIMULI:
        msgs = [{"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content": "Report: " + report}]
        draft, u = R3.gen_di(msgs)
        b_di_in += u.get("prompt_tokens", 0)
        b_di_out += u.get("completion_tokens", 0)
        if parse_answer(draft) == "PARSE_FAIL":
            draft, u = R3.gen_di(msgs + [{"role": "assistant", "content": draft},
                                         {"role": "user", "content": FORMAT_FEEDBACK}])
            b_di_in += u.get("prompt_tokens", 0)
            b_di_out += u.get("completion_tokens", 0)
        drafts[sid] = {"report": report, "truth": truth, "draft": draft.strip(),
                       "ans": parse_answer(draft), "msgs": msgs}

    CANON = (R1.RULE + "\nAnswer format: exactly one line BOOK:<domain>:<urgency>. "
             "DOMAIN/URGENCY values must be derivable from the report by the rule.")

    def batch_questions(sids):
        qs = {}
        for sid in sids:
            qs[sid + "_domain_ok"] = {
                "type": "noul",
                "question": "For report %s: does the draft answer's DOMAIN follow the rule_canon?" % sid,
                "instructions": "Answer true only if the draft's domain is what rule_canon yields for that report."}
            qs[sid + "_urgency_ok"] = {
                "type": "noul",
                "question": "For report %s: does the draft answer's URGENCY follow the rule_canon?" % sid,
                "instructions": "Answer true only if the draft's urgency is what rule_canon yields for that report."}
        return qs

    def batch_state(sids):
        return {"rule_canon": CANON,
                "reports": [{"sid": sid, "report": drafts[sid]["report"],
                             "draft_answer": drafts[sid]["draft"]} for sid in sids]}

    b_jt = {}
    resp = tsafe_batch(batch_state(list(drafts)), batch_questions(list(drafts)))
    b_jev_in = resp.get("usage", {}).get("input_tokens", 0)
    b_jev_out = resp.get("usage", {}).get("output_tokens", 0)
    b_jt["pass1"] = resp["_wall_s"]
    log("B batch1: %d answers in %.2fs jev=%d/%d"
        % (len(resp["answers"]), resp["_wall_s"], b_jev_in, b_jev_out))

    b_recs = []
    doubted = []
    for sid, report, truth in STIMULI:
        gd = float(resp["answers"][sid + "_domain_ok"]["noul"])
        gu = float(resp["answers"][sid + "_urgency_ok"]["noul"])
        d = drafts[sid]
        rec = {"sid": sid, "truth": truth, "gates": [(gd, gu)], "answer": d["ans"],
               "correct": d["ans"] == truth, "path": None,
               "jev_in": 0, "jev_out": 0, "di_in": 0, "di_out": 0}
        if d["ans"] == "PARSE_FAIL":
            rec["path"] = "FORMAT_PINCHED"
            rec["answer"] = keyword_router(report)
            rec["correct"] = rec["answer"] == truth
        elif min(gd, gu) < PINCH:
            doubted.append((sid, gd, gu))
            rec["path"] = "DOUBTED"
        else:
            rec["path"] = "DRAFT_PASS"
        b_recs.append(rec)

    # Retry doubted drafts (r3-style feedback), re-judge in ONE second batch.
    if doubted:
        for sid, gd, gu in doubted:
            d = drafts[sid]
            draft2, u = R3.gen_di(d["msgs"] + [
                {"role": "assistant", "content": d["draft"]},
                {"role": "user", "content":
                 "Gate scores domain=%.2f urgency=%.2f (threshold %.2f). "
                 "Re-derive carefully step by step, then answer again with "
                 "exactly one line BOOK:<domain>:<urgency>." % (gd, gu, PINCH)}])
            b_di_in += u.get("prompt_tokens", 0)
            b_di_out += u.get("completion_tokens", 0)
            d["draft"] = draft2.strip()
            d["ans"] = parse_answer(draft2)
        sids2 = [s for s, _, _ in doubted]
        resp2 = tsafe_batch(batch_state(sids2), batch_questions(sids2))
        b_jev_in += resp2.get("usage", {}).get("input_tokens", 0)
        b_jev_out += resp2.get("usage", {}).get("output_tokens", 0)
        b_jt["pass2"] = resp2["_wall_s"]
        for rec in b_recs:
            if rec["path"] != "DOUBTED":
                continue
            sid = rec["sid"]
            gd = float(resp2["answers"][sid + "_domain_ok"]["noul"])
            gu = float(resp2["answers"][sid + "_urgency_ok"]["noul"])
            rec["gates"].append((gd, gu))
            d = drafts[sid]
            if d["ans"] == "PARSE_FAIL" or min(gd, gu) < PINCH:
                rec["path"] = "PINCHED_FALLBACK"
                rec["answer"] = keyword_router(d["report"])
            else:
                rec["path"] = "RETRY_PASS"
                rec["answer"] = d["ans"]
            rec["correct"] = rec["answer"] == rec["truth"]

    for rec in b_recs:
        rec["di_in"] = b_di_in / len(b_recs)   # gen tokens shared; per-rec split noted
        rec["di_out"] = b_di_out / len(b_recs)
        rec["jev_in"] = b_jev_in / len(b_recs)
        rec["jev_out"] = b_jev_out / len(b_recs)
    cb = sum(r["correct"] for r in b_recs)
    b_paths = {}
    for r in b_recs:
        b_paths[r["path"]] = b_paths.get(r["path"], 0) + 1
    b_nouls = [g[0] for r in b_recs for g in r["gates"]
               if r["correct"] and r["path"] != "FORMAT_PINCHED"]
    b_cal = round(sum(b_nouls) / len(b_nouls), 3) if b_nouls else None
    diff = cb - ca
    verdict = ("RICH_WINS" if diff >= 2 else
               "RICH_HURTS" if diff <= -2 else "TIE_NOISE")
    log("B %d/12 paths=%s jev=%d/%d batch_walls=%s cal=%s -> %s (diff %+d)"
        % (cb, b_paths, b_jev_in, b_jev_out, b_jt, b_cal, verdict, diff))

    out = {"schema": "cm1-round4/1", "plan": "proposals/runs/CM1-r4-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "gen": R3.DI_MODEL, "pinch": PINCH,
           "factor": "gate call pattern: rule-blind per-stimulus (A) vs rule-rich batched (B)",
           "hypothesis": "r3 doubting caused by RULE absent from gate state",
           "correct_A": ca, "A_paths": a_paths, "A_jev": [ji, jo],
           "A_judge_wall_s": round(JTIME["a_s"], 2), "A_calls": JTIME["a_calls"],
           "A_cal_domain": a_cal, "armA": a_recs,
           "correct_B": cb, "B_paths": b_paths, "B_jev": [b_jev_in, b_jev_out],
           "B_batch_walls": b_jt, "B_cal_domain": b_cal, "armB": b_recs,
           "diff": diff, "verdict": verdict,
           "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({
            "schema": "cm1-round4/1", "created": out["created"], "gen": R3.DI_MODEL,
            "correct_A": ca, "correct_B": cb, "diff": diff, "verdict": verdict,
            "A_paths": a_paths, "B_paths": b_paths,
            "A_cal": a_cal, "B_cal": b_cal,
            "A_judge_wall_s": out["A_judge_wall_s"], "B_batch_walls": b_jt}) + "\n")
    log("DONE %.1fs" % out["wall_s"])


if __name__ == "__main__":
    main()
