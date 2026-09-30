"""QG2 — desert-break law at 4096 streams. Pre-reg: proposals/runs/QG2-desert-break-law.md."""
import sys, math, json, numpy as np, torch
sys.path.insert(0, "tools")
from qcell_sim import genome_unitary  # calibrated physics (balance=min, pi-units)

ANG = [0.25, 0.5, 0.75, 1.0]
PAIRS = [(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
TEMPLATES = ([[["h",q]] for q in range(3)] + [[["x",q]] for q in range(3)]
  + [[["rx",t,q]] for t in ANG for q in range(3)] + [[["rz",t,q]] for t in ANG for q in range(3)]
  + [[["cx",a,b]] for a,b in PAIRS] + [[["crx",t,a,b]] for t in ANG for a,b in PAIRS]
  + [[["swap",a,b]] for a,b in PAIRS])
PAD = len(TEMPLATES)                       # identity
DEV = "cuda"
W = 6                                      # budget width
LIB = torch.stack([genome_unitary(g, 3, torch) for g in TEMPLATES] + [torch.eye(8, dtype=torch.complex128)]).to(DEV)

def exact_balance(seqs):
    """seqs: [B, W] int gate-id tensor -> exact balance min(p000,p111)."""
    Ms = LIB[seqs.to(DEV)]                                   # [B,W,8,8]
    U = torch.eye(8, dtype=torch.complex128, device=DEV).expand_as(Ms[:,0]).clone()
    for i in range(seqs.shape[1]): U = torch.bmm(Ms[:,i], U)
    s = U @ torch.tensor([1.,0,0,0,0,0,0,0], dtype=torch.complex128, device=DEV)
    p0, p7 = s[:,0].abs()**2, s[:,7].abs()**2
    return torch.minimum(p0, p7).cpu()

def shot_balance(seqs, shots, gen):
    bal = exact_balance(seqs)
    p = torch.stack([bal, bal], dim=1).clamp(min=1e-12)      # balance of 2-target mass? no —
    # shots land on targets with prob p000 and p111 independently; balance = min(c000,c111)/shots
    p0 = (exact_balance(seqs) * 0)  # placeholder, replaced below
    return None

def shot_counts(seqs, shots, g):
    Ms = LIB[seqs.to(DEV)]
    U = torch.eye(8, dtype=torch.complex128, device=DEV).expand_as(Ms[:,0]).clone()
    for i in range(seqs.shape[1]): U = torch.bmm(Ms[:,i], U)
    s = U @ torch.tensor([1.,0,0,0,0,0,0,0], dtype=torch.complex128, device=DEV)
    probs = s.abs()**2                                        # [B, 8] over basis states
    out = torch.empty(seqs.shape[0], dtype=torch.float64)
    CH = 8192
    for lo in range(0, seqs.shape[0], CH):
        hi = min(lo+CH, seqs.shape[0])
        idx = torch.multinomial(probs[lo:hi], shots, replacement=True, generator=torch.Generator(device=DEV).manual_seed((g * 1000003 + lo) & 0x7fffffff))  # [c, shots]
        c0 = (idx == 0).sum(1).double(); c7 = (idx == 7).sum(1).double()
        out[lo:hi] = torch.minimum(c0, c7) / shots
    return out

def skeleton_seqs(S):
    sk = [TEMPLATES.index([["h",0]]), TEMPLATES.index([["cx",0,1]])]
    seq = np.full((S, W), PAD, dtype=np.int64); seq[:,0], seq[:,1] = sk
    return seq, np.full(S, 2, dtype=np.int64)

def mutate_draw(champ_seq, champ_len, rng):
    """One generation of children for all streams. Returns cseq [S,15,W], clen [S,15]."""
    S = champ_len.shape[0]; C = 15
    cseq = np.repeat(champ_seq[:,None,:], C, axis=1).copy()
    clen = champ_len[:,None].repeat(C, 1).copy()
    ops = rng.integers(0, 2, size=(S, C))          # 0 replace, 1 indel
    sub = rng.integers(0, 2, size=(S, C))          # indel: 0 insert, 1 delete
    posf = rng.random((S, C)); gates = rng.integers(0, PAD, size=(S, C))
    for s in range(S):
        for c in range(C):
            L = int(clen[s, c]); op = ops[s, c]
            if op == 0:                             # replace
                pos = int(posf[s, c] * L); cseq[s, c, pos] = gates[s, c]
            else:
                ins = (L < W) and (sub[s, c] == 0 or L <= 1)
                if ins:
                    pos = int(posf[s, c] * (L + 1))
                    cseq[s, c, pos+1:L+1] = cseq[s, c, pos:L]; cseq[s, c, pos] = gates[s, c]; clen[s, c] = L + 1
                elif L > 1:
                    pos = int(posf[s, c] * L)
                    cseq[s, c, pos:L-1] = cseq[s, c, pos+1:L]; cseq[s, c, L-1] = PAD; clen[s, c] = L - 1
                else:                               # invalid: replace instead (resample-equivalent)
                    pos = int(posf[s, c] * L); cseq[s, c, pos] = gates[s, c]
    return cseq, clen

def run_lane(S, arm, seed0=31000, gens=12, shots=512, bar=0.45):
    rng = np.random.default_rng(1234)  # global fresh-rng mutation stream (declared)
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, shots, -1) if arm == "shot" else exact_balance(t)
    champ_v = v.clone().double(); crossed_gen = np.full(S, -1); max_v = champ_v.clone()
    desert_n = desert_tot = 0; lon = []
    for g in range(gens):
        cseq, cl = mutate_draw(seq, L, rng)
        ct = torch.tensor(cseq.reshape(S*15, W))
        if arm == "shot":
            f = shot_counts(ct, shots, g)
            desert = ((f >= 0.30) & (f < 0.43)).sum().item(); desert_n += desert; desert_tot += f.numel()
            F = torch.cat([v.reshape(-1, 1), f.reshape(S, 15)], dim=1)   # [S,16]
        else:
            e = exact_balance(ct).reshape(S, 15)
            F = torch.cat([v.reshape(-1, 1), e], dim=1)
            desert = ((e >= 0.30) & (e < 0.43)).sum().item(); desert_n += desert; desert_tot += e.numel()
            top2 = torch.topk(F, 2, dim=1).values
            lon += (top2[:,0] - top2[:,1]).tolist()
        fmax = F.max(dim=1).values
        cseq_t = torch.cat([torch.tensor(seq)[:, None, :], torch.tensor(cseq)], dim=1)   # [S,16,W]
        clen_t = torch.cat([torch.tensor(L)[:, None], torch.tensor(cl)], dim=1)          # [S,16]
        key = torch.rand(F.shape)
        pick = torch.where(F == fmax[:, None], key, torch.tensor(-1.0)).argmax(dim=1)     # uniform among ties
        ar = torch.arange(S)
        bseq = cseq_t[ar, pick]; blen = clen_t[ar, pick]; btrain = F[ar, pick]
        bv = shot_counts(bseq, shots, g + 100) if arm == "shot" else fmax
        promote = (bv >= champ_v)
        seq = np.where(promote[:, None].numpy(), bseq.numpy(), seq)
        L = np.where(promote.numpy(), blen.numpy(), L)
        v = torch.where(promote, btrain, v).double()
        champ_v = torch.where(promote, bv.double(), champ_v)
        max_v = torch.maximum(max_v, champ_v)
        just = (champ_v.numpy() >= bar) & (crossed_gen < 0)
        crossed_gen[just] = g
    return {"crossed": (champ_v.numpy() >= bar), "crossed_gen": crossed_gen,
            "final_v": champ_v.numpy(), "max_v": max_v.numpy(),
            "desert_frac": desert_n / max(desert_tot, 1), "loneliness": lon}

def cp_ci(k, n, a=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(a/2, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(1-a/2, k+1, n-k)
    return lo, hi

if __name__ == "__main__":
    # ANCHOR-VEC
    rng = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng.integers(0, PAD)][0] for _ in range(rng.integers(1, 7))] for _ in range(50)]
    from qcell_sim import evaluate
    ref = evaluate(gsets, device="cpu")
    GID = {repr(g[0]): i for i, g in enumerate(TEMPLATES)}
    mine = exact_balance(torch.tensor([[ (GID[repr(gate)] if i < len(g) else PAD) for i, gate in enumerate(g)] + [PAD]*(6-len(g)) for g in gsets]))
    err = max(abs(mine[j].item() - ref[j]["balance"]) for j in range(50))
    print(f"ANCHOR-VEC: max |diff| = {err:.2e}  pass={err < 1e-9}")
    # ANCHOR-8
    r8 = run_lane(8, "shot")
    print("ANCHOR-8 (fresh rng, qualitative):")
    for k in range(8):
        print(f"  seed {31000+k}: crossed={r8['crossed'][k]} final_v={r8['final_v'][k]:.4f}")
    print(f"  desert_frac={r8['desert_frac']:.4f}")
    json.dump({"anchor8": {"crossed": r8["crossed"].tolist(), "final_v": r8["final_v"].tolist()},
               "desert_frac": r8["desert_frac"]}, open("results/qg1_exact_census/qg2_anchor8.json","w"), indent=1)
