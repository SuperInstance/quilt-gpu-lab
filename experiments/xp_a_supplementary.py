#!/usr/bin/env python3
"""XP-A supplementary — power context for the frozen instrument-transfer gates.

The pre-registered XP-A gates (experiments/xp_a_instrument_transfer.py, scout
§1c) score held-out recall against a "chance" of 0.50. That framing is a
balanced-prior detector: a coin detector has recall 0.50 AND false-positive
rate 0.50. Because the instruments here are very conservative (clean FPR 0.00
for A and B), recall-vs-0.50 alone understates an instrument that is merely
silent (A) and overstates one that fires noisily (C). This supplement reports,
WITHOUT changing the frozen verdict:

  - Wilson 95% CI on held-out recall (n=160) and clean FPR (n=200);
  - exact one-sided binomial p-values vs p0=0.50 (chance) and p0=0.60 (gate);
  - balanced accuracy = (recall + specificity)/2, the framing the 0.50 chance
    constant actually presumes;
  - the exact permutation distribution of Spearman rho at n=3 (why the frozen
    rho>=0.70 bar is almost binary here);
  - a "gap-zone" flag: instruments with known-power in [0.50, 0.65) AND
    held-out power <= 0.50 — the KILL shape present just under the frozen
    HIGH_KNOWN_POWER=0.65 bar.

Reads only atifact JSON (advisory, adds no randomness). Not part of the
frozen gates; the ledger verdict remains whatever xp_a_instrument_transfer.py
booked. Regenerate: python experiments/xp_a_supplementary.py
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / "results" / "xp_a"
CHANCE = 0.50
GATE = 0.60
HIGH_KNOWN = 0.65


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def binom_tail_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X~Bin(n,p) — exact, one-sided."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k2 in range(i, j + 1):
            r[order[k2]] = avg
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main() -> int:
    grid = json.loads((OUT / "grid.json").read_text())
    per = json.loads((OUT / "per_receipt_detections.json").read_text())
    import collections
    det = collections.Counter((d["instrument"], bool(d["heldout"])) for d in per)

    insts = list(grid["instrument_summary"])
    n_held = 4 * 40      # four held-out ops x 40 receipts
    n_known = 6 * 40     # six known ops x 40 receipts
    n_clean = 200

    rows = {}
    for inst in insts:
        kh, kk = det[(inst, True)], det[(inst, False)]
        # clean FP: use per-op grid clean recall (fraction of CLEAN flagged)
        fpr = grid["grid_recall_per_op"][inst].get("CLEAN", None)
        kc = round(fpr * n_clean) if fpr is not None else 0
        rec_h = kh / n_held
        spec = 1.0 - (kc / n_clean)
        bal = 0.5 * (rec_h + spec)
        rows[inst] = {
            "known_power_recall": round(kk / n_known, 4),
            "known_recall_wilson95": [round(v, 4) for v in wilson(kk, n_known)],
            "heldout_recall": round(rec_h, 4),
            "heldout_recall_wilson95": [round(v, 4) for v in wilson(kh, n_held)],
            "clean_fpr": fpr,
            "clean_fpr_wilson95": [round(v, 4) for v in wilson(kc, n_clean)],
            "balanced_accuracy_heldout": round(bal, 4),
            "p_ge_vs_chance_0.50": round(binom_tail_ge(kh, n_held, CHANCE), 6),
            "p_ge_vs_gate_0.60": round(binom_tail_ge(kh, n_held, GATE), 6),
            "beats_chance_recall": rec_h > CHANCE,
            "beats_chance_balanced": bal > CHANCE,
            "gap_zone_known_ge_0.50_and_heldout_le_0.50": (
                kk / n_known >= 0.50 and rec_h <= CHANCE),
        }

    xs = [grid["instrument_summary"][i]["known_power"] for i in insts]
    ys = [grid["instrument_summary"][i]["unknown_power"] for i in insts]
    rho_obs = spearman(xs, ys)
    perms = list(itertools.permutations(range(len(insts))))
    rho_dist = [spearman(list(p), ys) for p in perms]  # permute the known ranks
    n_ge = sum(1 for r in rho_dist if r >= rho_obs - 1e-12)
    perm_p = n_ge / len(perms)

    out = {
        "experiment": "XP-A-supplementary",
        "note": "advisory only; frozen verdict lives in grid.json",
        "n_heldout": n_held, "n_known": n_known, "n_clean": n_clean,
        "per_instrument": rows,
        "frozen_spearman_rho": round(rho_obs, 4),
        "spearman_n3_exact_permutation": {
            "distinct_rho_values": sorted(set(round(r, 4) for r in rho_dist)),
            "p_value_ge_observed": round(perm_p, 6),
            "note": "at n=3 instruments rho is drawn from a 4-value support; the "
                    "frozen bar rho>=0.70 is satisfiable only at rho=1.0 (perfect "
                    "rank agreement) — the gate is effectively binary here.",
        },
        "frozen_verdict": grid["verdict"],
        "frozen_verdict_reasons": grid.get("verdict_reasons"),
        "reading": (
            "verdict_gate_pins (A) transfers ZERO held-out power (0/160) despite "
            "non-trivial known recall; trained_classifier (C) is below the 0.50 "
            "recall bar held-out (66/160) and its balanced accuracy barely clears "
            "chance; only step_parser (B) transfers (159/160). A and C sit in the "
            "KILL 'gap zone' (known >=0.50, held-out <=0.50) but just BELOW the "
            "frozen HIGH_KNOWN_POWER=0.65 bar, so the KILL existence clause does "
            "not fire. Frozen verdict stands (INCONCLUSIVE); the shape the KILL "
            "gate targets is present at a lower known-power level."
        ),
    }
    (OUT / "supplementary.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
