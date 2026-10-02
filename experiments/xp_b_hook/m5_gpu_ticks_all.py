#!/usr/bin/env python3
"""m5_gpu_ticks_all.py — all M5 GPU ticks inside ONE guarded process window.

3 ticks: seed 2718 twice (determinism control) + seed 2719 (replay).
Writes out/m5_ticks.json. Run under guard.py (see m5_run.py).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from m5_gpu_tick import tick  # noqa: E402


def main() -> int:
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    recs = {"a": tick(2718), "b": tick(2718), "c": tick(2719)}
    with open(os.path.join(out, "m5_ticks.json"), "w") as f:
        json.dump(recs, f, indent=2, sort_keys=True)
    print(json.dumps({k: {"seed": v["seed"], "wall_s": v["wall_s"],
                          "state_sha256": v["state_sha256"]} for k, v in recs.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
