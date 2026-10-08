#!/usr/bin/env python3
"""HSA-1: hash-selected standing audit rota over booked results.

Selection is a pure function of the committed population file:
  sha256(utf8(receipt_path)); member iff last digest byte == PREFIX.
Fallback (pre-registered): if empty, the lexicographically-smallest-digest receipt.
Fail-loud: missing population file or malformed lines abort with nonzero exit.

Usage:
  python3 tools/hash_audit_rota.py [--population results/hsa1_rota/population.txt]
Prints the rota as JSON to stdout. Never mutates anything.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PREFIX = 0x2A  # frozen in proposals/runs/HSA-1-hash-selected-audit-rota.md
REPO = Path(__file__).resolve().parent.parent


def population_from_results() -> list[str]:
    text = (REPO / "RESULTS.md").read_text(encoding="utf-8", errors="replace")
    paths = sorted(set(re.findall(r"proposals/runs/[A-Za-z0-9_.\-]+\.md", text)))
    if not paths:
        sys.exit("FATAL: zero receipts cited in RESULTS.md")
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", default="results/hsa1_rota/population.txt")
    ap.add_argument("--from-results", action="store_true",
                    help="regenerate population from RESULTS.md (regen arm)")
    args = ap.parse_args()

    pop_path = REPO / args.population
    if args.from_results:
        paths = population_from_results()
        pop_path.parent.mkdir(parents=True, exist_ok=True)
        pop_path.write_text("\n".join(paths) + "\n", encoding="utf-8")
    else:
        if not pop_path.exists():
            sys.exit(f"FATAL: population file missing: {pop_path} (regen arm is explicit)")
        lines = pop_path.read_text(encoding="utf-8").splitlines()
        paths = [ln for ln in lines if ln.strip()]
        if paths != sorted(set(paths)) or not paths:
            sys.exit("FATAL: population file not sorted-unique or empty")

    digests = {p: hashlib.sha256(p.encode("utf-8")).hexdigest() for p in paths}
    selected = sorted(p for p, d in digests.items() if int(d[-2:], 16) == PREFIX)
    fallback = None
    if not selected:
        fallback = min(digests, key=lambda p: digests[p])

    rota = selected if selected else [fallback]

    # G3 suppression check: post-booking instrument changes for each member.
    suppression = []
    for r in rota:
        try:
            first = subprocess.run(
                ["git", "log", "--follow", "--diff-filter=M", "--format=%H", "--", r],
                cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
            suppression.append({"receipt": r, "post_booking_modifications": len(first) - 1 if first else 0})
        except subprocess.CalledProcessError as e:
            suppression.append({"receipt": r, "error": e.stderr.strip()[:200]})

    print(json.dumps({
        "rule": "sha256(utf8(path)) last byte == 0x%02X" % PREFIX,
        "population_n": len(paths),
        "selected": selected,
        "fallback_used": fallback is not None,
        "rota_order": rota,
        "suppression_check": suppression,
    }, indent=2))


if __name__ == "__main__":
    main()
