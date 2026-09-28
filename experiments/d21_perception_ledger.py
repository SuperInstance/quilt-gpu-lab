"""d21_perception_ledger.py — falsification of the superinstance-old identity
`imbalance ≡ d_mu` ("perception IS the ledger") on real receipt-chain data.

CLAIM UNDER TEST (research/2026-09-27-superinstance-old.md, 2026-09-27):
  "the cell-ledger's imbalance metric (`imbalance ≡ d_mu`) is mathematically
  identical to the elephant's field-edge delta between before and after a
  room event ... the room's temperature *is* the substrate's transaction
  history."
Stated UNCONDITIONALLY: ledger surprise and perception delta are "two sides
of the same currency", the SAME NUMBER per edge.

The careful form it compresses (quilt-rust/docs/field-edge-ledger-bridge.md):
  identity 1:  imbalance² = (‖a‖−‖b‖)² + ‖a‖‖b‖·d_mu²   (exact, always)
  identity 4:  ‖before‖ = ‖after‖ = 1  ⟹  imbalance ≡ d_mu   (unit collapse ONLY)
i.e. the identity is CONDITIONAL on unit-norm states; otherwise the scalar
imbalance conflates radial (magnitude) and directional drift and strictly
dominates d_mu. D21 measures which world the real data lives in.

CONCRETE DEFINITIONS
  ledger cell state x    : the raw field vector sealed per ledger entry.
  imbalance (quilt wire) : ‖x_after − x_before‖₂   (op_d, persistence prior
                           `expected = before` — ledger.rs / quilt-compat/1;
                           first edge of a room books nothing: null prior).
  d_mu (elephant vmf.py) : ‖x_after/‖x_after‖ − x_before/‖x_before‖‖₂
                           (unit-direction chord, elephant/vmf.py L215).
  kernel surprise        : ‖x_after − [x_before, corr, 1]@W‖₂ — the ledger's
                           learned prior (record_with(expected)); the
                           D19/TransitionPredictor relational kernel, seed 2718.

ROOMS (heldout edges only; 80/20 split, seed 2718)
  A "kernel" : make_tripartite_transitions(seed=2718, 4000 steps, d=32) —
               the relational transition kernel's own room (D19 config).
  B "harbor" : REAL receipt chain, probes.jsonl — 215 content-addressed
               canon/distortion probes, every probe's sha256 seal verified
               (sha256 of canonical JSON sans seal). Room field = cumulative
               (dock × cargo) slot counts over the 6×6 harbor grid; each
               probe = one message push (one-hot) → 214 before→after edges;
               the zero-prior first edge books nothing (214 → 213).
               Acting-edge ternary feature: sign(id_dock − id_cargo) with
               content-addressed identities (sha256 bytes → N(0,1)-style
               32-dim vectors, deterministic).

PRE-REGISTERED GATES (fixed before running; this file is the registration)
  G1 decomposition validity : identity-1 residual
        max |imb² − ((‖a‖−‖b‖)² + ‖a‖‖b‖·d_mu²)| / imb²  ≤ 1e-9  in BOTH rooms;
      else verdict = INVALID (definitions mis-implemented, numbers void).
  G2 sensitivity control    : on the unit-projected kernel room (all states
      normalized to the sphere before sealing) the claim MUST hold:
        max |imb − d_mu| / imb ≤ 1e-9;
      else verdict = INVALID (the harness cannot detect identity when it
      exists, so a KILL would be meaningless).
  G3 THE CLAIM              : imbalance ≡ d_mu on heldout edges of BOTH real
      rooms ⟺ max |imb − d_mu| / imb ≤ 1e-9 → KEEP, else KILL.

  (1e-9 = float64 slack around the 1e-12 golden-vector standard.)

OBSERVATIONS (booked either way, not gated)
  O0 precision note : measurements run in float64 (the bridge_demo.py golden
      standard); float32 state storage limits raw-numpy residuals to ~1e-6 —
      booked alongside so the KILL can't be mistaken for a precision artifact
      (claim deviation is ~0.96, six orders larger).
  O1 radial share  : mean (‖a‖−‖b‖)² / imb² — how much of the ledger's
      scalar surprise the direction-only field never sees.
  O2 Spearman ρ(imbalance, d_mu) — is perception at least a MONOTONE proxy
      of the ledger ("same currency" rescue, still not identity)?
  O3 kernel surprise vs d_mu — learned-prior ledger vs perception delta.

VERDICT: INVALID if G1 or G2 fails; KEEP iff G3 passes; else KILL.

CPU-only, numpy/stdlib, deterministic (seed 2718).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.transition_kernel import (  # noqa: E402
    SEED, TransitionPredictor, make_tripartite_transitions,
)

EPS_GATE = 1e-9
FIELD_DIM = 32


def mse(y, p):
    return float(np.mean((y - p) ** 2))


def unit(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.maximum(n, 1e-12)


def imbalance(before, after):
    """Quilt wire imbalance (op_d, persistence prior): ‖after − before‖."""
    return np.linalg.norm(after - before, axis=-1)


def d_mu(before, after):
    """Elephant field-edge delta (vmf.py): unit-direction chord ‖μ̂a − μ̂b‖."""
    return np.linalg.norm(unit(after) - unit(before), axis=-1)


def identity1_residual(before, after, imb, dm):
    """|imb² − ((‖a‖−‖b‖)² + ‖a‖‖b‖ d_mu²)| / imb²  (bridge identity 1)."""
    na, nb = np.linalg.norm(after, axis=-1), np.linalg.norm(before, axis=-1)
    pred = (na - nb) ** 2 + na * nb * dm ** 2
    return np.abs(imb ** 2 - pred) / np.maximum(imb ** 2, 1e-12)


def radial_share(before, after, imb):
    na, nb = np.linalg.norm(after, axis=-1), np.linalg.norm(before, axis=-1)
    return (na - nb) ** 2 / np.maximum(imb ** 2, 1e-12)


def spearman(x, y):
    """Pure-numpy Spearman (average ranks, Pearson on ranks); None if either
    side is constant — an honest 'undefined', not a fake number."""
    def ranks(v):
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v), float)
        sv = v[order]
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and sv[j + 1] == sv[i]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return r
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    rx, ry = ranks(np.asarray(x, float)), ranks(np.asarray(y, float))
    rx -= rx.mean(); ry -= ry.mean()
    den = math.sqrt(float((rx ** 2).sum()) * float((ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den > 0 else None


def id_vector(name: str) -> np.ndarray:
    """Content-addressed agent identity: sha256(name) bytes -> N(0,1)-ish
    32-dim float32 vector (deterministic, no RNG state shared)."""
    digest = hashlib.sha256(name.encode()).digest()
    buf = digest * (FIELD_DIM * 4 // len(digest) + 1)
    words = np.frombuffer(buf[: FIELD_DIM * 4], np.uint32)
    u = (words.astype(np.float32) + 0.5) / 2.0 ** 32
    return (math.sqrt(12.0) * (u - 0.5)).astype(np.float32)


def harbor_room():
    """Real receipt-chain room from probes.jsonl.

    Returns (before, corr, after) with before/after cumulative (dock×cargo)
    count vectors and corr = ternary_correlation(id_dock, id_cargo) of the
    acting edge. The first edge (null prior) books nothing.
    """
    probes = []
    for line in (ROOT / "probes.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        seal = p.pop("sha256")
        ok = hashlib.sha256(
            json.dumps(p, sort_keys=True).encode()).hexdigest() == seal
        if not ok:
            raise ValueError(f"receipt chain BROKEN at probe: {p}")
        probes.append(p)

    docks = sorted({p["dock"] for p in probes})
    cargos = sorted({p["cargo"] for p in probes})
    slot = {(d, c): docks.index(d) * len(cargos) + cargos.index(c)
            for d in docks for c in cargos}
    n_slots = len(docks) * len(cargos)

    ids = {name: id_vector(name) for name in docks + cargos}
    from tools.transition_kernel import ternary_correlation
    deadband = 0.15

    state = np.zeros(n_slots, np.float32)
    before, corr, after = [], [], []
    for p in probes:
        s = slot[(p["dock"], p["cargo"])]
        push = np.zeros(n_slots, np.float32)
        push[s] = 1.0
        c = ternary_correlation(ids[p["dock"]], ids[p["cargo"]], deadband)
        if np.linalg.norm(state) > 0:  # null prior books nothing
            before.append(state.copy())
            corr.append(c)
            after.append(state + push)
        state = state + push

    return (np.asarray(before), np.asarray(corr, np.int8),
            np.asarray(after), len(probes))


def fit_kernel(before, corr, after):
    split = int(0.8 * len(before))
    tr, te = slice(0, split), slice(split, None)
    k = TransitionPredictor().fit(
        before[tr], corr[tr].astype(np.float32), after[tr])
    return k, tr, te


def measure(before, after):
    """All gate math in float64 (golden-vector standard)."""
    b = np.asarray(before, np.float64)
    a = np.asarray(after, np.float64)
    imb, dm = imbalance(b, a), d_mu(b, a)
    out = {
        "n_heldout": int(len(b)),
        "imbalance_mean": float(imb.mean()),
        "d_mu_mean": float(dm.mean()),
        "max_rel_dev": float(np.max(np.abs(imb - dm) / np.maximum(imb, 1e-12))),
        "identity1_residual_max": float(identity1_residual(b, a, imb, dm).max()),
        "radial_share_mean": float(radial_share(b, a, imb).mean()),
        "spearman_imb_dmu": spearman(imb, dm),
    }
    return out


def main() -> dict:
    # ---- Room A: the kernel's own room (D19 config) ----------------------
    fb, corr, diff_n, fa, ids = make_tripartite_transitions(
        n_agents=8, field_dim=FIELD_DIM, n_steps=4000, push=0.5, noise=0.1,
        seed=SEED)
    kA, trA, teA = fit_kernel(fb, corr, fa)
    roomA = measure(fb[teA], fa[teA])
    roomA["kernel_surprise_mean"] = float(np.linalg.norm(
        fa[teA].astype(np.float64)
        - kA.predict(fb[teA], corr[teA].astype(np.float32)).astype(np.float64),
        axis=-1).mean())

    # ---- Room B: the REAL harbor receipt chain ---------------------------
    hb, hc, ha, n_probes = harbor_room()
    kB, trB, teB = fit_kernel(hb, hc, ha)
    roomB = measure(hb[teB], ha[teB])
    roomB.update({
        "n_probes_sealed": n_probes,
        "n_edges": int(len(hb)),
        "kernel_surprise_mean": float(np.linalg.norm(
            ha[teB].astype(np.float64)
            - kB.predict(hb[teB], hc[teB].astype(np.float32)).astype(np.float64),
            axis=-1).mean()),
    })

    # ---- G2 sensitivity control: unit-collapse room (identity 4) ---------
    bu, au = unit(np.asarray(fb[teA], np.float64)), unit(np.asarray(fa[teA], np.float64))
    imbu, dmu = imbalance(bu, au), d_mu(bu, au)
    ctrl = float(np.max(np.abs(imbu - dmu) / np.maximum(imbu, 1e-12)))
    g2 = bool(ctrl <= EPS_GATE)

    # float32 raw-storage residual scale, booked as O0 (precision context)
    b32, a32 = fb[teA], fa[teA]
    i32, d32 = imbalance(b32, a32), d_mu(b32, a32)
    f32_resid = float(identity1_residual(b32, a32, i32, d32).max())

    # ---- Pre-registered gates --------------------------------------------
    resid = max(roomA["identity1_residual_max"], roomB["identity1_residual_max"])
    g1 = bool(resid <= EPS_GATE)
    g3 = bool(max(roomA["max_rel_dev"], roomB["max_rel_dev"]) <= EPS_GATE)

    if not (g1 and g2):
        verdict = "INVALID"
        reason = (f"controls failed: G1(decomposition)={g1} "
                  f"(residual {resid:.3e}), G2(unit-collapse control)={g2} "
                  "— numbers are void, fix the harness")
    elif g3:
        verdict = "KEEP"
        reason = (f"imbalance ≡ d_mu holds on real edges: max rel dev "
                  f"{max(roomA['max_rel_dev'], roomB['max_rel_dev']):.3e} "
                  f"≤ {EPS_GATE:g}")
    else:
        verdict = "KILL"
        reason = (
            f"identity is CONDITIONAL, not unconditional: max |imb−d_mu|/imb = "
            f"{roomA['max_rel_dev']:.4f} (kernel room) and "
            f"{roomB['max_rel_dev']:.4f} (harbor receipt chain) ≫ "
            f"{EPS_GATE:g}; unit-collapse control passes "
            f"(G2, {ctrl:.1e}) and identity-1 decomposition is exact (G1 "
            f"residual {resid:.2e}), so the gap is real radial+directional "
            f"divergence, not harness error")

    return {
        "experiment": "D21 perception=ledger (imbalance ≡ d_mu falsification)",
        "seed": SEED,
        "device": "cpu",
        "claim": "superinstance-old: quilt ledger imbalance ≡ elephant field-edge d_mu (unconditional)",
        "definitions": {
            "imbalance": "‖x_after − x_before‖₂ (quilt wire op_d, persistence prior)",
            "d_mu": "‖x_after/‖x_after‖ − x_before/‖x_before‖‖₂ (elephant vmf.py unit-direction chord)",
            "kernel_surprise": "‖x_after − [x_before,corr,1]@W‖₂ (learned prior, TransitionPredictor seed 2718)",
        },
        "gates": {
            "G1_decomposition_exact_le_1e-9": g1,
            "G2_unit_collapse_control_le_1e-9": g2,
            "G3_claim_identity_le_1e-9_both_rooms": g3,
        },
        "unit_collapse_control": {"max_rel_dev": ctrl},
        "precision_note_O0": {
            "measurement_dtype": "float64",
            "float32_raw_storage_identity1_residual_max": f32_resid,
            "note": "float32 storage alone caps raw residuals near 1e-6; "
                    "float64 gate math is the golden-standard basis",
        },
        "room_A_kernel": roomA,
        "room_B_harbor_receipt_chain": roomB,
        "verdict": verdict,
        "reason": reason,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
