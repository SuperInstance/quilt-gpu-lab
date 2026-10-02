#!/usr/bin/env python3
"""b1d_capacity_floor.py — lane B1D-CAPACITY-FLOOR.

Pre-registration (FROZEN before fire): proposals/runs/B1D-capacity-floor.md.

Follow-up to B1C (results/b1c/, commit 5eed498): B1C's `cap` arm (3-128-128-128-1
ReLU, LINEAR head) was the B1 family's first PASS at 40ep (deadzone 0.9957 /
ramp 0.9186 @5e-2), while width-64 ReLU failed -> the deadzone/ramp deficit is
capacity-bound at 40ep, not representational.

B1D asks:
  Q1  what is the MINIMUM body width clearing BOTH per-region gates at 40ep?
  Q2  does B1C's loss reweighting lower that floor?

Design (frozen): B1C cap-arm body (3 hidden ReLU layers) with the width swept
{24,32,48,64}, a BOUNDED TANH HEAD (raw = A*tanh(z), A=1.05), x {plain,
reweight}, x 3 seeds, 40ep ONLY (the 300ep regime is structurally std==0 ->
INCONCLUSIVE). Plus control C6: a width-128 LINEAR-head plain body = B1C's cap
arm, must reproduce B1C's booked cap@ep40. Optional hybrid head at the found
floor if the Wh envelope allows.

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; do NOT commit. B1C code is IMPORTED (reused),
the B1C engine is reused UNCHANGED.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import guard  # noqa: E402

HERE = Path(__file__).resolve().parent
B1C_PY = HERE / "b1c_value_fidelity.py"
PREREG = LAB / "proposals" / "runs" / "B1D-capacity-floor.md"
OUT_DIR = LAB / "results" / "b1d"
B1C_DIR = LAB / "results" / "b1c"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
WIDTHS = (24, 32, 48, 64)
DEPTH = 3                       # hidden layers (B1C cap-arm depth)
TANH_SCALE = 1.05               # A in raw = A*tanh(z); law value-range assumption
GATED_REGIONS = ("deadzone", "ramp")
REGION_GATE_MIN = 0.90
TOL_GATED = 5e-2
REPORT_TOLS = (1e-3, 1e-2, 5e-2)
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)
EPOCH = 40
BATCH = 4096
LR = 1e-3
MECH_DZ_LIFT, MECH_RAMP_LIFT = 0.15, 0.20
BCE_LAMBDA = 1.0
ANCHOR_WIDTH = 128
ANCHOR_TOL = 0.05
GUARD_TIMEOUT_S = 3600.0
WH_ENVELOPE = 18.0
VRAM_CEIL_MB = 1500.0


# ── reuse the B1C driver (frame gen, regions, engine, weights) — imported ────
def _load_b1c():
    spec = importlib.util.spec_from_file_location("b1c_value_fidelity", str(B1C_PY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b1c_value_fidelity"] = mod
    spec.loader.exec_module(mod)
    return mod


bc = _load_b1c()
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

    class TanhMLP(nn.Module):
        """3 hidden ReLU layers of `width` + bounded tanh head A*tanh(z)."""

        def __init__(self, width: int):
            super().__init__()
            self.body, prev = _relu_body(width)
            self.out = nn.Linear(prev, 1)
            self.scale = TANH_SCALE

        def raw(self, X):
            return self.scale * torch.tanh(self.out(self.body(X)).squeeze(-1))

    class HybridMLP(nn.Module):
        """Same body + regression head A*tanh(z) + deadzone atom gate sigmoid."""

        def __init__(self, width: int):
            super().__init__()
            self.body, prev = _relu_body(width)
            self.reg = nn.Linear(prev, 1)
            self.gate = nn.Linear(prev, 1)
            self.scale = TANH_SCALE

        def gate_logit(self, X):
            return self.gate(self.body(X)).squeeze(-1)

        def raw(self, X):
            z = self.body(X)
            g = torch.sigmoid(self.gate(z)).squeeze(-1)
            reg = self.scale * torch.tanh(self.reg(z).squeeze(-1))
            return (1.0 - g) * reg   # in the deadzone (g->1) the output -> exact 0

    return TanhMLP, HybridMLP


def build_model(kind: str, width: int, seed: int, device: str):
    import torch
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if kind == "anchor":
        # EXACTLY B1C's cap arm: 3-128-128-128-1 ReLU, linear head
        return bc.build_model("cap", seed, device)
    TanhMLP, HybridMLP = _classes()
    if kind == "tanh":
        return TanhMLP(width).to(device)
    if kind == "hybrid":
        return HybridMLP(width).to(device)
    raise ValueError(kind)


def net_raw(net, kind, X):
    if kind == "anchor":
        return net(X).squeeze(-1)
    return net.raw(X)


def predict(net, kind, META, device, deployed: bool = True):
    import numpy as np
    import torch
    p = torch.from_numpy(META[:, 0].astype(np.float64)).to(device=device, dtype=torch.float32)
    b = torch.from_numpy(META[:, 1].astype(np.float64)).to(device=device, dtype=torch.float32)
    s = torch.from_numpy(META[:, 2].astype(np.float64)).to(device=device, dtype=torch.float32)
    X = torch.stack([(p - 30.0) / 30.0, (b - 30.0) / 30.0, s], dim=1)
    with torch.no_grad():
        raw = net_raw(net, kind, X)
    raw = raw.detach().cpu().numpy().astype(np.float64)
    if not deployed:
        return raw
    return np.clip(META[:, 0] + raw, 6.0, 54.0) - META[:, 0]


# ── training (frozen: deployed MSE; reweight = B1C inverse-region-freq) ──────
def train_one(kind, width, seed, Xtr, Ytr, Mtr, device, epochs, wtr=None, dzlab=None):
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
    Z = torch.from_numpy(np.asarray(dzlab, dtype=np.float32)).to(device) if dzlab is not None else None

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
            if kind == "hybrid":
                loss = loss + BCE_LAMBDA * bce(net.gate_logit(X[idx]), Z[idx])
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    return net, {"arm_kind": kind, "width": width, "seed": seed, "epochs": epochs,
                 "n_params": n_params, "batch": BATCH, "lr": LR,
                 "tanh_scale": (None if kind == "anchor" else TANH_SCALE),
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

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(bc.HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "B1/B1b/B1C's frame verbatim (reused engine, unchanged)",
        "traces_n": n_traces, "trace_ticks": ticks, "trace_seed_base": bc.TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {bc.HOLDOUT_MOD} == 0",
        "widths": list(WIDTHS), "depth": DEPTH, "tanh_scale": TANH_SCALE,
        "epochs": EPOCH, "weightings": ["plain", "reweight"],
        "primary_gate": f"deadzone >= {REGION_GATE_MIN} AND ramp >= {REGION_GATE_MIN} "
                        f"@ {TOL_GATED:g}, 3-seed mean, both std>0",
        "mechanism_bar": {"deadzone_lift_vs_plain": MECH_DZ_LIFT, "ramp_lift_vs_plain": MECH_RAMP_LIFT},
        "control_anchor": f"width-{ANCHOR_WIDTH} linear-head plain == B1C cap arm "
                          f"(booked cap@ep40 reproduced within |d|<{ANCHOR_TOL})",
        "head": f"body = {DEPTH} hidden ReLU layers x width w; head = A*tanh(z), A={TANH_SCALE}",
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

        # ── control C4: frame cross-check vs B1C, B1b-runB AND B1 ───────────
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

        c4 = {"vs_b1c": xcheck(B1C_DIR), "vs_runB": xcheck(bc.B1B_DIR), "vs_b1": xcheck(bc.B1_DIR)}
        print(f"[C4] {json.dumps(c4)[:400]}", flush=True)

        # ── control C1: switch-law vs pristine-law on holdout states ─────────
        sub = Mho[::max(1, len(Mho) // 4000)][:4000]
        eq = eng.send({"cmd": "laweq", "states": [
            {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
            for m in sub]})
        print(f"[C1 laweq] {eq}", flush=True)

        # ── weights for the reweight arm (train split, B1C mechanism) ───────
        wtr, reg_freq_tr, reg_wmean = region_weights(Ytr, Mtr)
        dz_tr = region_masks(Ytr, Mtr)["deadzone"].astype(np.float32)
        print(f"[reweight] train freq={ {k: round(v, 4) for k, v in reg_freq_tr.items()} } "
              f"mean_w={ {k: round(v, 3) for k, v in reg_wmean.items()} }", flush=True)

        def arm_specs():
            s = [("anchor_cap128", "anchor", ANCHOR_WIDTH, "plain")]
            for w in WIDTHS:
                s.append((f"plain_w{w}", "tanh", w, "plain"))
            for w in WIDTHS:
                s.append((f"reweight_w{w}", "tanh", w, "reweight"))
            return s

        def tm_weights(weighting):
            return wtr if weighting == "reweight" else None

        # ── train anchor + sweep ────────────────────────────────────────────
        nets, train_meta = {}, []
        for name, kind, width, weighting in arm_specs():
            for seed in TRAIN_SEEDS:
                mpath = out_dir / f"model_{name}_seed{seed}_ep{EPOCH}.pt"
                if resume and mpath.exists():
                    net = build_model(kind, width, seed, device)
                    net.load_state_dict(torch.load(mpath, map_location=device))
                    nets[(name, seed)] = net
                    resumed.append(mpath.name)
                    print(f"[reuse {name:14s} {seed}] loaded", flush=True)
                    continue
                net, tm = train_one(kind, width, seed, Xtr, Ytr, Mtr, device, epochs,
                                    wtr=tm_weights(weighting), dzlab=(dz_tr if kind == "hybrid" else None))
                nets[(name, seed)] = net
                tm["name"] = name
                tm["weighting"] = weighting
                train_meta.append(tm)
                torch.save(net.state_dict(), mpath)
                print(f"[train {name:14s} {seed}] {tm['first_train_loss']:.5g} -> "
                      f"{tm['final_train_loss']:.5g} ({tm['n_params']}p, {tm['loss']})", flush=True)

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
        for name, kind, width, weighting in arm_specs():
            r = score_arm(name, kind)
            scored[name] = r
            verdicts[name] = {"kind": kind, "width": width, "weighting": weighting,
                              "regions": r["regions"], "gated": r["gated"], "verdict": r["verdict"],
                              "n_params": r["n_params"]}
            print(f"[gate {name:14s}] dz={r['regions']['deadzone']['0.05']['mean']:.4f}"
                  f"±{r['regions']['deadzone']['0.05']['std']:.4f} "
                  f"ramp={r['regions']['ramp']['0.05']['mean']:.4f}"
                  f"±{r['regions']['ramp']['0.05']['std']:.4f} "
                  f"sat={r['regions']['saturation']['0.05']['mean']:.4f} "
                  f"agg={r['curve_mean']['0.05']:.4f} -> {r['verdict']}", flush=True)

        # ── the capacity floor (Q1 plain, Q2 reweight) ──────────────────────
        def floor_of(weighting):
            for w in sorted(WIDTHS):
                if verdicts[f"{weighting}_w{w}"]["verdict"] == "PASS":
                    return w
            return None

        floors = {"plain": floor_of("plain"), "reweight": floor_of("reweight")}

        # ── mechanism bar: reweight vs plain at same width ──────────────────
        mech = {}
        for w in WIDTHS:
            pl, rw = scored[f"plain_w{w}"], scored[f"reweight_w{w}"]
            dz = rw["regions"]["deadzone"]["0.05"]["mean"] - pl["regions"]["deadzone"]["0.05"]["mean"]
            rp = rw["regions"]["ramp"]["0.05"]["mean"] - pl["regions"]["ramp"]["0.05"]["mean"]
            mech[f"w{w}"] = {"deadzone_lift": dz, "ramp_lift": rp,
                             "mechanism_win": bool(dz >= MECH_DZ_LIFT and rp >= MECH_RAMP_LIFT)}

        # ── control C6: anchor == B1C cap@ep40 ──────────────────────────────
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
                  "tol": ANCHOR_TOL, "booked_ref": "results/b1c cap@ep40"}
            print(f"[C6 anchor repro] max|Δ|={mx:.4f} ok={c6['ok']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            c6 = {"ok": False, "error": str(exc)}

        # ── OPTIONAL hybrid at the found floor (if the envelope allows) ─────
        floor_w = floors["plain"] or floors["reweight"] or max(WIDTHS)
        hybrid = {"ran": False, "width": floor_w}
        hybrid_verdict = None
        if not smoke:
            hname = f"hybrid_w{floor_w}"
            for seed in TRAIN_SEEDS:
                mpath = out_dir / f"model_{hname}_seed{seed}_ep{EPOCH}.pt"
                if resume and mpath.exists():
                    net = build_model("hybrid", floor_w, seed, device)
                    net.load_state_dict(torch.load(mpath, map_location=device))
                    nets[(hname, seed)] = net
                    resumed.append(mpath.name)
                    continue
                net, tm = train_one("hybrid", floor_w, seed, Xtr, Ytr, Mtr, device, epochs, dzlab=dz_tr)
                nets[(hname, seed)] = net
                tm["name"] = hname
                tm["weighting"] = "plain"
                train_meta.append(tm)
                torch.save(net.state_dict(), mpath)
                print(f"[train {hname:14s} {seed}] {tm['first_train_loss']:.5g} -> "
                      f"{tm['final_train_loss']:.5g} ({tm['n_params']}p)", flush=True)
            r = score_arm(hname, "hybrid")
            scored[hname] = r
            verdicts[hname] = {"kind": "hybrid", "width": floor_w, "weighting": "plain",
                               "regions": r["regions"], "gated": r["gated"],
                               "verdict": r["verdict"], "n_params": r["n_params"],
                               "note": "OPTIONAL secondary interface probe, not part of Q1/Q2"}
            hybrid = {"ran": True, "width": floor_w, "verdict": r["verdict"],
                      "gated": r["gated"], "n_params": r["n_params"]}
            hybrid_verdict = r["verdict"]
            print(f"[gate {hname:14s}] dz={r['regions']['deadzone']['0.05']['mean']:.4f}"
                  f"±{r['regions']['deadzone']['0.05']['std']:.4f} "
                  f"ramp={r['regions']['ramp']['0.05']['mean']:.4f}"
                  f"±{r['regions']['ramp']['0.05']['std']:.4f} -> {r['verdict']}", flush=True)

        # ── controls bundle ─────────────────────────────────────────────────
        controls = {"C1_law_equivalence": eq, "C1_pass": bool(eq.get("max_abs_diff") == 0.0),
                    "C4_frame_cross_check": c4,
                    "C4_pass": bool(all(v.get("ok") for v in c4.values())),
                    "C6_anchor_reproduction": c6, "C6_pass": bool(c6.get("ok"))}

        # the lane verdict is decided by the SWEEP arms (tanh head) + the optional
        # hybrid — the width-128 LINEAR-head anchor is control C6, NOT an arm.
        sweep_pass = [k for k, v in verdicts.items()
                      if v["kind"] in ("tanh", "hybrid") and v["verdict"] == "PASS"]
        anchor_verdict = verdicts.get("anchor_cap128", {}).get("verdict")
        any_mech = [k for k, v in mech.items() if v["mechanism_win"]]
        lane = "KEEP" if sweep_pass else ("PARTIAL" if any_mech else "KILL")
        floor_reached = {"plain": floors["plain"] is not None,
                         "reweight": floors["reweight"] is not None}
        floor_stmt = ("reached" if any(floor_reached.values())
                      else f"NOT reached at 40ep for widths <= {max(WIDTHS)} (floor > {max(WIDTHS)})")

        (out_dir / "regions.json").write_text(json.dumps(
            {"counts": region_counts, "frac": region_frac,
             "tol_gated": TOL_GATED, "region_gate_min": REGION_GATE_MIN,
             "gated_regions": list(GATED_REGIONS),
             "per_arm": {k: {"meta": {kk: vv for kk, vv in v.items() if kk != "regions"},
                             "regions": v["regions"]} for k, v in verdicts.items()}}, indent=2))
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
            "lane": "B1D-CAPACITY-FLOOR",
            "claim": "the minimum body width clearing BOTH per-region gates at 40ep; and "
                     "whether loss reweighting lowers that floor",
            "verdict": lane, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1), "vram_ceiling_mb": VRAM_CEIL_MB,
            "primary_gate": {"regions": list(GATED_REGIONS), "min": REGION_GATE_MIN, "tol": TOL_GATED},
            "capacity_floor": floors, "floor_reached": floor_reached, "floor_statement": floor_stmt,
            "widths": list(WIDTHS), "epochs": EPOCH,
            "verdicts": verdicts, "passing_sweep_arms": sweep_pass,
            "control_anchor_verdict": anchor_verdict, "mechanism_wins": any_mech,
            "mechanism_bar": mech, "optional_hybrid": hybrid,
            "region_frac": region_frac, "region_counts": region_counts,
            "reweight": {"train_freq": reg_freq_tr, "mean_weight": reg_wmean},
            "controls": controls, "train": train_meta,
            "resume": {"enabled": bool(resume), "reused_models": resumed,
                       "n_reused": len(resumed), "n_trained": len(train_meta)},
            "elapsed_s": round(time.time() - t0, 1), "smoke": smoke,
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({"verdict": lane, "floor": floors,
                                      "floor_statement": floor_stmt,
                                      "passing_sweep": sweep_pass, "anchor": anchor_verdict,
                                      "mech": any_mech, "hybrid": hybrid_verdict,
                                      "vram_mb": round(vram_mb, 1),
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

    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1D-capacity-floor",
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
            {"lane": "B1D-CAPACITY-FLOOR", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
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
