"""g1_run.py — G1 real seat run: certified 96-prompt battery under guard instrumentation.

Wraps fleet-seeds g1_seat_harness.mjs in guard.py (power.draw sampled on the
guard's poll thread for the whole window), supplies pre-run evidence with an
honest estimated-energy derivation, then emits BOTH receipts:

  1. harness receipt  — built by the harness from the pre-run evidence
                        (source: estimated; schema-legal, derivation declared)
  2. guard receipt    — MEASURED energy for the same window (mean power x wall),
                        sealed post-run binding guard_summary.json; appended to
                        results/g1/guard/ledger.jsonl as the measured correction
                        (append-only correction law — never edits receipt 1)

Post-run: blind scores responses against results/g1/battery-96-key.json.

Usage: /home/eileen/venvs/elephant-gpu/bin/python experiments/g1_run.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import guard  # noqa: E402

FLEET_SEEDS = LAB.parent / "fleet-seeds"
BATTERY = FLEET_SEEDS / "docs" / "g1" / "battery-96.json"
OUT_DIR = LAB / "results" / "g1" / "run1"
KEY = LAB / "results" / "g1" / "battery-96-key.json"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

# Pre-run energy derivation (honest estimated, both anchors measured):
#   mean load power 67.7 W  <- G7 live validation (results/g7 ledger, 2026-10-01)
#   wall estimate    576 s  <- 96 prompts x ~6 s mean from the 3-prompt smoke
MEAN_W = 67.7
WALL_EST = 576.0


def evidence() -> dict:
    joules = round(MEAN_W * WALL_EST, 1)
    wh = joules / 3600.0
    return {
        "device": {"model": "NVIDIA GeForce RTX 4050 Laptop GPU", "vram_gb": 6.0,
                   "driver": "616.92 / WSL2 (/usr/lib/wsl/lib/nvidia-smi)"},
        "energy": {"joules": joules, "watt_hours": round(wh, 6), "source": "estimated",
                   "sampling_method": ("operator pre-run derivation; concurrent measured "
                                       "sampler (guard.py poll thread, 5 s cadence) runs for "
                                       "the same window and its MEASURED receipt is appended "
                                       "as a correction immediately post-run (append-only)"),
                   "derivation": (f"mean_power 67.7 W (MEASURED, G7 live validation "
                                  f"results/g7, bf16 matmul load, 2026-10-01) x est. wall "
                                  f"{WALL_EST:.0f} s (96 prompts x ~6 s from 3-prompt smoke "
                                  f"timing) = {joules} J = {wh:.4f} Wh; idle floor NOT "
                                  f"subtracted; priced at $0.23/kWh")},
        "compute": {"gpu_seconds": WALL_EST},
        "cost": {"currency": "USD", "amount": round(wh / 1000.0 * 0.23, 6),
                 "rate_source": ("host marginal grid rate $0.23/kWh (Alaska residential "
                                 "average, quoted 2026-10-01); gifted compute priced")},
    }


VERDICT_RE = re.compile(r'"verdict"\s*:\s*"(SUPPORTED|REFUTED|INSUFFICIENT)"', re.I)


def score(responses_path: Path) -> dict:
    key = json.loads(KEY.read_text())["key"]
    bundle = json.loads(responses_path.read_text())
    rows, parse_ok, correct, done_n, trunc_n = [], 0, 0, 0, 0
    eval_tokens = []
    for r in bundle["responses"]:
        cid, text = r["prompt_id"], r.get("text", "")
        raw = r.get("raw") or {}
        done_reason = raw.get("done_reason")
        eval_count = (r.get("timing") or {}).get("eval_count")
        if eval_count:
            eval_tokens.append(eval_count)
        if done_reason == "length":
            trunc_n += 1
        elif done_reason in ("stop", "end_turn", None) or done_reason == "done":
            done_n += 1
        m = VERDICT_RE.search(text)
        if not m:
            m2 = re.search(r"\b(SUPPORTED|REFUTED|INSUFFICIENT)\b", text, re.I)
            m = m2.group(0) and re.match(r"SUPPORTED|REFUTED|INSUFFICIENT", m2.group(0), re.I) or m
        got = m.group(1).upper() if m else None
        if got:
            parse_ok += 1
        exp = key.get(cid, {}).get("expected")
        hit = got == exp
        correct += hit
        rows.append({"id": cid, "expected": exp, "got": got, "correct": hit,
                     "done_reason": done_reason, "eval_count": eval_count,
                     "wall_ms": r.get("wall_ms")})
    n = len(rows)
    return {
        "prompts": n,
        "parse_ok": parse_ok,
        "verdict_correct": correct,
        "accuracy": round(correct / n, 4) if n else None,
        "completion_rate": round((n - trunc_n) / n, 4) if n else None,
        "truncated": trunc_n,
        "mean_eval_tokens": round(sum(eval_tokens) / len(eval_tokens), 1) if eval_tokens else None,
        "max_eval_tokens": max(eval_tokens) if eval_tokens else None,
        "rows": rows,
    }


def main():
    ev = evidence()
    ev_path = OUT_DIR / "run-evidence.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ev_path.write_text(json.dumps(ev, indent=1))

    g = guard.Guard(timeout_s=3600.0, task_id="G1-seat-spike",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed="31,50,23,51 (moth-seal g1-battery-96-master)",
                    receipt_dir=str(LAB / "results" / "g1" / "guard"))
    if not g.preflight():
        print(f"PREFLIGHT REFUSED: {g.breach}")
        sys.exit(2)
    cmd = ["node", str(FLEET_SEEDS / "scripts" / "g1_seat_harness.mjs"),
           "--battery", str(BATTERY), "--run-evidence", str(ev_path),
           "--model", MODEL, "--task-id", "G1-seat-spike",
           "--agent", "quilt-gpu-lab keeper (Lucineer, main Super Z)",
           "--out-dir", str(OUT_DIR)]
    rc, out, err = g.run(cmd, cwd=str(FLEET_SEEDS), env=dict(os.environ))
    print(f"harness rc={rc}")
    print(out[-1500:])
    if err.strip():
        print("stderr tail:", err[-600:])

    if rc == 0:
        rpath, receipt = g.emit_receipt()
        ok, msg = g.validate_receipt(rpath)
        print(f"guard MEASURED receipt: {rpath} valid={ok}")
        print(json.dumps({k: receipt[k] for k in ("energy", "compute", "gate") if k in receipt}, indent=1))
        resp = sorted(OUT_DIR.glob("*-responses.json"))[-1]
        s = score(resp)
        (OUT_DIR / "score.json").write_text(json.dumps(s, indent=1))
        print(f"SCORE: prompts={s['prompts']} parse_ok={s['parse_ok']} "
              f"correct={s['verdict_correct']} accuracy={s['accuracy']} "
              f"completion={s['completion_rate']} truncated={s['truncated']} "
              f"mean_eval_tokens={s['mean_eval_tokens']}")
    else:
        g.emit_receipt(verdict="VOID", void_reason=f"harness exit {rc}")
        print("VOID receipt sealed for failed run")
    sys.exit(0 if rc == 0 else 2)


if __name__ == "__main__":
    main()
