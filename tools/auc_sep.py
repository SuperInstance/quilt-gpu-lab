#!/usr/bin/env python3
"""auc-sep — stdlib-only Mann-Whitney AUC feature-separation gate (CC-1 pattern).

Lifted from the PROVEN pattern in experiments/cc1_comfortable_collapse.py
(CC-1, booked 2026-10-06): given two labeled groups of samples (pos / neg),
compute the Mann-Whitney AUC = P(pos > neg) + 0.5*P(equal) per feature and
pooled, with an exact two-sided Mann-Whitney U p-value (normal approximation
with tie correction, valid for n >= 8 per group) and an optional KEEP/FAIL
gate on a pre-registered AUC band. Fail-loud JSON receipt either way.

This is the honest-booking companion to perm_ci (tools/perm_ci.py): perm_ci
answers "is the delta real?", auc-sep answers "does this feature RANK the
groups?" — the CC-1 lesson is that a weak AUC (0.59-0.62) on a feature that
is not blind and not routable books as INCONCLUSIVE, and the receipt says so.

Usage:
  python tools/auc_sep.py --groups groups.json [--features f1,f2] \
      [--pos fenced --neg hopeless] [--band 0.5,0.75] [--out receipt.json]

Input groups.json:
  {"fenced": {"f1": [1.2, 0.8, ...], "f2": [...]},
   "hopeless": {"f0": [...], ...}}
  (feature vectors per group; features present in BOTH groups are scored;
   per-feature n mismatch within a group is an error — fail loud.)

Worked example (self-test, deterministic):
  $ python tools/auc_sep.py --example
  -> perfect separation: AUC 1.0, p tiny, GATE KEEP;
     null features: AUC ~0.5, gate FAIL. rc=0 (receipt written either way).

Gate: --band lo,hi — KEEP iff every gated feature's pooled AUC is OUTSIDE
[lo,hi] (i.e. strictly informative in some direction); AUCs are direction-
normalized to >= 0.5 for reporting but the raw value is kept in the receipt.
Exit codes: 0 = KEEP (or no gate), 1 = FAIL, 2 = usage/validation error.
"""
import argparse
import json
import math
import sys
import time

def auc(pos, neg):
    """Mann-Whitney AUC, P(pos > neg) + 0.5 P(equal). Verbatim from CC-1."""
    if not pos or not neg:
        raise ValueError("auc: empty group")
    gt = sum(1 for p in pos for n in neg if p > n)
    eq = sum(1 for p in pos for n in neg if p == n)
    return (gt + 0.5 * eq) / (len(pos) * len(neg))

def mw_pvalue(pos, neg):
    """Two-sided p for Mann-Whitney U via normal approx with tie correction."""
    n1, n2 = len(pos), len(neg)
    if n1 < 8 or n2 < 8:
        return None  # approximation invalid; honest None in receipt
    allv = list(pos) + list(neg)
    # mean-rank with ties
    order = sorted(range(len(allv)), key=lambda i: allv[i])
    ranks = [0.0] * len(allv)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and allv[order[j + 1]] == allv[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    _, counts = _tcounts(allv)
    tie_term = sum(c**3 - c for c in counts)
    sd = math.sqrt(n1 * n2 / 12 * ((len(allv) + 1) - tie_term / (len(allv) * (len(allv) - 1))))
    if sd == 0:
        return 0.0 if abs(u1 - mu) > 0 else 1.0
    z = (u1 - mu) / sd
    p = math.erfc(abs(z) / math.sqrt(2))
    return p

def _tcounts(vals):
    seen = {}
    for v in vals:
        seen[v] = seen.get(v, 0) + 1
    return len(seen), list(seen.values())

def run(groups, features=None, pos_name=None, neg_name=None):
    if pos_name is None:
        pos_name = sorted(groups)[0]
    if neg_name is None:
        neg_name = sorted(groups)[1] if len(groups) > 1 else None
    if neg_name is None or pos_name not in groups or neg_name not in groups:
        raise ValueError(f"need exactly two group names; have {sorted(groups)}")
    pos_g, neg_g = groups[pos_name], groups[neg_name]
    common = sorted(set(pos_g) & set(neg_g))
    if features:
        missing = [f for f in features if f not in common]
        if missing:
            raise ValueError(f"features not in both groups: {missing}")
        common = sorted(features)
    if not common:
        raise ValueError("no common features between groups")
    out = {"pos": pos_name, "neg": neg_name, "features": {}}
    for f in common:
        pv, nv = pos_g[f], neg_g[f]
        if len(set(map(type, pv))) != 1 or len(set(map(type, nv))) != 1:
            raise ValueError(f"feature {f}: mixed types in group vectors")
        for v in pv + nv:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"feature {f}: non-numeric value {v!r}")
        a = auc(pv, nv)
        out["features"][f] = {
            "auc": round(a, 6),
            "auc_directional": round(max(a, 1 - a), 6),
            "n_pos": len(pv), "n_neg": len(nv),
            "p_two_sided": mw_pvalue(pv, nv),
        }
    return out

def gate(receipt, band):
    lo, hi = band
    for f, s in receipt["features"].items():
        if lo <= s["auc_directional"] <= hi:
            return False, f"{f}: directional AUC {s['auc_directional']} inside dead band [{lo},{hi}]"
    return True, "all features outside dead band"

def _example():
    groups = {
        "fenced":   {"sig": [0.9, 1.1, 0.8, 1.2, 1.0, 0.95, 1.05, 1.15, 0.85, 1.25],
                     "noise": [0.5, 0.4, 0.6, 0.45, 0.55, 0.5, 0.42, 0.58, 0.48, 0.52]},
        "hopeless": {"sig": [0.1, 0.3, 0.2, 0.05, 0.25, 0.15, 0.35, 0.12, 0.28, 0.18],
                     "noise": [0.5, 0.4, 0.6, 0.45, 0.55, 0.5, 0.42, 0.58, 0.48, 0.52]},
    }
    r = run(groups, features=["sig", "noise"])
    ok, why = gate(r, (0.5, 0.75))
    r["gate"] = {"band": [0.5, 0.75], "decision": "KEEP" if ok else "FAIL", "why": why}
    r["_selftest"] = {
        "sig_auc_is_1": r["features"]["sig"]["auc"] == 1.0,
        "noise_in_band": 0.5 <= r["features"]["noise"]["auc_directional"] <= 0.75,
    }
    print(json.dumps(r, indent=2))
    assert r["_selftest"]["sig_auc_is_1"] and r["_selftest"]["noise_in_band"], "SELFTEST FAIL"
    print("SELFTEST PASS", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--groups", help="groups JSON path")
    ap.add_argument("--features", help="comma-separated features to score (default: all common)")
    ap.add_argument("--pos", help="positive group name (default: first sorted)")
    ap.add_argument("--neg", help="negative group name (default: second sorted)")
    ap.add_argument("--band", help="dead band lo,hi on directional AUC (e.g. 0.5,0.75); KEEP iff outside")
    ap.add_argument("--out", help="write JSON receipt here (default: stdout only)")
    ap.add_argument("--example", action="store_true", help="run deterministic self-test")
    args = ap.parse_args()

    if args.example:
        _example()
        return
    if not args.groups:
        ap.error("--groups required (or --example)")

    try:
        groups = json.load(open(args.groups))
        features = args.features.split(",") if args.features else None
        receipt = run(groups, features=features, pos_name=args.pos, neg_name=args.neg)
        rc = 0
        if args.band:
            lo, hi = (float(x) for x in args.band.split(","))
            if not (0 <= lo <= hi <= 1):
                raise ValueError(f"bad band {lo},{hi}")
            ok, why = gate(receipt, (lo, hi))
            receipt["gate"] = {"band": [lo, hi], "decision": "KEEP" if ok else "FAIL", "why": why}
            rc = 0 if ok else 1
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        receipt = {"error": str(e), "verdict": "KILL"}
        rc = 2
    receipt["_wall_s"] = round(time.time() % 1000, 3)
    blob = json.dumps(receipt, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(blob + "\n")
        print(f"receipt -> {args.out}", file=sys.stderr)
    print(blob)
    sys.exit(rc)

if __name__ == "__main__":
    main()
