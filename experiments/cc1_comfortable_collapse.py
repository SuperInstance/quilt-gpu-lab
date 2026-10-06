"""CC-1 — comfortable-collapse census on the QO6t desert-fence population.
Prereg: proposals/runs/CC-1-prereg-comfortable-collapse.md (committed 3092b69 BEFORE firing).
Lane kernel: experiments/qo6t_transient_stress.py run_lane_trajectory copied VERBATIM,
extended ONLY by also recording the champion-length trajectory (ltraj) per gen.
Groups at census gen g*=12: HOPELESS (never cross by 24), FENCED (cross gen>=13), EARLY (<=12).
AUC = Mann-Whitney U / (n1*n2), FENCED vs HOPELESS, per feature per seed + pooled.
"""
import sys, json, time, pathlib
import numpy as np
import torch

sys.path.insert(0, "tools")
sys.path.insert(0, "experiments")
from qcell_sim import genome_unitary, evaluate  # noqa: E402  (anchor only)

ANG = [0.25, 0.5, 0.75, 1.0]
PAIRS = [(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
TEMPLATES = ([[["h",q]] for q in range(3)] + [[["x",q]] for q in range(3)]
  + [[["rx",t,q]] for t in ANG for q in range(3)] + [[["rz",t,q]] for t in ANG for q in range(3)]
  + [[["cx",a,b]] for a,b in PAIRS] + [[["crx",t,a,b]] for t in ANG for a,b in PAIRS]
  + [[["swap",a,b]] for a,b in PAIRS])
PAD = len(TEMPLATES)
DEV = "cuda"
BAR = 0.45
SEEDS = [11, 12, 13, 14]
S = 512
GENS = 24
GSTAR = 12

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
    S = champ_len.shape[0]; C = 15
    cseq = np.repeat(champ_seq[:,None,:], C, axis=1).copy()
    clen = champ_len[:,None].repeat(C, 1).copy()
    for _ in range(k):
        cseq, clen = _one_mut_round(cseq, clen, rng, W)
    return cseq, clen

def run_lane_trajectory(S, W, gens, seed, bar=BAR):
    """qo6t run_lane_trajectory VERBATIM except: also records champ_len per gen (ltraj)."""
    LIB = make_lib()
    rng = np.random.default_rng(seed)
    seq = np.full((S, W), PAD, dtype=np.int64); seq[:,0] = TEMPLATES.index([["h",0]]); seq[:,1] = TEMPLATES.index([["cx",0,1]])
    L = np.full(S, 2, dtype=np.int64)
    v = exact_balance(torch.tensor(seq), LIB, W).double()
    champ_v = v.clone(); crossed_gen = np.full(S, -1)
    traj = np.zeros((gens, S)); ltraj = np.zeros((gens, S))
    for g in range(gens):
        traj[g] = champ_v.numpy(); ltraj[g] = L
        cseq, cl = mutate_draw(seq, L, rng, W, k=1)
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
    traj[0] = champ_v.numpy()
    return {"crossed": (champ_v.numpy() >= bar), "crossed_gen": crossed_gen,
            "traj": traj, "ltraj": ltraj}

def rank_col(col):
    order = col.argsort(); ranks = np.empty(len(col)); ranks[order] = np.arange(1, len(col)+1)
    return ranks / len(col)

def auc(pos, neg):
    """Mann-Whitney AUC, P(pos > neg) + 0.5 P(equal)."""
    if len(pos) == 0 or len(neg) == 0: return None
    gt = (pos[:,None] > neg[None,:]).sum(); eq = (pos[:,None] == neg[None,:]).sum()
    return float((gt + 0.5*eq) / (len(pos)*len(neg)))

if __name__ == "__main__":
    t0 = time.time()
    out = {"config": {"S": S, "gens": GENS, "seeds": SEEDS, "bar": BAR, "gstar": GSTAR,
                      "prereg": "proposals/runs/CC-1-prereg-comfortable-collapse.md",
                      "prereg_commit": "3092b69"}}
    # fail-loud anchor (QO6t precedent)
    LIB = make_lib()
    rng7 = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng7.integers(0, PAD)][0] for _ in range(rng7.integers(1, 7))] for _ in range(50)]
    ref2 = [d["balance"] for d in evaluate(gsets, device="cpu")]
    ours = exact_balance(torch.tensor([[TEMPLATES.index([g]) for g in gs] + [PAD]*(6-len(gs)) for gs in gsets]), LIB, 6)
    aerr = float(np.max(np.abs(np.array(ref2) - ours.numpy())))
    out["anchor_vec_err"] = aerr
    assert aerr < 1e-9, f"ANCHOR FAIL {aerr}"

    per_seed, pooled = {"fenced_auc": {}, "hopeless_n": [], "fenced_n": []}, {}
    for seed in SEEDS:
        r = run_lane_trajectory(S, 6, GENS, seed, bar=BAR)
        crossed24, cgen, traj, ltraj = r["crossed"], r["crossed_gen"], r["traj"], r["ltraj"]
        c24 = crossed24.mean(); c12 = (cgen >= 0) & (cgen <= GSTAR-1)
        per_seed.setdefault("c24", []).append(float(c24))
        per_seed.setdefault("c12", []).append(float(c12.mean()))
        hopeless = ~crossed24
        fenced = crossed24 & (cgen >= GSTAR)   # cross at gen 13..23
        early = crossed24 & (cgen < GSTAR)
        v12, l12 = traj[GSTAR], ltraj[GSTAR]
        rk12 = rank_col(v12)
        prev = traj[max(0, GSTAR-8):GSTAR]
        rate = (v12 - prev[0]) / max(1, GSTAR-1 - 0 + 0) if prev.shape[0] > 1 else np.zeros_like(v12)
        feats = {"v": v12, "rank": rk12, "len": l12, "rate": rate}
        per_seed["hopeless_n"].append(int(hopeless.sum()))
        per_seed["fenced_n"].append(int(fenced.sum()))
        sd = {}
        for name, fv in feats.items():
            a_f = auc(fv[fenced], fv[hopeless]); sd[name] = a_f
            pooled.setdefault(name, {"pos": [], "neg": []})
            pooled[name]["pos"] += fv[fenced].tolist(); pooled[name]["neg"] += fv[hopeless].tolist()
        per_seed.setdefault("fenced_auc", {})[str(seed)] = sd
        per_seed.setdefault("early_v_auc", []).append(auc(v12[early], v12[hopeless]))
    pooled_auc = {k: auc(np.array(d["pos"]), np.array(d["neg"])) for k, d in pooled.items()}
    out["per_seed"] = per_seed
    out["pooled_auc_gstar12"] = pooled_auc

    # Gates (prereg)
    c24s = per_seed["c24"]; c12s = per_seed["c12"]
    out["G1"] = {"c24": c24s, "c12": c12s,
                 "pass": all(abs(x-0.755) <= 0.05 for x in c24s) and all(abs(x-0.578) <= 0.05 for x in c12s)}
    out["G2"] = {"min_fenced_pooled": sum(per_seed["fenced_n"]), "pass": sum(per_seed["fenced_n"]) >= 40}
    out["G4"] = {"early_v_auc_min": min(x for x in per_seed["early_v_auc"] if x is not None),
                 "pass": min(x for x in per_seed["early_v_auc"] if x is not None) > 0.9}
    pa = pooled_auc
    blind = all(0.45 <= (pa[k] or 0.0) <= 0.60 for k in ["v","rank","len","rate"])
    newfeat = any((pa[k] or 0.0) >= 0.75 for k in ["v","rank","len","rate"])
    out["G3"] = {"pooled": pa, "verdict": ("COMFORTABLE_COLLAPSE_CONFIRMED" if blind else
                 ("NEW_FEATURE" if newfeat else "INCONCLUSIVE"))}

    odir = pathlib.Path("results/cc1_comfortable_collapse"); odir.mkdir(parents=True, exist_ok=True)
    (odir / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"G1": out["G1"]["pass"], "G2": out["G2"]["pass"], "G3": out["G3"],
                      "G4": out["G4"]["pass"], "secs": round(time.time()-t0, 1)}, indent=1))
