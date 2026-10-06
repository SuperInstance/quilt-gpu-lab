#!/usr/bin/env python3
"""verdict-cite-check — verdict-citation consistency gate (stdlib-only).

Pattern lifted PROVEN from SCOUT-57 / DC-1, booked 2026-10-06: a script's
docstring cited a REVERSED verdict against the results receipt (docstring said
"KILL_k_eff_is_k_eff_seff", the receipt booked "KILL_k_eff_is_p_local") and the
contradiction sat in a committed file until a sweep caught it. "The receipt is
the record" needs a mechanized check: any file that CITES a receipt's verdict
must cite it consistently.

What it does:
  - scans text files (py/md/txt) for lines citing `results/<name>.json`
  - on the same line or +-CONTEXT lines, finds a verdict CLAIM:
    KEEP*, KILL*, PASS, FAIL (token + optional suffix, e.g. KILL_k_eff_is_p_local)
  - loads the receipt, reads its `verdict` field
  - books RED when the claimed family contradicts the receipt family
    (KILL vs KEEP vs PASS vs FAIL), or when a suffixed claim
    (KILL_x) does not prefix-match the receipt verdict
  - MISSING receipt books MISSING (advisory, not RED — deletion is not
    contradiction; archive-by-rename is house law)
  - clean file -> CLEAN

Exit: 0 = CLEAN, 1 = RED (at least one contradiction), 2 = fail-loud input.
Read-only. Never mutates or deletes anything.

Usage:
  python tools/verdict_cite_check.py --file experiments/foo.py [--context 2] [--out r.json]
  python tools/verdict_cite_check.py --files experiments/ tools/ --glob "*.py"
  python tools/verdict_cite_check.py --selftest

Worked example (run from repo root):
  python tools/verdict_cite_check.py --file experiments/d12w_keff_seff_collapse.py
"""

import argparse
import json
import os
import re
import sys
import tempfile

CONTEXT = 2
FAMILIES = ("KILL", "KEEP", "PASS", "FAIL")
CITE_RE = re.compile(r"results/[\w./\-]+\.json")
# verdict claim: family token, optionally with _suffix words (no spaces)
CLAIM_RE = re.compile(
    r"\b((?:KILL|KEEP|PASS|FAIL)(?:_[a-z0-9_]+)?)\b"
)


def family(token):
    for fam in FAMILIES:
        if token == fam or token.startswith(fam + "_"):
            return fam
    return None


def consistent(claim, receipt_verdict):
    """claim: 'KILL_x' or 'KILL'; receipt_verdict: e.g. 'KILL_k_eff_is_p_local'."""
    cf, rf = family(claim), family(receipt_verdict)
    if cf is None or rf is None:
        return False
    if cf != rf:
        return False
    # suffixed claim must prefix-match the receipt verdict exactly
    if claim != cf and not receipt_verdict.startswith(claim):
        return False
    return True


QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'|`[^`]*`')


def strip_quotes(s):
    """Remove quoted spans ("...", '...', `...`) — quoted verdicts are prose
    ABOUT claims (amendment notes citing the old false verdict), not claims."""
    return QUOTED_RE.sub(' ', s)


IFF_RE = re.compile(
    r"\b(KILL|KEEP|PASS|FAIL)(?:_[a-z0-9_]+)?\s+iff\b|\belse\s+(KILL|KEEP|PASS|FAIL)(?:_[a-z0-9_]+)?\b",
    re.I)


def strip_iff(s):
    """Remove 'VERDICT iff ...' / 'else VERDICT' gate-definition arms — they
    define the criterion, they do not claim the receipt booked that verdict."""
    return IFF_RE.sub(" ", s)


def claims_near(lines, idx, context=CONTEXT):
    """Verdict claims on line idx or within +-context lines (quoted spans and
    'VERDICT iff' gate definitions stripped)."""
    out = []
    for j in range(max(0, idx - context), min(len(lines), idx + context + 1)):
        for m in CLAIM_RE.finditer(strip_iff(strip_quotes(lines[j]))):
            tok = m.group(1)
            out.append((j, tok))
    return out


def check_file(path, context=CONTEXT, root="."):
    """Returns list of findings: dicts {cite, line, claim, verdict, status}."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    findings = []
    for i, line in enumerate(lines):
        for cm in CITE_RE.finditer(line):
            cite = cm.group(0)
            rpath = os.path.join(root, cite)
            for j, tok in claims_near(lines, i, context):
                if family(tok) is None:
                    continue
                # ignore claims that are merely names of variables like KILLED
                if not os.path.exists(rpath):
                    findings.append({"file": path, "line": i + 1, "cite": cite,
                                     "claim": tok, "verdict": None,
                                     "status": "MISSING"})
                    continue
                try:
                    with open(rpath, "r", encoding="utf-8") as rf:
                        receipt = json.load(rf)
                except (json.JSONDecodeError, OSError):
                    findings.append({"file": path, "line": i + 1, "cite": cite,
                                     "claim": tok, "verdict": None,
                                     "status": "MISSING"})
                    continue
                verdict = receipt.get("verdict") if isinstance(receipt, dict) else None
                if not isinstance(verdict, str):
                    findings.append({"file": path, "line": i + 1, "cite": cite,
                                     "claim": tok, "verdict": None,
                                     "status": "MISSING"})
                    continue
                ok = consistent(tok, verdict)
                findings.append({"file": path, "line": i + 1, "cite": cite,
                                 "claim": tok, "verdict": verdict,
                                 "status": "CLEAN" if ok else "RED"})
    return findings


def selftest():
    """FAIL-FIRST pins: consistent citation, reversed citation (RED),
    missing receipt (MISSING, advisory), suffixed-claim mismatch."""
    checks = []
    tmp = tempfile.mkdtemp(prefix="vcc_selftest_")
    res = os.path.join(tmp, "results")
    os.makedirs(res)

    def w(name, obj):
        p = os.path.join(res, name)
        with open(p, "w") as f:
            json.dump(obj, f)
        return "results/" + name

    # 1. consistent KEEP citation -> CLEAN
    c1 = w("a.json", {"verdict": "KEEP"})
    src1 = os.path.join(tmp, "s1.py")
    with open(src1, "w") as f:
        f.write(f"# booked {c1}: KEEP\n")
    f1 = check_file(src1, root=tmp)
    checks.append(("consistent-KEEP", len(f1) == 1 and f1[0]["status"] == "CLEAN"))

    # 2. reversed citation -> RED (the SCOUT-57 class)
    c2 = w("b.json", {"verdict": "KILL_k_eff_is_p_local"})
    src2 = os.path.join(tmp, "s2.py")
    with open(src2, "w") as f:
        f.write(f"# booked {c2}: KILL_k_eff_is_k_eff_seff\n")
    f2 = check_file(src2, root=tmp)
    checks.append(("reversed-RED", len(f2) == 1 and f2[0]["status"] == "RED"))

    # 3. missing receipt -> MISSING, advisory
    src3 = os.path.join(tmp, "s3.py")
    with open(src3, "w") as f:
        f.write("# see results/gone.json for the KEEP\n")
    f3 = check_file(src3, root=tmp)
    checks.append(("missing-advisory", len(f3) == 1 and f3[0]["status"] == "MISSING"))

    # 4. right family, wrong suffix -> RED
    c4 = w("d.json", {"verdict": "KILL_alpha_mismatch"})
    src4 = os.path.join(tmp, "s4.py")
    with open(src4, "w") as f:
        f.write(f"# booked {c4}: KILL_coverage\n")
    f4 = check_file(src4, root=tmp)
    checks.append(("suffix-mismatch-RED", len(f4) == 1 and f4[0]["status"] == "RED"))

    # 5b. quoted claim (prose ABOUT a false verdict) must NOT book RED
    src5b = os.path.join(tmp, "s5b.py")
    with open(src5b, "w") as f:
        f.write(f"AMENDED: asserted REVERSED (\"verdict KEEP\") for\n"
                f"the result ({c4}); truth is KILL.\n")
    f5b = check_file(src5b, root=tmp)
    checks.append(("quoted-claim-not-RED",
                   not any(x["status"] == "RED" for x in f5b)))

    # 5c. receipt has no verdict -> MISSING advisory
    c5 = w("e.json", {"tool": "x"})
    src5 = os.path.join(tmp, "s5.py")
    with open(src5, "w") as f:
        f.write(f"# {c5} KEEP\n")
    f5 = check_file(src5, root=tmp)
    checks.append(("no-verdict-MISSING", len(f5) == 1 and f5[0]["status"] == "MISSING"))

    # 5d. 'KEEP iff ...' / 'else FAIL' gate definitions are criteria, not claims
    src5d = os.path.join(tmp, "s5d.py")
    with open(src5d, "w") as f:
        f.write(f"Gate: KEEP iff A-B >= 0.05.\n"
                f"verdict: PASS iff X > Y, else FAIL.\n"
                f"Receipt: {c4}.\n")
    f5d = check_file(src5d, root=tmp)
    checks.append(("iff-gate-not-RED",
                   not any(x["status"] == "RED" for x in f5d)))

    # leak check: temp paths never contain a token-looking secret; trivial here
    # but assert checks list shape
    ok = all(name for name, passed in checks) and all(passed for _, passed in checks)
    print(json.dumps({"selftest": "PASS" if ok else "FAIL",
                      "checks": [{"name": n, "ok": p} for n, p in checks]}))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="verdict-citation consistency gate")
    ap.add_argument("--file", help="single file to check")
    ap.add_argument("--files", nargs="*", help="dirs to sweep (with --glob)")
    ap.add_argument("--glob", default="*.py", help="glob for --files sweep")
    ap.add_argument("--context", type=int, default=CONTEXT)
    ap.add_argument("--root", default=".", help="root for results/ paths")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    targets = []
    if args.file:
        targets = [args.file]
    elif args.files:
        import glob as g
        for d in args.files:
            targets.extend(sorted(g.glob(os.path.join(d, args.glob))))
    else:
        ap.error("need --file, --files, or --selftest")
    if not targets:
        print(json.dumps({"error": "no target files"}))
        sys.exit(2)

    allf = []
    for t in targets:
        if not os.path.isfile(t):
            print(json.dumps({"error": f"not a file: {t}"}))
            sys.exit(2)
        allf.extend(check_file(t, context=args.context, root=args.root))

    reds = [f for f in allf if f["status"] == "RED"]
    receipt = {"tool": "verdict-cite-check", "files": len(targets),
               "citations": len(allf), "red": len(reds),
               "missing": sum(1 for f in allf if f["status"] == "MISSING"),
               "verdict": "RED" if reds else "CLEAN",
               "findings": allf}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
        receipt["out"] = args.out
    print(json.dumps({k: receipt[k] for k in
                      ("tool", "files", "citations", "red", "missing", "verdict")}))
    for f in reds:
        print(f"RED {f['file']}:{f['line']} claims {f['claim']} "
              f"but {f['cite']} booked {f['verdict']}")
    sys.exit(1 if reds else 0)


if __name__ == "__main__":
    main()
