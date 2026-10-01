"""PX5b — permutation null for the PX5 mutual-information asymmetry.

Follow-up to PX5 (results/px5_disagreement/px5_map.json), which booked
MI(signature -> composition-correct) = 0.5955 bits and
MI(signature -> threat class) = 0.1212 bits as point estimates with no
uncertainty (deepseek_stats review point 3).

PX5's runner did not persist per-state artifacts, so this script REGENERATES
the per-state join by re-running the frozen instrument machinery unchanged
(px2_cells.build_registry(seed=0) + the exact per-state code path of
experiments/px5_disagreement_map.py: same seeds, same estimator, terrain
digest asserted). It then CROSS-CHECKS the regenerated aggregates against the
booked px5_map.json values and FAILS LOUD on any mismatch — nothing is booked
unless the regenerated join reproduces the booked map. The per-state vectors
are saved to results/px5_disagreement/per_state.npz so all future analyses
have a real joinable artifact.

Permutation test (numpy only): shuffle the LABEL vector (which preserves the
label marginal) against the fixed signature vector, recompute MI with the
same estimator, 1,000 shuffles, seed 0. Two tests:
  T1: labels = composition-correct (2 classes)
  T2: labels = PX1b threat class (3 classes)
Reports observed MI (unrounded), null mean/sd, empirical p =
(1 + #{null >= observed}) / (1 + n_shuffles), Miller-Madow bias note, and the
effective cardinality (15 observed signature values, not 64).
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
from px5_disagreement_map import DEPTHS, top1_in_opt  # frozen instrument helpers

REPO = os.path.expanduser("~/projects/quilt-gpu-lab")
OUT_DIR = os.path.join(REPO, "results", "px5_disagreement")
N_SHUFFLES = 1000
SEED = 0


def mi_bits_exact(xs, ys) -> float:
    """Same estimator as px5_disagreement_map.mi_bits, without rounding."""
    n = len(xs)
    joint = Counter(zip(xs, ys))
    px, py = Counter(xs), Counter(ys)
    mi = 0.0
    for (a, b), nxy in joint.items():
        p = nxy / n
        mi += p * math.log2(p / ((px[a] / n) * (py[b] / n)))
    return mi


def miller_madow_bits(k_x: int, k_y: int, n: int) -> float:
    """Miller-Madow bias correction: (K-1)(L-1) / (2N ln 2) bits."""
    return (k_x - 1) * (k_y - 1) / (2.0 * n * math.log(2.0))


def permtest(sig: list, labels: list, rng: np.random.Generator) -> dict:
    obs = mi_bits_exact(sig, labels)
    lab_arr = np.asarray(labels, dtype=object)
    null = np.empty(N_SHUFFLES)
    for i in range(N_SHUFFLES):
        null[i] = mi_bits_exact(sig, list(lab_arr[rng.permutation(len(lab_arr))]))
    p = (1.0 + float(np.sum(null >= obs))) / (1.0 + N_SHUFFLES)
    k_x = len(set(sig))
    k_y = len(set(labels))
    return {
        "observed_mi_bits": round(obs, 6),
        "null_mean_bits": round(float(np.mean(null)), 6),
        "null_sd_bits": round(float(np.std(null, ddof=1)), 6),
        "null_max_bits": round(float(np.max(null)), 6),
        "empirical_p": round(p, 4),
        "n_shuffles": N_SHUFFLES,
        "effective_cardinality": {"signature_values_observed": k_x,
                                  "label_values": k_y,
                                  "joint_cells": k_x * k_y},
        "miller_madow_bias_bits": round(miller_madow_bits(k_x, k_y, len(sig)), 6),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)

    # -- regenerate the per-state join with the frozen instrument -------------
    states, (tr, te), cells, meta = build_registry(seed=0, depths=DEPTHS)
    assert meta["terrain_digest_fnv1a64"] == EXPECTED_TERRAIN_DIGEST
    B, M = matrices(states)
    Bte, Mte = B[te], M[te]
    n = len(te)
    tree_names = [f"tree_d{k}" for k in DEPTHS]

    opt_sets = [set(int(m) for m in Mte[j].nonzero()[0]) for j in range(n)]
    classes = [classify([int(v) for v in b], opt) for b, opt in zip(Bte, opt_sets)]
    cell_rows = {name: cells[name].score_batch(Bte) for name in tree_names}
    pinch_rows = cells["pinch"].score_batch(Bte)

    sigs = []
    for j in range(n):
        opt = opt_sets[j]
        sigs.append("".join(
            "1" if (cell_rows[name][j] is not None and top1_in_opt(cell_rows[name][j], opt)) else "0"
            for name in tree_names))
    comp = MajorityVote([cells[name] for name in tree_names + ["pinch"]])
    comp_rows = comp.score_batch(Bte)
    comp_correct = [bool(r is not None and top1_in_opt(r, opt_sets[j]))
                    for j, r in enumerate(comp_rows)]

    # -- cross-check against the BOOKED px5_map.json (fail loud) --------------
    with open(os.path.join(OUT_DIR, "px5_map.json")) as f:
        booked = json.load(f)
    checks = {
        "n_test": (n, booked["provenance"]["n_test"]),
        "n_unique_signatures": (len(set(sigs)), booked["signature_census"]["n_unique"]),
        "comp_top1_overall": (round(float(np.mean(comp_correct)), 4),
                              booked["comp_top1_overall"]),
        "mi_signature_vs_comp_correct": (round(mi_bits_exact(sigs, comp_correct), 4),
                                         booked["mi_bits"]["signature_vs_comp_correct"]),
        "mi_signature_vs_class": (round(mi_bits_exact(sigs, classes), 4),
                                  booked["mi_bits"]["signature_vs_class"]),
        "all_6_correct_n": (sum(1 for s in sigs if s == "111111"),
                            booked["unanimous_partitions"]["all_6_correct"]["n"]),
        "all_6_wrong_n": (sum(1 for s in sigs if s == "000000"),
                          booked["unanimous_partitions"]["all_6_wrong"]["n"]),
    }
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    if bad:
        print(json.dumps({"error": "regenerated per-state join does NOT reproduce booked px5_map",
                          "mismatches": {k: v for k, v in bad.items()}}, indent=2))
        sys.exit(1)

    # -- persist the now-joinable per-state artifact ---------------------------
    np.savez_compressed(
        os.path.join(OUT_DIR, "per_state.npz"),
        signature=np.array(sigs, dtype="U6"),
        comp_correct=np.array(comp_correct, dtype=bool),
        px1b_class=np.array(classes, dtype="U9"),
    )

    # -- permutation tests -----------------------------------------------------
    t1 = permtest(sigs, comp_correct, rng)
    t2 = permtest(sigs, classes, rng)

    out = {
        "experiment": "PX5b permutation null for PX5 MI asymmetry",
        "pre_reg": "REVISION-BRIEF-v1.md item 3 (panel 2026-09-30, deepseek_stats point 3)",
        "provenance": {
            "method": "per-state join regenerated via frozen px5 instrument machinery "
                      "(build_registry(seed=0), identical per-state code path); "
                      "aggregates cross-checked against booked px5_map.json before booking",
            "terrain_digest_fnv1a64": EXPECTED_TERRAIN_DIGEST,
            "n_test": n, "split_seed": 0, "tree_seed": 0,
            "permutation_seed": SEED, "numpy_rng": "np.random.default_rng(0)",
        },
        "cross_checks_vs_booked": {k: {"regenerated": v[0], "booked": v[1]}
                                   for k, v in checks.items()},
        "T1_signature_vs_composition_correct": t1,
        "T2_signature_vs_threat_class": t2,
        "notes": [
            "Empirical p is (1 + #{null >= observed}) / (1 + n_shuffles); the +1 avoids zero p-values.",
            "Shuffling the label vector preserves the label marginal, so the null is 'no association with signature', not 'label marginal changed'.",
            "Miller-Madow bias for T1 (15x2 cells, N=36,073) is ~2.8e-4 bits and for T2 (15x3) ~5.6e-4 bits — orders of magnitude below the observed asymmetry; effective cardinality is the 15 OBSERVED signature values, not 64.",
        ],
    }
    with open(os.path.join(OUT_DIR, "permtest.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({"T1_sig_vs_comp": t1, "T2_sig_vs_class": t2}, indent=2))
    print(f"booked: {OUT_DIR}/permtest.json (+ per_state.npz)", flush=True)


if __name__ == "__main__":
    main()
