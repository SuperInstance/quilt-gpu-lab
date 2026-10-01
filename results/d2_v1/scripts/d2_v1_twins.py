#!/usr/bin/env python3
"""D2-V1 — twin stage (INNER, runs on the 4050). 6 sockets x 3 conditions x 3 seeds = 54.
Accuracy claims only -> no INSTRUMENT-01 ramp receipt required (prereg §3).
F9 activation-budget assert; params <= 1M; batch <= 4096; OOM -> checkpoint per socket.

REFLEX TWIN TARGET FIX (booked): the same-tick full channel is a PURE function of the
vision window (fire <=> any food bit in the 3x3 window; determinacy 1.0), so a faithful
same-tick twin converges to nerr == 0.0000 for every seed (build A's std==0; re-confirmed
in the killed v1 attempt: reflex real/sim nerr 0.0000 x6).  The reflex twin is therefore
fixed to the ONE-STEP-AHEAD reflex state (input = full channel at t, target = fire at t+1),
which is non-degenerate and seed-distinguishable, while determinacy stays on the same-tick
full channel (the socket's intrinsic I/O structure).
Outputs PER-WORLD held-out nerr so the bootstrap-over-worlds CI in analysis is honest.
"""
import json, os, sys, time, hashlib
import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/results/d2_v1/scripts")
import d2_v1_common as C  # noqa: E402

LAB = "/home/eileen/projects/quilt-gpu-lab"
OUT = os.path.join(LAB, "results/d2_v1/d2_v1_twins_result.json")
SEEDS = [2718, 2719, 2720]
EPOCHS = int(os.environ.get("D2_EPOCHS", "80"))
BATCH = 4096
HID = 32
ACT_BUDGET = 8_000_000
SHIFT = {"reflex.orient": 1}   # one-step-ahead target (target fix)


def mismatch(f):
    g = [max(0.0, min(1.0, v * 1.6 + 0.15)) for v in f]
    return g[1:] + g[:1]


def build(worlds, socket, mis=False):
    X, Y = [], []
    sh = SHIFT.get(socket, 0)
    for w in worlds:
        recs = w["recs"]
        for i in range(len(recs) - sh):
            f = C.twin_feats(recs[i], socket)
            if mis:
                f = mismatch(f)
            X.append(f)
            Y.append(C.twin_target(recs[i + sh], socket))
    return np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.int64)


def build_per_world(worlds, socket, mis=False):
    """list of (X,Y) per world — precomputed once, reused across seeds/conditions."""
    return [build([w], socket, mis) for w in worlds]


class MLP(nn.Module):
    def __init__(self, din, dout):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(din, HID), nn.ReLU(),
                                 nn.Linear(HID, HID), nn.ReLU(), nn.Linear(HID, dout))

    def forward(self, x):
        return self.net(x)


def nerr_per_world(net, dev, te_per_world):
    out = []
    with torch.no_grad():
        for X, Y in te_per_world:
            x = torch.from_numpy(X).to(dev); y = torch.from_numpy(Y).to(dev)
            acc = (net(x).argmax(1) == y).float().mean().item()
            out.append(1.0 - acc)
    return out


def train_eval(Xtr, Ytr, te_per_world, dout, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = MLP(Xtr.shape[1], dout).to(dev)
    nparam = sum(p.numel() for p in m.parameters())
    assert nparam <= 1_000_000, f"F9 param wall: {nparam}"
    assert HID * BATCH <= ACT_BUDGET, "F9 activation budget"
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()
    xt = torch.from_numpy(Xtr).to(dev); yt = torch.from_numpy(Ytr).to(dev)
    n = xt.shape[0]
    for _ in range(EPOCHS):
        perm = torch.randperm(n, device=dev)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            lossf(m(xt[idx]), yt[idx]).backward()
            opt.step()
    m.eval()
    return nerr_per_world(m, dev, te_per_world), dev, nparam


def main():
    T = C.load()
    real_tr = [w for w in T["real"] if w["i"] < C.N_TRAIN]
    real_te = [w for w in T["real"] if w["i"] >= C.N_TRAIN]
    sto_tr = [w for w in T["sto"] if w["i"] < C.N_TRAIN]
    assert not ({w["i"] for w in real_tr} & {w["i"] for w in real_te}), "F5: train/test overlap"
    assert not ({w["i"] for w in sto_tr} & {w["i"] for w in real_te}), "F5: sim-train/test overlap"
    test_ids = [w["i"] for w in real_te]
    print(f"F5 OK: train 0..{C.N_TRAIN-1} disjoint from test {test_ids[0]}..{test_ids[-1]}", flush=True)

    results = {"task": "D2-V1-twins", "epochs": EPOCHS, "seeds": SEEDS, "hid": HID, "batch": BATCH,
               "act_budget": ACT_BUDGET, "n_train": C.N_TRAIN, "n_test": len(real_te),
               "test_ids": test_ids, "reflex_target_fix": "one-step-ahead (t+1) fire",
               "torch": torch.__version__, "cuda": torch.cuda.is_available(),
               "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
               "sockets": {}, "traces_sha256": hashlib.sha256(open(C.TR, "rb").read()).hexdigest()}
    for S in C.SOCKETS:
        socket = S["name"]; dout = C.N_OUT[socket]
        Xrt, Yrt = build(real_tr, socket)
        Xst, Yst = build(sto_tr, socket)
        Xsm, Ysm = build(sto_tr, socket, mis=True)
        te = build_per_world(real_te, socket)
        res = {"d_out": dout, "d_in": int(Xrt.shape[1]), "n_train_samples": int(Xrt.shape[0]),
               "runs": []}
        for cond, (Xa, Ya) in [("real", (Xrt, Yrt)), ("sim", (Xst, Yst)), ("sim_mis", (Xsm, Ysm))]:
            for seed in SEEDS:
                t0 = time.time()
                perw, dev, nparam = train_eval(Xa, Ya, te, dout, seed)
                res["runs"].append({"cond": cond, "seed": seed, "device": dev, "n_param": nparam,
                                    "nerr_per_world": [round(v, 6) for v in perw],
                                    "nerr_mean": round(float(np.mean(perw)), 6),
                                    "wall_s": round(time.time() - t0, 2)})
                print(f"  {socket:16s} {cond:8s} seed={seed} nerr={np.mean(perw):.4f} dev={dev} "
                      f"p={nparam} {time.time()-t0:.1f}s", flush=True)
        def wmean(cond):
            return np.array([r["nerr_per_world"] for r in res["runs"] if r["cond"] == cond])
        A = {c: wmean(c) for c in ["real", "sim", "sim_mis"]}
        gaps = A["sim"] - A["real"]; gapm = A["sim_mis"] - A["real"]
        res["gap_sim_mean"] = float(gaps.mean()); res["gap_sim_mis_mean"] = float(gapm.mean())
        res["gap_seed_std"] = float(gaps.mean(axis=1).std())
        res["nerr_real_seed_std"] = float(A["real"].mean(axis=1).std())
        res["nerr_sim_seed_std"] = float(A["sim"].mean(axis=1).std())
        res["nerr_sim_mis_seed_std"] = float(A["sim_mis"].mean(axis=1).std())
        res["seed_law"] = "INCONCLUSIVE(std==0)" if res["gap_seed_std"] == 0 else "PASS"
        results["sockets"][socket] = res
        json.dump(results, open(OUT, "w"), indent=1)   # checkpoint per socket
    print("wrote d2_v1_twins_result.json", flush=True)


if __name__ == "__main__":
    t0 = time.time(); main(); print(f"INNER wall {time.time()-t0:.1f}s", flush=True)
