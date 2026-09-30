#!/usr/bin/env python3
"""QC-JEV: discriminating-control pin for the jeff-0.8b oracle (pre-reg
proposals/runs/QC-JEV-discriminating-control.md, frozen before fire).

Fires 4 probes (2 noul, 2 choice) and scores the frozen gates. CPU only.
"""
import json, os, sys, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from decision_cell import DecisionCell

CKPT = "/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b"
assert os.path.exists(f"{CKPT}/model.safetensors"), "weights not present"

PROBES = [
    ("noul_pos", "noul",
     {"expression": "2+2", "claimed_result": "4"},
     {"instructions": "Is the claimed result of the arithmetic expression correct?"}),
    ("noul_neg", "noul",
     {"expression": "2+2", "claimed_result": "5"},
     {"instructions": "Is the claimed result of the arithmetic expression correct?"}),
    ("choice_pos", "choice",
     {"expression": "2+2"},
     {"instructions": "Which option describes the arithmetic expression?",
      "criteria": {"4": "correct sum of 2+2", "5": "incorrect sum of 2+2"}}),
    ("choice_neg", "choice",
     {"expression": "2+2"},
     {"instructions": "Which option describes the arithmetic expression?",
      "criteria": {"4": "incorrect sum of 2+2", "5": "correct sum of 2+2"}}),
]

cell = DecisionCell(CKPT, device="cpu")
out = {"checkpoint": CKPT, "probes": {}}
for name, qtype, state, q in PROBES:
    q["type"] = qtype
    res = cell.decide(state, q)
    out["probes"][name] = {k: v for k, v in res.items() if k != "_latency_ms"}
    print(name, json.dumps(res), flush=True)

pn, px = out["probes"]["noul_pos"], out["probes"]["noul_neg"]
cp, cx = out["probes"]["choice_pos"], out["probes"]["choice_neg"]
d_ptrue = abs(pn["noul"] - px["noul"])
identical = abs(pn["noul"] - px["noul"]) == 0.0  # noul answers carry a single scalar, not a distribution
choice_pos_ok = cp["choice"] == "4"
choice_neg_ok = cx["choice"] == "5"
choice_same = cp["choice"] == cx["choice"]

if identical:
    verdict = "NON-DISCRIMINATING-DEGENERATE"
elif d_ptrue >= 0.10 and pn["noul"] > px["noul"] and (choice_pos_ok or choice_neg_ok):
    verdict = "DISCRIMINATING"
elif d_ptrue < 0.10 and choice_same:
    verdict = "NON-DISCRIMINATING"
else:
    verdict = "PARTIAL"

out.update({
    "d_ptrue": round(d_ptrue, 6),
    "noul_identical_distribution": identical,
    "choice_pos_ok": choice_pos_ok,
    "choice_neg_ok": choice_neg_ok,
    "choice_argmax_same": choice_same,
    "verdict": verdict,
    "pre_reg": "proposals/runs/QC-JEV-discriminating-control.md",
    "runner_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
})
os.makedirs("results/qc_jev_control", exist_ok=True)
with open("results/qc_jev_control/results.json", "w") as f:
    json.dump(out, f, indent=2, sort_keys=True)
print("VERDICT:", verdict)
