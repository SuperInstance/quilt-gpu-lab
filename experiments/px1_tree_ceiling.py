"""PX1 — The decision-tree ceiling on 3x3 (fleet-triage GPU-EXPERIMENTS.md Exp 2).

PRE-REGISTERED PREDICTIONS (frozen before the run, 2026-09-30 ~15:55 AKDT):

P1. A deep (unlimited) decision tree on the same 9-cell board input reaches
    top1-in-optimal close to 1.0 on held-out states, because the 9-cell board IS the
    complete game state — there is no hidden information for this representation. The
    "ceiling" should therefore be the exact optimal function itself.
P2. A SHALLOW tree (depth 3-4) that still beats the linear 0.18 substantially would say
    the task is nonlinearly separable but shallowly structured. If shallow ~= linear,
    the composition minimax needs lives deeper than any small shallow split.
P3. The pre-registered SIMPLE/COMPOSED split (0-1 immediate wins vs >=2): the linear
    model's accuracy collapses on COMPOSED states relative to SIMPLE (the count-not-sum
    mechanism). The tree degrades much less across the same split.
P4. If ANY model beats the exact solver's ceiling, labels leaked — stop and diagnose.
    (Can only happen through a bug: the solver is the ceiling by construction here.)

Reported per GPU-EXPERIMENTS.md §4: device, provenance digest, ceiling fraction,
variance over seeds, branch landed, controls.
"""
from __future__ import annotations
import json, os, sys, hashlib, time

import numpy as np
from sklearn.tree import DecisionTreeRegressor

sys.path.insert(0, os.path.expanduser("~/projects/pie-minimax-readonly"))
from minmax import enumerate_reachable  # exact solver, ground truth computed not asserted

RNG_SEEDS = [0, 1, 2]
DEVICE = "cpu (numpy 1.x + sklearn 1.9.0, no CUDA involved)"


def fnv1a64(data: bytes) -> str:
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"0x{h:016x}"


def matrices(states):
    B = np.array([list(b) for b, _ in states], dtype=np.float64)
    M = np.zeros((len(states), 9))
    for r, (_, opt) in enumerate(states):
        for m in opt:
            M[r, m] = 1.0
    return B, M


def evaluate(S, M):
    """Same metric as pie-minimax linear_expert.evaluate: top-1 of the score row must be
    in the optimal SET. Set-recall reported alongside, always (Exp 7 rule)."""
    top1 = 0
    setrec = []
    for r in range(len(M)):
        k = max(1, int(M[r].sum()))
        top = np.argsort(-S[r])[:k]
        opt = set(np.nonzero(M[r])[0])
        top1 += 1.0 if top[0] in opt else 0.0
        setrec.append(len(opt & set(top.tolist())) / len(opt))
    return float(top1 / len(M)), float(np.mean(setrec))


def immediate_win_count(b):
    """Moves that complete a line for us right now. >=2 => COMPOSED (a count, not a sum)."""
    from minmax import LINES, winner
    n = 0
    for m in range(9):
        if b[m] != 0:
            continue
        nb = list(b)
        nb[m] = 1
        if winner(nb) == 1:
            n += 1
    return n


def main():
    t0 = time.time()
    states = enumerate_reachable()
    boards = [b for b, _ in states]
    B, M = matrices(states)
    digest = fnv1a64(
        b"".join(bytes((int(v) + 1) for v in b) + bytes(opt) for b, opt in states)
    )
    composed = np.array([immediate_win_count(b) >= 2 for b in boards])

    results = {
        "experiment": "PX1 decision-tree ceiling (fleet-triage Exp 2)",
        "device": DEVICE,
        "n_states": len(states),
        "provenance_fnv1a64": digest,
        "n_composed_states": int(composed.sum()),
        "frac_composed": float(composed.mean()),
        "seeds": RNG_SEEDS,
        "pre_registered": "P1-P4 in module docstring, frozen before run",
        "runs": [],
    }

    for seed in RNG_SEEDS:
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(states))
        n_tr = int(0.8 * len(idx))
        tr, te = idx[:n_tr], idx[n_tr:]
        Btr, Mtr, Bte, Mte = B[tr], M[tr], B[te], M[te]
        cte = composed[te]

        run = {"seed": seed, "n_train": n_tr, "n_test": len(te)}

        # Linear reference (same split, same 81 params, retrained — apples to apples).
        from linear_expert import train as train_linear
        fwd = train_linear(Btr, Mtr, steps=400, lr=0.5, seed=seed, hidden=0)
        t1, sr = evaluate(fwd(Bte), Mte)
        run["linear"] = {"top1": t1, "set_recall": sr}
        t1c, src = evaluate(fwd(Bte)[cte], Mte[cte])
        t1s, srs = evaluate(fwd(Bte)[~cte], Mte[~cte])
        run["linear_split"] = {
            "SIMPLE": {"top1": t1s, "set_recall": srs},
            "COMPOSED": {"top1": t1c, "set_recall": src},
        }

        # Trees: shallow ladder + deep.
        for depth in [3, 4, 6, None]:
            tree = DecisionTreeRegressor(
                max_depth=depth, min_samples_leaf=5, random_state=seed
            )
            tree.fit(Btr, Mtr)
            S = tree.predict(Bte)
            t1, sr = evaluate(S, Mte)
            key = "deep" if depth is None else f"depth{depth}"
            run[key] = {
                "top1": t1, "set_recall": sr, "n_leaves": int(tree.get_n_leaves())
            }
            t1c, src = evaluate(S[cte], Mte[cte])
            t1s, srs = evaluate(S[~cte], Mte[~cte])
            run[key]["split"] = {
                "SIMPLE": {"top1": t1s, "set_recall": srs},
                "COMPOSED": {"top1": t1c, "set_recall": src},
            }

        results["runs"].append(run)
        print(f"seed {seed} done ({time.time()-t0:.0f}s)", flush=True)

    # Variance across seeds (std==0 => INCONCLUSIVE per rule 2).
    summary = {}
    for key in ["linear", "depth3", "depth4", "depth6", "deep"]:
        tops = [r[key]["top1"] for r in results["runs"]]
        summary[key] = {
            "top1_mean": float(np.mean(tops)),
            "top1_std": float(np.std(tops)),
        }
    results["summary_top1"] = summary

    # Branch ruling (P1-P3).
    lin = summary["linear"]["top1_mean"]
    shal = min(
        summary[k]["top1_mean"] for k in ["depth3", "depth4"]
    )
    deep = summary["deep"]["top1_mean"]
    branches = []
    if deep > 0.95:
        branches.append(
            f"P1 CONFIRMED: deep tree ~= {deep:.4f}; ceiling is the exact function. "
            f"Linear {lin:.4f} = {lin/max(deep,1e-9)*100:.1f}% of ceiling."
        )
    branches.append(
        (
            "P2: shallow trees BEAT linear substantially -> task is nonlinearly "
            "separable but shallowly structured."
            if shal > lin + 0.10
            else "P2: shallow ~= linear -> composition lives deeper than shallow splits."
        )
    )
    r0 = results["runs"][0]
    lin_c = r0["linear_split"]["COMPOSED"]["top1"]
    lin_s = r0["linear_split"]["SIMPLE"]["top1"]
    d_c = r0["deep"]["split"]["COMPOSED"]["top1"]
    d_s = r0["deep"]["split"]["SIMPLE"]["top1"]
    branches.append(
        f"P3 (seed 0): linear SIMPLE {lin_s:.4f} -> COMPOSED {lin_c:.4f} "
        f"(drop {lin_s-lin_c:+.4f}); deep-tree SIMPLE {d_s:.4f} -> COMPOSED {d_c:.4f} "
        f"(drop {d_s-d_c:+.4f})."
    )
    results["branch_rulings"] = branches
    results["runtime_s"] = round(time.time() - t0, 1)

    os.makedirs(
        os.path.expanduser("~/projects/quilt-gpu-lab/results/px1_tree_ceiling"),
        exist_ok=True,
    )
    out = os.path.expanduser(
        "~/projects/quilt-gpu-lab/results/px1_tree_ceiling/results.json"
    )
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(summary, indent=2))
    for b in branches:
        print(b)
    print("wrote", out)


if __name__ == "__main__":
    main()
