#!/usr/bin/env python3
"""m4_avalanche.py — 1-bit input flip -> output-bit-change distribution.

Control arm for M4: the SAME measurement applied to two different digests
(house rule: vary the audited thing by a different path).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qthe_receipt as q  # noqa: E402

TRIALS = 20000


def popcount(x: int) -> int:
    return bin(x).count("1")


def main() -> int:
    rng = random.Random(2718)
    fnv_bits = []
    sha_bits = []
    for _ in range(TRIALS):
        buf = bytearray(rng.getrandbits(8) for _ in range(16))
        j = rng.randrange(16)
        k = rng.randrange(8)
        b2 = bytearray(buf)
        b2[j] ^= (1 << k)
        fnv_bits.append(popcount(q.fnv1a64(bytes(buf)) ^ q.fnv1a64(bytes(b2))))
        s1 = hashlib.sha256(bytes(buf)).digest()
        s2 = hashlib.sha256(bytes(b2)).digest()
        sha_bits.append(popcount(int.from_bytes(s1, "big") ^ int.from_bytes(s2, "big")))
    out = {
        "trials": TRIALS,
        "fnv1a64": {"ideal_bits": 32, "mean_bits_changed": round(sum(fnv_bits) / TRIALS, 3),
                    "min": min(fnv_bits), "max": max(fnv_bits)},
        "sha256": {"ideal_bits": 128, "mean_bits_changed": round(sum(sha_bits) / TRIALS, 3),
                   "min": min(sha_bits), "max": max(sha_bits)},
        "note": "1-bit input flip, 16-byte messages, seed 2718",
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "m4_avalanche.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
