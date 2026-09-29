#!/usr/bin/env python3
"""CM1 round 2 — format-first gate + pinch sweep (frozen per CM1-r2-plan.md).
Imports round-1 cells (STIMULI/RULE/gen_cell/judge_cell/parse_answer/
keyword_router); round-1 script stays byte-frozen."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cm1_relay import (STIMULI, gen_cell, judge_cell, parse_answer,
                       keyword_router)

LAB = os.path.dirname(HERE)
OUT_DIR = os.path.join(LAB, "results", "cm1")
OUT_JSON = os.path.join(OUT_DIR, "round_002_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
PINCHES = (0.3, 0.5, 0.7)

SYS_PROMPT = ("You are a routing cell on a fishing vessel. Apply the rule exactly.\n"
              "domain = engine if the report mentions engine terms (temp rising/falling, oil, fuel, rpm); "
              "else navigation if it mentions motion terms (blob moving, course drift, AIS contact); else deck.\n"
              "urgency = high if any hazard term (rising, falling, dropping, leak, fire) or two+ domains implicated; "
              "else mid if any motion term; else low.\n"
              "Answer with exactly one line: BOOK:<domain>:<urgency> "
              "where domain in {navigation, engine, deck} and urgency in {low, mid, high}. No other text.")
FORMAT_FEEDBACK = ("Your last answer was not in the required format. Answer again with exactly one line "
                   "BOOK:<domain>:<urgency> — nothing else.")


def log(msg):
    print("[cm1r2 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def arm_b(stimulus_msgs, report, pinch):
    """Gated relay with format-first gate. Returns record dict."""
    t0 = time.time()
    jev_in = jev_out = 0
    draft, ev = gen_cell(stimulus_msgs)
    ans = parse_answer(draft)
    via_format_retry = False
    if ans == "PARSE_FAIL":
        msgs = stimulus_msgs + [{"role": "assistant", "content": draft},
                                 {"role": "user", "content": FORMAT_FEEDBACK}]
        draft, ev2 = gen_cell(msgs)
        ev += ev2
        ans = parse_answer(draft)
        via_format_retry = True
        if ans == "PARSE_FAIL":
            return {"answer": keyword_router(report), "correct": None,
                    "path": "FORMAT_PINCHED", "gates": [], "retries": 1,
                    "jev_in": 0, "jev_out": 0, "t_s": round(time.time() - t0, 2),
                    "ollama_eval": ev}
    state = ("Report: " + report + "\nDraft answer: " + draft.strip())
    gd, gu, usage = judge_cell(state, draft)
    jev_in += usage.get("input_tokens", 0)
    jev_out += usage.get("output_tokens", 0)
    gates = [(gd, gu)]
    if min(gd, gu) < pinch:
        msgs = stimulus_msgs + [{"role": "assistant", "content": draft},
                                {"role": "user", "content":
                                 "Gate scores domain=%.2f urgency=%.2f (threshold %.2f). "
                                 "Re-derive carefully step by step, then answer again with exactly "
                                 "one line BOOK:<domain>:<urgency>." % (gd, gu, pinch)}]
        draft, ev3 = gen_cell(msgs)
        ev += ev3
        ans2 = parse_answer(draft)
        if ans2 == "PARSE_FAIL":
            return {"answer": keyword_router(report), "correct": None,
                    "path": "PINCHED_FALLBACK", "gates": gates, "retries": 1,
                    "jev_in": jev_in, "jev_out": jev_out,
                    "t_s": round(time.time() - t0, 2), "ollama_eval": ev}
        state2 = state + "\nRevised draft: " + draft.strip()
        gd2, gu2, usage = judge_cell(state2, draft)
        jev_in += usage.get("input_tokens", 0)
        jev_out += usage.get("output_tokens", 0)
        gates.append((gd2, gu2))
        ans = ans2
        if min(gd2, gu2) < pinch:
            return {"answer": keyword_router(report), "correct": None,
                    "path": "PINCHED_FALLBACK", "gates": gates, "retries": 1,
                    "jev_in": jev_in, "jev_out": jev_out,
                    "t_s": round(time.time() - t0, 2), "ollama_eval": ev}
        return {"answer": ans, "correct": None, "path": "RETRY_PASS",
                "gates": gates, "retries": 1, "jev_in": jev_in, "jev_out": jev_out,
                "t_s": round(time.time() - t0, 2), "ollama_eval": ev}
    path = "FORMAT_RETRY_PASS" if via_format_retry else "DRAFT_PASS"
    return {"answer": ans, "correct": None, "path": path, "gates": gates,
            "retries": 1 if via_format_retry else 0,
            "jev_in": jev_in, "jev_out": jev_out,
            "t_s": round(time.time() - t0, 2), "ollama_eval": ev}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    # Arm A — ungated baseline (fresh, deterministic)
    a_recs, ev_total = [], 0
    for sid, report, truth in STIMULI:
        ta = time.time()
        draft, ev = gen_cell([{"role": "system", "content": SYS_PROMPT},
                              {"role": "user", "content": "Report: " + report}])
        ev_total += ev
        ans = parse_answer(draft)
        a_recs.append({"sid": sid, "answer": ans, "correct": ans == truth,
                       "t_s": round(time.time() - ta, 2)})
    ca = sum(r["correct"] for r in a_recs)
    log("arm A: %d/12" % ca)

    out_b = {}
    for pinch in PINCHES:
        recs, ji, jo = [], 0, 0
        for sid, report, truth in STIMULI:
            r = arm_b([{"role": "system", "content": SYS_PROMPT},
                       {"role": "user", "content": "Report: " + report}],
                      report, pinch)
            r["sid"], r["truth"] = sid, truth
            r["correct"] = r["answer"] == truth
            recs.append(r)
            ji += r["jev_in"]; jo += r["jev_out"]
        cb = sum(r["correct"] for r in recs)
        paths = {}
        for r in recs:
            paths[r["path"]] = paths.get(r["path"], 0) + 1
        diff = cb - ca
        verdict = ("GATING_WINS" if diff >= 2 else
                   "GATING_HURTS" if diff <= -2 else "TIE_NOISE")
        out_b["p%.1f" % pinch] = {"correct": cb, "diff": diff, "verdict": verdict,
                                  "paths": paths, "jev_in": ji, "jev_out": jo,
                                  "records": recs}
        log("p=%.1f: B %d/12 diff %+d -> %s paths=%s jev=%d/%d"
            % (pinch, cb, diff, verdict, paths, ji, jo))

    out = {"schema": "cm1-round2/1", "plan": "proposals/runs/CM1-r2-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "pinches": list(PINCHES), "correct_A": ca, "armA": a_recs,
           "jev_r1_avg_in_per_stimulus": 802,  # sealed comparison baseline
           "armB": out_b, "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({
            "schema": "cm1-round2/1", "created": out["created"], "correct_A": ca,
            "correct_B": {k: v["correct"] for k, v in out_b.items()},
            "verdicts": {k: v["verdict"] for k, v in out_b.items()},
            "paths": {k: v["paths"] for k, v in out_b.items()},
            "jev_in": {k: v["jev_in"] for k, v in out_b.items()}}) + "\n")
    log("DONE %.1fs" % out["wall_s"])


if __name__ == "__main__":
    main()
