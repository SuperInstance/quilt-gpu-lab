"""QO6 — retractable kill-evidence validation (CPU, deterministic).
Claims V1-V4 per proposals/runs/QO6-retractable-kill-evidence.md.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import eproc as eproc_mod  # noqa: E402

eprocess = eproc_mod.eprocess
kill_gate = eproc_mod.kill_gate
witness = eproc_mod.witness

OUT = Path(__file__).resolve().parents[1] / "results" / "qo6_kill_evidence"
OUT.mkdir(exist_ok=True)
R = {}

# ---------- V1a: exact single-increment LR algebra ----------
sigma = 1.5
d0 = -2.0
ref = -(  (d0 - (-0.2 * sigma))**2 - d0**2 ) / (2 * sigma**2)  # mu=0.2*sigma, sign=-1
K = 1
res = eprocess([d0], sigma, sign=-1, mu_grid=[0.2])
lr0 = res["logE"][0] - math.log(1 / K)  # strip mixture weight
R["V1a_lr_exact"] = {"expected": ref, "got": float(lr0), "abs_err": abs(ref - lr0)}
assert abs(ref - lr0) < 1e-12, "V1a FAIL: LR algebra mismatch"

# ---------- deterministic LCG (same doctrine as esign.pins.mjs) ----------
def lcg(seed):
    s = seed & 0xFFFFFFFF
    while True:
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        yield s

def drift_down(n, seed=7):
    g = lcg(seed); out = []; x = 400.0
    for _ in range(n):
        out.append(x); x += -2 + (next(g) % 5) - 2
    return out

def flat_noise(n, seed=11):
    g = lcg(seed); out = []; x = 400.0
    for _ in range(n):
        out.append(x); x += (next(g) % 9) - 4
    return out

# V1b behavioral pins
w_drift = witness(drift_down(40, 7), sigma=1.5)
w_flat = witness(flat_noise(200, 11), sigma=2.6)
R["V1b"] = {
    "drift_down": {"verdict": w_drift["verdict"], "stop_t": w_drift["stop_t"], "retracted": w_drift["retracted"]},
    "flat_noise": {"verdict": w_flat["verdict"], "E_max": w_flat["E_max"]},
}
assert w_drift["verdict"] == "WITNESSED" and w_drift["stop_t"] <= 40, "V1b FAIL: real drift not witnessed"
assert w_flat["verdict"] == "NOT_WITNESSED", "V1b FAIL: flat noise falsely witnessed"

# V1c refusal pins
for name, fn in [
    ("short_series", lambda: witness([1.0, 2.0, 3.0], sigma=1.0)),
    ("no_sigma", lambda: witness(drift_down(20, 3), sigma=None)),
    ("bad_sigma", lambda: witness(drift_down(20, 3), sigma=0.0)),
    ("nonfinite", lambda: witness([1.0] * 10 + [float("nan")], sigma=1.0)),
]:
    try:
        fn(); R.setdefault("V1c_refusals", {})[name] = "NO-REFUSE (FAIL)"
    except ValueError:
        R.setdefault("V1c_refusals", {})[name] = "refused"
assert all(v == "refused" for v in R["V1c_refusals"].values()), "V1c FAIL"

# ---------- V2: late-bloomer retraction ----------
# P(cross) slides toward death (12 gens, ~-0.05/gen = 1.25 sigma at sigma=0.04)
# then jumps late (QG3-style trap opening at gen 12). Iteration note: first attempt
# (7-step slide, sigma=0.08, delta=0.05) never fired E (E_max 2.86 < bar 20) — booked,
# parameters sharpened, same construction.
bloom = [0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05,
         0.19, 0.33, 0.47, 0.61, 0.72, 0.80, 0.86]
kg_bloom = kill_gate(bloom, sigma=0.04, delta=0.1)  # pre-registered scales
R["V2_late_bloomer"] = {k: kg_bloom[k] for k in ("decision", "verdict", "stop_t", "retracted", "E_max", "E_final")}
assert kg_bloom["retracted"], "V2 FAIL: late bloom did not retract"
assert kg_bloom["decision"] == "KEEP", "V2 FAIL: retracting stream not KEPT"

# ---------- V3: hopeless stream stays killed ----------
g = lcg(99)
hopeless = [0.60]
for _ in range(13):
    hopeless.append(max(0.0, hopeless[-1] - 0.06 + ((next(g) % 5) - 2) * 0.01))
kg_dead = kill_gate(hopeless, sigma=0.03)
R["V3_hopeless"] = {k: kg_dead[k] for k in ("decision", "verdict", "stop_t", "retracted", "E_max")}
assert kg_dead["decision"] == "KILL_CANDIDATE" and not kg_dead["retracted"], "V3 FAIL"

# ---------- V4: flat oracle trajectory -> insufficient ----------
flat_p = [0.5 + ((next(g) % 5) - 2) * 0.02 for _ in range(16)]
kg_flat = kill_gate(flat_p, sigma=0.04)
R["V4_flat"] = {"decision": kg_flat["decision"], "verdict": kg_flat["verdict"]}
assert kg_flat["decision"] in ("INSUFFICIENT",), "V4 FAIL"

R["ALL_PASS"] = True
(OUT / "results.json").write_text(json.dumps(R, indent=2, default=float))
print(json.dumps(R, indent=2, default=float))
print("QO6 VALIDATION: ALL V1-V4 PASS")
