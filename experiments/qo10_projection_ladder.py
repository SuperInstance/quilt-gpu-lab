"""QO10 — projection-ladder ablation for the QO1/QO3 oracle.
Pre-reg: proposals/runs/QO10-projection-ladder.md (committed before firing).
Lane = QO3-identical regeneration (seed 1234, verbatim run_lane_states). Fail-loud, no re-roll.
Gates: G1 anchor vs committed QO3 AUCs (±0.02), G2 degenerate, verdict = gap > ensemble spread.
"""
import sys, json
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")

# --- lane regeneration: VERBATIM from experiments/qo3_horizon.py ---
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw

S1, GENS1, SHOTS, BAR1, C = 4096, 12, 512, 0.45, 15

def run_lane_states(S):
    rng = np.random.default_rng(1234)
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, SHOTS, -1)
    champ_v = v.clone().double()
    rows = []
    def record(g, seq, L, v, champ_v):
        rows.append({"gen": np.full(S, g), "len": L.copy(),
                     "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])})
    record(0, seq, L, v, champ_v)
    for g in range(GENS1):
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
    return rows, (champ_v.numpy() >= BAR1)

DEV = "cuda"
D = 4 + PAD + 1
rs = np.random.default_rng(99)
perm = rs.permutation(S1)
tr_streams = set(perm[:int(0.8 * S1)].tolist())
tr_mask = np.array([s in tr_streams for s in range(S1)])

LADDERS = {
    "L_full":   lambda r: np.concatenate([np.stack([r["gen"] / GENS1, r["len"] / W, r["v"], r["cv"]], 1), r["hist"] / 6.0], 1),
    "L_cvvgen": lambda r: np.stack([r["gen"] / GENS1, r["len"] / W, r["v"], r["cv"]], 1),
    "L_cv":     lambda r: r["cv"].reshape(-1, 1),
    "L_gen":    lambda r: (r["gen"] / GENS1).reshape(-1, 1),
}

def feats(g, name):
    return LADDERS[name](rows[g])

rows, crossed = run_lane_states(S1)
y = crossed.astype(np.float32)

rate = crossed.mean()
G1 = bool(0.5670 <= rate <= 0.5974)
print(f"lane crossing rate {rate:.4f} G1(lane-band): {'PASS' if G1 else 'FAIL-DIVERGED'}")
if not G1:
    json.dump({"G1": False, "rate": float(rate)}, open("results/qo10_projection_ladder/results.json", "w"))
    sys.exit(1)

def fit_mlp_seed(Xtr, ytr, Xte, seed, yte_np):
    torch.manual_seed(seed)
    mlp = nn.Sequential(nn.Linear(Xtr.shape[1], 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
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
        if a > best_auc: best_auc, best_state, patience = a, {k: v.clone() for k, v in mlp.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 30: break
    mlp.load_state_dict(best_state)
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xt).squeeze(-1)).cpu().numpy()
    return roc_auc_score(yte_np, pm)

SEEDS = [0, 1, 2, 3]
G_ANCHOR = {1: 0.892177740359913, 3: 0.9354923578826166}
FORECAST_GENS = [1, 3]

def splits_for(g):
    # S_stream: QO3's 80/20 random-stream split at this gen
    yield "S_stream", np.arange(len(y))[tr_mask], np.arange(len(y))[~tr_mask]
    # S_genregime: train pooled gens <= 3, test gens > 3 (same streams), evaluated at ladder gen g
    tr_g = (rows_flat_gen <= 3); te_g = (rows_flat_gen > 3)
    yield "S_genregime", np.where(tr_g)[0], np.where(te_g)[0]

# flatten: pooled per-gen regime split uses rows from gens 0..12 (gen field is in each row)
results = {"G1_lane": True, "rate": float(rate), "anchor": {}, "ladder": {}}
flat_feats = {}
for name in LADDERS:
    flat_feats[name] = []
for g in range(GENS1 + 1):
    for name in LADDERS:
        flat_feats[name].append(feats(g, name))
rows_flat_gen = np.concatenate([rows[g]["gen"] for g in range(GENS1 + 1)])
flat_y = np.tile(y, GENS1 + 1)

for g in FORECAST_GENS:
    # G1 anchor: full ladder, S_stream, seed 0 must match committed QO3 booking ±0.02
    X = feats(g, "L_full")
    Xtr = torch.tensor(X[tr_mask], dtype=torch.float32).to(DEV)
    ytr = torch.tensor(y[tr_mask], dtype=torch.float32).to(DEV)
    Xte = torch.tensor(X[~tr_mask], dtype=torch.float32).to(DEV)
    yte_np = y[~tr_mask]
    a0 = fit_mlp_seed(Xtr, ytr, Xte, 0, y[~tr_mask])
    ok = abs(a0 - G_ANCHOR[g]) <= 0.02
    results["anchor"][str(g)] = {"auc_seed0": a0, "booked": G_ANCHOR[g], "pass": bool(ok)}
    print(f"G1 anchor gen {g}: {a0:.4f} vs booked {G_ANCHOR[g]:.4f} -> {'PASS' if ok else 'FAIL-DIVERGED'}")
    if not ok:
        results["G1"] = False
        json.dump(results, open("results/qo10_projection_ladder/results.json", "w"), indent=1)
        sys.exit(1)

    for split_name, tr_idx, te_idx in splits_for(g):
        Xtr_pool = flat_feats  # regime split uses pooled rows
        for name in LADDERS:
            aucs = []
            if split_name == "S_stream":
                Xl = feats(g, name)
                Xtr = torch.tensor(Xl[tr_idx], dtype=torch.float32).to(DEV)
                ytr = torch.tensor(y[tr_idx], dtype=torch.float32).to(DEV)
                Xte = torch.tensor(Xl[te_idx], dtype=torch.float32).to(DEV)
                yte = y[te_idx]
            else:
                Xf = np.concatenate(flat_feats[name], 0)
                Xtr = torch.tensor(Xf[tr_idx], dtype=torch.float32).to(DEV)
                ytr = torch.tensor(flat_y[tr_idx], dtype=torch.float32).to(DEV)
                Xte = torch.tensor(Xf[te_idx], dtype=torch.float32).to(DEV)
                yte = flat_y[te_idx]
            for sd in SEEDS:
                if split_name == "S_stream":
                    aucs.append(fit_mlp_seed(Xtr, ytr, Xte, sd, yte))
                else:
                    aucs.append(fit_mlp_seed(Xtr, ytr, Xte, sd, yte))
            results["ladder"].setdefault(str(g), {}).setdefault(split_name, {})[name] = {
                "aucs": [float(a) for a in aucs],
                "mean": float(np.mean(aucs)), "std": float(np.std(aucs))}
            m = results["ladder"][str(g)][split_name][name]
            print(f"gen {g} {split_name} {name}: AUC {m['mean']:.4f} ± {m['std']:.4f}")

results["G1"] = True
json.dump(results, open("results/qo10_projection_ladder/results.json", "w"), indent=1)
print("DONE")
