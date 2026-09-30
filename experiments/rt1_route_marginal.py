#!/usr/bin/env python3
"""RT1 — what makes a route worth adding? marginal information vs the disagreement dial.

Pre-reg: proposals/runs/RT1-route-marginal-info.md
Source canon: quilt-research-canons/research/anti-gan-route-diversity.md (its own
named open problem: the retrospective disagreement dial is "weak").

Five routes read the same synthetic double-entry books through different views; each
route gets a tiny learned checker (MLP, CUDA). We compare, per route:
  marginal AUC  = AUC(ensemble) - AUC(ensemble minus this route)
  disagreement  = mean pairwise label-disagreement with the other routes
and ask whether the cheap retrospective dial tracks marginal information.

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/rt1_route_marginal.py
"""
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split

N_BOOKS, N_ENTRIES, N_ACCT = 4000, 20, 5
DEFECTS = ["clean", "missing", "sign", "rounding", "account"]
OUT = os.path.join(os.path.dirname(__file__), "..", "results", "rt1")
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def make_book(rng, defect):
    n = N_ENTRIES
    accts = rng.integers(0, N_ACCT, size=n)
    amt = rng.normal(0, 100, size=n)
    amt[-1] = -amt[:-1].sum()                    # balanced book
    if defect == "missing":
        i = rng.integers(0, n - 1)                      # R2 (count/parity), R1 (sum)
        accts, amt = np.delete(accts, i), np.delete(amt, i)
    elif defect == "sign":
        i = int(np.argmax(np.abs(amt)))                 # R1 (sum), R4 (sign stats)
        amt = amt.copy(); amt[i] = -amt[i]
    elif defect == "rounding":                          # R3 (fractional mass)
        idx = rng.choice(n - 1, size=4, replace=False)
        amt = amt.copy(); amt[idx] += rng.uniform(0.6, 1.4, size=4)
    elif defect == "account":                           # R5 (categorical shape)
        idx = rng.choice(n - 1, size=3, replace=False)
        accts = accts.copy()
        accts[idx] = (accts[idx] + 1 + rng.integers(1, N_ACCT - 1, size=3)) % N_ACCT
    return accts, amt


def route_features(accts, amt):
    s = float(amt.sum())
    frac = float(np.abs(amt - np.round(amt)).sum())
    counts = np.bincount(accts, minlength=N_ACCT).astype(float)
    p = counts / counts.sum()
    ent = float(-(p[p > 0] * np.log(p[p > 0])).sum())
    return {
        "R1_sum": [s, abs(s)],
        "R2_parity": [len(amt), len(amt) % 2],
        "R3_magnitude": [float(np.abs(amt).sum()), frac],
        "R4_sign": [float(np.sign(amt).sum()), float((amt > 0).sum())],
        "R5_categorical": [ent, float(counts.max()), float((counts > 0).sum())],
    }


class Tiny(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, 8), nn.Tanh(), nn.Linear(8, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_route(Xtr, ytr, Xte, seed):
    torch.manual_seed(seed)
    mu, sd = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True).clamp_min(1e-6)
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd   # standardize (train stats only)
    m = Tiny(Xtr.shape[1]).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=0.02)
    lossf = nn.BCEWithLogitsLoss()
    Xt, yt = Xtr.to(DEV), ytr.to(DEV)
    for _ in range(500):
        opt.zero_grad()
        loss = lossf(m(Xt), yt)
        loss.backward()
        opt.step()
    with torch.no_grad():
        return m(Xte.to(DEV)).cpu()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(0)
    books = [(make_book(rng, d), d) for d in DEFECTS for _ in range(N_BOOKS // len(DEFECTS))]
    y = np.array([1 if d != "clean" else 0 for _, d in books])
    feats = {r: [] for r in route_features(*books[0][0])}
    for (accts, amt), _ in books:
        f = route_features(accts, amt)
        for r in feats:
            feats[r].append(f[r])
    feats = {r: np.array(v, dtype=np.float32) for r, v in feats.items()}
    print(f"RT1 — {len(books)} books, defect balance {y.mean():.2f}, device={DEV}",
          flush=True)

    idx = np.arange(len(y))
    tr, te = train_test_split(idx, test_size=0.4, random_state=0, stratify=y)
    logits, probs = {}, {}
    for r, F in feats.items():
        z = np.mean([train_route(torch.tensor(F[tr]), torch.tensor(y[tr]).float(),
                                 torch.tensor(F[te]), s).numpy() for s in (0, 1, 2)], axis=0)
        logits[r], probs[r] = z, 1 / (1 + np.exp(-z))
        print(f"  {r}: AUC {roc_auc_score(y[te], probs[r]):.4f}", flush=True)

    L = np.column_stack([logits[r] for r in feats])   # route logits on the TEST split
    y_te = y[te]                                      # same rows — the length bug fixed
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    ens = cross_val_predict(LogisticRegression(max_iter=1000), L, y_te,
                            cv=skf, method="predict_proba")[:, 1]
    auc_full = roc_auc_score(y_te, ens)
    names = list(feats)
    marginal = {}
    for i, r in enumerate(names):
        keep = [j for j in range(len(names)) if j != i]
        loo = cross_val_predict(LogisticRegression(max_iter=1000), L[:, keep], y_te,
                                cv=skf, method="predict_proba")[:, 1]
        marginal[r] = auc_full - roc_auc_score(y_te, loo)
    pred = {r: (probs[r] > 0.5).astype(int) for r in names}
    # probability divergence (thresholded disagreement is degenerate at 0.5 on an
    # 80%-positive label — measured all-zero on the first pass)
    disagree = {r: float(np.mean([np.mean(np.abs(probs[r] - probs[s]))
                                  for s in names if s != r])) for r in names}
    disagree_thresh = {r: float(np.mean([np.mean(pred[r] != pred[s])
                                         for s in names if s != r])) for r in names}
    rho, pval = spearmanr([marginal[r] for r in names], [disagree[r] for r in names])
    spread = np.ptp([logits[r].std() for r in names])

    per_route = {r: roc_auc_score(y[te], probs[r]) for r in names}
    g1 = max(per_route.values()) >= 0.70
    g2 = np.ptp(list(marginal.values())) >= 0.01
    g3 = rho is not None and rho >= 0.5
    verdict = ("DIAL_TRACKS" if (g1 and g2 and g3) else
               "DIAL_DECORATIVE" if (g1 and g2) else "INVALID")
    summary = {
        "experiment": "RT1 — marginal information vs the disagreement dial",
        "n_books": len(books), "device": DEV,
        "per_route_auc": per_route,
        "ensemble_auc_full": auc_full,
        "marginal_auc": marginal,
        "disagreement_divergence": disagree,
        "disagreement_thresholded": disagree_thresh,
        "spearman_marginal_vs_disagreement": [rho, pval],
        "gates": {"G1_learnable": bool(g1), "G2_spread": bool(g2), "G3_dial_tracks": bool(g3)},
        "verdict": verdict,
        "wall_clock_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(OUT, "rt1_results.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2, default=float), flush=True)
