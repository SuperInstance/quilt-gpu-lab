#!/usr/bin/env python3
"""ie3_dedicated_trunks — crew doctrine in silicon: specialists need dedicated trunks.

Standalone numpy demonstration-of-mechanism for the IE3 finding
(RESULTS.md IE3, 2026-09-29: DILUTION_CONFIRMS — A-joint and B-sequential
shared-trunk arms dilute; C-split-trunks specialists hit r2_blob 0.987 /
r2_direction 0.984 at density 32), with the federation texture the doctrine
fed downstream: COMP0 (2026-10-01, INCONCLUSIVE by the std==0 law but
FED 0.8182 > SINGLE 0.7778 / JOINT 0.803 at matched params, dilution
localized to the contested regime) and COMP1 (2026-10-01, the doctrine's
booked win: FED > SINGLE ONLY on negation-scope, +0.126, CI excludes 0,
where BOTH monolith arms sit BELOW regime chance — a dedicated cell fixes
a structural blindness a shared trunk cannot see).

Two-task synthetic regression. Every input carries BOTH signal families
("mixed in the input"); the two families live in orthogonal subspaces of
the input space (the toy skeleton of IE1's grating-codes-vs-blob-codes
split). Three arm layouts on identical data:

  A_joint       one SHARED trunk (rank-m bottleneck) + two linear heads,
                both tasks fit jointly (reduced-rank regression, closed form)
  B_sequential  same single trunk: task 1 to a competence plateau, then an
                anchored fine-tune on task 2 only -> task-1 forgetting is
                measurable on the same held-out streams
  C_split       two small DEDICATED trunks, one per task, each the same width
                as A's one trunk (crew budget: two cells, not two heads)

Mechanism: the shared trunk is a hard rank-m bottleneck. Two orthogonal
rank-k tasks need 2k total trunk rank; one width-k trunk splits it (~k/2
each -> dilution on both tasks). Two dedicated width-k trunks each cover
their task's k -> no dilution. IE3's gradient-trained trunk (4->12->8 tanh,
600 epochs, Adam) showed the same ordering under real training; this block
makes the capacity competition legible in closed form. The contract
exported to composers is the ARM LAYOUT (how to wire shared vs dedicated
capacity), not this dataset.

House contracts: seed 2718 default; >=5 seeds with mean +- std, degenerate
std==0 -> INCONCLUSIVE; fail loud; final stdout line is exactly one JSON
object with exactly one top-level "verdict" (PASS/KILL/INCONCLUSIVE); exit
0 iff verdict == "PASS". CPU-only, seconds.
"""
from __future__ import annotations

import json
import time

import numpy as np

# ---- frozen config (toy harness, seed law: seed 2718) ----
SEED = 2718
SEEDS = (2718, 2719, 2720, 2721, 2722)   # >=5 seeds; house law needs spread
N_SEEDS_MIN = 5
DENSITIES = (8, 16, 32)                   # input-dim grid echo of IE3 8/16/32
DENSITY_OF_RECORD = 32                    # IE3's density of record
SUBSPACE_K = 4                            # per-task signal subspace dim (rank)
N_OUT = 4                                 # outputs per task (multi-dim target)
TRUNK_WIDTH = 4                           # one trunk = one task's worth of rank
SIGMA = 0.15                              # label noise; ceiling r2 = 0.9779
N_TRAIN = 512
N_TEST = 4096
RIDGE_ALPHA = 1e-3
ANCHOR_LAM = float(N_TRAIN)             # fine-tune anchor = data-term strength
ORDER_MARGIN = 0.02                       # required gap for the C>A, C>B order

TASKS = ("blob", "direction")             # task-1 / task-2 family names (IE3)


# ---------------- data: two orthogonal signal families mixed in one input ----
def _orthonormal_rows(rng, d, k, complement_of=None):
    """k orthonormal d-dim rows; optionally inside the complement of an
    existing orthonormal row set (keeps the two task subspaces orthogonal)."""
    if complement_of is None:
        a = rng.standard_normal((k, d))
        q, _ = np.linalg.qr(a.T)
        return q.T[:k]
    comp_dim = d - complement_of.shape[0]
    assert k <= comp_dim, "subspaces would overlap"
    a = rng.standard_normal((comp_dim, d))
    q, _ = np.linalg.qr(a.T)
    basis = q.T[comp_dim - k:]
    return basis


def make_dataset(seed, d):
    """One draw: train/test streams shared verbatim across all three arms."""
    rng = np.random.default_rng(seed)
    # task maps: y = x @ W_true + noise, W_true = P.T @ G, rank k per task,
    # row spaces P1 / P2 orthogonal -> families are mixed in x but separable.
    data = {"d": d, "k": SUBSPACE_K}
    for task in TASKS:
        if "P1" not in data:
            p1 = _orthonormal_rows(rng, d, SUBSPACE_K)
            data["P1"] = p1
            p2 = None
        p = data["P1"] if task == "blob" else _orthonormal_rows(
            rng, d, SUBSPACE_K, complement_of=data["P1"])
        g, _ = np.linalg.qr(rng.standard_normal((SUBSPACE_K, N_OUT)))
        data[f"W_{task}"] = p.T @ g
    x_tr = rng.standard_normal((N_TRAIN, d))
    x_te = rng.standard_normal((N_TEST, d))
    data["x_tr"], data["x_te"] = x_tr, x_te
    for task in TASKS:
        w = data[f"W_{task}"]
        data[f"y_{task}_tr"] = x_tr @ w + SIGMA * rng.standard_normal((N_TRAIN, N_OUT))
        data[f"y_{task}_te"] = x_te @ w  # clean targets: measure the reader, not the draw
    return data


# ---------------- closed-form ridge + reduced-rank trunk --------------------
def ridge_fit(x, y, alpha=RIDGE_ALPHA):
    d = x.shape[1]
    return np.linalg.solve(x.T @ x + alpha * np.eye(d), x.T @ y)


def reduce_rank(w, m):
    """Trunk/head factorization: keep top-m singular directions (width-m trunk)."""
    u, s, vt = np.linalg.svd(w, full_matrices=False)
    return (u[:, :m] * s[:m]) @ vt[:m, :]


def r2_score(y_true, y_pred):
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean(axis=0)) ** 2).sum())
    assert np.isfinite(ss_res) and np.isfinite(ss_tot) and ss_tot > 0, "bad r2 inputs"
    return 1.0 - ss_res / ss_tot


# ---------------- the three arms (identical data objects in, r2 per task out)
def arm_A_joint(data):
    """Shared width-m trunk, two heads, both tasks fit jointly."""
    y = np.concatenate([data["y_blob_tr"], data["y_direction_tr"]], axis=1)
    w_hat = reduce_rank(ridge_fit(data["x_tr"], y), TRUNK_WIDTH)
    out = {}
    for i, t in enumerate(TASKS):  # per-task head = its column block
        out[t] = r2_score(data[f"y_{t}_te"],
                          data["x_te"] @ w_hat[:, i * N_OUT:(i + 1) * N_OUT])
    return out


def arm_B_sequential(data):
    """One trunk: task 1 to plateau, then anchored fine-tune on task 2 only.
    The moved trunk is one map; scoring it on task 1 IS the forgetting read."""
    w1 = reduce_rank(ridge_fit(data["x_tr"], data["y_blob_tr"]), TRUNK_WIDTH)
    switch_blob = r2_score(data["y_blob_te"], data["x_te"] @ w1)  # competence at switch
    xtx = data["x_tr"].T @ data["x_tr"] + RIDGE_ALPHA * np.eye(data["d"])
    rhs = data["x_tr"].T @ data["y_direction_tr"] + ANCHOR_LAM * w1
    w2 = reduce_rank(np.linalg.solve(xtx, rhs), TRUNK_WIDTH)
    return {"blob": r2_score(data["y_blob_te"], data["x_te"] @ w2),
            "direction": r2_score(data["y_direction_te"], data["x_te"] @ w2),
            "switch_blob_r2": switch_blob}


def arm_C_split(data):
    """Two dedicated width-m trunks, one per task (crew baseline)."""
    out = {}
    for t in TASKS:
        w = reduce_rank(ridge_fit(data["x_tr"], data[f"y_{t}_tr"]), TRUNK_WIDTH)
        out[t] = r2_score(data[f"y_{t}_te"], data["x_te"] @ w)
    return out


ARMS = {"A_joint": arm_A_joint, "B_sequential": arm_B_sequential,
        "C_split": arm_C_split}


def run_grid(seed):
    """One seed, the 8/16/32 density grid. Returns {density: {arm: {task: r2}}}."""
    grid = {}
    for d in DENSITIES:
        data = make_dataset(seed, d)
        grid[d] = {name: fn(data) for name, fn in ARMS.items()}
    return grid


# ---------------- main: receipt, house-law gates, single-JSON verdict -------
def main():
    t0 = time.time()
    print("[ie3_dedicated_trunks] IE3 doctrine toy: 3 arms x densities "
          f"{DENSITIES}, seeds {SEEDS}", flush=True)
    print(f"[ie3_dedicated_trunks] rank-k={SUBSPACE_K} tasks, shared trunk width "
          f"m={TRUNK_WIDTH}, sigma={SIGMA}, n_train={N_TRAIN} (seed {SEED})",
          flush=True)

    per_seed = {s: run_grid(s) for s in SEEDS}

    # per-arm per-task mean +- std across seeds at the density of record
    drec = DENSITY_OF_RECORD
    stats = {}
    for arm in ARMS:
        stats[arm] = {}
        for t in TASKS:
            vals = np.array([per_seed[s][drec][arm][t] for s in SEEDS])
            assert np.all(np.isfinite(vals)), f"non-finite r2 {arm}/{t}"
            stats[arm][t] = {"mean": float(vals.mean()), "std": float(vals.std()),
                             "per_seed": [round(float(v), 6) for v in vals]}

    # ---- ordering gates at density 32 (the block's contract) ----
    ordering = {}
    ordering_holds_tasks = []
    for t in TASKS:
        c_over_a = stats["C_split"][t]["mean"] - stats["A_joint"][t]["mean"]
        c_over_b = stats["C_split"][t]["mean"] - stats["B_sequential"][t]["mean"]
        ordering[t] = {"C_minus_A": round(c_over_a, 6),
                       "C_minus_B": round(c_over_b, 6),
                       "holds": bool(c_over_a > ORDER_MARGIN and c_over_b > ORDER_MARGIN)}
        ordering_holds_tasks.append(ordering[t]["holds"])
    # receipt narrative: B's forgetting on task 1
    forgetting = round(stats["C_split"]["blob"]["mean"]
                       - stats["B_sequential"]["blob"]["mean"], 6)

    # ---- default-seed receipt table (density grid at seed 2718) ----
    receipt = {str(d): {arm: {t: round(per_seed[SEED][d][arm][t], 6)
                              for t in TASKS} for arm in ARMS} for d in DENSITIES}
    print(f"[ie3_dedicated_trunks] seed {SEED} receipt r2 by density/arm:", flush=True)
    for d in DENSITIES:
        for arm in ARMS:
            row = receipt[str(d)][arm]
            print(f"[ie3_dedicated_trunks]   d={d:>2} {arm:<12} "
                  f"r2_blob={row['blob']:.4f} r2_direction={row['direction']:.4f}",
                  flush=True)
    b_switch = round(per_seed[SEED][drec]["B_sequential"]["switch_blob_r2"], 6)
    print(f"[ie3_dedicated_trunks] B phase-1 switch competence (seed {SEED}, d={drec}): "
          f"r2_blob={b_switch:.4f}; forgetting -> "
          f"{round(b_switch - per_seed[SEED][drec]['B_sequential']['blob'], 6)}",
          flush=True)

    # ---- house law: >=5 seeds, degenerate std==0 -> INCONCLUSIVE ----
    reasons = []
    if len(SEEDS) < N_SEEDS_MIN:
        reasons.append(f"only {len(SEEDS)} seeds (< {N_SEEDS_MIN})")
    for arm in ARMS:
        for t in TASKS:
            if stats[arm][t]["std"] == 0.0:
                reasons.append(f"degenerate std==0 on {arm}/{t} across {len(SEEDS)} seeds")

    ordering_holds = any(ordering_holds_tasks)
    checks = {
        "C_beats_A_and_B_at_density_32": {
            "holds_on_at_least_one_task": ordering_holds,
            "per_task": ordering,
            "required_margin": ORDER_MARGIN},
        "per_arm_per_task_r2_mean_std": stats,
    }

    if reasons:
        verdict = "INCONCLUSIVE"
    elif not ordering_holds:
        verdict = "KILL"
    else:
        verdict = "PASS"

    result = {
        "verdict": verdict,
        "block": "ie3_dedicated_trunks",
        "seed": SEED,
        "seeds": list(SEEDS),
        "density_of_record": DENSITY_OF_RECORD,
        "config": {"subspace_k": SUBSPACE_K, "n_out": N_OUT,
                   "trunk_width": TRUNK_WIDTH, "sigma": SIGMA,
                   "n_train": N_TRAIN, "n_test": N_TEST,
                   "ridge_alpha": RIDGE_ALPHA, "anchor_lam": ANCHOR_LAM},
        "receipt_seed_2718": receipt,
        "density32_mean_std_across_seeds": stats,
        "B_switch_blob_r2_seed2718": b_switch,
        "B_task1_forgetting_mean_vs_C": forgetting,
        "checks": checks,
        "provenance": "RESULTS.md IE3 (2026-09-29) DILUTION_CONFIRMS: "
                      "C-split-trunks r2_blob 0.987 / r2_direction 0.984 @ density 32; "
                      "COMP0 (2026-10-01) FED>SINGLE +0.0404 / FED>JOINT +0.0152 "
                      "(INCONCLUSIVE by std==0 law); COMP1 (2026-10-01) FED>SINGLE "
                      "+0.126 on negation-scope only, CI excludes 0",
        "seconds": round(time.time() - t0, 2),
    }
    print(json.dumps(result), flush=True)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
