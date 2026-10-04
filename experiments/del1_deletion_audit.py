"""DEL-1 — sufficiency-by-deletion audit over the QO2 routing stack.
Pre-reg: proposals/runs/DEL1-deletion-audit-qo2.md (committed 20f07ba BEFORE this fired).
Deterministic CPU; deletes one component/branch at a time and asks whether the booked
QO6 V1-V4 verdicts (and cited QO3/QG7 numbers, D4 citation-level) would change.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import eproc as eproc_mod  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "results" / "del1_deletion_audit"
OUT.mkdir(exist_ok=True)
R = {"pre_reg": "proposals/runs/DEL1-deletion-audit-qo2.md (20f07ba)"}

# ---------- rebuild the exact QO6 booked fixtures (verbatim from experiments/qo6_kill_evidence.py) ----------
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

BLOOM = [0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05,
         0.19, 0.33, 0.47, 0.61, 0.72, 0.80, 0.86]
g99 = lcg(99)
HOPELESS = [0.60]
for _ in range(13):
    HOPELESS.append(max(0.0, HOPELESS[-1] - 0.06 + ((next(g99) % 5) - 2) * 0.01))
FLAT_P = [0.5 + ((next(g99) % 5) - 2) * 0.02 for _ in range(16)]

# ---------- D1: delete retraction (once-witnessed = final kill; p-value-in-disguise class) ----------
def kill_gate_no_retract(series, sigma, delta=0.05):
    w = eproc_mod.witness(series, claim="DECREASES", sigma=sigma, delta=delta)
    if w["verdict"] == "WITNESSED":   # E_max >= bar at ANY t; retraction erased
        decision = "KILL_CANDIDATE"
    else:
        decision = "INSUFFICIENT"
    return {"decision": decision}

d1 = {
    "bloom": kill_gate_no_retract(BLOOM, sigma=0.04, delta=0.1)["decision"],      # booked KEEP
    "hopeless": kill_gate_no_retract(HOPELESS, sigma=0.03)["decision"],           # booked KILL_CANDIDATE
    "flat_p": kill_gate_no_retract(FLAT_P, sigma=0.04)["decision"],               # booked INSUFFICIENT
}
d1["V2_flip"] = (d1["bloom"] == "KILL_CANDIDATE")   # PREDICTION: True (flips KEEP->KILL)
d1["VERDICT"] = "LOAD-BEARING (retraction deletes KEEP on late bloomers)" if d1["V2_flip"] else "RED: retraction decorative"
R["D1_delete_retraction"] = d1

# ---------- D2: delete mu-mixture (single mu=0.2*sigma) ----------
def witness_single_mu(series, sigma, delta):
    series = list(series)
    sign = -1.0
    d = np.diff(np.asarray(series, dtype=float))
    mu = sign * 0.2 * sigma
    lr = -(((d - mu) ** 2 - d ** 2) / (2.0 * sigma * sigma))
    log_e = np.cumsum(lr)
    E = np.exp(log_e)
    bar = 1.0 / delta
    stop_t = next((t + 1 for t, e in enumerate(E) if e >= bar), -1)
    return {"verdict": "WITNESSED" if stop_t > 0 else "NOT_WITNESSED",
            "retracted": stop_t > 0 and E[-1] < bar, "E_max": float(E.max())}

d2 = {}
d2["drift_down"] = witness_single_mu(drift_down(40, 7), 1.5, 0.05)     # booked WITNESSED
d2["flat_noise"] = witness_single_mu(flat_noise(200, 11), 2.6, 0.05)   # booked NOT_WITNESSED
d2["bloom_gate"] = witness_single_mu(BLOOM, 0.04, 0.1)                 # booked retract->KEEP
d2["VERDICT"] = ("all pinned verdicts survive single-mu; mixture is pin-level, not outcome-level"
                 if (d2["drift_down"]["verdict"] == "WITNESSED"
                     and d2["flat_noise"]["verdict"] == "NOT_WITNESSED"
                     and d2["bloom_gate"]["retracted"])
                 else "MIXTURE LOAD-BEARING: a pinned verdict flipped")
R["D2_delete_mixture"] = d2

# ---------- D3: delete sigma contract (silent default = std of series) ----------
d3 = {}
d3["flat_noise_Emax_booked_sigma"] = eproc_mod.witness(flat_noise(200, 11), sigma=2.6)["E_max"]
d3["flat_noise_Emax_self_sigma"] = eproc_mod.witness(
    flat_noise(200, 11), sigma=float(np.std(np.diff(np.asarray(flat_noise(200, 11), dtype=float)))))["E_max"]
w_bloom_self = eproc_mod.witness(BLOOM, sigma=float(np.std(np.diff(np.asarray(BLOOM, dtype=float)))), delta=0.1)
d3["bloom_self_sigma_retracted"] = w_bloom_self["retracted"]
d3["NOTE"] = "self-referential sigma materially moves E_max; refusal contract separately pinned by QO6 V1c"
R["D3_delete_sigma_contract"] = d3

# ---------- D4: oracle deletion (citation-level, booked numbers) ----------
R["D4_oracle_citation"] = {
    "QO3_gen1_AUC_booked": 0.880, "chance": 0.500,
    "QG7_P2_frozen_oracle_range": [0.566, 0.581],
    "VERDICT": "NON-DECORATIVE by inspection: deletion -> chance collapses both booked signals",
}

json.dump(R, open(OUT / "results.json", "w"), indent=2, default=float)
print(json.dumps(R, indent=2, default=float))
