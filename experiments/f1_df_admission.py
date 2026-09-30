#!/usr/bin/env python3
"""F1 — dF-admission scheduling falsifier (frozen pre-reg: proposals/runs/F1-df-admission.md).

Tests the ternary-* cluster's mined claim: ordering by -dF = u - T*churn beats priority-FIFO on
queue variance and depth blowups at ~equal mean wait; slack-extreme (T max always) is >=15% slower.
Paired streams: same arrivals/utilities/depths/requeue draws across all arms per seed.
"""
import argparse
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "f1_df_admission"

TICKS = 30000
P_ARR = 0.8
DEPTHS = np.array([1, 2, 3, 4, 5, 6])
DP = np.array([0.40, 0.25, 0.15, 0.10, 0.06, 0.04])
P_REQUEUE_PER_DEPTH = 0.05
MEAN_D, STD_D = 2.29, 1.43           # frozen population stats for z-scoring depth
BAND_LO, BAND_HI = 2, 6              # budget trit band on queue length
T_MAP = {-1: 0.0, 0: 1.0, 1: 2.0}
MAX_PASSES = 24
SEEDS = [91, 92, 93]
ARMS = ["pfifo", "df", "slack"]


def budget_T(queue_len):
    status = -1 if queue_len > BAND_HI else (1 if queue_len < BAND_LO else 0)
    return T_MAP[status]


def simulate(arm, seed, ticks):
    rng = np.random.default_rng(seed)
    arrivals = rng.random(ticks) < P_ARR
    n_jobs = int(arrivals.sum())
    u = rng.exponential(1.0, size=n_jobs)
    d = rng.choice(DEPTHS, size=n_jobs, p=DP)
    requeue_draws = rng.random((n_jobs, MAX_PASSES)) < P_REQUEUE_PER_DEPTH * d[:, None]

    queue = []          # job indices waiting
    current = None      # (j, progress)
    first_start = np.full(n_jobs, -1, dtype=int)
    completion = np.full(n_jobs, -1, dtype=int)
    passes = np.zeros(n_jobs, dtype=int)
    q_trace = np.empty(ticks, dtype=np.int32)
    jid = 0
    last_completion = -1

    for tick in range(ticks):
        if arrivals[tick]:
            queue.append(jid)
            jid += 1
        if current is None and queue:
            Q = len(queue)
            if arm == "pfifo":
                pick = max(queue, key=lambda j: (u[j], -j))
            else:
                T = 2.0 if arm == "slack" else budget_T(Q)
                key = lambda j: u[j] - T * (d[j] - MEAN_D) / STD_D
                pick = max(queue, key=lambda j: (key(j), -j))
            queue.remove(pick)
            if first_start[pick] < 0:
                first_start[pick] = tick
            current = [pick, 0.0]
        if current is not None:
            j = current[0]
            current[1] += 1.0
            if current[1] >= 1.0 + 0.1 * d[j]:
                done = not (passes[j] < MAX_PASSES and requeue_draws[j, passes[j]])
                passes[j] += 1
                if done:
                    completion[j] = tick + 1
                    last_completion = tick + 1
                    current = None
                else:
                    queue.append(j)   # nesting pressure: back of queue
                    current = None
        q_trace[tick] = len(queue)

    done = completion >= 0
    arr_ticks = np.nonzero(arrivals)[0]
    started = first_start >= 0
    # Censored waits: never-started jobs count wait = ticks - arrival (conservative lower bound;
    # same streams across arms, so the comparison stays paired and no survivorship bias).
    wait = (np.where(started, first_start, ticks) - arr_ticks).astype(float)
    dd = d
    w_deep = float(wait[dd >= 4].mean()) if (dd >= 4).any() else float("nan")
    w_shallow = float(wait[dd <= 2].mean()) if (dd <= 2).any() else float("nan")
    return {
        "mean_wait": float(wait.mean()),
        "q_var": float(q_trace.var()),
        "w_deep": w_deep, "w_shallow": w_shallow,
        "r_blowup": w_deep / w_shallow,
        "last_completion": int(last_completion),
        "n_done": int(done.sum()), "n_jobs": n_jobs,
        "frac_started": float(started.mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    ticks, seeds = (3000, [91]) if args.smoke else (TICKS, SEEDS)
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"ticks": ticks, "seeds": seeds, "arms": {}}
    for arm in ARMS:
        res["arms"][arm] = [simulate(arm, s, ticks) for s in seeds]
    agg = {}
    for arm in ARMS:
        agg[arm] = {k: float(np.mean([r[k] for r in res["arms"][arm]]))
                    for k in ["mean_wait", "q_var", "r_blowup", "last_completion", "frac_started"]}
    res["aggregate"] = agg
    if not args.smoke:
        g1 = abs(agg["df"]["mean_wait"] - agg["pfifo"]["mean_wait"]) / agg["pfifo"]["mean_wait"] <= 0.05
        g2 = agg["df"]["q_var"] <= 0.6 * agg["pfifo"]["q_var"]
        premise = agg["pfifo"]["r_blowup"] >= 3.0
        g3 = premise and agg["df"]["r_blowup"] < 3.0
        g4 = agg["slack"]["mean_wait"] >= 1.15 * agg["df"]["mean_wait"]
        verdict = ("PREMISE-ABSENT" if not premise else
                   ("KEEP" if (g1 and g2 and g3 and g4) else "KILL"))
        res["gates"] = {"G1_within5pct": g1, "G2_var_minus40": g2,
                        "G3_premise_and_eliminated": g3, "premise_r_pfifo": premise,
                        "G4_slack_15pct_slower": g4, "verdict": verdict}
    path = OUT / ("smoke_results.json" if args.smoke else "results.json")
    path.write_text(json.dumps(res, indent=2))
    print(json.dumps(res.get("gates", agg), indent=2)[:700])
    print("WROTE", path)


if __name__ == "__main__":
    main()
