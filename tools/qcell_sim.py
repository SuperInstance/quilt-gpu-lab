#!/usr/bin/env python3
"""qcell-sim — exact small-circuit cell evaluator (one named tool, cell-slot ready).

WHAT: batched statevector evaluator for qcell genomes (n<=12 qubits) on the GPU.
Answers, exactly and in one call: p(target strings), balance, and (optionally) shot samples with a receipt.

CALIBRATED CONVENTIONS (reverse-engineered from MicroMoth-quilt exp020-022 receipts, anchor 0.9854
against 960 recorded cells; see proposals/runs/QG1-exact-census.md):
  * fitness readout  = min(p000, p111)          ("balance": GHZ -> 0.5, deterministic |000> -> 0.0)
  * gate angles      = units of pi               (rx(0.5, q) means Rx(pi/2))
      -- this is the calibration cut (delta-shape D10): ratios exact, only the unit label drifts.
  * qubit indexing   = q0 is the MSB of the target bitstring
  * gate set         = h, x, rx(theta,q), rz(theta,q), cx(c,t), crx(theta,c,t), swap(a,b)
                       (crx = controlled-RX: RX(theta) on target t iff control c is 1)
  * rz is phase-only -> invisible to the balance observable; carried for fidelity of the artifact.

USAGE
  python qcell_sim.py --genome '[["h",0],["cx",0,2],["cx",0,1]]' --shots 512
  python qcell_sim.py --genomes-file genomes.json --shots 512 --receipt out.json
  python qcell_sim.py --selftest
IMPORT
  from qcell_sim import evaluate
  evaluate([["h",0],["cx",0,1]], n_qubits=3, shots=512, seed=101) -> dict
"""
import json, math, argparse, hashlib

def _torch():
    import torch
    return torch

def _embed(U, q, n, torch):
    I = torch.eye(2, dtype=torch.complex128)
    parts = [U if i == q else I for i in range(n)]
    M = parts[0]
    for p in parts[1:]:
        M = torch.kron(M, p)
    return M

def _apply_bit_perm(pairs, n, torch):
    """pairs = [(control,target), ...] applied as XOR flips; returns the 2^n permutation matrix."""
    N = 1 << n
    P = torch.zeros(N, N, dtype=torch.complex128)
    for s in range(N):
        b = [(s >> (n - 1 - i)) & 1 for i in range(n)]
        for c, t in pairs:
            b[t] ^= b[c]
        idx = 0
        for bit in b:
            idx = (idx << 1) | bit
        P[idx, s] = 1
    return P

def _rx(theta, torch):
    return torch.tensor([[complex(math.cos(theta/2), 0), complex(0, -math.sin(theta/2))],
                         [complex(0, -math.sin(theta/2)), complex(math.cos(theta/2), 0)]], dtype=torch.complex128)

def _rz(theta, torch):
    return torch.tensor([[complex(math.cos(theta/2), -math.sin(theta/2)), 0],
                         [0, complex(math.cos(theta/2), math.sin(theta/2))]], dtype=torch.complex128)

def genome_unitary(genome, n, torch):
    N = 1 << n
    M = torch.eye(N, dtype=torch.complex128)
    for g in genome:
        name = g[0]
        if name == "h":
            M = _embed(torch.tensor([[1,1],[1,-1]], dtype=torch.complex128)/math.sqrt(2), int(g[1]), n, torch) @ M
        elif name == "x":
            M = _embed(torch.tensor([[0,1],[1,0]], dtype=torch.complex128), int(g[1]), n, torch) @ M
        elif name in ("rx", "rz"):
            th, q = float(g[1]) * math.pi, int(g[2])
            M = _embed(_rx(th, torch) if name == "rx" else _rz(th, torch), q, n, torch) @ M
        elif name == "crx":
            th, c, t = float(g[1]) * math.pi, int(g[2]), int(g[3])
            U = _embed(_rx(th, torch), t, n, torch)
            P0 = torch.zeros(N, N, dtype=torch.complex128); P1 = torch.zeros(N, N, dtype=torch.complex128)
            for s in range(N):
                (P1 if (s >> (n - 1 - c)) & 1 else P0)[s, s] = 1
            M = (P0 + P1 @ U) @ M
        elif name == "crx":
            th, c, t = float(g[1]) * math.pi, int(g[2]), int(g[3])
            U = _embed(_rx(th, torch), t, n, torch)
            P0 = torch.zeros(N, N, dtype=torch.complex128); P1 = torch.zeros(N, N, dtype=torch.complex128)
            for st in range(N):
                (P1 if (st >> (n - 1 - c)) & 1 else P0)[st, st] = 1
            M = (P0 + P1 @ U) @ M
        elif name == "cx":
            M = _apply_bit_perm([(int(g[1]), int(g[2]))], n, torch) @ M
        elif name == "swap":
            a, b = int(g[1]), int(g[2])
            M = _apply_bit_perm([(a, b), (b, a)], n, torch) @ M
        else:
            raise ValueError(f"unknown gate {name!r}")
    return M

def evaluate(genomes, n_qubits=3, targets=None, shots=None, seed=None, device="cuda"):
    """Batched exact evaluation. Returns a list of per-genome dicts (JSON-safe)."""
    torch = _torch()
    if genomes and isinstance(genomes[0], dict):
        genomes = [g["genome"] for g in genomes]
    if genomes and isinstance(genomes[0][0], str):  # single genome -> list of one
        genomes = [genomes]
    targets = targets or ["0" * n_qubits, "1" * n_qubits]
    tidx = []
    for t in targets:
        i = 0
        for b in t:
            i = (i << 1) | int(b)
        tidx.append(i)
    Ms = torch.stack([genome_unitary(g, n_qubits, torch) for g in genomes]).to(device)
    e0 = torch.zeros(len(genomes), 1 << n_qubits, 1, dtype=torch.complex128, device=device)
    e0[:, 0, 0] = 1
    s = torch.bmm(Ms, e0).squeeze(-1).cpu()
    ps = [s[:, i].abs() ** 2 for i in tidx]
    stack = torch.stack(ps)
    lo = stack.min(dim=0).values.tolist(); hi = stack.max(dim=0).values.tolist()
    tot = stack.sum(dim=0).tolist()
    out = []
    for j in range(len(genomes)):
        rec = {"genome": genomes[j], "probs": {targets[k]: ps[k][j].item() for k in range(len(targets))},
               "balance": lo[j], "best_target": hi[j], "union": tot[j]}
        if shots:
            rng = torch.Generator().manual_seed(seed if seed is not None else 0)
            counts = {}
            pv = torch.tensor([ps[k][j].item() for k in range(len(targets))], dtype=torch.float64)
            pv = pv / pv.sum()
            idxs = torch.multinomial(pv, shots, replacement=True, generator=rng)
            for k, t in enumerate(targets):
                counts[t] = int((idxs == k).sum().item())
            rec["shots"] = {"n": shots, "counts": counts,
                            "shots_balance": min(counts.values()) / shots}
        out.append(rec)
    return out

def _selftest():
    r = evaluate([["h",0],["cx",0,1]], shots=512, seed=101, device="cpu")[0]
    assert abs(r["probs"]["000"] - 0.5) < 1e-9, r
    assert abs(r["balance"] - 0.0) < 1e-9, r
    r2 = evaluate([["h",0],["cx",0,2],["cx",0,1]], device="cpu")[0]
    assert abs(r2["balance"] - 0.5) < 1e-9, r2
    r3 = evaluate([["rz",0.25,0],["h",0],["cx",0,2],["cx",0,1]], device="cpu")[0]
    assert abs(r3["balance"] - 0.5) < 1e-9, r3
    r4 = evaluate([["crx",0.5,2,0]], device="cpu")[0]
    assert abs(r4["balance"] - 0.0) < 1e-9, r4   # control q2=0 -> no-op -> |000> -> balance 0
    r5 = evaluate([["h",2],["rx",0.25,0],["crx",0.5,2,0],["crx",1.0,2,1]], device="cpu")[0]
    assert abs(r5["balance"] - 0.4267578125) < 1e-3, r5  # k4 champion receipt anchor
    print("selftest OK: bell balance=0.0 (shot 0.0), GHZ balance=0.5, rz-phase balance=0.5")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="qcell-sim: exact small-circuit cell evaluator")
    ap.add_argument("--genome", type=str); ap.add_argument("--genomes-file")
    ap.add_argument("--n-qubits", type=int, default=3); ap.add_argument("--shots", type=int)
    ap.add_argument("--seed", type=int); ap.add_argument("--device", default="cuda")
    ap.add_argument("--receipt"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest(); raise SystemExit(0)
    genomes = json.load(open(a.genomes_file)) if a.genomes_file else json.loads(a.genome)
    res = evaluate(genomes, a.n_qubits, shots=a.shots, seed=a.seed, device=a.device)
    if a.receipt:
        payload = {"tool": "qcell-sim", "n_qubits": a.n_qubits, "shots": a.shots, "results": res}
        payload["receipt_id"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
        json.dump(payload, open(a.receipt, "w"), indent=1)
    for r in res:
        print(f"balance={r['balance']:.4f} best_target={r['best_target']:.4f} union={r['union']:.4f} "
              f"p={ {k: round(v,4) for k,v in r['probs'].items()} }"
              + (f" shots_balance={r['shots']['shots_balance']:.4f}" if 'shots' in r else ""))
