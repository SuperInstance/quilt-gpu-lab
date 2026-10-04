#!/usr/bin/env python3
"""pidfire_common.py — shared substrate for PIDFIRE-1 (pre-reg proposals/runs/PIDFIRE-1-servo-soc.md).

Ports, verbatim in RULES, the pinned upstream semantics:
  - ternary-fire  @ ab69abde05fb804b5581f1df8154210450877f40 (src/lib.rs sha256 1a0c4dc1...)
  - ternary-pid   @ 6fbaf738f01296d1c4f69728cafac305864e2268 (src/lib.rs sha256 9a13e326...)
  - ternary-irradiate @ 1010fd20d901ea68d083f1391deead743bf57102 (composition mapping:
    primary-knock point ignition + shadow/obstacle cells that anneal back)

Declared deviations (pre-reg "Frozen protocol"): numpy PCG64 vector draws replace per-cell
xorshift64 (transition rules identical); per-tree catch probability 1-(1-p)^k is
distribution-equal to the crate's sequential per-edge trials (break on success).

Memory law: O(grid) — grids are fixed-size bool arrays; avalanche sizes are the only
accumulated per-run state (<= ~1e3 ints).
"""
from __future__ import annotations

import math

import numpy as np

TREE_DUMMY = 1  # ternary-fire state names (+1 tree, 0 empty, -1 burning) kept for reference

N_GRID = 128          # frozen: 128x128
N_CELLS = N_GRID * N_GRID
T_TOTAL = 60_000      # frozen
T_TRANSIENT = 10_000  # frozen
F_STEP = 1.0 / 150.0  # frozen: quiet-gated lightning admission prob per step (fixed arm)


# ----------------------------------------------------------------------------
# ternary-fire CA step (vectorized port of upstream `step`)
# ----------------------------------------------------------------------------

def make_ic(rng: np.random.Generator, rho: float):
    """Random IC: tree cells w.p. rho, rest empty, none burning (pre-reg)."""
    tree = rng.random((N_GRID, N_GRID)) < rho
    burn = np.zeros((N_GRID, N_GRID), dtype=bool)
    shadow = np.zeros((N_GRID, N_GRID), dtype=np.int32)  # shadow-timer grid (PID arm only)
    return tree, burn, shadow


def burning_neighbors(burn: np.ndarray) -> np.ndarray:
    """Count of burning von Neumann neighbors, non-wrapping (upstream get_neighbors)."""
    k = np.zeros_like(burn, dtype=np.int8)
    k[1:, :] += burn[:-1, :].astype(np.int8)
    k[:-1, :] += burn[1:, :].astype(np.int8)
    k[:, 1:] += burn[:, :-1].astype(np.int8)
    k[:, :-1] += burn[:, 1:].astype(np.int8)
    return k


def step_grid(tree, burn, shadow, p, q, rng, ignite_idx=None):
    """One synchronous step (shape-generic; runs use 128x128), upstream rule order:

    1. forced ignitions applied to next (TREE -> BURN)  [upstream applies ignitions first]
    2. BURN(t) -> EMPTY(t+1)
    3. TREE(t) w/ k burning OLD-grid neighbors catches w.p. 1-(1-p)^k
       (upstream: sequential per-edge trials, break on success)
    4. EMPTY(t) -> TREE(t+1) w.p. q   (SHADOW cells excluded — they are EMPTY-with-immunity)

    Newly ignited cells do NOT spread this step (spread reads old grid only).
    Returns (new_tree, new_burn). Shadow timer decays in place (caller owns semantics).
    """
    h, w = tree.shape
    r_catch = rng.random((h, w))
    r_grow = rng.random((h, w))

    empty = ~tree & ~burn
    k = burning_neighbors(burn)
    catch_prob = 1.0 - (1.0 - p) ** k
    catch = tree & (r_catch < catch_prob)

    grow = empty & (shadow <= 0) & (r_grow < q)

    new_burn = catch.copy()
    if ignite_idx is not None:
        y, x = ignite_idx
        if tree[y, x]:  # upstream: ignition only if cell is a tree
            new_burn[y, x] = True

    new_tree = (tree & ~new_burn) | grow
    return new_tree, new_burn


# ----------------------------------------------------------------------------
# ternary-pid TernaryPid port (field-for-field; Δt = 1 discrete, as upstream)
# ----------------------------------------------------------------------------

class TernaryPid:
    def __init__(self, kp: float, ki: float, kd: float,
                 deadband: float = 0.0, integral_limit: float = 100.0,
                 derivative_filter: float = 0.1):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.deadband = deadband
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter
        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0
        self.initialized = False

    def update(self, setpoint: float, measurement: float) -> int:
        """Upstream update(): deadband short-circuit (integral bleeds x0.95,
        prev_error kept consistent), else discrete PID + sign quantization."""
        error = setpoint - measurement
        if abs(error) < self.deadband:
            self.integral *= 0.95
            self.prev_error = error
            self.initialized = True
            return 0
        out = self._compute_pid(error)
        if out > 0.0:
            return 1
        if out < 0.0:
            return -1
        return 0

    def update_raw(self, setpoint: float, measurement: float) -> float:
        """Upstream update_raw(): continuous signal, NO deadband/bleed (anti-windup
        clamp still applies). Exists for the textbook-parity test pin."""
        return self._compute_pid(setpoint - measurement)

    def _compute_pid(self, error: float) -> float:
        p = self.kp * error
        self.integral += error
        if self.integral > self.integral_limit:
            self.integral = self.integral_limit
        elif self.integral < -self.integral_limit:
            self.integral = -self.integral_limit
        i = self.ki * self.integral
        if self.initialized:
            a = self.derivative_filter
            self.filtered_derivative = a * (error - self.prev_error) + (1.0 - a) * self.filtered_derivative
            deriv = self.filtered_derivative
        else:
            deriv = 0.0
        d = self.kd * deriv
        self.prev_error = error
        self.initialized = True
        return p + i + d


# ----------------------------------------------------------------------------
# run loops (fixed arm / PID arm) — O(grid) memory, sizes streamed to caller
# ----------------------------------------------------------------------------

def run_fixed(p: float, q: float, seed: int, rho: float,
              t_total: int = T_TOTAL, t_transient: int = T_TRANSIENT):
    """Fixed-rule arm: quiet-gated Poisson lightning f_step=1/150, constant q.
    Returns (sizes, mean_burn_frac, mean_density) over the measure window."""
    rng = np.random.default_rng(seed)
    tree, burn, shadow = make_ic(rng, rho)
    sizes = []
    in_fire = False
    cur_size = 0
    fire_start = -1
    burn_sum = 0
    tree_sum = 0
    for t in range(t_total):
        ignite_idx = None
        if not burn.any():
            if rng.random() < F_STEP:
                ys, xs = np.nonzero(tree)
                if len(ys) > 0:
                    j = int(rng.integers(len(ys)))
                    ignite_idx = (int(ys[j]), int(xs[j]))
        tree, burn = step_grid(tree, burn, shadow, p, q, rng, ignite_idx)
        bc = int(burn.sum())
        if bc > 0:
            if not in_fire:
                in_fire = True
                fire_start = t
                cur_size = bc
            else:
                cur_size += bc
        elif in_fire:
            if fire_start >= t_transient:  # fires spanning the boundary excluded (pre-reg)
                sizes.append(cur_size)
            in_fire = False
            cur_size = 0
        if t >= t_transient:
            burn_sum += bc
            tree_sum += int(tree.sum())
    n_meas = t_total - t_transient
    return sizes, burn_sum / n_meas / N_CELLS, tree_sum / n_meas / N_CELLS


def run_pid(p: float, kp: float, ki: float, kd: float, deadband: float,
            ilim: float, alpha: float, g_scale: float, q_cap: float,
            k_shadow: int, sp: float, seed: int, rho: float,
            t_total: int = T_TOTAL, t_transient: int = T_TRANSIENT):
    """PID arm: ternary-pid servo on PV=burn fraction; integrator = fuel schedule
    (q_t = clip(g_scale*integral_after_update, 0, q_cap), windup = fuel growth);
    u=+1 quiet-gated primary-knock ignition; u=-1 shadow/firebreak cast (anneals
    after k_shadow steps). Returns (sizes, mean_burn_frac, mean_density, pv_series_dsum,
    n_ignitions, n_shadows)."""
    rng = np.random.default_rng(seed)
    tree, burn, shadow = make_ic(rng, rho)
    pid = TernaryPid(kp, ki, kd, deadband=deadband, integral_limit=ilim, derivative_filter=alpha)
    sizes = []
    in_fire = False
    cur_size = 0
    fire_start = -1
    burn_sum = 0
    tree_sum = 0
    sq_err = 0.0
    n_ign = 0
    n_sh = 0
    for t in range(t_total):
        pv = int(burn.sum()) / N_CELLS
        u = pid.update(sp, pv)
        q_t = g_scale * pid.integral
        if q_t < 0.0:
            q_t = 0.0
        elif q_t > q_cap:
            q_t = q_cap
        ignite_idx = None
        if u == 1 and not burn.any():
            ys, xs = np.nonzero(tree)
            if len(ys) > 0:
                j = int(rng.integers(len(ys)))
                ignite_idx = (int(ys[j]), int(xs[j]))
                n_ign += 1
        elif u == -1:
            bys, bxs = np.nonzero(burn)
            placed = False
            if len(bys) > 0:
                j = int(rng.integers(len(bys)))
                y, x = int(bys[j]), int(bxs[j])
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < N_GRID and 0 <= nx < N_GRID and not tree[ny, nx] and not burn[ny, nx]:
                        shadow[ny, nx] = k_shadow
                        placed = True
                        break
            if not placed:
                eys, exs = np.nonzero(~tree & ~burn)
                if len(eys) > 0:
                    j = int(rng.integers(len(eys)))
                    shadow[int(eys[j]), int(exs[j])] = k_shadow
                    placed = True
            if placed:
                n_sh += 1
        tree, burn = step_grid(tree, burn, shadow, p, q_t, rng, ignite_idx)
        if shadow.any():
            np.subtract(shadow, 1, out=shadow, where=shadow > 0)
        bc = int(burn.sum())
        if bc > 0:
            if not in_fire:
                in_fire = True
                fire_start = t
                cur_size = bc
            else:
                cur_size += bc
        elif in_fire:
            if fire_start >= t_transient:  # fires spanning the boundary excluded (pre-reg)
                sizes.append(cur_size)
            in_fire = False
            cur_size = 0
        if t >= t_transient:
            burn_sum += bc
            tree_sum += int(tree.sum())
            sq_err += (pv - sp) ** 2
    n_meas = t_total - t_transient
    return (sizes, burn_sum / n_meas / N_CELLS, tree_sum / n_meas / N_CELLS,
            math.sqrt(sq_err / n_meas), n_ign, n_sh)


# ----------------------------------------------------------------------------
# power-law stats (frozen in pre-reg)
# ----------------------------------------------------------------------------

def mle_tau(sizes, s_min: int) -> float:
    """Discrete MLE (Clauset-Shalizi-Newman): tau = 1 + n / sum(ln(s/(s_min-0.5)))."""
    tail = [s for s in sizes if s >= s_min]
    n = len(tail)
    if n < 2:
        return float("nan")
    acc = sum(math.log(s / (s_min - 0.5)) for s in tail)
    if acc <= 0:
        return float("nan")
    return 1.0 + n / acc


def ks_one_sample(sizes, tau: float, s_min: int) -> float:
    """One-sample KS of sizes>=s_min vs fitted discrete power law on integer support
    [s_min, s_max_obs]. D = max_i |F_fit(s_i) - F_emp(s_i)| (declared form, pre-reg)."""
    tail = np.sort(np.asarray([s for s in sizes if s >= s_min], dtype=np.int64))
    n = len(tail)
    if n < 2 or not math.isfinite(tau):
        return float("inf")
    support = np.arange(s_min, int(tail[-1]) + 1, dtype=np.float64)
    w = support ** (-tau)
    cdf = np.cumsum(w) / w.sum()
    idx = (tail - s_min).astype(np.int64)
    f_fit = cdf[idx]
    f_emp = (np.arange(1, n + 1, dtype=np.float64)) / n
    return float(np.max(np.abs(f_fit - f_emp)))


def fit_powerlaw(sizes):
    """s_min scan (unique sizes <= s_max/4, <=40 log-spaced candidates), argmin one-sample
    KS. Returns (tau_hat, s_min_hat, ks_hat, n_tail)."""
    arr = np.asarray(sizes, dtype=np.int64)
    if len(arr) < 8:
        return (float("nan"), 1, float("inf"), 0)
    smax = int(arr.max())
    cands = sorted(set(int(x) for x in np.unique(arr) if 1 <= x <= max(1, smax // 4)))
    if len(cands) > 40:
        sel = np.unique(np.geomspace(1, max(cands), 40).astype(int))
        cands = sorted(set(int(x) for x in sel if x <= max(cands)))
    best = (float("nan"), 1, float("inf"), 0)
    for sm in cands:
        tau = mle_tau(arr, sm)
        d = ks_one_sample(arr, tau, sm)
        if d < best[2]:
            n_tail = int((arr >= sm).sum())
            best = (tau, sm, d, n_tail)
    return best


def ks_two_sample(a, b) -> float:
    """Two-sample KS statistic."""
    x = np.sort(np.asarray(a, dtype=np.float64))
    y = np.sort(np.asarray(b, dtype=np.float64))
    if len(x) == 0 or len(y) == 0:
        return float("inf")
    allv = np.concatenate([x, y])
    cdf_x = np.searchsorted(x, allv, side="right") / len(x)
    cdf_y = np.searchsorted(y, allv, side="right") / len(y)
    return float(np.max(np.abs(cdf_x - cdf_y)))


def ks_two_sample_gate(n1: int, n2: int, alpha_floor: float = 0.10) -> float:
    """D_gate = max(alpha_floor, 1.358*sqrt((n1+n2)/(n1*n2)))  (c(0.05)=1.358, pre-reg)."""
    crit = 1.358 * math.sqrt((n1 + n2) / (n1 * n2))
    return max(alpha_floor, crit)
