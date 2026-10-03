#!/usr/bin/env python3
"""ensemble-corr-census — rerun-ensemble correlation census (stdlib-only).

Lifted from the PROVEN QG7b pattern (experiments/qg7b_rerun_correlation.py,
booked 2026-10-03 INTERMEDIATE rho 0.787): given per-run score vectors from R
reruns of the *same* computation (plus optional per-run subpopulation masks and
binary labels), compute the mean pairwise Spearman rho on the mask intersection
(primary), label agreement vs run0 on run0's mask (secondary), and book one of
three pre-reg verdict bands:

  rho > hi (default 0.9)  -> ENSEMBLE ~ 1-2 DRAWS  (reruns are intra-computation
                             noise, NOT judge diversity; divide by R at your peril)
  rho < lo (default 0.5)  -> CORRELATED-JUDGE TRANSFER REFUTED (reruns are
                             effectively independent draws)
  else                    -> INTERMEDIATE (no verdict-language change)

The question it answers: "my headline number was the best-of-R ensemble — how
many *effective* draws do I actually have?" Any lane reporting ensemble results
should run this census before quoting R-fold robustness.

Input JSON:
{
  "runs": [
    {"scores": [0.71, 0.43, ...],            # per-stream scores, run r
     "mask":   [1, 0, 1, ...],               # OPTIONAL 0/1 subpop mask
     "labels": [1, 0, 0, ...]},              # OPTIONAL binary labels (run order)
    ...
  ],
  "hi": 0.9, "lo": 0.5                       # OPTIONAL band overrides
}
Ragged runs are fine: pairs compare on the intersection of masks (or full
overlap when no masks). Non-finite scores fail loud (rc=2).

Usage:
  python tools/ensemble_corr_census.py --runs runs.json [--out receipt.json]
  python tools/ensemble_corr_census.py --selftest

Exit codes: 0 ok (verdict in receipt), 1 degenerate (<2 runs or empty
intersection in every pair), 2 validation error.

Worked example:
  $ cat > /tmp/ec.json <<'EOF'
  {"runs": [
    {"scores": [0.1, 0.9, 0.4, 0.8, 0.3], "mask": [1,1,1,1,0], "labels": [1,0,1,0,1]},
    {"scores": [0.2, 0.8, 0.3, 0.7, 0.4], "mask": [1,1,1,0,1], "labels": [1,0,1,0,0]},
    {"scores": [0.1, 0.7, 0.5, 0.9, 0.2], "mask": [1,0,1,1,1], "labels": [1,0,0,1,1]}]}
  EOF
  $ python tools/ensemble_corr_census.py --runs /tmp/ec.json
"""
import argparse
import json
import math
import sys


def fail(msg, code=2):
    print(f"FAIL({code}): {msg}", file=sys.stderr)
    sys.exit(code)


def _avg_ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0  # average 1-based rank for ties
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def _pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    num = sum(x * y for x, y in zip(da, db))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    return num / den if den > 0 else None


def spearman(a, b):
    """Spearman rho via average ranks + Pearson (ties handled)."""
    ra = _avg_ranks(a)
    rb = _avg_ranks(b)
    return _pearson(ra, rb)


def census(runs, hi=0.9, lo=0.5):
    R = len(runs)
    if R < 2:
        fail("need >=2 runs", 1)
    for r, run in enumerate(runs):
        if not run["scores"] or any(not math.isfinite(x) for x in run["scores"]):
            fail(f"run {r}: empty or non-finite score")
        if "mask" in run and len(run["mask"]) != len(run["scores"]):
            fail(f"run {r}: mask length != scores length")
        if "labels" in run and len(run["labels"]) != len(run["scores"]):
            fail(f"run {r}: labels length != scores length")

    masks = [[bool(m) for m in run.get("mask", [1] * len(run["scores"]))] for run in runs]
    rhos, pair_ns = [], []
    for i in range(R):
        for j in range(i + 1, R):
            both = [a and b for a, b in zip(masks[i], masks[j])]
            n = sum(both)
            if n < 3:
                continue
            si = [s for s, b in zip(runs[i]["scores"], both) if b]
            sj = [s for s, b in zip(runs[j]["scores"], both) if b]
            rho = spearman(si, sj)
            if rho is None:
                fail(f"pair ({i},{j}): degenerate (constant scores on intersection n={n})", 1)
            rhos.append(rho)
            pair_ns.append(n)
    if not rhos:
        fail("no pair with intersection >= 3 streams", 1)
    rho_mean = sum(rhos) / len(rhos)

    # secondary: label agreement vs run0 on run0's mask, ragged subpops
    agree = []
    if all("labels" in run for run in runs):
        pos = [None] * len(runs[0]["scores"])
        c = 0
        for k, m in enumerate(masks[0]):
            if m:
                pos[k] = c
                c += 1
        for j in range(1, R):
            both = [a and b for a, b in zip(masks[0], masks[j])]
            cj = 0
            hits = tot = 0
            for k, b in enumerate(both):
                if not b:
                    continue
                l0 = runs[0]["labels"][pos[k]]
                lj = runs[j]["labels"][cj]
                cj += 1
                hits += l0 == lj
                tot += 1
            agree.append(hits / tot if tot else None)
        agree = [a for a in agree if a is not None]
    label_agree = sum(agree) / len(agree) if agree else None

    if rho_mean > hi:
        verdict = (f"ENSEMBLE~1-2-DRAWS: mean pairwise Spearman {rho_mean:.4f} > {hi} — "
                   "the R-fold ensemble is ~1-2 effective draws; spread is intra-computation "
                   "noise, not judge diversity.")
    elif rho_mean < lo:
        verdict = (f"CORRELATED-JUDGE TRANSFER REFUTED: mean pairwise Spearman {rho_mean:.4f} < {lo} — "
                   "reruns are effectively independent draws.")
    else:
        verdict = f"INTERMEDIATE: mean pairwise Spearman {rho_mean:.4f} in [{lo},{hi}] — no verdict-language change."

    return {
        "n_runs": R,
        "pairwise_spearman": rhos,
        "pair_intersection_n": pair_ns,
        "spearman_mean": rho_mean,
        "spearman_min": min(rhos),
        "spearman_max": max(rhos),
        "label_agreement_vs_run0": label_agree,
        "bands": {"hi": hi, "lo": lo},
        "verdict": verdict,
    }


def selftest():
    ok = [0]

    def check(name, cond):
        if not cond:
            fail(f"selftest {name}")
        ok[0] += 1

    # exact spearman sanity: perfect monotone, anti-monotone, ties
    check("mono", abs(spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-12)
    check("anti", abs(spearman([1, 2, 3, 4], [40, 30, 20, 10]) + 1.0) < 1e-12)
    check("ties", abs(spearman([1, 1, 2, 3], [5, 7, 6, 9]) - 0.6324555320336759) < 1e-12)

    # no-mask path
    runs = [{"scores": [0.1, 0.9, 0.4]}, {"scores": [0.2, 0.8, 0.3]},
            {"scores": [0.0, 1.0, 0.5]}]
    r = census(runs)
    check("nomask-high", r["spearman_mean"] > 0.99 and "DRAWS" in r["verdict"])

    # noisy path -> independent-ish
    runs2 = [{"scores": [0.1, 0.9, 0.4, 0.8, 0.3]}, {"scores": [0.9, 0.1, 0.8, 0.3, 0.6]}]
    r2 = census(runs2)
    check("anti", r2["spearman_mean"] < 0.0 and "REFUTED" in r2["verdict"])

    # mask intersection
    runs3 = [{"scores": [1, 2, 3, 4], "mask": [1, 1, 1, 0]},
             {"scores": [10, 20, 30, 99], "mask": [1, 1, 1, 1]}]
    r3 = census(runs3)
    check("mask-int", abs(r3["spearman_mean"] - 1.0) < 1e-12
          and r3["pair_intersection_n"] == [3])

    # ragged labels agreement
    runs4 = [{"scores": [1, 2, 3], "labels": [1, 0, 1]},
             {"scores": [1, 2, 4], "mask": [1, 1, 1], "labels": [1, 0, 0]}]
    r4 = census(runs4)
    check("label-agree", abs(r4["label_agreement_vs_run0"] - 2 / 3) < 1e-12)

    # non-finite fails loud rc=2
    bad = [{"scores": [0.1, float("nan")]}, {"scores": [0.1, 0.2]}]
    try:
        census(bad)
        fail("selftest nan-should-fail")
    except SystemExit as e:
        check("nan-rc2", e.code == 2)

    print(f"SELFTEST OK ({ok[0]} checks)")


def main():
    ap = argparse.ArgumentParser(description="rerun-ensemble correlation census (QG7b pattern)")
    ap.add_argument("--runs", help="input JSON (see docstring)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--hi", type=float, default=0.9)
    ap.add_argument("--lo", type=float, default=0.5)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.runs:
        ap.error("--runs required (or --selftest)")
    try:
        with open(args.runs) as f:
            spec = json.load(f)
    except Exception as e:
        fail(f"cannot read {args.runs}: {e}")
    if not isinstance(spec, dict) or not isinstance(spec.get("runs"), list):
        fail("input must be {\"runs\": [...]}")
    res = census(spec["runs"], hi=args.hi, lo=args.lo)
    res["input"] = args.runs
    print(f"PRIMARY: mean pairwise Spearman {res['spearman_mean']:.4f} "
          f"(min {res['spearman_min']:.4f} max {res['spearman_max']:.4f})")
    if res["label_agreement_vs_run0"] is not None:
        print(f"SECONDARY: label agreement vs run0 {res['label_agreement_vs_run0']:.4f}")
    print(f"VERDICT: {res['verdict']}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, indent=1)
        print(f"booked {args.out}")


if __name__ == "__main__":
    main()
