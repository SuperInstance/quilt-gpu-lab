#!/usr/bin/env python3
"""b1f_crossing_ramp_interface.py — lane B1F-CROSSING-AND-RAMP-INTERFACE.

Pre-registration (FROZEN before fire): proposals/runs/B1F-crossing-and-ramp-interface.md.

Two booked questions handed down by B1E (results/b1e/):

  Q1  NAME THE CROSSING — bisect the linear-head floor {80, 96} (plain, 3 seeds
      each) and add linear-reweight w80 to test whether the region-reweight at
      width 80 clears the ramp gate.
  Q2  IS THE RAMP AN INTERFACE PROBLEM TOO? — hybrid head v2: regression body +
      atom gates for BOTH regions (the B1D deadzone atom gate + a ramp atom gate,
      a ramp-shaped output piecewise-linear in the cue), width 64, 3 seeds.

Reuse: the B1C driver (frame gen / regions / engine / weights) is IMPORTED; the
B1C engine is reused UNCHANGED; B1D's saved width-128 anchor nets are REUSED as
controls C6/C7. B1E's safeguards are kept (prereg-arm assert + append-window
guard snapshot).

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; verdict counts ONLY preregistered arms;
append-window guard summaries; do NOT commit.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import guard  # noqa: E402

HERE = Path(__file__).resolve().parent
B1C_PY = HERE / "b1c_value_fidelity.py"
B1D_PY = HERE / "b1d_capacity_floor.py"
PREREG = LAB / "proposals" / "runs" / "B1F-crossing-and-ramp-interface.md"
OUT_DIR = LAB / "results" / "b1f"
B1C_DIR = LAB / "results" / "b1c"
B1D_DIR = LAB / "results" / "b1d"
B1E_DIR = LAB / "results" / "b1e"
B1B_DIR = LAB / "results" / "b1b_kink_runB"
B1_DIR = LAB / "results" / "b1_distill"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
DEPTH = 3                       # hidden layers (B1C cap-arm depth)
GATED_REGIONS = ("deadzone", "ramp")
REGION_GATE_MIN = 0.90
TOL_GATED = 5e-2
REPORT_TOLS = (1e-3, 1e-2, 5e-2)
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)
EPOCH = 40
BATCH = 4096
LR = 1e-3
TANH_SCALE = 1.05
BCE_LAMBDA = 1.0
RAMP_SLOPE_INIT = 1.0           # learnable; NOT the law's constants (knot init 1.0)
RAMP_KNOT_INIT = 1.0
ANCHOR_WIDTH = 128
ANCHOR_TOL = 0.05
CROSSING_WIDTHS = (80, 96)
GUARD_TIMEOUT_S = 3600.0
WH_ENVELOPE = 6.0
VRAM_CEIL_MB = 1500.0

# ── the 4 preregistered arms (frozen) ───────────────────────────────────────
ARMS = (
    ("linear_plain_w80", "linear", 80, "plain"),
    ("linear_plain_w96", "linear", 96, "plain"),
    ("linear_reweight_w80", "linear", 80, "reweight"),
    ("hybridv2_w64", "hybridv2", 64, "plain"),
)
EXPECTED_ARMS = tuple(a[0] for a in ARMS)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bc = _load("b1c_value_fidelity", B1C_PY)
bd = _load("b1d_capacity_floor", B1D_PY)
Engine = bc.Engine
generate_traces = bc.generate_traces
label_traces = bc.label_traces
build_arrays = bc.build_arrays
region_masks = bc.region_masks
region_weights = bc.region_weights
mean_std = bc.mean_std


# ── models (frozen) ─────────────────────────────────────────────────────────
def _relu_body(width: int):
    import torch.nn as nn
    layers, prev = [], 3
    for _ in range(DEPTH):
        layers += [nn.Linear(prev, width), nn.ReLU()]
        prev = width
    return nn.Sequential(*layers), prev


def _classes():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class LinearMLP(nn.Module):
        """3 hidden ReLU layers of `width` + LINEAR (identity) head (B1C cap)."""

        def __init__(self, width: int):
            super().__init__()
            self.body, prev = _relu_body(width)
            self.out = nn.Linear(prev, 1)

        def raw(self, X):
            return self.out(self.body(X)).squeeze(-1)

    class HybridV2MLP(nn.Module):
        """Body + regression head + deadzone atom gate + ramp atom gate.

        raw = (1 - g_dz) * [ (1 - g_r) * reg + g_r * ramp_atom ]
          reg       = TANH_SCALE * tanh(z_reg)        (regression head)
          g_dz      = sigmoid(z_dz)                   (deadzone atom gate)
          g_r       = sigmoid(z_r)                    (ramp atom gate)
          ramp_atom = sign(b-p) * a * relu(u - k)     (piecewise-linear in cue u)
        with u = |b-p| (the cue) and (a, k) LEARNABLE scalars.
        """

        def __init__(self, width: int):
            super().__init__()
            self.body, prev = _relu_body(width)
            self.reg = nn.Linear(prev, 1)
            self.gate_dz = nn.Linear(prev, 1)
            self.gate_r = nn.Linear(prev, 1)
            self.ramp_slope = nn.Parameter(torch.tensor(float(RAMP_SLOPE_INIT)))
            self.ramp_knot = nn.Parameter(torch.tensor(float(RAMP_KNOT_INIT)))
            self.scale = TANH_SCALE

        def gate_dz_logit(self, X):
            return self.gate_dz(self.body(X)).squeeze(-1)

        def gate_r_logit(self, X):
            return self.gate_r(self.body(X)).squeeze(-1)

        def ramp_atom(self, X):
            dp = X[:, 1] - X[:, 0]                 # (b - p) / 30
            u = torch.abs(dp) * 30.0               # cue = |b - p|
            sgn = torch.sign(dp)
            return sgn * self.ramp_slope * F.relu(u - self.ramp_knot)

        def raw(self, X):
            z = self.body(X)
            g_dz = torch.sigmoid(self.gate_dz(z)).squeeze(-1)
            g_r = torch.sigmoid(self.gate_r(z)).squeeze(-1)
            reg = self.scale * torch.tanh(self.reg(z).squeeze(-1))
            atom = self.ramp_atom(X)
            return (1.0 - g_dz) * ((1.0 - g_r) * reg + g_r * atom)

    return LinearMLP, HybridV2MLP


def build_model(kind: str, width: int, seed: int, device: str):
    import torch
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if kind == "anchor":
        # EXACTLY B1C's cap arm: 3-128-128-128-1 ReLU, linear head
        return bc.build_model("cap", seed, device)
    LinearMLP, HybridV2MLP = _classes()
    if kind == "linear":
        return LinearMLP(width).to(device)
    if kind == "hybridv2":
        return HybridV2MLP(width).to(device)
    raise ValueError(kind)


def net_raw(net, kind, X):
    if kind == "anchor":
        return net(X).squeeze(-1)
    return net.raw(X)


def predict(net, kind, META, device):
    import numpy as np
    import torch
    p = torch.from_numpy(META[:, 0].astype(np.float64)).to(device=device, dtype=torch.float32)
    b = torch.from_numpy(META[:, 1].astype(np.float64)).to(device=device, dtype=torch.float32)
    s = torch.from_numpy(META[:, 2].astype(np.float64)).to(device=device, dtype=torch.float32)
    X = torch.stack([(p - 30.0) / 30.0, (b - 30.0) / 30.0, s], dim=1)
    with torch.no_grad():
        raw = net_raw(net, kind, X)
    raw = raw.detach().cpu().numpy().astype(np.float64)
    return np.clip(META[:, 0] + raw, 6.0, 54.0) - META[:, 0]


# ── training (frozen: deployed MSE; reweight = B1C inverse-region-freq) ──────
def train_one(kind, width, seed, Xtr, Ytr, Mtr, device, epochs, wtr=None,
              dzlab=None, ramplab=None):
    import numpy as np
    import torch
    import torch.nn as nn

    net = build_model(kind, width, seed, device)
    n_params = int(sum(q.numel() for q in net.parameters()))
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    mse = nn.MSELoss(reduction="none")
    bce = nn.BCEWithLogitsLoss()
    p_all = torch.from_numpy(Mtr[:, 0].astype(np.float32)).to(device)
    X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = Y.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)
    W = torch.from_numpy(np.asarray(wtr, dtype=np.float32)).to(device) if wtr is not None else None
    ZD = torch.from_numpy(np.asarray(dzlab, dtype=np.float32)).to(device) if dzlab is not None else None
    ZR = torch.from_numpy(np.asarray(ramplab, dtype=np.float32)).to(device) if ramplab is not None else None

    hist = []
    for _ep in range(epochs):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            out = net_raw(net, kind, X[idx])
            pred = torch.clamp(p_all[idx] + out, 6.0, 54.0) - p_all[idx]
            se = mse(pred, Y[idx])
            loss = (se * W[idx]).mean() if W is not None else se.mean()
            if kind == "hybridv2":
                loss = (loss + BCE_LAMBDA * bce(net.gate_dz_logit(X[idx]), ZD[idx])
                        + BCE_LAMBDA * bce(net.gate_r_logit(X[idx]), ZR[idx]))
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    return net, {"arm_kind": kind, "width": width, "seed": seed, "epochs": epochs,
                 "n_params": n_params, "batch": BATCH, "lr": LR,
                 "tanh_scale": (TANH_SCALE if kind == "hybridv2" else None),
                 "ramp_atom": ("sign(b-p)*a*relu(|b-p|-k), a,k learned" if kind == "hybridv2" else None),
                 "final_train_loss": hist[-1], "first_train_loss": hist[0],
                 "loss": "weighted_deployed_mse" if wtr is not None else "deployed_mse"}


# ── inner (guarded) run ──────────────────────────────────────────────────────
def run_inner(out_dir: Path, smoke: bool = False, resume: bool = False) -> int:
    import numpy as np
    import torch

    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        raise SystemExit("FAIL LOUD: CUDA unavailable — a CPU run is not the preregistered run")
    dev_name = torch.cuda.get_device_name(0)
    print(f"[env] device={device} {dev_name} torch={torch.__version__} smoke={smoke}", flush=True)

    n_traces = 2 if smoke else bc.TRACES_N
    ticks = 200 if smoke else bc.TRACE_TICKS
    epochs = 3 if smoke else EPOCH

    # smoke keeps the PREREGISTERED arm names (so every analysis path runs) at
    # tiny widths; its output dir is discarded and is never a booked artifact.
    arms_spec = ([("linear_plain_w80", "linear", 16, "plain"),
                  ("linear_plain_w96", "linear", 16, "plain"),
                  ("linear_reweight_w80", "linear", 16, "reweight"),
                  ("hybridv2_w64", "hybridv2", 16, "plain")] if smoke else list(ARMS))

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(bc.HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "B1/B1b/B1C's frame verbatim (reused engine, unchanged)",
        "traces_n": n_traces, "trace_ticks": ticks, "trace_seed_base": bc.TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {bc.HOLDOUT_MOD} == 0",
        "arms": [{"name": n, "kind": k, "width": w, "weighting": wg} for n, k, w, wg in arms_spec],
        "epochs": EPOCH,
        "crossing_widths": list(CROSSING_WIDTHS),
        "hybrid_v2": ("body + reg(1.05*tanh) + deadzone atom gate sigmoid + ramp atom gate; "
                      "ramp atom = sign(b-p)*a*relu(|b-p|-k), (a,k) learned; "
                      "raw=(1-g_dz)*((1-g_r)*reg+g_r*atom)"),
        "primary_gate": f"deadzone >= {REGION_GATE_MIN} AND ramp >= {REGION_GATE_MIN} "
                        f"@ {TOL_GATED:g}, 3-seed mean, both std>0",
        "control_anchor": f"width-{ANCHOR_WIDTH} linear-head plain == B1C cap arm, "
                          f"C6/C7 reused from B1D nets",
        "verdict_counts": "PREREGISTERED ARMS ONLY (4); anchor = control",
        "prediction_convention": "Delta_pred = clamp(p + raw, 6, 54) - p (deployed)",
        "regions": "clamp / deadzone (u<=1.5) / saturation (u>=s+1.5) / ramp, from law ground truth",
        "wh_envelope": WH_ENVELOPE, "vram_ceiling_mb": VRAM_CEIL_MB, "smoke": smoke,
    }, indent=2))

    eng = Engine()
    resumed = []
    try:
        traces = generate_traces(eng, n_traces, ticks)
        label_traces(eng, traces)
        (Xtr, Ytr, Mtr), (Xho, Yho, Mho) = build_arrays(traces, n_traces)
        print(f"[data] train={Xtr.shape[0]} holdout={Xho.shape[0]}", flush=True)
        np.savez_compressed(out_dir / "holdout_samples.npz", X=Xho, Y=Yho, META=Mho)
        (out_dir / "traces_meta.json").write_text(json.dumps({
            "frame": "B1/B1b/B1C verbatim", "traces_n": n_traces, "trace_ticks": ticks,
            "trace_seed_base": bc.TRACE_SEED_BASE, "holdout_mod": bc.HOLDOUT_MOD,
            "n_train_samples": int(Xtr.shape[0]), "n_holdout_samples": int(Xho.shape[0]),
            "traces": traces["meta"]}, indent=2))

        # ── control C4: frame cross-check vs B1C/B1E/runB/B1 ────────────────
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

        c4 = {"vs_b1c": xcheck(B1C_DIR), "vs_b1e": xcheck(B1E_DIR),
              "vs_runB": xcheck(B1B_DIR), "vs_b1": xcheck(B1_DIR)}
        print(f"[C4] {json.dumps(c4)[:400]}", flush=True)

        # ── control C1: switch-law vs pristine-law on holdout states ─────────
        sub = Mho[::max(1, len(Mho) // 4000)][:4000]
        eq = eng.send({"cmd": "laweq", "states": [
            {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
            for m in sub]})
        print(f"[C1 laweq] {eq}", flush=True)

        # ── weights + atom labels (train split, B1C mechanisms) ─────────────
        wtr, reg_freq_tr, reg_wmean = region_weights(Ytr, Mtr)
        reg_tr = region_masks(Ytr, Mtr)
        dz_tr = reg_tr["deadzone"].astype(np.float32)
        ramp_tr = reg_tr["ramp"].astype(np.float32)
        print(f"[reweight] train freq={ {k: round(v, 4) for k, v in reg_freq_tr.items()} } "
              f"mean_w={ {k: round(v, 3) for k, v in reg_wmean.items()} }", flush=True)
        print(f"[atoms] train deadzone={int(dz_tr.sum())} ramp={int(ramp_tr.sum())}", flush=True)

        def tm_weights(weighting):
            return wtr if weighting == "reweight" else None

        # ── reuse B1D's width-128 LINEAR-head anchor nets (controls C6/C7) ──
        nets, train_meta = {}, []
        for seed in TRAIN_SEEDS:
            apath = B1D_DIR / f"model_anchor_cap128_seed{seed}_ep40.pt"
            net = build_model("anchor", ANCHOR_WIDTH, seed, device)
            net.load_state_dict(torch.load(apath, map_location=device))
            nets[("anchor_cap128", seed)] = net
            resumed.append(str(apath))
            print(f"[reuse anchor_cap128 {seed}] loaded {apath.name}", flush=True)

        # ── train the 12 preregistered nets ─────────────────────────────────
        for name, kind, width, weighting in arms_spec:
            for seed in TRAIN_SEEDS:
                mpath = out_dir / f"model_{name}_seed{seed}_ep{EPOCH}.pt"
                if resume and mpath.exists():
                    net = build_model(kind, width, seed, device)
                    net.load_state_dict(torch.load(mpath, map_location=device))
                    nets[(name, seed)] = net
                    resumed.append(mpath.name)
                    print(f"[reuse {name:20s} {seed}] loaded", flush=True)
                    continue
                net, tm = train_one(kind, width, seed, Xtr, Ytr, Mtr, device, epochs,
                                    wtr=tm_weights(weighting),
                                    dzlab=(dz_tr if kind == "hybridv2" else None),
                                    ramplab=(ramp_tr if kind == "hybridv2" else None))
                nets[(name, seed)] = net
                tm["name"] = name
                tm["weighting"] = weighting
                train_meta.append(tm)
                torch.save(net.state_dict(), mpath)
                extra = ""
                if kind == "hybridv2":
                    extra = (f" [atom a={float(net.ramp_slope.detach()):.3f} "
                             f"k={float(net.ramp_knot.detach()):.3f}]")
                print(f"[train {name:20s} {seed}] {tm['first_train_loss']:.5g} -> "
                      f"{tm['final_train_loss']:.5g} ({tm['n_params']}p, {tm['loss']}){extra}", flush=True)

        # ── regions + scoring helpers ───────────────────────────────────────
        reg = region_masks(Yho, Mho)
        region_counts = {k: int(v.sum()) for k, v in reg.items()}
        region_frac = {k: float(v.mean()) for k, v in reg.items()}
        print("[regions] " + json.dumps({k: round(v, 4) for k, v in region_frac.items()}), flush=True)

        def score_arm(name, kind):
            reg_seeds = {r: [] for r in reg}
            curves = []
            for seed in TRAIN_SEEDS:
                pr = predict(nets[(name, seed)], kind, Mho, device)
                diff = np.abs(pr - Yho)
                curves.append({f"{t:g}": float(np.mean(diff <= t)) for t in EPS})
                for rname, mask in reg.items():
                    if int(mask.sum()) == 0:
                        reg_seeds[rname].append({f"{t:g}": 0.0 for t in REPORT_TOLS})
                        continue
                    reg_seeds[rname].append({f"{t:g}": float(np.mean(np.abs(pr[mask] - Yho[mask]) <= t))
                                             for t in REPORT_TOLS})
            reg_arm, gv = {}, {}
            for rname in reg:
                if int(reg[rname].sum()) == 0:
                    reg_arm[rname] = {"n": 0}
                    continue
                reg_arm[rname] = {"n": int(reg[rname].sum())}
                for t in REPORT_TOLS:
                    m, s = mean_std([x[f"{t:g}"] for x in reg_seeds[rname]])
                    reg_arm[rname][f"{t:g}"] = {"mean": m, "std": s}
            for rname in GATED_REGIONS:
                m = reg_arm[rname][f"{TOL_GATED:g}"]["mean"]
                s = reg_arm[rname][f"{TOL_GATED:g}"]["std"]
                gv[rname] = {"mean": m, "std": s, "margin": m - REGION_GATE_MIN,
                             "verdict": ("INCONCLUSIVE" if s == 0.0 else
                                         ("PASS" if m >= REGION_GATE_MIN else "FAIL"))}
            gpass = all(gv[r]["verdict"] == "PASS" for r in GATED_REGIONS)
            ginc = any(gv[r]["verdict"] == "INCONCLUSIVE" for r in GATED_REGIONS)
            verdict = "PASS" if gpass else ("INCONCLUSIVE" if ginc else "FAIL")
            curve_mean = {f"{t:g}": float(np.mean([c[f"{t:g}"] for c in curves])) for t in EPS}
            return {"regions": reg_arm, "gated": gv, "verdict": verdict, "curve_mean": curve_mean,
                    "n_params": int(sum(q.numel() for q in nets[(name, TRAIN_SEEDS[0])].parameters()))}

        scored, verdicts = {}, {}
        specs = arms_spec + [("anchor_cap128", "anchor", ANCHOR_WIDTH, "plain")]
        for name, kind, width, weighting in specs:
            r = score_arm(name, kind)
            scored[name] = r
            verdicts[name] = {"kind": kind, "width": width, "weighting": weighting,
                              "regions": r["regions"], "gated": r["gated"], "verdict": r["verdict"],
                              "n_params": r["n_params"]}
            tag = "CONTROL" if kind == "anchor" else "arm"
            print(f"[gate {name:20s}] {tag:7s} dz={r['regions']['deadzone']['0.05']['mean']:.4f}"
                  f"±{r['regions']['deadzone']['0.05']['std']:.4f} "
                  f"ramp={r['regions']['ramp']['0.05']['mean']:.4f}"
                  f"±{r['regions']['ramp']['0.05']['std']:.4f} "
                  f"sat={r['regions']['saturation']['0.05']['mean']:.4f} "
                  f"agg={r['curve_mean']['0.05']:.4f} -> {r['verdict']}", flush=True)

        # ── Q1: the named crossing (plain linear, {80,96}) ──────────────────
        plain_pass = [w for w in CROSSING_WIDTHS
                      if verdicts[f"linear_plain_w{w}"]["verdict"] == "PASS"]
        crossing = min(plain_pass) if plain_pass else None
        crossing_stmt = (f"CROSSING = {crossing} (plain linear head, 40ep)"
                         if crossing is not None
                         else f"CROSSING > {max(CROSSING_WIDTHS)} (no plain linear arm <= {max(CROSSING_WIDTHS)} clears both gates)")
        # reweight@80
        rw80 = verdicts["linear_reweight_w80"]
        rw80_ramp = scored["linear_reweight_w80"]["regions"]["ramp"]["0.05"]["mean"]
        pl80_ramp = scored["linear_plain_w80"]["regions"]["ramp"]["0.05"]["mean"]
        reweight80 = {"verdict": rw80["verdict"], "ramp@5e-2": rw80_ramp,
                      "deadzone@5e-2": scored["linear_reweight_w80"]["regions"]["deadzone"]["0.05"]["mean"],
                      "plain_w80_ramp@5e-2": pl80_ramp, "ramp_lift_vs_plain": rw80_ramp - pl80_ramp,
                      "clears_ramp_gate": bool(rw80_ramp >= REGION_GATE_MIN),
                      "clears_both_gates": bool(rw80["verdict"] == "PASS")}

        # ── Q2: interface verdict from hybridv2_w64 ─────────────────────────
        hv = verdicts["hybridv2_w64"]
        hv_dz = hv["gated"]["deadzone"]["verdict"]
        hv_rp = hv["gated"]["ramp"]["verdict"]
        hv_dz_v = scored["hybridv2_w64"]["regions"]["deadzone"]
        hv_rp_v = scored["hybridv2_w64"]["regions"]["ramp"]
        if hv_dz == "PASS" and hv_rp == "PASS":
            iface_verdict = "INTERFACE"
            iface_stmt = ("both regions are interface problems at 40ep; the capacity floor is "
                          "an interface story")
        elif hv_dz == "PASS" and hv_rp == "FAIL":
            iface_verdict = "REPRESENTATIONAL"
            iface_stmt = ("the ramp resists the ramp atom gate; the ramp is genuinely "
                          "representational at 40ep")
        else:
            iface_verdict = "INCONCLUSIVE"
            iface_stmt = ("hybrid-v2 deadzone gate did not clear — interface reading "
                          "inconclusive at w64")
        interface = {"arm": "hybridv2_w64", "verdict": hv["verdict"],
                     "deadzone_verdict": hv_dz, "ramp_verdict": hv_rp,
                     "deadzone@5e-2": hv_dz_v["0.05"]["mean"], "deadzone@5e-2_std": hv_dz_v["0.05"]["std"],
                     "ramp@5e-2": hv_rp_v["0.05"]["mean"], "ramp@5e-2_std": hv_rp_v["0.05"]["std"],
                     "deadzone@1e-2": hv_dz_v["0.01"]["mean"], "ramp@1e-2": hv_rp_v["0.01"]["mean"],
                     "reference": {"b1d_hybrid_w64_dz@5e-2": 0.9998, "b1d_hybrid_w64_ramp@5e-2": 0.8042,
                                   "b1e_plain_w64_ramp@5e-2": 0.5675, "b1e_reweight_w64_ramp@5e-2": 0.7977},
                     "reading": iface_verdict, "statement": iface_stmt}

        # ── ramp-only table (frozen headline) ───────────────────────────────
        ramp_only = {"rows": {}, "note": "ramp-region fidelity per arm (3-seed mean±std)"}
        for name, kind, width, weighting in arms_spec:
            rr = scored[name]["regions"]["ramp"]
            ramp_only["rows"][name] = {
                "kind": kind, "width": width, "weighting": weighting,
                "ramp@5e-2": rr["0.05"]["mean"], "ramp@5e-2_std": rr["0.05"]["std"],
                "ramp@1e-2": rr["0.01"]["mean"], "ramp@1e-2_std": rr["0.01"]["std"],
                "ramp@1e-3": rr[f"{1e-3:g}"]["mean"], "ramp@1e-3_std": rr[f"{1e-3:g}"]["std"],
                "clears_ramp_gate@5e-2": bool(rr["0.05"]["mean"] >= REGION_GATE_MIN
                                              and rr["0.05"]["std"] > 0)}
        ramp_only["best_ramp_arm"] = max(
            ramp_only["rows"].items(), key=lambda kv: kv[1]["ramp@5e-2"])[0]

        # ── control C6: anchor == B1C cap@ep40 (booked) ─────────────────────
        c6 = {"ok": None, "note": "B1C regions.json missing"}
        try:
            rb = json.load(open(B1C_DIR / "regions.json"))["per_arm_budget"]["cap@ep40"]
            mine = scored["anchor_cap128"]["regions"]
            deltas = {}
            for rname in ("deadzone", "ramp", "saturation"):
                for t in ("0.01", "0.05"):
                    deltas[f"{rname}@{t}"] = abs(mine[rname][t]["mean"] - rb[rname][t]["mean"])
            mx = max(deltas.values())
            c6 = {"ok": bool(mx < ANCHOR_TOL), "max_abs_delta": mx, "per_cell": deltas,
                  "tol": ANCHOR_TOL, "booked_ref": "results/b1c cap@ep40",
                  "note": "anchor nets REUSED from results/b1d (bit-identical frame)"}
            print(f"[C6 anchor repro vs B1C] max|Δ|={mx:.5f} ok={c6['ok']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            c6 = {"ok": False, "error": str(exc)}

        # ── control C7: anchor nets re-score == B1D booked anchor cells ─────
        c7 = {"ok": None, "note": "B1D regions.json missing"}
        try:
            bd_reg = json.load(open(B1D_DIR / "regions.json"))["per_arm"]["anchor_cap128"]["regions"]
            mine = scored["anchor_cap128"]["regions"]
            deltas = {}
            for rname in ("deadzone", "ramp", "saturation"):
                for t in ("0.01", "0.05"):
                    deltas[f"{rname}@{t}"] = abs(mine[rname][t]["mean"] - bd_reg[rname][t]["mean"])
            mx = max(deltas.values())
            c7 = {"ok": bool(mx < 1e-6), "max_abs_delta": mx, "per_cell": deltas,
                  "tol": 1e-6, "booked_ref": "results/b1d anchor_cap128",
                  "note": "net-reuse cross-lane proof: same nets, same frame, same scores"}
            print(f"[C7 anchor vs B1D booked] max|Δ|={mx:.3g} ok={c7['ok']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            c7 = {"ok": False, "error": str(exc)}

        controls = {"C1_law_equivalence": eq, "C1_pass": bool(eq.get("max_abs_diff") == 0.0),
                    "C4_frame_cross_check": c4,
                    "C4_pass": bool(all(v.get("ok") for v in c4.values())),
                    "C6_anchor_vs_b1c": c6, "C6_pass": bool(c6.get("ok")),
                    "C7_anchor_vs_b1d": c7, "C7_pass": bool(c7.get("ok"))}

        # verdict is decided by the PREREGISTERED arms ONLY; anchor is control.
        counted = [k for k, v in verdicts.items() if v["kind"] in ("linear", "hybridv2")]
        assert sorted(counted) == sorted(EXPECTED_ARMS), \
            f"verdict counted set != preregistered arms: {sorted(counted)}"
        sweep_pass = [k for k in counted if verdicts[k]["verdict"] == "PASS"]
        any_lift = bool(rw80_ramp > pl80_ramp)
        lane = "KEEP" if sweep_pass else ("PARTIAL" if any_lift else "KILL")

        (out_dir / "regions.json").write_text(json.dumps(
            {"counts": region_counts, "frac": region_frac,
             "tol_gated": TOL_GATED, "region_gate_min": REGION_GATE_MIN,
             "gated_regions": list(GATED_REGIONS),
             "per_arm": {k: {"meta": {kk: vv for kk, vv in v.items() if kk != "regions"},
                             "regions": v["regions"]} for k, v in verdicts.items()}}, indent=2))
        (out_dir / "ramp_only.json").write_text(json.dumps(ramp_only, indent=2))
        (out_dir / "agreement.json").write_text(json.dumps(
            {"tol_gated": TOL_GATED, "n_holdout": int(len(Yho)),
             "per_arm": {k: {"curve_mean": scored[k]["curve_mean"],
                             "verdict": verdicts[k]["verdict"],
                             "width": verdicts[k]["width"],
                             "weighting": verdicts[k]["weighting"],
                             "kind": verdicts[k]["kind"],
                             "n_params": verdicts[k]["n_params"]}
                         for k in scored}}, indent=2))
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        result = {
            "lane": "B1F-CROSSING-AND-RAMP-INTERFACE",
            "claim": "name the linear-head capacity-floor crossing and test whether the ramp "
                     "is an interface problem too",
            "verdict": lane, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1), "vram_ceiling_mb": VRAM_CEIL_MB,
            "primary_gate": {"regions": list(GATED_REGIONS), "min": REGION_GATE_MIN, "tol": TOL_GATED},
            "crossing": {"width": crossing, "statement": crossing_stmt,
                         "plain_pass_widths": plain_pass, "bisect": list(CROSSING_WIDTHS)},
            "reweight_w80": reweight80,
            "interface_verdict": interface,
            "ramp_only": ramp_only,
            "verdicts": verdicts, "counted_arms": counted, "passing_arms": sweep_pass,
            "control_anchor_verdict": verdicts["anchor_cap128"]["verdict"],
            "region_frac": region_frac, "region_counts": region_counts,
            "reweight": {"train_freq": reg_freq_tr, "mean_weight": reg_wmean},
            "controls": controls, "train": train_meta,
            "resume": {"enabled": bool(resume), "reused_models": resumed,
                       "n_reused": len(resumed), "n_trained": len(train_meta)},
            "elapsed_s": round(time.time() - t0, 1), "smoke": smoke,
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({"verdict": lane, "crossing": crossing_stmt,
                                      "reweight_w80": {"verdict": reweight80["verdict"],
                                                       "ramp": round(rw80_ramp, 4),
                                                       "clears": reweight80["clears_ramp_gate"]},
                                      "interface": {"reading": iface_verdict, "stmt": iface_stmt,
                                                    "dz": round(hv_dz_v["0.05"]["mean"], 4),
                                                    "ramp": round(hv_rp_v["0.05"]["mean"], 4)},
                                      "ramp_only_best": ramp_only["best_ramp_arm"],
                                      "passing": sweep_pass,
                                      "vram_mb": round(vram_mb, 1),
                                      "elapsed_s": result["elapsed_s"]}), flush=True)
        if vram_mb > VRAM_CEIL_MB:
            print(f"WARN VRAM {vram_mb:.1f} MB > ceiling {VRAM_CEIL_MB}", flush=True)
    finally:
        eng.close()
    return 0


# ── append-window guard summaries (B1D/B1E wart fix) ─────────────────────────
def _snapshot_window(receipt_dir: Path) -> None:
    src = receipt_dir / "guard_summary.json"
    if not src.exists():
        return
    n = len(sorted(receipt_dir.glob("guard_summary.window*.json")))
    shutil.copyfile(src, receipt_dir / f"guard_summary.window{n + 1}.json")


# ── outer (guarded) run ──────────────────────────────────────────────────────
def run_outer(out_dir: Path, smoke: bool = False, resume: bool = False) -> int:
    if smoke:
        return run_inner(out_dir, smoke=True)

    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1F-crossing-and-ramp-interface",
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
            {"lane": "B1F-CROSSING-AND-RAMP-INTERFACE", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        _snapshot_window(out_dir / "guard")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    if resume:
        cmd.append("--resume")
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-6000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-2000:], flush=True)

    rpath, receipt = g.emit_receipt(verdict=("PASS" if rc == 0 else "VOID"),
                                    void_reason=(None if rc == 0 else f"inner rc={rc}"))
    _snapshot_window(out_dir / "guard")   # never let a later window clobber this one
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
