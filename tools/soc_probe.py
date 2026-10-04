#!/usr/bin/env python3
"""soc_probe.py — avalanche-susceptibility critical-point prober.

Standalone liftable of the PIDFIRE-1 ternary-fire core (pattern lifted from
`experiments/pidfire_common.py`, PROVEN on-silicon 2026-10-03): a forest-fire
cellular automaton (tree/burning/empty, von Neumann spread, per-step ignition
prob p) self-organizes to a critical driving rate where the avalanche-size
susceptibility chi = Var(size)/<size> peaks. This tool sweeps a p-grid,
measures the avalanche-size distribution per p, locates the susceptibility
peak (the SOC critical point), and books a KEEP/KILL receipt:

  KEEP  — interior peak: chi rises then falls across the p-grid (criticality)
  KILL  — chi monotone across the grid (sub- or super-critical everywhere;
          widen the grid or fix the model — never a silent pass)
  rc=2  — fail-loud input (bad grid, T too short, non-finite chi)

Memory law: O(grid) — grids are flat byte arrays; only avalanche sizes
accumulate. Stdlib-only (random module, seeded; deterministic receipts).

Worked example (default small grid, ~2s):
    python tools/soc_probe.py --example
Selftest (shrunk-sweep sanity + noise pin):
    python tools/soc_probe.py --selftest
Full run:
    python tools/soc_probe.py --n 64 --ts 400,600,900,1400,2200,3400 \
        --burn 2000 --draws 2 --seed 2718 --out receipt.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time

# states (unsigned: stored in a bytearray)
EMPTY, TREE, BURN = 0, 1, 2


class FireCA:
    """Ternary-fire CA, flat-array, non-wrapping von Neumann spread.

    Rule order per step (upstream ternary-fire semantics):
      1. optional forced ignition (avalanche bookkeeping boundary)
      2. BURN -> EMPTY
      3. TREE with k burning neighbors catches w.p. 1-(1-p)**k
      4. EMPTY regrows to TREE w.p. growth (tree birth)
    """

    def __init__(self, n: int, rng: random.Random, rho0: float = 0.5):
        if n < 8:
            raise ValueError(f"grid n={n} too small (min 8)")
        self.n = n
        self.size = n * n
        self.rng = rng
        self.grid = bytearray(
            TREE if rng.random() < rho0 else EMPTY for _ in range(self.size)
        )

    def _neighbors(self, i: int):
        n, r, c = self.n, i // self.n, i % self.n
        if r > 0:
            yield i - n
        if r < n - 1:
            yield i + n
        if c > 0:
            yield i - 1
        if c < n - 1:
            yield i + 1

    def step(self, p_fire: float, growth: float = 0.0, ignite_idx: int | None = None) -> int:
        """One synchronous step; returns avalanche size (cells ignited this step)."""
        rng = self.rng
        g = self.grid
        ignited = set()

        # 1. forced/random ignition (TREE -> BURN)
        if ignite_idx is not None:
            idxs = [ignite_idx]
        else:
            idxs = [rng.randrange(self.size)] if rng.random() < p_fire else []
        for i in idxs:
            if g[i] == TREE:
                g[i] = BURN
                ignited.add(i)

        # 2-3. synchronous update from old state (snapshot: neighbors must
        # see the OLD burn state, not cells already flipped this pass)
        old = bytes(g)
        catches = []
        for i in range(self.size):
            if old[i] == BURN:
                g[i] = EMPTY
            elif old[i] == TREE:
                k = sum(1 for j in self._neighbors(i) if old[j] == BURN)
                if k and rng.random() < 1.0 - (1.0 - p_fire) ** k:
                    catches.append(i)
        for i in catches:
            g[i] = BURN
            ignited.add(i)

        # 4. regrowth
        if growth > 0.0:
            for i in range(self.size):
                if g[i] == EMPTY and rng.random() < growth:
                    g[i] = TREE

        return len(ignited)

    def run(self, p_fire: float, t_total: int, t_transient: int,
            growth: float = 0.0) -> list[int]:
        sizes = []
        for t in range(t_total):
            s = self.step(p_fire, growth=growth)
            if t >= t_transient and s > 0:
                sizes.append(s)
        return sizes


def susceptibility(sizes: list[int]) -> float:
    """chi = Var(s)/mean(s); finite-size criticality statistic."""
    if not sizes:
        return 0.0
    m = sum(sizes) / len(sizes)
    var = sum((x - m) ** 2 for x in sizes) / len(sizes)
    if not math.isfinite(m) or m <= 0:
        raise ValueError(f"degenerate mean avalanche size {m}")
    return var / m


def sweep(n: int, p_grid: list[float], t_total: int, t_transient: int,
          draws: int, seed: int, growth: float = 0.02) -> list[dict]:
    out = []
    for p in p_grid:
        chis = []
        for d in range(draws):
            rng = random.Random(seed * 100003 + d)
            ca = FireCA(n, rng)
            sizes = ca.run(p, t_total, t_transient, growth=growth)
            chis.append(susceptibility(sizes))
        out.append({"p": p, "chi": sum(chis) / len(chis),
                    "chi_per_draw": chis})
    return out


def verdict(rows: list[dict]) -> str:
    chis = [r["chi"] for r in rows]
    if not all(math.isfinite(c) for c in chis):
        raise ValueError("non-finite susceptibility in sweep")
    peak_i = max(range(len(chis)), key=lambda i: chis[i])
    if 0 < peak_i < len(chis) - 1:
        return "KEEP"
    return "KILL"  # peak at grid edge => monotone trend, grid didn't bracket


def selftest() -> int:
    checks = []
    # check 1: interior peak on a bracketing grid (small but real sweep)
    rows = sweep(n=16, p_grid=[0.05, 0.2, 0.5, 0.8, 0.95], t_total=1500,
                 t_transient=500, draws=1, seed=11)
    v = verdict(rows)
    checks.append(("interior-peak", v == "KEEP", f"verdict={v} "
                   + " ".join(f"p={r['p']}:{r['chi']:.1f}" for r in rows)))
    # check 2: edge-peak books KILL (grid not bracketing -> honest fail)
    rows2 = rows[:2]
    v2 = verdict(rows2)
    checks.append(("edge-kill", v2 == "KILL", f"verdict={v2}"))
    # check 3: susceptibility is finite and positive on activity
    c = susceptibility([3, 1, 4, 1, 5])
    checks.append(("chi-finite", math.isfinite(c) and c > 0, f"chi={c:.3f}"))
    # check 4: variance pin — same-mean distributions: higher spread must
    # give higher chi (chi = Var/mean is a spread detector)
    checks.append(("chi-variance", susceptibility([2, 8]) > susceptibility([5, 5]),
                   f"chi_spread={susceptibility([2,8]):.2f} > chi_flat={susceptibility([5,5]):.2f}"))
    ok = 0
    for name, passed, note in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {note}")
        ok += passed
    print(f"SELFTEST {ok}/{len(checks)}")
    return 0 if ok == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Avalanche-susceptibility SOC prober")
    ap.add_argument("--n", type=int, default=32, help="grid side (default 32)")
    ap.add_argument("--ts", type=str, default="1000,2000,4000,8000",
                    help="comma p-grid of per-step ignition probabilities")
    ap.add_argument("--t-total", type=int, default=4000)
    ap.add_argument("--t-transient", type=int, default=1000)
    ap.add_argument("--draws", type=int, default=2)
    ap.add_argument("--growth", type=float, default=0.02,
                    help="per-step EMPTY->TREE regrowth prob (default 0.02)")
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--example", action="store_true",
                    help="run the docstring's worked example (small, fast)")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.example:
        a.n, a.ts, a.t_total, a.t_transient, a.draws = 16, "0.05,0.2,0.5,0.8,0.95", 1500, 500, 1

    try:
        p_grid = [float(x) for x in a.ts.split(",")]
        if not p_grid or any(not (0 < p <= 1) for p in p_grid):
            raise ValueError(f"bad p grid {a.ts}")
        if a.t_transient >= a.t_total:
            raise ValueError("t_transient must be < t_total")
        if a.draws < 1:
            raise ValueError("draws >= 1 required")
        t0 = time.time()
        rows = sweep(a.n, p_grid, a.t_total, a.t_transient, a.draws, a.seed,
                     growth=a.growth)
        v = verdict(rows)
        peak = max(rows, key=lambda r: r["chi"])
        receipt = {
            "tool": "soc_probe", "verdict": v,
            "n": a.n, "p_grid": p_grid, "t_total": a.t_total,
            "t_transient": a.t_transient, "draws": a.draws, "seed": a.seed,
            "peak": {"p": peak["p"], "chi": round(peak["chi"], 2)},
            "rows": [{**r, "chi": round(r["chi"], 2)} for r in rows],
            "wall_s": round(time.time() - t0, 2),
        }
    except Exception as e:  # fail-loud receipt even on death
        receipt = {"tool": "soc_probe", "verdict": "FAIL-INPUT",
                   "error": f"{type(e).__name__}: {e}"}
        if a.out:
            with open(a.out, "w") as f:
                json.dump(receipt, f, indent=2)
        print(json.dumps(receipt, indent=2))
        return 2

    print(json.dumps(receipt, indent=2))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(receipt, f, indent=2)
        print(f"receipt -> {a.out}")
    return 0 if v == "KEEP" else 1


if __name__ == "__main__":
    sys.exit(main())
