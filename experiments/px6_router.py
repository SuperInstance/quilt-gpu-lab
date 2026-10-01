"""PX6 — signature-router: does board-predictable routing claim the PX5 headroom?

Pre-reg (FROZEN before any scoring run): proposals/runs/PX6-signature-router.md

Arms (both reported, no post-hoc selection):
  (a) primary: DT(d6) best-cell router, deterministic target priority
      (pinch-if-correct, else lowest-index correct tree; no-correct states excluded)
  (b) secondary: confidence-gated router (proba max < 0.5 -> exact MajorityVote fallback)

Baselines: composition 0.7437 / any-cell ceiling 0.8698 (PX5, same split).
Branches: WIN >= 0.807, PARTIAL >= 0.759, KILL < 0.759 (arm a, test split).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from px2_cells import build_registry, matrices, MajorityVote, EXPECTED_TERRAIN_DIGEST
from px1b_threat_locality import classify
from px5_disagreement_map import top1_in_opt

DEPTHS = (1, 2, 3, 4, 5, 6)
OUT_DIR = os.path.expanduser("~/projects/quilt-gpu-lab/results/px6_router")
CONF_THRESHOLD = 0.5  # frozen in pre-reg


def main() -> None:
    states, (tr, te), cells, meta = build_registry(seed=0, depths=DEPTHS)
    B, M = matrices(states)
    Btr, Mtr, Bte, Mte = B[tr], M[tr], B[te], M[te]
    n_tr, n_te = len(tr), len(te)
    tree_names = [f"tree_d{k}" for k in DEPTHS]
    names = tree_names + ["pinch"]
    print(f"registry built: test n={n_te}, digest {meta['terrain_digest_fnv1a64']}", flush=True)
    assert meta["terrain_digest_fnv1a64"] == EXPECTED_TERRAIN_DIGEST

    def correctness(split_rows, opts):
        out = np.zeros((len(opts), len(names)), dtype=bool)
        for ci, nm in enumerate(names):
            rows = split_rows[nm]
            for j in range(len(opts)):
                r = rows[j]
                if r is not None and top1_in_opt(r, opts[j]):
                    out[j, ci] = True
        return out

    rows_tr = {nm: cells[nm].score_batch(Btr) for nm in names}
    rows_te = {nm: cells[nm].score_batch(Bte) for nm in names}
    opt_tr = [set(int(m) for m in Mtr[j].nonzero()[0]) for j in range(n_tr)]
    opt_te = [set(int(m) for m in Mte[j].nonzero()[0]) for j in range(n_te)]
    Ctr = correctness(rows_tr, opt_tr)
    Cte = correctness(rows_te, opt_te)
    classes = [classify([int(v) for v in b], opt) for b, opt in zip(Bte, opt_te)]

    # router targets on TRAIN (deterministic priority from pre-reg)
    y_tr = np.full(n_tr, -1, dtype=int)
    for j in range(n_tr):
        if Ctr[j, 6]:                      # pinch correct -> pinch (index 6)
            y_tr[j] = 6
        else:
            correct_trees = [ci for ci in range(6) if Ctr[j, ci]]
            if correct_trees:
                y_tr[j] = correct_trees[0]

    # reflex-coverage probe (pre-reg secondary): pinch fired-rate within all-correct train states
    all_correct_tr = [j for j in range(n_tr) if Ctr[j, :6].all()]
    pinch_fired_allc = round(float(np.mean(
        [rows_tr["pinch"][j] is not None for j in all_correct_tr])), 4) if all_correct_tr else None

    fit = y_tr != -1
    router = DecisionTreeClassifier(max_depth=6, min_samples_leaf=5, random_state=0)
    router.fit(Btr[fit], y_tr[fit])

    pred = router.predict(Bte).astype(int)
    proba = router.predict_proba(Bte)
    conf = proba.max(axis=1)
    routed_a = [bool(Cte[j, pred[j]]) for j in range(n_te)]

    comp = MajorityVote([cells[nm] for nm in names])
    comp_rows = comp.score_batch(Bte)
    comp_correct = [bool(r is not None and top1_in_opt(r, opt_te[j])) for j, r in enumerate(comp_rows)]

    routed_b = [routed_a[j] if conf[j] >= CONF_THRESHOLD else comp_correct[j]
                for j in range(n_te)]

    any_cell = [bool(Cte[j].any()) for j in range(n_te)]

    def per_class(mask):
        out = {}
        for cname in ("WIN", "BLOCK", "NON_LOCAL"):
            idx = [j for j in range(n_te) if classes[j] == cname]
            out[cname] = round(float(np.mean([1.0 if mask[j] else 0.0 for j in idx])), 4) if idx else None
        return out

    def headroom(v):
        h = 0.8698 - 0.7437
        return round((v - 0.7437) / h, 4)

    a_top = round(float(np.mean(routed_a)), 4)
    b_top = round(float(np.mean(routed_b)), 4)
    branch = "WIN" if a_top >= 0.807 else ("PARTIAL" if a_top >= 0.759 else "KILL")
    pred_dist = Counter(int(p) for p in pred)
    degenerate = max(pred_dist.values()) / n_te > 0.95

    out = {
        "pre_reg": "proposals/runs/PX6-signature-router.md",
        "provenance": {"device": meta["device"],
                       "terrain_digest_fnv1a64": meta["terrain_digest_fnv1a64"],
                       "n_train": n_tr, "n_test": n_te,
                       "router_fit_states": int(fit.sum()),
                       "router_hyperparams": {"max_depth": 6, "min_samples_leaf": 5,
                                              "random_state": 0},
                       "conf_threshold": CONF_THRESHOLD},
        "baselines": {"composition_top1": round(float(np.mean(comp_correct)), 4),
                      "any_cell_ceiling": round(float(np.mean(any_cell)), 4)},
        "arm_a": {"routed_top1": a_top, "headroom_claimed_frac": headroom(a_top),
                  "branch": branch, "per_class": per_class(routed_a),
                  "pred_distribution": {names[k]: v for k, v in sorted(pred_dist.items())},
                  "degenerate_flag": degenerate},
        "arm_b": {"routed_top1": b_top, "headroom_claimed_frac": headroom(b_top),
                  "per_class": per_class(routed_b)},
        "reflex_coverage": {"train_all_correct_n": len(all_correct_tr),
                            "pinch_fired_rate_within": pinch_fired_allc},
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "px6_result.json"), "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({
        "arm_a_routed_top1": a_top, "branch": branch,
        "headroom_claimed_frac": headroom(a_top),
        "arm_b_routed_top1": b_top,
        "composition_top1": out["baselines"]["composition_top1"],
        "any_cell_ceiling": out["baselines"]["any_cell_ceiling"],
        "per_class_a": out["arm_a"]["per_class"],
        "degenerate_flag": degenerate,
        "reflex_coverage": out["reflex_coverage"],
    }, indent=2))
    print(f"booked: {OUT_DIR}/px6_result.json", flush=True)


if __name__ == "__main__":
    main()
