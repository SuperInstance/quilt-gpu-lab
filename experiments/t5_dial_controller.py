#!/usr/bin/env python3
"""t5 — the 5D dial controller (resolution<->framerate as a BEHAVIOR).

Casey's wave-5 hypothesis: the resolution-to-framerate dial is the generalized
saccade — still -> slide r up (CONFIRM: high-res/low-fps verification), moving
-> slide r down (PREDICT: low-res/high-fps extrapolation). Under a fixed
pixel-throughput budget, adaptive allocation should beat every fixed point.

Implements proposals/runs/t5-plan.md (v2 per its §7 abort addendum). Gate frozen
before the original code existed; v2 changed ONLY the shared per-arm estimator
(steady-state Kalman), not the gate/scene/budget/thresholds/seeds. CPU numpy.

Pixel-space honesty: the scene is a phase-space superposition of K sinusoidal
components; a component with amplitude A whose phase is off by dphi contributes
exactly 2*A^2*(1-cos(dphi)) pixel MSE — no small-angle approximation, no frames
materialized. The metric is closed-form pixel error.
"""
import json
import math
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- config ----
# FROZEN by proposals/runs/t5-plan.md — do not touch without a new plan.
DT = 1 / 40
TICKS_PER_SEC = 40
DURATION = 120.0
TICKS = int(DURATION * TICKS_PER_SEC)          # 4800
K = 4
AMPS = np.array([1.0, 0.8, 0.6, 0.5])
WTS = AMPS ** 2
OU_QUIET = (2.0, 0.12)                          # (tau_s, sigma_rad_per_s)
OU_BURST = (0.08, 1.4)
QUIET_LEN = (4.0, 9.0)                          # seconds, uniform
BURST_LEN = (0.8, 2.5)

BUDGET_PER_TICK = 0.5                           # 20 pts/s
TOTAL_BUDGET = BUDGET_PER_TICK * TICKS          # 2400
COST = {"hi": 4.0, "mid": 2.0, "lo": 1.0}
SIGMA = {"hi": 0.015, "mid": 0.05, "lo": 0.12}
CADENCE = {"hi": 8, "mid": 4, "lo": 2}          # ticks between acquisitions
MODE_RES = {"confirm": "hi", "mid": "mid", "predict": "lo"}

LEDGER_CAP = 8.0
LEDGER_INIT = 4.0

# adaptive controller (frozen)
Z_ENTER = 4.0          # surprise above this -> PREDICT
Z_EXIT = 1.5           # below this, sustained -> CONFIRM
Z_EXIT_OBS = 20        # consecutive observations below Z_EXIT
Z_EMA = 0.3            # EMA weight of the newest innovation
MIN_DWELL = 30         # ticks in a mode before switching (0.75 s)
RANDOM_FLIP = 1 / 60   # per-tick mode flip prob (mean dwell 1.5 s)

# v2 shared world prior (plan §7): every arm's filter assumes the expected
# (quiet) world — bursts are exactly the model violation surprise detects.
Q_U = 2 * OU_QUIET[1] ** 2 / OU_QUIET[0]   # 0.0144 rad^2/s^3 vel random walk

SEEDS = [41, 42, 43, 44, 45]
SMOKE_SEED = 999
SMOKE_TICKS = 30 * TICKS_PER_SEC

MODE_IDX = {"confirm": 0, "mid": 1, "predict": 2}
ARM_SEED_OFFSET = {"all-confirm": 11, "all-predict": 22, "all-mid": 33,
                   "random": 44, "oracle": 55, "adaptive": 66}
ARM_MODE = {"all-confirm": "confirm", "all-predict": "predict", "all-mid": "mid"}


# ----------------------------------------------------------------- truth ----
def make_regimes(rng, n_ticks):
    regimes = np.zeros(n_ticks, dtype=bool)  # True = burst
    t = 0
    while t < n_ticks:
        t = min(n_ticks, t + int(rng.uniform(*QUIET_LEN) * TICKS_PER_SEC))
        t2 = min(n_ticks, t + int(rng.uniform(*BURST_LEN) * TICKS_PER_SEC))
        regimes[t:t2] = True
        t = t2
    return regimes


def simulate_truth(seed, n_ticks=TICKS):
    rng = np.random.default_rng(seed)
    regimes = make_regimes(rng, n_ticks)
    phi = rng.uniform(0, 2 * np.pi, size=K)
    u = rng.normal(0.0, OU_QUIET[1], size=K)
    PH = np.empty((n_ticks, K))
    for tk in range(n_ticks):
        PH[tk] = phi
        tau, sig = OU_BURST if regimes[tk] else OU_QUIET
        th = math.exp(-DT / tau)
        u = u * th + sig * math.sqrt(1 - th * th) * rng.standard_normal(K)
        phi = phi + u * DT
    return regimes, PH


# ---------------------------------------------------------------- metrics ----
def surprise_series(PH):
    """s(t) = sum_i w_i (phi_i(t) - phi_i(t-10))^2 — true 0.25s velocity."""
    s = np.zeros(len(PH))
    d = PH[10:] - PH[:-10]
    s[10:] = np.sum(WTS * d * d, axis=1)
    return s


def make_weights(s):
    """W(t) = 1 + 4*clip(s/median(s) - 1, 0, 5)/5  (frozen)."""
    med = float(np.median(s[10:]))
    u = np.clip(s / med - 1.0, 0.0, 5.0) / 5.0
    return 1.0 + 4.0 * u


# ------------------------------------------------------------- v2 predictor ----
class ComponentKF:
    """Scalar 2-state KF [phi, u] for ONE scene component. Identical machinery
    for every arm and component; arms differ only via (R=sigma_res^2, how often
    updates happen). World prior q from the quiet OU."""

    F = np.array([[1.0, DT], [0.0, 1.0]])
    Q = Q_U * np.array([[DT ** 3 / 3, DT ** 2 / 2], [DT ** 2 / 2, DT]])
    H1 = np.array([1.0, 0.0])

    __slots__ = ("x", "P")

    def __init__(self):
        self.x = np.zeros(2)
        self.P = np.diag([1.0, 1.0])

    def tick(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, phi_obs, R):
        y = phi_obs - self.x[0]
        S = self.P[0, 0] + R
        k0, k1 = self.P[0, 0] / S, self.P[1, 0] / S
        self.x[0] += k0 * y
        self.x[1] += k1 * y
        p00, p01, p10, p11 = self.P[0, 0], self.P[0, 1], self.P[1, 0], self.P[1, 1]
        self.P[0, 0] = (1 - k0) * p00
        self.P[0, 1] = (1 - k0) * p01
        self.P[1, 0] = p10 - k1 * p00
        self.P[1, 1] = p11 - k1 * p01
        return y, S


class ArmFilter:
    """K independent ComponentKFs; observation R passed per acquisition so it
    always matches the CURRENT mode's resolution (adaptive arms switch it)."""

    def __init__(self):
        self.filters = [ComponentKF() for _ in range(K)]

    def tick(self):
        for f in self.filters:
            f.tick()

    def phases(self):
        return np.array([f.x[0] for f in self.filters])


# ------------------------------------------------------------------ arms ----
class Ledger:
    def __init__(self):
        self.bal = LEDGER_INIT
        self.spent = 0.0

    def income(self):
        self.bal = min(LEDGER_CAP, self.bal + BUDGET_PER_TICK)

    def try_spend(self, cost):
        if self.bal >= cost:
            self.bal -= cost
            self.spent += cost
            return True
        return False


def run_arm(arm, seed, PH, regimes, n_ticks=TICKS):
    rng = np.random.default_rng((seed * 1000 + ARM_SEED_OFFSET[arm]) % 2 ** 32)
    e = np.zeros(n_ticks)
    modes = np.full(n_ticks, -1, dtype=np.int8)
    ledger = Ledger() if arm in ("random", "oracle", "adaptive") else None

    z_ema, z_below_run = 1.0, 0
    current_mode = "confirm"
    mode_since = 0
    enter_predict_at = []

    is_fixed = arm in ARM_MODE
    filt = ArmFilter()

    for tk in range(n_ticks):
        if ledger is not None:
            ledger.income()

        # ---- allocation decision (the only thing that differs between arms)
        action = None
        if is_fixed:
            if tk % CADENCE[MODE_RES[ARM_MODE[arm]]] == 0:
                action = ARM_MODE[arm]
        elif arm == "random":
            if tk > 0 and rng.random() < RANDOM_FLIP:
                current_mode = "predict" if current_mode == "confirm" else "confirm"
                mode_since = 0
            action = current_mode
        elif arm == "oracle":
            current_mode = "predict" if regimes[tk] else "confirm"
            action = current_mode
        elif arm == "adaptive":
            if tk > 0:
                want = None
                if z_ema > Z_ENTER and current_mode != "predict" \
                        and mode_since >= MIN_DWELL:
                    want = "predict"
                elif (current_mode == "predict" and z_below_run >= Z_EXIT_OBS
                      and mode_since >= MIN_DWELL):
                    want = "confirm"
                if want and want != current_mode:
                    current_mode = want
                    mode_since = 0
                    if want == "predict":
                        enter_predict_at.append(tk)
            action = current_mode

        # ---- acquisition through the physical channel (same physics for all)
        observed = False
        if action is not None:
            res = MODE_RES[action]
            if ledger is None or ledger.try_spend(COST[res]):
                observed = True
                theta_obs = PH[tk] + SIGMA[res] * rng.standard_normal(K)
                z_raw_terms = []
                for i, f in enumerate(filt.filters):
                    y, S = f.update(float(theta_obs[i]), SIGMA[res] ** 2)
                    z_raw_terms.append(y * y / S)
                z_raw = float(np.mean(z_raw_terms))
                z_ema = (1 - Z_EMA) * z_ema + Z_EMA * z_raw
                if arm == "adaptive":
                    z_below_run = z_below_run + 1 if z_ema < Z_EXIT else 0

        if action is not None:
            modes[tk] = MODE_IDX[action]

        # ---- reconstruction for this tick, then the shared world-model tick
        filt.tick()
        e[tk] = pixel_mse_vec(filt.phases(), PH[tk])
        mode_since += 1

    # ---- spend accounting (single source of truth, checked for parity)
    if arm == "all-confirm":
        spend = COST["hi"] * len(range(0, n_ticks, CADENCE["hi"]))
    elif arm == "all-predict":
        spend = COST["lo"] * len(range(0, n_ticks, CADENCE["lo"]))
    elif arm == "all-mid":
        spend = COST["mid"] * len(range(0, n_ticks, CADENCE["mid"]))
    else:
        spend = ledger.spent

    stats = {"spend": spend}
    if arm in ("random", "oracle", "adaptive"):
        stats["frac_predict"] = float(np.mean(modes == 2))
        known = modes >= 0
        stats["switches"] = int(np.sum(known[1:] & known[:-1]
                                       & (modes[1:] != modes[:-1])))
        pred_burst = modes == 2
        tp = float(np.sum(pred_burst & regimes))
        stats["burst_precision"] = tp / max(1.0, float(np.sum(pred_burst)))
        stats["burst_recall"] = tp / max(1.0, float(np.sum(regimes)))
        if arm == "adaptive":
            onsets = np.flatnonzero(regimes[1:] & ~regimes[:-1]) + 1
            lats = []
            for on in onsets:
                later = [t for t in enter_predict_at if t >= on]
                if later:
                    lats.append((min(later) - on) * DT)
            stats["onset_latency_s"] = float(np.median(lats)) if lats else None
            stats["n_bursts"] = int(len(onsets))
            stats["missed_bursts"] = int(sum(
                1 for on in onsets
                if not any(on <= t < on + int(2.5 * TICKS_PER_SEC)
                           for t in enter_predict_at)))
    return e, stats


def pixel_mse_vec(phi_hat, phi_true):
    d = phi_hat - phi_true
    return float(np.sum(2.0 * WTS * (1.0 - np.cos(d))))


def score(e, W, regimes):
    sw = float(np.sum(W * e)) / float(np.sum(W))
    return {
        "sw_mse": sw,
        "mse": float(np.mean(e[10:])),
        "mse_quiet": float(np.mean(e[~regimes][10:])),
        "mse_burst": float(np.mean(e[regimes][10:])) if regimes[10:].any() else None,
    }


# ------------------------------------------------------------------ fire ----
ARMS = ["all-confirm", "all-predict", "all-mid", "random", "oracle", "adaptive"]
FIXED = ["all-confirm", "all-predict", "all-mid", "random"]


def fire(seeds, n_ticks=TICKS, label="official"):
    truths = {s: simulate_truth(s, n_ticks) for s in seeds}
    out = {"label": label, "config": {
        "dt": DT, "duration_s": DURATION, "K": K, "amps": AMPS.tolist(),
        "ou_quiet": OU_QUIET, "ou_burst": OU_BURST, "q_u_prior": Q_U,
        "budget_per_tick": BUDGET_PER_TICK, "total_budget": TOTAL_BUDGET,
        "cost_per_frame": COST, "sigma_per_res": SIGMA, "cadence_ticks": CADENCE,
        "controller": {"z_enter": Z_ENTER, "z_exit": Z_EXIT,
                       "z_exit_obs": Z_EXIT_OBS, "z_ema": Z_EMA,
                       "min_dwell_ticks": MIN_DWELL, "random_flip": RANDOM_FLIP},
        "predictor": "v2 per-component scalar KF [phi,u], quiet-world prior",
        "seeds": seeds,
    }, "arms": {}}

    per_seed = {}
    for arm in ARMS:
        rows = []
        for s in seeds:
            regimes, PH = truths[s]
            e, stats = run_arm(arm, s, PH, regimes, n_ticks)
            W = make_weights(surprise_series(PH))
            rows.append({"seed": s, **score(e, W, regimes), **stats})
        per_seed[arm] = rows
        out["arms"][arm] = {
            "per_seed": rows,
            "mean_sw_mse": float(np.mean([r["sw_mse"] for r in rows])),
            "sd_sw_mse": float(np.std([r["sw_mse"] for r in rows])),
            "mean_mse": float(np.mean([r["mse"] for r in rows])),
            "mean_mse_quiet": float(np.mean([r["mse_quiet"] for r in rows])),
            "mean_mse_burst": float(np.mean(
                [r["mse_burst"] for r in rows if r["mse_burst"] is not None])),
            "mean_spend": float(np.mean([r["spend"] for r in rows])),
            "spend_ratio": float(np.mean([r["spend"] for r in rows]) / TOTAL_BUDGET),
        }

    agg = {a: out["arms"][a]["mean_sw_mse"] for a in ARMS}
    adaptive = agg["adaptive"]
    best_fixed = min(agg[a] for a in FIXED)
    best_fixed_arm = min(FIXED, key=lambda a: agg[a])
    oracle = agg["oracle"]

    win = adaptive < 0.98 * best_fixed
    ceiling = oracle < 0.95 * adaptive
    robust_wins = sum(
        1 for i in range(len(seeds))
        if per_seed["adaptive"][i]["sw_mse"] < min(
            per_seed[a][i]["sw_mse"] for a in FIXED))
    robust = robust_wins >= 4
    parity = all(0.95 <= out["arms"][a]["spend_ratio"] <= 1.05 for a in ARMS)
    kill = any(agg[a] <= 1.02 * adaptive for a in FIXED)

    if kill:
        verdict = "KILL"
    elif win and ceiling and robust and parity:
        verdict = "KEEP"
    else:
        verdict = "INCONCLUSIVE"

    out["gate"] = {
        "frozen_in": "proposals/runs/t5-plan.md (§4, unchanged through v2)",
        "means_sw_mse": agg,
        "adaptive_mean": adaptive,
        "best_fixed_arm": best_fixed_arm,
        "best_fixed_mean": best_fixed,
        "adaptive_vs_best_fixed_ratio": adaptive / best_fixed,
        "oracle_mean": oracle,
        "oracle_vs_adaptive_ratio": oracle / adaptive,
        "robust_wins_out_of": f"{robust_wins}/5",
        "checks": {"WIN(adaptive<0.98xbest_fixed)": win,
                   "CEILING(oracle<0.95xadaptive)": ceiling,
                   "ROBUST(>=4/5 seeds)": robust,
                   "PARITY(0.95-1.05 spend)": parity},
        "KILL_condition(any fixed<=1.02xadaptive)": kill,
        "verdict": verdict,
    }
    return out


def main():
    t0 = time.time()
    resdir = Path(__file__).resolve().parent.parent / "results"
    resdir.mkdir(exist_ok=True)

    # smoke gate (seed 999, 30 s) — crash/finite/switch check only, NOT tuned on
    smoke = fire([SMOKE_SEED], SMOKE_TICKS, label="smoke")
    sa = smoke["arms"]
    finite = all(np.isfinite(a["mean_sw_mse"]) for a in sa.values())
    ada = sa["adaptive"]["per_seed"][0]
    switched = ada.get("switches", 0) >= 1 and ada.get("frac_predict", 0) < 0.9
    smoke_ok = finite and switched
    print(f"[smoke seed {SMOKE_SEED}] finite={finite} "
          f"adaptive switches={ada.get('switches')} "
          f"frac_predict={ada.get('frac_predict'):.2f} ok={smoke_ok}")
    if not smoke_ok:
        print("SMOKE GATE FAILED — official fire withheld")
        return

    out = fire(SEEDS, TICKS, label="official")
    out["smoke"] = {"seed": SMOKE_SEED, "passed": smoke_ok}
    out["wall_seconds"] = round(time.time() - t0, 1)

    path = resdir / "t5_dial_controller.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}")

    g = out["gate"]
    print("\n=== T5 DIAL CONTROLLER — official fire (v2) ===")
    for a in ARMS:
        arm = out["arms"][a]
        r0 = arm["per_seed"][0]
        extra = ""
        if "frac_predict" in r0:
            extra = (f" | in-predict {r0['frac_predict']:.2f}"
                     f" switches {r0['switches']}"
                     f" prec/rec {r0['burst_precision']:.2f}/"
                     f"{r0['burst_recall']:.2f}")
        print(f"{a:>12}: SW-MSE {arm['mean_sw_mse']:.6g} "
              f"(quiet {arm['mean_mse_quiet']:.4g} / burst "
              f"{arm['mean_mse_burst']:.4g}) spend {arm['spend_ratio']:.3f}x"
              f"{extra}")
    if "onset_latency_s" in out["arms"]["adaptive"]["per_seed"][0]:
        r0 = out["arms"]["adaptive"]["per_seed"][0]
        print(f"adaptive: onset->predict median {r0['onset_latency_s']}s, "
              f"missed bursts {r0['missed_bursts']}/{r0['n_bursts']}")
    print(f"\nadaptive/best-fixed = {g['adaptive_vs_best_fixed_ratio']:.4f} "
          f"({g['best_fixed_arm']}) | oracle/adaptive = "
          f"{g['oracle_vs_adaptive_ratio']:.4f} | robust {g['robust_wins_out_of']}")
    print(f"checks: {g['checks']}")
    print(f"VERDICT: {g['verdict']}  ({out['wall_seconds']}s)")


if __name__ == "__main__":
    main()
