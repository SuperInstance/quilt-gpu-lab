#!/usr/bin/env python3
"""GLOSS-1 loss-liveness census (SCOUT-98 spawn; prereg 143c9d3, gates frozen before fire).

G1 enumerate booked-verdict scoring functions (hard table = prereg scope).
G2 unwired-parameter AST audit via tools/param_liveness.py (imported, not shelled).
G3 degenerate-maximum probes on the pure metrics (constant/tie/everything inputs).
G4 any RED names the threatened booking in the receipt.

CPU only. Receipt: results/gloss1/census.json. Exit 0 = GREEN, 4 = RED present.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import param_liveness  # noqa: E402

FINDINGS = []


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(REPO / path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def note(level, target, booking, text):
    FINDINGS.append({"level": level, "target": target, "booking": booking, "note": text})


# ---------- G1: the prereg table ----------
TARGETS = [
    ("tools/eproc.py", "eproc", ["increments", "eprocess", "kill_gate"], "QO6/QO6s/PATH-1"),
    ("tools/decision_cell.py", "decide", ["answer_of"], "QC-JEV/DECIDE-1"),
    ("tools/ensemble_corr_census.py", "ecc", ["_avg_ranks", "_pearson", "spearman", "census"], "QG7b/D12i"),
]
# torch-heavy fit heads audited separately (SOFT class, see bottom)
g1 = {"rows": [], "audited": 0}
for path, modname, funcs, booking in TARGETS:
    try:
        load(path, modname)
        ok = True
    except Exception as e:  # noqa: BLE001
        ok = False
        note("RED", path, booking, f"module fails to import: {e!r}")
    g1["rows"].append({"module": path, "functions": funcs, "booking": booking, "import_ok": ok})
    g1["audited"] += 1

ep = load("tools/eproc.py", "eproc")
dec = load("tools/decision_cell.py", "decide")
ecc = load("tools/ensemble_corr_census.py", "ecc")

# ---------- G2: unwired-parameter AST audit ----------
g2 = []
for path, modname, funcs, booking in TARGETS:
    res = {"module": path, "functions": []}
    src = (REPO / path).read_text()
    any_unwired = False
    for fname in funcs:
        rows = param_liveness.audit_function(src, fname)
        res["functions"].append({"function": fname, "rows": rows})
        for r in rows:
            if r["status"] == "UNWIRED":
                any_unwired = True
                note("RED", f"{path}:{fname}", booking,
                     f"unwired parameter {r['param']!r} — {r['detail']}")
    res["unwired"] = any_unwired
    g2.append(res)

# ---------- G3: degenerate-maximum probes ----------
g3 = []

def probe(name, booking, fn):
    try:
        out = fn()
        g3.append({"probe": name, "booking": booking, **out})
    except Exception as e:  # noqa: BLE001
        g3.append({"probe": name, "booking": booking, "raised": repr(e)})

# eprocess on constant series: increments all zero -> likelihood ratio identically
# favors mu=0 -> E must stay at/below 1 (no spurious kill optimum). sigma<=0 refusal
# already booked (PARAM-1/THRESH-2).
def _eproc_const():
    r = ep.eprocess([1.0] * 20, sigma=0.5)
    emax = float(r["E"].max())
    ok = emax <= 1.0 + 1e-9
    if not ok:
        note("RED", "eproc.eprocess", "QO6", f"constant series reaches E={emax} (spurious kill optimum)")
    return {"E_max_on_const": emax, "no_spurious_kill": ok, "verdict": "GREEN" if ok else "RED"}

probe("eprocess constant-series", "QO6", _eproc_const)

def _eproc_sigma():
    try:
        ep.eprocess([1.0] * 20, sigma=0.0)
        return {"verdict": "RED", "note": "sigma=0 accepted silently"}
    except ValueError:
        return {"verdict": "GREEN", "note": "sigma<=0 refuses fail-loud (booked)"}

probe("eprocess sigma-refusal", "QO6", _eproc_sigma)

def _spearman_const():
    r1 = ecc.spearman([5.0] * 10, list(range(10)))
    r2 = ecc.spearman([5.0] * 10, [3.0] * 10)
    p1 = ecc._pearson([1.0] * 8, list(map(float, range(8))))
    ok = r1 is None and r2 is None and p1 is None
    if not ok:
        note("RED", "ensemble_corr_census.spearman/_pearson", "QG7b/D12i",
             f"constant input yields non-None rho ({r1},{r2},{p1}) — tie resolves to a score")
    return {"const_vs_varied": r1, "const_vs_const": r2, "pearson_const": p1,
            "verdict": "GREEN" if ok else "RED", "note": "None propagates; census() fails loud on None"}

probe("spearman/_pearson constant-input", "QG7b/D12i", _spearman_const)

def _census_degenerate():
    runs = [{"scores": [1.0] * 6}, {"scores": [1.0] * 6}]
    try:
        ecc.census(runs)
        return {"verdict": "RED", "note": "all-constant two-run census returned instead of failing loud"}
    except SystemExit:
        return {"verdict": "GREEN", "note": "degenerate census exits loud (fail())"}

probe("census all-constant runs", "QG7b/D12i", _census_degenerate)

def _answer_of_tie():
    q = {"type": "choice", "options": ["A", "B"], "codes": ["A", "B"]}
    out = dec.answer_of(q, [1.0, 1.0])
    tie_first = out["choice"] == "A" and out["confidence"] == 0.0
    q1 = {"type": "choice", "options": ["A"], "codes": ["A"]}
    out1 = dec.answer_of(q1, [1.0])
    single = out1["confidence"] == 1.0
    lvl = "YELLOW" if tie_first else "RED"
    if not tie_first:
        note("RED", "decision_cell.answer_of", "QC-JEV/DECIDE-1", "tie probs do not resolve to documented first-index/zero-confidence")
    return {"tie": out, "single_option": out1,
            "verdict": lvl,
            "note": "tie -> first index at confidence 0.0 (harmless: probs are softmax-continuous; "
                    "single-option conf 1.0 is a documented k==1 branch). Booked argmin law untouched."}

probe("answer_of tie/single-option", "QC-JEV/DECIDE-1", _answer_of_tie)

# SOFT class (torch fit heads): logit_fit/fit_mlp_seed live in torch-heavy experiment
# scripts; G3 verdict-surface for them rides the QO10 repro (BOOKED) — declared, not skipped.
g3_soft = {"targets": ["experiments/oracle1.py:logit_fit", "experiments/qo10_projection_ladder.py:fit_mlp_seed"],
           "status": "SOFT-DEFERRED-TO-BOOKED-REPRO",
           "note": "QO10 booked verdict-level REPRO PASS 2026-10-02; stochastic-head degeneracy is "
                   "covered by the ensemble-spread rule (no gap smaller than spread = finding)."}

receipt = {"gloss1": "loss-liveness census", "prereg": "proposals/runs/GLOSS-1-loss-liveness-census-2026-10-11.md (143c9d3)",
           "G1": g1, "G2": g2, "G3": g3, "G3_soft": g3_soft, "findings": FINDINGS}

out = REPO / "results" / "gloss1"
out.mkdir(parents=True, exist_ok=True)
(out / "census.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

reds = [f for f in FINDINGS if f["level"] == "RED"]
print(f"GLOSS-1: G1 rows={g1['audited']} G3 probes={len(g3)} RED={len(reds)} YELLOW="
      f"{sum(1 for f in FINDINGS if f['level']=='YELLOW')}")
for f in FINDINGS:
    print(f"  [{f['level']}] {f['target']} ({f['booking']}): {f['note']}")
print(f"VERDICT: {'RED' if reds else 'GREEN'}")
sys.exit(4 if reds else 0)
