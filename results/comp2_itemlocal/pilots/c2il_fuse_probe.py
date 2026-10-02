#!/usr/bin/env python3
"""Disclosed direction-finding probe: which item-local fusion operator, if any,
clears BEST-SINGLE on the C2-IL corpus?  NOT a booking.  CPU-only."""
import sys, json
from pathlib import Path
import numpy as np

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from experiments.comp2_itemlocal import (gen_corpus_il, featurize, load_bank, infer,
                                         SENSORS, SEEDS, H_CELL, H_JOINT, BANKS)
from experiments.comp2_arms import REGIMES
from sklearn.linear_model import LogisticRegression

variant = sys.argv[1] if len(sys.argv) > 1 else "B"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 500
train, held, _ = gen_corpus_il(N, variant)
y_tr = np.array([1 if it["label"] == "canon" else 0 for it in train])
y_he = np.array([1 if it["label"] == "canon" else 0 for it in held])
ch_he = np.array([it["channel"] or "none" for it in held])
F_tr, F_he = featurize(train), featurize(held)

# frozen per-sensor MLP cells (seed-mean)
Pm = {}
for s in SENSORS:
    Pm[s] = np.stack([infer(load_bank(BANKS / f"HETERO_{s}_seed{sd}.pt", H_CELL), F_he[s]) for sd in SEEDS])
# train-side margins too (for the gate)
Pm_tr = {}
for s in SENSORS:
    Pm_tr[s] = np.stack([infer(load_bank(BANKS / f"HETERO_{s}_seed{sd}.pt", H_CELL), F_tr[s]) for sd in SEEDS]).mean(axis=0)

def acc(p, y=y_he):
    return float(((p >= 0.5) == (y == 1)).mean())

sm = {s: Pm[s].mean(axis=0) for s in SENSORS}          # seed-mean p
bt = {s: acc(sm[s]) for s in SENSORS}
# cheap refit cells (TRAIN-fit on the IL split) -- also "per-sensor views"
from sklearn.linear_model import LogisticRegression as _LR
cheap_tr, cheap_he = {}, {}
for s in SENSORS:
    c = _LR(solver="lbfgs", C=1.0, max_iter=3000, random_state=2718).fit(F_tr[s], y_tr)
    cheap_tr[s] = c.predict_proba(F_tr[s])[:, 1]
    cheap_he[s] = c.predict_proba(F_he[s])[:, 1]
    sm["cheap_" + s] = cheap_he[s]
    bt["cheap_" + s] = acc(cheap_he[s])
ALL = list(sm.keys())
best_s = max(bt, key=bt.get)
print(f"variant {variant}  N={N}  train/held {len(train)}/{len(held)}  chance {max(y_he.mean(),1-y_he.mean()):.4f}")
print("single:", {s: round(bt[s], 4) for s in ALL}, "-> best", best_s, round(bt[best_s], 4))

# ── candidate fusions ───────────────────────────────────────────────────────
def route_margin(P):                       # argmax |p-0.5|
    M = np.stack([P[s] for s in P]); k = np.argmax(np.abs(M - 0.5), axis=0)
    return M[k, np.arange(M.shape[1])]
def join(P, ss):                           # min-p over subset
    return np.min(np.stack([P[s] for s in ss]), axis=0)
def maj(P):
    M = np.stack([P[s] for s in P]); v = (M >= 0.5).sum(0)
    return np.where(v > len(M) // 2, 1.0, np.where(v < (len(M) + 1) // 2, 0.0, np.min(M, axis=0) >= 0.5))

MLP = SENSORS
CHEAP = ["cheap_" + s for s in SENSORS]
cands = {
    "MARGIN-mlp": route_margin({s: sm[s] for s in MLP}),
    "MARGIN-all8": route_margin(sm),
    "JOIN4-mlp": join(sm, MLP),
    "JOIN-S1S4": join(sm, ["S1", "S4"]),
    "JOIN-cheap4": join(sm, CHEAP),
    "JOIN-all8": join(sm, ALL),
    "MAJ-all8": maj(sm),
    "AVG-all8": np.mean(np.stack([sm[s] for s in ALL]), axis=0),
}
# learned 8-feature gate -> best sensor (per seed-mean cells, all 8 views)
# target: sensor whose verdict is correct with the largest margin (canon: max-margin correct)
Pt = np.stack([Pm_tr[s] for s in SENSORS] + [cheap_tr[s] for s in SENSORS], axis=1)
feat_tr = np.concatenate([Pt, np.abs(Pt - 0.5)], axis=1)
ok = ((Pt >= 0.5) == (y_tr[:, None] == 1))
marg = np.abs(Pt - 0.5)
score = np.where(ok, marg, -1.0)
tgt = np.argmax(score, axis=1)
gate = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000, random_state=2718).fit(feat_tr, tgt)
Ph = np.stack([sm[s] for s in ALL], axis=1)   # (n, 8)
feat_he = np.concatenate([Ph, np.abs(Ph - 0.5)], axis=1)
pick = gate.predict(feat_he)
cands["GATE16"] = Ph[np.arange(len(pick)), pick]
# gate over the 8 cheap+mlp views is above; add cheap-only gates
for tag, src_he, src_tr in (("CHEAP", CHEAP, cheap_tr), ("MLP", MLP, Pm_tr)):
    ci = [ALL.index(c) for c in src_he]
    gt = np.stack([src_tr[s.replace("cheap_", "")] if tag == "CHEAP" else src_tr[s]
                   for s in src_he], axis=1)
    gfeat = np.concatenate([gt, np.abs(gt - 0.5)], axis=1)
    okc = ((gt >= 0.5) == (y_tr[:, None] == 1))
    gtg = np.argmax(np.where(okc, np.abs(gt - 0.5), -1.0), axis=1)
    gg = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000, random_state=2718).fit(gfeat, gtg)
    ph = Ph[:, ci]
    pk = gg.predict(np.concatenate([ph, np.abs(ph - 0.5)], axis=1))
    cands[f"GATE-{tag}"] = ph[np.arange(len(pk)), pk]
    cands[f"MARGIN-{tag}"] = route_margin({s: sm[s] for s in src_he})
    cands[f"MAJ-{tag}"] = maj({s: sm[s] for s in src_he})
# logistic stack on the 8 sensor logits
L_tr = np.log(np.clip(Pt, 1e-6, 1 - 1e-6) / (1 - np.clip(Pt, 1e-6, 1 - 1e-6)))
L_he = np.log(np.clip(Ph, 1e-6, 1 - 1e-6) / (1 - np.clip(Ph, 1e-6, 1 - 1e-6)))
stk = LogisticRegression(solver="lbfgs", C=1.0, max_iter=3000, random_state=2718).fit(L_tr, y_tr)
cands["STACK16"] = stk.predict_proba(L_he)[:, 1]
Ph_all = np.stack([sm[s] for s in ALL], axis=1)
k_or = np.argmax(np.where(((Ph_all >= 0.5) == (y_he[:, None] == 1)),
                          np.abs(Ph_all - 0.5), -1.0), axis=1)
cands["ORACLE-best-per-item"] = Ph_all[np.arange(len(y_he)), k_or]

for k, p in cands.items():
    grps = {"canon": y_he == 1}
    for c in sorted(set(ch_he)):
        grps[f"d_{c}"] = ch_he == c
    g = " ".join(f"{n}:{acc(p[m], y_he[m]):.3f}" if m.sum() else f"{n}:-" for n, m in grps.items())
    print(f"  {k:12s} full {acc(p):.4f}   {g}")
