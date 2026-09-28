"""d19_transitional_jepa.py — does ternary correlation carry transition signal?

Falsifies one clean claim using the relational transition kernel:

  CLAIM: the acting edge's ternary correlation (the D18 "consistent
  relational target", in the codec's {-1,0,+1} alphabet) carries predictive
  signal for the next field-state, beyond what Markov-1 (field-before alone)
  recovers.

Held-out MSE comparison:
  markov1        — field_before alone (floor)
  jepa           — field_before + ternary correlation
  oracle         — field_before + continuous id-difference (ceiling)
  jepa_shuffled  — field_before + row-shuffled correlation (negative control)

Verdict: KEEP if jepa beats markov1 AND the shuffled control collapses back
to markov1's level; KILL otherwise.
"""
from __future__ import annotations

import json

import numpy as np

from tools.transition_kernel import (
    Markov1, TransitionPredictor, make_tripartite_transitions, SEED,
)


def mse(y_true, y_pred):
    return float(np.mean((y_true - y_pred) ** 2))


def main() -> dict:
    fb, corr, diff_n, fa, ids = make_tripartite_transitions(
        n_agents=8, field_dim=32, n_steps=4000, push=0.5, noise=0.1, seed=SEED)

    split = int(0.8 * len(fb))
    tr, te = slice(0, split), slice(split, None)

    markov = Markov1().fit(fb[tr], fa[tr])
    jepa = TransitionPredictor().fit(fb[tr], corr[tr].astype(np.float32), fa[tr])
    oracle = TransitionPredictor().fit(fb[tr], diff_n[tr], fa[tr])

    # negative control: shuffle the correlation rows (break corr <-> field link)
    rng = np.random.default_rng(SEED)
    shuf = corr.copy()
    rng.shuffle(shuf)
    jepa_shuf = TransitionPredictor().fit(fb[tr], shuf[tr].astype(np.float32), fa[tr])

    markov_mse = mse(fa[te], markov.predict(fb[te]))
    jepa_mse = mse(fa[te], jepa.predict(fb[te], corr[te].astype(np.float32)))
    oracle_mse = mse(fa[te], oracle.predict(fb[te], diff_n[te]))
    shuf_mse = mse(fa[te], jepa_shuf.predict(fb[te], shuf[te].astype(np.float32)))

    signal = markov_mse - jepa_mse
    ternarization_cost = jepa_mse - oracle_mse
    # control holds if shuffling destroys most of the win (>= 50% of signal)
    control_ok = (shuf_mse - jepa_mse) >= 0.5 * signal

    verdict = "KEEP" if (signal > 0 and control_ok) else "KILL"
    reason = (
        f"ternary corr MSE {jepa_mse:.4f} vs markov1 {markov_mse:.4f} "
        f"(signal {signal:.4f}); oracle {oracle_mse:.4f} (ternarization cost "
        f"{ternarization_cost:.4f}); shuffled control {shuf_mse:.4f} "
        f"(control_ok={control_ok})"
    )
    return {
        "experiment": "D19 transitional-jepa (relational transition kernel)",
        "seed": SEED,
        "n_agents": 8, "field_dim": 32, "n_steps": 4000,
        "heldout_mse": {
            "markov1": markov_mse,
            "jepa_ternary": jepa_mse,
            "oracle_continuous": oracle_mse,
            "jepa_shuffled": shuf_mse,
        },
        "signal_gain": signal,
        "ternarization_cost": ternarization_cost,
        "control_ok": bool(control_ok),
        "verdict": verdict,
        "reason": reason,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
