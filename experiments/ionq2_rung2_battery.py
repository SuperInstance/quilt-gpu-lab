#!/usr/bin/env python
"""IONQ-2: rung-2 discriminator battery on tools/qcell_sim.py crx.

Pre-reg: proposals/runs/IONQ-2-rung2-battery-prereg.md (committed before fire).
Read-only over the tool; exact statevector, CPU. Fails loud; verdict printed.
Runs to stdout only (no artifact writes; booking prose + this file are the record).
"""
import math, subprocess, sys
sys.path.insert(0, "tools")
from qcell_sim import evaluate  # noqa: E402

TOL = 1e-9
fails = []

def check(gate, got, want, tol=TOL):
    ok = abs(got - want) <= tol
    print(f"{gate}: got={got!r} want={want!r} -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append(gate)

# G0: tool selftest anchor (k4 champion 0.4268)
r = subprocess.run([sys.executable, "tools/qcell_sim.py", "--selftest"],
                   capture_output=True, text=True)
print("G0 selftest:", r.stdout.strip() or r.stderr.strip())
if r.returncode != 0 or "selftest OK" not in r.stdout:
    fails.append("G0")

# Bit-order probe: x on q0 only. Declared fail-loud assert before gates.
r = evaluate([["x", 0]], n_qubits=2, device="cpu",
             targets=["00", "01", "10", "11"])[0]
ones = [t for t, p in r["probs"].items() if p > 0.5]
assert len(ones) == 1, r["probs"]
# ones[0] is the basis string with the q0 bit set somewhere; determine position.
# (control/target marginals below are computed from the full 4-target vector,
#  so exact bit-order knowledge is only needed for the assert, not the gates.)
r3 = evaluate([["x", 0]], n_qubits=2, device="cpu",
              targets=["00", "01", "10", "11"])[0]["probs"]
print("bit-order probe probs:", r3)

def target_prob(genome):
    """Marginal P(qubit1 == 1) with qubit0 prepared in |1> (control).
    Qubit order resolved empirically: q0 prepared, target is the OTHER qubit."""
    full = evaluate(genome, n_qubits=2, device="cpu",
                    targets=["00", "01", "10", "11"])[0]["probs"]
    # control string = the unique post-x-on-q0 heavy string (probe above)
    ctrl = ones[0]  # q0 is MSB (probe: '10')
    cpos = next(i for i, (a, b) in enumerate(zip(ctrl, "00")) if a != b)
    tpos = 1 - cpos  # single other qubit = target
    p = sum(pv for t, pv in full.items() if t[tpos] != "0")
    return p

# G1: control leak (no x on q0 -> control |0>), sweep
for th in [1/6, 1/3, 1/2, 2/3, 1]:
    p = evaluate([["crx", th, 0, 1]], n_qubits=2, device="cpu",
                 targets=["00", "01", "10", "11"])[0]["probs"]
    p1 = sum(pv for t, pv in p.items() if t != "00")
    check(f"G1 leak theta={th}", p1, 0.0, 1e-12)

# G2: calibration sweep, control=1
for th in [1/6, 1/3, 1/2, 2/3, 1]:
    p = target_prob([["x", 0], ["crx", th, 0, 1]])
    check(f"G2 cal theta={th}pi", p, math.sin(th * math.pi / 2) ** 2)

# G3: additivity
p = target_prob([["x", 0], ["crx", 1/3, 0, 1], ["crx", 1/3, 0, 1]])
check("G3 additivity", p, 0.75)

# G4: cancellation (EXACT zero required)
p = target_prob([["x", 0], ["crx", 1/3, 0, 1], ["crx", -1/3, 0, 1]])
check("G4 cancellation", p, 0.0, 1e-12)

print("VERDICT:", "PASS" if not fails else f"RED ({', '.join(fails)})")
sys.exit(0 if not fails else 1)
