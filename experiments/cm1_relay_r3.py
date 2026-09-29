#!/usr/bin/env python3
"""CM1 round 3 — DeepInfra Seed-2.0-mini GEN + format gate + pinch sweep.
Frozen per proposals/runs/CM1-r3-plan.md. Imports r1 cells; r2 script frozen."""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cm1_relay import (STIMULI, judge_cell, parse_answer, keyword_router)
from cm1_relay_r2 import SYS_PROMPT, FORMAT_FEEDBACK

LAB = os.path.dirname(HERE)
OUT_DIR = os.path.join(LAB, "results", "cm1")
OUT_JSON = os.path.join(OUT_DIR, "round_003_out.json")
JSONL = os.path.join(OUT_DIR, "rounds.jsonl")
PINCHES = (0.3, 0.5, 0.7)
DI_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
DI_MODEL = "ByteDance/Seed-2.0-mini"
DI_TOKEN_FILE = os.path.expanduser("~/.config/deepinfra/token")


def log(msg):
    print("[cm1r3 %s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def gen_di(messages):
    with open(DI_TOKEN_FILE) as f:
        tok = f.read().strip()
    payload = {"model": DI_MODEL, "messages": messages, "temperature": 0,
               "max_tokens": 200}
    req = urllib.request.Request(
        DI_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + tok,
                 "Content-Type": "application/json"}, method="POST")
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read().decode("utf-8"))
            msg = out["choices"][0]["message"].get("content", "") or ""
            usage = out.get("usage", {})
            return msg, usage
        except Exception as e:
            if attempt == 2:
                raise RuntimeError("GEN cell (deepinfra) failed twice: %r" % e)
            time.sleep(2)


def arm_b(msgs, report, pinch):
    t0 = time.time()
    di_in = di_out = jev_in = jev_out = 0
    draft, u = gen_di(msgs)
    di_in += u.get("prompt_tokens", 0)
    di_out += u.get("completion_tokens", 0)
    ans = parse_answer(draft)
    via_format_retry = False
    if ans == "PARSE_FAIL":
        draft, u = gen_di(msgs + [{"role": "assistant", "content": draft},
                                  {"role": "user", "content": FORMAT_FEEDBACK}])
        di_in += u.get("prompt_tokens", 0)
        di_out += u.get("completion_tokens", 0)
        ans = parse_answer(draft)
        via_format_retry = True
        if ans == "PARSE_FAIL":
            return {"answer": keyword_router(report), "correct": None,
                    "path": "FORMAT_PINCHED", "gates": [],
                    "di_in": di_in, "di_out": di_out,
                    "jev_in": 0, "jev_out": 0,
                    "t_s": round(time.time() - t0, 2)}
    state = "Report: " + report + "\nDraft answer: " + draft.strip()
    gd, gu, ju = judge_cell(state, draft)
    jev_in += ju.get("input_tokens", 0)
    jev_out += ju.get("output_tokens", 0)
    gates = [(gd, gu)]
    if min(gd, gu) < pinch:
        draft, u = gen_di(msgs + [{"role": "assistant", "content": draft},
                                  {"role": "user", "content":
                                   "Gate scores domain=%.2f urgency=%.2f (threshold %.2f). "
                                   "Re-derive carefully step by step, then answer again with "
                                   "exactly one line BOOK:<domain>:<urgency>."
                                   % (gd, gu, pinch)}])
        di_in += u.get("prompt_tokens", 0)
        di_out += u.get("completion_tokens", 0)
        ans2 = parse_answer(draft)
        if ans2 == "PARSE_FAIL":
            return {"answer": keyword_router(report), "correct": None,
                    "path": "PINCHED_FALLBACK", "gates": gates,
                    "di_in": di_in, "di_out": di_out,
                    "jev_in": jev_in, "jev_out": jev_out,
                    "t_s": round(time.time() - t0, 2)}
        gd2, gu2, ju = judge_cell(state + "\nRevised draft: " + draft.strip(), draft)
        jev_in += ju.get("input_tokens", 0)
        jev_out += ju.get("output_tokens", 0)
        gates.append((gd2, gu2))
        ans = ans2
        if min(gd2, gu2) < pinch:
            return {"answer": keyword_router(report), "correct": None,
                    "path": "PINCHED_FALLBACK", "gates": gates,
                    "di_in": di_in, "di_out": di_out,
                    "jev_in": jev_in, "jev_out": jev_out,
                    "t_s": round(time.time() - t0, 2)}
        return {"answer": ans, "correct": None, "path": "RETRY_PASS",
                "gates": gates, "di_in": di_in, "di_out": di_out,
                "jev_in": jev_in, "jev_out": jev_out,
                "t_s": round(time.time() - t0, 2)}
    path = "FORMAT_RETRY_PASS" if via_format_retry else "DRAFT_PASS"
    return {"answer": ans, "correct": None, "path": path, "gates": gates,
            "di_in": di_in, "di_out": di_out, "jev_in": jev_in, "jev_out": jev_out,
            "t_s": round(time.time() - t0, 2)}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    a_recs, a_di_in, a_di_out = [], 0, 0
    for sid, report, truth in STIMULI:
        draft, u = gen_di([{"role": "system", "content": SYS_PROMPT},
                           {"role": "user", "content": "Report: " + report}])
        a_di_in += u.get("prompt_tokens", 0)
        a_di_out += u.get("completion_tokens", 0)
        ans = parse_answer(draft)
        a_recs.append({"sid": sid, "answer": ans, "correct": ans == truth})
    ca = sum(r["correct"] for r in a_recs)
    log("arm A (Seed ungated): %d/12" % ca)

    out_b = {}
    for pinch in PINCHES:
        recs, ji, jo, di_i, di_o = [], 0, 0, 0, 0
        for sid, report, truth in STIMULI:
            r = arm_b([{"role": "system", "content": SYS_PROMPT},
                       {"role": "user", "content": "Report: " + report}],
                      report, pinch)
            r["sid"], r["truth"] = sid, truth
            r["correct"] = r["answer"] == truth
            recs.append(r)
            ji += r["jev_in"]; jo += r["jev_out"]
            di_i += r["di_in"]; di_o += r["di_out"]
        cb = sum(r["correct"] for r in recs)
        paths = {}
        for r in recs:
            paths[r["path"]] = paths.get(r["path"], 0) + 1
        diff = cb - ca
        verdict = ("GATING_WINS" if diff >= 2 else
                   "GATING_HURTS" if diff <= -2 else "TIE_NOISE")
        out_b["p%.1f" % pinch] = {"correct": cb, "diff": diff, "verdict": verdict,
                                  "paths": paths, "jev_in": ji, "jev_out": jo,
                                  "di_in": di_i, "di_out": di_o, "records": recs}
        log("p=%.1f: B %d/12 diff %+d -> %s paths=%s jev=%d/%d di=%d/%d"
            % (pinch, cb, diff, verdict, paths, ji, jo, di_i, di_o))

    out = {"schema": "cm1-round3/1", "plan": "proposals/runs/CM1-r3-plan.md",
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "gen": DI_MODEL, "pinches": list(PINCHES),
           "correct_A": ca, "armA_di_tokens": {"in": a_di_in, "out": a_di_out},
           "armA": a_recs, "armB": out_b, "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(OUT_JSON, "w"), indent=1)
    with open(JSONL, "a") as f:
        f.write(json.dumps({
            "schema": "cm1-round3/1", "created": out["created"], "gen": DI_MODEL,
            "correct_A": ca, "correct_B": {k: v["correct"] for k, v in out_b.items()},
            "verdicts": {k: v["verdict"] for k, v in out_b.items()},
            "paths": {k: v["paths"] for k, v in out_b.items()},
            "jev_in": {k: v["jev_in"] for k, v in out_b.items()}}) + "\n")
    log("DONE %.1fs" % out["wall_s"])


if __name__ == "__main__":
    main()
