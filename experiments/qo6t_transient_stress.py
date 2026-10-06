"""QO6t — transient-stress the QO6 kill gate on the QG3 desert-fence population.
Prereg: proposals/runs/QO6t-prereg-transient-stress.md (committed 38dfa44 BEFORE firing).
Lane kernel: experiments/qg6_variance_rescue.py run_lane, copied verbatim, extended ONLY by
per-gen champion fitness trajectory recording. Gate: tools/eproc.kill_gate (QO6-validated).
"""
import sys, json, time
import numpy as np
import torch

sys.path.insert(0, "tools")
sys.path.insert(0, "experiments")
from qcell_sim import genome_unitary, evaluate  # noqa: E402  (anchor only)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from tools import eproc as eproc_mod  # noqa: E402
kill_gate = eproc_mod.kill_gate

ANG = [0.25, 0.5, 0.75, 1.0]
PAIRS = [(0,1),(0,2),(1,0),(1,2),(2,0),(2,1)]
TEMPLATES = ([[["h",q]] for q in range(3)] + [[["x",q]] for q in range(3)]
  + [[["rx",t,q]] for t in ANG for q in range(3)] + [[["rz",t,q]] for t in ANG for q in range(3)]
  + [[["cx",a,b]] for a,b in PAIRS] + [[["crx",t,a,b]] for t in ANG for a,b in PAIRS]
  + [[["swap",a,b]] for a,b in PAIRS])
PAD = len(TEMPLATES)
DEV = "cuda"
BAR = 0.45
SIGMA_PRIMARY = 0.03
SIGMAS_SWEEP = [0.02, 0.04, 0.05]
DELTA = 0.1
SEEDS = [11, 12, 13, 14]
S = 512
GENS = 24

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
    """QG6 run_lane VERBATIM except: records champ_v per gen -> (gens, S) trajectory."""
    LIB = make_lib()
    rng = np.random.default_rng(seed)
    seq = np.full((S, W), PAD, dtype=np.int64); seq[:,0] = TEMPLATES.index([["h",0]]); seq[:,1] = TEMPLATES.index([["cx",0,1]])
    L = np.full(S, 2, dtype=np.int64)
    v = exact_balance(torch.tensor(seq), LIB, W).double()
    champ_v = v.clone(); crossed_gen = np.full(S, -1)
    traj = np.zeros((gens, S))
    for g in range(gens):
        traj[g] = champ_v.numpy()
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
    traj[0] = champ_v.numpy()  # final state recorded as last row already; row0 was pre-selection
    return {"crossed": (champ_v.numpy() >= bar), "crossed_gen": crossed_gen, "traj": traj}

def rank_series(traj):
    """Per-gen empirical CDF rank of each stream's champ fitness within the population."""
    gens, S = traj.shape
    out = np.zeros_like(traj)
    for g in range(gens):
        col = traj[g]
        order = col.argsort()
        ranks = np.empty(S); ranks[order] = np.arange(1, S+1)
        out[g] = ranks / S
    return out

if __name__ == "__main__":
    t0 = time.time()
    # G1-adjacent ANCHOR (QG6 pin): kernel arithmetic unchanged
    LIB = make_lib()
    rng = np.random.default_rng(7)
    gsets = [[TEMPLATES[rng.integers(0, PAD)][0] for _ in range(rng.integers(1, 7))] for _ in range(50)]
    ref = evaluate(gsets, device="cpu")
    GID = {repr(g[0]): i for i, g in enumerate(TEMPLATES)}
    mine = exact_balance(torch.tensor([[GID[repr(gate)] if i < len(g) else PAD for i, gate in enumerate(g)] + [PAD]*(6-len(g)) for g in gsets]), LIB, 6)
    err = max(abs(mine[j].item() - ref[j]["balance"]) for j in range(50))
    print(f"ANCHOR-VEC: max|diff|={err:.2e} pass={err<1e-9}", flush=True)
    assert err < 1e-9, "ANCHOR FAIL"

    out = {"anchor_vec_err": err, "config": {"S": S, "gens": GENS, "seeds": SEEDS, "bar": BAR,
            "sigma_primary": SIGMA_PRIMARY, "sigmas_sweep": SIGMAS_SWEEP, "delta": DELTA},
           "seeds": {}}
    for seed in SEEDS:
        R = run_lane_trajectory(S, 6, GENS, seed=seed)
        crossed = R["crossed"]; cg = R["crossed_gen"]
        rs = rank_series(R["traj"])
        # G1 construction gates
        rate24 = float(crossed.mean())
        rate12 = float((cg[(cg >= 0) & (cg < 12)]).size / S)
        g1 = {"crossed24": rate24, "crossed_by_12": rate12,
              "pass": bool(abs(rate24 - 0.755) <= 0.05 and abs(rate12 - 0.578) <= 0.05)}
        # G2+G3: gate at checkpoints A=[0..11], B=[0..15], full-24
        per_sigma = {}
        for sig in [SIGMA_PRIMARY] + SIGMAS_SWEEP:
            decA = {}; decB = {}; decF = {}
            for sidx in range(S):
                decA[sidx] = kill_gate(list(rs[:12, sidx]), sigma=sig, delta=DELTA)
                decB[sidx] = kill_gate(list(rs[:16, sidx]), sigma=sig, delta=DELTA)
                decF[sidx] = kill_gate(list(rs[:, sidx]), sigma=sig, delta=DELTA)
            cross_idx = np.where(crossed)[0]; dead_idx = np.where(~crossed)[0]
            fkA = np.mean([decA[i]["decision"] == "KILL_CANDIDATE" for i in cross_idx]) if len(cross_idx) else 0.0
            a_kills = [i for i in cross_idx if decA[i]["decision"] == "KILL_CANDIDATE"]
            recovery = (np.mean([decF[i]["retracted"] for i in a_kills]) if a_kills else 1.0)
            powerB = np.mean([decB[i]["decision"] == "KILL_CANDIDATE" for i in dead_idx]) if len(dead_idx) else 0.0
            per_sigma[str(sig)] = {
                "falseKill_A": float(fkA), "recovery_of_A_kills": float(recovery),
                "power_B_hopeless": float(powerB),
                "n_A_kills": len(a_kills),
                "retracted_at_full_among_all": float(np.mean([decF[i]["retracted"] for i in range(S)])),
                "verdict": ("PASS" if (recovery >= 0.80 and powerB >= 0.30) else
                            ("PREMATURE-KILL" if (fkA > 0.30 and recovery < 0.50) else "MIXED")),
            }
        out["seeds"][str(seed)] = {"g1": g1, "gates": per_sigma}
        print(f"seed {seed}: g1 {g1} | sigma={SIGMA_PRIMARY}: {per_sigma[str(SIGMA_PRIMARY)]} ({time.time()-t0:.0f}s)", flush=True)

    # pooled primary verdict across seeds (sigma primary)
    prim = [out["seeds"][s]["gates"][str(SIGMA_PRIMARY)] for s in map(str, SEEDS)]
    pooled = {k: float(np.mean([p[k] for p in prim]))
              for k in ("falseKill_A", "recovery_of_A_kills", "power_B_hopeless")}
    passes = sum(1 for p in prim if p["verdict"] == "PASS")
    out["pooled_primary"] = {**pooled, "seeds_pass": passes, "seeds_total": len(prim),
        "overall": "PASS" if passes >= 3 else ("PREMATURE-KILL" if sum(1 for p in prim if p["verdict"]=="PREMATURE-KILL") >= 3 else "MIXED")}
    print("POOLED:", json.dumps(out["pooled_primary"]), flush=True)

    from pathlib import Path
    odir = Path(__file__).resolve().parents[1] / "results" / "qo6t_transient_stress"
    odir.mkdir(exist_ok=True)
    (odir / "results.json").write_text(json.dumps(out, indent=2, default=float))
    (odir / "run.log").write_text(f"anchor_err={err}\ncompleted={time.time()-t0:.0f}s\n")
    print(f"QO6T DONE ({time.time()-t0:.0f}s)", flush=True)
