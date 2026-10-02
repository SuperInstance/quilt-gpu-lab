#!/usr/bin/env python3
"""Generate 200 Eisenstein Z[omega] vectors (seeded 2718) and the 4x50 prompts
for the granite rate-vs-luck batch. Canonical judge lives in ../canonical_ref.py.

Vector i: z=(a,b), w=(c,d); ops: add(z,w), mul(z,w), conj(z), norm(z).
Output format one line per vector:
  i add:<a'> <b'> mul:<a'> <b'> conj:<a'> <b'> norm:<n>
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
RNG = random.Random(2718)
N = 200
BATCH = 10


def gen():
    vecs = []
    for i in range(N):
        a = RNG.randint(-9, 9)
        b = RNG.randint(-9, 9)
        c = RNG.randint(-9, 9)
        d = RNG.randint(-9, 9)
        vecs.append({"i": i, "z": [a, b], "w": [c, d]})
    return vecs


RULES = """Eisenstein integers Z[omega]: omega^2 = -1 - omega. Write z = a + b*omega.
Given z=(a,b) and w=(c,d):
  add(z,w)  = (a+c, b+d)
  mul(z,w)  = (a*c - b*d, a*d + b*c - b*d)
  conj(z)   = (a - b, -b)
  norm(z)   = a*a - a*b + b*b
All results are integers (norm is a plain integer, not a pair)."""


def prompt_for(chunk):
    lines = []
    for v in chunk:
        a, b = v["z"]
        c, d = v["w"]
        lines.append(f"  i={v['i']} z=({a},{b}) w=({c},{d})")
    return (RULES + "\n\nCompute add(z,w), mul(z,w), conj(z), norm(z) for EACH vector below.\n"
            "Output EXACTLY one line per vector, no prose, no markdown, format:\n"
            "  i add:A B mul:A B conj:A B norm:N\n\n"
            "Vectors:\n" + "\n".join(lines) + "\n")


def main():
    vecs = gen()
    (HERE / "vectors.json").write_text(json.dumps(vecs, indent=1))
    chunks = [vecs[k:k + BATCH] for k in range(0, N, BATCH)]
    for k, ch in enumerate(chunks):
        (HERE / f"prompt_{k}.txt").write_text(prompt_for(ch))
    print(json.dumps({"n": N, "batches": len(chunks), "batch_size": BATCH,
                      "seed": 2718, "range": [-9, 9]}))


if __name__ == "__main__":
    main()
