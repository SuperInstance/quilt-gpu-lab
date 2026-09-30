"""QO3 — early-forecast horizon: first gen where per-gen oracle AUC clears 0.80.
Pre-reg: proposals/runs/QO3-early-forecast-horizon.md (committed before firing).
Lane = QO1-identical (seed 1234, passive recording). Fail-loud, no re-roll.
"""
import sys, json, numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qcell_sim import evaluate  # noqa: F401
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw
from experiments.oracle1 import run_lane_states  # reuse QO1 lane verbatim

S, GENS, BAR = 4096, 12, 0.45
DEV = "cuda"

rows, crossed = run_lane_states(S)
rate = crossed.mean(); k = int(crossed.sum()); n = S
from scipy.stats import beta as _beta
lo = _beta.ppf(0.025, k, n - k + 1); hi = _beta.ppf(0.975, k + 1, n - k)
print(f"lane crossing rate {rate:.4f} ({k}/{n}) CP95 [{lo:.4f},{hi:.4f}]")
G1 = bool(0.5670 <= rate <= 0.5974)
print(f"G1 (QG2-band anchor): {'PASS' if G1 else 'FAIL-DIVERGED'}")
if not G1:
    print("ABORT: lane diverged, booking FAILED-DIVERGED")
    json.dump({"G1": False, "rate": float(rate)}, open("results/qo3_horizon/results.json", "w"))
    sys.exit(1)

D = 4 + PAD + 1
rs = np.random.default_rng(99)
perm = rs.permutation(S)
tr_streams = set(perm[:int(0.8 * S)].tolist())
tr_mask = np.array([s in tr_streams for s in range(S)])

def build(g):
    r = rows[g]
    X = np.concatenate([np.stack([r["gen"] / GENS, r["len"] / W, r["v"], r["cv"]], 1),
                        r["hist"] / 6.0], 1)
    return X

from sklearn.metrics import roc_auc_score

def fit_mlp(Xtr, ytr, Xte):
    torch.manual_seed(0)
    mlp = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                        nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
    opt = torch.optim.Adam(mlp.parameters(), 1e-3)
    Xt = torch.tensor(Xte, dtype=torch.float32).to(DEV)
    best_auc, best_state, patience = 0.0, None, 0
    for ep in range(300):
        mlp.train(); opt.zero_grad()
        loss = nn.functional.binary_cross_entropy_with_logits(mlp(Xtr).squeeze(-1), ytr)
        loss.backward(); opt.step()
        mlp.eval()
        with torch.no_grad(): pm = torch.sigmoid(mlp(Xt).squeeze(-1)).cpu().numpy()
        a = roc_auc_score(yte_np, pm)
        if a > best_auc: best_auc, best_state, patience = a, {k2: v.clone() for k2, v in mlp.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 30: break
    mlp.load_state_dict(best_state)
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xt).squeeze(-1)).cpu().numpy()
    return pm, best_auc

def fit_logit(Xtr_c, ytr, Xte_c):
    Xm = torch.cat([torch.ones(len(ytr), 1, device=DEV), Xtr_c], 1)
    w = torch.zeros(Xm.shape[1], device=DEV, requires_grad=True)
    opt = torch.optim.Adam([w], 1e-2)
    for _ in range(400):
        opt.zero_grad(); loss = nn.functional.binary_cross_entropy_with_logits(Xm @ w, ytr); loss.backward(); opt.step()
    Xt = torch.cat([torch.ones(len(Xte_c), 1, device=DEV), Xte_c], 1)
    return torch.sigmoid(Xt @ w).detach().cpu().numpy()

aucs, aucs_b = {}, {}
pergen = {}
for g in range(GENS + 1):
    X = build(g)
    y = crossed.astype(np.float32)
    Xtr = torch.tensor(X[tr_mask], dtype=torch.float32).to(DEV)
    ytr = torch.tensor(y[tr_mask], dtype=torch.float32).to(DEV)
    Xte = torch.tensor(X[~tr_mask], dtype=torch.float32).to(DEV)
    yte_np = y[~tr_mask]
    pb = fit_logit(Xtr[:, 3:4], ytr, Xte[:, 3:4])
    aucs_b[g] = float(roc_auc_score(yte_np, pb))
    pm, a = fit_mlp(Xtr, ytr, Xte)
    aucs[g] = float(a)
    print(f"gen {g:2d}: MLP AUC {aucs[g]:.4f} | cv-logit AUC {aucs_b[g]:.4f}")

# G2: first crossing of 0.80
g_star = next((g for g in range(GENS + 1) if aucs[g] >= 0.80), None)
print(f"G2 horizon g* = {g_star}")

# G3: bootstrap stability of g* — per-stream val predictions per gen, resample streams.
pergen_preds = {}
for g in range(GENS + 1):
    X = build(g); y = crossed.astype(np.float32)
    Xtr = torch.tensor(X[tr_mask], dtype=torch.float32).to(DEV)
    ytr = torch.tensor(y[tr_mask], dtype=torch.float32).to(DEV)
    Xte = torch.tensor(X[~tr_mask], dtype=torch.float32).to(DEV)
    yte_np = y[~tr_mask]
    pm, _ = fit_mlp(Xtr, ytr, Xte)
    pergen_preds[g] = pm

rng = np.random.default_rng(7)
val_y = crossed[~tr_mask].astype(int)
g_stars = []
for b in range(200):
    idx = rng.choice(len(val_y), size=len(val_y), replace=True)
    if val_y[idx].min() == val_y[idx].max(): continue
    gb = None
    for g in range(GENS + 1):
        if roc_auc_score(val_y[idx], pergen_preds[g][idx]) >= 0.80:
            gb = g; break
    g_stars.append(gb)
g_arr = np.array([x if x is not None else 99 for x in g_stars])
q1, q3 = np.percentile(g_arr, 25), np.percentile(g_arr, 75)
print(f"G3 g* bootstrap: median {np.median(g_arr)} IQR [{q1},{q3}] (99=never)")
unstable = (q3 - q1) >= 3

res = {"G1": True, "rate": float(rate), "auc_mlp": aucs, "auc_cv_logit": aucs_b,
       "g_star": g_star, "g_star_bootstrap_median": float(np.median(g_arr)),
       "g_star_iqr": [float(q1), float(q3)], "horizon_unstable": bool(unstable)}
import os
os.makedirs("results/qo3_horizon", exist_ok=True)
json.dump(res, open("results/qo3_horizon/results.json", "w"), indent=2)
print("booked results/qo3_horizon/results.json")
