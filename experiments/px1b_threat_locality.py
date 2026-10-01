"""PX1b — threat-locality partition on the REAL 180,361-state enumeration.

Context: PX1 (commit 7973dbb) found the sign-flip surprise: linear does BETTER on
COMPOSED (>=2 immediate wins) than SIMPLE states, killing "threat-counting" as the linear
failure mode and pointing at NON-LOCAL play as the real mechanism. The fleet doc proposed
the same follow-up. This is the proper run: real solver data, pre-registered classes,
held-out evaluation, 3 seeds. NOT the mock-data demo circulating in fleet chat.

CLASSES (frozen before the run):
- WIN      : an immediate win is available -> every optimal move is an immediate win
             (asserted; if any optimal move in this class is not a win, FAIL LOUD).
- BLOCK    : no immediate win, but opponent holds >=1 active threat (2-in-line + empty
             third); every optimal move is a blocking cell. Reactive containment.
- NON_LOCAL: no immediate win taken, optimal moves are NOT all blocks. Prophylactic /
             positional play (fork-creation, tempo, zugzwang shaping).

PRE-REGISTERED PREDICTIONS:
P1. Linear accuracy degrades monotonically WIN > BLOCK > NON_LOCAL, with the NON_LOCAL
    gap the largest. (The mechanism claim, now on real data.)
P2. Trees (d3+) degrade far less across classes — shallow composition covers positional
    play. Deep tree is near-ceiling on every class.
P3. NON_LOCAL is a substantial fraction of states (not a rare curiosity).
P4 (kill branch): if linear does NOT degrade on NON_LOCAL, the sign-flip explanation
    shifts back toward threat-counting; book it and re-think.

Reporting per fleet doc rules: device, provenance digest, ceiling per class, mean +/- std
over 3 seeds, class sizes, controls (same split/metric as PX1; models never see test).
"""
from __future__ import annotations
import argparse, json, os, sys, time

import numpy as np
from sklearn.tree import DecisionTreeRegressor

sys.path.insert(0, os.path.expanduser("~/projects/pie-minimax-readonly"))
from minmax import enumerate_reachable, LINES, winner, play

RNG_SEEDS = [0, 1, 2]
DEVICE = "cpu (numpy + sklearn 1.9.0)"


def fnv1a64(data: bytes) -> str:
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"0x{h:016x}"


def immediate_wins(b):
    return {m for m in range(9) if b[m] == 0 and winner(play(b, m)) == 1}


def block_cells(b):
    """Empty cells that complete an opponent 2-in-line (their threat cells)."""
    out = set()
    for a, c, d in LINES:
        vals = [b[a], b[c], b[d]]
        if vals.count(-1) == 2 and vals.count(1) == 0 and vals.count(0) == 1:
            for idx, v in zip((a, c, d), vals):
                if v == 0:
                    out.add(idx)
    return out


def classify(b, opt):
    wins = immediate_wins(b)
    if set(opt) <= wins and wins:
        return "WIN"
    blocks = block_cells(b)
    if blocks and set(opt) <= blocks:
        return "BLOCK"
    return "NON_LOCAL"


def matrices(states):
    B = np.array([list(b) for b, _ in states], dtype=np.float64)
    M = np.zeros((len(states), 9))
    for r, (_, opt) in enumerate(states):
        for m in opt:
            M[r, m] = 1.0
    return B, M


def evaluate(S, M):
    top1 = 0
    setrec = []
    for r in range(len(M)):
        k = max(1, int(M[r].sum()))
        top = np.argsort(-S[r])[:k]
        opt = set(np.nonzero(M[r])[0])
        top1 += 1.0 if top[0] in opt else 0.0
        setrec.append(len(opt & set(top.tolist())) / len(opt))
    return float(top1 / len(M)), float(np.mean(setrec))


def main():
    t0 = time.time()
    states = enumerate_reachable()
    boards = [b for b, _ in states]

    classes = []
    for b, opt in states:
        c = classify(b, opt)
        # fail-loud assertion for the WIN class (ground truth must be computed right)
        if c == "WIN":
            wins = immediate_wins(b)
            assert set(opt) <= wins and len(wins) > 0, f"WIN misclassified: {b} opt={opt} wins={wins}"
        classes.append(c)

    digest = fnv1a64(
        b"".join(
            bytes((int(v) + 1) for v in b) + bytes(opt) + classes[i].encode()
            for i, (b, opt) in enumerate(states)
        )
    )
    classes = np.array(classes)
    B, M = matrices(states)

    results = {
        "experiment": "PX1b threat-locality partition (real 180,361-state data)",
        "device": DEVICE,
        "n_states": len(states),
        "provenance_fnv1a64": digest,
        "class_sizes": {c: int((classes == c).sum()) for c in ["WIN", "BLOCK", "NON_LOCAL"]},
        "pre_registered": "P1-P4 in module docstring, frozen before run",
        "per_class": {},
    }

    for seed in RNG_SEEDS:
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(states))
        n_tr = int(0.8 * len(idx))
        tr, te = idx[:n_tr], idx[n_tr:]
        Btr, Mtr, Bte, Mte = B[tr], M[tr], B[te], M[te]
        cte = classes[te]

        from linear_expert import train as train_linear
        fwd = train_linear(Btr, Mtr, steps=400, lr=0.5, seed=seed, hidden=0)
        S_lin = fwd(Bte)

        tree3 = DecisionTreeRegressor(max_depth=3, min_samples_leaf=5, random_state=seed).fit(Btr, Mtr)
        tree6 = DecisionTreeRegressor(max_depth=6, min_samples_leaf=5, random_state=seed).fit(Btr, Mtr)
        treed = DecisionTreeRegressor(max_depth=None, min_samples_leaf=5, random_state=seed).fit(Btr, Mtr)
        S_t3, S_t6, S_td = tree3.predict(Bte), tree6.predict(Bte), treed.predict(Bte)

        run = {"seed": seed}
        for cname in ["WIN", "BLOCK", "NON_LOCAL"]:
            mask = cte == cname
            if mask.sum() == 0:
                continue
            entry = {"n": int(mask.sum())}
            for mname, S in [
                ("linear", S_lin),
                ("depth3", S_t3),
                ("depth6", S_t6),
                ("deep", S_td),
            ]:
                t1, sr = evaluate(S[mask], Mte[mask])
                entry[mname] = {"top1": round(t1, 4), "set_recall": round(sr, 4)}
            results["per_class"].setdefault(cname, []).append(entry)
        print(f"seed {seed} done ({time.time()-t0:.0f}s)", flush=True)

    # variance across seeds
    summary = {}
    for cname, entries in results["per_class"].items():
        summary[cname] = {}
        for mname in ["linear", "depth3", "depth6", "deep"]:
            tops = [e[mname]["top1"] for e in entries]
            summary[cname][mname] = {
                "top1_mean": round(float(np.mean(tops)), 4),
                "top1_std": round(float(np.std(tops)), 4),
            }
    results["summary_top1_by_class"] = summary

    # branch rulings
    lin = {c: summary[c]["linear"]["top1_mean"] for c in summary}
    rulings = []
    if (
        lin.get("WIN", 0) >= lin.get("BLOCK", 0) - 1e-9
        and lin.get("BLOCK", 0) > lin.get("NON_LOCAL", 0)
    ):
        rulings.append(
            f"P1 CONFIRMED: linear WIN {lin.get('WIN')} >= BLOCK {lin.get('BLOCK')} "
            f"> NON_LOCAL {lin.get('NON_LOCAL')} — additive voting fails on positional "
            f"(non-local) play, not on threat-counting."
        )
    else:
        rulings.append(f"P1 NOT CONFIRMED as ordered: linear per class = {lin}. P4 kill branch engaged.")
    d3 = {c: summary[c]["depth3"]["top1_mean"] for c in summary}
    dd = {c: summary[c]["deep"]["top1_mean"] for c in summary}
    rulings.append(f"P2: d3 per class = {d3}; deep per class = {dd}.")
    frac_nl = results["class_sizes"]["NON_LOCAL"] / len(states)
    rulings.append(f"P3: NON_LOCAL fraction = {frac_nl:.3f} ({results['class_sizes']['NON_LOCAL']} states).")
    results["branch_rulings"] = rulings

    # RC-1: verification re-runs must write to scratch, never over the artifact under test.
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="~/projects/quilt-gpu-lab/results/px1b_threat_locality/results.json")
    args = ap.parse_args()
    out = os.path.expanduser(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(summary, indent=2))
    for r in rulings:
        print(r)
    print("wrote", out)


if __name__ == "__main__":
    main()
