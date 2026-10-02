#!/usr/bin/env python3
"""b1c_value_fidelity.py — lane B1C-VALUE-FIDELITY: close the deadzone/ramp deficit.

Pre-registration (FROZEN before fire): proposals/runs/B1C-value-fidelity.md.
Follow-up to the B1b RECONCILIATION (RESULTS.md keeper fold; commit 2f123d9),
which localised B1's value-fidelity deficit: saturation (88.4%) is SOLVED
(ReLU 0.9654 vs tanh 0.6759 @1e-2) and clamp is perfect; the OPEN gap is
deadzone (7.8%, all bases < 0.50 @40ep) and ramp (3.7%, unmoved by ANY basis).

Frame is B1/B1b's, VERBATIM: uniform-random reachable states, engine-driven law
labels, held out by whole trace, seed 2718.

Arms (3 seeds each, at BOTH 40 and 300 epochs):
  (relu_ref) reference ReLU net (also control C5)   — B1b's arm verbatim
  (reweight) arm (c): inverse-region-frequency MSE reweighting
  (cap)      arm (b): capacity bump 3-128-128-128-1 (2x wide, 3 hidden)
  (binned)   arm (d): softmax-over-bins head on Delta in [-1.05, 1.05], K=105

PRIMARY GATE (frozen, PER-REGION): deadzone >= 0.90 AND ramp >= 0.90 @5e-2,
3-seed mean, both std > 0. std==0 -> INCONCLUSIVE, never PASS. Aggregate is
reported, NOT the claim.

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
HARNESS = HERE / "b1c_value_fidelity_engine.mjs"
OUT_DIR = LAB / "results" / "b1c"
B1_DIR = LAB / "results" / "b1_distill"
B1B_DIR = LAB / "results" / "b1b_kink_runB"
PREREG = LAB / "proposals" / "runs" / "B1C-value-fidelity.md"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
TRACES_N = 240
TRACE_TICKS = 1200
TRACE_SEED_BASE = 900000
HOLDOUT_MOD = 5
MAX_TICKS = 20000
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)
TOL_GATED = 5e-2
REGION_GATE_MIN = 0.90
GATED_REGIONS = ("deadzone", "ramp")
MECH_DZ_LIFT, MECH_RAMP_LIFT = 0.15, 0.20   # mechanism-effect bar vs same-budget relu_ref
EPOCHS_BUDGETS = (40, 300)
BATCH = 4096
LR = 1e-3
NORM = 30.0
K_BINS = 105
BIN_LO, BIN_HI = -1.05, 1.05
WEIGHT_CLIP = (0.5, 30.0)
GUARD_TIMEOUT_S = 10800.0
FLOOR_MIB = 1024
VRAM_CEIL_MB = 1500.0
WH_ENVELOPE = 12.0
CONTROL_C5_TOL = 0.05

ARMS = ("relu_ref", "reweight", "cap", "binned")
CAP_HIDDEN = (128, 128, 128)
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
def generate_traces(eng: Engine, n_traces: int, ticks: int) -> dict:
    trace_samples, trace_meta = [], []
    for i in range(n_traces):
        seed = TRACE_SEED_BASE + i
        r = eng.send({"cmd": "collect", "seed": seed, "left": "random", "right": "random",
                      "ticks": ticks, "rngSeed": seed})
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


def build_arrays(traces: dict, n_traces: int):
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
    # holdout rule is i % HOLDOUT_MOD over ORIGINAL index; in smoke mode we keep
    # the same rule so region arithmetic is unchanged.
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
def build_model(arm: str, seed: int, device: str):
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if arm in ("relu_ref", "reweight"):
        net = nn.Sequential(nn.Linear(3, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(),
                            nn.Linear(64, 1))
    elif arm == "cap":
        layers, prev = [], 3
        for h in CAP_HIDDEN:
            layers += [nn.Linear(prev, h), nn.ReLU()]
            prev = h
        layers += [nn.Linear(prev, 1)]
        net = nn.Sequential(*layers)
    elif arm == "binned":
        net = BinnedNet()
    else:
        raise ValueError(arm)
    return net.to(device)


def _bins():
    import numpy as np
    return np.linspace(BIN_LO, BIN_HI, K_BINS, dtype=np.float64)


def _binned_cls():
    """Lazily define the binned-head module (needs torch at runtime only)."""
    import torch
    import torch.nn as nn

    class _BinnedNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(nn.Linear(3, 64), nn.ReLU(),
                                      nn.Linear(64, 64), nn.ReLU())
            self.head = nn.Linear(64, K_BINS)
            self.register_buffer("bins", torch.tensor(_bins(), dtype=torch.float32))

        def logits(self, X):
            return self.head(self.body(X))

        def forward(self, X):
            return self.logits(X)

    return _BinnedNet


def BinnedNet():
    return _binned_cls()()


def arm_predict(net, arm: str, META, device, deployed: bool = True, dtype=None):
    """torch RAW (or DEPLOYED) forward over META rows -> numpy."""
    import copy
    import numpy as np
    import torch
    dt = torch.float64 if dtype is not None else torch.float32
    if dtype is not None:
        net = copy.deepcopy(net).to(dtype)   # NEVER mutate the trained net
    p = torch.from_numpy(META[:, 0].astype(np.float64)).to(device=device, dtype=dt)
    b = torch.from_numpy(META[:, 1].astype(np.float64)).to(device=device, dtype=dt)
    with torch.no_grad():
        if arm == "binned":
            X = torch.stack([(p - 30.0) / NORM, (b - 30.0) / NORM,
                             torch.from_numpy(META[:, 2].astype(np.float64)).to(
                                 device=device, dtype=dt)], dim=1)
            idx = net.logits(X).argmax(dim=1)
            raw = net.bins.to(dt)[idx]
        else:
            s = torch.from_numpy(META[:, 2].astype(np.float64)).to(device=device, dtype=dt)
            X = torch.stack([(p - 30.0) / NORM, (b - 30.0) / NORM, s], dim=1)
            raw = net(X).squeeze(-1)
        if not deployed:
            return raw.detach().cpu().numpy().astype(np.float64)
        y = torch.clamp(p + raw, 6.0, 54.0)
        return (y - p).detach().cpu().numpy().astype(np.float64)


def region_weights(Ytr, Mtr):
    """Inverse-region-frequency sample weights, clipped, normalised to mean 1."""
    import numpy as np
    reg = region_masks(Ytr, Mtr)
    n = len(Ytr)
    freq = {k: max(float(v.sum()) / n, 1e-6) for k, v in reg.items()}
    w = np.ones(n, dtype=np.float64)
    for k, mask in reg.items():
        w[mask] = 1.0 / freq[k]
    w = np.clip(w, WEIGHT_CLIP[0], WEIGHT_CLIP[1])
    w = w / w.mean()
    return w, freq, {k: (float(w[mask].mean()) if int(mask.sum()) else 0.0)
                     for k, mask in reg.items()}


def train_one(arm: str, seed: int, Xtr, Ytr, Mtr, device: str, epochs: int, wtr=None):
    import numpy as np
    import torch
    import torch.nn as nn

    net = build_model(arm, seed, device)
    n_params = sum(q.numel() for q in net.parameters())
    opt = torch.optim.Adam(net.parameters(), lr=LR)

    p_all = torch.from_numpy(Mtr[:, 0].astype(np.float32)).to(device)
    X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = Y.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)

    W = None
    if arm == "reweight":
        if wtr is None:
            raise RuntimeError("reweight arm needs wtr")
        W = torch.from_numpy(np.asarray(wtr, dtype=np.float32)).to(device)

    bin_idx = None
    if arm == "binned":
        bins = _bins()
        lo, wbin = bins[0], bins[1] - bins[0]
        idx = np.clip(np.rint((Ytr - lo) / wbin).astype(np.int64), 0, K_BINS - 1)
        bin_idx = torch.from_numpy(idx).to(device)
        ce = nn.CrossEntropyLoss()

    mse = nn.MSELoss(reduction="none")
    hist = []
    for _ep in range(epochs):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            if arm == "binned":
                logits = net.logits(X[idx])
                loss = ce(logits, bin_idx[idx])
            else:
                out = net(X[idx]).squeeze(-1)
                pred = torch.clamp(p_all[idx] + out, 6.0, 54.0) - p_all[idx]
                se = mse(pred, Y[idx])
                loss = (se * W[idx]).mean() if arm == "reweight" else se.mean()
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    return net, {"arm": arm, "seed": seed, "epochs": epochs, "n_params": n_params,
                 "batch": BATCH, "lr": LR, "final_train_loss": hist[-1],
                 "first_train_loss": hist[0],
                 "loss": {"reweight": "weighted_mse", "binned": "cross_entropy"}.get(arm, "deployed_mse")}


def export_net(net, arm: str) -> dict:
    def layers_of(seq_linear_pairs):
        return seq_linear_pairs

    if arm == "cap":
        return {"kind": "mlp",
                "layers": [{"W": net[i].weight.detach().cpu().tolist(),
                            "b": net[i].bias.detach().cpu().tolist(), "act": "relu"}
                           for i in (0, 2, 4)],
                "Wout": net[6].weight.detach().cpu().tolist(),
                "bout": net[6].bias.detach().cpu().tolist()}
    if arm == "binned":
        return {"kind": "binned",
                "layers": [{"W": net.body[i].weight.detach().cpu().tolist(),
                            "b": net.body[i].bias.detach().cpu().tolist(), "act": "relu"}
                           for i in (0, 2)],
                "Wk": net.head.weight.detach().cpu().tolist(),
                "bk": net.head.bias.detach().cpu().tolist(),
                "bins": net.bins.detach().cpu().tolist()}
    # relu_ref / reweight — B1b's relu export format (kind 'relu')
    return {"kind": "relu",
            "W1": net[0].weight.detach().cpu().tolist(), "b1": net[0].bias.detach().cpu().tolist(),
            "W2": net[2].weight.detach().cpu().tolist(), "b2": net[2].bias.detach().cpu().tolist(),
            "W3": net[4].weight.detach().cpu().tolist(), "b3": net[4].bias.detach().cpu().tolist()}


# ── inner (guarded) run ──────────────────────────────────────────────────────
def run_inner(out_dir: Path, smoke: bool = False, resume: bool = False) -> int:
    import numpy as np
    import torch

    n_traces = 10 if smoke else TRACES_N
    ticks = 200 if smoke else TRACE_TICKS
    budgets = (2, 3) if smoke else EPOCHS_BUDGETS

    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        raise SystemExit("FAIL LOUD: CUDA unavailable — a CPU run is not the preregistered run")
    dev_name = torch.cuda.get_device_name(0)
    print(f"[env] device={device} {dev_name} torch={torch.__version__} smoke={smoke}", flush=True)

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "uniform-random reachable states (engine-driven, both paddles U{-1,0,+1}) "
                 "— B1/B1b's frame verbatim",
        "traces_n": n_traces, "trace_ticks": ticks, "trace_seed_base": TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {HOLDOUT_MOD} == 0",
        "arms": list(ARMS), "epoch_budgets": list(budgets),
        "prediction_convention": "Delta_pred = clamp(p + raw, 6, 54) - p (deployed)",
        "primary_gate": f"deadzone >= {REGION_GATE_MIN} AND ramp >= {REGION_GATE_MIN} "
                        f"@ {TOL_GATED:g}, 3-seed mean, both std>0",
        "mechanism_bar": {"deadzone_lift_vs_ref": MECH_DZ_LIFT, "ramp_lift_vs_ref": MECH_RAMP_LIFT},
        "model": {"relu_ref/reweight": "3-64-64-1 ReLU (deployed MSE; reweight=weighted MSE)",
                  "cap": f"3-{'-'.join(map(str, CAP_HIDDEN))}-1 ReLU",
                  "binned": f"3-64-64 ReLU body + softmax head K={K_BINS} on "
                            f"[{BIN_LO},{BIN_HI}] (bin {round((BIN_HI-BIN_LO)/(K_BINS-1), 4)})"},
        "regions": "clamp / deadzone (u<=1.5) / saturation (u>=s+1.5) / ramp, from law ground truth",
        "wh_envelope": WH_ENVELOPE,
        "vram_ceiling_mb": VRAM_CEIL_MB,
        "smoke": smoke,
    }, indent=2))

    eng = Engine()
    try:
        traces = generate_traces(eng, n_traces, ticks)
        label_traces(eng, traces)
        (Xtr, Ytr, Mtr), (Xho, Yho, Mho) = build_arrays(traces, n_traces)
        print(f"[data] train={Xtr.shape[0]} holdout={Xho.shape[0]}", flush=True)

        np.savez_compressed(out_dir / "holdout_samples.npz", X=Xho, Y=Yho, META=Mho)
        (out_dir / "traces_meta.json").write_text(json.dumps({
            "frame": "uniform-random reachable states", "traces_n": n_traces,
            "trace_ticks": ticks, "trace_seed_base": TRACE_SEED_BASE,
            "holdout_mod": HOLDOUT_MOD, "n_train_samples": int(Xtr.shape[0]),
            "n_holdout_samples": int(Xho.shape[0]), "traces": traces["meta"],
        }, indent=2))

        # ── control C4: frame cross-check vs B1b runB AND B1 ────────────────
        def xcheck(d):
            try:
                b = np.load(d / "holdout_samples.npz", allow_pickle=True)
                return {"ok": bool(b["X"].shape == Xho.shape and b["Y"].shape == Yho.shape
                                   and float(np.max(np.abs(b["X"] - Xho))) == 0.0
                                   and float(np.max(np.abs(b["Y"] - Yho))) == 0.0),
                        "shape_match": bool(b["X"].shape == Xho.shape),
                        "max_abs_dX": float(np.max(np.abs(b["X"] - Xho))),
                        "max_abs_dY": float(np.max(np.abs(b["Y"] - Yho))),
                        "max_abs_dMETA": float(np.max(np.abs(b["META"] - Mho)))}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": str(exc)}

        c4 = {"vs_runB": xcheck(B1B_DIR), "vs_b1": xcheck(B1_DIR)}
        if smoke:
            c4 = {"skipped": "smoke mode (frame reduced)", "vs_runB": xcheck(B1B_DIR)["ok"]
                  if (B1B_DIR / "holdout_samples.npz").exists() else None}
        print(f"[C4] {json.dumps(c4)[:300]}", flush=True)

        # ── control C1: switch-law vs pristine-law on holdout states ─────────
        eq = {"max_abs_diff": None, "skipped": "smoke"}
        if not smoke:
            sub = Mho[::max(1, len(Mho) // 4000)][:4000]
            eq = eng.send({"cmd": "laweq", "states": [
                {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
                for m in sub]})
            print(f"[C1 laweq] {eq}", flush=True)

        # ── region weights (train split) for the reweight arm ────────────────
        wtr, reg_freq_tr, reg_wmean = region_weights(Ytr, Mtr)
        print(f"[reweight] train region freq={ {k: round(v, 4) for k, v in reg_freq_tr.items()} } "
              f"mean_w={ {k: round(v, 3) for k, v in reg_wmean.items()} }", flush=True)

        # ── train every arm × seed × budget ──────────────────────────────────
        nets, train_meta, reused = {}, [], []
        for ep in budgets:
            for arm in ARMS:
                for seed in TRAIN_SEEDS:
                    mpath = out_dir / f"model_{arm}_seed{seed}_ep{ep}.pt"
                    if resume and not smoke and mpath.exists():
                        net = build_model(arm, seed, device)
                        net.load_state_dict(torch.load(mpath, map_location=device))
                        nets[(arm, seed, ep)] = net
                        tm = {"arm": arm, "seed": seed, "epochs": ep, "reused": True,
                              "path": mpath.name, "loss": "loaded_state_dict",
                              "n_params": int(sum(q.numel() for q in net.parameters()))}
                        train_meta.append(tm)
                        reused.append(mpath.name)
                        print(f"[reuse {arm:9s} {seed} ep{ep:3d}] loaded {mpath.name}", flush=True)
                        continue
                    net, tm = train_one(arm, seed, Xtr, Ytr, Mtr, device, ep, wtr=wtr)
                    nets[(arm, seed, ep)] = net
                    train_meta.append(tm)
                    torch.save(net.state_dict(), mpath)
                    print(f"[train {arm:9s} {seed} ep{ep:3d}] loss {tm['first_train_loss']:.5g} -> "
                          f"{tm['final_train_loss']:.5g} ({tm['loss']}, {tm['n_params']}p)", flush=True)
            torch.cuda.empty_cache()

        # ── control C2: JS vs torch port, per arm per side (raw outputs) ─────
        port = []
        submeta = Mho[:50000] if not smoke else Mho[:500]
        for arm in ARMS:
            ep0 = budgets[0]
            net = nets[(arm, TRAIN_SEEDS[0], ep0)]
            jsnet = export_net(net, arm)
            tpred64 = arm_predict(net, arm, submeta, device, deployed=False, dtype=torch.float64)
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
            print(f"[C2 port {p['arm']:9s} {p['side']:5s}] f64 max|d|="
                  f"{p['max_abs_diff_js_vs_torch']:.3g} f32={p['max_abs_diff_js_vs_torch_f32']:.3g}",
                  flush=True)

        # ── Gate A: per-region agreement per arm × budget ────────────────────
        reg = region_masks(Yho, Mho)
        region_counts = {k: int(v.sum()) for k, v in reg.items()}
        region_frac = {k: float(v.mean()) for k, v in reg.items()}
        print("[regions] " + json.dumps({k: round(v, 4) for k, v in region_frac.items()}), flush=True)

        def score(pred):
            diff = np.abs(pred - Yho)
            return {"curve": {f"{t:g}": float(np.mean(diff <= t)) for t in EPS},
                    "mean_abs_err": float(np.mean(diff)),
                    "rms_err": float(np.sqrt(np.mean(diff ** 2)))}

        agreement = {"tol_gated": TOL_GATED, "region_gate_min": REGION_GATE_MIN,
                     "gated_regions": list(GATED_REGIONS), "per_arm_budget": {},
                     "n_holdout": int(len(Yho))}
        regions_report = {"counts": region_counts, "frac": region_frac, "per_arm_budget": {}}
        verdicts = {}

        for ep in budgets:
            for arm in ARMS:
                per_seed, reg_preds, reg_seeds = [], {}, {r: [] for r in reg}
                all_preds = []
                for seed in TRAIN_SEEDS:
                    pr = arm_predict(nets[(arm, seed, ep)], arm, Mho, device)
                    all_preds.append(pr)
                    sc = score(pr); sc["seed"] = seed
                    per_seed.append(sc)
                    for rname, mask in reg.items():
                        if int(mask.sum()) == 0:
                            reg_seeds[rname].append({f"{t:g}": 0.0 for t in (1e-3, 1e-2, 5e-2)})
                            continue
                        reg_seeds[rname].append({
                            f"{t:g}": float(np.mean(np.abs(pr[mask] - Yho[mask]) <= t))
                            for t in (1e-3, 1e-2, 5e-2)})
                curve_mean = {f"{t:g}": float(np.mean([a["curve"][f"{t:g}"] for a in per_seed]))
                              for t in EPS}
                # per-region table
                reg_arm = {}
                for rname in reg:
                    if int(reg[ rname].sum()) == 0:
                        reg_arm[rname] = {"n": 0}
                        continue
                    d = {}
                    for t in (1e-3, 1e-2, 5e-2):
                        vals = [s[f"{t:g}"] for s in reg_seeds[rname]]
                        m, s = mean_std(vals)
                        d[f"{t:g}"] = {"mean": m, "std": s}
                    reg_arm[rname] = {"n": int(reg[rname].sum()), **d}
                # gate
                gv = {}
                for rname in GATED_REGIONS:
                    m, s = reg_arm[rname][f"{TOL_GATED:g}"]["mean"], reg_arm[rname][f"{TOL_GATED:g}"]["std"]
                    gv[rname] = {"mean": m, "std": s, "margin": m - REGION_GATE_MIN,
                                 "verdict": ("INCONCLUSIVE" if s == 0.0 else
                                             ("PASS" if m >= REGION_GATE_MIN else "FAIL"))}
                gpass = all(gv[r]["verdict"] == "PASS" for r in GATED_REGIONS)
                ginc = any(gv[r]["verdict"] == "INCONCLUSIVE" for r in GATED_REGIONS)
                verdict = "PASS" if gpass else ("INCONCLUSIVE" if ginc else "FAIL")
                verdicts[f"{arm}@ep{ep}"] = {"per_region": gv, "verdict": verdict}
                agreement["per_arm_budget"][f"{arm}@ep{ep}"] = {
                    "per_seed": per_seed, "curve_mean": curve_mean, "verdict": verdict,
                    "n_params": int(sum(q.numel() for q in nets[(arm, TRAIN_SEEDS[0], ep)].parameters())),
                    "gated": gv}
                regions_report["per_arm_budget"][f"{arm}@ep{ep}"] = reg_arm
                print(f"[gate {arm:9s} ep{ep:3d}] aggregate5e-2={curve_mean['0.05']:.4f} "
                      f"| deadzone={reg_arm['deadzone']['0.05']['mean']:.4f}"
                      f"±{reg_arm['deadzone']['0.05']['std']:.4f} "
                      f"ramp={reg_arm['ramp']['0.05']['mean']:.4f}"
                      f"±{reg_arm['ramp']['0.05']['std']:.4f} "
                      f"| sat={reg_arm['saturation']['0.05']['mean']:.4f} -> {verdict}", flush=True)

        (out_dir / "agreement.json").write_text(json.dumps(agreement, indent=2))
        (out_dir / "regions.json").write_text(json.dumps(regions_report, indent=2))

        # ── control C5: relu_ref@40ep reproduces runB relu per-region ────────
        c5 = {"ok": None, "note": "smoke or runB missing"}
        ref_ep = 40 if 40 in budgets else budgets[0]
        if not smoke and (B1B_DIR / "regions.json").exists():
            try:
                rb = json.load(open(B1B_DIR / "regions.json"))["per_arm"]["relu"]
                mine = regions_report["per_arm_budget"][f"relu_ref@ep{ref_ep}"]
                deltas = {}
                for rname in ("deadzone", "ramp", "saturation"):
                    for t in ("0.01", "0.05"):
                        deltas[f"{rname}@{t}"] = abs(mine[rname][t]["mean"] - rb[rname][t]["mean"])
                mx = max(deltas.values())
                c5 = {"ok": bool(mx < CONTROL_C5_TOL), "max_abs_delta": mx, "per_cell": deltas,
                      "tol": CONTROL_C5_TOL, "ref_budget_ep": ref_ep}
                print(f"[C5 relu_ref repro] max|Δ|={mx:.4f} ok={c5['ok']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                c5 = {"ok": False, "error": str(exc)}

        controls = {"C1_law_equivalence": eq,
                    "C1_pass": bool(eq.get("max_abs_diff") == 0.0),
                    "C2_js_vs_torch_port": port, "C2_tol": 1e-6, "C2_pass": bool(port_pass),
                    "C4_frame_cross_check": c4,
                    "C5_ref_reproduction": c5}

        # ── mechanism-effect bar vs same-budget relu_ref ─────────────────────
        mech = {}
        for ep in budgets:
            rb = regions_report["per_arm_budget"][f"relu_ref@ep{ep}"]
            for arm in ARMS:
                if arm == "relu_ref":
                    continue
                a = regions_report["per_arm_budget"][f"{arm}@ep{ep}"]
                dz = a["deadzone"]["0.05"]["mean"] - rb["deadzone"]["0.05"]["mean"]
                rp = a["ramp"]["0.05"]["mean"] - rb["ramp"]["0.05"]["mean"]
                mech[f"{arm}@ep{ep}"] = {"deadzone_lift": dz, "ramp_lift": rp,
                                         "mechanism_win": bool(dz >= MECH_DZ_LIFT and rp >= MECH_RAMP_LIFT)}

        any_pass = [k for k, v in verdicts.items() if v["verdict"] == "PASS"]
        any_mech = [k for k, v in mech.items() if v["mechanism_win"]]
        lane = "KEEP" if any_pass else ("PARTIAL" if any_mech else "KILL")

        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))
        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        result = {
            "lane": "B1C-VALUE-FIDELITY",
            "claim": "the deadzone/ramp value-fidelity deficit is clonable to >=0.90 @5e-2 in "
                     "BOTH regions by signal (reweight), capacity, or interface (binned) changes",
            "verdict": lane, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1), "vram_ceiling_mb": VRAM_CEIL_MB,
            "primary_gate": {"regions": list(GATED_REGIONS), "min": REGION_GATE_MIN,
                             "tol": TOL_GATED},
            "verdicts": verdicts, "passing_arms": any_pass, "mechanism_wins": any_mech,
            "mechanism_bar": mech,
            "regions": {"frac": region_frac, "counts": region_counts,
                        "per_arm_budget": regions_report["per_arm_budget"]},
            "reweight": {"train_freq": reg_freq_tr, "mean_weight": reg_wmean},
            "controls": controls,
            "train": train_meta,
            "resume": {"enabled": bool(resume), "reused_models": reused,
                       "n_reused": len(reused), "n_trained": len(train_meta) - len(reused)},
            "elapsed_s": round(time.time() - t0, 1),
            "artifacts": sorted(p_.name for p_ in out_dir.iterdir()),
            "smoke": smoke,
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({"verdict": lane, "passing": any_pass,
                                      "mech": any_mech, "vram_mb": round(vram_mb, 1),
                                      "elapsed_s": result["elapsed_s"]}), flush=True)
        if vram_mb > VRAM_CEIL_MB:
            print(f"WARN VRAM {vram_mb:.1f} MB > ceiling {VRAM_CEIL_MB}", flush=True)
    finally:
        eng.close()
    return 0


# ── outer (guarded) run ──────────────────────────────────────────────────────
def run_outer(out_dir: Path, smoke: bool = False, resume: bool = False) -> int:
    if smoke:
        return run_inner(out_dir, smoke=True)

    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1C-value-fidelity",
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
            {"lane": "B1C-VALUE-FIDELITY", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    if resume:
        cmd.append("--resume")
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-5000:], flush=True)
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
    out_dir = OUT_DIR
    if "--out" in args:
        out_dir = Path(args[args.index("--out") + 1])
    smoke = "--smoke" in args
    resume = "--resume" in args
    if "--inner" in args:
        return run_inner(out_dir, smoke=smoke, resume=resume)
    return run_outer(out_dir, smoke=smoke, resume=resume)


if __name__ == "__main__":
    sys.exit(main())
