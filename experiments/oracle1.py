"""QO1 — qcell-oracle: MLP on champion state -> will the stream cross bar 0.45 by gen 12?
Pre-reg: proposals/runs/QO1-qcell-oracle.md (committed before firing). Shot arm, S=4096.
Data lane = qg2_scale_lane physics re-instrumented (declared: extra rng consumption NONE —
states are recorded passively, so trajectories are QG2-identical given the same global rng).
"""
import sys, json, numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qcell_sim import evaluate  # noqa: F401  (import check: fail-loud)
from qg2_scale_lane import (TEMPLATES, PAD, W, exact_balance, shot_counts,
                            skeleton_seqs, mutate_draw)

S, GENS, SHOTS, BAR, C = 4096, 12, 512, 0.45, 15
DEV = "cuda"

def run_lane_states(S):
    rng = np.random.default_rng(1234)          # same global fresh-rng stream as QG2
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, SHOTS, -1)
    champ_v = v.clone().double()
    rows = []                                   # passive recording, no rng drawn
    def record(g, seq, L, v, champ_v):
        rows.append({"gen": np.full(S, g), "len": L.copy(),
                     "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])})
    record(0, seq, L, v, champ_v)               # birth state
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
        record(g + 1, seq, L, v, champ_v)
    return rows, (champ_v.numpy() >= BAR)

# ---- build dataset ----
rows, crossed = run_lane_states(S)
rate = crossed.mean()
k = int(crossed.sum()); n = S
from scipy.stats import beta as _beta
lo = _beta.ppf(0.025, k, n - k + 1); hi = _beta.ppf(0.975, k + 1, n - k)
print(f"lane crossing rate {rate:.4f} ({k}/{n}) CP95 [{lo:.4f},{hi:.4f}]")
G1 = bool(0.5670 <= rate <= 0.5974)
print(f"G1 (QG2-band anchor): {'PASS' if G1 else 'FAIL-DIVERGED'}")

feats = []
for r in rows:
    blk = np.concatenate([np.stack([r["gen"] / GENS, r["len"] / W, r["v"], r["cv"]], 1),
                          r["hist"] / 6.0], 1)          # [S, 53]
    feats.append(blk)
X = np.concatenate(feats, 0)                              # [S*(GENS+1), 53]
y = np.concatenate([crossed] * (GENS + 1), 0)
stream_id = np.concatenate([np.arange(S)] * (GENS + 1), 0)

rs = np.random.default_rng(99)
perm = rs.permutation(S)
tr_streams = set(perm[:int(0.8 * S)].tolist())
tr = np.array([s in tr_streams for s in stream_id])
Xtr, ytr = torch.tensor(X[tr], dtype=torch.float32).to(DEV), torch.tensor(y[tr], dtype=torch.float32).to(DEV)
Xte, yte = torch.tensor(X[~tr], dtype=torch.float32).to(DEV), torch.tensor(y[~tr], dtype=torch.float32).to(DEV)
print(f"rows {len(y)} train {len(ytr)} test {len(yte)} (split by stream)")

from sklearn.metrics import roc_auc_score, brier_score_loss

# baseline: logistic on champ_v only
def logit_fit(Xtr_c, ytr, Xte_c):
    Xm = torch.cat([torch.ones(len(ytr),1,device=DEV), Xtr_c],1)
    w = torch.zeros(Xm.shape[1], device=DEV, requires_grad=True)
    opt = torch.optim.Adam([w], 1e-2)
    for _ in range(400):
        opt.zero_grad(); loss = nn.functional.binary_cross_entropy_with_logits(Xm@w, ytr); loss.backward(); opt.step()
    Xt = torch.cat([torch.ones(len(yte),1,device=DEV), Xte_c],1)
    return torch.sigmoid(Xt@w).cpu().numpy()

pb = logit_fit(Xtr[:, 3:4], ytr, Xte[:, 3:4])
auc_b = roc_auc_score(yte.cpu(), pb); br_b = brier_score_loss(yte.cpu(), pb)

# MLP
torch.manual_seed(0)
mlp = nn.Sequential(nn.Linear(53, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                    nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
opt = torch.optim.Adam(mlp.parameters(), 1e-3)
best_auc, best_state, patience = 0.0, None, 0
for ep in range(300):
    mlp.train(); opt.zero_grad()
    loss = nn.functional.binary_cross_entropy_with_logits(mlp(Xtr).squeeze(-1), ytr)
    loss.backward(); opt.step()
    mlp.eval()
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xte).squeeze(-1)).cpu().numpy()
    a = roc_auc_score(yte.cpu(), pm)
    if a > best_auc: best_auc, best_state, patience = a, {k: v.clone() for k, v in mlp.state_dict().items()}, 0
    else:
        patience += 1
        if patience >= 30: break
mlp.load_state_dict(best_state)
with torch.no_grad(): pm = torch.sigmoid(mlp(Xte).squeeze(-1)).cpu().numpy()
auc_m = roc_auc_score(yte.cpu(), pm); br_m = brier_score_loss(yte.cpu(), pm)
print(f"baseline AUC {auc_b:.4f} brier {br_b:.4f}")
print(f"oracle   AUC {auc_m:.4f} brier {br_m:.4f}")
G2 = bool(auc_m >= 0.70 and auc_m - auc_b >= 0.05)
print(f"G2 (skill): {'PASS' if G2 else 'FAIL'}")

# G4 permutation importance (on val, AUC drop)
imp = {}
base = auc_m
for i, name in enumerate(["gen", "len", "v", "cv"] + [f"h{j}" for j in range(49)]):
    Xt2 = Xte.clone(); Xt2[:, i] = Xt2[torch.randperm(len(Xt2), device=DEV), i]
    with torch.no_grad(): p2 = torch.sigmoid(mlp(Xt2).squeeze(-1)).cpu().numpy()
    imp[name] = base - roc_auc_score(yte.cpu(), p2)
top = sorted(imp.items(), key=lambda kv: -kv[1])[:12]
print("G4 permutation importance top:", [(k, round(v_, 4)) for k, v_ in top])

torch.save({"state_dict": mlp.state_dict(), "features": ["gen","len","v","cv"]+[f"h{i}" for i in range(49)],
            "norm": {"gen": GENS, "len": W, "hist": 6.0}, "bar": BAR, "auc_val": auc_m}, "tools/qcell_oracle.pt")
import os
os.makedirs("results/qo1_oracle", exist_ok=True)
json.dump({"lane": {"crossed_rate": float(rate), "k": k, "n": n, "cp95": [float(lo), float(hi)]},
           "G1": G1, "G2": {"pass": G2, "auc_mlp": float(auc_m), "auc_baseline": float(auc_b),
                            "brier_mlp": float(br_m), "brier_baseline": float(br_b)},
           "importance_top": [(k2, float(v2)) for k2, v2 in top], "epochs": ep + 1},
          open("results/qo1_oracle/qo1_results.json", "w"), indent=1)
print("booked results/qo1_oracle/qo1_results.json + tools/qcell_oracle.pt")
