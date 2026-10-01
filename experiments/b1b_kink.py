#!/usr/bin/env python3
"""b1b_kink.py — lane B1b-KINK-HEAD: is the B1 distillation deficit representational?

Pre-registration (FROZEN before fire): proposals/runs/B1b-kink-head.md.
Follow-up to B1-DISTILL (KILL at frozen 1e-3; step-direction 1.0000 exact; the
deficit is deadzone/clamp VALUE fidelity — representational per B1's 300-epoch
control).

Frame is B1's, VERBATIM: uniform-random reachable states, engine-driven law
labels, held out by whole trace, seed 2718.

Arms (3 seeds each), all Gate-A actions are the DEPLOYED action
clamp(p+raw, 6, 54) - p:
  (a) tanh   — B1's net (3-64-64-1 tanh); + a B1-EXACT control arm (raw MSE /
               raw eval) that must reproduce B1's published curve.
  (b) relu   — same MLP with ReLU (piecewise-linear basis).
  (c) kink   — learned-knot hinge spline on u=|b-p| (the law's own coordinate).

Gate A: mean agreement >= 0.99 AND std > 0 at BOTH 1e-2 and 5e-2.
NEW: per-region breakdown (clamp / deadzone / saturation / ramp) per arm.
Gate B (secondary): h2h vs the law, 600 games, only for arms passing both gates.

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; do NOT commit.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import guard  # noqa: E402

HERE = Path(__file__).resolve().parent
HARNESS = HERE / "b1b_kink_engine.mjs"
OUT_DIR = LAB / "results" / "b1b_kink"
B1_DIR = LAB / "results" / "b1_distill"
PREREG = LAB / "proposals" / "runs" / "B1b-kink-head.md"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
TRACES_N = 240
TRACE_TICKS = 1200
TRACE_SEED_BASE = 900000
HOLDOUT_MOD = 5
H2H_SEEDS = list(range(2718, 2818))
MAX_TICKS = 20000
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)
TOL_GATES = (1e-2, 5e-2)          # GATED
TOL_GATE_MIN = 0.99
TOL_B1 = 1e-3                     # reported, not gated (B1's frozen tol)
GATE_B_LO, GATE_B_HI = 0.40, 0.60
EPOCHS = 40
BATCH = 4096
LR = 1e-3
NORM = 30.0
K_KNOTS = 8                       # arm (c) hinge knots
KNOT_INIT = (0.5, 1.0, 1.5, 2.0, 3.0, 4.5, 6.5, 9.0)
GUARD_TIMEOUT_S = 10800.0
FLOOR_MIB = 1024
VRAM_CEIL_MB = 1500.0

ARMS = ("tanh", "relu", "kink")                 # gated arms
CONTROL_ARM = "tanh_b1exact"                    # reproduction control (not gated)
SPEED = {"left": 0.85, "right": 0.70}
DEAD = 1.5


class Engine:
    """JSON-lines child owning the quilt-arcade engine tick (list-form subprocess)."""

    def __init__(self):
        self.proc = subprocess.Popen(
            ["node", str(HARNESS)], cwd=str(LAB), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        hello = self._read()
        if not hello.get("ok"):
            raise RuntimeError(f"harness failed to boot: {hello}")

    def _read(self) -> dict:
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("harness died (no output): " + self.proc.stderr.read()[-2000:])
        return json.loads(line)

    def send(self, msg: dict) -> dict:
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        r = self._read()
        if not r.get("ok"):
            raise RuntimeError(f"engine error on {msg.get('cmd')}: {r.get('error')}")
        return r

    def close(self):
        try:
            self.send({"cmd": "quit"})
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def mean_std(vals):
    n = len(vals)
    m = sum(vals) / n
    return m, (sum((v - m) ** 2 for v in vals) / n) ** 0.5


# ── phase 1: traces (engine-driven law labels) — B1's frame verbatim ─────────
def generate_traces(eng: Engine) -> dict:
    trace_samples, trace_meta = [], []
    for i in range(TRACES_N):
        seed = TRACE_SEED_BASE + i
        r = eng.send({"cmd": "collect", "seed": seed, "left": "random", "right": "random",
                      "ticks": TRACE_TICKS, "rngSeed": seed})
        trace_samples.append(r["samples"])
        trace_meta.append({"i": i, "seed": seed, "ticks": r["ticks"], "closed": r["over"],
                           "holdout": (i % HOLDOUT_MOD == 0)})
        if i % 40 == 0:
            print(f"[trace {i:3d}] ticks={r['ticks']} closed={r['over']}", flush=True)
    return {"samples": trace_samples, "meta": trace_meta}


def label_traces(eng: Engine, traces: dict) -> None:
    """EXECUTE the shipped law cell on every sampled state (pristine engine)."""
    for i, samples in enumerate(traces["samples"]):
        states = []
        for s in samples:
            states.append({"p": s["left"], "b": s["ballY"], "side": "left"})
            states.append({"p": s["right"], "b": s["ballY"], "side": "right"})
        d = eng.send({"cmd": "labels", "engine": "pristine", "states": states})["deltas"]
        for k, s in enumerate(samples):
            s["d_left"] = d[2 * k]
            s["d_right"] = d[2 * k + 1]
        if i % 40 == 0:
            print(f"[label {i:3d}] n={len(states)}", flush=True)


def build_arrays(traces: dict):
    import numpy as np

    def pack(sel):
        X, Y, META = [], [], []
        for s in sel:
            b = s["ballY"]
            X.append([(s["left"] - 30.0) / NORM, (b - 30.0) / NORM, 0.0])
            Y.append(s["d_left"])
            META.append((s["left"], b, 0))
            X.append([(s["right"] - 30.0) / NORM, (b - 30.0) / NORM, 1.0])
            Y.append(s["d_right"])
            META.append((s["right"], b, 1))
        return (np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.float32),
                np.asarray(META, dtype=np.float64))

    train_samples, hold_samples = [], []
    for tr, meta in zip(traces["samples"], traces["meta"]):
        (hold_samples if meta["holdout"] else train_samples).extend(tr)
    return pack(train_samples), pack(hold_samples)


# ── regions: law-regime partition of held-out ticks (arm-independent) ────────
def region_masks(Y, META):
    import numpy as np
    p = META[:, 0]
    b = META[:, 1]
    side = META[:, 2]
    u = np.abs(b - p)
    sp = np.where(side == 0, SPEED["left"], SPEED["right"])
    p_out = p + Y                              # = the law's new paddle y
    clamp = (u > DEAD) & ((p_out <= 6.0 + 1e-6) | (p_out >= 54.0 - 1e-6))
    dead = (~clamp) & (u <= DEAD)
    sat = (~clamp) & (u >= sp + DEAD)
    ramp = (~clamp) & (u > DEAD) & (u < sp + DEAD)
    return {"clamp": clamp, "deadzone": dead, "saturation": sat, "ramp": ramp}


# ── models ──────────────────────────────────────────────────────────────────
def make_kink(K: int):
    import torch
    import torch.nn as nn

    class Kink(nn.Module):
        def __init__(self, K):
            super().__init__()
            self.b0 = nn.Parameter(torch.zeros(2))
            self.W = nn.Parameter(torch.randn(2, K) * 0.1)
            self.d = nn.Parameter(torch.tensor(KNOT_INIT[:K], dtype=torch.float32))

        def raw(self, p, b, side_idx):
            z = b - p
            u = z.abs()
            sg = torch.sign(z)
            h = torch.relu(u.unsqueeze(-1) - self.d)          # [N,K]
            g = self.b0[side_idx] + (self.W[side_idx] * h).sum(-1)
            return sg * g

        def forward(self, p, b, side_idx):
            return self.raw(p, b, side_idx)

    return Kink(K)


def build_model(arm: str, seed: int, device: str):
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if arm in ("tanh", "tanh_b1exact", "relu"):
        act = nn.ReLU() if arm == "relu" else nn.Tanh()
        net = nn.Sequential(nn.Linear(3, 64), act, nn.Linear(64, 64), act, nn.Linear(64, 1))
    elif arm == "kink":
        net = make_kink(K_KNOTS)
    else:
        raise ValueError(arm)
    return net.to(device)


def arm_predict(net, arm: str, META, device, deployed: bool = True, dtype=None):
    """torch RAW (or DEPLOYED) forward over META rows -> numpy.

    dtype: optional torch dtype for the port control. The JS harness evaluates in
    float64, so the faithful JS<->torch port comparison is float64-vs-float64
    (formula identity); the float32 reference is reported alongside.
    """
    import copy
    import numpy as np
    import torch
    dt = torch.float64 if dtype is not None else torch.float32
    if dtype is not None:
        net = copy.deepcopy(net).to(dtype)   # NEVER mutate the trained net
    p = torch.from_numpy(META[:, 0].astype(np.float64)).to(device=device, dtype=dt)
    b = torch.from_numpy(META[:, 1].astype(np.float64)).to(device=device, dtype=dt)
    with torch.no_grad():
        if arm == "kink":
            si = torch.from_numpy(META[:, 2].astype(np.int64)).to(device)
            raw = net.raw(p, b, si)
        else:
            s = torch.from_numpy(META[:, 2].astype(np.float64)).to(device=device, dtype=dt)
            X = torch.stack([(p - 30.0) / NORM, (b - 30.0) / NORM, s], dim=1)
            raw = net(X).squeeze(-1)
        if not deployed:
            return raw.detach().cpu().numpy().astype(np.float64)
        y = torch.clamp(p + raw, 6.0, 54.0)
        return (y - p).detach().cpu().numpy().astype(np.float64)


def train_one(arm: str, seed: int, Xtr, Ytr, Mtr, device: str):
    import numpy as np
    import torch
    import torch.nn as nn

    net = build_model(arm, seed, device)
    n_params = sum(q.numel() for q in net.parameters())
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    lossf = nn.MSELoss()

    raw_loss = (arm == CONTROL_ARM)          # B1's exact recipe trains raw, no clamp
    p_all = torch.from_numpy(Mtr[:, 0].astype(np.float32)).to(device)
    if arm == "kink":
        b_all = torch.from_numpy(Mtr[:, 1].astype(np.float32)).to(device)
        si_all = torch.from_numpy(Mtr[:, 2].astype(np.int64)).to(device)
    else:
        X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = Y.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)

    def fwd(idx):
        if arm == "kink":
            return net.raw(p_all[idx], b_all[idx], si_all[idx])
        return net(X[idx]).squeeze(-1)

    hist = []
    for _ep in range(EPOCHS):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            out = fwd(idx)
            pred = out if raw_loss else torch.clamp(p_all[idx] + out, 6.0, 54.0) - p_all[idx]
            loss = lossf(pred, Y[idx])
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    return net, {"arm": arm, "seed": seed, "n_params": n_params,
                 "final_train_mse": hist[-1], "first_train_mse": hist[0],
                 "epochs": EPOCHS, "batch": BATCH, "lr": LR,
                 "loss": "raw" if raw_loss else "deployed"}


def export_net(net, arm: str) -> dict:
    if arm == "kink":
        return {"kind": "kink", "b0": net.b0.detach().cpu().tolist(),
                "W": net.W.detach().cpu().tolist(), "d": net.d.detach().cpu().tolist()}
    kind = "relu" if arm == "relu" else "tanh"
    return {"kind": kind,
            "W1": net[0].weight.detach().cpu().tolist(), "b1": net[0].bias.detach().cpu().tolist(),
            "W2": net[2].weight.detach().cpu().tolist(), "b2": net[2].bias.detach().cpu().tolist(),
            "W3": net[4].weight.detach().cpu().tolist(), "b3": net[4].bias.detach().cpu().tolist()}


# ── inner (guarded) run ──────────────────────────────────────────────────────
def run_inner(out_dir: Path) -> int:
    import numpy as np
    import torch

    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        raise SystemExit("FAIL LOUD: CUDA unavailable — a CPU run is not the preregistered run")
    dev_name = torch.cuda.get_device_name(0)

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "uniform-random reachable states (engine-driven, both paddles U{-1,0,+1}) "
                 "— B1's frame verbatim",
        "traces_n": TRACES_N, "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {HOLDOUT_MOD} == 0",
        "arms": list(ARMS), "control_arm": CONTROL_ARM,
        "tol_gates": list(TOL_GATES), "tol_gate_min": TOL_GATE_MIN, "tol_b1_reported": TOL_B1,
        "prediction_convention": "Delta_pred = clamp(p + raw, 6, 54) - p (deployed)",
        "model": {"tanh/relu": "3-64-64-1", "kink": f"hinge spline K={K_KNOTS}, knot init {KNOT_INIT}",
                  "epochs": EPOCHS, "batch": BATCH, "lr": LR},
        "regions": "clamp / deadzone (u<=1.5) / saturation (u>=s+1.5) / ramp, from law ground truth",
        "gate_b": {"lo": GATE_B_LO, "hi": GATE_B_HI, "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
                   "max_ticks": MAX_TICKS, "games_per_arm": 3 * len(H2H_SEEDS) * 2},
        "vram_ceiling_mb": VRAM_CEIL_MB,
    }, indent=2))

    eng = Engine()
    try:
        traces = generate_traces(eng)
        label_traces(eng, traces)
        (Xtr, Ytr, Mtr), (Xho, Yho, Mho) = build_arrays(traces)
        print(f"[data] train={Xtr.shape[0]} holdout={Xho.shape[0]}", flush=True)

        np.savez_compressed(out_dir / "holdout_samples.npz", X=Xho, Y=Yho, META=Mho)
        (out_dir / "traces_meta.json").write_text(json.dumps({
            "frame": "uniform-random reachable states", "traces_n": TRACES_N,
            "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
            "holdout_mod": HOLDOUT_MOD, "n_train_samples": int(Xtr.shape[0]),
            "n_holdout_samples": int(Xho.shape[0]), "traces": traces["meta"],
        }, indent=2))

        # ── control C4: frame cross-check vs B1's frozen holdout ─────────────
        c4 = {"ok": False, "note": "B1 holdout_samples.npz missing"}
        try:
            b1 = np.load(B1_DIR / "holdout_samples.npz", allow_pickle=True)
            c4 = {"ok": bool(b1["X"].shape == Xho.shape and b1["Y"].shape == Yho.shape
                             and float(np.max(np.abs(b1["X"] - Xho))) == 0.0
                             and float(np.max(np.abs(b1["Y"] - Yho))) == 0.0),
                  "n": int(Xho.shape[0]), "shape_match": bool(b1["X"].shape == Xho.shape),
                  "max_abs_dX": float(np.max(np.abs(b1["X"] - Xho))),
                  "max_abs_dY": float(np.max(np.abs(b1["Y"] - Yho))),
                  "max_abs_dMETA": float(np.max(np.abs(b1["META"] - Mho)))}
            print(f"[C4 frame cross-check] ok={c4['ok']} dX={c4['max_abs_dX']} "
                  f"dY={c4['max_abs_dY']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            c4 = {"ok": False, "error": str(exc)}

        # ── control C1: switch-law vs pristine-law on holdout states ─────────
        sub = Mho[::max(1, len(Mho) // 4000)][:4000]
        eq = eng.send({"cmd": "laweq", "states": [
            {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
            for m in sub]})
        print(f"[C1 laweq] {eq}", flush=True)

        # ── train every arm × seed ───────────────────────────────────────────
        nets, train_meta = {}, []
        for arm in list(ARMS) + [CONTROL_ARM]:
            for seed in TRAIN_SEEDS:
                net, tm = train_one(arm, seed, Xtr, Ytr, Mtr, device)
                nets[(arm, seed)] = net
                train_meta.append(tm)
                torch.save(net.state_dict(), out_dir / f"model_{arm}_seed{seed}.pt")
                print(f"[train {arm:12s} {seed}] mse {tm['first_train_mse']:.5g} -> "
                      f"{tm['final_train_mse']:.5g} ({tm['loss']}, {tm['n_params']}p)", flush=True)
            del net

        # ── control C2: JS vs torch port, per arm per side (raw outputs) ─────
        # Gate is on the FLOAT64-vs-FLOAT64 comparison: the JS harness evaluates
        # in float64, so this isolates FORMULA identity (what h2h actually runs).
        # The float32-vs-JS line is reported alongside for transparency.
        port = []
        submeta = Mho[:50000]
        for arm in list(ARMS) + [CONTROL_ARM]:
            net = nets[(arm, TRAIN_SEEDS[0])]
            jsnet = export_net(net, arm)
            tpred64 = arm_predict(net, arm, submeta, device, deployed=False,
                                  dtype=torch.float64)
            tpred32 = arm_predict(net, arm, submeta, device, deployed=False)
            for side, sval in (("left", 0), ("right", 1)):
                sel = submeta[:, 2] == sval
                pairs = [[float(m[0]), float(m[1])] for m in submeta[sel]]
                eng.send({"cmd": "setnet", "side": side, "net": jsnet})
                js = np.asarray(eng.send({"cmd": "netforward", "side": side,
                                          "pairs": pairs})["deltas"])
                port.append({"arm": arm, "side": side, "n": len(pairs),
                             "max_abs_diff_js_vs_torch": float(np.max(np.abs(js - tpred64[sel]))),
                             "max_abs_diff_js_vs_torch_f32": float(np.max(np.abs(js - tpred32[sel]))),
                             "max_abs_js": float(np.max(np.abs(js)))})
        port_pass = all(p["max_abs_diff_js_vs_torch"] < 1e-6 for p in port)
        for p in port:
            print(f"[C2 port {p['arm']:12s} {p['side']:5s}] f64 max|d|="
                  f"{p['max_abs_diff_js_vs_torch']:.3g} f32={p['max_abs_diff_js_vs_torch_f32']:.3g} "
                  f"max|js|={p['max_abs_js']:.3g}", flush=True)

        # ── Gate A: agreement (deployed) per arm + regions ───────────────────
        reg = region_masks(Yho, Mho)
        region_counts = {k: int(v.sum()) for k, v in reg.items()}
        region_frac = {k: float(v.mean()) for k, v in reg.items()}
        print("[regions] " + json.dumps({k: round(v, 4) for k, v in region_frac.items()}), flush=True)

        agree = {"tol_gates": list(TOL_GATES), "tol_gate_min": TOL_GATE_MIN,
                 "per_arm": {}, "n_holdout": int(len(Yho))}
        regions_report = {"counts": region_counts, "frac": region_frac, "per_arm": {}}

        def score(pred):
            diff = np.abs(pred - Yho)
            return {"curve": {f"{t:g}": float(np.mean(diff <= t)) for t in EPS},
                    "deployed_1e-3": float(np.mean(diff <= TOL_B1)),
                    "mean_abs_err": float(np.mean(diff)),
                    "rms_err": float(np.sqrt(np.mean(diff ** 2))),
                    "max_abs_err": float(np.max(diff))}

        for arm in list(ARMS) + [CONTROL_ARM]:
            per_seed, per_seed_raw = [], []
            for seed in TRAIN_SEEDS:
                net = nets[(arm, seed)]
                sc = score(arm_predict(net, arm, Mho, device, deployed=True))
                sc["seed"] = seed
                per_seed.append(sc)
                if arm == "tanh":
                    per_seed_raw.append(score(arm_predict(net, arm, Mho, device, deployed=False)))
            curve_mean = {f"{t:g}": float(np.mean([a["curve"][f"{t:g}"] for a in per_seed]))
                          for t in EPS}
            gate = {}
            for t in TOL_GATES:
                vals = [a["curve"][f"{t:g}"] for a in per_seed]
                m, s = mean_std(vals)
                gate[f"{t:g}"] = {"mean": m, "std": s,
                                  "verdict": ("INCONCLUSIVE" if s == 0.0 else
                                              ("PASS" if m >= TOL_GATE_MIN else "FAIL"))}
            arm_pass = all(gate[f"{t:g}"]["verdict"] == "PASS" for t in TOL_GATES)
            arm_inc = any(gate[f"{t:g}"]["verdict"] == "INCONCLUSIVE" for t in TOL_GATES)
            verdict = "PASS" if arm_pass else ("INCONCLUSIVE" if arm_inc else "FAIL")
            entry = {"per_seed": per_seed, "curve_mean": curve_mean, "gates": gate,
                     "verdict": verdict, "n_params": int(sum(
                         q.numel() for q in nets[(arm, TRAIN_SEEDS[0])].parameters()))}
            if arm == "tanh":
                entry["per_seed_raw"] = per_seed_raw
                entry["curve_mean_raw"] = {f"{t:g}": float(np.mean(
                    [a["curve"][f"{t:g}"] for a in per_seed_raw])) for t in EPS}
            agree["per_arm"][arm] = entry
            print(f"[gateA {arm:12s}] 1e-3={curve_mean['0.001']:.4f} 1e-2={curve_mean['0.01']:.4f} "
                  f"5e-2={curve_mean['0.05']:.4f} verdict={verdict}", flush=True)

            # per-region agreement for this arm
            reg_arm = {}
            preds = [arm_predict(nets[(arm, sd)], arm, Mho, device) for sd in TRAIN_SEEDS]
            for rname, mask in reg.items():
                if int(mask.sum()) == 0:
                    reg_arm[rname] = {"n": 0}
                    continue
                d = {}
                for t in (1e-3, 1e-2, 5e-2):
                    vals = [float(np.mean(np.abs(pr[mask] - Yho[mask]) <= t)) for pr in preds]
                    m, s = mean_std(vals)
                    d[f"{t:g}"] = {"mean": m, "std": s}
                reg_arm[rname] = {"n": int(mask.sum()), **d}
            regions_report["per_arm"][arm] = reg_arm

        agree["verdict"] = ("KEEP" if any(agree["per_arm"][a]["verdict"] == "PASS" for a in ARMS)
                            else "NEGATIVE")
        (out_dir / "agreement.json").write_text(json.dumps(agree, indent=2))
        (out_dir / "regions.json").write_text(json.dumps(regions_report, indent=2))

        # ── Gate B (secondary): h2h for arms passing BOTH gates ──────────────
        qualifying = [a for a in ARMS if agree["per_arm"][a]["verdict"] == "PASS"]
        h2h_all, control = {}, None
        if qualifying:
            def play_many(tally, left_mode, right_mode):
                wins = draws = games = 0
                for seed in H2H_SEEDS:
                    r = eng.send({"cmd": "h2h", "seed": seed, "left": left_mode,
                                  "right": right_mode, "maxTicks": MAX_TICKS})
                    games += 1
                    if not r["closed"]:
                        draws += 1
                        continue
                    if r["winner"] == tally:
                        wins += 1
                return wins, draws, games

            cw = cd = cg = 0
            for tally in ("left", "right"):
                w, d, g = play_many(tally, "law", "law")
                cw += w; cd += d; cg += g
            control = {"wins": cw, "draws": cd, "games": cg,
                       "left_win_rate": cw / (cg - cd) if (cg - cd) else None}
            print(f"[h2h control] law-vs-law swapped win-rate={control['left_win_rate']} "
                  f"draws={cd}", flush=True)

            for arm in qualifying:
                h = {"arm": arm, "per_seed": [], "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
                     "n_seeds": len(H2H_SEEDS), "max_ticks": MAX_TICKS,
                     "protocol": "per seed two matches with sides swapped; win = first to 7; "
                                 "rates use closed games only (draws booked)"}
                for seed in TRAIN_SEEDS:
                    jsnet = export_net(nets[(arm, seed)], arm)
                    eng.send({"cmd": "setnet", "side": "left", "net": jsnet})
                    eng.send({"cmd": "setnet", "side": "right", "net": jsnet})
                    w = d = g = 0
                    for tally, lm, rm in (("left", "net", "law"), ("right", "law", "net")):
                        ww, dd, gg = play_many(tally, lm, rm)
                        w += ww; d += dd; g += gg
                    rate = w / (g - d) if (g - d) else None
                    h["per_seed"].append({"seed": seed, "wins": w, "draws": d,
                                          "games": g, "win_rate": rate})
                    print(f"[gateB {arm:12s} {seed}] win_rate={rate} wins={w} draws={d} games={g}",
                          flush=True)
                m, s = mean_std([x["win_rate"] for x in h["per_seed"]])
                h["mean"], h["std"] = m, s
                h["control"] = control
                h["verdict"] = ("INCONCLUSIVE" if s == 0.0 else
                                ("PASS" if GATE_B_LO <= m <= GATE_B_HI else "FAIL"))
                h2h_all[arm] = h
                (out_dir / f"h2h_{arm}.json").write_text(json.dumps(h, indent=2))
                print(f"[gateB {arm:12s}] mean={m:.4f} std={s:.4f} verdict={h['verdict']}",
                      flush=True)
        else:
            print("[gateB] no arm passed both gates -> Gate B not run (frozen rule)", flush=True)

        controls = {"frame_cross_check_b1": c4,
                    "law_equivalence_switch_vs_pristine": eq,
                    "law_equiv_pass": bool(eq["max_abs_diff"] == 0.0),
                    "js_vs_torch_port": port, "js_port_tolerance": 1e-6,
                    "js_port_pass": bool(port_pass)}
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        lane = agree["verdict"]
        result = {
            "lane": "B1b-KINK-HEAD",
            "claim": "re-scored at 1e-2/5e-2, a kink-capable basis reaches near-100% per-tick "
                     "agreement with the pong derived law; a smooth tanh basis does not",
            "verdict": lane, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1),
            "vram_ceiling_mb": VRAM_CEIL_MB,
            "gates": {"tol_gates": list(TOL_GATES), "tol_gate_min": TOL_GATE_MIN,
                      "arm_verdicts": {a: agree["per_arm"][a]["verdict"] for a in ARMS},
                      "control_arm_verdict": agree["per_arm"][CONTROL_ARM]["verdict"]},
            "agreement": {a: {"curve_mean": agree["per_arm"][a]["curve_mean"],
                              "gates": agree["per_arm"][a]["gates"],
                              "verdict": agree["per_arm"][a]["verdict"]} for a in agree["per_arm"]},
            "regions": {"frac": region_frac, "counts": region_counts,
                        "per_arm": regions_report["per_arm"]},
            "h2h": h2h_all, "h2h_control": control, "qualifying_arms": qualifying,
            "controls": {"frame_cross_check_ok": c4.get("ok"),
                         "law_equiv_pass": bool(eq["max_abs_diff"] == 0.0),
                         "js_port_pass": bool(port_pass)},
            "train": train_meta,
            "elapsed_s": round(time.time() - t0, 1),
            "artifacts": sorted(p_.name for p_ in out_dir.iterdir()),
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({"verdict": result["verdict"],
                                      "gpu_peak_vram_mb": result["gpu_peak_vram_mb"],
                                      "elapsed_s": result["elapsed_s"]}), flush=True)
        print("ARMS " + json.dumps({a: agree["per_arm"][a]["verdict"] for a in agree["per_arm"]}),
              flush=True)
        if vram_mb > VRAM_CEIL_MB:
            print(f"WARN VRAM {vram_mb:.1f} MB > ceiling {VRAM_CEIL_MB}", flush=True)
    finally:
        eng.close()
    return 0


# ── outer (guarded) run ──────────────────────────────────────────────────────
def run_outer(out_dir: Path) -> int:
    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1b-kink-head",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed=str(MASTER_SEED), receipt_dir=str(out_dir / "guard"))

    ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60 s", flush=True)
        time.sleep(60.0)
        ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED twice: {g.breach} — booking NOT-RUN", flush=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(
            {"lane": "B1b-KINK-HEAD", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-4000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-1500:], flush=True)

    rpath, receipt = g.emit_receipt(verdict=("PASS" if rc == 0 else "VOID"),
                                    void_reason=(None if rc == 0 else f"inner rc={rc}"))
    okv, msgv = g.validate_receipt(rpath)
    print(f"guard receipt: {rpath} valid={okv} {msgv}", flush=True)
    e = (receipt or {}).get("energy", {})
    print(f"ENERGY: {e.get('watt_hours')} Wh ({e.get('joules')} J); "
          f"gate={(receipt or {}).get('gate')}", flush=True)
    return 0 if rc == 0 else 2


def main() -> int:
    args = sys.argv[1:]
    out_dir = OUT_DIR
    if "--out" in args:
        out_dir = Path(args[args.index("--out") + 1])
    if "--inner" in args:
        return run_inner(out_dir)
    return run_outer(out_dir)


if __name__ == "__main__":
    sys.exit(main())
