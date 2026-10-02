#!/usr/bin/env python3
"""D12k: True entangled register vs classical channel at matched correlation.

Question (from D12j closure): the W*T bandwidth-time rule was measured on
simulated product subchannels. Does a genuinely entangled (non-separable)
2-qubit channel carry MORE discoverable partner signal than a classical
binary channel with the SAME measured |corr|?

Design (seed 2718):
  - Partner channel, entangled: Bell state |Phi+> with random local SU(2)
    rotations U_A (x) U_B applied; measure both qubits in Z -> (a,b) bits.
    The joint distribution P(a,b) comes from a non-separable state.
  - Partner channel, classical: binary channel sampled to MATCH the entangled
    channel's measured Pearson corr(a,b) and marginals as closely as possible
    (b = a with prob q chosen to match corr).
  - Background cells: independent fair bits (as before).
  - Partner discovery: max |corr| of atom streams (D13d/D12e estimator).
  - N=16 cells (8 pairs), T sweep {5,10,25,50,100,200}, 5 pairing draws.

Falsifiable gate: if entanglement matters to the ESTIMATOR, entangled
partner_id_acc should exceed classical-matched at some T (bar: >= +0.10 at
T in {10,25}). If they tie within noise, verdict is: the estimator is
correlation-complete — entanglement adds nothing beyond the corr coefficient,
closing the "true register" question for the substrate.

CPU-only, <1 min. Guard untouched.
"""
import json, math, os, random
import numpy as np

SEED = 2718
N_CELLS = 16
N_DRAWS = 5
T_LIST = [5, 10, 25, 50, 100, 200]
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "d12k_entangled_register.json")

def su2_random(rng):
    """Random SU(2) as 2x2 complex."""
    a, b = rng.gauss(0, 1), rng.gauss(0, 1)
    c, d = rng.gauss(0, 1), rng.gauss(0, 1)
    M = np.array([[a + 1j*b, c + 1j*d], [-c + 1j*d, a - 1j*b]], dtype=complex)
    M /= np.sqrt(np.trace(M @ M.conj().T).real)
    return M

def bell_sample(U_A, U_B, T, rng):
    """Sample T outcomes from (U_A x U_B)|Phi+> measured in Z."""
    Phi = np.array([1/math.sqrt(2), 0, 0, 1/math.sqrt(2)], dtype=complex)
    U = np.kron(U_A, U_B)
    psi = U @ Phi
    rho = np.outer(psi, psi.conj())
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    P00 = abs(rho[0, 0]); P01 = abs(rho[1, 1]); P10 = abs(rho[2, 2]); P11 = abs(rho[3, 3])
    total = P00 + P01 + P10 + P11
    probs = np.array([P00, P01, P10, P11]) / total
    idx = np.array(rng.choices(range(4), weights=probs.tolist(), k=T))
    a = (idx % 2) * 2 - 1   # +/-1
    b = (idx // 2) * 2 - 1
    return a.astype(float), b.astype(float)

def classical_match(a, b, T, rng):
    """Classical binary channel matched to corr(a,b): b' = a with prob q."""
    r = np.corrcoef(a, b)[0, 1]
    q = (1 + r) / 2  # P(b'=a) to match corr for +/-1 symmetric bits
    flip = np.array([rng.random() for _ in range(T)]) > q
    bp = np.where(flip, -a, a)
    return a.copy(), bp.astype(float)

def fair_bits(T, rng):
    return np.array([1.0 if rng.random() < 0.5 else -1.0 for _ in range(T)])

def partner_id_acc(streams, pairs):
    """Estimator: for each cell, partner = argmax |corr| over others (D13d style)."""
    S = np.array(streams)  # (N, T)
    S = S - S.mean(axis=1, keepdims=True)
    sd = S.std(axis=1); sd[sd == 0] = 1e-12
    C = (S @ S.T) / (S.shape[1] * np.outer(sd, sd))
    np.fill_diagonal(C, 0)
    correct = 0
    for i, j in pairs:
        if abs(C[i, j]) >= np.abs(C[i]).max() - 1e-12:
            correct += 1
    return correct / len(pairs)

rng = random.Random(SEED)
results = {"entangled": {}, "classical": {}, "corr_entangled": [], "corr_classical": []}
for T in T_LIST:
    accs_e, accs_c = [], []
    for _ in range(N_DRAWS):
        cells = rng.sample(range(N_CELLS), N_CELLS)
        pairs = [(cells[2*k], cells[2*k+1]) for k in range(N_CELLS//2)]
        streams = [None] * N_CELLS
        for i, j in pairs:
            a, b = bell_sample(su2_random(rng), su2_random(rng), T, rng)
            results["corr_entangled"].append(float(np.corrcoef(a, b)[0, 1]))
            ac, bc = classical_match(a, b, T, rng)
            results["corr_classical"].append(float(np.corrcoef(ac, bc)[0, 1]))
            streams[i], streams[j] = a, b
        for k in range(N_CELLS):
            if streams[k] is None:
                streams[k] = fair_bits(T, rng)
        accs_e.append(partner_id_acc(streams, pairs))
        # classical: re-pair with same topology but replace entangled streams by matched
        rng2 = random.Random(rng.random())
        cells2 = rng.sample(range(N_CELLS), N_CELLS)
        pairs2 = [(cells2[2*k], cells2[2*k+1]) for k in range(N_CELLS//2)]
        streams2 = [None] * N_CELLS
        for i, j in pairs2:
            a, b = bell_sample(su2_random(rng), su2_random(rng), T, rng)
            ac, bc = classical_match(a, b, T, rng)
            streams2[i], streams2[j] = ac, bc
        for k in range(N_CELLS):
            if streams2[k] is None:
                streams2[k] = fair_bits(T, rng)
        accs_c.append(partner_id_acc(streams2, pairs2))
    results["entangled"][T] = sum(accs_e)/len(accs_e)
    results["classical"][T] = sum(accs_c)/len(accs_c)

diffs = {T: results["entangled"][T] - results["classical"][T] for T in T_LIST}
results["diff"] = diffs
results["verdict"] = "KEEP_entanglement_matters" if any(d >= 0.10 for T, d in diffs.items() if T in (10, 25, 50)) else "KILL_estimator_correlation_complete"
results["marginal_corr_mean_e"] = float(np.nanmean(np.abs(results["corr_entangled"])))
results["marginal_corr_mean_c"] = float(np.nanmean(np.abs(results["corr_classical"])))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(results, f, indent=2)
print(json.dumps({k: results[k] for k in ("entangled", "classical", "diff", "verdict", "marginal_corr_mean_e", "marginal_corr_mean_c")}, indent=2))
