#!/usr/bin/env python3
"""reloc-gate — semantic-identity gate for relocated code blocks.

Pattern lifted PROVEN from EP-1d (commit 5fbf882, 2026-10-05: the G-DRY dry-run
block in tools/ep1d_pointer_census.py was moved wholesale to fix an
UnboundLocalError with "no semantic delta" claimed in the commit message).
This tool mechanizes that claim: given a named block and two git revisions, it
extracts the block from both, normalizes it (blank lines, comments, trailing
whitespace dropped; leading indentation compared only relatively), and requires
EXACT line-sequence identity. A move is only a move if the lines did not change.

Fail-loud; stdlib-only; never mutates the repo (reads via `git show`).
Exit codes: 0 = IDENTITY (block preserved), 1 = RED (block drifted or missing
in either revision), 2 = FAIL-INPUT (bad args, bad ref, bad path).

Library: extract_block(text, start_sub, end_sub) -> str
         normalize_block(lines) -> list[str]
         reloc_identity(old_text, new_text, start, end) -> (ok: bool, why: str)

Worked example (the real EP-1d move):
    python tools/reloc_gate.py --file tools/ep1d_pointer_census.py \
        --start "# EP-1d G-DRY" --end "DRY-VERDICT" \
        --ref-old 5fbf882~1 --ref-new 5fbf882
    -> IDENTITY rc=0 (the block moved, lines identical)

    python tools/reloc_gate.py --selftest
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def fail_loud(msg):
    print(f"FAIL-LOUD: {msg}")
    sys.exit(2)


def extract_block(text, start_sub, end_sub):
    """Lines from the first line containing start_sub through the first later
    line containing end_sub (inclusive). Raises ValueError if not found."""
    lines = text.splitlines()
    s = next((i for i, ln in enumerate(lines) if start_sub in ln), None)
    if s is None:
        raise ValueError(f"start marker not found: {start_sub!r}")
    e = next((i for i in range(s, len(lines)) if end_sub in lines[i]), None)
    if e is None or e < s:
        raise ValueError(f"end marker not found after start: {end_sub!r}")
    return "\n".join(lines[s:e + 1])


def normalize_block(block):
    """Code lines only: drop blank lines, comment-only lines, and trailing
    whitespace. Keeps content lines verbatim (order and spelling must match)."""
    out = []
    for ln in block.splitlines():
        t = ln.rstrip()
        if not t.strip():
            continue
        if t.lstrip().startswith("#"):
            continue
        out.append(t)
    return out


def reloc_identity(old_text, new_text, start, end):
    """(ok, why): ok iff both blocks extract and normalized lines are equal."""
    try:
        old_b = normalize_block(extract_block(old_text, start, end))
    except ValueError as e:
        return False, f"OLD revision: {e}"
    try:
        new_b = normalize_block(extract_block(new_text, start, end))
    except ValueError as e:
        return False, f"NEW revision: {e}"
    if not old_b:
        return False, "OLD block normalizes to empty"
    if not new_b:
        return False, "NEW block normalizes to empty"
    if old_b != new_b:
        for i, (a, b) in enumerate(zip(old_b, new_b)):
            if a != b:
                return False, f"line {i + 1} drifted:\n  OLD: {a}\n  NEW: {b}"
        longer, which = (old_b, "OLD") if len(old_b) > len(new_b) else (new_b, "NEW")
        return False, f"{which} block has {len(longer)} content lines vs {min(len(old_b), len(new_b))}: extra {longer[min(len(old_b), len(new_b))]!r}"
    return True, f"IDENTITY: {len(old_b)} content lines match exactly"


def git_show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO,
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        fail_loud(f"git show {ref}:{path} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def selftest():
    """Hermetic battery: PASS control + tamper RED + missing-marker rc=2."""
    old = "def f():\n    # marker A\n    for i in range(3):\n        y = step(x, i)\n    # end A\n    return y\n"
    moved = "def f():\n    return y\n    # marker A\n    for i in range(3):\n        y = step(x, i)\n    # end A\n"
    drifted = moved.replace("range(3)", "range(4)")
    checks = []
    ok, why = reloc_identity(old, moved, "# marker A", "# end A")
    checks.append(("move-identity PASS control", ok, why))
    ok, why = reloc_identity(old, drifted, "# marker A", "# end A")
    checks.append(("tamper RED control", (not ok) and "drifted" in why, why))
    ok, why = reloc_identity(old, moved, "# missing", "# end A")
    checks.append(("missing-start fails", (not ok) and "not found" in why, why))
    bad = [n for n, passed, _ in checks if not passed]
    for n, passed, why in checks:
        print(f"  {'PASS' if passed else 'FAIL'}: {n} :: {why.splitlines()[0]}")
    print(f"SELFTEST: {'OK' if not bad else 'FAIL ' + str(bad)}")
    sys.exit(0 if not bad else 1)


def main():
    ap = argparse.ArgumentParser(description="Semantic-identity gate for relocated code blocks.")
    ap.add_argument("--file", help="repo-relative file path")
    ap.add_argument("--start", help="substring marking block start")
    ap.add_argument("--end", help="substring marking block end (inclusive)")
    ap.add_argument("--ref-old", default="HEAD~1", help="git ref for the before state")
    ap.add_argument("--ref-new", default="HEAD", help="git ref for the after state")
    ap.add_argument("--selftest", action="store_true", help="hermetic control battery")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    for req, val in (("--file", a.file), ("--start", a.start), ("--end", a.end)):
        if not val:
            fail_loud(f"{req} is required (or use --selftest)")
    old_t = git_show(a.ref_old, a.file)
    new_t = git_show(a.ref_new, a.file)
    ok, why = reloc_identity(old_t, new_t, a.start, a.end)
    print(f"reloc-gate {a.file} [{a.ref_old} -> {a.ref_new}]: {why}")
    print(f"VERDICT: {'IDENTITY' if ok else 'RED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
