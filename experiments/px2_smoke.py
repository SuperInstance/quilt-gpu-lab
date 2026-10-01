"""PX2 SMOKE GATE — cells alone, no gardener.

Pre-reg (FROZEN 2026-09-30): proposals/runs/PX2-patchwork-3x3.md, section
"Smoke gate (before gardener ever runs)":

    Cells alone, no gardener: majority-vote(d3,d4) + format gate must beat d3
    alone on the quick-eval. If plain composition can't beat d3, fix the harness
    before crediting any gardener.

This script:
- trains d3 and d4 trees on the PX1 seed-0 80% TRAIN split ONLY (no test states
  in any training),
- draws the 200-state quick-eval frozen (seed 0) from the 36,073-state test split,
- scores two arms: d3-alone vs majority-vote(format_gate(d3), format_gate(d4)),
- reports top1-in-optimal AND set-recall for both, plus device string, seeds, n,
- verdict: PASS iff composed top1-in-optimal > d3-alone top1-in-optimal, else FAIL.

Fail loud on any exception. Writes results/px2_patchwork/smoke.json. CPU-only:
ollama cells are flag-gated OFF by default and are NOT part of either arm.
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

from px2_cells import (EXPECTED_TERRAIN_DIGEST, FormatGate, MajorityVote,
                       QUICK_EVAL_N, QUICK_EVAL_SEED, REPO, build_registry,
                       device_string, evaluate, matrices, ollama_enabled,
                       quick_eval_indices)

RESULTS_DIR = os.path.join(REPO, "results", "px2_patchwork")
SPLIT_SEED = 0
TREE_SEED = 0


def main() -> None:
    t0 = time.time()

    # --- terrain + PX1 seed-0 split (train cells ONLY on the train split) ---
    states, (tr, te), cells, meta = build_registry(seed=SPLIT_SEED)
    if meta["terrain_digest_fnv1a64"] != EXPECTED_TERRAIN_DIGEST:
        raise RuntimeError("terrain digest mismatch — refusing to run")

    quick = quick_eval_indices(te)  # frozen seed-0 draw from the test split
    overlap = len(set(quick.tolist()) & set(tr.tolist()))
    if overlap != 0:
        raise RuntimeError(f"leakage: {overlap} quick-eval states appear in the train split")

    Bq, Mq = matrices([states[i] for i in quick])

    d3, d4 = cells["tree_d3"], cells["tree_d4"]
    arms = {
        "d3_alone": d3,
        "composed_majority_vote_d3_d4_format_gate": MajorityVote(
            [FormatGate(d3), FormatGate(d4)],
            name="majority_vote(format_gate(d3), format_gate(d4))",
        ),
    }

    results = {
        "experiment": "PX2 smoke gate — cells alone, no gardener",
        "pre_reg": "proposals/runs/PX2-patchwork-3x3.md (FROZEN 2026-09-30)",
        "smoke_gate_rule": "PASS iff majority-vote(d3,d4)+format-gate top1 > d3-alone top1 on quick-eval",
        "device": device_string(ollama_enabled()),
        "ollama_flag_enabled": ollama_enabled(),
        "ollama_in_arms": False,
        "seeds": {
            "split": SPLIT_SEED,
            "tree_random_state": TREE_SEED,
            "quick_eval_draw": QUICK_EVAL_SEED,
            "quick_eval_draw_method": "np.random.default_rng(0).permutation(len(test))[:200]",
        },
        "n": {
            "total_states": len(states),
            "train_split": int(len(tr)),
            "test_split": int(len(te)),
            "quick_eval": int(len(quick)),
        },
        "terrain_digest_fnv1a64": meta["terrain_digest_fnv1a64"],
        "train_split_only": True,
        "quick_eval_train_overlap": overlap,
        "quick_eval_indices": [int(i) for i in quick],
        "trees": {"tree_d3": d3.meta(), "tree_d4": d4.meta()},
        "composition": "majority-vote over format-gated rows of tree_d3 and tree_d4; "
                       "abstaining cells do not vote; combined row = votes + 1e-3*mean + 1e-9*tiebreak",
        "arms": {},
        "runtime_seconds": None,
    }

    for name, cell in arms.items():
        rows = cell.score_batch(Bq)
        n_abstain = sum(1 for r in rows if r is None)
        if n_abstain:
            raise RuntimeError(
                f"arm {name}: {n_abstain}/{len(quick)} quick-eval states abstained — "
                "registered smoke arms must cover the quick-eval (trees never abstain; "
                "an abstention here is a harness bug)"
            )
        S = np.stack([np.asarray(r, dtype=np.float64) for r in rows])
        top1, set_recall = evaluate(S, Mq)  # exact px1 evaluate()
        results["arms"][name] = {
            "top1_in_optimal": top1,
            "set_recall": set_recall,
            "n": int(len(quick)),
            "n_abstain": n_abstain,
        }
        print(f"{name}: top1_in_optimal={top1:.4f} set_recall={set_recall:.4f} (n={len(quick)})", flush=True)

    d3_top1 = results["arms"]["d3_alone"]["top1_in_optimal"]
    comp_top1 = results["arms"]["composed_majority_vote_d3_d4_format_gate"]["top1_in_optimal"]
    margin = comp_top1 - d3_top1
    results["verdict"] = "PASS" if margin > 0 else "FAIL"
    results["margin_top1"] = margin

    results["runtime_seconds"] = round(time.time() - t0, 1)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "smoke.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps({k: results[k] for k in
                      ["verdict", "margin_top1", "device", "seeds", "n"]}, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
