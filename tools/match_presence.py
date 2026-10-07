#!/usr/bin/env python3
"""match_presence — no-zero-match gate for any probe/haystack census.

Pattern lifted PROVEN from MUA-1, booked PASS 2026-10-07 (commit 575a77b):
a grep-style census that GREENs with ZERO matches is indistinguishable from
clean — it may just be a dead matcher (corrupt join, case-folding regression,
empty haystack). Every probe must assert POSITIVE EVIDENCE (matched somewhere,
count >= 1) before a pass is recorded; zero matched evidence books
INDETERMINATE, never CLEAN. Mutant-applied canary (MUA-1 G3b): a seeded term
injected into a copy of a haystack MUST be found — proves the matcher is alive.

Gates:
  G1 positive evidence — every probe matches >= min_count (default 1) somewhere.
  G2 negative control — the neg term returns zero hits on the live haystacks.
  G3 matcher-alive canary — the neg term, seeded into a copy of a designated
     haystack, IS found (mutant applied, detection witnessed).
  G4 vacuity guard — total haystack bytes must exceed a floor; an empty corpus
     is fail-loud, not a quiet pass.

Exit: 0 = CLEAN (all gates pass) / 1 = RED (any gate fails) / 2 = fail-loud
input error. One JSON receipt either way. Stdlib-only, read-only.

Usage:
  python tools/match_presence.py --probes 'taintA,taintB' --neg taintNEG \\
      --haystack file1.txt --haystack file2.txt [--out r.json] [--selftest]

Worked example (docstring is runnable intent):
  echo "the taintA landed here" > /tmp/h1.txt
  python tools/match_presence.py --probes taintA --neg nope --haystack /tmp/h1.txt
  -> CLEAN rc=0 with per-probe match counts.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile

MIN_BYTES = 32  # G4 vacuity floor: corpus must carry real content


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def load_haystacks(paths):
    """Read each path; return list of {path, text, sha256}. Missing/empty fail loud."""
    out = []
    for p in paths:
        if not os.path.isfile(p):
            raise SystemExit(f"FAIL-INPUT: haystack not a file: {p}")
        with open(p, "rb") as f:
            raw = f.read()
        if len(raw) < MIN_BYTES:
            raise SystemExit(
                f"FAIL-INPUT: haystack {p} has {len(raw)} bytes < floor {MIN_BYTES} "
                f"(empty corpus is not a census, it is a tautology)")
        out.append({"path": p, "text": raw.decode("utf-8", errors="replace"),
                    "sha256": _sha256(raw)})
    return out


def count_matches(haystacks, term):
    """Case-insensitive total + per-file match counts for term. Never echoes content."""
    per_file = {}
    total = 0
    t = term.lower()
    for h in haystacks:
        n = h["text"].lower().count(t)
        if n:
            per_file[h["path"]] = n
        total += n
    return total, per_file


def run_gate(probes, neg, haystacks, min_count=1):
    """Returns (ok, findings, details). G1-G4 per module docstring."""
    findings = []
    details = {"g1": {}, "g2": None, "g3": None}

    # G4 vacuity guard first — a trivial corpus fails loud.
    total_bytes = sum(os.path.getsize(h["path"]) for h in haystacks)
    if total_bytes < MIN_BYTES * len(haystacks):
        findings.append(f"G4 vacuity: corpus {total_bytes}B below floor")
        return False, findings, details

    # G1 positive evidence.
    for p in probes:
        total, per_file = count_matches(haystacks, p)
        details["g1"][p] = {"total": total, "per_file": per_file}
        if total < min_count:
            findings.append(
                f"G1 probe {p!r}: matched evidence {total} < {min_count} "
                f"-> INDETERMINATE (dead matcher vs clean is unresolvable)")

    # G2 negative control on live corpus.
    neg_total, _ = count_matches(haystacks, neg)
    details["g2"] = {"total": neg_total}
    if neg_total != 0:
        findings.append(f"G2 negative control {neg!r}: {neg_total} hits on live corpus (expected 0)")

    # G3 matcher-alive canary: seed neg into a copy of the first haystack.
    seeded = [dict(h, text=h["text"] + "\n" + neg + "\n") for h in haystacks]
    seed_total, _ = count_matches(seeded, neg)
    details["g3"] = {"seeded_hits": seed_total}
    if seed_total < 1:
        findings.append(f"G3 matcher-alive canary FAILED: seeded {neg!r} not detected")

    ok = not findings
    return ok, findings, details


def selftest():
    """Red-first battery: dead-matcher, contaminated-neg, canary-dead, vacuity, clean."""
    fails = []
    with tempfile.TemporaryDirectory() as td:
        def mk(name, text):
            p = os.path.join(td, name)
            with open(p, "w") as f:
                f.write(text * 4)  # exceed vacuity floor
            return p

        # Positive control: probes match, neg absent -> CLEAN.
        p_ok = mk("ok.txt", "alpha evidence present here\n")
        ok, fnd, _ = run_gate(["alpha"], "omega", load_haystacks([p_ok]))
        if not ok:
            fails.append(f"positive control should be CLEAN: {fnd}")

        # RED 1: dead matcher — probe matches nothing -> INDETERMINATE-as-RED, not CLEAN.
        ok, fnd, _ = run_gate(["missingterm"], "omega", load_haystacks([p_ok]))
        if ok or not any("G1" in f for f in fnd):
            fails.append("dead-matcher RED not booked")

        # RED 2: neg actually present in live corpus.
        p_bad = mk("bad.txt", "the omega taint is here\n")
        ok, fnd, _ = run_gate(["taint"], "omega", load_haystacks([p_bad]))
        if ok or not any("G2" in f for f in fnd):
            fails.append("contaminated-neg RED not booked")

        # RED 3: canary dead (patch the module-global matcher so nothing ever matches).
        orig = count_matches
        globals()["count_matches"] = lambda hs, t: (0, {})
        try:
            ok, fnd, _ = run_gate(["alpha"], "omega", load_haystacks([p_ok]))
        finally:
            globals()["count_matches"] = orig
        if ok or not any("G3" in f for f in fnd):
            fails.append("matcher-alive canary RED not booked")

        # RED 4: vacuity — tiny corpus fails loud (raises).
        tiny = os.path.join(td, "tiny.txt")
        with open(tiny, "w") as f:
            f.write("x")
        try:
            load_haystacks([tiny])
            fails.append("vacuity corpus did not fail loud")
        except SystemExit:
            pass

        # min_count sensitivity: 4 real matches < bar 5 books RED.
        ok, fnd, _ = run_gate(["alpha"], "omega", load_haystacks([p_ok]), min_count=5)
        if ok:
            fails.append("min_count bar not enforced")

    if fails:
        for f in fails:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        sys.exit(1)
    print("SELFTEST PASS (5 checks: clean, dead-matcher, contaminated-neg, canary-dead, vacuity+min_count)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probes", help="comma-separated probe terms; each MUST match (G1)")
    ap.add_argument("--neg", help="negative-control term; must be absent live, detected seeded (G2/G3)")
    ap.add_argument("--haystack", action="append", required=False, help="corpus file (repeatable)")
    ap.add_argument("--min-count", type=int, default=1)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if not (args.probes and args.neg and args.haystack):
        ap.error("--probes, --neg and at least one --haystack are required (or --selftest)")

    try:
        haystacks = load_haystacks(args.haystack)
    except SystemExit as e:
        receipt = {"verdict": "FAIL-INPUT", "why": str(e)}
        if args.out:
            with open(args.out, "w") as f:
                json.dump(receipt, f, indent=2)
        print(str(e), file=sys.stderr)
        sys.exit(2)

    probes = [p.strip() for p in args.probes.split(",") if p.strip()]
    ok, findings, details = run_gate(probes, args.neg, haystacks, args.min_count)

    receipt = {
        "verdict": "CLEAN" if ok else "RED",
        "probes": probes,
        "neg": args.neg,
        "min_count": args.min_count,
        "haystacks": [{"path": h["path"], "sha256": h["sha256"]} for h in haystacks],
        "findings": findings,
        "details": details,
        "note": "match-presence doctrine: zero matched evidence = INDETERMINATE, booked as RED (MUA-1 pattern)",
    }
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)

    print(json.dumps({"verdict": receipt["verdict"],
                      "probe_counts": {p: d["total"] for p, d in details["g1"].items()},
                      "findings": findings}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
