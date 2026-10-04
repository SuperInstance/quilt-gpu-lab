#!/usr/bin/env python3
"""calib_gate — proper-scoring calibration battery for a probabilistic
classifier (pattern lifted from ST3-calibrated-noul / QC-JEV doctrine).

Given a list of (p, y) predictions — p = model probability of class 1,
y = true 0/1 label — computes and books:

  * ECE      expected calibration error, 10 equal-width bins (reliability)
  * Brier    mean squared error of p vs y (proper score)
  * accuracy at 0.5 threshold
  * AURC     area under the risk-coverage curve (selective prediction:
             rank by confidence, mean error over coverage prefixes);
             lower is better, perfect predictor -> 0
  * E-AURC   AURC minus oracle AURC (excess over the ideal selective
             model — the honest difficulty-adjusted number)

Optional gate: PASS only if ECE <= --ece-bar (default 0.05) AND Brier
<= --brier-bar (default 0.25). Verdicts KEEP / FAIL / VOID and exit
codes 0 / 1 / 2 (fail-loud input) follow the lab receipt doctrine.

Stdlib-only, seeded/deterministic, fail-loud on p outside [0,1],
labels not in {0,1}, or empty input. One JSON receipt (--out).

Worked example
--------------
  $ python tools/calib_gate.py --preds '[{"p":0.9,"y":1},{"p":0.1,"y":0},
      {"p":0.8,"y":1},{"p":0.3,"y":0},{"p":0.7,"y":1}]' --out r.json
  -> 5 items, accuracy 1.0 but ECE 0.2 (conf 0.7-0.9 at perfect accuracy
     is honestly underconfident-overclaim) -> FAIL rc=1. Bars are gates;
     small honest samples fail them. Use real-sized prediction lists.

Selftest runs a hermetic battery: calibrated clean control (KEEP),
overconfident decoy (FAIL), and fail-loud pins (p>1, bad label, empty).

Usage
-----
  python tools/calib_gate.py --preds file.json | --preds-json '...' |
         --selftest [--ece-bar 0.05] [--brier-bar 0.25] [--out r.json]
"""
import argparse
import json
import sys

BINS = 10


def fail_loud(msg):
    print(json.dumps({"verdict": "FAIL-INPUT", "error": msg}))
    sys.exit(2)


def ece_binned(preds, n_bins=BINS):
    conf = [max(p, 1 - p) for p, _ in preds]
    corr = [1 if (p >= 0.5) == (y == 1) else 0 for p, y in preds]
    total = len(preds)
    e = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [i for i in range(total) if (b == 0 and lo <= conf[i] <= hi)
               or (lo < conf[i] <= hi)]
        if not idx:
            continue
        e += (len(idx) / total) * abs(sum(conf[i] for i in idx) / len(idx)
                                     - sum(corr[i] for i in idx) / len(idx))
    return e


def risk_coverage(preds):
    """rank by confidence desc, cumulative risk at each prefix; returns
    (aurc, eaurc)."""
    order = sorted(range(len(preds)),
                   key=lambda i: -max(preds[i][0], 1 - preds[i][0]))
    errs = [0 if (preds[i][0] >= 0.5) == (preds[i][1] == 1) else 1
            for i in order]
    n = len(preds)
    cume, risk_sum, risks = 0, 0.0, []
    for k, e in enumerate(errs, 1):
        cume += e
        r = cume / k
        risks.append(r)
        risk_sum += r
    aurc = risk_sum / n
    # oracle: sort by actual error (correct first)
    oe = sorted(errs)
    oc, orisk_sum = 0, 0.0
    for k, e in enumerate(oe, 1):
        oc += e
        orisk_sum += oc / k
    return aurc, aurc - orisk_sum / n


def run(preds):
    if not preds:
        fail_loud("empty prediction list")
    for i, it in enumerate(preds):
        p, y = it.get("p"), it.get("y")
        if not isinstance(p, (int, float)) or not (0.0 <= p <= 1.0):
            fail_loud(f"item {i}: p={p!r} not a probability in [0,1]")
        if y not in (0, 1):
            fail_loud(f"item {i}: y={y!r} not in {{0,1}}")
    p = [(it["p"], it["y"]) for it in preds]
    n = len(p)
    pos = sum(y for _, y in p)
    acc = sum(1 for pp, y in p if (pp >= 0.5) == (y == 1)) / n
    brier = sum((pp - y) ** 2 for pp, y in p) / n
    aurc, eaurc = risk_coverage(p)
    return {
        "n": n,
        "base_rate": round(pos / n, 6),
        "accuracy@0.5": round(acc, 6),
        "ece": round(ece_binned(p), 6),
        "brier": round(brier, 6),
        "aurc": round(aurc, 6),
        "eaurc": round(eaurc, 6),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--preds", help="JSON file: list of {p, y}")
    ap.add_argument("--preds-json", help="inline JSON list of {p, y}")
    ap.add_argument("--ece-bar", type=float, default=0.05)
    ap.add_argument("--brier-bar", type=float, default=0.25)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest(a.out))

    if a.preds_json:
        raw = a.preds_json
    elif a.preds:
        with open(a.preds) as f:
            raw = f.read()
    else:
        fail_loud("need --preds FILE or --preds-json '...' (or --selftest)")
    try:
        preds = json.loads(raw)
    except json.JSONDecodeError as e:
        fail_loud(f"bad JSON: {e}")
    if not isinstance(preds, list):
        fail_loud("predictions must be a JSON list of {p, y}")

    out = run(preds)
    out["ece_bar"], out["brier_bar"] = a.ece_bar, a.brier_bar
    if out["ece"] <= a.ece_bar and out["brier"] <= a.brier_bar:
        out["verdict"] = "KEEP"
        rc = 0
    else:
        out["verdict"] = "FAIL"
        rc = 1
    print(json.dumps(out, indent=2))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
    sys.exit(rc)


def selftest(out_path=None):
    checks = []
    # 1. clean control: confidences that MATCH bin accuracy (0.9 correct at
    # conf 0.9, 0.7 correct at conf 0.7) -> ECE ~ 0, Brier small -> KEEP
    import random
    rng = random.Random(3)
    good = []
    for conf in (0.9, 0.7):
        for _ in range(50):
            y = 1 if rng.random() < conf else 0
            good.append({"p": conf, "y": y})
    r = run(good)
    ok = r["ece"] <= 0.05 and r["brier"] <= 0.25 and r["aurc"] < 0.3
    checks.append(("clean-KEEP", ok, r))
    # 2. overconfident decoy: says 0.99 when 50/50 -> FAIL (high ECE+Brier)
    import random
    rng = random.Random(7)
    bad = [{"p": 0.99 if rng.random() < 0.5 else 0.01,
            "y": 1 if rng.random() < 0.5 else 0} for _ in range(200)]
    r = run(bad)
    checks.append(("overconfident-FAIL",
                   r["ece"] > 0.05 or r["brier"] > 0.25, r))
    # 3-5. fail-loud pins
    for name, items in [("p>1", [{"p": 1.5, "y": 1}]),
                        ("bad-label", [{"p": 0.5, "y": 2}]),
                        ("empty", [])]:
        try:
            run(items)
            checks.append((name, False, {}))
        except SystemExit as e:
            checks.append((name, e.code == 2, {}))
    receipt = {"selftest": "calib_gate",
               "results": [{"check": n, "ok": ok} for n, ok, _ in checks],
               "pass": all(ok for _, ok, _ in checks)}
    for n, ok, r in checks:
        print(f"  {n}: {'OK' if ok else 'MISMATCH'} {json.dumps(r) if r else ''}")
    print(json.dumps(receipt))
    if out_path:
        with open(out_path, "w") as f:
            json.dump(receipt, f, indent=2)
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    main()
