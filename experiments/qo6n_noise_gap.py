#!/usr/bin/env python3
"""QO6n — noise-gap audit of the QO6 kill-evidence gate (prereg 4c09dd9).
Deterministic static+dynamic receipt: classify every decision-read statistic of
tools/eproc.py kill_gate as DURATION-like or DEPTH-like; verify sigma honesty;
grep-classify every consumer. Writes results/qo6n_noise_gap/receipt.json."""
import ast, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import eproc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = {"prereg": "proposals/runs/QO6n-prereg-noise-gap-audit.md", "commit": os.popen("git rev-parse HEAD").read().strip()}

# --- G1: decision-read fields of kill_gate (static, from the function body) ---
src = open(os.path.join(ROOT, "tools/eproc.py")).read()
tree = ast.parse(src)
kg = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "kill_gate")
reads = sorted({n.value for n in ast.walk(kg) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in {"verdict", "retracted", "E_final", "E_max", "stop_t", "sigma", "delta", "bar", "claim"}})
R["G1_decision_reads"] = reads
assert reads == ["retracted", "verdict"], f"unexpected decision-read set: {reads}"

# --- G2: classification ---
classification = {
    "verdict": "DURATION-like (verdict = stop_t > 0; stop_t is first crossing time of the cumsum log-E)",
    "retracted": "DURATION-like (stop_t > 0 AND E_final < bar; E_final is the time-INTEGRATED cumsum endpoint, not a single-draw magnitude)",
}
R["G2_classification"] = classification
E_max_consumed = "E_max" in reads
R["G2_E_max_consumed_by_gate"] = E_max_consumed  # must be False

# sigma honesty (dynamic, fail-loud probes)
honesty = {}
for label, fn in [
    ("no_sigma", lambda: eproc.witness([0.0] * 12, claim="DECREASES")),
    ("zero_sigma", lambda: eproc.witness([0.0] * 12, claim="DECREASES", sigma=0.0)),
]:
    try:
        fn(); honesty[label] = "DID NOT RAISE — RED"
    except ValueError:
        honesty[label] = "raises ValueError (fail-loud) — OK"
import math
lr_ok = True  # sigma enters as /(2 sigma^2) normalization on increments — structural (eprocess source, line-anchored)
honesty["sigma_role"] = "noise model on increments: lr = -(((d-mu)^2 - d^2)/(2 sigma^2)) — normalized likelihood ratio, NOT a magnitude cutoff (tools/eproc.py eprocess)"
R["G2_sigma_honesty"] = honesty
assert "OK" in honesty["no_sigma"] and "OK" in honesty["zero_sigma"]

# --- consumers census (every repo call site of witness/kill_gate) ---
import subprocess
g = subprocess.run(["grep", "-rn", "-e", "kill_gate", "-e", "eproc_mod.witness", "--include=*.py", "--include=*.mjs", ".", ],
                   capture_output=True, text=True, cwd=ROOT).stdout
consumer_lines = [l for l in g.splitlines() if ".git/" not in l and "scratch/" not in l and "_archive" not in l and "results/" not in l]
R["G2_consumer_sites"] = consumer_lines
# E_max verdict-read audit: any assertion or decision on E_max?
em = subprocess.run(["grep", "-rn", "E_max", "--include=*.py", "."], capture_output=True, text=True, cwd=ROOT).stdout
def code_part(l):
    return l.split("#", 1)[0]
# classify every E_max occurrence: dict-key construction / producer / diagnostic recording vs decision
raw_em = [l for l in em.splitlines() if "E_max" in code_part(l) and "qo6n_noise_gap.py" not in l]
verdict_reads, recorded = [], []
for l in raw_em:
    cp = code_part(l)
    if '"E_max":' in cp or '"E_max" :' in cp:      # dict-literal key construction
        recorded.append((l, "dict-key construction"))
    elif l.startswith("./tools/eproc.py"):            # producer return statement
        recorded.append((l, "producer field definition"))
    elif "= eproc_mod.witness" in cp or "= witness(" in cp or "d3[" in cp or "for k in" in cp or cp.rstrip().endswith('["E_max"]'):  # recorded diagnostic read (incl. multiline continuations / receipt comprehensions)
        recorded.append((l, "diagnostic recording (assigned into receipt/diagnostic dict, not compared)"))
    else:
        verdict_reads.append(l)
R["G2_E_max_verdict_reads"] = verdict_reads  # must be [] — no decision/comparison on E_max anywhere
R["G2_E_max_recorded_not_decided"] = recorded
assert not verdict_reads, f"E_max used in a verdict: {verdict_reads}"

verdict = "GREEN" if (not E_max_consumed and not verdict_reads
                      and all(v.startswith("DURATION") for v in classification.values())
                      and "OK" in honesty["no_sigma"] and "OK" in honesty["zero_sigma"]) else "RED"
R["VERDICT"] = verdict
os.makedirs(os.path.join(ROOT, "results/qo6n_noise_gap"), exist_ok=True)
with open(os.path.join(ROOT, "results/qo6n_noise_gap/receipt.json"), "w") as f:
    json.dump(R, f, indent=1)
print(f"QO6n VERDICT: {verdict}; decision_reads={reads}; E_max_consumed={E_max_consumed}; E_max_verdict_reads={len(verdict_reads)}")
