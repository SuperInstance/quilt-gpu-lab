#!/usr/bin/env python3
"""cudaclaw_spool.py — GPU turn-taking: local models rotate through a shared task queue.

One model resident at a time (keep_alive=0 => full spool-out after every turn), so every
turn pays the spool-in cost and the receipts measure it. Tasks are REAL fleet work:
cite-gap guesses, PX-result tagging, one-line meaning extraction.

EXPLORATORY instrument demo (no pre-reg branch; receipts only).
Run: python3 experiments/cudaclaw_spool.py
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
OUT_DIR = os.path.expanduser("~/projects/quilt-gpu-lab/results/cudaclaw_spool")
OUT = os.path.join(OUT_DIR, "receipts.jsonl")

# big spool last; every turn unloads the previous resident
MODELS = ["qwen3.5:0.8b", "tev1:0.8b", "qwen2.5:0.5b", "tev1:4b"]

TASKS = [
    # round 1: cite-gap guesses (feeds the paper panel)
    ("cite", "One line only: what venue and year published Shazeer et al.'s sparse mixture-of-experts layer with LSTM gating?"),
    ("cite", "One line only: what venue and year published Jacobs, Jordan, Nowlan, Hinton's adaptive mixtures of local experts?"),
    ("cite", "One line only: what venue and year published the Switch Transformer paper?"),
    ("cite", "One line only: what venue and year published MT-Bench / LLM-as-a-judge by Zheng et al.?"),
    # round 2: tag today's PX results
    ("tag", "Reply with a 2-4 word tag, nothing else: 'Composition top1 0.7437 sits below single d6 tree 0.7481 on full split; routing+gating 0.7774 beats it.'"),
    ("tag", "Reply with a 2-4 word tag, nothing else: 'Judge jev-1.13.0 returns needs_fix on 96/96 blind states; cross-field corr 0.9167 but degeneracy guard fires.'"),
    ("tag", "Reply with a 2-4 word tag, nothing else: 'Board router wins BLOCK 0.873 but dies NON_LOCAL 0.497; pure router KILL, gated arm claims 26.7% of headroom.'"),
    ("tag", "Reply with a 2-4 word tag, nothing else: '15 unique cell signatures over 36,073 states; MI(signature->success)=0.5955 bits vs MI(class)=0.1212 bits.'"),
    # round 3: one-line meaning (paper voice test on small models)
    ("mean", "One sentence: why does an exact solver ground truth make an ML result more trustworthy than human labels?"),
    ("mean", "One sentence: what does it mean that the routing signal is predictable for defense but not for positional play?"),
    ("mean", "One sentence: why is a lucky 0.855 control run dangerous for an experiment that runs unattended?"),
    ("mean", "One sentence: what is the cheapest defense against a judge model that almost always returns the same verdict?"),
]


def turn(model: str, kind: str, task: str) -> dict:
    t0 = time.time()
    payload = json.dumps({
        "model": model,
        "prompt": task,
        "keep_alive": 0,                      # spool-out after every turn
        "stream": False,
        "options": {"num_predict": 200},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read().decode())
    wall_ms = round((time.time() - t0) * 1000)
    spool_ms = round(data.get("load_duration", 0) / 1e6)
    eval_n, eval_d = data.get("eval_count", 0), data.get("eval_duration", 0)
    tok_s = round(eval_n / (eval_d / 1e9), 1) if eval_d else None
    rec = {
        "model": model, "kind": kind, "wall_ms": wall_ms, "spool_ms": spool_ms,
        "eval_tokens": eval_n, "tok_s": tok_s,
        "task_head": task[:70], "response_head": (data.get("response") or "").strip()[:220],
        "prompt_eval_count": data.get("prompt_eval_count"),
    }
    print(json.dumps(rec), flush=True)
    return rec


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    queue = list(TASKS)
    receipts = []
    with open(OUT, "w") as f:
        for rnd in range(3):
            for mi, model in enumerate(MODELS):
                kind, task = queue[mi + rnd * len(MODELS)]
                try:
                    rec = turn(model, kind, task)
                except Exception as e:  # fail loud per-turn, keep the lane moving
                    rec = {"model": model, "kind": kind, "error": f"{type(e).__name__}: {e}"}
                    print(json.dumps(rec), flush=True)
                rec["round"] = rnd
                receipts.append(rec)
                f.write(json.dumps(rec) + "\n")
                f.flush()
    ok = [r for r in receipts if "error" not in r]
    summary = {
        "turns": len(receipts), "ok": len(ok),
        "spool_ms_by_model": {m: [r.get("spool_ms") for r in ok if r["model"] == m] for m in MODELS},
        "tok_s_by_model": {m: [r.get("tok_s") for r in ok if r["model"] == m] for m in MODELS},
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"booked: {OUT_DIR}/", flush=True)


if __name__ == "__main__":
    main()
