#!/usr/bin/env python3
"""b1b_kink_head.py — lane B1b-KINK-HEAD: is B1's value-fidelity deficit representational?

Pre-registration (FROZEN before fire): proposals/runs/B1b-kink-head.md.
Follow-up to B1-DISTILL (KILL at frozen 1e-3; step-direction exact 1.0000, the
deficit is deadzone/clamp VALUE fidelity).

The teacher is the SHIPPED quilt-arcade pong derived law (`games/pong/sheet.mjs`
cell `ai.track`), executed by the engine — never reimplemented here. The trace
frame is REUSED VERBATIM from B1 (uniform-random reachable states, both paddles
U{-1,0,+1}, held out by WHOLE trace, seed 2718). Three head classes are trained
on the SAME train split and scored on the SAME holdout split, at the corrected
tolerances 1e-2 (discriminating: B1's converged tanh floor is 0.8803) and 5e-2
(the tolerance at which B1's converged control already reached 0.9904):

  arm (a) TANH      — 3-64-64-1 tanh, linear head   (B1's exact arch, re-scored)
  arm (b) RELU      — 3-64-64-1 ReLU, linear head   (piecewise-linear basis)
  arm (c) KINK-RESID— ReLU trunk -> learned deadzone d / reflex speed k (softplus)
                      + linear residual r -> clamp(p + kink + r,[6,54]) - p

All arms: 300 epochs (convergence), 3 seeds (2718/2719/2720), mean±std.
std==0 -> INCONCLUSIVE, never PASS. NEW: per-region agreement (deadzone / ramp /
saturation / clamp) for every arm. Gate B (h2h vs the law, 600 games) runs ONLY
for arms that clear BOTH tolerance gates, as a secondary.

Energy is booked by guard.py's G7 watt receipt: this script re-execs itself as the
guarded child (`--inner`) so the whole measured window is sampled.

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; O(chunk) data-gen; do NOT commit.
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
import guard  # noqa: E402  (the GPU law: preflight/run/emit_receipt)

HERE = Path(__file__).resolve().parent
HARNESS = HERE / "b1b_pong_law_engine.mjs"
DEFAULT_OUT = LAB / "results" / "b1b_kink"
PREREG = LAB / "proposals" / "runs" / "B1b-kink-head-ALT-300ep.archived-20261001.md"
# NOTE (booked): the canonical prereg path proposals/runs/B1b-kink-head.md was
# clobbered at 14:57 by a concurrent duplicate B1b subagent. This lane's frozen
# text (written 14:56, before its 15:04 fire) lives at PREREG above; its fire was
# stopped at 15:07 to deconflict and resumed with NO gate/constant changed.

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
TRACES_N = 240
TRACE_TICKS = 1200
TRACE_SEED_BASE = 900000
HOLDOUT_MOD = 5                       # trace i is holdout iff i % 5 == 0 -> 48 traces
H2H_SEEDS = list(range(2718, 2818))   # 100 seeds
MAX_TICKS = 20000
TOL_LO = 1e-2                         # discriminating gate (B1 tanh floor 0.8803)
TOL_HI = 5e-2                         # honest "near-100%" gate (B1 control 0.9904)
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)
GATE_MIN = 0.99
EPOCHS = 300
BATCH = 4096
LR = 1e-3
NORM = 30.0
PH, HFIELD = 6.0, 54.0
SIDE_SPEED = {0: 0.85, 1: 0.70}       # 0 = left, 1 = right
DEADZONE = 1.5
ARMS = ("tanh", "relu", "kink")
REGION_NAMES = ("clamp", "deadzone", "saturation", "ramp")
GUARD_TIMEOUT_S = 10800.0
FLOOR_MIB = 1024
# B1's exploratory 300-epoch control (same arch/data/seed 2718) — replication check.
B1_CTL = {"rms": 0.02077317051589489, "a1e-2": 0.8803255251292202,
          "a5e-2": 0.9904322005938634}
REPL_TOL = 1e-6


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
    var = sum((v - m) ** 2 for v in vals) / n
    return m, var ** 0.5


# ── phase 1: traces (engine-driven law labels) — frame verbatim from B1 ──────
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


# ── per-region partition (the law's own regime; frozen in the prereg) ────────
def region_ids(META, Y):
    """Mutually exclusive law-regime label per held-out tick.

    0 clamp       — the position clamp is binding AND the law still moves
    1 deadzone    — Δlaw == 0 (the |b-p|<=1.5 deadzone + clamp-at-rest at a wall)
    2 saturation  — |b-p| >= 1.5+s (no clamp): |Δlaw| == s exactly
    3 ramp        — 1.5 < |b-p| < 1.5+s (no clamp): Δlaw = sign(b-p)(|b-p|-1.5)
    """
    import numpy as np
    p = META[:, 0]
    b = META[:, 1]
    side = META[:, 2].astype(int)
    s = np.where(side == 0, SIDE_SPEED[0], SIDE_SPEED[1])
    raw = b - p
    araw = np.abs(raw)
    d0 = np.where(araw > DEADZONE,
                  np.sign(raw) * np.minimum(s, araw - DEADZONE), 0.0)
    y1 = np.clip(p + d0, PH, HFIELD)
    clamp_binding = y1 != (p + d0)
    dead = Y == 0.0
    clamp = clamp_binding & (~dead)
    sat = (araw >= DEADZONE + s) & (~clamp) & (~dead)
    ramp = (araw > DEADZONE) & (araw < DEADZONE + s) & (~clamp) & (~dead)
    reg = np.full(len(Y), -1, dtype=np.int64)
    reg[ramp] = 3
    reg[sat] = 2
    reg[dead] = 1
    reg[clamp] = 0
    if int((reg < 0).sum()) != 0:
        raise AssertionError(f"region partition incomplete: {(reg < 0).sum()} unassigned")
    return reg


# ── models ───────────────────────────────────────────────────────────────────
def build_net(arm: str, seed: int):
    """Construct an arm's net with the frozen init. arm in ARMS."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    if arm == "tanh":
        return nn.Sequential(nn.Linear(3, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(),
                             nn.Linear(64, 1))
    if arm == "relu":
        return nn.Sequential(nn.Linear(3, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                             nn.Linear(64, 1))
    raise ValueError(arm)


def _make_kink_net():
    import math

    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class _KinkNet(nn.Module):
        """ReLU trunk -> (learned deadzone d, learned reflex k via softplus) + residual r.

        Δ_pred = clamp(p + sign(b-p)*min(k, relu(|b-p| - d)) + r, [6,54]) - p
        At d=1.5, k=s, r=0 this IS the shipped law; the head is a superset of it.
        """

        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(3, 64)
            self.fc2 = nn.Linear(64, 64)
            self.hd = nn.Linear(64, 1)
            self.hk = nn.Linear(64, 1)
            self.hr = nn.Linear(64, 1)
            with torch.no_grad():
                # init: d ~ 1.5, k ~ 0.775 (between the side speeds), r ~ 0
                self.hd.weight.mul_(0.01)
                self.hd.bias.fill_(math.log(math.expm1(1.5)))          # softplus^-1(1.5)
                self.hk.weight.mul_(0.01)
                self.hk.bias.fill_(math.log(math.expm1(0.775)))        # softplus^-1(0.775)
                self.hr.weight.mul_(0.01)
                self.hr.bias.fill_(0.0)

        def forward(self, x):
            h1 = F.relu(self.fc1(x))
            h2 = F.relu(self.fc2(h1))
            d = F.softplus(self.hd(h2)).squeeze(-1)
            k = F.softplus(self.hk(h2)).squeeze(-1)
            r = self.hr(h2).squeeze(-1)
            p = NORM * (x[:, 0] + 1.0)
            b = NORM * (x[:, 1] + 1.0)
            raw = b - p
            g = torch.sign(raw) * torch.minimum(k, torch.clamp(torch.abs(raw) - d, min=0.0))
            return torch.clamp(p + g + r, PH, HFIELD) - p

    return _KinkNet()


def train_one(arm: str, seed: int, Xtr, Ytr, device: str):
    import torch
    import torch.nn as nn

    if arm == "kink":
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        net = _make_kink_net().to(device)
    else:
        net = build_net(arm, seed).to(device)
    n_params = sum(p.numel() for p in net.parameters())
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    lossf = nn.MSELoss()

    X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = X.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)
    hist = []
    for _ep in range(EPOCHS):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            loss = lossf(net(X[idx]).squeeze(-1), Y[idx])
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    return net, {"arm": arm, "seed": seed, "n_params": n_params,
                 "final_train_mse": hist[-1], "first_train_mse": hist[0],
                 "epochs": EPOCHS, "batch": BATCH, "lr": LR}


def export_net(arm: str, net) -> dict:
    import torch
    with torch.no_grad():
        if arm == "kink":
            return {"arch": "kink",
                    "W1": net.fc1.weight.cpu().numpy().tolist(),
                    "b1": net.fc1.bias.cpu().numpy().tolist(),
                    "W2": net.fc2.weight.cpu().numpy().tolist(),
                    "b2": net.fc2.bias.cpu().numpy().tolist(),
                    "Wd": net.hd.weight.cpu().numpy().tolist(),
                    "bd": net.hd.bias.cpu().numpy().tolist(),
                    "Wk": net.hk.weight.cpu().numpy().tolist(),
                    "bk": net.hk.bias.cpu().numpy().tolist(),
                    "Wr": net.hr.weight.cpu().numpy().tolist(),
                    "br": net.hr.bias.cpu().numpy().tolist()}
        return {"arch": arm,
                "W1": net[0].weight.cpu().numpy().tolist(), "b1": net[0].bias.cpu().numpy().tolist(),
                "W2": net[2].weight.cpu().numpy().tolist(), "b2": net[2].bias.cpu().numpy().tolist(),
                "W3": net[4].weight.cpu().numpy().tolist(), "b3": net[4].bias.cpu().numpy().tolist()}


def torch_forward(net, meta, dtype=None):
    import numpy as np
    import torch
    X = np.stack([[(m[0] - 30.0) / NORM, (m[1] - 30.0) / NORM, m[2]] for m in meta])
    dev = next(net.parameters()).device
    dtype = dtype or next(net.parameters()).dtype
    xt = torch.from_numpy(X.astype(np.float64)).to(device=dev, dtype=dtype)
    with torch.no_grad():
        out = net(xt)
    return out.squeeze(-1).cpu().numpy()


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
        "device_name": dev_name, "torch": torch.__version__, "lane": "B1b-KINK-HEAD",
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "uniform-random reachable states (engine-driven, both paddles U{-1,0,+1}) "
                 "— reused verbatim from B1-DISTILL",
        "traces_n": TRACES_N, "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {HOLDOUT_MOD} == 0",
        "arms": list(ARMS), "epochs": EPOCHS, "batch": BATCH, "lr": LR,
        "tol_lo": TOL_LO, "tol_hi": TOL_HI, "gate_min": GATE_MIN,
        "std_zero": "INCONCLUSIVE (never PASS)",
        "regions": list(REGION_NAMES),
        "gate_b": {"secondary": True, "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
                   "n_seeds": len(H2H_SEEDS), "max_ticks": MAX_TICKS,
                   "runs_for": "arms passing BOTH tolerance gates only"},
    }, indent=2))

    eng = Engine()
    try:
        traces = generate_traces(eng)
        label_traces(eng, traces)
        (Xtr, Ytr, Mtr), (Xho, Yho, Mho) = build_arrays(traces)
        print(f"[data] train={Xtr.shape[0]} holdout={Xho.shape[0]}", flush=True)

        reg = region_ids(Mho, Yho)
        n_reg = {REGION_NAMES[r]: int((reg == r).sum()) for r in range(4)}
        print(f"[regions] {n_reg}", flush=True)

        np.savez_compressed(out_dir / "holdout_samples.npz",
                            X=Xho, Y=Yho, META=Mho, REGION=reg.astype(np.int8),
                            trace_meta=np.array([json.dumps(m) for m in traces["meta"]]))
        (out_dir / "traces_meta.json").write_text(json.dumps({
            "frame": "uniform-random reachable states", "traces_n": TRACES_N,
            "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
            "holdout_mod": HOLDOUT_MOD, "n_train_samples": int(Xtr.shape[0]),
            "n_holdout_samples": int(Xho.shape[0]), "region_counts": n_reg,
            "traces": traces["meta"],
        }, indent=2))

        # ── control 1: switch-law vs pristine-law on holdout states
        sub = Mho[::max(1, len(Mho) // 4000)][:4000]
        eq = eng.send({"cmd": "laweq", "states": [
            {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
            for m in sub]})
        print(f"[ctrl law-equiv] max_abs_diff={eq['max_abs_diff']} n_diff={eq['n_diff']}",
              flush=True)

        # ── train 3 arms × 3 seeds
        nets, train_meta = {}, []
        for arm in ARMS:
            nets[arm] = {}
            for seed in TRAIN_SEEDS:
                net, tm = train_one(arm, seed, Xtr, Ytr, device)
                nets[arm][seed] = net
                train_meta.append(tm)
                torch.save(net.state_dict(), out_dir / f"model_{arm}_seed{seed}.pt")
                print(f"[train {arm} {seed}] mse {tm['first_train_mse']:.6g} -> "
                      f"{tm['final_train_mse']:.6g} params={tm['n_params']}", flush=True)

        # ── Gate A: agreement on held-out traces, two tolerances + per-region
        agree = {"arms": {}, "tols": {"lo": TOL_LO, "hi": TOL_HI},
                 "gate_min": GATE_MIN, "regions": list(REGION_NAMES),
                 "region_counts": n_reg}
        for arm in ARMS:
            per = []
            for seed in TRAIN_SEEDS:
                pred = torch_forward(nets[arm][seed], Mho)
                diff = np.abs(pred - Yho)
                law_letter = np.where(Yho == 0.0, "S", np.where(Yho > 0, "D", "U"))
                pred_letter = np.where(np.abs(pred) <= TOL_LO, "S",
                                       np.where(pred > 0, "D", "U"))
                moving = Yho != 0.0
                a = {
                    "arm": arm, "seed": seed, "n": int(len(Yho)),
                    "agree_lo": float(np.mean(diff <= TOL_LO)),
                    "agree_hi": float(np.mean(diff <= TOL_HI)),
                    "letter": float(np.mean(law_letter == pred_letter)),
                    "direction_where_law_moves": float(
                        np.mean(np.sign(pred[moving]) == np.sign(Yho[moving]))),
                    "mean_abs_err": float(np.mean(diff)),
                    "rms_err": float(np.sqrt(np.mean(diff ** 2))),
                    "max_abs_err": float(np.max(diff)),
                    "max_abs_pred": float(np.max(np.abs(pred))),
                    "curve": {f"{t:g}": float(np.mean(diff <= t)) for t in EPS},
                    "per_region": {REGION_NAMES[r]: {
                        "n": int((reg == r).sum()),
                        "agree_lo": (float(np.mean(diff[reg == r] <= TOL_LO))
                                     if (reg == r).sum() else None),
                        "agree_hi": (float(np.mean(diff[reg == r] <= TOL_HI))
                                     if (reg == r).sum() else None),
                    } for r in range(4)},
                }
                per.append(a)
                print(f"[gateA {arm} {seed}] @1e-2={a['agree_lo']:.6f} "
                      f"@5e-2={a['agree_hi']:.6f} "
                      f"dz={a['per_region']['deadzone']['agree_lo']} "
                      f"rms={a['rms_err']:.4g} max={a['max_abs_err']:.3g}", flush=True)

            def ms(key):
                return mean_std([a[key] for a in per])

            def _pmean(vals):
                vals = [v for v in vals if v is not None]
                return float(np.mean(vals)) if vals else None

            def _pstd(vals):
                vals = [v for v in vals if v is not None]
                return float(np.std(vals)) if vals else None

            lo_m, lo_s = ms("agree_lo")
            hi_m, hi_s = ms("agree_hi")
            armv = {
                "per_seed": per,
                "agree_lo_mean": lo_m, "agree_lo_std": lo_s,
                "agree_hi_mean": hi_m, "agree_hi_std": hi_s,
                "curve_mean": {f"{t:g}": float(np.mean([a["curve"][f"{t:g}"] for a in per]))
                               for t in EPS},
                "per_region_mean": {REGION_NAMES[r]: {
                    "n": int((reg == r).sum()),
                    "agree_lo_mean": _pmean([a["per_region"][REGION_NAMES[r]]["agree_lo"]
                                             for a in per]),
                    "agree_lo_std": _pstd([a["per_region"][REGION_NAMES[r]]["agree_lo"]
                                           for a in per]),
                    "agree_hi_mean": _pmean([a["per_region"][REGION_NAMES[r]]["agree_hi"]
                                             for a in per]),
                    "agree_hi_std": _pstd([a["per_region"][REGION_NAMES[r]]["agree_hi"]
                                           for a in per]),
                } for r in range(4)},
            }

            def gv(m, s):
                return "INCONCLUSIVE" if s == 0.0 else ("PASS" if m >= GATE_MIN else "FAIL")

            armv["gate_lo"] = gv(lo_m, lo_s)
            armv["gate_hi"] = gv(hi_m, hi_s)
            if armv["gate_lo"] == "PASS" and armv["gate_hi"] == "PASS":
                armv["verdict"] = "PASS"
            elif "INCONCLUSIVE" in (armv["gate_lo"], armv["gate_hi"]):
                armv["verdict"] = "INCONCLUSIVE"
            else:
                armv["verdict"] = "FAIL"
            agree["arms"][arm] = armv
            print(f"[arm {arm}] @1e-2 {lo_m:.6f}+-{lo_s:.6f} ({armv['gate_lo']}) | "
                  f"@5e-2 {hi_m:.6f}+-{hi_s:.6f} ({armv['gate_hi']}) -> {armv['verdict']}",
                  flush=True)
        (out_dir / "agreement.json").write_text(json.dumps(agree, indent=2))

        # ── control 2: JS vs torch port for EVERY arm, PER SIDE (B1 defect not repeated)
        submeta = [(float(m[0]), float(m[1]), float(m[2])) for m in Mho[:50000]]
        js_pairs = [[p, b] for p, b, _s in submeta]
        ports = []
        for arm in ARMS:
            net = nets[arm][TRAIN_SEEDS[0]]
            tpred = torch_forward(net, submeta)                      # float32 (the trained dtype)
            tpred64 = torch_forward(net.double(), submeta)           # float64 (matched-precision port)
            for side, sid in (("left", 0), ("right", 1)):
                eng.send({"cmd": "setnet", "side": side, "net": export_net(arm, net)})
                js = np.asarray(eng.send({"cmd": "netforward", "side": side,
                                          "pairs": js_pairs})["deltas"])
                # compare only this net's own side flag (torch_forward encodes META's side)
                idx = [i for i, mm in enumerate(submeta) if int(mm[2]) == sid]
                tsel = tpred[idx]
                tsel64 = tpred64[idx]
                jsel = js[idx]
                ports.append({"arm": arm, "side": side, "n": int(len(idx)),
                              "max_abs_diff_js_vs_torch_f64": float(np.max(np.abs(jsel - tsel64))),
                              "max_abs_diff_js_vs_torch_f32": float(np.max(np.abs(jsel - tsel)))})
                print(f"[ctrl port {arm} {side}] n={len(idx)} js-vs-t64="
                      f"{ports[-1]['max_abs_diff_js_vs_torch_f64']:.3g} js-vs-t32="
                      f"{ports[-1]['max_abs_diff_js_vs_torch_f32']:.3g}", flush=True)

        # ── control 3: replication of B1's exploratory 300-epoch control (arm a, seed 2718)
        ca = agree["arms"]["tanh"]["per_seed"][0]
        repl = {"arm": "tanh", "seed": 2718, "epochs": EPOCHS,
                "b1_control": B1_CTL,
                "reproduced": {"rms": ca["rms_err"], "a1e-2": ca["curve"]["0.01"],
                               "a5e-2": ca["curve"]["0.05"]}}
        repl["deltas"] = {k: abs(repl["reproduced"][k] - B1_CTL[k])
                          for k in ("rms", "a1e-2", "a5e-2")}
        repl["pass"] = bool(all(d < REPL_TOL for d in repl["deltas"].values()))
        print(f"[ctrl repl] deltas={repl['deltas']} pass={repl['pass']}", flush=True)

        # ── Gate B (SECONDARY): h2h for every arm that PASSed both tolerance gates
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

        # control first (different path): law vs law, sides swapped
        cw = cdl = cg = 0
        for tally in ("left", "right"):
            w, d, g = play_many(tally, "law", "law")
            cw += w; cdl += d; cg += g
        control = {"wins": cw, "draws": cdl, "games": cg,
                   "left_win_rate": cw / (cg - cdl) if (cg - cdl) else None}
        print(f"[h2h control] law-vs-law swapped win-rate={control['left_win_rate']} "
              f"draws={cdl}", flush=True)

        h2h = {"secondary": True, "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
               "n_seeds": len(H2H_SEEDS), "max_ticks": MAX_TICKS, "control": control,
               "protocol": "per seed two matches with sides swapped; win = first to 7; "
                           "rates use closed games only (draws booked); NOT a gate — "
                           "secondary corroboration for arms clearing both tolerance gates",
               "arms": {}}
        for arm in ARMS:
            if agree["arms"][arm]["verdict"] != "PASS":
                h2h["arms"][arm] = {"ran": False,
                                    "reason": f"arm verdict {agree['arms'][arm]['verdict']} "
                                              "(Gate B is secondary, runs only for arms "
                                              "clearing BOTH tolerance gates)"}
                continue
            netw = export_net(arm, nets[arm][TRAIN_SEEDS[0]])
            eng.send({"cmd": "setnet", "side": "left", "net": netw})
            eng.send({"cmd": "setnet", "side": "right", "net": netw})
            per = []
            for seed in TRAIN_SEEDS:
                # reload that seed's net into both sides
                nw = export_net(arm, nets[arm][seed])
                eng.send({"cmd": "setnet", "side": "left", "net": nw})
                eng.send({"cmd": "setnet", "side": "right", "net": nw})
                w = d = g = 0
                for tally, lm, rm in (("left", "net", "law"), ("right", "law", "net")):
                    ww, dd, gg = play_many(tally, lm, rm)
                    w += ww; d += dd; g += gg
                per.append({"seed": seed, "wins": w, "draws": d, "games": g,
                            "win_rate": (w / (g - d)) if (g - d) else None})
                print(f"[gateB {arm} {seed}] rate={per[-1]['win_rate']} wins={w} draws={d}",
                      flush=True)
            m, s = mean_std([x["win_rate"] for x in per])
            h2h["arms"][arm] = {"ran": True, "per_seed": per, "mean": m, "std": s,
                                "aggregate_wins": sum(x["wins"] for x in per),
                                "aggregate_games": sum(x["games"] for x in per),
                                "aggregate_draws": sum(x["draws"] for x in per)}
        (out_dir / "h2h.json").write_text(json.dumps(h2h, indent=2))

        controls = {
            "law_equivalence_switch_vs_pristine": eq,
            "law_equiv_pass": bool(eq["max_abs_diff"] == 0.0),
            "js_vs_torch_ports": ports,
            "js_port_tolerance": 1e-6,
            "js_port_pass": bool(all(p["max_abs_diff_js_vs_torch_f64"] < 1e-6 for p in ports)),
            "b1_control_replication": repl,
            "note": "ports compared PER SIDE (the B1 booked defect — mixed-side rows — is "
                    "not repeated); every compared row is scored with the side flag its own "
                    "net was built for. The JS evaluator is float64; the port gate is "
                    "js-vs-torch evaluated at MATCHED precision (f64), which tests that the "
                    "JS implements the identical function. The f32 column is the "
                    "evaluation-precision gap (torch float32, the trained dtype used for "
                    "Gate A) and is reported, not gated: it is ~1e-7 for the smooth arms and "
                    "~1e-6..1e-5 for the kink arm's piecewise min/softplus, i.e. far below "
                    "any action-relevant scale (a step is ~0.7 field units).",
        }
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        # ── verdict (mechanical)
        vs = {arm: agree["arms"][arm]["verdict"] for arm in ARMS}
        if any(v == "PASS" for v in vs.values()):
            verdict = "KEEP"
        elif any(v == "FAIL" for v in vs.values()):
            verdict = "KILL"
        else:
            verdict = "INCONCLUSIVE"

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        result = {
            "lane": "B1b-KINK-HEAD",
            "claim": "B1-DISTILL's residual value-fidelity deficit at the honest "
                     "tolerances is representational: a piecewise-linear / explicit "
                     "learned-kink head reaches near-100% per-tick action agreement "
                     "where the converged tanh basis floors.",
            "verdict": verdict, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1),
            "tols": {"lo": TOL_LO, "hi": TOL_HI}, "gate_min": GATE_MIN,
            "arms": {arm: {"verdict": agree["arms"][arm]["verdict"],
                           "gate_lo": agree["arms"][arm]["gate_lo"],
                           "gate_hi": agree["arms"][arm]["gate_hi"],
                           "agree_lo_mean": agree["arms"][arm]["agree_lo_mean"],
                           "agree_lo_std": agree["arms"][arm]["agree_lo_std"],
                           "agree_hi_mean": agree["arms"][arm]["agree_hi_mean"],
                           "agree_hi_std": agree["arms"][arm]["agree_hi_std"],
                           "per_region_mean": agree["arms"][arm]["per_region_mean"],
                           "curve_mean": agree["arms"][arm]["curve_mean"]}
                     for arm in ARMS},
            "region_counts": n_reg,
            "h2h": {arm: h2h["arms"][arm] for arm in ARMS},
            "h2h_control": control,
            "controls": {"law_equiv_pass": controls["law_equiv_pass"],
                         "js_port_pass": controls["js_port_pass"],
                         "b1_control_replication": repl},
            "train": train_meta,
            "elapsed_s": round(time.time() - t0, 1),
            "artifacts": sorted(p.name for p in out_dir.iterdir()),
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({k: result[k] for k in
              ("verdict", "gpu_peak_vram_mb", "elapsed_s")}), flush=True)
        print("ARMS " + json.dumps({a: result["arms"][a]["verdict"] for a in ARMS}), flush=True)
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
    print(out[-6000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-2000:], flush=True)

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
    out_dir = DEFAULT_OUT
    if "--out" in args:
        out_dir = Path(args[args.index("--out") + 1])
    if "--inner" in args:
        return run_inner(out_dir)
    return run_outer(out_dir)


if __name__ == "__main__":
    sys.exit(main())
