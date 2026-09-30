"""QO9 — lane-vs-stream stratification of the gen-1 oracle signal.
Pre-reg: proposals/runs/QO9-lane-vs-stream-stratification.md (AMENDMENT 1; committed before firing).
Pipeline VERBATIM from experiments/qo3_horizon.py (itself a verbatim copy of oracle1.py's lane),
with per-lane mutation-draw seeds. RC-1: --out flag; embeds runner_sha256 + args + lane membership.
"""
import sys, os, json, hashlib, argparse
import numpy as np, torch, torch.nn as nn
sys.path.insert(0, "tools"); sys.path.insert(0, "experiments")
from qg2_scale_lane import PAD, W, shot_counts, skeleton_seqs, mutate_draw
from sklearn.metrics import roc_auc_score

SHOTS, C, BAR = 512, 15, 0.45
DEV = "cuda" if torch.cuda.is_available() else "cpu"
GENS = 12
LANE_SEEDS = [1234, 1235, 1236, 1237]
S = 1024
D = 4 + PAD + 1


def run_lane_states(S, lane_seed):
    rng = np.random.default_rng(lane_seed)
    seq, L = skeleton_seqs(S)
    t = torch.tensor(seq); v = shot_counts(t, SHOTS, -1)
    champ_v = v.clone().double()
    rows = []
    def record(g, seq, L, v, champ_v):
        rows.append({"gen": np.full(S, g), "len": L.copy(),
                     "v": v.numpy().copy(), "cv": champ_v.numpy().copy(),
                     "hist": np.array([np.bincount(seq[s], minlength=PAD + 1) for s in range(S)])})
    record(0, seq, L, v, champ_v)
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


def build(r):
    return np.concatenate([np.stack([r["gen"] / GENS, r["len"] / W, r["v"], r["cv"]], 1),
                           r["hist"] / 6.0], 1)


def fit_mlp(Xtr, ytr, Xte):
    torch.manual_seed(0)
    mlp = nn.Sequential(nn.Linear(D, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                        nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1)).to(DEV)
    opt = torch.optim.Adam(mlp.parameters(), 1e-3)
    Xt = torch.tensor(Xte, dtype=torch.float32).to(DEV)
    ytr_t = torch.tensor(ytr, dtype=torch.float32).to(DEV)
    Xtr_t = torch.tensor(Xtr, dtype=torch.float32).to(DEV)
    best_auc, best_state, patience = 0.0, None, 0
    for ep in range(300):
        mlp.train(); opt.zero_grad()
        loss = nn.functional.binary_cross_entropy_with_logits(mlp(Xtr_t).squeeze(-1), ytr_t)
        loss.backward(); opt.step()
        mlp.eval()
        with torch.no_grad(): pm = torch.sigmoid(mlp(Xt).squeeze(-1)).cpu().numpy()
        a = roc_auc_score(yte_np, pm)
        if a > best_auc: best_auc, best_state, patience = a, {k: vv.clone() for k, vv in mlp.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 30: break
    mlp.load_state_dict(best_state)
    with torch.no_grad(): pm = torch.sigmoid(mlp(Xt).squeeze(-1)).cpu().numpy()
    return pm, best_auc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output dir (RC-1: never write into results/ from a verification run)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    lanes = {}
    lane_rates = {}
    for ls in LANE_SEEDS:
        rows, crossed = run_lane_states(S, ls)
        rate = float(crossed.mean())
        lane_rates[ls] = rate
        print(f"lane {ls}: rate {rate:.4f}", flush=True)
        lanes[ls] = {"X1": build(rows[1]), "y": crossed.astype(np.float32)}

    # G1 fail-loud anchor
    diverged = {ls: r for ls, r in lane_rates.items() if not (0.50 <= r <= 0.65)}
    G1 = not diverged
    print(f"G1 rate-band anchor [0.50,0.65]: {'PASS' if G1 else 'FAIL ' + str(diverged)}", flush=True)
    if not G1:
        res = {"G1": False, "lane_rates": lane_rates, "diverged": diverged}
        json.dump(res, open(os.path.join(args.out, "results.json"), "w"), indent=2)
        print("ABORT: lane diverged, booking FAILED-DIVERGED"); sys.exit(1)

    # pooled: mix all lanes, stream-level 80/20
    Xall = np.concatenate([lanes[ls]["X1"] for ls in LANE_SEEDS])
    yall = np.concatenate([lanes[ls]["y"] for ls in LANE_SEEDS])
    rs = np.random.default_rng(99)
    perm = rs.permutation(len(yall))
    tr = np.zeros(len(yall), bool); tr[perm[:int(0.8 * len(yall))]] = True
    global yte_np
    yte_np = yall[~tr]
    _, pooled_auc = fit_mlp(Xall[tr], yall[tr], Xall[~tr])
    print(f"pooled AUC(g1) {pooled_auc:.4f}", flush=True)

    # lane-held-out folds
    fold_auc = {}
    for ho in LANE_SEEDS:
        tr_lanes = [ls for ls in LANE_SEEDS if ls != ho]
        Xtr = np.concatenate([lanes[ls]["X1"] for ls in tr_lanes])
        ytr = np.concatenate([lanes[ls]["y"] for ls in tr_lanes])
        Xte = lanes[ho]["X1"]; yte_np = lanes[ho]["y"]
        _, a = fit_mlp(Xtr, ytr, Xte)
        fold_auc[ho] = float(a)
        print(f"held-out lane {ho}: AUC(g1) {a:.4f}", flush=True)

    fvals = list(fold_auc.values())
    all_hi = all(a >= 0.80 for a in fvals)
    all_lo = all(a < 0.60 for a in fvals)
    if all_hi:
        verdict = "P1_STREAM_LEVEL"
    elif all_lo and pooled_auc >= 0.80:
        verdict = "P2_LANE_LEVEL"
    else:
        verdict = "INCONCLUSIVE"

    res = {
        "G1": True, "lane_rates": lane_rates,
        "pooled_auc_g1": float(pooled_auc), "lane_heldout_auc_g1": fold_auc,
        "gates_frozen": {"p1_min_fold_auc": 0.80, "p2_max_fold_auc": 0.60, "p2_min_pooled": 0.80},
        "verdict": verdict,
        "runner_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "args": vars(args), "lane_seeds": LANE_SEEDS, "S_per_lane": S, "gens": GENS,
        "lane_membership": {str(ls): S for ls in LANE_SEEDS},
        "notes": "pipeline verbatim qo3_horizon; skeleton deterministic+shared (qo5 birth-lottery); per-lane var = mutation-draw seed; gen-1 features + outcome persisted in artifact",
    }
    # persist per-lane gen-1 features + outcomes (compressed)
    np.savez_compressed(os.path.join(args.out, "lane_data_g1.npz"),
                        **{f"X1_{ls}": lanes[ls]["X1"] for ls in LANE_SEEDS},
                        **{f"y_{ls}": lanes[ls]["y"] for ls in LANE_SEEDS})
    json.dump(res, open(os.path.join(args.out, "results.json"), "w"), indent=2)
    print(f"verdict {verdict}; booked to {args.out}")


if __name__ == "__main__":
    main()
