"""DETERM-1 — lattice-snap determinism probe over the QG7 lane.
Pre-reg: proposals/runs/DETERM-1-lattice-snap-determinism.md (frozen before fire).
Arm A: committed QG7 lane verbatim, no snap. Arm B: v/champ_v rounded to eps-grid each
selection round. Usage: determ1_lattice_snap.py <arm> <eps> <tag>
  arm in {A, B}; eps ignored for A; tag = run label for the output JSON.
"""
import sys, json, time, hashlib
import numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw

ARM, EPS, TAG = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0, sys.argv[3]
assert ARM in ("A", "B"), f"bad arm {ARM}"
SNAP = (ARM == "B")

S, GENS, SHOTS, BAR, C = 2048, 24, 512, 0.45, 15
DEV = "cuda"
t0 = time.time()


def snap(t):
    return torch.round(t / EPS) * EPS


def run_lane():
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
        if SNAP:  # the primitive under test: pin the state to the eps-lattice each round
            v = snap(v); champ_v = snap(champ_v)
        just = (champ_v.numpy() >= BAR) & (crossed_gen < 0); crossed_gen[just] = g + 1
        if g == 0:
            rows1 = {"len": L.copy(), "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])}
    return rows1, crossed_gen, champ_v.numpy()


rows1, crossed_gen, cv = run_lane()
torch.cuda.synchronize()

crossed12 = (crossed_gen >= 0) & (crossed_gen <= 12)
rate12 = float(crossed12.mean())
crossed24 = crossed_gen >= 0
rate24 = float(crossed24.mean())
ANCHOR = bool(0.567 <= rate12 <= 0.598)
print(f"[{ARM}/{TAG}] rate12 {rate12:.4f} rate24 {rate24:.4f} anchor-in-band {ANCHOR} elapsed {time.time()-t0:.0f}s")

sub = ~crossed12
late = sub & crossed24
hopeless = sub & ~crossed24
y = late[sub].astype(np.float32)

D = 4 + PAD + 1
X = np.concatenate([np.stack([np.full(sub.sum(), 1.0 / 12), rows1["len"][sub] / W,
                              rows1["v"][sub], rows1["cv"][sub]], 1),
                    rows1["hist"][sub] / 6.0], 1).astype(np.float32)

from sklearn.metrics import roc_auc_score
rs = np.random.default_rng(99)
perm = rs.permutation(len(y)); tr, te = perm[:int(0.8 * len(y))], perm[int(0.8 * len(y)):]
Xtr = torch.tensor(X[tr]).to(DEV); ytr = torch.tensor(y[tr]).to(DEV)
Xte = torch.tensor(X[te]).to(DEV); yte_np = y[te]
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
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xte).squeeze(-1)).cpu().numpy()
    a = roc_auc_score(yte_np, pm) if 0 < yte_np.sum() < len(yte_np) else 0.5
    if a > best_auc: best_auc, patience = a, 0
    else:
        patience += 1
        if patience >= 30: break
auc_fresh = float(best_auc)

ck = torch.load("tools/qcell_oracle.pt", map_location=DEV)
oracle = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                       nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
oracle.load_state_dict(ck["state_dict"]); oracle.eval()
with torch.no_grad():
    po = torch.sigmoid(oracle(torch.tensor(X).to(DEV)).squeeze(-1)).cpu().numpy()
auc_oracle = float(roc_auc_score(y, po))

rec = {
    "arm": ARM, "eps": EPS if SNAP else None, "tag": TAG,
    "rate12": rate12, "rate24": rate24, "anchor_in_band": ANCHOR,
    "subpop": int(sub.sum()), "late": int(late.sum()), "hopeless": int(hopeless.sum()),
    "auc_fresh": auc_fresh, "auc_oracle": auc_oracle,
    "crossed_gen_sha": hashlib.sha256(crossed_gen.astype(np.int64).tobytes()).hexdigest(),
    "champ_v_sha": hashlib.sha256(cv.astype(np.float64).tobytes()).hexdigest(),
    "wall_s": round(time.time() - t0, 2),
}
print(json.dumps(rec))
json.dump(rec, open(f"results/determ1_lattice_snap/{ARM}-{TAG}.json", "w"), indent=1)
