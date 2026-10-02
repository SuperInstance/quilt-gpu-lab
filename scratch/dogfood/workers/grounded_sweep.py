#!/usr/bin/env python3
"""grounded_sweep.py — deterministic scan for the `coercion-before-??` bug class.

Detects: <unary +/-/! operation> or Number()/parseInt()/parseFloat() applied
DIRECTLY to an operand, immediately followed by `??` with NO parentheses around
the coercion. In that case the coercion binds first, so a missing value becomes
NaN and `NaN ?? d` returns NaN (default dead).

Also reports the SANE near-miss: `+(x ?? d)` / `Number(x ?? d)` (default first).
"""
import re
import sys
from pathlib import Path

ROOTS = [
    "/home/eileen/projects/superinstance-api/src",
    "/home/eileen/projects/superinstance-api/scripts",
    # edge-lab arm = the PRESERVED PRE-FIX tree (the read-only clone now carries
    # the applied patch on branch dogfood/promote-precedence-fix).
    "/home/eileen/projects/quilt-gpu-lab/scratch/dogfood/workers/edge-lab-buggy/src",
    "/home/eileen/projects/quilt-gpu-lab/scratch/dogfood/workers/edge-lab-buggy/tools",
    "/home/eileen/projects/quilt-gpu-lab/experiments",
]

# BUG: coercion then ?? with no wrapping parens. The unary coercion must START
# an expression (preceded by = ( , : [ ; { return, or line start) — this excludes
# binary `+` used for string concatenation / addition.
BUG_UNARY = re.compile(
    r'(?:^|[=(,:;\[\]{}]|\breturn)\s*[+\-!](?!=)\s*[A-Za-z_$0-9"\'\[](?:[\w$.\[\]()"\']*)\s*\?\?')
BUG_CALL = re.compile(r'\b(?:Number|parseInt|parseFloat)\s*\([^()]*\)\s*\?\?')
# SANE near-miss: default applied INSIDE the coercion call/paren.
SANE = re.compile(r'[+\-!]\s*\([^()]*\?\?[^()]*\)|\b(?:Number|parseInt|parseFloat)\s*\([^()]*\?\?[^()]*\)')


def scan():
    tot = {"BUG": 0, "SANE": 0}
    for root in ROOTS:
        p = Path(root)
        if not p.exists():
            print(f"--- {root}: MISSING ---")
            continue
        files = [f for f in p.rglob("*") if f.is_file() and f.suffix in (".js", ".mjs", ".ts")]
        bugs, sanes = [], []
        for f in files:
            try:
                for i, line in enumerate(f.read_text().splitlines(), 1):
                    if "??" not in line:
                        continue
                    if BUG_UNARY.search(line) or BUG_CALL.search(line):
                        bugs.append((f, i, line.strip()))
                    elif SANE.search(line):
                        sanes.append((f, i, line.strip()))
            except OSError:
                pass
        tot["BUG"] += len(bugs)
        tot["SANE"] += len(sanes)
        print(f"--- {root}: {len(files)} files, {len(bugs)} BUG, {len(sanes)} SANE ---")
        for f, i, ln in bugs:
            print(f"  BUG  {f}:{i}: {ln}")
    print("\nTOTAL:", tot)


if __name__ == "__main__":
    scan()
