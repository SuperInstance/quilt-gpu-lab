#!/usr/bin/env python3
"""ie2 — blob-only reader: is IE1's blob gap a reader problem or a sensor problem?

Pre-registered: proposals/runs/IE2-plan.md. ONE delta vs IE1: the ridge reader
trains on BLOB-ONLY sequences, tests blob-only. Gate: r2(direction) >= 0.5 at
>= 2 of 3 densities, tau = 2 frames. KEEP -> reader dilution (H-reader);
KILL -> wide-field pooling cannot carry small-field motion (H-sensor, matches
fly biology: objects read in lobula, not the LPTC wide-field path).

CPU-only numpy (system python3), same as IE1. No GPU lock.
"""
import importlib.util
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "results"))

spec = importlib.util.spec_from_file_location("ie1", os.path.join(HERE, "ie1_reichardt.py"))
ie1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ie1)  # main() is __main__-guarded


def blob_dataset(n, tau):
    """Blob-only dataset at density n. Same seed protocol as IE1 (fresh ci space)."""
    cfgs = []
    for sigma in ie1.BLOB_SIGMAS:
        for v in ie1.BLOB_SPEEDS:
            for name in ie1.DIR_ORDER:
                cfgs.append(dict(sigma=sigma, v=v, dvec=ie1.DIRS[name]))

    def collect(split_offset):
        feats, y_dir = [], []
        for ci, kw in enumerate(cfgs):
            n_seq = ie1.N_TRAIN_SEQ if split_offset == 0 else ie1.N_TEST_SEQ
            for si in range(n_seq):
                rng = np.random.default_rng(ie1.SEED_BASE + 1000 * ci + 10 * si + split_offset)
                seq = ie1.blob_scene(n, kw["sigma"], kw["v"], kw["dvec"],
                                     ie1.WARMUP + ie1.T_FRAMES, rng)
                codes = ie1.fam_codes(seq, tau)[ie1.WARMUP:]
                feats.append(codes)
                vx, vy = kw["dvec"]
                y_dir.append(np.tile(np.array([vx, vy]), (ie1.T_FRAMES, 1)))
        return np.concatenate(feats), np.concatenate(y_dir)

    return collect(0), collect(100)


def eval_blob(n, tau):
    (x_tr, y_tr), (x_te, y_te) = blob_dataset(n, tau)
    m = ie1.fit_ridge(x_tr, y_tr)
    pred = ie1.apply_ridge(m, x_te)
    return {"tau_frames": tau,
            "train_frames": int(len(x_tr)), "test_frames": int(len(x_te)),
            "r2_direction": round(ie1.r2_multi(y_te, pred), 6),
            "cardinal_accuracy": round(ie1.cardinal_accuracy(y_te, pred), 6)}


def amplitude_dilution(n, tau=ie1.TAU_BASELINE):
    """Mean |pooled R code|: blob vs grating at matched speed, per density."""
    rng = np.random.default_rng(ie1.SEED_BASE + 555)
    g = ie1.grating_scene(n, 8.0, 0.5, ie1.DIRS["R"], ie1.WARMUP + ie1.T_FRAMES, rng)
    b = ie1.blob_scene(n, 2.0, 0.5, ie1.DIRS["R"], ie1.WARMUP + ie1.T_FRAMES, rng)
    cg = np.abs(ie1.fam_codes(g, tau)[ie1.WARMUP:, 0]).mean()
    cb = np.abs(ie1.fam_codes(b, tau)[ie1.WARMUP:, 0]).mean()
    return {"grating_mean_abs_R": round(float(cg), 8),
            "blob_mean_abs_R": round(float(cb), 8),
            "ratio_blob_over_grating": round(float(cb / cg), 4)}


def main():
    t0 = time.time()
    out = {"experiment": "ie2 blob-only reader (sensor gap or reader dilution?)",
           "date": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "plan": "proposals/runs/IE2-plan.md",
           "cpu_only": True, "numpy_version": np.__version__,
           "config": {"delta": "ridge reader trained blob-only, tested blob-only; "
                               "all else identical to IE1 (sigma 2/3, speeds 0.25/0.5, "
                               "4 cardinals, 3 densities, tau 2, ridge alpha 0.01)",
                      "gate": "blob-only r2(direction) >= 0.5 at >= 2 of 3 densities, tau=2",
                      "seed_base": ie1.SEED_BASE}}
    print("[ie2] blob-only reader gate, tau=2", flush=True)
    for n in ie1.DENSITIES:
        res = eval_blob(n, ie1.TAU_BASELINE)
        out[f"gate_density_{n}"] = res
        print(f"[ie2] density {n}: R2_dir={res['r2_direction']} "
              f"acc={res['cardinal_accuracy']}", flush=True)
    passing = sum(1 for n in ie1.DENSITIES
                  if out[f"gate_density_{n}"]["r2_direction"] >= ie1.GATE_THRESHOLD)
    out["gate_densities_passing"] = passing
    out["verdict"] = "KEEP" if passing >= ie1.GATE_MIN_DENSITIES else "KILL"
    out["interpretation"] = ("H-reader: gap was training-distribution dilution; "
                             "lobula-plate rung carries small-field direction"
                             if out["verdict"] == "KEEP" else
                             "H-sensor: small-field motion past the wide-field pooling "
                             "rung's envelope (lobula object pathway territory, not LPTC)")
    print(f"[ie2] GATE: {passing}/{len(ie1.DENSITIES)} densities -> {out['verdict']}", flush=True)

    print("[ie2] blob-only tau sweep (density 16, descriptive)", flush=True)
    out["tau_sweep_density16"] = {}
    for tau in ie1.TAU_SWEEP:
        res = eval_blob(16, tau)
        out["tau_sweep_density16"][str(tau)] = res
        print(f"[ie2]   tau={tau}: R2_dir={res['r2_direction']}", flush=True)

    print("[ie2] amplitude dilution (descriptive)", flush=True)
    out["amplitude_dilution"] = {}
    for n in ie1.DENSITIES:
        res = amplitude_dilution(n)
        out["amplitude_dilution"][str(n)] = res
        print(f"[ie2]   density {n}: blob/grating amplitude ratio = "
              f"{res['ratio_blob_over_grating']}", flush=True)

    out["seconds"] = round(time.time() - t0, 1)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "ie2_blob_reader.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"[ie2] DONE {out['seconds']}s -> results/ie2_blob_reader.json", flush=True)
    print(json.dumps({"verdict": out["verdict"], "passing": passing,
                      "r2_by_density": {n: out[f"gate_density_{n}"]["r2_direction"]
                                        for n in ie1.DENSITIES},
                      "amplitude_ratio": {n: out["amplitude_dilution"][str(n)]["ratio_blob_over_grating"]
                                          for n in ie1.DENSITIES}}), flush=True)


if __name__ == "__main__":
    main()
