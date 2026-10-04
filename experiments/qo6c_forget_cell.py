"""QO6c experiment driver — forget_cell v2 gates G1-G4 (pre-reg proposals/runs/QO6c-forget-cell-v2.md).

Deterministic: sha256 chain + fixed seed 424242 for synthetic witness series only.
Writes results/qo6c_forget_cell_v2/results.json. Fail-loud; no re-roll.
"""
import copy
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from forget_cell import ForgetCell  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results", "qo6c_forget_cell_v2")
os.makedirs(OUT, exist_ok=True)

gates = {}


def gate(name, cond, detail=""):
    gates[name] = {"pass": bool(cond), "detail": detail}


# --- build a small honest ledger: 3 witness shots + QO6-style keep/kill reasons
rng = np.random.default_rng(424242)
cell = ForgetCell()
ids = {}
for shot, mu in [("late-bloomer-E581", 0.02), ("hopeless-D07", -0.15), ("control-K2", 0.0)]:
    series = list(np.cumsum(rng.normal(mu, 1.0, 24)))
    ids[shot] = cell.append(shot, "witness", {"claim": "DECREASES", "sigma": 1.0,
                                              "series": [round(float(x), 6) for x in series]})

# honest forget of the hopeless shot (v2: witness bytes untouched)
forgotten = cell.forget("hopeless-D07", "QO6 KILL_CANDIDATE: E final below bar at T=24")

# G1 tamper-evidence through erasure
c1 = copy.deepcopy(cell)
c1.witness_receipt("hopeless-D07")["payload"]["sigma"] = 0.9
g1a = c1.verify()
c2 = copy.deepcopy(cell)
for r in c2.receipts:
    if r["kind"] == "FORGET":
        r["payload"]["reason"] = "tampered reason"
g1b = c2.verify()
gate("G1", g1a["verdict"] == "TAMPERED" and g1b["verdict"] == "TAMPERED",
     f"witness-tamper->{g1a}; forget-tamper->{g1b}")

# G2 erased_id diff (honest forget): v2 rederive reads the UNTOUCHED witness bytes
rederived, erased_id = cell.rederive("hopeless-D07")
gate("G2a", rederived == erased_id, f"rederive {rederived[:16]} vs erased_id {erased_id[:16]}")

# G2b: attacker re-seals a FORGET with a WRONG erased_id -> caught by rederive
c3 = copy.deepcopy(cell)
wf = next(r for r in c3.receipts if r["kind"] == "FORGET")
wf["payload"]["erased_id"] = "0" * 64
base = {k: wf[k] for k in wf if k != "digest"}
wf["digest"] = hashlib.sha256(json.dumps(base, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
try:
    rd, _ = c3.rederive("hopeless-D07")
    g2b = rd != wf["payload"]["erased_id"]
except ValueError:
    g2b = True
gate("G2b", g2b, "wrong erased_id (attacker re-sealed) caught by rederive diff")
gate("G2", gates["G2a"]["pass"] and g2b)

# G3 non-wedge (canvas-tui trapdoor) — THE gate QO6b failed
v_after = cell.verify()  # must be VERIFIED, not exception
new_id = cell.append("post-forge-witness", "witness", {"claim": "INCREASES", "sigma": 1.0})
v_re = cell.verify()
gate("G3", v_after["verdict"] == "VERIFIED" and v_re["verdict"] == "VERIFIED"
     and isinstance(new_id, str) and len(new_id) == 64,
     f"verify-after-forget {v_after}; append-then-verify {v_re}")
gate("G3b", ForgetCell().verify()["verdict"] == "VERIFIED", "empty ledger VERIFIED")

# G4 fail-first pins
def raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True

g4 = (raises(lambda: cell.forget("no-such-shot", "r"))
      and raises(lambda: cell.forget("hopeless-D07", "double"))
      and raises(lambda: cell.append("", "witness", {}))
      and raises(lambda: cell.append("no-kind", "", {}))
      and raises(lambda: cell.append("hopeless-D07", "witness", {})))
gate("G4", g4, "unknown-forget/double-forget/empty-shot/empty-kind/append-under-erased all raise")

verdict = "PASS" if all(g["pass"] for g in gates.values()) else "FAIL"
result = {"verdict": verdict, "gates": gates, "pre_reg": "proposals/runs/QO6c-forget-cell-v2.md",
          "n_receipts_final": len(cell.receipts)}
with open(os.path.join(OUT, "results.json"), "w") as f:
    json.dump(result, f, indent=2, sort_keys=True)
print(json.dumps(result, indent=2, sort_keys=True))
if verdict == "FAIL":
    sys.exit(1)
