#!/usr/bin/env python3
"""b1_distill.py — lane B1-DISTILL: policy distillation of the pong derived law.

Pre-registration (FROZEN before fire): proposals/runs/B1-pong-law-distill.md.
Harvest of fleet-triage/docs/RTX4050-WORKLIST.md item B1.

The teacher is the SHIPPED quilt-arcade pong derived law (`games/pong/sheet.mjs`
cell `ai.track`), executed by the engine — never reimplemented here. Traces are
generated in the frozen frame "uniform-random reachable states" (both paddles
uniform-random {−1,0,+1}, engine-driven), held out by WHOLE trace. A tiny MLP
(3→64→64→1, 4,481 params) is trained on GPU; two receipts are booked:

  Gate A — per-tick action agreement vs the law on HELD-OUT traces.
  Gate B — h2h win-rate of the distilled policy vs the law over 100 seeds ×2
           sides (sides swapped), 3 training seeds, mean±std.

Energy is booked by guard.py's G7 watt receipt: this script re-execs itself as
the guarded child (`--inner`) so the whole measured window is sampled.

House laws: seed 2718; fail loud; std==0 → INCONCLUSIVE never PASS; receipt or
VOID; do NOT commit.
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
HARNESS = HERE / "b1_pong_law_engine.mjs"
DEFAULT_OUT = LAB / "results" / "b1_distill"
PREREG = LAB / "proposals" / "runs" / "B1-pong-law-distill.md"

# ── FROZEN CONSTANTS (mirror the pre-registration; do not tune post-fire) ────
MASTER_SEED = 2718
TRAIN_SEEDS = (2718, 2719, 2720)
TRACES_N = 240
TRACE_TICKS = 1200
TRACE_SEED_BASE = 900000
HOLDOUT_MOD = 5           # trace i is holdout iff i % 5 == 0  -> 48 holdout traces
H2H_SEEDS = list(range(2718, 2818))   # 100 seeds
MAX_TICKS = 20000
TOL = 1e-3                # primary per-tick agreement tolerance (field units)
TOL_STRICT = 1e-6
EPS = (1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)   # agreement-vs-tolerance curve points
GATE_A_MIN = 0.99
GATE_B_LO, GATE_B_HI = 0.40, 0.60
EPOCHS = 40
BATCH = 4096
LR = 1e-3
NORM = 30.0               # inputs normalised: (x-30)/30 ; side in {0,1}
GUARD_TIMEOUT_S = 10800.0
FLOOR_MIB = 1024          # co-tenancy retry rule (<1 GB free -> retry once after 60 s)


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


# ── phase 1: traces (engine-driven law labels) ───────────────────────────────
def generate_traces(eng: Engine) -> dict:
    trace_samples, trace_meta = [], []
    for i in range(TRACES_N):
        seed = TRACE_SEED_BASE + i
        r = eng.send({"cmd": "collect", "seed": seed, "left": "random", "right": "random",
                      "ticks": TRACE_TICKS, "rngSeed": seed})
        samples = r["samples"]
        trace_samples.append(samples)
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
        # store as 2 labels per sample
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


# ── phase 2: train ───────────────────────────────────────────────────────────
def train_one(seed: int, Xtr, Ytr, device: str, out_dir: Path):
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    net = nn.Sequential(nn.Linear(3, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(),
                        nn.Linear(64, 1)).to(device)
    n_params = sum(p.numel() for p in net.parameters())
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    lossf = nn.MSELoss()

    X = torch.from_numpy(Xtr).to(device)
    Y = torch.from_numpy(Ytr).to(device)
    n = X.shape[0]
    g = torch.Generator(device="cpu").manual_seed(seed)
    hist = []
    for ep in range(EPOCHS):
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
    return net, {"seed": seed, "n_params": n_params,
                 "final_train_mse": hist[-1], "first_train_mse": hist[0],
                 "epochs": EPOCHS, "batch": BATCH, "lr": LR}


def export_net(net) -> dict:
    import torch
    with torch.no_grad():
        W1, b1 = net[0].weight.cpu().numpy(), net[0].bias.cpu().numpy()
        W2, b2 = net[2].weight.cpu().numpy(), net[2].bias.cpu().numpy()
        W3, b3 = net[4].weight.cpu().numpy(), net[4].bias.cpu().numpy()
    return {"W1": W1.tolist(), "b1": b1.tolist(), "W2": W2.tolist(),
            "b2": b2.tolist(), "W3": W3.tolist(), "b3": b3.tolist()}


def torch_forward(net, meta):
    import numpy as np
    import torch
    X = np.stack([[(m[0] - 30.0) / NORM, (m[1] - 30.0) / NORM, m[2]] for m in meta])
    with torch.no_grad():
        return net(torch.from_numpy(X.astype(np.float32)).to(next(net.parameters()).device)).squeeze(-1).cpu().numpy()


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
        "frame": "uniform-random reachable states (engine-driven, both paddles U{-1,0,+1})",
        "traces_n": TRACES_N, "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
        "holdout_rule": f"trace index % {HOLDOUT_MOD} == 0",
        "tol": TOL, "tol_strict": TOL_STRICT,
        "gate_a": {"min_mean": GATE_A_MIN, "std_zero": "INCONCLUSIVE"},
        "gate_b": {"lo": GATE_B_LO, "hi": GATE_B_HI, "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
                   "n_seeds": len(H2H_SEEDS), "max_ticks": MAX_TICKS},
        "model": {"arch": "3-64-64-1 tanh", "params": 4481, "epochs": EPOCHS,
                  "batch": BATCH, "lr": LR},
    }, indent=2))

    eng = Engine()
    try:
        traces = generate_traces(eng)
        label_traces(eng, traces)
        (Xtr, Ytr, Mtr), (Xho, Yho, Mho) = build_arrays(traces)
        print(f"[data] train={Xtr.shape[0]} holdout={Xho.shape[0]}", flush=True)

        np.savez_compressed(out_dir / "holdout_samples.npz",
                            X=Xho, Y=Yho, META=Mho,
                            trace_meta=np.array([json.dumps(m) for m in traces["meta"]]))
        (out_dir / "traces_meta.json").write_text(json.dumps({
            "frame": "uniform-random reachable states", "traces_n": TRACES_N,
            "trace_ticks": TRACE_TICKS, "trace_seed_base": TRACE_SEED_BASE,
            "holdout_mod": HOLDOUT_MOD, "n_train_samples": int(Xtr.shape[0]),
            "n_holdout_samples": int(Xho.shape[0]), "traces": traces["meta"],
        }, indent=2))

        # ── control 1: switch-law vs pristine-law on holdout states (bit-identical?)
        sub = Mho[::max(1, len(Mho) // 4000)][:4000]
        eq = eng.send({"cmd": "laweq", "states": [
            {"p": float(m[0]), "b": float(m[1]), "side": "left" if m[2] == 0 else "right"}
            for m in sub]})

        # ── train 3 nets
        nets, train_meta = {}, []
        for seed in TRAIN_SEEDS:
            net, tm = train_one(seed, Xtr, Ytr, device, out_dir)
            nets[seed] = net
            train_meta.append(tm)
            torch.save(net.state_dict(), out_dir / f"model_seed{seed}.pt")
            print(f"[train {seed}] mse {tm['first_train_mse']:.6g} -> {tm['final_train_mse']:.6g}",
                  flush=True)

        # ── control 2: JS forward vs torch forward on holdout states
        port = []
        submeta = [(float(m[0]), float(m[1]), float(m[2])) for m in Mho[:50000]]
        js_pairs = [[p, b] for p, b, _s in submeta]
        for seed in [TRAIN_SEEDS[0]]:
            net = nets[seed]
            eng.send({"cmd": "setnet", "side": "left", "net": export_net(net)})
            js = np.asarray(eng.send({"cmd": "netforward", "side": "left",
                                      "pairs": js_pairs})["deltas"])
            tpred = torch_forward(net, submeta)
            port.append({"seed": seed, "n": len(js_pairs),
                         "max_abs_diff_js_vs_torch": float(np.max(np.abs(js - tpred)))})

        # ── Gate A: agreement on held-out traces
        agree = {"per_seed": [], "tol": TOL, "tol_strict": TOL_STRICT}
        for seed in TRAIN_SEEDS:
            pred = torch_forward(nets[seed], Mho)
            diff = np.abs(pred - Yho)
            law_letter = np.where(np.abs(Yho) == 0.0, "S", np.where(Yho > 0, "D", "U"))
            pred_letter = np.where(np.abs(pred) <= TOL, "S", np.where(pred > 0, "D", "U"))
            moving = np.abs(Yho) > 0.0
            a = {
                "seed": seed,
                "n": int(len(Yho)),
                "agreement_1e-3": float(np.mean(diff <= TOL)),
                "agreement_1e-6": float(np.mean(diff <= TOL_STRICT)),
                "agreement_letter": float(np.mean(law_letter == pred_letter)),
                "agreement_direction_where_law_moves": float(
                    np.mean(np.sign(pred[moving]) == np.sign(Yho[moving]))),
                "mean_abs_err": float(np.mean(diff)),
                "rms_err": float(np.sqrt(np.mean(diff ** 2))),
                "max_abs_err": float(np.max(diff)),
                "max_abs_pred": float(np.max(np.abs(pred))),
                "curve": {f"{t:g}": float(np.mean(diff <= t)) for t in EPS},
            }
            agree["per_seed"].append(a)
            print(f"[gateA {seed}] agree1e-3={a['agreement_1e-3']:.6f} "
                  f"letter={a['agreement_letter']:.6f} rms={a['rms_err']:.4g} "
                  f"maxerr={a['max_abs_err']:.3g}", flush=True)
        m, s = mean_std([a["agreement_1e-3"] for a in agree["per_seed"]])
        agree["mean"], agree["std"] = m, s
        ml, sl = mean_std([a["agreement_letter"] for a in agree["per_seed"]])
        agree["letter_mean"], agree["letter_std"] = ml, sl
        md, sd = mean_std([a["agreement_direction_where_law_moves"] for a in agree["per_seed"]])
        agree["direction_mean"], agree["direction_std"] = md, sd
        agree["curve_mean"] = {f"{t:g}": float(np.mean([a["curve"][f"{t:g}"]
                                                         for a in agree["per_seed"]]))
                               for t in EPS}
        agree["holdout_delta_zero_frac"] = float(np.mean(Yho == 0.0))
        agree["verdict"] = ("INCONCLUSIVE" if s == 0.0 else
                            ("PASS" if m >= GATE_A_MIN else "FAIL"))
        (out_dir / "agreement.json").write_text(json.dumps(agree, indent=2))

        # ── exploratory (NOT gated): optimization plateau or representational floor?
        sens = {"note": "EXPLORATORY, never folded into Gate A's verdict: a longer-training "
                         "control net, same arch/data/seed, to separate optimization from "
                         "representation at the frozen 1e-3 tolerance",
                "frozen_epochs": EPOCHS, "control_epochs": 300}
        try:
            globals()["EPOCHS"] = 300
            cnet, ctm = train_one(TRAIN_SEEDS[0], Xtr, Ytr, device, out_dir)
            globals()["EPOCHS"] = EPOCHS
            cd = np.abs(torch_forward(cnet, Mho) - Yho)
            sens["control"] = {"seed": TRAIN_SEEDS[0],
                               "final_train_mse": ctm["final_train_mse"],
                               "rms_err": float(np.sqrt(np.mean(cd ** 2))),
                               "curve": {f"{t:g}": float(np.mean(cd <= t)) for t in EPS}}
            print(f"[sens 300ep] rms={sens['control']['rms_err']:.4g} "
                  f"a1e-3={sens['control']['curve']['0.001']:.4f} "
                  f"a1e-1={sens['control']['curve']['0.1']:.4f}", flush=True)
        except Exception as exc:  # noqa: BLE001
            globals()["EPOCHS"] = EPOCHS
            sens["control"] = {"error": str(exc)}
        (out_dir / "sensitivity.json").write_text(json.dumps(sens, indent=2))

        # ── Gate B: h2h
        def play_many(tally, left_mode, right_mode):
            """Run the frozen seed set; count wins for side `tally` ('left'|'right')."""
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

        # control first (different path): law vs law, sides swapped. Both sides
        # are the identical law, so wins(left)+wins(right) == closed games and
        # the control rate lands at 0.50 by construction.
        cw = cd = cg = 0
        for tally in ("left", "right"):
            w, d, g = play_many(tally, "law", "law")
            cw += w; cd += d; cg += g
        control = {"wins": cw, "draws": cd, "games": cg,
                   "left_win_rate": cw / (cg - cd) if (cg - cd) else None}
        print(f"[h2h control] law-vs-law swapped win-rate={control['left_win_rate']} draws={cd}",
              flush=True)

        h2h = {"per_seed": [], "seeds": [H2H_SEEDS[0], H2H_SEEDS[-1]],
               "n_seeds": len(H2H_SEEDS), "max_ticks": MAX_TICKS,
               "protocol": "per seed two matches with sides swapped; win = first to 7; "
                           "rates use closed games only (draws booked)"}
        for seed in TRAIN_SEEDS:
            netw = export_net(nets[seed])
            eng.send({"cmd": "setnet", "side": "left", "net": netw})
            eng.send({"cmd": "setnet", "side": "right", "net": netw})
            w = d = g = 0
            for tally, lm, rm in (("left", "net", "law"), ("right", "law", "net")):
                ww, dd, gg = play_many(tally, lm, rm)
                w += ww; d += dd; g += gg
            rate = w / (g - d) if (g - d) else None
            h2h["per_seed"].append({"seed": seed, "wins": w, "draws": d, "games": g,
                                    "win_rate": rate})
            print(f"[gateB {seed}] win_rate={rate} wins={w} draws={d} games={g}", flush=True)
        m, s = mean_std([x["win_rate"] for x in h2h["per_seed"]])
        h2h["mean"], h2h["std"] = m, s
        h2h["control"] = control
        h2h["verdict"] = ("INCONCLUSIVE" if s == 0.0 else
                          ("PASS" if GATE_B_LO <= m <= GATE_B_HI else "FAIL"))
        (out_dir / "h2h.json").write_text(json.dumps(h2h, indent=2))

        controls = {"law_equivalence_switch_vs_pristine": eq,
                    "js_vs_torch_port": port,
                    "js_port_tolerance": 1e-6,
                    "law_equiv_pass": bool(eq["max_abs_diff"] == 0.0),
                    "js_port_pass": bool(all(p["max_abs_diff_js_vs_torch"] < 1e-6 for p in port))}
        (out_dir / "controls.json").write_text(json.dumps(controls, indent=2))

        vram_mb = torch.cuda.max_memory_allocated() / 1e6
        a_v, b_v = agree["verdict"], h2h["verdict"]
        if a_v == "PASS" and b_v == "PASS":
            verdict = "KEEP"
        elif a_v == "FAIL" and b_v == "PASS":
            verdict = "KILL"
        elif "INCONCLUSIVE" in (a_v, b_v):
            verdict = "INCONCLUSIVE"
        elif a_v == "PASS" and b_v == "FAIL":
            verdict = "PARTIAL"
        else:
            verdict = "FAIL"

        result = {
            "lane": "B1-DISTILL", "claim": "tiny MLP distilled from exact law traces "
            "reaches near-100% per-tick action agreement and is h2h-indistinguishable "
            "from the law",
            "verdict": verdict, "prereg": str(PREREG),
            "device": device, "device_name": dev_name,
            "gpu_peak_vram_mb": round(vram_mb, 1),
            "gate_a": {"verdict": a_v, "agreement_mean": agree["mean"],
                       "agreement_std": agree["std"], "per_seed": agree["per_seed"],
                       "letter_mean": agree["letter_mean"], "tol": TOL,
                       "direction_mean": agree["direction_mean"],
                       "curve_mean": agree["curve_mean"],
                       "holdout_delta_zero_frac": agree["holdout_delta_zero_frac"]},
            "gate_b": {"verdict": b_v, "win_rate_mean": h2h["mean"],
                       "win_rate_std": h2h["std"], "per_seed": h2h["per_seed"],
                       "control": control},
            "controls": controls,
            "train": train_meta,
            "elapsed_s": round(time.time() - t0, 1),
            "artifacts": sorted(p.name for p in out_dir.iterdir()),
        }
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        print("RESULT " + json.dumps({k: result[k] for k in
              ("verdict", "gpu_peak_vram_mb", "elapsed_s")}), flush=True)
        print("GATE_A " + json.dumps({k: result["gate_a"][k] for k in
              ("verdict", "agreement_mean", "agreement_std", "letter_mean",
               "direction_mean")}), flush=True)
        print("GATE_B " + json.dumps({k: result["gate_b"][k] for k in
              ("verdict", "win_rate_mean", "win_rate_std")}), flush=True)
    finally:
        eng.close()
    return 0


# ── outer (guarded) run ──────────────────────────────────────────────────────
def run_outer(out_dir: Path) -> int:
    g = guard.Guard(timeout_s=GUARD_TIMEOUT_S, task_id="B1-pong-law-distill",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed=str(MASTER_SEED), receipt_dir=str(out_dir / "guard"))

    # co-tenancy rule (<1 GB free): retry once after 60 s, else NOT-RUN.
    ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60 s", flush=True)
        time.sleep(60.0)
        ok = g.preflight()
    if not ok:
        print(f"PREFLIGHT REFUSED twice: {g.breach} — booking NOT-RUN", flush=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(
            {"lane": "B1-DISTILL", "verdict": "NOT-RUN",
             "reason": f"guard preflight refused twice (<1 GB free): {g.breach}"}, indent=2))
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused twice: {g.breach}")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()), "--inner", "--out", str(out_dir)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-3000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-1200:], flush=True)

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
