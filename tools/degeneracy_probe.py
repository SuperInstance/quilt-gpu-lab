#!/usr/bin/env python3
"""degeneracy_probe — G5+G6 verdict-surface witness, lifted from DECOY-1b (BOOKED GREEN 2026-10-09).

Two structural probes for ANY scoring/metric function, from the proven DECOY-1b
amendment (proposals/runs/DECOY-1b-amendment-prereg-2026-10-09.md):

  G5 EMPTY-INPUT-DEGENERATE — feed the metric empty/degenerate inputs (empty
     list, empty string, None where callable). A metric that silently returns
     a number on empty input can let a gate pass on nothing. Fail-loud
     (raises) = PASS; silent numeric return = RED.

  G6 INVERSION-DISCRIMINATION PIN — a deliberately INVERTED labeling
     (worst-case adversarial assignment) must score strictly WORSE than true
     labels and no better than shuffled. A metric that can't tell inverted
     from true at instrument level = inversion-blind = RED.

Stdlib-only, deterministic (seeded shuffle), fail-loud JSON receipt either way.

Module API:
    from degeneracy_probe import probe, rank_auc
    receipt = probe(metric=lambda pos, neg: rank_auc(pos, neg),
                    pos=[1.2, 0.8, ...], neg=[0.1, 0.3, ...])
    # receipt["verdict"] in {"GREEN", "RED"}; never raises on probe result.

Worked example (self-test, uses the DECOY-1b witness numbers):
    python tools/degeneracy_probe.py --selftest
    # -> G5 PASS (empty raises), G6 PASS (auc_inv 0.085 < auc_true 0.915,
    #    <= shuffled+0.05): verdict GREEN

Probe a metric defined in your own module (must expose metric(pos, neg) -> float):
    python tools/degeneracy_probe.py --module mymetrics.py --fn metric \
        --pos 1.2,0.9,1.5,0.7 --neg 0.2,0.4,0.1,0.3 --out receipt.json
"""
import argparse
import importlib.util
import json
import random
import sys


def rank_auc(pos, neg):
    """Rank-statistic AUC (the DECOY-1 oracle statistic). Raises on empty input."""
    gt = sum(1 for p in pos for n in neg if p > n)
    eq = sum(1 for p in pos for n in neg if p == n)
    return (gt + 0.5 * eq) / (len(pos) * len(neg))  # ZeroDivisionError on empty = fail-loud


def _g5_empty_input(metric):
    """True = PASS (metric raises fail-loud on every degenerate input)."""
    degenerates = [
        ("empty-pos", lambda: metric([], [0.1])),
        ("empty-neg", lambda: metric([0.1], [])),
        ("both-empty", lambda: metric([], [])),
    ]
    for name, call in degenerates:
        try:
            v = call()
        except Exception:
            continue  # raising = fail-loud = good
        if isinstance(v, (int, float)):  # silent numeric on degenerate input
            return False, name, v
    return True, None, None


def _g6_inversion(metric, pos, neg, seed=20261009, tol=0.05):
    """Probe inverted-vs-true-vs-shuffled discrimination."""
    auc_true = metric(pos, neg)
    auc_inv = metric(neg, pos)  # worst-case: labels flipped
    rng = random.Random(seed)
    shufs = []
    for _ in range(16):
        m = pos + neg[:]
        rng.shuffle(m)
        shufs.append(metric(m[: len(pos)], m[len(pos):]))
    auc_shuf_mean = sum(shufs) / len(shufs)
    g6_pass = (auc_inv < auc_true) and (auc_inv <= auc_shuf_mean + tol)
    return g6_pass, {
        "auc_true": round(auc_true, 4),
        "auc_inverted": round(auc_inv, 4),
        "auc_shuffled_mean": round(auc_shuf_mean, 4),
        "tol": tol,
    }


def probe(metric, pos, neg, seed=20261009, tol=0.05):
    """Run G5+G6 on metric(pos, neg). Returns a receipt dict; verdict GREEN/RED."""
    if not pos or not neg:
        raise ValueError("pos/neg samples must be non-empty (probe inputs, not metric inputs)")
    g5_pass, g5_site, g5_val = _g5_empty_input(metric)
    g6_pass, g6_stats = _g6_inversion(metric, pos, neg, seed=seed, tol=tol)
    return {
        "tool": "degeneracy_probe",
        "G5_empty_input": "PASS" if g5_pass else "RED",
        "G5_site": g5_site,
        "G5_degenerate_value": g5_val,
        "G6_inversion": "PASS" if g6_pass else "RED",
        **g6_stats,
        "verdict": "GREEN" if (g5_pass and g6_pass) else "RED",
    }


def _load_metric(module_path, fn_name):
    spec = importlib.util.spec_from_file_location("usermetric", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, fn_name)
    if not callable(fn):
        raise TypeError(f"{module_path}:{fn_name} is not callable")
    return fn


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--module", help="python file exposing the metric function")
    ap.add_argument("--fn", default="metric", help="metric function name (default: metric)")
    ap.add_argument("--pos", help="comma-separated positive-sample scores")
    ap.add_argument("--neg", help="comma-separated negative-sample scores")
    ap.add_argument("--selftest", action="store_true", help="run built-in DECOY-1b witness")
    ap.add_argument("--out", help="write JSON receipt here")
    a = ap.parse_args()

    if a.selftest:
        # Deterministic witness reproducing the DECOY-1b G6 numbers.
        rng = random.Random(20261009)
        pos = [rng.gauss(1.0, 0.5) for _ in range(64)]
        neg = [rng.gauss(0.0, 0.5) for _ in range(64)]
        receipt = probe(rank_auc, pos, neg)
    elif a.module and a.pos and a.neg:
        pos = [float(x) for x in a.pos.split(",")]
        neg = [float(x) for x in a.neg.split(",")]
        receipt = probe(_load_metric(a.module, a.fn), pos, neg)
    else:
        ap.error("need --selftest, or --module + --fn + --pos + --neg")

    text = json.dumps(receipt, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    print(text)
    sys.exit(0 if receipt["verdict"] == "GREEN" else 1)


if __name__ == "__main__":
    main()
