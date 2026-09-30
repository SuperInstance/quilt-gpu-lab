"""QG3 — landscape-trap anatomy: budget sensitivity (W/gens) + champion-basin clustering.
Pre-reg: proposals/runs/QG3-trap-anatomy.md. Exact arm only (shot==exact per QG2)."""
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

def mutate_draw(champ_seq, champ_len, rng, W):
    S = champ_len.shape[0]; C = 15
    cseq = np.repeat(champ_seq[:,None,:], C, axis=1).copy()
    clen = champ_len[:,None].repeat(C, 1).copy()
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

def run_lane(S, W, gens, seed, bar=0.45):
    LIB = make_lib()
    rng = np.random.default_rng(seed)
    seq = np.full((S, W), PAD, dtype=np.int64); seq[:,0] = TEMPLATES.index([["h",0]]); seq[:,1] = TEMPLATES.index([["cx",0,1]])
    L = np.full(S, 2, dtype=np.int64)
    v = exact_balance(torch.tensor(seq), LIB, W).double()
    champ_v = v.clone(); crossed_gen = np.full(S, -1)
    for g in range(gens):
        cseq, cl = mutate_draw(seq, L, rng, W)
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
            "final_v": champ_v.numpy(), "champions": [seq[i,:int(L[i])].tolist() for i in range(S)]}

def lev(a, b):
    m, n = len(a), len(b)
    if m == 0 or n == 0: return max(m, n)
    prev = list(range(n+1))
    for i in range(1, m+1):
        cur = [i] + [0]*n
        ai = a[i-1]
        for j in range(1, n+1):
            cur[j] = min(prev[j]+1, cur[j-1]+1, prev[j-1] + (ai != b[j-1]))
        prev = cur
    return prev[n]

def single_linkage(seqs, thr=2, cap=400):
    """Greedy single-linkage basins on first `cap` seqs (pairwise Levenshtein O(n^2))."""
    n = min(len(seqs), cap)
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(n):
        for j in range(i+1, n):
            if lev(seqs[i], seqs[j]) <= thr:
                ri, rj = find(i), find(j)
                if ri != rj: parent[ri] = rj
    from collections import Counter
    sizes = Counter(find(i) for i in range(n))
    return len(sizes), sizes.most_common(5), n

def cp_ci(k, n, a=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(a/2, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(1-a/2, k+1, n-k)
    return lo, hi

if __name__ == "__main__":
    t0 = time.time()
    # G3 anchor
    LIB = make_lib()
    rng = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng.integers(0, PAD)][0] for _ in range(rng.integers(1, 7))] for _ in range(50)]
    ref = evaluate(gsets, device="cpu")
    GID = {repr(g[0]): i for i, g in enumerate(TEMPLATES)}
    mine = exact_balance(torch.tensor([[GID[repr(gate)] if i < len(g) else PAD for i, gate in enumerate(g)] + [PAD]*(6-len(g)) for g in gsets]), LIB, 6)
    err = max(abs(mine[j].item() - ref[j]["balance"]) for j in range(50))
    print(f"ANCHOR-VEC: max|diff|={err:.2e} pass={err<1e-9}", flush=True)
    assert err < 1e-9, "G3 ANCHOR FAIL"

    S = 1024
    print("arm A: W=6 gens=12 ...", flush=True)
    A = run_lane(S, 6, 12, seed=1234)
    print(f"  crossed {A['crossed'].sum()}/{S}  ({time.time()-t0:.0f}s)", flush=True)
    print("arm B: W=8 gens=24 ...", flush=True)
    B = run_lane(S, 8, 24, seed=4321)
    print(f"  crossed {B['crossed'].sum()}/{S}  ({time.time()-t0:.0f}s)", flush=True)

    # G1 budget gate
    kA, nA = int(A["crossed"].sum()), S
    kB, nB = int(B["crossed"].sum()), S
    lA, hA = cp_ci(kA, nA); lB, hB = cp_ci(kB, nB)
    d_lo = lB - hA  # conservative lower bound on difference
    print(f"G1: A={kA/nA:.3f} [{lA:.3f},{hA:.3f}]  B={kB/nB:.3f} [{lB:.3f},{hB:.3f}]  delta_lb={d_lo:+.3f}", flush=True)

    # G2 basins: stuck champions, arm A (baseline stuck set) and B
    out = {"anchor_vec_err": err, "armA": {"crossed": kA/nA, "ci": [lA,hA]},
           "armB": {"crossed": kB/nB, "ci": [lB,hB]}, "delta_lb": d_lo}
    for name, R in [("A", A), ("B", B)]:
        stuck = [c for c, x in zip(R["champions"], R["crossed"]) if not x]
        nb, top, n_used = single_linkage(stuck, thr=2)
        # null: random genomes matched length distribution
        rng2 = np.random.default_rng(999)
        lens = [len(s) for s in stuck]
        null = [rng2.integers(0, PAD, size=l).tolist() for l in lens]
        nb0, top0, _ = single_linkage(null, thr=2)
        out[f"basins_{name}"] = {"n_stuck": len(stuck), "n_basins": nb, "top5": [(r, s) for r, s in top],
                                 "null_basins": nb0, "null_top5": [(r, s) for r, s in top0]}
        print(f"basins {name}: n_stuck={len(stuck)} basins={nb} top={top[:3]}")
        print(f"          null: basins={nb0} top={top0[:3]}", flush=True)

    json.dump(out, open("results/qg3_trap_anatomy/results.json", "w"), indent=1)
    print(f"DONE {time.time()-t0:.0f}s")
