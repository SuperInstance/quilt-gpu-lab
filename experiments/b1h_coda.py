#!/usr/bin/env python3
"""b1h_coda.py — lane B1H-CODA (the B1-family coda).

Pre-registration (FROZEN before fire): proposals/runs/B1H-coda.md.

Booked by B1G (results/b1g/RESULTS-ENTRY.md):

  (A) NAME THE HYBRID'S RAMP FLOOR — bisect the hybrid ramp atom-gate crossing
      {64, 72, 80, 88} at the best recipe (MSE, 160ep), name the width whose
      ramp@5e-2 crosses 0.90 (B1F w64 = 0.2930, B1G w96 = 0.9979 @160ep).
  (B) TWO-KNOT ATOM — at w96/160ep replace the single-knot learned ramp with a
      two-knot variant (k1 < k2, both learned; a1, a2 learned; a2 init 0 so the
      first forward is bit-identical to the single-knot family). Does the
      residual @1e-3 ramp tail (0.8247) yield >= 0.05 (CI excl 0) WITHOUT
      regressing the deadzone below 0.99?

Reuse: the B1G driver (b1g_epochs_vs_ramp_loss.py) is IMPORTED wholesale, which
itself imports the B1F driver + reuses the B1C engine UNCHANGED; B1D's saved
width-128 anchor nets are reused (controls C6/C7); B1G's own
model_hybridv2_w96_mse_seed2718_ep160.pt is reused as the Part B single-knot
arm (resume-not-rebuild). B1G's safeguards are kept (prereg-arm assert +
append-window guard snapshot).

House laws: seed 2718; fail loud; std==0 -> INCONCLUSIVE never PASS; receipt or
VOID; list-form subprocess only; verdict counts ONLY preregistered arms;
INSTRUMENT-01 ramp before measurement; append-window guard summaries; do NOT
commit.
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
PREREG = LAB / "proposals" / "runs" / "B1H-coda.md"
OUT_DIR = LAB / "results" / "b1h"
B1G_DIR = LAB / "results" / "b1g"
B1C_DIR = LAB / "results" / "b1c"
B1D_DIR = LAB / "results" / "b1d"
B1E_DIR = LAB / "results" / "b1e"
B1B_DIR = LAB / "results" / "b1b_kink_runB"
B1_DIR = LAB / "results" / "b1_distill"
B1G_SINGLE_REF = B1G_DIR / "model_hybridv2_w96_mse_seed2718_ep160.pt"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# B1G driver, imported wholesale: gives us Engine/gen/labels/arrays/regions/
# build_model/net_raw/predict/_bootstrap_ci + the frozen constants + paths.
b1g = _load("b1g_epochs_vs_ramp_loss", HERE / "b1g_epochs_vs_ramp_loss.py")
Engine = b1g.Engine
generate_traces = b1g.generate_traces
label_traces = b1g.label_traces
build_arrays = b1g.build_arrays
region_masks = b1g.region_masks
net_raw = b1g.net_raw
predict = b1g.predict
mean_std = b1g.mean_std
BATCH = b1g.BATCH
LR = b1g.LR
BCE_LAMBDA = b1g.BCE_LAMBDA
EPS = b1g.EPS
REPORT_TOLS = b1g.REPORT_TOLS
TOL_GATED = b1g.TOL_GATED

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
SEED = 2718
WIDTHS = (64, 72, 80, 88)          # Part A bisection set
EPOCHS = 160                        # B1G's best recipe
TWO_KNOT_WIDTH = 96                 # Part B
LOSS = "mse"

RAMP_FLOOR = 0.90                   # the gate the crossing is named on
CI_FLOOR = 0.90                     # CI lower bound must exceed it (family law)
TAIL_TOL = 1e-3                     # the sharp-tail tolerance
TAIL_GAIN_MIN = 0.05                # G-B1H2 bar (0.8247 -> >= 0.8747)
DZ_NO_REGRESS = 0.99                # G-B1H2: deadzone must not fall below
B1G_REF_RAMP_1E3 = 0.8246869409660107   # booked B1G h96_mse_ep160 ramp@1e-3
B1G_REF_RAMP_5E2 = 0.9979129397734049   # booked B1G h96_mse_ep160 ramp@5e-2
N_BOOT = 1000
BOOT_SEED = 2718
ANCHOR_WIDTH = 128
ANCHOR_TOL = 0.05
GUARD_TIMEOUT_S = 3600.0
WH_ENVELOPE = 3.0
VRAM_CEIL_MB = 1500.0

# ── the 5 preregistered arms (frozen) ───────────────────────────────────────
ARM_SPECS = tuple(
    [(f"w{w}_mse_ep{EPOCHS}", "hybridv2", w) for w in WIDTHS]
    + [(f"w{TWO_KNOT_WIDTH}_2knot_ep{EPOCHS}", "hybridv2_2k", TWO_KNOT_WIDTH)]
)
EXPECTED_ARMS = tuple(n for n, _k, _w in ARM_SPECS)
PART_A_ARMS = tuple(f"w{w}_mse_ep{EPOCHS}" for w in WIDTHS)
PART_B_ARM = f"w{TWO_KNOT_WIDTH}_2knot_ep{EPOCHS}"


# ── the two-knot atom (frozen design) ───────────────────────────────────────
_TWO_KNOT_CLS = None
_SP_INV_1P5 = None   # softplus^-1(1.5): gap init s.t. k2 init = 2.5


def _two_knot_class():
    global _TWO_KNOT_CLS, _SP_INV_1P5
    if _TWO_KNOT_CLS is not None:
        return _TWO_KNOT_CLS
    import math
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    _SP_INV_1P5 = math.log(math.expm1(1.5))     # log(e^1.5 - 1) = softplus^-1(1.5)
    _LinearMLP, HybridV2MLP = b1g.b1f._classes()

    class HybridV2TwoKnot(HybridV2MLP):
        """HybridV2MLP with the ramp atom replaced by a TWO-KNOT piecewise linear.

        atom(u) = sign(b-p) * [ a1*relu(u - k1) + a2*relu(u - k2) ]
          k1 = ramp_knot                       (learned, init 1.0)
          k2 = ramp_knot + softplus(ramp_gap)  (learned; k2 > k1 STRUCTURAL)
          a1 = ramp_slope                      (learned, init 1.0)
          a2 = ramp_slope2                     (learned, init 0.0 -> identical
                                                atom at init to the single-knot)
        """

        def __init__(self, width: int):
            super().__init__(width)
            self.ramp_slope2 = nn.Parameter(torch.zeros(()))
            self.ramp_gap = nn.Parameter(torch.tensor(float(_SP_INV_1P5)))

        def knot2(self):
            return self.ramp_knot + F.softplus(self.ramp_gap)

        def ramp_atom(self, X):
            dp = X[:, 1] - X[:, 0]
            u = torch.abs(dp) * 30.0
            sgn = torch.sign(dp)
            return sgn * (self.ramp_slope * F.relu(u - self.ramp_knot)
                          + self.ramp_slope2 * F.relu(u - self.knot2()))

    _TWO_KNOT_CLS = HybridV2TwoKnot
    return _TWO_KNOT_CLS


def build_model(kind: str, width: int, seed: int, device: str):
    if kind == "hybridv2_2k":
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        return _two_knot_class()(width).to(device)
    return b1g.build_model(kind, width, seed, device)


# ── training (B1G's loop verbatim, single milestone at `epochs`) ─────────────
def train_arm(kind, width, seed, Xtr, Ytr, Mtr, device, epochs, dzlab, ramplab):
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
    ZD = torch.from_numpy(np.asarray(dzlab, dtype=np.float32)).to(device)
    ZR = torch.from_numpy(np.asarray(ramplab, dtype=np.float32)).to(device)

    hist = []
    for _ep in range(1, epochs + 1):
        perm = torch.randperm(n, generator=g)
        tot = 0.0
        for k in range(0, n, BATCH):
            idx = perm[k:k + BATCH].to(device)
            opt.zero_grad()
            out = net_raw(net, kind, X[idx])
            pred = torch.clamp(p_all[idx] + out, 6.0, 54.0) - p_all[idx]
            se = mse(pred, Y[idx])
            loss = (se.mean() + BCE_LAMBDA * bce(net.gate_dz_logit(X[idx]), ZD[idx])
                    + BCE_LAMBDA * bce(net.gate_r_logit(X[idx]), ZR[idx]))
            loss.backward()
            opt.step()
            tot += float(loss.item()) * idx.shape[0]
        hist.append(tot / n)
    torch.cuda.synchronize()
    meta = {"arm_kind": kind, "width": width, "seed": seed, "epochs": epochs,
            "n_params": n_params, "batch": BATCH, "lr": LR,
            "final_train_loss": hist[-1], "first_train_loss": hist[0],
            "loss_fn": "deployed_mse + BCE gates (B1G verbatim)"}
    return net, meta


def learned_knots(net, kind):
    out = {"learned_a1": float(net.ramp_slope.detach()),
           "learned_k1": float(net.ramp_knot.detach())}
    if kind == "hybridv2_2k":
        out["learned_a2"] = float(net.ramp_slope2.detach())
        out["learned_k2"] = float(net.knot2().detach())
    return out


def score_net(net, kind, Mho, Yho, reg, device, want_hits=False):
    import numpy as np

    pr = predict(net, kind, Mho, device)
    diff = np.abs(pr - Yho)
    curve = {f"{t:g}": float(np.mean(diff <= t)) for t in EPS}
    regions = {}
    for rname, mask in reg.items():
        if int(mask.sum()) == 0:
            regions[rname] = {"n": 0}
            continue
        d = diff[mask]
        cell = {"n": int(mask.sum())}
        for t in REPORT_TOLS:
            hits = (d <= t)
            if t == TOL_GATED:
                m, lo, hi = b1g._bootstrap_ci(hits)
                cell[f"{t:g}"] = {"mean": m, "ci_low": lo, "ci_high": hi}
            else:
                cell[f"{t:g}"] = {"mean": float(np.mean(hits)),
                                  "std": float(np.std(hits))}
        regions[rname] = cell
    out = {"regions": regions, "curve_mean": curve,
           "n_params": int(sum(q.numel() for q in net.parameters()))}
    out.update(learned_knots(net, kind))
    if want_hits:
        out["ramp_hits_1e-3"] = (diff[reg["ramp"]] <= TAIL_TOL)
    return out


def paired_bootstrap(h2, h1, n_boot=N_BOOT, seed=BOOT_SEED):
    """Percentile bootstrap of the PAIRED mean difference (h2 - h1)."""
    import numpy as np
    a = np.asarray(h2, dtype=np.float64)
    b = np.asarray(h1, dtype=np.float64)
    n = a.shape[0]
    rng = np.random.default_rng(seed)
    d = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        d[i] = (a[idx] - b[idx]).mean()
    lo, hi = np.percentile(d, [2.5, 97.5])
    return float(a.mean() - b.mean()), float(lo), float(hi), float(np.std(d))


def ramp_burn(device) -> dict:
    """INSTRUMENT-01: >= 0.6 s sustained synced CUDA load before measurement."""
    import torch
    a = torch.randn(2048, 2048, device=device)
    t0 = time.time()
    while time.time() - t0 < 0.6:
        for _ in range(20):
            a = a @ a
            a = a / a.norm()
        torch.cuda.synchronize()
    return {"ramp_s": round(time.time() - t0, 3), "synced": True}


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

    n_traces = 2 if smoke else b1g.b1f.bc.TRACES_N
    ticks = 200 if smoke else b1g.b1f.bc.TRACE_TICKS
    epochs = 4 if smoke else EPOCHS
    smoke_width = 16
    # smoke keeps the PREREGISTERED arm NAMES (so every analysis path runs) at a
    # tiny width/epoch count; the run is never a booked artifact.
    arms_spec = (tuple((n, k, (smoke_width if k != "hybridv2_2k" else smoke_width))
                       for n, k, _w in ARM_SPECS) if smoke else ARM_SPECS)
    if not smoke:   # B1E/B1F/B1G safeguard: verdict-counted set == prereg arms
        assert sorted(n for n, _k, _w in arms_spec) == sorted(EXPECTED_ARMS), "arm set drift"

    (out_dir / "run_config.json").write_text(json.dumps({
        "prereg": str(PREREG), "harness": str(b1g.b1f.bc.HARNESS), "device": device,
        "device_name": dev_name, "torch": torch.__version__,
        "master_seed": MASTER_SEED, "seed": SEED,
        "frame": "B1/B1b/B1C/B1F/B1G's frame verbatim (reused B1G+ drivers/engine)",
        "traces_n": n_traces, "trace_ticks": ticks, "trace_seed_base": b1g.b1f.bc.TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {b1g.b1f.bc.HOLDOUT_MOD} == 0",
        "arms": [{"name": n, "kind": k, "width": w, "epochs": epochs, "loss": LOSS}
                 for n, k, w in arms_spec],
        "part_a_widths": list(WIDTHS), "part_b_width": TWO_KNOT_WIDTH,
        "two_knot_atom": "sign(b-p)*[a1*relu(u-k1)+a2*relu(u-k2)], k2=k1+softplus(gap)>k1, "
                         "a2 init 0 (first forward identical to single-knot), (a1,k1,a2,gap) learned",
        "gates": {"G_B1H1": f"some w in {list(WIDTHS)}: ramp@5e-2 >= {RAMP_FLOOR} AND ramp CI_low > {CI_FLOOR} "
                            f"AND deadzone@5e-2 >= {RAMP_FLOOR} AND deadzone CI_low > {CI_FLOOR} (crossing intact)",
                  "G_B1H2": f"two-knot paired ramp@1e-3 gain >= {TAIL_GAIN_MIN} AND paired-boot CI_low > 0 "
                            f"AND deadzone@5e-2 >= {DZ_NO_REGRESS} AND ramp@5e-2 >= {RAMP_FLOOR}"},
        "reference": {"b1g_h96_mse_ep160_ramp@5e-2": B1G_REF_RAMP_5E2,
                      "b1g_h96_mse_ep160_ramp@1e-3": B1G_REF_RAMP_1E3,
                      "b1f_hybridv2_w64_ramp@5e-2": 0.2930,
                      "b1e_plain_w64_ramp@5e-2": 0.5675,
                      "b1f_linear_plain_w96_ramp@5e-2": 0.9617},
        "bootstrap": {"B": N_BOOT, "seed": BOOT_SEED,
                      "partB": "paired percentile CI on mean(hit_2k - hit_1k) within ramp"},
        "control_anchor": f"width-{ANCHOR_WIDTH} linear-head plain == B1C cap arm, C6/C7 reused from B1D nets",
        "verdict_counts": f"PREREGISTERED ARMS ONLY ({len(EXPECTED_ARMS)}); anchor + single-knot ref = control",
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
            "frame": "B1/B1b/B1C/B1F/B1G verbatim", "traces_n": n_traces, "trace_ticks": ticks,
            "trace_seed_base": b1g.b1f.bc.TRACE_SEED_BASE, "holdout_mod": b1g.b1f.bc.HOLDOUT_MOD,
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

        # ── atom labels (train split) ───────────────────────────────────────
        reg_tr = region_masks(Ytr, Mtr)
        dz_tr = reg_tr["deadzone"].astype(np.float32)
        ramp_tr = reg_tr["ramp"].astype(np.float32)
        print(f"[atoms] train deadzone={int(dz_tr.sum())} ramp={int(ramp_tr.sum())} "
              f"ramp_frac={float(ramp_tr.mean()):.4f}", flush=True)

        # ── INSTRUMENT-01: ramp before the measured window ──────────────────
        ramp = ramp_burn(device)
        print(f"[INSTRUMENT-01 ramp] {ramp}", flush=True)

        # ── train / reuse the arms ──────────────────────────────────────────
        nets, train_meta = {}, []
        for name, kind, width in arms_spec:
            mpath = out_dir / f"model_{name}_seed{SEED}_ep{epochs}.pt"
            if resume and mpath.exists():
                net = build_model(kind, width, SEED, device)
                net.load_state_dict(torch.load(mpath, map_location=device))
                nets[name] = net
                resumed.append(mpath.name)
                print(f"[reuse {name:20s} {SEED}] loaded", flush=True)
                continue
            net, tm = train_arm(kind, width, SEED, Xtr, Ytr, Mtr, device, epochs,
                                dzlab=dz_tr, ramplab=ramp_tr)
            nets[name] = net
            tm["name"] = name
            train_meta.append(tm)
            torch.save(net.state_dict(), mpath)
            print(f"[train {name:22s} {SEED}] {tm['first_train_loss']:.5g} -> "
                  f"{tm['final_train_loss']:.5g} ({tm['n_params']}p) "
                  f"{learned_knots(net, kind)}", flush=True)

        # ── reused B1G single-knot reference (control / Part B baseline) ────
        ref_net = b1g.build_model("hybridv2", TWO_KNOT_WIDTH, SEED, device)
        ref_net.load_state_dict(torch.load(B1G_SINGLE_REF, map_location=device))
        resumed.append(str(B1G_SINGLE_REF))
        print(f"[reuse single-knot ref] {B1G_SINGLE_REF.name}", flush=True)

        # ── regions + scoring ───────────────────────────────────────────────
        reg = region_masks(Yho, Mho)
        region_counts = {k: int(v.sum()) for k, v in reg.items()}
        region_frac = {k: float(v.mean()) for k, v in reg.items()}
        print("[regions] " + json.dumps({k: round(v, 4) for k, v in region_frac.items()}), flush=True)

        scored, verdicts = {}, {}
        for name, kind, width in arms_spec:
            r = score_net(nets[name], kind, Mho, Yho, reg, device, want_hits=True)
            scored[name] = r
            dz = r["regions"]["deadzone"][f"{TOL_GATED:g}"]
            rp = r["regions"]["ramp"][f"{TOL_GATED:g}"]
            verdicts[name] = {"kind": kind, "width": width, "epochs": epochs,
                              "regions": r["regions"], "curve_mean": r["curve_mean"],
                              "n_params": r["n_params"], "learned": learned_knots(nets[name], kind),
                              "crossing_pass": bool(dz["mean"] >= RAMP_FLOOR and rp["mean"] >= RAMP_FLOOR)}
            print(f"[gate {name:22s}] dz={dz['mean']:.4f} CI[{dz['ci_low']:.4f},{dz['ci_high']:.4f}] "
                  f"ramp={rp['mean']:.4f} CI[{rp['ci_low']:.4f},{rp['ci_high']:.4f}] "
                  f"ramp@1e-2={r['regions']['ramp'][f'{1e-2:g}']['mean']:.4f} "
                  f"ramp@1e-3={r['regions']['ramp'][f'{TAIL_TOL:g}']['mean']:.4f} "
                  f"{learned_knots(nets[name], kind)}", flush=True)

        ref = score_net(ref_net, "hybridv2", Mho, Yho, reg, device, want_hits=True)
        print(f"[ref single-knot h96_mse_ep160] ramp@5e-2="
              f"{ref['regions']['ramp'][f'{TOL_GATED:g}']['mean']:.4f} "
              f"ramp@1e-3={ref['regions']['ramp'][f'{TAIL_TOL:g}']['mean']:.4f}", flush=True)

        # ── controls C6/C7: reuse B1D width-128 anchor nets ─────────────────
        anchor_seeds = (2718, 2719, 2720)
        anchor_scores = []
        for seed in anchor_seeds:
            apath = B1D_DIR / f"model_anchor_cap128_seed{seed}_ep40.pt"
            net = b1g.build_model("anchor", ANCHOR_WIDTH, seed, device)
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

        # ── PART A: name the hybrid ramp floor (prereg arms only) ──────────
        def gated(nm, rname):
            cell = scored[nm]["regions"].get(rname, {})
            if int(cell.get("n", 0)) == 0 or f"{TOL_GATED:g}" not in cell:
                return None
            return cell[f"{TOL_GATED:g}"]

        def arm_inconclusive(nm):
            return gated(nm, "ramp") is None or gated(nm, "deadzone") is None

        def clears(nm):
            rp, dz = gated(nm, "ramp"), gated(nm, "deadzone")
            if rp is None or dz is None:
                return False
            return bool(rp["mean"] >= RAMP_FLOOR and rp["ci_low"] > CI_FLOOR
                        and dz["mean"] >= RAMP_FLOOR and dz["ci_low"] > CI_FLOOR)

        def soft_clears(nm):
            rp = gated(nm, "ramp")
            return bool(rp is not None and rp["mean"] >= RAMP_FLOOR)

        part_a = {"rows": {}, "note": "width bisection, hybridv2 MSE 160ep, seed 2718 (boot CI over holdout)"}
        for w in WIDTHS:
            nm = f"w{w}_mse_ep{EPOCHS}"
            rp, dz = gated(nm, "ramp"), gated(nm, "deadzone")
            part_a["rows"][nm] = {
                "width": w, "params": scored[nm]["n_params"],
                "ramp@5e-2": (rp or {}).get("mean"), "ramp@5e-2_ci": ([rp["ci_low"], rp["ci_high"]] if rp else None),
                "ramp@1e-2": scored[nm]["regions"].get("ramp", {}).get(f"{1e-2:g}", {}).get("mean"),
                "ramp@1e-3": scored[nm]["regions"].get("ramp", {}).get(f"{TAIL_TOL:g}", {}).get("mean"),
                "deadzone@5e-2": (dz or {}).get("mean"),
                "deadzone@5e-2_ci": ([dz["ci_low"], dz["ci_high"]] if dz else None),
                "clears_0.90_ci": clears(nm), "clears_0.90_mean": soft_clears(nm),
                "inconclusive": arm_inconclusive(nm),
                **learned_knots(nets[nm], "hybridv2")}
        clearing = [w for w in WIDTHS if clears(f"w{w}_mse_ep{EPOCHS}")]
        clearing_soft = [w for w in WIDTHS if soft_clears(f"w{w}_mse_ep{EPOCHS}")]
        floor = min(clearing) if clearing else None
        floor_soft = min(clearing_soft) if clearing_soft else None
        G_B1H1 = bool(clearing)
        part_a["clearing_widths"] = clearing
        part_a["clearing_widths_mean_only"] = clearing_soft
        part_a["inconclusive_arms"] = [n for n, _k, _w in arms_spec if arm_inconclusive(n)]
        part_a["named_hybrid_floor"] = floor
        part_a["named_hybrid_floor_mean_only"] = floor_soft
        part_a["statement"] = (
            f"hybrid ramp atom-gate floor = {floor} (ramp@5e-2 >= 0.90 with CI_low > 0.90)"
            if floor is not None else
            f"hybrid ramp atom-gate floor > {max(WIDTHS)} (no width <= {max(WIDTHS)} clears 0.90 with CI_low > 0.90)")
        # include the B1G w96 point + plain references for pairing
        part_a["pairing"] = {"b1g_w96_mse_ep160_ramp@5e-2": B1G_REF_RAMP_5E2,
                             "b1f_hybridv2_w64_40ep_ramp@5e-2": 0.2930,
                             "b1e_plain_w64_ramp@5e-2": 0.5675,
                             "b1f_linear_plain_w96_ramp@5e-2": 0.9617}
        print(f"[PART A] {part_a['statement']} clearing={clearing} (mean-only {clearing_soft})", flush=True)

        # ── PART B: two-knot atom vs reused single-knot (paired) ────────────
        h2 = scored[PART_B_ARM]["ramp_hits_1e-3"]
        h1 = ref["ramp_hits_1e-3"]
        gain, lo, hi, bstd = paired_bootstrap(h2, h1)
        r1e3_2k = float(h2.mean())
        r1e3_1k = float(h1.mean())
        dz2 = scored[PART_B_ARM]["regions"]["deadzone"][f"{TOL_GATED:g}"]["mean"]
        rp2 = scored[PART_B_ARM]["regions"]["ramp"][f"{TOL_GATED:g}"]["mean"]
        inconclusive_b = bool(bstd == 0.0)
        G_B1H2 = bool((gain >= TAIL_GAIN_MIN) and (lo > 0.0)
                      and (dz2 >= DZ_NO_REGRESS) and (rp2 >= RAMP_FLOOR))
        if inconclusive_b:
            G_B1H2 = False
        tail = {
            "single_knot": {"arm": "b1g h96_mse_ep160 (reused)",
                            "ramp@1e-3": r1e3_1k, "ramp@5e-2": B1G_REF_RAMP_5E2,
                            "deadzone@5e-2": scored and None},
            "two_knot": {"arm": PART_B_ARM, "ramp@1e-3": r1e3_2k,
                         "ramp@5e-2": rp2, "deadzone@5e-2": dz2,
                         "learned": learned_knots(nets[PART_B_ARM], "hybridv2_2k"),
                         "n_params": scored[PART_B_ARM]["n_params"]},
            "paired_gain@1e-3": {"point": gain, "ci_low": lo, "ci_high": hi,
                                 "boot_std": bstd, "B": N_BOOT, "seed": BOOT_SEED,
                                 "n_ramp": int(len(h2))},
            "ref_single_knot_ramp@1e-3": r1e3_1k,
            "single_knot_n_params": ref["n_params"],
            "two_knot_n_params": scored[PART_B_ARM]["n_params"],
            "param_budget_pct": (100.0 * (scored[PART_B_ARM]["n_params"] - ref["n_params"])
                                 / ref["n_params"]),
            "param_budget_ok": bool(abs(scored[PART_B_ARM]["n_params"] - ref["n_params"])
                                    / ref["n_params"] <= 0.20),
            "gates": {"gain_bar": TAIL_GAIN_MIN, "ci_excl_0": bool(lo > 0.0),
                      "deadzone_no_regress_bar": DZ_NO_REGRESS, "deadzone@5e-2": dz2,
                      "crossing_ramp_bar": RAMP_FLOOR, "ramp@5e-2": rp2,
                      "inconclusive_boot_std0": inconclusive_b},
        }
        print(f"[PART B] 2knot ramp@1e-3={r1e3_2k:.4f} vs 1knot {r1e3_1k:.4f} "
              f"gain={gain:+.4f} CI[{lo:+.4f},{hi:+.4f}] dz={dz2:.4f} ramp={rp2:.4f} "
              f"G_B1H2={G_B1H2}", flush=True)

        if G_B1H2:
            sentence = "the residual @1e-3 ramp tail was interface-shaped — two knots buy it."
            grain = "TAIL-INTERFACE"
            lane = "KEEP"
        elif inconclusive_b:
            sentence = "two-knot comparison degenerate (zero-variance bootstrap) — INCONCLUSIVE, not booked as a limit."
            grain = "INCONCLUSIVE"
            lane = "INCONCLUSIVE"
        else:
            sentence = "the tail is the map's intrinsic quantization — B1 closes with the tail booked as a limit."
            grain = "TAIL-QUANTIZED"
            lane = "KILL"

        # ── write artifacts ─────────────────────────────────────────────────
        (out_dir / "crossing.json").write_text(json.dumps(part_a, indent=2))
        (out_dir / "tail.json").write_text(json.dumps(tail, indent=2))
        (out_dir / "regions.json").write_text(json.dumps(
            {"counts": region_counts, "frac": region_frac,
             "tol_gated": TOL_GATED, "ramp_floor": RAMP_FLOOR, "ci_floor": CI_FLOOR,
             "per_arm": {k: {"meta": {kk: vv for kk, vv in v.items()
                                      if kk not in ("regions", "curve_mean")},
                             "regions": v["regions"]} for k, v in verdicts.items()},
             "reference_single_knot_h96_mse_ep160": {
                 "regions": ref["regions"], "n_params": ref["n_params"],
                 **learned_knots(ref_net, "hybridv2")}}, indent=2))
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        result = {
            "lane": "B1H-CODA",
            "claim": "name the hybrid ramp atom-gate crossing width; test whether a two-knot "
                     "ramp atom buys the residual @1e-3 ramp tail without deadzone regression",
            "verdict": lane, "grain": grain, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1), "vram_ceiling_mb": VRAM_CEIL_MB,
            "seed": SEED, "epochs": epochs, "loss": LOSS,
            "gates": {
                "G_B1H1": {"pass": G_B1H1, "bar": RAMP_FLOOR, "ci_floor": CI_FLOOR,
                           "clearing_widths": clearing, "clearing_widths_mean_only": clearing_soft,
                           "rule": "some w: ramp@5e-2 >= 0.90 AND CI_low > 0.90 AND deadzone >= 0.90 AND CI_low > 0.90"},
                "G_B1H2": {"pass": G_B1H2, "gain_bar": TAIL_GAIN_MIN, "gain": gain,
                           "ci": [lo, hi], "deadzone@5e-2": dz2, "ramp@5e-2": rp2,
                           "rule": "paired ramp@1e-3 gain >= 0.05 AND CI_low > 0 AND deadzone@5e-2 >= 0.99 AND ramp@5e-2 >= 0.90"}},
            "part_a_crossing": part_a, "part_b_tail": tail,
            "named_hybrid_floor": floor, "named_hybrid_floor_mean_only": floor_soft,
            "booked_sentence": sentence,
            "reference_single_knot": {"ramp@1e-3": r1e3_1k, "ramp@5e-2": B1G_REF_RAMP_5E2,
                                      "n_params": ref["n_params"]},
            "verdicts": verdicts, "counted_arms": list(EXPECTED_ARMS),
            "anchor_cap128": anchor, "region_frac": region_frac, "region_counts": region_counts,
            "controls": controls, "train": train_meta, "instrument_ramp": ramp,
            "resume": {"enabled": bool(resume), "reused_models": resumed,
                       "n_reused": len(resumed), "n_trained": len(train_meta)},
            "elapsed_s": round(time.time() - t0, 1), "smoke": smoke,
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({
            "lane": "B1H-CODA", "verdict": lane, "grain": grain, "sentence": sentence,
            "named_floor": floor, "named_floor_mean_only": floor_soft,
            "part_a_rows": {f"w{w}": round(scored[f'w{w}_mse_ep{EPOCHS}']["regions"]["ramp"][f"{TOL_GATED:g}"]["mean"], 4)
                            for w in WIDTHS},
            "part_b": {"gain": round(gain, 4), "ci": [round(lo, 4), round(hi, 4)],
                       "ramp@1e-3_2knot": round(r1e3_2k, 4), "ramp@1e-3_1knot": round(r1e3_1k, 4),
                       "dz": round(dz2, 4), "ramp@5e-2": round(rp2, 4), "G_B1H2": G_B1H2,
                       "knots": learned_knots(nets[PART_B_ARM], "hybridv2_2k")},
            "vram_mb": round(vram_mb, 1), "elapsed_s": result["elapsed_s"]}), flush=True)
        if vram_mb > VRAM_CEIL_MB:
            print(f"WARN VRAM {vram_mb:.1f} MB > ceiling {VRAM_CEIL_MB}", flush=True)
    finally:
        eng.close()
    return 0


# ── append-window guard summaries (B1D/B1E/B1F/B1G wart fix) ─────────────────
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

    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1H-coda",
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
            {"lane": "B1H-CODA", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        _snapshot_window(out_dir / "guard")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    if resume:
        cmd.append("--resume")
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-8000:], flush=True)
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
