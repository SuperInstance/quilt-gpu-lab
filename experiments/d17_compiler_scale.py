#!/usr/bin/env python3
"""D17 — does the compiler actually COMPRESS at scale? (the honest null-check)

The compiler (qthe_compiler.py) separates the two planes and RLE-encodes the
timbre plane. The smoke test showed a 3.25x INFLATION on 12 bytes — but that
was fixed-header overhead (magic + 2 length fields + crc32) swamping a tiny
payload. This closes the loop: does the compiler actually win on a REAL-scale
tone stream, and WHERE is the crossover?

Falsifiable claim (pre-registered): on a realistic-length text (>= 500 bytes)
with a tone trajectory that has long runs (real tone, not noise), the compiled
form must be SMALLER than the raw byte stream (ratio < 1.0), and the timbre
plane must compress (RLE < raw). If the compiler never beats raw even at scale,
it is a toy, not a tool -> KILL.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "projects" / "qthe-codec"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import qthe_codec as qc
import qthe_compiler as qcomp

SEED = 2718


def make_realistic_text(rng, n_chars):
    """A realistic paragraph: a fixed vocabulary with spaces and punctuation,
    so the data plane is high-entropy (text is NOT compressible by RLE)."""
    words = ["the", "sea", "does", "not", "know", "about", "you", "yet",
             "keeps", "its", "own", "counsel", "under", "a", "grey", "sky",
             "and", "the", "tide", "comes", "in", "without", "asking"]
    text = []
    while sum(len(w) + 1 for w in text) < n_chars:
        text.append(rng.choice(words))
    return " ".join(text)


def make_tonal_trajectory(rng, n_tokens):
    """A tone trajectory with LONG RUNS (real emotional arcs), the kind of
    thing RLE should crush: slow rises, long flats, sudden drops."""
    d, f, u, h = 0, 1, 2, 3
    tone = []
    while len(tone) < n_tokens:
        kind = rng.choice(["rise", "flat", "drop", "hold"])
        run = rng.randint(8, 40)
        tone += {"rise": [u], "flat": [f], "drop": [d], "hold": [h]}[kind] * run
    return tone[:n_tokens]


def main():
    rng = random.Random(SEED)
    sizes = [50, 200, 500, 1000, 2000, 4000]
    table = []
    for n in sizes:
        text = make_realistic_text(rng, n)
        data = qc.data_encode(text)
        tone = make_tonal_trajectory(rng, len(data))
        stream = qc.encode(text, tone)
        compiled = qcomp.compile(stream)
        r = qcomp.compression_ratio(stream)
        table.append({
            "n_chars": n, "raw_bytes": r["raw_bytes"], "compiled_bytes": r["compiled_bytes"],
            "ratio": r["ratio"], "momentum_compression": r["momentum_compression"],
            "wire_compression": r["wire_compression"],
        })

    # crossover: first size where ratio < 1.0
    crossover = None
    for row in table:
        if row["ratio"] < 1.0:
            crossover = row["n_chars"]
            break

    # verify roundtrip at the largest size
    text = make_realistic_text(rng, 2000)
    stream = qc.encode(text, make_tonal_trajectory(rng, len(qc.data_encode(text))))
    assert qcomp.decompile(qcomp.compile(stream)) == stream, "roundtrip failed at scale"
    assert qc.decode_bytes(stream)[0] == text, "text did not survive the compiler at scale"

    largest = table[-1]
    verdict = "KEEP" if (largest["ratio"] < 1.0 and largest["momentum_compression"] < 1.0) else "KILL"
    result = {
        "experiment": "D17 compiler compression at scale",
        "seed": SEED,
        "table": table,
        "crossover_chars": crossover,
        "largest_ratio": largest["ratio"],
        "largest_momentum_compression": largest["momentum_compression"],
        "verdict": verdict,
        "note": "compiler must beat raw at scale (ratio<1.0) AND the momentum plane must compress; roundtrip verified. The fix (found by the first D17 KILL): the Latin square scrambles the WIRE timbre, so RLE must run on the DECODED momentum (with context), not the wire.",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
