"""d20_transitional_ablate.py — nonlinear + identity ablations of D19's kernel.

D19: the linear ternary kernel beats Markov-1 (0.0101 vs 0.0179) and matches
the continuous oracle (0.0110) — ternarization is free. Two follow-ups:

  Q1 (nonlinear): does a quadratic expansion of [field_before, corr] extract
      signal the LINEAR kernel leaves on the table?
  Q2 (identity): does giving the exact source/target pair (one-hot) beat the
      sign-only ternary correlation? i.e., does ternarization lose identity
      info that matters?

Honest prior: the generator is LINEAR in field_before and corr is already
{-1,0,+1}, so Q1 should answer "no" (linear sufficient). Q2 asks whether
sign-only loses predictive identity — if ternary ≈ identity ≈ oracle, the
3-state codec carries essentially all the signal, which is the thesis.

Verdict (pre-registered): KEEP iff the simple linear ternary kernel is
SUFFICIENT — i.e. neither nonlinear nor exact-identity improves on it by
>= 2% relative. KILL if a more expressive model extracts real signal the
ternary kernel missed.
"""
from __future__ import annotations

import json

import numpy as np

from tools.transition_kernel import make_tripartite_transitions, SEED


def mse(y, p):
    return float(np.mean((y - p) ** 2))


def linfit(X, y):
    W, *_ = np.linalg.lstsq(X, y, rcond=None)
    return W


def oh(idx, n):
    m = np.zeros((len(idx), n), np.float32)
    m[np.arange(len(idx)), idx] = 1.0
    return m


def main() -> dict:
    fb, corr, diff_n, fa, ids, src, tgt = make_tripartite_transitions(
        n_agents=8, field_dim=32, n_steps=4000, push=0.5, noise=0.1, seed=SEED,
        return_pairs=True)
    c = corr.astype(np.float32)
    split = int(0.8 * len(fb))
    tr, te = slice(0, split), slice(split, None)

    ones_tr = np.ones((len(fb[tr]), 1), np.float32)
    ones_te = np.ones((len(fb[te]), 1), np.float32)

    # D19 reference: linear ternary kernel
    X_lin_tr = np.hstack([fb[tr], c[tr], ones_tr])
    X_lin_te = np.hstack([fb[te], c[te], ones_te])
    lin_mse = mse(fa[te], X_lin_te @ linfit(X_lin_tr, fa[tr]))

    # Q1: quadratic expansion
    X_q_tr = np.hstack([fb[tr], c[tr], fb[tr] ** 2, c[tr] ** 2, fb[tr] * c[tr], ones_tr])
    X_q_te = np.hstack([fb[te], c[te], fb[te] ** 2, c[te] ** 2, fb[te] * c[te], ones_te])
    quad_mse = mse(fa[te], X_q_te @ linfit(X_q_tr, fa[tr]))

    # Q2: identity (one-hot pair)
    X_i_tr = np.hstack([fb[tr], c[tr], oh(src[tr], 8), oh(tgt[tr], 8), ones_tr])
    X_i_te = np.hstack([fb[te], c[te], oh(src[te], 8), oh(tgt[te], 8), ones_te])
    id_mse = mse(fa[te], X_i_te @ linfit(X_i_tr, fa[tr]))

    # oracle reference (continuous diff)
    X_o_tr = np.hstack([fb[tr], diff_n[tr], ones_tr])
    X_o_te = np.hstack([fb[te], diff_n[te], ones_te])
    or_mse = mse(fa[te], X_o_te @ linfit(X_o_tr, fa[tr]))

    rel_quad = (lin_mse - quad_mse) / lin_mse
    rel_id = (lin_mse - id_mse) / lin_mse
    sufficient = (rel_quad < 0.02) and (rel_id < 0.02)
    verdict = "KEEP" if sufficient else "KILL"
    reason = (
        f"linear {lin_mse:.4f}; nonlinear {quad_mse:.4f} ({rel_quad:+.3f} rel); "
        f"identity {id_mse:.4f} ({rel_id:+.3f} rel); oracle {or_mse:.4f} — "
        f"{'neither improves >= 2%: ternary kernel sufficient' if sufficient else 'a more expressive model wins: ternary kernel leaves signal on the table'}"
    )
    return {
        "experiment": "D20 transitional-jepa ablation (nonlinear + identity)",
        "seed": SEED,
        "heldout_mse": {
            "linear_ternary": lin_mse,
            "nonlinear_quadratic": quad_mse,
            "identity_onehot": id_mse,
            "oracle_continuous": or_mse,
        },
        "rel_gain_nonlinear": rel_quad,
        "rel_gain_identity": rel_id,
        "verdict": verdict,
        "reason": reason,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
