#!/usr/bin/env python3
"""t5b — the trackability horizon sweep (the boundary map of the 5th dimension).

t5 KILLed the dial controller because the burst regime was white-jerk motion
(OU tau=0.08 s — nothing to extrapolate). t5b maps the boundary: regenerate the
SAME t5-v2 sim with burst OU tau in {0.08, 0.2, 0.5, 1.0, 2.0, 4.0} s (sigma
frozen at 1.4; quiet OU untouched) and run the six-arm tournament per tau under
the SAME frozen gate family (proposals/runs/t5b-plan.md section 4, frozen before
this code existed). THE answer: the smallest tau where adaptive first beats
all-confirm — the trackability horizon.

Honesty:
- The controller never sees tau. All thresholds/priors/cadences are t5-frozen.
- This file NEVER modifies t5's files; it imports the module and sets the
  burst-tau knob on the imported module object at runtime only.
- The per-tick arm loop below is a verbatim copy of t5's run_arm plus the one
  frozen 'uniform' arm (round-robin over [confirm, mid, predict], cursor
  advances only on a successful ledger spend, arm-RNG offset 77, never drawn).
  A bitwise regression check vs t5.run_arm (tau=0.08, seed 41, five shared
  arms) runs BEFORE the official fire; failure = VOID.
- Paired truth across tau: identical RNG draw order per seed, so each seed has
  the same burst schedule and standard-normal stream at every tau.

CPU only (GPU owned by K2). System python3 + numpy.
"""
import json
import math
import time
from pathlib import Path

import numpy as np

import t5_dial_controller as t5
from t5_dial_controller import (
    DT, TICKS, K, AMPS, WTS, OU_QUIET, QUIET_LEN, BURST_LEN,
    BUDGET_PER_TICK, TOTAL_BUDGET, COST, SIGMA, CADENCE, MODE_RES,
    LEDGER_CAP, LEDGER_INIT, Z_ENTER, Z_EXIT, Z_EXIT_OBS, Z_EMA,
    MIN_DWELL, RANDOM_FLIP, Q_U, SEEDS, SMOKE_SEED, SMOKE_TICKS,
    MODE_IDX, surprise_series, make_weights, score, simulate_truth,
    pixel_mse_vec,
)

# ---------------------------------------------------------------- sweep config ----
# FROZEN by proposals/runs/t5b-plan.md (written before this code existed).
TAUS = [0.08, 0.2, 0.5, 1.0, 2.0, 4.0]          # ascending; the one free knob
SIGMA_BURST = t5.OU_BURST[1]                    # 1.4 rad/s, frozen from t5
ARMS = ["all-confirm", "all-predict", "uniform", "random", "oracle", "adaptive"]
FIXED = ["all-confirm", "all-predict", "uniform", "random"]
ARM_SEED_OFFSET = dict(t5.ARM_SEED_OFFSET)      # 11/22/33/44/55/66 verbatim...
ARM_SEED_OFFSET["uniform"] = 77                 # ...+77 for the new arm (never drawn)
RR = ["confirm", "mid", "predict"]              # uniform round-robin dial positions

BASELINE = "ab8ec08"


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
    """Verbatim copy of t5_dial_controller.run_arm plus the frozen 'uniform'
    branch (cursor advance on successful acquisition). Regression-gated."""
    rng = np.random.default_rng((seed * 1000 + ARM_SEED_OFFSET[arm]) % 2 ** 32)
    e = np.zeros(n_ticks)
    modes = np.full(n_ticks, -1, dtype=np.int8)
    ledger = Ledger() if arm in ("random", "oracle", "adaptive", "uniform") else None

    z_ema, z_below_run = 1.0, 0
    current_mode = "confirm"
    mode_since = 0
    enter_predict_at = []
    rr_pos = 0

    is_fixed = arm in ("all-confirm", "all-predict")
    filt = t5.ArmFilter()

    for tk in range(n_ticks):
        if ledger is not None:
            ledger.income()

        # ---- allocation decision (the only thing that differs between arms)
        action = None
        if is_fixed:
            if tk % CADENCE[MODE_RES[ARM_MODE[arm]]] == 0:
                action = ARM_MODE[arm]
        elif arm == "uniform":
            action = RR[rr_pos]           # retry same position until affordable
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

        if arm == "uniform" and observed:
            rr_pos = (rr_pos + 1) % len(RR)   # advance ONLY on successful spend

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
    else:
        spend = ledger.spent

    stats = {"spend": spend}
    if arm in ("uniform", "random", "oracle", "adaptive"):
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


ARM_MODE = {"all-confirm": "confirm", "all-predict": "predict"}
TICKS_PER_SEC = t5.TICKS_PER_SEC


# ------------------------------------------------------------------ fire ----
def fire_tau(tau, seeds, n_ticks=TICKS, label="official"):
    t5.OU_BURST = (tau, SIGMA_BURST)   # the ONE knob, on the imported module only
    truths = {s: simulate_truth(s, n_ticks) for s in seeds}
    out = {"label": label, "tau_burst_s": tau, "ou_burst": [tau, SIGMA_BURST],
           "config": {
               "dt": DT, "duration_s": t5.DURATION, "K": K, "amps": AMPS.tolist(),
               "ou_quiet": OU_QUIET, "q_u_prior": Q_U,
               "budget_per_tick": BUDGET_PER_TICK, "total_budget": TOTAL_BUDGET,
               "cost_per_frame": COST, "sigma_per_res": SIGMA,
               "cadence_ticks": CADENCE,
               "controller": {"z_enter": Z_ENTER, "z_exit": Z_EXIT,
                              "z_exit_obs": Z_EXIT_OBS, "z_ema": Z_EMA,
                              "min_dwell_ticks": MIN_DWELL,
                              "random_flip": RANDOM_FLIP},
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
        "frozen_in": "proposals/runs/t5b-plan.md (§4; t5 §4 gate family per tau)",
        "means_sw_mse": agg,
        "adaptive_mean": adaptive,
        "best_fixed_arm": best_fixed_arm,
        "best_fixed_mean": best_fixed,
        "adaptive_vs_best_fixed_ratio": adaptive / best_fixed,
        "adaptive_vs_allconfirm_ratio": adaptive / agg["all-confirm"],
        "oracle_mean": oracle,
        "oracle_vs_adaptive_ratio": oracle / adaptive,
        "robust_wins_out_of": f"{robust_wins}/5",
        "checks": {"WIN(adaptive<0.98xbest_fixed)": win,
                   "CEILING(oracle<0.95xadaptive)": ceiling,
                   "ROBUST(>=4/5 seeds)": robust,
                   "PARITY(0.95-1.05 spend)": parity},
        "KILL_condition(any fixed<=1.02xadaptive)": kill,
        "verdict": verdict,
        "pays(WIN)": win,
    }
    return out


def regression_gate():
    """Bitwise faithfulness check vs t5.run_arm at tau=0.08, seed 41."""
    t5.OU_BURST = (TAUS[0], SIGMA_BURST)
    regimes, PH = simulate_truth(SEEDS[0])
    checks = {}
    ok = True
    for arm in ["all-confirm", "all-predict", "random", "oracle", "adaptive"]:
        e_mine, st_mine = run_arm(arm, SEEDS[0], PH, regimes)
        e_t5, st_t5 = t5.run_arm(arm, SEEDS[0], PH, regimes)
        same = bool(np.array_equal(e_mine, e_t5)) and st_mine == st_t5
        checks[arm] = same
        ok = ok and same
    return ok, checks


def horizon_analysis(per_tau):
    """Frozen §4 definitions: first tau with adaptive < all-confirm (horizon),
    first tau with WIN (pays), sub-grid log-tau linear crossing estimate."""
    ratios = [(tau, per_tau[str(tau)]["gate"]["adaptive_vs_allconfirm_ratio"])
              for tau in TAUS]
    horizon = next((t for t, r in ratios if r < 1.0), None)
    pays = next((t for t in TAUS if per_tau[str(t)]["gate"]["pays(WIN)"]), None)
    crossing = None
    for (t0, r0), (t1, r1) in zip(ratios, ratios[1:]):
        if r0 >= 1.0 > r1:
            lt0, lt1 = math.log(t0), math.log(t1)
            crossing = math.exp(lt0 + (1.0 - r0) / (r1 - r0) * (lt1 - lt0))
            break
    return {"horizon_tau_first_beats_allconfirm": horizon,
            "pays_tau_first_WIN": pays,
            "subgrid_crossing_tau_est": crossing,
            "adaptive_vs_allconfirm_ratio_by_tau": {str(t): r for t, r in ratios}}


def main():
    t0 = time.time()
    resdir = Path(__file__).resolve().parent.parent / "results"
    resdir.mkdir(exist_ok=True)

    # ---- gate 1: regression faithfulness vs t5 (VOID on failure)
    reg_ok, reg_checks = regression_gate()
    print(f"[regression vs t5.run_arm, tau=0.08 seed {SEEDS[0]}] "
          f"{reg_checks} ok={reg_ok}")
    if not reg_ok:
        print("REGRESSION GATE FAILED — VOID, no fire")
        return

    # ---- gate 2: smoke per tau (seed 999, 30 s)
    smoke = {}
    smoke_ok_all = True
    for tau in TAUS:
        sm = fire_tau(tau, [SMOKE_SEED], SMOKE_TICKS, label="smoke")
        sa = sm["arms"]
        finite = all(np.isfinite(a["mean_sw_mse"]) for a in sa.values())
        ada = sa["adaptive"]["per_seed"][0]
        switched = ada.get("switches", 0) >= 1 and ada.get("frac_predict", 0) < 0.9
        smoke[str(tau)] = {"finite": finite, "adaptive_switches": ada.get("switches"),
                           "frac_predict": ada.get("frac_predict"),
                           "passed": bool(finite and switched)}
        smoke_ok_all = smoke_ok_all and (finite and switched)
        print(f"[smoke tau={tau}] finite={finite} switches={ada.get('switches')} "
              f"frac_predict={ada.get('frac_predict'):.2f} "
              f"passed={smoke[str(tau)]['passed']}")
    if not smoke_ok_all:
        print("SMOKE GATE FAILED on >=1 tau — official fire withheld")
        return

    # ---- official fire
    per_tau = {}
    for tau in TAUS:
        per_tau[str(tau)] = fire_tau(tau, SEEDS, TICKS, label="official")
        g = per_tau[str(tau)]["gate"]
        print(f"[official tau={tau}] all-confirm {g['means_sw_mse']['all-confirm']:.6g} "
              f"| adaptive {g['adaptive_mean']:.6g} "
              f"(ratio vs confirm {g['adaptive_vs_allconfirm_ratio']:.3f}) "
              f"| best-fixed {g['best_fixed_arm']} {g['best_fixed_mean']:.6g} "
              f"| oracle {g['oracle_mean']:.6g} | {g['verdict']} "
              f"| pays={g['pays(WIN)']}")

    hz = horizon_analysis(per_tau)
    out = {
        "experiment": "t5b_tau_sweep",
        "date": time.strftime("%Y-%m-%d %H:%M %Z", time.localtime()),
        "baseline_revision": BASELINE,
        "plan": "proposals/runs/t5b-plan.md",
        "question": "smallest burst OU tau where the surprise-driven dial "
                    "controller first beats all-confirm (trackability horizon)",
        "grid": {"taus": TAUS, "sigma_burst": SIGMA_BURST,
                 "ou_quiet_frozen": OU_QUIET,
                 "note": "only OU_BURST[0] varies; everything else t5-v2 frozen; "
                         "controller never sees tau; paired truth per seed"},
        "config_snapshot": per_tau[str(TAUS[0])]["config"],
        "smoke": {"seed": SMOKE_SEED, "ticks_s": SMOKE_TICKS / t5.TICKS_PER_SEC,
                  "per_tau": smoke, "all_passed": smoke_ok_all},
        "regression_check": {"tau": TAUS[0], "seed": SEEDS[0],
                             "arms": reg_checks, "passed": reg_ok},
        "per_tau": per_tau,
        "horizon": hz,
        "wall_seconds": round(time.time() - t0, 1),
    }

    path = resdir / "t5b_tau_sweep.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}")

    print("\n=== T5B — TRACKABILITY HORIZON SWEEP ===")
    print(f"{'tau_s':>6} | {'all-conf':>9} {'all-pred':>9} {'uniform':>9} "
          f"{'random':>9} {'oracle':>9} {'adaptive':>9} | {'ada/conf':>8} verdict")
    for tau in TAUS:
        g = per_tau[str(tau)]["gate"]
        m = g["means_sw_mse"]
        print(f"{tau:>6} | {m['all-confirm']:>9.5f} {m['all-predict']:>9.5f} "
              f"{m['uniform']:>9.5f} {m['random']:>9.5f} {m['oracle']:>9.5f} "
              f"{m['adaptive']:>9.5f} | {g['adaptive_vs_allconfirm_ratio']:>8.3f} "
              f"{g['verdict']}{' PAYS' if g['pays(WIN)'] else ''}")
    print(f"\nhorizon (adaptive first beats all-confirm): {hz['horizon_tau_first_beats_allconfirm']} s")
    print(f"pays (adaptive first beats ALL fixed):      {hz['pays_tau_first_WIN']} s")
    print(f"sub-grid crossing estimate: {hz['subgrid_crossing_tau_est']} s")
    print(f"({out['wall_seconds']}s)")


if __name__ == "__main__":
    main()
