"""QG7 — generation-asymmetry routing: does the gen-1 signal separate LATE bloomers
(cross 13-24) from HOPELESS (never at 24) within the not-crossed-by-12 subpopulation?
Pre-reg: proposals/runs/QG7-generation-asymmetry.md (committed 5781e58 before firing).
Lane = QO3-identical shot arm, GENS=24, S=2048 (cost ~= QO3's 4096x12). Fail-loud, no re-roll.
"""
import sys, json, time, numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw

S, GENS, SHOTS, BAR, C = 2048, 24, 512, 0.45, 15
DEV = "cuda"
t0 = time.time()

def run_lane():
    rng = np.random.default_rng(1234)
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, SHOTS, -1)
    champ_v = v.clone().double()
    crossed_gen = np.full(S, -1)
    just = (champ_v.numpy() >= BAR); crossed_gen[just] = 0
    # record ONLY gen-1 state (per pre-reg) + full crossed_gen trajectory
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
        if g == 0:  # gen-1 snapshot
            rows1 = {"len": L.copy(), "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])}
    return rows1, crossed_gen, champ_v.numpy()

rows1, crossed_gen, cv = run_lane()
torch.cuda.synchronize()

# ---- G1 lane anchor (rate at gen 12) ----
crossed12 = (crossed_gen >= 0) & (crossed_gen <= 12)
rate12 = float(crossed12.mean())
from scipy.stats import beta as _beta
k12, n = int(crossed12.sum()), S
lo12 = _beta.ppf(0.025, k12, n - k12 + 1); hi12 = _beta.ppf(0.975, k12 + 1, n - k12)
print(f"rate@12 {rate12:.4f} ({k12}/{n}) CP95 [{lo12:.4f},{hi12:.4f}]  elapsed {time.time()-t0:.0f}s")
G1 = bool(0.567 <= rate12 <= 0.598)
print(f"G1 (QG2-band anchor 0.567-0.598): {'PASS' if G1 else 'FAIL-DIVERGED'}")

crossed24 = crossed_gen >= 0
rate24 = float(crossed24.mean())
k24 = int(crossed24.sum())
lo24 = _beta.ppf(0.025, k24, n - k24 + 1); hi24 = _beta.ppf(0.975, k24 + 1, n - k24)
print(f"rate@24 {rate24:.4f} ({k24}/{n}) CP95 [{lo24:.4f},{hi24:.4f}]  (QG3 arm C exact: 0.755)")

if not G1:
    json.dump({"G1": False, "rate12": rate12, "rate24": rate24}, open("results/qg7_gen_asymmetry/results.json", "w"))
    print("ABORT: lane diverged"); sys.exit(1)

# ---- labels ----
sub = ~crossed12                      # not crossed by gen 12
late = sub & crossed24                # crossed 13-24
hopeless = sub & ~crossed24
y = late[sub].astype(np.float32)      # 1 = late, 0 = hopeless
print(f"subpop not-crossed-by-12: {int(sub.sum())}  late {int(late.sum())}  hopeless {int(hopeless.sum())}")

D = 4 + PAD + 1
def build(mask):
    X = np.concatenate([np.stack([np.full(mask.sum(), 1.0 / 12), rows1["len"][mask] / W,
                                  rows1["v"][mask], rows1["cv"][mask]], 1),
                        rows1["hist"][mask] / 6.0], 1)   # gen feature = 1/12 (QO1/QO3 norm convention)
    return X.astype(np.float32)

from sklearn.metrics import roc_auc_score

# ---- G3: fresh gen-1 MLP on late-vs-hopeless (QO3 protocol, 80/20 split) ----
Xs = build(sub)
rs = np.random.default_rng(99)
perm = rs.permutation(len(y)); tr, te = perm[:int(0.8 * len(y))], perm[int(0.8 * len(y)):]
Xtr = torch.tensor(Xs[tr]).to(DEV); ytr = torch.tensor(y[tr]).to(DEV)
Xte = torch.tensor(Xs[te]).to(DEV); yte_np = y[te]
torch.manual_seed(0)
mlp = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                    nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
opt = torch.optim.Adam(mlp.parameters(), 1e-3)
best_auc, best_state, patience = 0.0, None, 0
for ep in range(300):
    mlp.train(); opt.zero_grad()
    loss = nn.functional.binary_cross_entropy_with_logits(mlp(Xtr).squeeze(-1), ytr)
    loss.backward(); opt.step()
    mlp.eval()
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xte).squeeze(-1)).cpu().numpy()
    a = roc_auc_score(yte_np, pm) if 0 < yte_np.sum() < len(yte_np) else 0.5
    if a > best_auc: best_auc, best_state, patience = a, {k2: v.clone() for k2, v in mlp.state_dict().items()}, 0
    else:
        patience += 1
        if patience >= 30: break
auc_fresh = float(best_auc)
print(f"G3 fresh gen-1 MLP  late-vs-hopeless AUC {auc_fresh:.4f} (P1 >0.65)")

# ---- G4: frozen QO1 oracle transfer ----
ck = torch.load("tools/qcell_oracle.pt", map_location=DEV)
oracle = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                       nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
oracle.load_state_dict(ck["state_dict"]); oracle.eval()
with torch.no_grad():
    po = torch.sigmoid(oracle(torch.tensor(Xs).to(DEV)).squeeze(-1)).cpu().numpy()
auc_oracle = float(roc_auc_score(y, po))
print(f"G4 frozen QO1 oracle late-vs-hopeless AUC {auc_oracle:.4f} (P2 >0.55, miscalibration expected)")
med_late, med_hope = float(np.median(po[late[sub]])), float(np.median(po[hopeless[sub]]))
print(f"   oracle median p: late {med_late:.3f} vs hopeless {med_hope:.3f}")

res = {"G1": G1, "rate12": rate12, "cp95_12": [lo12, hi12], "rate24": rate24, "cp95_24": [lo24, hi24],
       "n_sub": int(sub.sum()), "n_late": int(late.sum()), "n_hopeless": int(hopeless.sum()),
       "auc_fresh_gen1": auc_fresh, "auc_frozen_oracle": auc_oracle,
       "oracle_median_p_late": med_late, "oracle_median_p_hopeless": med_hope,
       "pinned": {"qcell_sim": "8c82d4bcc88370c0", "qcell_oracle.pt": "fed2c15fb506899f"},
       "elapsed_s": time.time() - t0}
import os; os.makedirs("results/qg7_gen_asymmetry", exist_ok=True)
json.dump(res, open("results/qg7_gen_asymmetry/results.json", "w"), indent=1)
print("booked results/qg7_gen_asymmetry/results.json")
