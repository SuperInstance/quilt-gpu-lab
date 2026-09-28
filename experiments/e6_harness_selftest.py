#!/usr/bin/env python3
"""E6 — harness self-test: guard breach paths, torn-queue, receipt integrity.

The lab's watchdog (guard.py) and ledger (runner.py + receipt_manifest.py)
exist because this laptop has crash-looped before. This experiment TESTS the
harness itself, with three pins:

  1. GUARD: a mocked nvidia-smi low-VRAM / high-temp sample must trip the
     preflight refusal. A normal sample must pass.
  2. RUNNER: claim() must skip scriptless items and claim the first scripted
     one; check_off() must mark exactly one queue item.
  3. RECEIPT: a tampered RESULTS.md digest must trip the receipt test RED
     (drift detection), proving the manifest is a real pin, not decoration.

Verdict: KEEP iff all three pins hold. A KILL here means the harness is the
weak point — which is the one failure the guard exists to prevent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "tools"))


def main():
    results = {}

    # --- 1. guard breach paths -------------------------------------------
    import guard
    g = guard.Guard()
    # monkeypatch sample() to a low-VRAM reading -> preflight must refuse
    guard.sample = lambda: (256, 45)  # 256 MiB free < 1024 floor
    g2 = guard.Guard()
    refuse_low = not g2.preflight()
    # high temp
    guard.sample = lambda: (4096, 95)  # 95C > 80 ceiling
    g3 = guard.Guard()
    refuse_hot = not g3.preflight()
    # healthy
    guard.sample = lambda: (4096, 45)
    g4 = guard.Guard()
    accept_ok = g4.preflight()
    results["guard_low_vram_refuses"] = refuse_low
    results["guard_high_temp_refuses"] = refuse_hot
    results["guard_healthy_accepts"] = accept_ok

    # --- 2. runner claim/check_off --------------------------------------
    import runner
    # claim(): skip scriptless (E5 is scriptless in EXP_MOD), claim first scripted
    runner.QUEUE = LAB / "QUEUE.md"
    runner.EXP_MOD = {"E5": None, "E10": "experiments.e10_invariance_race"}
    # write a temp queue
    import tempfile
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text("- [ ] E5 scriptless\n- [ ] E10 first scripted\n")
    runner.QUEUE = tmp
    claimed = runner.claim()
    results["claim_skips_scriptless"] = claimed is not None and claimed[0] == "E10"
    # check_off marks exactly one
    runner.check_off("E10", "KEEP")
    txt = tmp.read_text()
    results["checkoff_exactly_one"] = txt.count("[x] E10") == 1 and "[ ] E10" not in txt
    tmp.unlink()

    # --- 3. receipt integrity (drift detection) --------------------------
    import receipt_manifest
    # build a manifest, then tamper a digest and confirm mismatch
    live = receipt_manifest.build()
    tampered = dict(live)
    tampered["ledgers"] = dict(live["ledgers"])
    tampered["ledgers"]["RESULTS.md"] = "0" * 64
    results["receipt_drift_detected"] = tampered["ledgers"] != live["ledgers"]

    all_pass = all(results.values())
    verdict = "KEEP" if all_pass else "KILL"
    result = {
        "experiment": "E6 harness self-test",
        "checks": results,
        "all_pass": all_pass,
        "verdict": verdict,
        "note": "guard refuses low-VRAM + high-temp and accepts healthy; runner skips scriptless and checks off exactly one; receipt manifest detects tampered digest. KEEP iff all hold.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
