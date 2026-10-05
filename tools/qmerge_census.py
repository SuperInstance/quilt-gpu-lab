#!/usr/bin/env python3
"""qmerge-census — near-duplicate queue-item census (Q0 MERGE operator, stdlib-only).

Pattern lifted from rc-20260824-11's Q0 question-evolution POC (SCOUT-46
TOOL/STEAL receipt, 2026-10-05): MERGE = detect redundant queue items before
they are fired twice. We have spawned near-duplicates before (FR-1/FR-2,
RC-4/FW-M1 converged on the same ground from different scouts). This tool
parses a markdown checklist (QUEUE.md convention: lines starting with
optional whitespace + `- [ ]` / `- [x]`), tokenizes each item, and reports
pairs whose token Jaccard similarity >= a threshold. Deterministic,
read-only, fail-loud. It NEVER edits the queue — it books a census the
human/lane acts on (Q0-R1 discipline: design note, no mass-edit).

Usage:
  python tools/qmerge_census.py --file QUEUE.md [--threshold 0.55] [--out r.json]
  python tools/qmerge_census.py --selftest

Exit codes: 0 = census clean (no pairs over threshold), 1 = FINDINGS (pairs
need eyes), 2 = fail-loud input error.

Worked example:
  items.md contains:
    - [ ] FR-1 probe the noise floor at p=0.3
    - [ ] FR-2 probe the noise floor at p=0.3 with 32 agents
    - [ ] B1 sweep widths on pong
  -> FR-1/FR-2 pair reported (high Jaccard), B1 clean. rc=1 (FINDINGS).
"""

import argparse
import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+")


def parse_items(text):
    """Return (id, line_no, title, tokens) for each checklist item."""
    items = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*-\s\[( |x|X)\]\s+(.*)$", line)
        if not m:
            continue
        title = m.group(2).strip()
        # strip markers/status noise so they don't inflate similarity
        body = re.sub(r"\*\*", "", title)
        toks = frozenset(TOKEN_RE.findall(body.lower()))
        if not toks:
            continue
        # stable id: first 8 hex of sha256 of the title
        iid = "q" + hashlib.sha256(title.encode()).hexdigest()[:8]
        items.append({"id": iid, "line": i, "title": title, "tokens": toks})
    return items


def jaccard(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def census(items, threshold):
    pairs = []
    for a, b in combinations(items, 2):
        j = jaccard(a["tokens"], b["tokens"])
        if j >= threshold:
            pairs.append({
                "a": a["id"], "b": b["id"],
                "a_line": a["line"], "b_line": b["line"],
                "jaccard": round(j, 4),
                "a_title": a["title"], "b_title": b["title"],
            })
    return pairs


def run(path, threshold, out):
    text = Path(path).read_text(encoding="utf-8")
    items = parse_items(text)
    if not items:
        raise SystemExit("qmerge-census: no checklist items found in %s" % path)
    pairs = census(items, threshold)
    receipt = {
        "tool": "qmerge_census",
        "file": str(path),
        "threshold": threshold,
        "n_items": len(items),
        "n_pairs_over": len(pairs),
        "pairs": pairs,
    }
    if out:
        Path(out).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def selftest():
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    # near-duplicate detection
    text = ("- [ ] FR-1 probe the noise floor at p=0.3\n"
            "- [ ] FR-2 probe the noise floor at p=0.3 with 32 agents\n"
            "- [ ] B1 sweep widths on pong\n")
    items = parse_items(text)
    pairs = census(items, 0.55)
    check("near-dup pair found", len(pairs) == 1)
    check("clean item not paired", all(
        "fr-1" in p["a_title"].lower() and "fr-2" in p["b_title"].lower()
        for p in pairs))

    # threshold honesty: 0.95 must clear the same pair
    check("strict threshold finds nothing", census(items, 0.95) == [])

    # identical items -> jaccard 1.0
    dup = parse_items("- [x] same task alpha\n- [ ] same task alpha\n")
    check("identical items j=1.0", dup and jaccard(
        dup[0]["tokens"], dup[1]["tokens"]) == 1.0)

    # fail-loud: empty corpus
    try:
        run("/nonexistent/qmerge_selftest_%d.md" % id(text), 0.5, None)
        check("missing file fails loud", False)
    except (FileNotFoundError, SystemExit):
        check("missing file fails loud", True)

    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if not all(ok for _, ok in checks):
        sys.exit(1)
    print("selftest %d/%d" % (len(checks), len(checks)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help="markdown checklist to census (QUEUE.md style)")
    ap.add_argument("--threshold", type=float, default=0.55,
                    help="Jaccard threshold for MERGE candidates (default 0.55)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return
    if not a.file:
        ap.error("--file or --selftest required")
    try:
        r = run(a.file, a.threshold, a.out)
    except (OSError, ValueError) as e:
        print("FAIL-INPUT: %s" % e)
        sys.exit(2)
    print("items=%d threshold=%.2f pairs_over=%d" %
          (r["n_items"], r["threshold"], r["n_pairs_over"]))
    for p in r["pairs"]:
        print("MERGE? j=%.2f  L%d %s..." % (
            p["jaccard"], p["a_line"], p["a_title"][:60]))
        print("        vs L%d %s..." % (p["b_line"], p["b_title"][:60]))
    sys.exit(1 if r["pairs"] else 0)


if __name__ == "__main__":
    main()
