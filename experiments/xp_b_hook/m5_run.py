#!/usr/bin/env python3
"""m5_run.py — M5 GPU lane: ONE guard window around all ticks.

guard.py contract used: Guard(task_id="XP-B-hook-gpu-cell"); preflight/run;
emit_receipt(). NOTE (defect booked): Guard._stop is a one-shot Event, so a Guard
instance watches only its FIRST run(); all ticks therefore run in a single child
process. Preflight refusal -> wait 60 s, retry once, else M5 = NOT-RUN.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = "/home/eileen/projects/quilt-gpu-lab"
GPU_PY = "/home/eileen/venvs/elephant-gpu/bin/python"
TICKS_ALL = os.path.join(HERE, "m5_gpu_ticks_all.py")
OUT = os.path.join(HERE, "out")

sys.path.insert(0, LAB)
import guard  # noqa: E402


def go() -> int:
    os.makedirs(OUT, exist_ok=True)
    g = guard.Guard(timeout_s=300.0, task_id="XP-B-hook-gpu-cell",
                    receipt_dir=os.path.join(OUT, "g7"))
    if not g.preflight():
        print("preflight refused: %s — waiting 60 s" % g.breach, flush=True)
        time.sleep(60)
        g = guard.Guard(timeout_s=300.0, task_id="XP-B-hook-gpu-cell",
                        receipt_dir=os.path.join(OUT, "g7"))
        if not g.preflight():
            ev = {"ran": False, "note": "guard preflight refused twice: %s" % g.breach}
            json.dump(ev, open(os.path.join(OUT, "m5_gpu.json"), "w"), indent=2)
            print(json.dumps(ev))
            return 0

    env = dict(os.environ)
    env["PYTHONPATH"] = HERE + ":" + env.get("PYTHONPATH", "")
    rc, out, err = g.run([GPU_PY, TICKS_ALL], cwd=HERE, env=env)
    if rc != 0:
        print("ticks rc=%d\n%s\n%s" % (rc, out[-500:], err[-1500:]), file=sys.stderr)
    ticks = json.load(open(os.path.join(OUT, "m5_ticks.json")))
    a, b, c = ticks["a"], ticks["b"], ticks["c"]

    det = {"dials_identical": a["dials"] == b["dials"],
           "state_sha256_identical": a["state_sha256"] == b["state_sha256"],
           "dials_a": a["dials"], "dials_b": b["dials"],
           "state_sha256": a["state_sha256"]}

    verdict = "PASS" if (det["state_sha256_identical"] and rc == 0) else "VOID"
    path, receipt = g.emit_receipt(verdict=verdict)

    with open(os.path.join(OUT, "m5_gpu.json"), "w") as f:
        json.dump({
            "ran": True, "process_rc": rc,
            "ticks": {"a": a, "b": b, "c": c},
            "determinism": det,
            "cell_seed2718": {"id": "cell-gpu000", "kind": "matmul", "seed": 2718,
                              "body": "gpu tick 2718 (device %s, torch %s)" % (a["device"], a["torch"]),
                              "dials": a["dials"]},
            "dials_seed2719": c["dials"],
            "ramp_receipt": a["ramp_receipt"],
            "guard_receipt": {"path": path, "receipt_id": receipt["receipt_id"],
                              "gate_verdict": receipt["gate"]["verdict"],
                              "joules": receipt["energy"]["joules"],
                              "watt_hours": receipt["energy"]["watt_hours"],
                              "source": receipt["energy"]["source"],
                              "gpu_seconds": receipt["compute"]["gpu_seconds"]},
        }, f, indent=2)
    print(json.dumps({"det": det["dials_identical"],
                      "guard": {"joules": receipt["energy"]["joules"],
                                "watt_hours": receipt["energy"]["watt_hours"],
                                "gpu_seconds": receipt["compute"]["gpu_seconds"],
                                "verdict": receipt["gate"]["verdict"]},
                      "tick_wall_s": [a["wall_s"], b["wall_s"], c["wall_s"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(go())
