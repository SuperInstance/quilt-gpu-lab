#!/usr/bin/env python3
"""repro_blindspots.py — minimal per-shape reproduction of the exp015
self-play grader's three 0.00 shapes.

For each shape we (a) synthesize the mutation with the instrument's own
synthesizer, (b) load pristine + mutated kernels side by side, (c) show
the observable the battery *could* look at, and (d) show the observable
the battery actually pins.  CPU only, no writes outside this dir.
"""
from __future__ import annotations
import importlib.util, json, random, sys, tempfile
from math import cos, sin
from pathlib import Path

REPO = Path(__file__).resolve().parent / "repo"
SRC = (REPO / "micromoth.py").read_text()
sys.path.insert(0, str(REPO / "tools"))
import selfplay  # noqa: E402  (SHAPES + synthesize)

def load(name: str, src: str):
    td = Path(tempfile.mkdtemp(prefix=f"k_{name}_"))
    (td / "micromoth.py").write_text(src)
    spec = importlib.util.spec_from_file_location(f"{name}_micromoth", td / "micromoth.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def synth(shape: str, vidx: int = 0):
    mut, desc = selfplay.synthesize(SRC, shape, vidx)
    return mut, desc

P = load("pristine", SRC)
out: dict = {}

# ------------------------------------------------------------------ (1) phase_sign_flip
mut, desc = synth("phase_sign_flip")
M = load("phase", mut)
r = {}
# rz on |0>: statevector is the only output that keeps the complex phase
qc_p, qc_m = P.QuantumCircuit(1), M.QuantumCircuit(1)
qc_p.rz(0.7, 0); qc_m.rz(0.7, 0)
r["desc"] = desc
r["statevector_pristine"] = P.simulate(qc_p, get="statevector")
r["statevector_mutated"] = M.simulate(qc_m, get="statevector")
r["statevector_differs"] = r["statevector_pristine"] != r["statevector_mutated"]
r["probs_pristine"] = P.simulate(qc_p, get="probabilities_dict")
r["probs_mutated"] = M.simulate(qc_m, get="probabilities_dict")
r["probs_identical"] = r["probs_pristine"] == r["probs_mutated"]
# bell + rz: does any *measured* statistic move?
def bell_rz(mod):
    qc = mod.QuantumCircuit(2, 2); qc.h(0); qc.cx(0, 1); qc.rz(0.7, 0)
    qc.measure(0, 0); qc.measure(1, 1); return qc
r["bell_rz_counts_identical_seed42"] = (lambda: (random.seed(42), P.simulate(bell_rz(P), shots=4096, get="counts"))[1] == (random.seed(42), M.simulate(bell_rz(M), shots=4096, get="counts"))[1])()
r["battery_has_statevector_after_rz"] = "rz(0.7" in (REPO / "tests/test_cell_mapping.py").read_text() and "get=\"statevector\"" in (REPO / "tests/test_cell_mapping.py").read_text()
out["phase_sign_flip"] = r

# ------------------------------------------------------------------ (2) noise_mixing_swap
mut, desc = synth("noise_mixing_swap")
M2 = load("noise", mut)
r = {"desc": desc}
# asymmetric single-qubit circuit: rx(0.6) -> probs [cos^2(0.3), sin^2(0.3)]
def rx_meas(mod):
    qc = mod.QuantumCircuit(1, 1); qc.rx(0.6, 0); qc.measure(0, 0); return qc
pp = P.simulate(rx_meas(P), get="probabilities_dict", noise_model=[0.1])
pm = M2.simulate(rx_meas(M2), get="probabilities_dict", noise_model=[0.1])
r["asym_pristine"] = pp; r["asym_mutated"] = pm
r["asym_differs"] = pp != pm
r["mutated_is_bit_relabel"] = pm == {"0": pp["1"], "1": pp["0"]}
# the battery's noise circuit is a Bell state -> p(0)==p(1) -> symmetric
def bell(mod):
    qc = mod.QuantumCircuit(2, 2); qc.h(0); qc.cx(0, 1)
    qc.measure(0, 0); qc.measure(1, 1); return qc
bp = P.simulate(bell(P), get="probabilities_dict", noise_model=[0.1, 0.1])
bm = M2.simulate(bell(M2), get="probabilities_dict", noise_model=[0.1, 0.1])
r["bell_pristine"] = bp; r["bell_mutated"] = bm; r["bell_identical"] = bp == bm
r["collapse_ledger_noise_uses_bell"] = "bell()" in (REPO / "tests/test_collapse_ledger.py").read_text() and "noise_model=0.1" in (REPO / "tests/test_collapse_ledger.py").read_text()
out["noise_mixing_swap"] = r

# ------------------------------------------------------------------ (3) comparison_flip
mut, desc = synth("comparison_flip")
M3 = load("cmp", mut)
r = {"desc": desc}
# 3a. equivalence in the battery's input domain: r is continuous -> P(r==cumu)=0
def counts(mod, seed, shots=512):
    random.seed(seed)
    return mod.simulate(bell(mod), shots=shots, get="counts")
same = all(counts(P, s) == counts(M3, s) for s in range(40))
r["counts_identical_over_40_seeds"] = same
# 3b. the flip is a REAL semantic change, but only on the exact boundary.
#     Inject r == cumu (the value the sampler compares against) for both kernels.
target = P.simulate(bell(P), get="probabilities_dict")  # {'00':.5,'11':.5}
cumu_boundary = target["00"]  # 0.5 — a cumulative partial sum for index j=0
def probe(mod):
    real = mod.random.random
    seq = [cumu_boundary]  # first draw lands exactly on the boundary
    mod.random.random = lambda: seq.pop(0) if seq else 0.99
    try:
        got = mod.simulate(bell(mod), shots=1, get="memory")
    finally:
        mod.random.random = real
    return got
r["boundary_pristine"] = probe(P)   # '<' -> 0.5 not accepted at j=0, accepted at j=3
r["boundary_mutated"] = probe(M3)   # '<=' -> 0.5 accepted at j=0
r["boundary_differs"] = r["boundary_pristine"] != r["boundary_mutated"]
r["battery_has_boundary_test"] = any("random.random" in f.read_text() and "cum" in f.read_text()
                                     for f in (REPO / "tests").glob("test_*.py"))
out["comparison_flip"] = r

print(json.dumps(out, indent=2, default=str))
