"""transition_kernel.py — the relational transition kernel.

The "Transitional JEPA" primitive (Casey's 2026-09-27 synthesis).

Three threads converge here:
1. D13d/D18 — the relational target is found by CORRELATION, not reward;
   the ternary codec {-1,0,+1} is the fleet's native signal alphabet
   (D14 timbre, D17 compression).
2. Elephant / JEPA — perception is a ROOM's temperature sense: a field, not
   a stream; the unit is the field-EDGE (before -> after).
3. SuperInstance old->new survey — the elephant's room-temperature sense and
   the quilt cell-ledger's transaction imbalance are the SAME currency
   (`imbalance ≡ d_mu` = field-edge delta). Perception IS the ledger.

The kernel makes that operational: predict the field-AFTER a transition from
the field-before plus the acting edge's TERNARY correlation (the relational
"who pulled whom" signal), with persistent per-agent identity.

Deliberately minimal and CPU-only (numpy) so it runs while the GPU serves
heavier lanes. Deterministic: seed passed in (lab rule = 2718).
"""
from __future__ import annotations

import numpy as np

SEED = 2718


def ternary_correlation(id_a: np.ndarray, id_b: np.ndarray,
                        deadband: float = 0.15) -> np.ndarray:
    """Ternary correlation between two agent identities: sign(id_a - id_b).

    dims within `deadband` of each other read 0 (the codec's third state), so
    near-equal dimensions are explicitly "no signal" rather than noise.
    Returns int8 in {-1, 0, +1}^d.
    """
    d = id_a - id_b
    return np.where(np.abs(d) <= deadband, 0, np.sign(d)).astype(np.int8)


class Markov1:
    """Baseline: predict field_after from field_before alone (no relational
    context). Linear least squares. The honest floor the kernel must beat."""

    def __init__(self):
        self.W = None

    def _X(self, fb):
        return np.hstack([fb, np.ones((len(fb), 1), dtype=fb.dtype)])

    def fit(self, field_before, field_after):
        self.W, *_ = np.linalg.lstsq(self._X(field_before), field_after, rcond=None)
        return self

    def predict(self, field_before):
        return self._X(field_before) @ self.W


class TransitionPredictor:
    """Transitional-JEPA predictor: field_after ~ [field_before, feature, 1] @ W.

    `feature` is the relational context of the acting edge. Pass the TERNARY
    correlation for the kernel; pass the continuous id-difference for the
    oracle. Same model class, differing only in the feature — so the gap
    between them is exactly the information cost of ternarization."""

    def __init__(self):
        self.W = None

    def _X(self, fb, feat):
        return np.hstack([fb, feat, np.ones((len(fb), 1), dtype=fb.dtype)])

    def fit(self, field_before, feat, field_after):
        self.W, *_ = np.linalg.lstsq(self._X(field_before, feat), field_after, rcond=None)
        return self

    def predict(self, field_before, feat):
        return self._X(field_before, feat) @ self.W


def make_tripartite_transitions(n_agents=8, field_dim=32, n_steps=4000,
                                push=0.5, noise=0.1, seed=SEED,
                                return_pairs: bool = False):
    """Synthesize field-state transitions on a tripartite-style agent graph.

    Each agent has a persistent identity id_i ~ N(0,1)^field_dim. A step picks
    an ordered source->target pair and pushes the field toward the
    (id_source - id_target) direction. The kernel sees only the TERNARY sign of
    that difference — strictly less information than the generator — so the
    test measures how much relational signal survives ternarization.

    Returns (field_before, corr, diff_n, field_after, ids):
      field_before: (n_steps, field_dim) float32
      corr:         (n_steps, field_dim) int8   in {-1,0,+1}
      diff_n:       (n_steps, field_dim) float32  (continuous, oracle-only)
      field_after:  (n_steps, field_dim) float32
      ids:          (n_agents, field_dim) float32
    """
    rng = np.random.default_rng(seed)
    ids = rng.standard_normal((n_agents, field_dim)).astype(np.float32)
    src = rng.integers(0, n_agents, size=n_steps)
    tgt = rng.integers(0, n_agents, size=n_steps)
    tgt = np.where(tgt == src, (tgt + 1) % n_agents, tgt)  # no self-edges
    field_before = rng.standard_normal((n_steps, field_dim)).astype(np.float32)
    diff = (ids[src] - ids[tgt]).astype(np.float32)
    diff_n = diff / (np.linalg.norm(diff, axis=1, keepdims=True) + 1e-6)
    eps = noise * rng.standard_normal((n_steps, field_dim)).astype(np.float32)
    field_after = 0.5 * field_before + push * diff_n + eps
    corr = ternary_correlation(ids[src], ids[tgt])
    if return_pairs:
        return field_before, corr, diff_n, field_after, ids, src, tgt
    return field_before, corr, diff_n, field_after, ids
