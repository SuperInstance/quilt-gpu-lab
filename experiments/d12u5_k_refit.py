#!/usr/bin/env python3
"""D12u5 — k-miscalibration check (seed 2718).

D12u2 (p=0.3, N=64) and D12u4 (p=0.4, N=64) both showed model/harness ratios
one-directionally conservative (1.0-1.5, model always under-predicts).
Hypothesis under test: a SINGLE refit of the variance scale k (fit on the
p=0.4 surface) centers BOTH p axes two-sidedly.

Model floors scale exactly linearly in k (M1's sigma = k/sqrt(W*T)), so the
per-surface least-squares refit is k_fit = k0 * geomean(harness/model ratios)
on the fit surface. Gates:
  G1: after refit on p=0.4, ALL p=0.3 heldout ratios within [0.67, 1.5].
  G2: heldout ratios STRADDLE 1.0 (min < 0.95 and max > 1.05) — genuinely
      two-sided, not merely covered.
Verdict KEEP_miscalibrated only if G1 and G2 both pass; else the conservatism
is config-dependent (structural), KILL_single_k.
"""
import json
import math
from pathlib import Path

SEED = 2718
K0 = 0.657
R = Path(__file__).resolve().parents[1] / "results"

u2 = json.load(open(R / "d12u2_n64_heldout.json"))
u4 = json.load(open(R / "d12u4_p04_heldout.json"))

def ratios(surface, k):
    out = []
    for c in surface["cells"]:
        model = c.get("model_pred", c.get("model_floor")) * (k / K0)
        out.append({"W": c.get("W", c.get("w")), "eps": c["eps"], "harness": c["harness_floor"],
                    "model": model, "ratio": model / c["harness_floor"]})
    return out

fit = ratios(u4, K0)          # p=0.4 surface at old k
k_fit = K0 * math.exp(sum(math.log(c["harness"] / c["model"]) for c in fit) / len(fit))
held = ratios(u2, k_fit)      # p=0.3 heldout at refit k

hr = [c["ratio"] for c in held]
g1 = all(0.67 <= r <= 1.5 for r in hr)
g2 = min(hr) < 0.95 and max(hr) > 1.05
verdict = "KEEP_single_k_miscalibrated" if (g1 and g2) else "KILL_conservatism_structural"

res = {"seed": SEED, "fit_surface": "d12u4 p=0.4 N=64", "heldout_surface": "d12u2 p=0.3 N=64",
       "k_old": K0, "k_refit": round(k_fit, 4),
       "fit_ratios_p04_at_krefit": [round(c["ratio"], 3) for c in ratios(u4, k_fit)],
       "heldout_cells": [{**c, "ratio": round(c["ratio"], 3)} for c in held],
       "gates": {"G1_covered_067_150": g1, "G2_straddle_1": g2},
       "verdict": verdict}
(R / "d12u5_k_refit.json").write_text(json.dumps(res, indent=1))
print(f"k_refit={k_fit:.4f}  fit(p=0.4) ratios={[round(c['ratio'],2) for c in ratios(u4,k_fit)]}")
print(f"heldout(p=0.3) ratios={[round(r,2) for r in hr]}")
print(f"G1={g1} G2={g2} -> {verdict}")
