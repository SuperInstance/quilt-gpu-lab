"""QG6 — variance rescue: bigger move-set (k mutation applications/child) at FIXED total children.
Pre-reg: proposals/runs/QG6-variance-rescue.md. Lane copied verbatim from experiments/qg3_trap_anatomy.py
(declared inheritance); mutate_draw extended by k parameter only."""
import sys, json, time, numpy as np, torch
sys.path.insert(0, "tools")
from qcell_sim import genome_unitary, evaluate

ANG = [0.25, 0.5, 0.75, 1.0]
PAIRS = [(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
TEMPLATES = ([[["h",q]] for q in range(3)] + [[["x",q]] for q in range(3)]
  + [[["rx",t,q]] for t in ANG for q in range(3)] + [[["rz",t,q]] for t in ANG for q in range(3)]
  + [[["cx",a,b]] for a,b in PAIRS] + [[["crx",t,a,b]] for t in ANG for a,b in PAIRS]
  + [[["swap",a,b]] for a,b in PAIRS])
PAD = len(TEMPLATES)
DEV = "cuda"

def make_lib():
    return torch.stack([genome_unitary(g, 3, torch) for g in TEMPLATES]
                       + [torch.eye(8, dtype=torch.complex128)]).to(DEV)

def exact_balance(seqs, LIB, W):
    Ms = LIB[seqs.to(DEV)]
    U = torch.eye(8, dtype=torch.complex128, device=DEV).expand_as(Ms[:,0]).clone()
    for i in range(W): U = torch.bmm(Ms[:,i], U)
    s = U @ torch.tensor([1.,0,0,0,0,0,0,0], dtype=torch.complex128, device=DEV)
    return torch.minimum(s[:,0].abs()**2, s[:,7].abs()**2).cpu()

def _one_mut_round(cseq, clen, rng, W):
    """Single mutation application per child (QG3 kernel, one op per child)."""
    S, C = clen.shape
    ops = rng.integers(0, 2, size=(S, C)); sub = rng.integers(0, 2, size=(S, C))
    posf = rng.random((S, C)); gates = rng.integers(0, PAD, size=(S, C))
    for s in range(S):
        for c in range(C):
            L = int(clen[s, c]); op = ops[s, c]
            if op == 0:
                pos = int(posf[s, c] * L); cseq[s, c, pos] = gates[s, c]
            else:
                ins = (L < W) and (sub[s, c] == 0 or L <= 1)
                if ins:
                    pos = int(posf[s, c] * (L + 1))
                    cseq[s, c, pos+1:L+1] = cseq[s, c, pos:L]; cseq[s, c, pos] = gates[s, c]; clen[s, c] = L + 1
                elif L > 1:
                    pos = int(posf[s, c] * L)
                    cseq[s, c, pos:L-1] = cseq[s, c, pos+1:L]; cseq[s, c, L-1] = PAD; clen[s, c] = L - 1
                else:
                    pos = int(posf[s, c] * L); cseq[s, c, pos] = gates[s, c]
    return cseq, clen

def mutate_draw(champ_seq, champ_len, rng, W, k=1):
    """k independent mutation applications per child; total children C=15 FIXED."""
    S = champ_len.shape[0]; C = 15
    cseq = np.repeat(champ_seq[:,None,:], C, axis=1).copy()
    clen = champ_len[:,None].repeat(C, 1).copy()
    for _ in range(k):
        cseq, clen = _one_mut_round(cseq, clen, rng, W)
    return cseq, clen

def run_lane(S, W, gens, seed, bar=0.45, k=1):
    LIB = make_lib()
    rng = np.random.default_rng(seed)
    seq = np.full((S, W), PAD, dtype=np.int64); seq[:,0] = TEMPLATES.index([["h",0]]); seq[:,1] = TEMPLATES.index([["cx",0,1]])
    L = np.full(S, 2, dtype=np.int64)
    v = exact_balance(torch.tensor(seq), LIB, W).double()
    champ_v = v.clone(); crossed_gen = np.full(S, -1)
    for g in range(gens):
        cseq, cl = mutate_draw(seq, L, rng, W, k=k)
        ct = torch.tensor(cseq.reshape(S*15, W))
        e = exact_balance(ct, LIB, W).reshape(S, 15)
        F = torch.cat([v.reshape(-1,1), e], dim=1)
        fmax = F.max(dim=1).values
        key = torch.rand(F.shape)
        pick = torch.where(F == fmax[:,None], key, torch.tensor(-1.0)).argmax(dim=1)
        cseq_t = torch.cat([torch.tensor(seq)[:,None,:], torch.tensor(cseq)], dim=1)
        clen_t = torch.cat([torch.tensor(L)[:,None], torch.tensor(cl)], dim=1)
        ar = torch.arange(S)
        bseq, blen, btrain = cseq_t[ar,pick], clen_t[ar,pick], F[ar,pick]
        promote = (btrain >= champ_v)
        seq = np.where(promote[:,None].numpy(), bseq.numpy(), seq)
        L = np.where(promote.numpy(), blen.numpy(), L)
        v = torch.where(promote, btrain, v).double(); champ_v = v.clone()
        just = (champ_v.numpy() >= bar) & (crossed_gen < 0); crossed_gen[just] = g
    return {"crossed": (champ_v.numpy() >= bar), "crossed_gen": crossed_gen,
            "final_v": champ_v.numpy()}

def cp_ci(kk, n, a=0.05):
    from scipy.stats import beta
    lo = 0.0 if kk == 0 else beta.ppf(a/2, kk, n-kk+1)
    hi = 1.0 if kk == n else beta.ppf(1-a/2, kk+1, n-kk)
    return lo, hi

if __name__ == "__main__":
    t0 = time.time()
    # G1 ANCHOR (same as QG3)
    LIB = make_lib()
    rng = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng.integers(0, PAD)][0] for _ in range(rng.integers(1, 7))] for _ in range(50)]
    ref = evaluate(gsets, device="cpu")
    GID = {repr(g[0]): i for i, g in enumerate(TEMPLATES)}
    mine = exact_balance(torch.tensor([[GID[repr(gate)] if i < len(g) else PAD for i, gate in enumerate(g)] + [PAD]*(6-len(g)) for g in gsets]), LIB, 6)
    err = max(abs(mine[j].item() - ref[j]["balance"]) for j in range(50))
    print(f"ANCHOR-VEC: max|diff|={err:.2e} pass={err<1e-9}", flush=True)
    assert err < 1e-9, "G6 ANCHOR FAIL"

    S = 1024; out = {"anchor_vec_err": err, "arms": {}}
    res = {}
    for k in (1, 2, 3):
        print(f"arm k={k}: W=6 gens=12 S={S} ...", flush=True)
        R = run_lane(S, 6, 12, seed=1234, k=k)
        kk = int(R["crossed"].sum()); lo, hi = cp_ci(kk, S)
        cg = R["crossed_gen"][R["crossed_gen"] >= 0]
        cgmed = float(np.median(cg)) if len(cg) else -1.0
        res[k] = R
        out["arms"][str(k)] = {"crossed": kk/S, "ci": [lo, hi], "crossed_gen_median": cgmed,
                               "crossed_gen_hist": {str(int(g)): int((cg == g).sum()) for g in np.unique(cg)}}
        print(f"  k={k}: crossed {kk}/{S} = {kk/S:.3f} [{lo:.3f},{hi:.3f}]  med_gen={cgmed}  ({time.time()-t0:.0f}s)", flush=True)

    # G2 REPLICATE gate: k=1 must be inside QG3 arm A CP95 [0.547,0.609] (+-0.006 band)
    r1 = out["arms"]["1"]["crossed"]
    rep_ok = 0.547 - 0.006 <= r1 <= 0.609 + 0.006
    out["replicate_gate"] = {"k1_rate": r1, "window": [0.541, 0.615], "pass": bool(rep_ok)}
    print(f"G2 REPLICATE: k1={r1:.3f} in [0.541,0.615]? {'PASS' if rep_ok else 'FAIL'}", flush=True)

    # deltas vs k=1 (conservative lower bounds)
    l1, h1 = out["arms"]["1"]["ci"]
    for k in (2, 3):
        lk, hk = out["arms"][str(k)]["ci"]
        out[f"delta_lb_k{k}_vs_k1"] = lk - h1
        print(f"delta_lb k={k} vs k=1: {lk - h1:+.3f}", flush=True)

    json.dump(out, open("results/qg6_variance_rescue/results.json", "w"), indent=1)
    print(f"GATE {'PASS' if rep_ok else 'FAIL'} — {'continuing to booking' if rep_ok else 'STOP per pre-reg'}")
    print(f"DONE {time.time()-t0:.0f}s")
