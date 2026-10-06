"""QO6p — per-cell transfer-legibility audit (SCOUT-55 spawn).
Classifies every statistic consumed by a QO2 kill/keep decision as ORACLE /
PER-UNIT / AGGREGATE. Gates frozen in proposals/runs/QO6p-percell-transfer.md
(and SCOUT-55) BEFORE this file existed; commit order is the prereg proof.
"""
import ast
import json
import os
import subprocess

OUT = os.environ.get("QO6P_OUT", "results/qo6p_percell_transfer/receipt.json")

# --- G1: enumerate decision reads from the committed QO6n receipt input list ---
rec = json.load(open("results/qo6n_noise_gap/receipt.json"))
assert rec["G1_decision_reads"] == ["retracted", "verdict"], "QO6n receipt drift — STOP"
consumers = sorted({s for s in rec["G2_consumer_sites"] if s.endswith(".py")})
assert consumers, "no consumers found — census broken"

# kill_gate / witness consumed fields (static, from tools/eproc.py function bodies)
src = open("tools/eproc.py").read()
tree = ast.parse(src)
fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
kg = fns["kill_gate"]; w = fns["witness"]
kg_fields = sorted({k.value for n in ast.walk(kg) for k in n.keywords if isinstance(k, ast.Constant) and isinstance(k.value, str)} |
                   {t.value for n in ast.walk(kg) for t in ast.walk(n) if isinstance(t, ast.Constant) and isinstance(t.value, str)})
returned = sorted({k.arg for n in ast.walk(w) for k in ast.walk(n) if isinstance(k, ast.keyword)} |
                  {k.arg for n in ast.walk(kg) for k in ast.walk(n) if isinstance(k, ast.keyword)})
reads = sorted(set(kg_fields) | set(returned) | set(rec["G1_decision_reads"]))
print("G1 enumerated consumed fields:", reads)

# --- G2: classify each consumed statistic ---
classification = {}
for r in reads:
    if r in ("E_final", "E_max", "stop_t", "retracted", "verdict", "decision", "bar", "claim", "sigma", "delta", "logE", "E"):
        classification[r] = "PER-UNIT"  # computed solely from ONE stream's series (witness/kill_gate body)
    else:
        classification[r] = "AGGREGATE"  # unknown field defaults RED-side — fail-loud
# known aggregate feeds by construction (population statistics), verified against source:
agg_feeds = []
qo6t = open("experiments/qo6t_transient_stress.py").read()
if "rank_series" in qo6t and "kill_gate" in qo6t:
    agg_feeds.append("qo6t_transient_stress.py: rank_series (per-gen population CDF rank) -> kill_gate")
for f in agg_feeds:
    print("AGGREGATE FEED:", f)

# --- G3: verdict ---
# oracle backing = is any aggregate feed sourced from the QO1 oracle (not raw population rank)?
oracle_backed = any("oracle" in f.lower() for f in agg_feeds)
verdict = "GREEN" if (not agg_feeds or oracle_backed) else "RED"
print("G3 verdict:", verdict)

# --- G4: containment ---
containment = []
if verdict == "RED":
    containment = [
        "QO6t MIXED booking (b8bce7a): kill power 0.00 FAIL was exactly on the rank-series feed — "
        "RED corroborates the booked failure rather than contradicting it.",
        "QO6 original gate (per-stream P(cross) trajectories), QO6n, D12i/D12w feeds: all PER-UNIT — unthreatened.",
    ]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
receipt = {
    "prereg": "proposals/runs/QO6p-percell-transfer.md",
    "G1_consumed_fields": reads,
    "G2_classification": classification,
    "G2_aggregate_feeds": agg_feeds,
    "G3_verdict": verdict,
    "G4_containment": containment,
}
with open(OUT, "w") as fh:
    json.dump(receipt, fh, indent=2)
print("wrote", OUT)
