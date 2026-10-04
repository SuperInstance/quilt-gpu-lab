"""Timing probe for PIDFIRE-1 (timing only — no outcome data recorded).
Measures numpy step cost for the ternary-fire DS substrate at candidate sizes."""
import time
import numpy as np

RNG = np.random.default_rng(7)

def step_count(burn, tree, p, q, empty_next, tree_next):
    # burn: bool grid currently burning; tree/empty bool grids
    nb = np.zeros_like(burn)
    nb[1:, :] |= burn[:-1, :]
    nb[:-1, :] |= burn[1:, :]
    nb[:, 1:] |= burn[:, :-1]
    nb[:, :-1] |= burn[:, 1:]
    new_burn = tree & nb & tree_next
    new_tree = empty & empty_next
    return new_burn, new_tree

for N in (96, 128):
    tree = RNG.random((N, N)) < 0.5
    burn = np.zeros((N, N), dtype=bool)
    r1 = RNG.random((N, N))
    r2 = RNG.random((N, N))
    t0 = time.perf_counter()
    M = 2000
    for _ in range(M):
        empty = ~tree & ~burn
        b1 = RNG.random((N, N))
        b2 = RNG.random((N, N))
        nb = np.zeros_like(burn)
        nb[1:, :] |= burn[:-1, :]
        nb[:-1, :] |= burn[1:, :]
        nb[:, 1:] |= burn[:, :-1]
        nb[:, :-1] |= burn[:, 1:]
        new_burn = tree & nb & (b1 < 0.8)
        new_tree = empty & (b2 < 0.001)
        tree = (tree & ~new_burn) | new_tree
        burn = new_burn
    dt = (time.perf_counter() - t0) / M
    print(f"N={N}: {dt*1e3:.3f} ms/step -> 40k steps = {dt*40000:.0f} s")
