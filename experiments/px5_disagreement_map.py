"""PX5 — cell-signature map: routing structure BETWEEN cells (exploratory map).

Pre-reg (FROZEN before any scoring run): proposals/runs/PX5-cell-signature-map.md

Question: IE3 found cells are dedicated specialists and routing happens BETWEEN cells.
Does the per-state pattern of WHICH cells succeed (6-bit tree signature d1..d6,
x pinch fired/correct/abstain axis) segment the state space into interpretable regions?

Instrument: PX2 registry, PX1 seed-0 split, full 36,073-state test split (never
trained on). Analyses fixed in the pre-reg: census, MI(signature, class),
MI(signature, composition-correct), unanimous partitions, router ceiling,
per-cell x class correctness matrix. EXPLORATORY — no confirmatory branch.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from px2_cells import build_registry, matrices, MajorityVote, EXPECTED_TERRAIN_DIGEST
from px1b_threat_locality import classify

DEPTHS = (1, 2, 3, 4, 5, 6)
OUT_DIR = os.path.expanduser("~/projects/quilt-gpu-lab/results/px5_disagreement")


def top1_in_opt(row, opt_set) -> bool:
    top = int(np.argsort(-np.asarray(row, dtype=np.float64), kind="stable")[0])
    return top in opt_set


def mi_bits(xs, ys) -> float:
    """Mutual information in bits; 0.0 if either variable is constant."""
    n = len(xs)
    if n == 0:
        return 0.0
    joint = Counter(zip(xs, ys))
    px, py = Counter(xs), Counter(ys)
    mi = 0.0
    for (a, b), nxy in joint.items():
        p = nxy / n
        mi += p * math.log2(p / ((px[a] / n) * (py[b] / n)))
    return round(mi, 4)


def main() -> None:
    states, (tr, te), cells, meta = build_registry(seed=0, depths=DEPTHS)
    B, M = matrices(states)
    Bte, Mte = B[te], M[te]
    n = len(te)
    tree_names = [f"tree_d{k}" for k in DEPTHS]
    print(f"registry built: {meta['n_states']} states, test n={n}, "
          f"digest {meta['terrain_digest_fnv1a64']}", flush=True)
    assert meta["terrain_digest_fnv1a64"] == EXPECTED_TERRAIN_DIGEST

    opt_sets = [set(int(m) for m in Mte[j].nonzero()[0]) for j in range(n)]
    classes = [classify([int(v) for v in b], opt) for b, opt in zip(Bte, opt_sets)]

    cell_rows = {name: cells[name].score_batch(Bte) for name in tree_names}
    pinch_rows = cells["pinch"].score_batch(Bte)

    sigs, pinch_axis = [], []
    for j in range(n):
        opt = opt_sets[j]
        bits = "".join(
            "1" if (cell_rows[name][j] is not None and top1_in_opt(cell_rows[name][j], opt)) else "0"
            for name in tree_names
        )
        sigs.append(bits)
        r = pinch_rows[j]
        pinch_axis.append("abstain" if r is None else
                          ("correct" if top1_in_opt(r, opt) else "wrong"))

    comp = MajorityVote([cells[name] for name in tree_names + ["pinch"]])
    comp_rows = comp.score_batch(Bte)
    comp_correct = [bool(r is not None and top1_in_opt(r, opt_sets[j]))
                    for j, r in enumerate(comp_rows)]

    # -- 1. census ------------------------------------------------------------
    sig_counts = Counter(sigs)

    # -- 2. mutual information ------------------------------------------------
    mi_class = mi_bits(sigs, classes)
    mi_comp = mi_bits(sigs, ["C" if c else "W" for c in comp_correct])

    # -- 3. unanimous partitions ----------------------------------------------
    def partition_stats(mask):
        idx = [j for j in range(n) if mask[j]]
        return {
            "n": len(idx),
            "class_mix": dict(Counter(classes[j] for j in idx)),
            "comp_top1": round(float(np.mean([comp_correct[j] for j in idx])), 4) if idx else None,
        }

    all_correct = partition_stats([s == "1" * len(tree_names) for s in sigs])
    all_wrong = partition_stats([s == "0" * len(tree_names) for s in sigs])

    # -- 4. router ceiling ----------------------------------------------------
    any_tree = [s != "0" * len(tree_names) for s in sigs]
    pinch_correct = [p == "correct" for p in pinch_axis]
    any_cell = [a or p for a, p in zip(any_tree, pinch_correct)]

    def rate(mask, sub=None):
        vals = [1.0 if (a and (sub is None or classes[j] == sub)) else 0.0
                for j, a in enumerate(mask)]
        m = vals if sub is None else [v for j, v in enumerate(vals) if sub is None or classes[j] == sub]
        return round(float(np.mean(m)), 4) if m else None

    router = {"any_tree_correct": {"overall": rate(any_tree)},
              "any_cell_correct": {"overall": rate(any_cell)},
              "comp_top1": {"overall": round(float(np.mean(comp_correct)), 4)}}
    for cname in ("WIN", "BLOCK", "NON_LOCAL"):
        router["any_tree_correct"][cname] = rate(any_tree, cname)
        router["any_cell_correct"][cname] = rate(any_cell, cname)
        router["comp_top1"][cname] = round(float(np.mean(
            [1.0 if comp_correct[j] else 0.0 for j in range(n) if classes[j] == cname])), 4)

    # -- 5. per-cell x class correctness --------------------------------------
    cell_class = {}
    for name in tree_names:
        cell_class[name] = {cname: round(float(np.mean(
            [1.0 if (cell_rows[name][j] is not None and top1_in_opt(cell_rows[name][j], opt_sets[j])) else 0.0
             for j in range(n) if classes[j] == cname])), 4)
            for cname in ("WIN", "BLOCK", "NON_LOCAL")}
    def pinch_fired_correct_rate(cname):
        idx = [j for j in range(n) if classes[j] == cname and pinch_axis[j] != "abstain"]
        if not idx:
            return None
        return round(float(np.mean([1.0 if pinch_axis[j] == "correct" else 0.0 for j in idx])), 4)

    pin = {cname: pinch_fired_correct_rate(cname) for cname in ("WIN", "BLOCK", "NON_LOCAL")}
    pinch_fired_rate = {cname: round(float(np.mean(
        [1.0 if pinch_axis[j] != "abstain" else 0.0
         for j in range(n) if classes[j] == cname])), 4)
        for cname in ("WIN", "BLOCK", "NON_LOCAL")}
    cell_class["pinch_fired_correct"] = pin
    cell_class["pinch_fired_rate"] = pinch_fired_rate

    # pinch pre-emption: how much of the space does the reflex own?
    pinch_share = {k: round(v / n, 4) for k, v in Counter(pinch_axis).items()}

    out = {
        "pre_reg": "proposals/runs/PX5-cell-signature-map.md",
        "class": "EXPLORATORY_MAP",
        "provenance": {
            "device": meta["device"],
            "terrain_digest_fnv1a64": meta["terrain_digest_fnv1a64"],
            "n_states": meta["n_states"], "n_test": n,
            "split_seed": 0, "tree_seed": 0,
            "depths": list(DEPTHS), "tree_hyperparams": {"min_samples_leaf": 5, "random_state": 0},
        },
        "signature_census": {"n_unique": len(sig_counts),
                             "top10": sig_counts.most_common(10)},
        "mi_bits": {"signature_vs_class": mi_class, "signature_vs_comp_correct": mi_comp},
        "unanimous_partitions": {"all_6_correct": all_correct, "all_6_wrong": all_wrong},
        "router_ceiling": router,
        "cell_class_matrix": cell_class,
        "pinch_preemption_share": pinch_share,
        "comp_top1_overall": round(float(np.mean(comp_correct)), 4),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "px5_map.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({
        "n_unique_signatures": len(sig_counts),
        "mi_signature_vs_class_bits": mi_class,
        "mi_signature_vs_comp_bits": mi_comp,
        "all_correct_n": all_correct["n"], "all_wrong_n": all_wrong["n"],
        "all_wrong_class_mix": all_wrong["class_mix"],
        "router_any_cell_overall": router["any_cell_correct"]["overall"],
        "comp_top1_overall": out["comp_top1_overall"],
        "pinch_share": pinch_share,
    }, indent=2))
    print(f"booked: {OUT_DIR}/px5_map.json", flush=True)


if __name__ == "__main__":
    main()
