"""QG7b — rerun-ensemble correlation census.
Pre-reg: proposals/runs/QG7b-rerun-correlation.md (committed BEFORE firing).
Refires the QG7 lane R=5 times, dumps per-stream frozen-oracle scores + labels per rerun,
computes mean pairwise Spearman rho (primary gate) + label agreement (secondary).
Fail-loud; no re-roll. Pinned instruments identical to QG7 booking.
DECLARED COPY: run_lane is copied VERBATIM from experiments/qg7_gen_asymmetry.py (which has no
__main__ guard — importing it executes the whole experiment; QO3 precedent). Any divergence
between this copy and qg7_gen_asymmetry.py's run_lane invalidates the census.
"""
import sys, json, time, numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw

S, GENS, SHOTS, BAR, C = 2048, 24, 512, 0.45, 15
R = 5
DEV = "cuda"
t0 = time.time()

def run_lane():
    # VERBATIM COPY of qg7_gen_asymmetry.run_lane
    rng = np.random.default_rng(1234)
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, SHOTS, -1)
    champ_v = v.clone().double()
    crossed_gen = np.full(S, -1)
    just = (champ_v.numpy() >= BAR); crossed_gen[just] = 0
    rows1 = None
    for g in range(GENS):
        cseq, cl = mutate_draw(seq, L, rng)
        ct = torch.tensor(cseq.reshape(S * C, W))
        f = shot_counts(ct, SHOTS, g)
        F = torch.cat([v.reshape(-1, 1), f.reshape(S, C)], dim=1)
        fmax = F.max(dim=1).values
        cseq_t = torch.cat([torch.tensor(seq)[:, None, :], torch.tensor(cseq)], dim=1)
        clen_t = torch.cat([torch.tensor(L)[:, None], torch.tensor(cl)], dim=1)
        key = torch.rand(F.shape)
        pick = torch.where(F == fmax[:, None], key, torch.tensor(-1.0)).argmax(dim=1)
        ar = torch.arange(S)
        bseq = cseq_t[ar, pick]; blen = clen_t[ar, pick]; btrain = F[ar, pick]
        bv = shot_counts(bseq, SHOTS, g + 100)
        promote = (bv >= champ_v)
        seq = np.where(promote[:, None].numpy(), bseq.numpy(), seq)
        L = np.where(promote.numpy(), blen.numpy(), L)
        v = torch.where(promote, btrain, v).double()
        champ_v = torch.where(promote, bv.double(), champ_v)
        just = (champ_v.numpy() >= BAR) & (crossed_gen < 0); crossed_gen[just] = g + 1
        if g == 0:
            rows1 = {"len": L.copy(), "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])}
    return rows1, crossed_gen, champ_v.numpy()

D = 4 + PAD + 1

def build(rows1, mask):
    X = np.concatenate([np.stack([np.full(int(mask.sum()), 1.0 / 12), rows1["len"][mask] / W,
                                  rows1["v"][mask], rows1["cv"][mask]], 1),
                        rows1["hist"][mask] / 6.0], 1)
    return X.astype(np.float32)

from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ck = torch.load("tools/qcell_oracle.pt", map_location=DEV)
oracle = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                       nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
oracle.load_state_dict(ck["state_dict"]); oracle.eval()

runs = {"rate12": [], "n_sub": [], "oracle_scores_full": [], "sub_masks": [], "labels": [], "auc_oracle": [], "auc_fresh": []}
for r in range(R):
    rows1, crossed_gen, cv = run_lane()
    torch.cuda.synchronize()
    crossed12 = (crossed_gen >= 0) & (crossed_gen <= 12)
    rate12 = float(crossed12.mean())
    runs["rate12"].append(rate12)
    sub = ~crossed12
    late = (~crossed12) & (crossed_gen >= 0)
    hopeless = (~crossed12) & (crossed_gen < 0)
    y = late[sub].astype(np.float32)
    Xall = build(rows1, np.ones(S, dtype=bool))
    with torch.no_grad():
        po_all = torch.sigmoid(oracle(torch.tensor(Xall).to(DEV)).squeeze(-1)).cpu().numpy()
    po = po_all[sub]
    runs["n_sub"].append(int(sub.sum()))
    runs["labels"].append(y.astype(np.int8).tolist())
    runs["oracle_scores_full"].append(po_all.astype(np.float64).tolist())
    runs["sub_masks"].append(sub.astype(np.int8).tolist())
    a_or = float(roc_auc_score(y, po))
    # G3 fresh MLP (verbatim QG7 protocol)
    Xtr = torch.tensor(Xs).to(DEV); ytr = torch.tensor(y).to(DEV)
    torch.manual_seed(0)
    mlp = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                        nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
    opt = torch.optim.Adam(mlp.parameters(), 1e-3)
    best_auc, patience = 0.0, 0
    for ep in range(300):
        mlp.train(); opt.zero_grad()
        loss = nn.functional.binary_cross_entropy_with_logits(mlp(Xtr).squeeze(-1), ytr)
        loss.backward(); opt.step()
        mlp.eval()
        with torch.no_grad(): pa = roc_auc_score(y, torch.sigmoid(mlp(Xtr).squeeze(-1)).cpu().numpy())
        if pa > best_auc: best_auc, patience = pa, 0
        else:
            patience += 1
            if patience >= 30: break
    runs["auc_fresh"].append(float(best_auc))
    runs["auc_oracle"].append(a_or)
    print(f"run {r}: rate12 {rate12:.4f} n_sub {int(sub.sum())} late {int(late.sum())} "
          f"oracle-AUC {a_or:.4f} fresh-train-AUC {best_auc:.4f}  ({time.time()-t0:.0f}s)")

# ---- G1/G2 anchors ----
G1 = all(0.567 <= x <= 0.598 for x in runs["rate12"])
G2 = all(820 <= nsub <= 880 for nsub in runs["n_sub"])
print(f"G1 rate@12 in band all reruns: {'PASS' if G1 else 'FAIL'}  rates {runs['rate12']}")
print(f"G2 n_sub in [820,880] all reruns: {'PASS' if G2 else 'FAIL'}  n {runs['n_sub']}")
if not (G1 and G2):
    json.dump({"G1": G1, "G2": G2, "rate12": runs["rate12"], "n_sub": runs["n_sub"]},
              open("results/qg7b_rerun_correlation/results.json", "w"), indent=1)
    print("ABORT: lane diverged"); sys.exit(1)

# ---- primary gate: mean pairwise Spearman of oracle scores ----
rhos = []
for i in range(R):
    for j in range(i + 1, R):
        both = (np.array(runs["sub_masks"][i]) == 1) & (np.array(runs["sub_masks"][j]) == 1)
        si = np.array(runs["oracle_scores_full"])[i][both]
        sj = np.array(runs["oracle_scores_full"])[j][both]
        rho, _ = spearmanr(si, sj)
        rhos.append(float(rho))
rho_mean = float(np.mean(rhos))
# ---- secondary: label agreement ----
Lm = np.array(runs["labels"])  # R x n_sub
label_agree = float((Lm == Lm[0]).all(axis=0).mean())

if rho_mean > 0.9:
    verdict = ("ENSEMBLE~1-2-DRAWS: mean pairwise Spearman %.4f > 0.9 — QG7's 4-rerun ensemble is "
               "~1-2 effective draws; P1 FAIL stands on the point estimate but the 1/4-clears-0.65 "
               "spread is intra-computation noise, not judge diversity." % rho_mean)
elif rho_mean < 0.5:
    verdict = ("CORRELATED-JUDGE TRANSFER REFUTED: mean pairwise Spearman %.4f < 0.5 — "
               "identical-computation reruns are effectively independent draws; QG7 booking gains "
               "a robustness note." % rho_mean)
else:
    verdict = ("INTERMEDIATE: mean pairwise Spearman %.4f in [0.5,0.9] — no verdict-language "
               "change either way per pre-reg." % rho_mean)
print(f"PRIMARY: mean pairwise Spearman {rho_mean:.4f} (min {min(rhos):.4f} max {max(rhos):.4f})")
print(f"SECONDARY: label agreement vs run0 {label_agree:.4f}")
print(f"VERDICT: {verdict}")

import os; os.makedirs("results/qg7b_rerun_correlation", exist_ok=True)
res = {"G1": G1, "G2": G2, "rate12_runs": runs["rate12"], "n_sub_runs": runs["n_sub"],
       "auc_oracle_runs": runs["auc_oracle"], "auc_fresh_runs": runs["auc_fresh"],
       "pairwise_spearman": rhos, "spearman_mean": rho_mean, "spearman_intersection_min": int(min(((np.array(a)==1)&(np.array(b)==1)).sum() for a,b in [((runs["sub_masks"][i]),(runs["sub_masks"][j])) for i in range(R) for j in range(i+1,R)])),
       "label_agreement_vs_run0": label_agree, "verdict": verdict,
       "pinned": {"qcell_sim": "8c82d4bcc88370c0", "qcell_oracle.pt": "fed2c15fb506899f"},
       "elapsed_s": time.time() - t0,
       "honest_notes": "run_lane copied verbatim from qg7_gen_asymmetry.py (no __main__ guard there; "
                       "import-executes — QO3 precedent, declared). G3 refit here uses full-subpop "
                       "train AUC (no 80/20 split) as a cheap diversity probe only — QG7's booked "
                       "G3 numbers remain the canonical ones; this run's fresh AUCs are NOT comparable."}
json.dump(res, open("results/qg7b_rerun_correlation/results.json", "w"), indent=1)
print("booked results/qg7b_rerun_correlation/results.json")
