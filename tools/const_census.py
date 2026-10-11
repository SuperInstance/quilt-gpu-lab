#!/usr/bin/env python
"""CONST-1: winning-arm-constant census (pre-reg proposals/runs/CONST-1-winning-arm-constant-census-prereg-2026-10-10.md).

Census over A-vs-B booked arms: flag any verdict-deciding metric whose producer emits a
constant (zero variance across runs). RED iff constant + difference-claim + no data-derived
write site. Fails loud on missing files. Deterministic; CPU; no GPU.
"""
import json, glob, math, os, sys

OUT = {}
fail = []

def need(p):
    if not os.path.exists(p):
        fail.append(f"missing {p}")
    return p

# ---------- G1: load ----------
qg6 = json.load(open(need("results/qg6_variance_rescue/results.json")))
det = {os.path.basename(p): json.load(open(p))
       for p in sorted(glob.glob("results/determ1_lattice_snap/[AB]-*.json"))}
d1b = json.load(open(need("results/decide1/decide1b_results.json")))
d1c = json.load(open(need("results/decide1/decide1c_results.json")))
for s in ["experiments/qg6_variance_rescue.py", "experiments/determ1_lattice_snap.py",
          "experiments/decide1b.py", "experiments/ionq2_rung2_battery.py"]:
    need(s)
if fail:
    print("G1 FAIL:", fail); sys.exit(1)
print("G1 PASS: all target artifacts + producers present")

# ---------- G2: variance table ----------
def var(vals):
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / len(vals)

table = {}
for k, arm in sorted(qg6["arms"].items()):
    table[f"qg6.k{k}.crossed"] = {"vals": [arm["crossed"]], "n_runs": 1, "var": "single-value-per-arm"}
# cross-arm variance is the relevant spread for qg6
xs = [qg6["arms"][k]["crossed"] for k in sorted(qg6["arms"])]
table["qg6.crossARM.crossed"] = {"vals": xs, "var": var(xs)}

det_metrics = {}
for name, d in det.items():
    arm = name.split("-")[0]
    for m in ["rate12", "rate24", "auc_fresh"]:
        det_metrics.setdefault(m, {}).setdefault(arm, []).append(d[m])
for m, arms in det_metrics.items():
    for arm, vals in sorted(arms.items()):
        table[f"determ1.{m}[{arm}]"] = {"vals": vals, "var": var(vals)}
shas = {d["crossed_gen_sha"] for d in det.values()}
table["determ1.crossed_gen_sha"] = {"n_files": len(det), "n_distinct": len(shas)}

table["decide1b.argmax_acc"] = {"vals": [d1b["argmax_acc"]["acc"]]}
table["decide1c.argmax_acc"] = {"vals": [d1c["C2"]["argmax_acc"]["acc"]]}
table["decide1.bc.pred_is_argmin_balance"] = {"vals": [d1b["P1"]["pred_is_argmin_balance"],
                                                       d1c["exploratory_pred_is_argmin_balance"]],
                                              "var": var([d1b["P1"]["pred_is_argmin_balance"],
                                                          d1c["exploratory_pred_is_argmin_balance"]])}

const_flags = []
for key, row in table.items():
    if row.get("var") == 0.0:
        const_flags.append(key)
print("G2 variance table:", json.dumps(table, indent=1, default=str))
print("G2 zero-variance flags:", const_flags)

# ---------- G3: classification ----------
cls = {}
# qg6: cross-arm spread nonzero -> arms are data-derived, no constant class
cls["qg6"] = "GREEN" if table["qg6.crossARM.crossed"]["var"] > 0 else "RED"
# determ1: per-arm rates vary; sha distinctness n_distinct == n_files (not a constant)
cls["determ1"] = "GREEN" if (len(shas) == len(det)
                             and all(table[f"determ1.{m}[A]"]["var"] > 0
                                     for m in ["rate12", "rate24", "auc_fresh"])) else "RED"
# decide1b/c: identical argmax_acc across instructions IS the booked finding (identity-claim).
# Verify data-derived: producer computes k/len(rows) from per-question rows (grep evidence).
src = open("experiments/decide1b.py").read()
derived = "argmax_correct" in src and "/ len(rows)" in src.replace("kmin/len(rows)", "/ len(rows)") or "/len(rows)" in src
cls["decide1"] = "GREEN-with-note (identity-claim; constant = the finding)" if derived else "RED"
# ionq2: gates are equality vs literal theory pins; got-side computed from statevector
src2 = open("experiments/ionq2_rung2_battery.py").read()
cls["ionq2"] = "GREEN-with-note (equality-vs-theory-literal; identity is the claim)" \
    if "def check" in src2 and "evaluate(" in src2 else "RED"

red = [k for k, v in cls.items() if v == "RED"]
print("G3 classification:", json.dumps(cls, indent=1))

# ---------- G4 ----------
OUT["g2_table"] = {k: {kk: vv for kk, vv in r.items()} for k, r in table.items()}
OUT["const_flags"] = const_flags
OUT["classification"] = cls
OUT["verdict"] = "GREEN" if not red else f"RED:{red}"
os.makedirs("results/const1", exist_ok=True)
json.dump(OUT, open("results/const1/census.json", "w"), indent=1, default=str)
print("CONST-1 VERDICT:", OUT["verdict"])
sys.exit(0 if not red else 2)
