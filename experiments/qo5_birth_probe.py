"""QO5 — birth-state insufficiency probe: WHY is g0 AUC exactly 0.500?
Uses the QO3/QO1 lane (seed 1234). Census of g0 state diversity across streams.
Pre-reg (retroactive-cheap, analysis-only on existing lane): if g0 states near-identical ->
desert-at-birth = birth LOTTERY; if diverse but uninformative -> landscape decides.
"""
import sys, json, numpy as np, torch
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw
from qo3_horizon import run_lane_states, BAR

rows, crossed = run_lane_states(4096)
r0 = rows[0]
v0, cv0, L0, h0 = r0["v"], r0["cv"], r0["len"], r0["hist"]
print("g0 len unique:", np.unique(L0), " v0 std:", v0.std(), " cv0 std:", cv0.std())
print("g0 v percentiles:", np.percentile(v0, [0, 25, 50, 75, 100]).round(4))
auc_v = None
from sklearn.metrics import roc_auc_score
auc_v = roc_auc_score(crossed, cv0)
# do crossed vs not-crossed differ in birth cv?
print("birth cv mean crossed vs not:", cv0[crossed].mean().round(5), cv0[~crossed].mean().round(5))
print("birth cv AUC:", round(auc_v, 4))
hist_var = h0.std(axis=0).mean()
print("g0 hist across-stream mean std:", round(float(hist_var), 4))

# does birth cv distribution basically collapse (all same skeleton shot noise)?
print("frac streams identical cv:", float((cv0 == cv0[0]).mean()))
res = {"cv_std": float(cv0.std()), "auc_birth_cv": float(auc_v),
       "mean_crossed": float(cv0[crossed].mean()), "mean_not": float(cv0[~crossed].mean()),
       "frac_identical_cv": float((cv0 == cv0[0]).mean()),
       "len_unique": np.unique(L0).tolist(),
       "hist_across_stream_std": float(hist_var)}
json.dump(res, open("results/qo3_horizon/qo5_birth_probe.json", "w"), indent=2)
print("booked results/qo3_horizon/qo5_birth_probe.json")
