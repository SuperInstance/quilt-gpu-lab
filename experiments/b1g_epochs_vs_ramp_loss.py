#!/usr/bin/env python3
"""b1g_epochs_vs_ramp_loss.py — lane B1G-EPOCHS-VS-RAMP-LOSS (B1-family closer).

Pre-registration (FROZEN before fire):
    proposals/runs/B1G-epochs-vs-ramp-loss.md.

Booked question handed down by B1F (results/b1f/):

  Is the 40ep ramp number (hybrid-v2 ramp atom gate 0.2930 @ w64) an EPOCHS
  artifact or a LOSS-SHAPE artifact — does longer training OR a ramp-weighted
  objective close the ramp gap WITHOUT breaking the crossing?

Design (frozen): architecture `hybridv2` (B1F's class, reused unchanged) at
width 96 (the plain crossing point named by B1F), single seed 2718, arms =
{MSE, ramp-weighted} x {40, 80, 160} epochs. Each loss trains ONCE to 160ep and
is snapshotted at the three milestones; every snapshot is a first-class arm.

Reuse: the B1F driver is IMPORTED wholesale (b1f_crossing_ramp_interface.py),
which itself imports the B1C driver and reuses the B1C engine UNCHANGED and
B1D's saved width-128 anchor nets (controls C6/C7). B1F's safeguards are kept
(prereg-arm assert + append-window guard snapshot).

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; verdict counts ONLY preregistered arms;
append-window guard summaries; do NOT commit.
"""
from __future__ import annotations

import copy
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
B1F_PY = HERE / "b1f_crossing_ramp_interface.py"
PREREG = LAB / "proposals" / "runs" / "B1G-epochs-vs-ramp-loss.md"
OUT_DIR = LAB / "results" / "b1g"
B1C_DIR = LAB / "results" / "b1c"
B1D_DIR = LAB / "results" / "b1d"
B1E_DIR = LAB / "results" / "b1e"
B1B_DIR = LAB / "results" / "b1b_kink_runB"
B1_DIR = LAB / "results" / "b1_distill"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718,)          # single seed per mission
WIDTH = 96                     # the plain crossing point named by B1F
MILESTONES = (40, 80, 160)
LOSSES = ("mse", "rw")
RAMP_BOOST = 10.0              # ramp-weighted: w = 1 + RAMP_BOOST*1[ramp]
KIND = "hybridv2"
MAX_EPOCHS = max(MILESTONES)
GATED_REGIONS = ("deadzone", "ramp")

RAMP_GATE_MIN = 0.80           # G-B1G1 bar
REF_PLAIN_40 = 0.5675          # B1E plain w64 ramp (the 40ep reference)
REF_MARGIN = 0.05              # CI must exclude REF_PLAIN_40 - REF_MARGIN
CI_FLOOR = REF_PLAIN_40 - REF_MARGIN          # = 0.5175
DZ_GATE_MIN = 0.90             # G-B1G2 bar (crossing intact)
DZ_CI_FLOOR = 0.90             # deadzone CI lower bound must exceed the gate
TOL_GATED = 5e-2
REPORT_TOLS = (1e-3, 1e-2, 5e-2)
N_BOOT = 1000
BOOT_SEED = 2718
ANCHOR_WIDTH = 128
ANCHOR_TOL = 0.05
GUARD_TIMEOUT_S = 3600.0
WH_ENVELOPE = 6.0
VRAM_CEIL_MB = 1500.0

# ── the 6 preregistered arms (frozen) ───────────────────────────────────────
ARM_SPECS = tuple((f"h96_{loss}_ep{ep}", loss, ep) for loss in LOSSES for ep in MILESTONES)
EXPECTED_ARMS = tuple(a[0] for a in ARM_SPECS)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# B1F driver, imported wholesale: gives us Engine/gen/labels/arrays/regions/
# build_model/net_raw/predict + the frozen constants + B1C/B1D reuse paths.
b1f = _load("b1f_crossing_ramp_interface", B1F_PY)
Engine = b1f.Engine
generate_traces = b1f.generate_traces
label_traces = b1f.label_traces
build_arrays = b1f.build_arrays
region_masks = b1f.region_masks
build_model = b1f.build_model
net_raw = b1f.net_raw
predict = b1f.predict
mean_std = b1f.mean_std
BATCH = b1f.BATCH
LR = b1f.LR
BCE_LAMBDA = b1f.BCE_LAMBDA
TANH_SCALE = b1f.TANH_SCALE
EPS = b1f.EPS


# ── training (mirrors b1f.train_one EXACTLY; adds milestone snapshots) ───────
def train_to_milestones(loss: str, seed: int, Xtr, Ytr, Mtr, device: str,
                        milestones, width: int, w_rw=None, dzlab=None, ramplab=None):
    """b1f.train_one's loop, extended with state-dict snapshots at milestones.

    loss='mse' -> b1f's deployed objective verbatim (unweighted MSE + BCE gates)
    loss='rw'  -> same, but the deployed-MSE term is weighted by
                  w = 1 + RAMP_BOOST * 1[ramp]  (BCE gate terms unweighted).
    """
    import numpy as np
    import torch
    import torch.nn as nn

    net = build_model(KIND, width, seed, device)
    n_params = int(sum(q.numel() for q in net.parameters()))
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    mse = nn.MSELoss(reduction="none")
    bce = nn.BCEWithLogitsLoss()
    p_all = torch.from_numpy(Mtr[:, 0].astype(np.float32)).to(device)
    X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = Y.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)
    W = None
    if loss == "rw":
        W = torch.from_numpy(np.asarray(w_rw, dtype=np.float32)).to(device)
    ZD = torch.from_numpy(np.asarray(dzlab, dtype=np.float32)).to(device)
    ZR = torch.from_numpy(np.asarray(ramplab, dtype=np.float32)).to(device)

    hist = []
    snaps = {}
    max_epochs_ = max(milestones)
    for ep in range(1, max_epochs_ + 1):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            out = net_raw(net, KIND, X[idx])
            pred = torch.clamp(p_all[idx] + out, 6.0, 54.0) - p_all[idx]
            se = mse(pred, Y[idx])
            l = (se * W[idx]).mean() if W is not None else se.mean()
            l = (l + BCE_LAMBDA * bce(net.gate_dz_logit(X[idx]), ZD[idx])
                 + BCE_LAMBDA * bce(net.gate_r_logit(X[idx]), ZR[idx]))
            l.backward()
            opt.step()
            tot += float(l.item()) * idx.shape[0]
        hist.append(tot / n)
        if ep in milestones:
            snaps[ep] = copy.deepcopy(net.state_dict())
    torch.cuda.synchronize()
    meta = {"arm_kind": KIND, "width": width, "seed": seed, "loss": loss,
            "n_params": n_params, "batch": BATCH, "lr": LR,
            "max_epochs": max(milestones), "milestones": list(milestones),
            "final_train_loss": hist[-1], "first_train_loss": hist[0],
            "loss_fn": ("deployed_mse + BCE gates" if loss == "mse"
                        else f"ramp_weighted_mse(1+{RAMP_BOOST:g}*1[ramp]) + BCE gates"),
            "train_loss_at_milestones": {str(m): hist[m - 1] for m in milestones}}
    return snaps, meta


def _bootstrap_ci(ind_hits, n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    """Percentile bootstrap over per-sample hit indicators (single-arm)."""
    import numpy as np
    a = np.asarray(ind_hits, dtype=np.float64)
    n = a.shape[0]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        means[b] = a[idx].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(a.mean()), float(lo), float(hi)


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

    n_traces = 2 if smoke else b1f.bc.TRACES_N
    ticks = 200 if smoke else b1f.bc.TRACE_TICKS
    milestones = (2, 4, 6) if smoke else MILESTONES
    max_epochs = max(milestones)
    width = 16 if smoke else WIDTH
    arms = (tuple((f"h96_{loss}_ep{ep}", loss, ep) for loss in LOSSES for ep in milestones)
            if smoke else ARM_SPECS)

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(b1f.bc.HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "train_seeds": list(TRAIN_SEEDS),
        "frame": "B1/B1b/B1C/B1F's frame verbatim (reused B1F driver + engine unchanged)",
        "traces_n": n_traces, "trace_ticks": ticks, "trace_seed_base": b1f.bc.TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {b1f.bc.HOLDOUT_MOD} == 0",
        "arms": [{"name": n, "kind": KIND, "width": width, "loss": l, "epochs": e}
                 for n, l, e in arms],
        "epochs_milestones": list(milestones), "epochs_trained": max_epochs,
        "width": width, "ramp_boost": RAMP_BOOST,
        "losses": {"mse": "deployed_mse + BCE gates (b1f verbatim)",
                   "rw": "deployed_mse weighted by 1+RAMP_BOOST*1[ramp] + BCE gates"},
        "gates": {"G_B1G1": f"any arm ramp@5e-2 >= {RAMP_GATE_MIN} AND boot CI_low > {CI_FLOOR}",
                  "G_B1G2": f"a G1 arm keeps deadzone@5e-2 >= {DZ_GATE_MIN} AND boot CI_low > {DZ_CI_FLOOR}"},
        "reference": {"b1f_hybridv2_w64_ramp@5e-2": 0.2930, "b1e_plain_w64_ramp@5e-2": REF_PLAIN_40,
                      "b1e_reweight_w64_ramp@5e-2": 0.7977, "b1f_linear_plain_w96_ramp@5e-2": 0.9617},
        "bootstrap": {"B": N_BOOT, "seed": BOOT_SEED, "method": "percentile 95% CI over region samples"},
        "control_anchor": f"width-{ANCHOR_WIDTH} linear-head plain == B1C cap arm, C6/C7 reused from B1D nets",
        "verdict_counts": f"PREREGISTERED ARMS ONLY ({len(EXPECTED_ARMS)}); anchor = control",
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
            "frame": "B1/B1b/B1C/B1F verbatim", "traces_n": n_traces, "trace_ticks": ticks,
            "trace_seed_base": b1f.bc.TRACE_SEED_BASE, "holdout_mod": b1f.bc.HOLDOUT_MOD,
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

        # ── weights + atom labels (train split, B1C/B1F mechanisms) ─────────
        reg_tr = region_masks(Ytr, Mtr)
        dz_tr = reg_tr["deadzone"].astype(np.float32)
        ramp_tr = reg_tr["ramp"].astype(np.float32)
        w_rw = (1.0 + RAMP_BOOST * ramp_tr.astype(np.float64))
        print(f"[atoms] train deadzone={int(dz_tr.sum())} ramp={int(ramp_tr.sum())} "
              f"ramp_frac={float(ramp_tr.mean()):.4f} "
              f"ramp_mse_mass={(float(w_rw[ramp_tr > 0].sum()) / float(w_rw.sum())):.4f}", flush=True)

        # ── train the 2 loss runs; snapshot the 6 arms ──────────────────────
        nets, train_meta = {}, []
        for loss in LOSSES:
            need = [f"model_hybridv2_w96_{loss}_seed{s}_ep{e}.pt"
                    for s in TRAIN_SEEDS for e in milestones]
            have = all((out_dir / f).exists() for f in need)
            if resume and have:
                for seed in TRAIN_SEEDS:
                    for ep in milestones:
                        nm = f"h96_{loss}_ep{ep}"
                        net = build_model(KIND, width, seed, device)
                        net.load_state_dict(torch.load(
                            out_dir / f"model_hybridv2_w96_{loss}_seed{seed}_ep{ep}.pt",
                            map_location=device))
                        nets[(nm, seed)] = net
                resumed.append(f"{loss} (6 checkpoints)")
                print(f"[reuse {loss}] loaded 6 snapshots", flush=True)
                continue
            for seed in TRAIN_SEEDS:
                snaps, tm = train_to_milestones(
                    loss, seed, Xtr, Ytr, Mtr, device, milestones,
                    width=width, w_rw=w_rw, dzlab=dz_tr, ramplab=ramp_tr)
                tm["seed"] = seed
                train_meta.append(tm)
                for ep in milestones:
                    nm = f"h96_{loss}_ep{ep}"
                    net = build_model(KIND, width, seed, device)
                    net.load_state_dict(snaps[ep])
                    nets[(nm, seed)] = net
                    torch.save(snaps[ep],
                               out_dir / f"model_hybridv2_w96_{loss}_seed{seed}_ep{ep}.pt")
                    print(f"[ckpt {nm:16s} {seed}] trloss={tm['train_loss_at_milestones'][str(ep)]:.5g} "
                          f"a={float(net.ramp_slope.detach()):.3f} k={float(net.ramp_knot.detach()):.3f}",
                          flush=True)

        # ── regions + scoring helpers ───────────────────────────────────────
        reg = region_masks(Yho, Mho)
        region_counts = {k: int(v.sum()) for k, v in reg.items()}
        region_frac = {k: float(v.mean()) for k, v in reg.items()}
        print("[regions] " + json.dumps({k: round(v, 4) for k, v in region_frac.items()}), flush=True)

        def score_arm(name, seed):
            net = nets[(name, seed)]
            pr = predict(net, KIND, Mho, device)
            diff = np.abs(pr - Yho)
            curve = {f"{t:g}": float(np.mean(diff <= t)) for t in EPS}
            reg_arm = {}
            for rname in reg:
                mask = reg[rname]
                if int(mask.sum()) == 0:
                    reg_arm[rname] = {"n": 0}
                    continue
                d = diff[mask]
                reg_arm[rname] = {"n": int(mask.sum())}
                for t in REPORT_TOLS:
                    hits = (d <= t)
                    if t == TOL_GATED:
                        m, lo, hi = _bootstrap_ci(hits)
                        reg_arm[rname][f"{t:g}"] = {"mean": m, "ci_low": lo, "ci_high": hi}
                    else:
                        reg_arm[rname][f"{t:g}"] = {"mean": float(np.mean(hits)),
                                                    "std": float(np.std(hits))}
            return {"regions": reg_arm, "curve_mean": curve,
                    "learned_k": float(net.ramp_knot.detach()),
                    "learned_a": float(net.ramp_slope.detach()),
                    "n_params": int(sum(q.numel() for q in net.parameters()))}

        scored, verdicts = {}, {}
        for name, loss, ep in arms:
            r = score_arm(name, TRAIN_SEEDS[0])
            dz = r["regions"]["deadzone"][f"{TOL_GATED:g}"]
            rp = r["regions"]["ramp"][f"{TOL_GATED:g}"]
            cross_pass = bool(dz["mean"] >= DZ_GATE_MIN and rp["mean"] >= DZ_GATE_MIN)
            verdicts[name] = {"kind": KIND, "width": width, "loss": loss, "epochs": ep,
                              "regions": r["regions"], "curve_mean": r["curve_mean"],
                              "learned_k": r["learned_k"], "learned_a": r["learned_a"],
                              "crossing_pass": cross_pass, "n_params": r["n_params"]}
            scored[name] = r
            print(f"[gate {name:16s}] dz={dz['mean']:.4f} CI[{dz['ci_low']:.4f},{dz['ci_high']:.4f}] "
                  f"ramp={rp['mean']:.4f} CI[{rp['ci_low']:.4f},{rp['ci_high']:.4f}] "
                  f"k={r['learned_k']:.3f} a={r['learned_a']:.3f} "
                  f"crossing={'PASS' if cross_pass else 'FAIL'}", flush=True)

        # ── controls C6/C7: reuse B1D width-128 anchor nets ─────────────────
        anchor_seeds = (2718, 2719, 2720)
        anchor_scores = []
        for seed in anchor_seeds:
            apath = B1D_DIR / f"model_anchor_cap128_seed{seed}_ep40.pt"
            net = build_model("anchor", ANCHOR_WIDTH, seed, device)
            net.load_state_dict(torch.load(apath, map_location=device))
            resumed.append(str(apath))
            pr = predict(net, "anchor", Mho, device)
            diff = np.abs(pr - Yho)
            cell = {}
            for rname, mask in reg.items():
                if int(mask.sum()) == 0:
                    continue
                cell[rname] = {}
                for t in ("0.01", "0.05"):
                    cell[rname][t] = float(np.mean(diff[mask] <= float(t)))
            anchor_scores.append(cell)
            print(f"[reuse anchor_cap128 {seed}] loaded {apath.name}", flush=True)
        anchor = {}
        for rname in reg:
            if not any(rname in c for c in anchor_scores):
                continue
            anchor[rname] = {}
            for t in ("0.01", "0.05"):
                anchor[rname][t] = {"mean": mean_std([c[rname][t] for c in anchor_scores])[0],
                                    "std": mean_std([c[rname][t] for c in anchor_scores])[1]}

        c6 = {"ok": None, "note": "B1C regions.json missing"}
        try:
            rb = json.load(open(B1C_DIR / "regions.json"))["per_arm_budget"]["cap@ep40"]
            deltas = {}
            for rname in ("deadzone", "ramp", "saturation"):
                for t in ("0.01", "0.05"):
                    deltas[f"{rname}@{t}"] = abs(anchor[rname][t]["mean"] - rb[rname][t]["mean"])
            mx = max(deltas.values())
            c6 = {"ok": bool(mx < ANCHOR_TOL), "max_abs_delta": mx, "per_cell": deltas,
                  "tol": ANCHOR_TOL, "booked_ref": "results/b1c cap@ep40",
                  "note": "anchor nets REUSED from results/b1d (bit-identical frame)"}
            print(f"[C6 anchor repro vs B1C] max|Δ|={mx:.5f} ok={c6['ok']}", flush=True)
        except Exception as exc:  # noqa: BLE001
            c6 = {"ok": False, "error": str(exc)}

        c7 = {"ok": None, "note": "B1D regions.json missing"}
        try:
            bd_reg = json.load(open(B1D_DIR / "regions.json"))["per_arm"]["anchor_cap128"]["regions"]
            deltas = {}
            for rname in ("deadzone", "ramp", "saturation"):
                for t in ("0.01", "0.05"):
                    deltas[f"{rname}@{t}"] = abs(anchor[rname][t]["mean"] - bd_reg[rname][t]["mean"])
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

        # ── gates (frozen, mechanical) — preregistered arms ONLY ────────────
        counted = [nm for nm, _l, _e in arms]
        if not smoke:
            assert sorted(counted) == sorted(EXPECTED_ARMS), "arm set drift"

        def g1_ok(nm):
            rp = scored[nm]["regions"]["ramp"][f"{TOL_GATED:g}"]
            return bool(rp["mean"] >= RAMP_GATE_MIN and rp["ci_low"] > CI_FLOOR)

        def g2_ok(nm):
            dz = scored[nm]["regions"]["deadzone"][f"{TOL_GATED:g}"]
            return bool(dz["mean"] >= DZ_GATE_MIN and dz["ci_low"] > DZ_CI_FLOOR)

        g1_arms = [nm for nm in counted if g1_ok(nm)]
        g2_arms = [nm for nm in g1_arms if g2_ok(nm)]
        G_B1G1 = bool(g1_arms)
        G_B1G2 = bool(g2_arms)
        if G_B1G1 and G_B1G2:
            sentence = ("the ramp is epochs/loss-shaped after all — "
                        "B1F's representational call was undertrained")
            grain = "RAMP-CLOSES"
        elif not G_B1G1:
            sentence = ("the ramp floor is stable — representation limit confirmed at the margin")
            grain = "RAMP-FLOOR-STABLE"
        else:
            sentence = ("the ramp can be bought, but only by breaking the interface (the crossing)")
            grain = "TRADEOFF"
        lane = "KEEP" if G_B1G1 else "KILL"

        # best arm by ramp@5e-2
        best = max(counted, key=lambda nm: scored[nm]["regions"]["ramp"][f"{TOL_GATED:g}"]["mean"])

        # ── ramp trajectory (the frozen headline) ────────────────────────────
        ramp_only = {"rows": {}, "note": "ramp-region fidelity per arm (single seed 2718, boot CI)"}
        for name, loss, ep in arms:
            rr = scored[name]["regions"]["ramp"]
            ramp_only["rows"][name] = {
                "loss": loss, "width": width, "epochs": ep,
                "ramp@5e-2": rr["0.05"]["mean"], "ramp@5e-2_ci": [rr["0.05"]["ci_low"], rr["0.05"]["ci_high"]],
                "ramp@1e-2": rr["0.01"]["mean"], "ramp@1e-3": rr["0.001"]["mean"],
                "deadzone@5e-2": scored[name]["regions"]["deadzone"]["0.05"]["mean"],
                "deadzone@5e-2_ci": [scored[name]["regions"]["deadzone"]["0.05"]["ci_low"],
                                     scored[name]["regions"]["deadzone"]["0.05"]["ci_high"]],
                "learned_k": scored[name]["learned_k"], "learned_a": scored[name]["learned_a"],
                "clears_g1_bar@5e-2": bool(rr["0.05"]["mean"] >= RAMP_GATE_MIN)}
        ramp_only["best_ramp_arm"] = best
        ramp_only["trajectories"] = {loss: [{"epochs": ep,
                                             "ramp@5e-2": scored[f"h96_{loss}_ep{ep}"]["regions"]["ramp"]["0.05"]["mean"],
                                             "learned_k": scored[f"h96_{loss}_ep{ep}"]["learned_k"]}
                                            for ep in milestones] for loss in LOSSES}

        (out_dir / "regions.json").write_text(json.dumps(
            {"counts": region_counts, "frac": region_frac,
             "tol_gated": TOL_GATED, "gated_regions": list(GATED_REGIONS),
             "ramp_gate_min": RAMP_GATE_MIN, "deadzone_gate_min": DZ_GATE_MIN,
             "per_arm": {k: {"meta": {kk: vv for kk, vv in v.items()
                                      if kk not in ("regions", "curve_mean")},
                             "regions": v["regions"]} for k, v in verdicts.items()}}, indent=2))
        (out_dir / "ramp_only.json").write_text(json.dumps(ramp_only, indent=2))
        (out_dir / "agreement.json").write_text(json.dumps(
            {"tol_gated": TOL_GATED, "n_holdout": int(len(Yho)),
             "per_arm": {k: {"curve_mean": scored[k]["curve_mean"],
                             "verdict_regions": verdicts[k]["regions"],
                             "crossing_pass": verdicts[k]["crossing_pass"],
                             "width": width, "loss": verdicts[k]["loss"],
                             "epochs": verdicts[k]["epochs"], "kind": KIND,
                             "n_params": verdicts[k]["n_params"]}
                         for k in counted}}, indent=2))
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        result = {
            "lane": "B1G-EPOCHS-VS-RAMP-LOSS",
            "claim": "is the 40ep ramp number an epochs artifact or a loss-shape artifact "
                     "(longer training or a ramp-weighted objective) at the plain crossing width 96",
            "verdict": lane, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1), "vram_ceiling_mb": VRAM_CEIL_MB,
            "width": width, "seed": TRAIN_SEEDS[0], "losses": list(LOSSES),
            "milestones": list(milestones), "ramp_boost": RAMP_BOOST,
            "gates": {
                "G_B1G1": {"pass": G_B1G1, "bar": RAMP_GATE_MIN, "ci_floor": CI_FLOOR,
                           "arms": g1_arms,
                           "rule": "ramp@5e-2 >= 0.80 AND boot CI_low > 0.5175"},
                "G_B1G2": {"pass": G_B1G2, "bar": DZ_GATE_MIN, "ci_floor": DZ_CI_FLOOR,
                           "arms": g2_arms,
                           "rule": "a G1 arm keeps deadzone@5e-2 >= 0.90 AND boot CI_low > 0.90"}},
            "booked_sentence": sentence, "grain": grain,
            "best_ramp_arm": best,
            "best_ramp@5e-2": scored[best]["regions"]["ramp"][f"{TOL_GATED:g}"]["mean"],
            "reference": {"b1f_hybridv2_w64_ramp@5e-2": 0.2930, "b1e_plain_w64_ramp@5e-2": REF_PLAIN_40,
                          "b1e_reweight_w64_ramp@5e-2": 0.7977, "b1f_linear_plain_w96_ramp@5e-2": 0.9617},
            "ramp_only": ramp_only,
            "verdicts": verdicts, "counted_arms": counted,
            "anchor_cap128": anchor,
            "control_anchor": {"deadzone@5e-2": anchor["deadzone"]["0.05"]["mean"],
                               "ramp@5e-2": anchor["ramp"]["0.05"]["mean"]},
            "region_frac": region_frac, "region_counts": region_counts,
            "controls": controls, "train": train_meta,
            "resume": {"enabled": bool(resume), "reused_models": resumed,
                       "n_reused": len(resumed), "n_trained": len(train_meta)},
            "elapsed_s": round(time.time() - t0, 1), "smoke": smoke,
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({
            "verdict": lane, "grain": grain, "sentence": sentence,
            "G_B1G1": G_B1G1, "G_B1G2": G_B1G2,
            "g1_arms": g1_arms, "g2_arms": g2_arms, "best": best,
            "best_ramp": round(ramp_only["rows"][best]["ramp@5e-2"], 4),
            "best_dz": round(ramp_only["rows"][best]["deadzone@5e-2"], 4),
            "trajectories": ramp_only["trajectories"],
            "vram_mb": round(vram_mb, 1), "elapsed_s": result["elapsed_s"]}), flush=True)
        if vram_mb > VRAM_CEIL_MB:
            print(f"WARN VRAM {vram_mb:.1f} MB > ceiling {VRAM_CEIL_MB}", flush=True)
    finally:
        eng.close()
    return 0


# ── append-window guard summaries (B1D/B1E/B1F wart fix) ─────────────────────
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

    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1G-epochs-vs-ramp-loss",
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
            {"lane": "B1G-EPOCHS-VS-RAMP-LOSS", "verdict": "NOT-RUN",
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
