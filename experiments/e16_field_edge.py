#!/usr/bin/env python3
"""E16 — field-edge (transitional) dial read: is the CHANGE more readable than
the state?

CLAIM UNDER TEST (concrete, falsifiable)
  E12 (experiments/e12_room_dial_reader.py) returned KEEP: a frozen I-JEPA
  linearly READS the elephant's dials (mood/volume/presence) off staged lavfi
  rooms — R2_still_loro(k=64) = 0.81 / 0.96 / 0.95. E13 then narrowed that read
  to a moderate nonlinear carrier, and E18 asks the same question about the
  CONTRAST between two arbitrary rooms (the sauna/plunge gap). E16 asks the
  elephant's core doctrine, verbatim (SPOOL.E16): "the walk between rooms is
  the only lesson" —

      does the read capture the CHANGE (field_before -> field_after, the
      delta-dial) MORE than static state?

  Concretely: a FIELD-EDGE is a step of a temporal walk through the staged
  room bank. Its target is the dial DELTA, delta = dial_B - dial_A, read from
  embedding-pair features (both endpoints concatenated AND the signed
  difference). The claim is SUPER-ADDITIVITY ON THE EDGE: the delta read beats
  (a) the static single-room dial read and (b) the two-absolutes baseline
  (delta = the two rooms' own out-of-fold absolute reads, differenced) on
  >= 2 of 3 dials.
  KEEP = edge > both comparators (+ its own shuffle null) on >= 2/3 dials —
      the walk carries signal the rooms do not.
  KILL = edge <= the two-absolutes baseline on >= 2/3 dials — the change is
      just the two states differenced; static state IS everything.
  INVALID_STAGING = the carrier certificate fails (dead or non-injective
      staged carrier, or the scripts stopped moving the dials).
  A KILL is a win (a claim died honestly); INVALID_* always means the arm
  tested nothing and is NEVER reported as a KILL.

WHAT IS NEW HERE (and what is deliberately reused)
  Reused by import, no fork: E12's bank/staging/probe (mood/volume/presence
  DIAL_NAMES, the 27-cell grid, stage_transcript -> the REAL elephant DialBank
  readings as labels, PCA basis, grouped ridge, permutation null, LORO);
  E13's `build_bank` + Arm-L linear carrier + `collect_arm` + `carrier_
  certificate` + `mirror_check`; E18's pair machinery (the leave-one-ROOM-out
  probe over pair-index arrays, the two-absolutes baselines, the pair feature
  arms, the room-level permutation null). E16 adds exactly two things:

  1. THE FIELD-EDGE BANK. E18's sample was ALL C(27,2) = 351 room pairs — a
     spatial CONTRAST between any two rooms. E16's sample is the steps of a
     TEMPORAL WALK: 8 deterministic walks over the same 27-cell dial grid
     (4 pure stride-1 serpentines = "the local walk", 4 seeded greedy
     nearest-neighbour walks with strides 1..3 = "the walk with jumps"),
     26 steps each = 208 directed edges (A before -> B after). An edge is a
     transition the field actually takes, and the walk ensemble is frozen
     before the run. That sample difference is the experiment: E16 tests
     whether the READ of a transition beats the read of the states, and the
     stride-bucket control (below) says how much of it is the walk's locality
     and how much is just room-pair contrast.
  2. THE TEMPORAL DESIGN CHECKS that only make sense for directed edges:
     stride-bucket R2 (local step vs jump), reverse-edge invariance (the
     directedness must be a pure sign/block relabelling), the all-pairs
     control (the same reader on E18's 351-pair sample — is the walk sample
     harder/easier than arbitrary contrast?), and the sum control (if the pair
     reader reads the SUM of the two endpoints as well as their difference, it
     is reading two states, not the change).

DEFINITIONS
  bank            : E13's `build_bank(1)` verbatim — E12's 27-cell dial grid
                    (m in {-0.8,0,0.8}, v,p in {0.15,0.50,0.85}), one staged
                    script per room, target triple booked alongside, and the
                    dial LABELS read by the REAL elephant DialBank (never
                    typed). Rendered through E13's Arm-L carrier = E12's
                    `stage_source` formulas (audited by the Arm-L mirror check).
  walk            : a Hamiltonian ordering of the 27 cells. Serpentines change
                    exactly ONE dial by one grid level per step (the local
                    walk); greedy walks occasionally jump 2-3 levels.
  field-edge      : (A, B) = two CONSECUTIVE states of one walk, directed in
                    walk order. A is field_before, B is field_after.
  edge target     : PRIMARY = the ELEPHANT-LABEL delta label_B - label_A
                    (the delta-dial the doctrine is about); the design-target
                    delta (target_B - target_A) is booked and read alongside.
  room feature    : E12/E18's room-level convention — PCA basis fit
                    label-free on the 324 still embeddings (top K_WIDE=256),
                    each room's 12 stills averaged IN that space. Width
                    k = 13 = min(K_PRIMARY=64, 27//2) = E12's room-level
                    overdetermination rule (PRIMARY); sweep {6, 13, 20}.
  pair features   : arms, all ridge, all multi-output (3 dials at once)
                      concat = [z_A, z_B]                (2k)
                      diff   = z_B - z_A                 (k)  — the walk alone
                      pair   = [z_A, z_B, z_B - z_A]     (3k) — PRIMARY (as tasked)
  comparators     : (a) static single-room absolute dial read at the SAME
                    room-level representation/width (E12's room-level LORO);
                    (b) two-absolutes baseline = the two out-of-fold absolute
                    predictions differenced (`two_abs_loo`), plus the
                    CONSERVATIVE in-fold variant `two_abs_fold` (booked).
                    E12's still-level k=64 headline is replicated in-run and
                    booked as the strict comparator (`strict_pass`, reported,
                    not gated): the still-level and room-level numbers are
                    computed on different units (12 stills/room vs 1 room
                    mean) and gating a room-level delta read against a
                    still-level absolute read would be an uninterpretable
                    comparison — pre-registered deviation, E18's convention.

CRITICAL CV DESIGN (pre-registered BEFORE the run)
  208 directed edges over 27 rooms. Leave-one-EDGE-out is FORBIDDEN: a
  held-out edge shares rooms with training edges, so it would measure "predict
  a transition between rooms I have already seen in other transitions", not
  "predict a transition involving an UNSEEN room" — which is the claim, and
  the only split under which the two-absolutes baseline is definable. The outer
  CV is therefore LEAVE-ONE-ROOM-OUT ON ROOMS:
      for each held-out room h (27 folds):
          test  = EVERY edge touching h (either endpoint)   -> ~15 edges
          train = every edge among the other 26 rooms       -> ~193 edges
      i.e. no room appears in ANY training edge of the fold it is tested on.
  Asserted structurally at run time (`edge_fold_structure_check`): per fold
  every test edge touches h, no train edge does, test/train partition the edge
  set, and no edge is both. A booked leak probe also runs the primary arm under
  a random 80/20 EDGE split (never gated) — the inflation is the run-time
  evidence for the room-level CV.
  Inner lambda selection is ALSO grouped on rooms (E18's `pair_pick_lambda`):
  inside each outer fold, for each training room g the inner-test is every
  training edge touching g and the inner-train is the rest (26 inner folds x 6
  lambdas, one SVD per inner fold via e12's `_ridge_path_pred` many-lambda
  trick).
  PCA basis: label-free, fit once on all still embeddings, frozen for every
  fold and arm — no label ever enters the basis.
  Null: 200 ROOM-LEVEL label shuffles — permute the 27 label triples across
  rooms, rebuild the edge deltas from the permuted triples, rerun the SAME
  LORO edge probe at the fold-median lambda. The embedding pairing is left
  intact (the shuffle destroys only the room -> dial correspondence), exactly
  E12's room-level null lifted to edges.

PRE-REGISTERED GATES (fixed before running; this file IS the registration)
  G0d harness self-test : CPU-only, synthetic (the SAME 27 cells, a synthetic
      embedding in which the dials are exactly linear, 2% still noise): the
      imported pair+LORO machinery on THIS walk-edge set must read the
      synthetic delta at R2 >= 0.90 per dial, a room-shuffled control must
      collapse below 0.10, and the edge fold structure must assert clean.
      Carrier-free and model-free.
  G0a staging fidelity  : Spearman(target, elephant_label) >= 0.5 for >= 2/3
      dials on the shared bank — E12's G0a verbatim.
  G0c carrier certificate : E13's `carrier_certificate` on this bank's knob
      matrix, gated on its LIVENESS half only: the 27 knob vectors are
      pairwise distinct/injective AND >= 2 of 3 dials show distance-correlation
      p <= 0.05 against a 200-shuffle null AND 3-NN LOO-R2 >= 0.20, AND the
      Arm-L mirror check reproduces e12.stage_source's lavfi string. Both
      halves are reported, but NON-AFFINITY IS DELIBERATELY NOT GATED: E16
      uses E12's LINEAR carrier (E13 measured its curvature at 0.000 by
      construction), so gating non-affinity would invalidate by construction.
      Deviation from E13 pre-registered here (E18's convention).
  G0b sensitivity       : G0b.1 — E12's control verbatim: the still-level
      k=64 LORO read of per-still mean luminance R2 >= 0.90 (E12 measured
      0.993). G0b.2 — the EDGE machinery's own control: the SAME LORO edge
      probe reading the mean-luminance DELTA (lum_B - lum_A) at the primary
      width must reach EDGE_SENSITIVITY_FLOOR = 0.50 and beat its own null95.
      The lower floor is pre-registered because a DIFFERENCE of the same
      signal shares strictly less variance than the absolute target (the
      delta/absolute std ratio is booked per dial in edge_composition).
  G0e E12 replication   : in-run replication of E12's own gate at the still
      level — >= 2/3 dials with R2_still_loro(k=64) >= R2_FLOOR = 0.30. If
      E12's read does not reproduce here, the (a)/(b) comparators are
      meaningless in this run (E13's INVALID_CONTROL lesson, applied).
  G1 THE CLAIM (KEEP)   : on the PRIMARY arm ("pair") at k = 13, primary
      targeting the LABEL delta:
        exceed_d := edge_R2(d) > single_room_abs_R2(d)   (comparator a, room level)
                    AND edge_R2(d) > two_abs_loo_R2(d)   (comparator b)
                    AND edge_R2(d) > null95_d            (the edge's own null)
      KEEP = exceed_d for >= 2 of 3 dials.
      Booked alongside per dial: whether it also beats E12's still-level k=64
      headline (`strict_pass_still_level`) and the conservative baseline
      `two_abs_fold`.
  G2 INCONCLUSIVE       : exactly 1 dial exceeds both comparators and the
      null, or mean edge_R2 > mean null95.
  G3 KILL               : at most 1 dial beats the two-absolutes baseline
      (i.e. >= 2/3 dials: edge_R2 <= two_abs_loo_R2) — the edge read is not
      super-additive; the change is the two states differenced.
      (mean_edge_r2 vs mean_null95 is BOOKED and does not rescue a KILL: the
      pre-registered lane is the baseline comparison.)
  INVALID_STAGING       : G0a or G0c fails.
  INVALID_HARNESS       : G0d, G0b or G0e fails.
  ABORTED               : guard preflight, model load, no frames, < 8 rooms, or
      an empty/degenerate edge set.

CONTROLS / BOOKED (never gated)
  C1 raw-pixel edge probe : the same LORO edge read on the ROOM-MEAN 16x9
      grayscale stills (144-d), PCA-reduced label-free to the SAME width as
      the embedding reader (k = 13) so the control is apples-to-apples. If
      pixels beat the embedding, the embedding is losing the change signal
      (E12's C1, lifted to edges).
  C2 luminance-delta Spearman per dial.
  C3 permutation null (200 room shuffles) + p-values for the edge read.
  C4 E12 headline replication: still-level absolute dial R2 at k=16/64 (the
      booked reference numbers 0.81-0.97) alongside the room-level comparators.
  C5 knob ranges + E12's room-identity half-split accuracy (chance 1/27) —
      harness sanity only.
  C6 edge composition: per dial the delta histogram, zero/sign balance,
      delta-vs-absolute std ratio, label-delta Spearman, stride histogram,
      duplicate directed/undirected edge counts, and the count of edges whose
      delta is zero in at least one dial (a serpentine step moves exactly one
      dial, so the other two columns are zero on that edge — honest and
      expected, and the reason the per-dial zero fraction is booked).
  C7 STRIDE BUCKETS (the E16-specific scope control): the out-of-fold edge R2
      restricted to stride-1 edges ("the local walk") vs stride>=2 edges
      ("jumps"). If the read exists only on jumps, the "walk" reading is
      really room-pair contrast — reported, not gated.
  C8 reverse-edge invariance: reversing every edge (A,B) -> (B,A) negates the
      delta and permutes/signs the feature blocks — a pure relabelling, so the
      R2 must reproduce exactly. A mismatch means the fold bookkeeping (not
      the signal) is direction-dependent.
  C9 arm ladder: diff / concat / pair across k in {6,13,20} — which part of
      the pair carries the change. If `diff` alone reads as well as `pair`, the
      reader is genuinely reading the walk; if `concat` is needed, it is
      reading the endpoints.
  C10 all-pairs control: the SAME primary reader on E18's C(27,2)=351-pair
      sample (arbitrary spatial contrast, not walk steps) — is the walk sample
      harder or easier than contrast? Booked; the two samples have different
      sizes and delta distributions, so this is a scope read, not a gate.
  C11 sum control: the same pair reader predicting target_A + target_B. If the
      sum is read as well or better, the pair features are reading "both
      states", not "the change".
  C12 random edge-split leak probe (wrong split, booked).
  C13 extra dials booked by the bank (never gated, not tasked).

HONESTY / CAVEATS BOOKED WITH THE RESULT
  - Carriers are STAGED (E12/E13's caveat, unchanged): this tests staged visual
    carriers of the dials, not arbitrary camera feeds. A KEEP is a floor.
  - Edge R2 and absolute R2 are computed on DIFFERENT sample sets (208 edges vs
    27 rooms) with DIFFERENT target variance, and each R2 is computed against
    its OWN target's mean, so the numbers are comparable but not identical in
    difficulty. The direction is NOT assumed: the measured std ratio (delta
    std / absolute std) is booked per dial in edge_composition, and the
    edge's own null95 anchors every dial.
  - Comparator (b) two_abs_loo differences two OUT-OF-FOLD predictions, so it
    is symmetric between the two endpoints and shares nothing with the pair
    reader's fitting; the in-sample `two_abs_fold` variant is reported too and
    is the harder baseline.
  - The absolute comparators use the SAME room-level representation (room-mean
    of still embeddings in the label-free PCA basis, same width k) as the edge
    reader — apples to apples. E12's still-level headline is booked separately
    and reported as `strict_pass_still_level` (never gated).
  - 208 edges are NOT 208 independent samples (each fold's test edges all share
    the held-out room, and each room enters ~15 edges), which is exactly why
    the outer unit is the room. The effective sample size is ~27 room-level
    draws; ridge lambda is selected per fold to respect that. The walk ensemble
    is 8 walks over 27 cells, so the same directed edge can occur in two walks
    (booked count) — duplicates are different walk steps, not independent
    draws, and the CV holds out rooms, not edges.
  - The 8 walks are a FROZEN design choice (deterministic generators, seeds in
    the file): a different ensemble is a different sample of transitions. The
    stride-bucket control (C7) is what tells the reader how much the result
    depends on the ensemble's local-vs-jump mix.
  - SPOOL.E16's original phrasing suggested a paired-frame renderer ("same
    room, two dial sets") for a genuinely identity-preserving field evolution
    (nuisance dims — occupant positions, noise seed — would cancel in the
    delta). That arm is OUT OF SCOPE here, pre-registered as E16b: it needs
    ~2x the renders (a second state per identity) and an identity-level CV that
    27 identities cannot support at the pre-registered width (39 features on
    26 training edges). This build follows the tasked design: reuse E12's bank
    (its rendered stills and embeddings) and read the CHANGE along a walk over
    it.
  - Presence's carrier (drawn boxes) and volume's (noise amount) both move the
    absolute dials' luminance/contrast correlates; the delta reads inherit
    that (C2 names it).

Dev path: `python -m experiments.e16_field_edge --cpu-only` runs everything
except the encoder — bank, Arm-L carrier + mirror check, certificate, the walk
ensemble and its edge set with the fold-structure check, the harness self-test,
and a labelled plumbing run of every edge arm on the LABEL-FREE KNOB matrix as
a stand-in feature space (no model, no GPU, no claim).
Never writes to results/ and is not wired into runner.EXP_MOD / QUEUE.md.

Verdict printed as ONE JSON object on stdout (progress on stderr).
Deterministic (seed 2718). CPU-only probe; GPU only for the encoder forwards.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# BLAS thread cap — E12's reason, verbatim: the probe does thousands of tiny
# ridge solves (27 outer folds x 26 inner folds x 6 lambdas x arms x widths,
# plus 200 null permutations), and the default thread count turns each 39-d
# solve into a thread storm. Must be set BEFORE numpy loads (and this module
# imports E12/E13/E18, which import numpy).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np  # noqa: E402

try:  # belt-and-braces for callers that imported numpy before this module
    from threadpoolctl import threadpool_limits  # noqa: E402
    _BLAS_LIMIT = threadpool_limits(limits=4)
    _BLAS_LIMIT.__enter__()
except Exception:  # threadpoolctl absent — the env vars above still apply
    _BLAS_LIMIT = None

SEED = 2718
LAB = Path(__file__).resolve().parents[1]
ELEPHANT = Path.home() / "projects" / "elephant"
for _p in (str(LAB), str(LAB / "experiments"), str(ELEPHANT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --------------------------------------------------------------------- #
# E12 is the probe + bank schema, E13 the carrier + collector, E18 the   #
# pair/edge machinery (leave-one-ROOM-out probe over pair-index arrays,  #
# two-absolutes baselines, pair feature arms). E16 forks NONE of them:    #
# it adds the walk-edge SAMPLE and the edge-specific checks.             #
#   probe    : r2_columns, pca_basis, loro_predict, spearman,            #
#              room_halfsplit_acc                                        #
#   carrier  : knobs_linear, build_bank, carrier_certificate,            #
#              mirror_check, collect_arm, knob_ranges                    #
#   edges    : pair_features, pair_loro_predict, pair_perm_null,         #
#              gap_targets, sum_targets, gap_from_abs, abs_room_oof,     #
#              two_abs_fold_gaps, pair_split_leak_probe, pairs_from_rooms #
#   loader   : e9's load_encoder / preflight_guard / N_STILLS            #
# --------------------------------------------------------------------- #
from e12_room_dial_reader import (                            # noqa: E402
    DIAL_NAMES, EXTRA_DIALS, GRID_M, GRID_P, GRID_V, K_PRIMARY, K_STRICT,
    K_WIDE, LAM_GRID, PERMS, R2_FLOOR, SENSITIVITY_FLOOR, loro_predict,
    pca_basis, r2_columns, room_halfsplit_acc, spearman,
)
from e13_nonlinear_dial_reader import (                       # noqa: E402
    build_bank, carrier_certificate, collect_arm, knob_ranges, knobs_linear,
    mirror_check, render_scene,
)
from e18_sauna_plunge_contrast import (                       # noqa: E402
    abs_room_oof, gap_from_abs, gap_targets, pair_features, pair_loro_predict,
    pair_perm_null, pair_split_leak_probe, pairs_from_rooms, r2_dict,
    sum_targets, two_abs_fold_gaps,
)
from e9_ijepa_stills import N_STILLS, load_encoder, preflight_guard  # noqa: E402

# --------------------------------------------------------------------- #
# Pre-registered constants (see the module docstring — this IS the       #
# registration; nothing here is chosen after seeing a result)            #
# --------------------------------------------------------------------- #
CELL_LEVELS = (GRID_M, GRID_V, GRID_P)     # 3 x 3 x 3 = 27 cells
GRID_SHAPE = (3, 3, 3)

# The frozen walk ensemble: 4 stride-1 serpentines ("the local walk") with
# fixed axis orders + 4 seeded greedy nearest-neighbour walks ("the walk with
# jumps", strides 1..3).
SERPENTINE_PERMS = ((0, 1, 2), (1, 2, 0), (2, 0, 1), (0, 2, 1))
GREEDY_STARTS = ((0, 0, 0), (2, 2, 2), (0, 2, 0), (2, 0, 2))
GREEDY_SEEDS = tuple(SEED + 101 + i for i in range(len(GREEDY_STARTS)))
N_WALKS = len(SERPENTINE_PERMS) + len(GREEDY_STARTS)      # 8
STEPS_PER_WALK = 26                                       # 27 cells -> 26 steps
LOCAL_STRIDE_MAX = 1

K_EDGE_PRIMARY = 13      # = min(K_PRIMARY, 27 // 2): E12's room-level rule
K_EDGE_SWEEP = (6, 13, 20)
ARMS = ("diff", "concat", "pair")
PRIMARY_ARM = "pair"
ARM_TITLES = {
    "diff": "the signed walk alone, z_B - z_A",
    "concat": "both endpoints concatenated [z_A, z_B]",
    "pair": "concat + signed difference [z_A, z_B, z_B - z_A] — PRIMARY",
}
EDGE_SENSITIVITY_FLOOR = 0.50   # luminance-DELTA read floor (G0b.2)
E12_REPL_FLOOR = R2_FLOOR       # 0.30, E12's per-dial floor (G0e)
LEAK_SPLIT_FRACTION = 0.80      # booked random edge split (never gated)
GATE_HIT_DIALS = 2              # ">= 2 of 3 dials" everywhere
NULL_BEATS = "strict"           # edge_R2 > null95 (not >=)


def log(msg: str) -> None:
    """Progress goes to stderr; stdout is reserved for the JSON verdict."""
    print(f"[e16] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------- #
# The walk ensemble (the field-edge bank)                                #
# --------------------------------------------------------------------- #
def all_cells() -> list[tuple[int, int, int]]:
    return [(i, j, k) for i in range(GRID_SHAPE[0])
            for j in range(GRID_SHAPE[1]) for k in range(GRID_SHAPE[2])]


def cell_target(cell: tuple[int, int, int]) -> tuple[float, float, float]:
    """Grid cell -> the dial triple it sits on (E12's grid levels)."""
    return (float(CELL_LEVELS[0][cell[0]]), float(CELL_LEVELS[1][cell[1]]),
            float(CELL_LEVELS[2][cell[2]]))


def cell_coords(bank: list) -> list[tuple[int, int, int]]:
    """Each bank room's grid cell (level indices), read off its target triple."""
    coords = []
    for r in bank:
        c = []
        for i, levels in enumerate(CELL_LEVELS):
            d = [abs(float(r["target"][i]) - float(x)) for x in levels]
            c.append(int(np.argmin(d)))
        coords.append(tuple(c))
    return coords


def serpentine_order(perm: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    """A stride-1 Hamiltonian path over the 3x3x3 cell graph.

    Standard 3-D serpentine: the fastest axis alternates direction per row, the
    middle axis alternates per slab. Every consecutive step changes exactly ONE
    axis by exactly one level (asserted by the caller) — this is "the local
    walk", the transition a field takes when one dial moves by one notch.
    """
    seq = []
    for i in range(GRID_SHAPE[0]):
        for j in range(GRID_SHAPE[1]):
            for k in range(GRID_SHAPE[2]):
                kk = k if (i + j) % 2 == 0 else GRID_SHAPE[2] - 1 - k
                jj = j if i % 2 == 0 else GRID_SHAPE[1] - 1 - j
                cell = [0, 0, 0]
                cell[perm[0]] = i
                cell[perm[1]] = jj
                cell[perm[2]] = kk
                seq.append(tuple(cell))
    return seq


def greedy_order(start: tuple[int, int, int], seed: int) -> list[tuple[int, int, int]]:
    """Seeded nearest-neighbour walk over the cell graph — "the walk with
    jumps": each step goes to the nearest unvisited cell, ties broken by a
    frozen RNG. Deterministic given (start, seed)."""
    rng = np.random.default_rng(int(seed))
    remaining = set(all_cells())
    if start not in remaining:
        raise ValueError(f"start {start} not a cell")
    remaining.discard(start)
    order = [start]
    cur = start
    while remaining:
        dists = {c: sum(abs(c[a] - cur[a]) for a in range(3)) for c in remaining}
        best = min(dists.values())
        cands = sorted(c for c, d in dists.items() if d == best)
        nxt = cands[int(rng.integers(0, len(cands)))]
        order.append(nxt)
        remaining.discard(nxt)
        cur = nxt
    return order


def build_walks() -> list[dict]:
    """The FROZEN walk ensemble: 4 local serpentines + 4 greedy walks."""
    walks = []
    for wi, perm in enumerate(SERPENTINE_PERMS):
        walks.append({"id": f"local{wi + 1}", "kind": "local",
                      "order": serpentine_order(perm)})
    for wi, (start, seed) in enumerate(zip(GREEDY_STARTS, GREEDY_SEEDS)):
        walks.append({"id": f"mixed{wi + 1}", "kind": "mixed",
                      "order": greedy_order(start, seed),
                      "start": list(start), "seed": int(seed)})
    return walks


def walk_report(walks: list[dict]) -> dict:
    """Every walk is a Hamiltonian path; book its stride histogram."""
    out = []
    seen_cells = True
    for w in walks:
        order = w["order"]
        strides = [sum(abs(order[t + 1][a] - order[t][a]) for a in range(3))
                   for t in range(len(order) - 1)]
        seen_cells = seen_cells and len(set(order)) == int(np.prod(GRID_SHAPE))
        out.append({"id": w["id"], "kind": w["kind"],
                    "n_cells": len(order),
                    "n_steps": len(order) - 1,
                    "strides": strides,
                    "max_stride": int(max(strides)),
                    "n_jump_steps": int(sum(1 for s in strides
                                            if s > LOCAL_STRIDE_MAX))})
    return {"walks": out, "n_walks": len(walks),
            "all_hamiltonian": bool(seen_cells),
            "n_cells": int(np.prod(GRID_SHAPE)),
            "note": ("local = serpentine, every step changes ONE dial by one "
                     "level (stride 1); mixed = seeded greedy nearest "
                     "neighbour, strides 1..3. Frozen before the run.")}


def edges_from_walks(walks: list[dict],
                     coords: list[tuple[int, int, int]]) -> np.ndarray:
    """Consecutive walk steps -> (n_edges, 2) DIRECTED edge array of ROOM
    indices (A = field_before, B = field_after), in walk order."""
    key = {tuple(int(x) for x in c): i for i, c in enumerate(coords)}
    if len(key) != len(coords):
        raise ValueError("bank has duplicate grid cells — not a dial grid")
    edges = []
    for w in walks:
        order = w["order"]
        for t in range(len(order) - 1):
            a, b = tuple(order[t]), tuple(order[t + 1])
            if a not in key or b not in key:
                raise ValueError(f"walk cell {a} / {b} not in the bank")
            edges.append((key[a], key[b]))
    return np.asarray(edges, int)


def edge_strides(edge_idx: np.ndarray, coords: list[tuple[int, int, int]]
                 ) -> np.ndarray:
    """Per-edge L1 (grid) distance between its endpoints."""
    c = np.asarray(coords, int)
    a, b = c[edge_idx[:, 0]], c[edge_idx[:, 1]]
    return np.abs(a - b).sum(1)


def edge_fold_structure_check(edge_idx: np.ndarray, n_rooms: int) -> dict:
    """Structural assertion of the pre-registered CV on THIS edge set.

    Per fold (held-out room h): every test edge touches h, no train edge does,
    test and train partition the edge set, and the test size equals the number
    of edges touching h. A failure means the CV is not room-disjoint and every
    R2 below is meaningless.
    """
    n = int(n_rooms)
    sizes_te, sizes_tr, bad = [], [], []
    for h in range(n):
        inc = np.isin(edge_idx[:, 0], [h]) | np.isin(edge_idx[:, 1], [h])
        te, tr = inc, ~inc
        sizes_te.append(int(te.sum()))
        sizes_tr.append(int(tr.sum()))
        if int(te.sum()) + int(tr.sum()) != len(edge_idx):
            bad.append(f"room {h}: test+train != edges")
        if int(te.sum()) == 0:
            bad.append(f"room {h}: no test edges")
        if bool(te[tr].any()):
            bad.append(f"room {h}: test/train overlap")
        if not bool(np.isin(edge_idx[te][:, 0], [h]).any()
                    or np.isin(edge_idx[te][:, 1], [h]).any()):
            bad.append(f"room {h}: a test edge avoids the held room")
        if bool(np.isin(edge_idx[tr][:, 0], [h]).any()
                or np.isin(edge_idx[tr][:, 1], [h]).any()):
            bad.append(f"room {h}: a train edge touches the held room")
    return {
        "n_rooms": n, "n_edges": int(len(edge_idx)), "folds": n,
        "min_test_edges": int(min(sizes_te)),
        "max_test_edges": int(max(sizes_te)),
        "min_train_edges": int(min(sizes_tr)),
        "max_train_edges": int(max(sizes_tr)),
        "bad_folds": bad[:5],
        "ok": bool(not bad),
        "note": ("leave-one-ROOM-out on WALK EDGES: the held-out room appears "
                 "in every test edge (either endpoint) and in no train edge. "
                 "Leave-one-EDGE-out is forbidden (it leaks the rooms of the "
                 "test edge into training and makes the two-absolutes "
                 "baseline undefined)."),
    }


# --------------------------------------------------------------------- #
# Edge-specific controls                                                 #
# --------------------------------------------------------------------- #
def edge_composition(T: np.ndarray, edge_idx: np.ndarray, labels: np.ndarray,
                     strides: np.ndarray) -> dict:
    """C6 — the delta targets' own shape: histogram, sign balance, zero
    fraction, std vs the absolutes', the label-delta Spearman, and the
    duplicate-edge bookkeeping."""
    T = np.asarray(T, float)
    Yd = gap_targets(T, edge_idx)
    Ld = gap_targets(np.asarray(labels, float), edge_idx)
    und = np.sort(np.asarray(edge_idx, int), axis=1)
    uniq_directed = {tuple(e) for e in np.asarray(edge_idx, int).tolist()}
    uniq_undirected = {tuple(e) for e in und.tolist()}
    out = {}
    for i, d in enumerate(DIAL_NAMES):
        vals, counts = np.unique(np.round(Yd[:, i], 6), return_counts=True)
        out[d] = {
            "unique_values": [round(float(v), 4) for v in vals],
            "counts": [int(c) for c in counts],
            "std_delta": round(float(Yd[:, i].std()), 4),
            "std_absolute": round(float(T[:, i].std()), 4),
            "std_ratio_delta_over_absolute": round(
                float(Yd[:, i].std()) / max(float(T[:, i].std()), 1e-12), 4),
            "frac_zero": round(float((np.abs(Yd[:, i]) < 1e-9).mean()), 4),
            "frac_positive": round(float((Yd[:, i] > 1e-9).mean()), 4),
            "frac_negative": round(float((Yd[:, i] < -1e-9).mean()), 4),
            "spearman_target_delta_vs_label_delta": round(
                spearman(Yd[:, i], Ld[:, i]), 4),
        }
    any_zero = np.any(np.abs(Yd) < 1e-9, axis=1)
    return {
        "per_dial": out,
        "n_edges": int(len(edge_idx)),
        "n_unique_directed_edges": int(len(uniq_directed)),
        "n_unique_undirected_edges": int(len(uniq_undirected)),
        "n_duplicate_directed": int(len(edge_idx) - len(uniq_directed)),
        "n_edges_with_a_zero_dial_delta": int(any_zero.sum()),
        "n_edges_all_dials_zero": int(np.all(np.abs(Yd) < 1e-9, axis=1).sum()),
        "stride_histogram": {str(s): int((strides == s).sum())
                             for s in sorted(set(int(x) for x in strides))},
        "note": ("a stride-1 step moves exactly ONE dial by one grid level, so "
                 "the other two columns of that edge's delta are exactly zero — "
                 "expected, and why the per-dial zero fraction is booked and "
                 "the read is measured per dial."),
    }


def stride_bucket_r2(Y: np.ndarray, pred: np.ndarray,
                     strides: np.ndarray) -> dict:
    """C7 — out-of-fold edge R2 restricted to stride-1 ("the local walk") vs
    stride>=2 ("jumps"). Conditional on the model fitted on ALL edges, so it is
    a scope read, never a gate."""
    strides = np.asarray(strides, int)
    out = {}
    for name, mask in (("stride1_local", strides <= LOCAL_STRIDE_MAX),
                       ("stride_ge2_jump", strides > LOCAL_STRIDE_MAX)):
        m = np.asarray(mask, bool)
        if int(m.sum()) < 3:
            out[name] = {"n_edges": int(m.sum()), "r2": None}
            continue
        out[name] = {"n_edges": int(m.sum()),
                     "r2": r2_dict(r2_columns(Y[m], pred[m]))}
    out["note"] = ("R2 on a SUBSET of the same out-of-fold predictions "
                   "(conditional read, booked not gated): if the delta read "
                   "exists only on jumps, 'the walk' is really room-pair "
                   "contrast.")
    return out


# --------------------------------------------------------------------- #
# Harness self-test (CPU-only, carrier-free, model-free)                  #
# --------------------------------------------------------------------- #
def edge_harness_selftest() -> dict:
    """G0d — the imported edge+LORO path on a synthetic embedding over the SAME
    27 cells and the SAME walk ensemble.

    Dials exactly linear in a 40-d embedding with small still noise; the delta
    must read at R2 >= 0.90 per dial, a room-shuffled target must collapse
    below 0.10, and the edge fold structure must assert clean. Model-free.
    """
    rng = np.random.default_rng(SEED + 5)
    coords = all_cells()
    n_rooms, n_still, d = len(coords), 6, 40
    T = np.asarray([cell_target(c) for c in coords], float)
    A = rng.standard_normal((3, d))
    Xr = T @ A + 0.05 * rng.standard_normal((n_rooms, d))
    X = np.repeat(Xr, n_still, 0) + 0.02 * rng.standard_normal(
        (n_rooms * n_still, d))
    groups = np.repeat(np.arange(n_rooms), n_still)
    basis, _ = pca_basis(X, 20)
    zr = np.stack([X[groups == g].mean(0) for g in range(n_rooms)]) @ basis

    edge_idx = edges_from_walks(build_walks(), coords)
    Yd = gap_targets(T, edge_idx)
    F = pair_features(zr, edge_idx, PRIMARY_ARM)
    pred, lam = pair_loro_predict(F, Yd, edge_idx, n_rooms)
    r2_signal = r2_columns(Yd, pred)
    perm = rng.permutation(n_rooms)
    Yp = gap_targets(T[perm], edge_idx)
    pred_p, _ = pair_loro_predict(F, Yp, edge_idx, n_rooms, fixed_lam=lam)
    r2_null = r2_columns(Yp, pred_p)
    struct = edge_fold_structure_check(edge_idx, n_rooms)
    strides = edge_strides(edge_idx, coords)
    return {
        "n_edges": int(len(edge_idx)),
        "r2_delta_signal": [round(float(v), 4) for v in r2_signal],
        "r2_delta_shuffled": [round(float(v), 4) for v in r2_null],
        "r2_delta_signal_min": round(float(r2_signal.min()), 4),
        "r2_delta_shuffled_max": round(float(r2_null.max()), 4),
        "lambda_median": round(float(lam), 6),
        "stride_histogram": {str(s): int((strides == s).sum())
                             for s in sorted(set(int(x) for x in strides))},
        "fold_structure": struct,
        "pass": bool(r2_signal.min() >= 0.90 and r2_null.max() < 0.10
                     and struct["ok"]),
        "note": ("carrier-free, model-free check of pca_basis -> "
                 "pair_features -> pair_loro_predict -> pair_pick_lambda -> "
                 "r2_columns on THIS walk-edge set with a synthetic linear "
                 "dial signal."),
    }


# --------------------------------------------------------------------- #
# Edge probe helpers (comparators + reverse invariance)                   #
# --------------------------------------------------------------------- #
def comparators(zr: np.ndarray, Y_room: np.ndarray, Y_edge: np.ndarray,
                edge_idx: np.ndarray, n_rooms: int) -> dict:
    """(a) single-room absolute read at the same representation/width; (b) the
    two-absolutes deltas (LOO and conservative in-fold). One probe serves (a)
    and the LOO part of (b) by design — no third estimator sneaks in."""
    abs_pred, lam_abs = abs_room_oof(zr, Y_room, n_rooms)
    r2_abs = r2_columns(Y_room, abs_pred)
    base_loo = gap_from_abs(abs_pred, edge_idx)
    r2_base_loo = r2_columns(Y_edge, base_loo)
    base_fold = two_abs_fold_gaps(zr, Y_room, edge_idx, n_rooms)
    r2_base_fold = r2_columns(Y_edge, base_fold)
    return {
        "single_room_abs_r2": r2_dict(r2_abs),
        "two_abs_loo_r2": r2_dict(r2_base_loo),
        "two_abs_fold_r2": r2_dict(r2_base_fold),
        "lambda_median_abs": (round(float(lam_abs), 6)
                              if lam_abs == lam_abs else None),
    }


def reverse_edges(edge_idx: np.ndarray) -> np.ndarray:
    """(A, B) -> (B, A): the same edges, reversed in time."""
    return np.asarray(edge_idx, int)[:, ::-1].copy()


def edge_read(zr: np.ndarray, Y_edge: np.ndarray, edge_idx: np.ndarray,
              n_rooms: int, arm: str = PRIMARY_ARM):
    """One edge-probe run: features -> LORO predictions (+ fold-median lambda)."""
    F = pair_features(zr, edge_idx, arm)
    pred, lam = pair_loro_predict(F, Y_edge, edge_idx, n_rooms)
    return F, pred, lam


# --------------------------------------------------------------------- #
# CPU-only mode (no model, no GPU): the plumbing test                     #
# --------------------------------------------------------------------- #
def cpu_only() -> dict:
    """Bank + walk ensemble + edge set + certificate + self-test, no model.
    Also runs every edge arm on the label-free KNOB matrix as a stand-in
    feature space — plumbing only, explicitly NOT evidence for the claim."""
    st = edge_harness_selftest()
    bank = build_bank(1)
    n_rooms = len(bank)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    coords = cell_coords(bank)

    K_L = {r["name"]: knobs_linear(float(r["target"][0]), float(r["target"][1]),
                                   float(r["target"][2])) for r in bank}
    mirror = mirror_check(bank, {"L": K_L})
    knob_mat = np.stack([K_L[r["name"]] for r in bank])
    cert_dials, cert = carrier_certificate(knob_mat, targets)

    walks = build_walks()
    edge_idx = edges_from_walks(walks, coords)
    strides = edge_strides(edge_idx, coords)
    struct = edge_fold_structure_check(edge_idx, n_rooms)
    Y_edge_label = gap_targets(labels, edge_idx)

    plumbing = {}
    for arm in ARMS:
        plumbing[arm] = {}
        for k in K_EDGE_SWEEP:
            F = pair_features(knob_mat[:, :k], edge_idx, arm)
            pred, lam = pair_loro_predict(F, Y_edge_label, edge_idx, n_rooms)
            plumbing[arm][str(k)] = {
                "n_features": int(F.shape[1]),
                "r2_delta_knobspace": r2_dict(r2_columns(Y_edge_label, pred)),
                "lambda_median": round(float(lam), 6),
            }

    out = {
        "experiment": "E16 field-edge (transitional) dial read",
        "mode": "cpu-only (no model, no GPU)",
        "seed": SEED,
        "dial_names": DIAL_NAMES,
        "extra_dials_available": EXTRA_DIALS,
        "rooms": n_rooms,
        "walks": walk_report(walks),
        "edges": int(len(edge_idx)),
        "edges_per_walk": STEPS_PER_WALK,
        "k_edge_primary": K_EDGE_PRIMARY,
        "k_edge_sweep": list(K_EDGE_SWEEP),
        "arms": list(ARMS),
        "primary_arm": PRIMARY_ARM,
        "fold_structure": struct,
        "harness_selftest": st,
        "arm_L_mirror_check": mirror,
        "carrier_certificate": {
            "summary": cert, "per_dial": cert_dials,
            "knob_ranges": knob_ranges(knob_mat),
            "gate_used": ("liveness half only (injective + >=2/3 dials live) "
                          "plus the mirror check; non-affinity deliberately "
                          "NOT gated (curvature 0.000 is E12's linear carrier "
                          "by construction)"),
        },
        "staging_fidelity_spearman_target_vs_label": {
            d: round(spearman(targets[:, i], labels[:, i]), 4)
            for i, d in enumerate(DIAL_NAMES)},
        "edge_composition": edge_composition(targets, edge_idx, labels, strides),
        "sample_walk_edges_head": [
            {"walk": w["id"], "room_a": int(edge_idx[i, 0]),
             "room_b": int(edge_idx[i, 1]), "stride": int(strides[i])}
            for i, w in [(0, walks[0]), (26, walks[1]), (104, walks[4]),
                         (105, walks[4])]],
        "sample_lavfi_source_room01": render_scene(
            K_L[bank[0]["name"]], bank[0]["seed"]),
        "plumbing_only_not_evidence": {
            "feature_space": ("the 7-d label-free KNOB matrix (room -> scene "
                              "parameters), not I-JEPA embeddings — the "
                              "embedding space needs the GPU run. Widths k > 7 "
                              "therefore clamp to the matrix's 7 columns "
                              "(n_features saturates at 3*7 = 21), so this "
                              "block exercises the code path and the fold "
                              "bookkeeping ONLY; the R2 values are a "
                              "near-affine sanity read, not a claim."),
            "arms": plumbing,
        },
        "note": ("No verdict in CPU-only mode. Watch: fold_structure must be "
                 "clean (27 folds, every test edge touching the held room, no "
                 "train edge touching it), the harness self-test must read the "
                 "synthetic delta at >= 0.90 and collapse on the room shuffle, "
                 "the mirror check must match e12.stage_source byte-for-byte, "
                 "and the liveness half of the carrier certificate must pass "
                 "(non-affinity is NOT gated here — E16 uses E12's linear "
                 "carrier)."),
    }
    print(json.dumps(out, indent=2))
    return out


# --------------------------------------------------------------------- #
# Plumbing mode (no model, no GPU): the FULL post-collection code path    #
# --------------------------------------------------------------------- #
def fake_stills(knob_mat: np.ndarray, labels: np.ndarray):
    """Stand-in (X, Ylab, groups, lum, pix) so the ENTIRE post-collection
    path of main() runs without a model: the 7-d label-free knob matrix is
    repeated to N_STILLS per room as a fake embedding, and the luminance
    surrogate is the brightness knob plus deterministic per-still jitter.

    The numbers this produces are MEANINGLESS (a 7-d near-affine stand-in);
    the point is to execute every comparator, control, sweep, null and gate in
    the real code path so a plumbing fault cannot hide behind a GPU run.
    """
    n_rooms = len(knob_mat)
    X = np.repeat(np.asarray(knob_mat, float) * 100.0, N_STILLS, axis=0)
    X = X + 0.01 * np.arange(X.shape[0])[:, None]     # break still-level ties
    Ylab = np.repeat(np.asarray(labels, float), N_STILLS, axis=0)
    groups = np.repeat(np.arange(n_rooms), N_STILLS)
    lum = np.repeat(knob_mat[:, 3], N_STILLS)
    lum = lum + 1e-6 * (np.arange(len(lum)) % N_STILLS)
    pix = np.repeat(np.asarray(knob_mat, float), N_STILLS, axis=0)
    return X, Ylab, groups, lum, pix


# --------------------------------------------------------------------- #
# Main                                                                  #
# --------------------------------------------------------------------- #
def main() -> dict:
    if "--cpu-only" in sys.argv:
        return cpu_only()
    plumbing = "--plumbing" in sys.argv

    if plumbing:
        ok, reason, guard_info = True, None, {"skipped": "plumbing mode"}
    else:
        ok, reason, guard_info = preflight_guard()
    if not ok:
        out = {"experiment": "E16 field-edge (transitional) dial read",
               "verdict": "ABORTED", "reason": reason,
               "guard_preflight": guard_info}
        print(json.dumps(out, indent=2))
        return out

    base = {
        "experiment": "E16 field-edge (transitional) dial read", "seed": SEED,
        "dial_names": DIAL_NAMES, "extra_dials": EXTRA_DIALS,
        "primary_arm": PRIMARY_ARM, "arm_titles": ARM_TITLES,
        "k_edge_primary": K_EDGE_PRIMARY, "k_edge_sweep": list(K_EDGE_SWEEP),
        "guard_preflight": guard_info,
        "mode": ("plumbing (fake embeddings — NO CLAIM)" if plumbing
                 else "full (frozen I-JEPA embeddings)"),
        "claim": ("the read of a field EDGE (the delta-dial between two "
                  "consecutive states of a walk) beats both the static "
                  "single-room dial read and the two-absolutes baseline on "
                  ">= 2/3 dials — the walk carries signal the rooms do not"),
    }

    # G0d — cheapest gate first: if the imported edge probe path is broken,
    # nothing else is interpretable (and it is model-free).
    selftest = edge_harness_selftest()
    log(f"harness self-test: signal_min={selftest['r2_delta_signal_min']} "
        f"shuffled_max={selftest['r2_delta_shuffled_max']} "
        f"pass={selftest['pass']}")

    # Bank + carrier + certificate — all CPU, all before the model.
    bank = build_bank(1)
    n_rooms = len(bank)
    targets = np.stack([r["target"] for r in bank])
    labels = np.stack([r["label"] for r in bank])
    coords = cell_coords(bank)
    K_L = {r["name"]: knobs_linear(float(r["target"][0]), float(r["target"][1]),
                                   float(r["target"][2])) for r in bank}
    mirror = mirror_check(bank, {"L": K_L})
    knob_mat = np.stack([K_L[r["name"]] for r in bank])
    cert_dials, cert = carrier_certificate(knob_mat, targets)

    # The walk ensemble -> the field-edge bank.
    walks = build_walks()
    edge_idx = edges_from_walks(walks, coords)
    strides = edge_strides(edge_idx, coords)
    struct = edge_fold_structure_check(edge_idx, n_rooms)
    Y_edge_label = gap_targets(labels, edge_idx)      # PRIMARY target (gated)
    Y_edge_target = gap_targets(targets, edge_idx)    # design-target delta (booked)
    log(f"bank: {n_rooms} rooms; {len(walks)} walks -> {len(edge_idx)} edges "
        f"(strides {sorted(set(int(s) for s in strides))}); "
        f"certificate live={cert['n_dials_live']}/3 "
        f"injective={cert['injectivity']['injective']} "
        f"curvature={cert['mean_curvature']} mirror={mirror['match']}")

    fid = {d: round(spearman(targets[:, i], labels[:, i]), 4)
           for i, d in enumerate(DIAL_NAMES)}
    fid_pass = bool(sum(1 for d in DIAL_NAMES if fid[d] >= 0.5)
                    >= GATE_HIT_DIALS)
    cert_ok = bool(cert["live_pass"] and cert["injectivity"]["injective"]
                   and mirror["match"])

    gate_notes: list[dict] = []

    def bail(verdict: str, why: str, extra: dict | None = None) -> dict | None:
        """Emit the verdict JSON and return it. In plumbing mode the gate is
        RECORDED and None is returned, so the caller continues down the code
        path instead of stopping at the first (meaningless) gate failure."""
        if plumbing:
            gate_notes.append({"would_be_verdict": verdict, "why": why})
            log(f"[plumbing] gate would bail: {verdict}: {why}")
            return None
        out = dict(base)
        out.update({
            "verdict": verdict, "verdict_reason": why,
            "harness_selftest": selftest,
            "fold_structure": struct,
            "walks": walk_report(walks),
            "edges": int(len(edge_idx)),
            "carrier_certificate": {"summary": cert, "per_dial": cert_dials,
                                    "knob_ranges": knob_ranges(knob_mat)},
            "arm_L_mirror_check": mirror,
            "staging_fidelity_spearman_target_vs_label": fid,
        })
        if extra:
            out.update(extra)
        print(json.dumps(out, indent=2))
        return out

    if not selftest["pass"]:
        b = bail("INVALID_HARNESS",
                 "G0d: the imported edge+LORO probe failed the synthetic "
                 "self-test (or the fold structure is not room-disjoint)")
        if b is not None:
            return b
    if not struct["ok"]:
        b = bail("INVALID_HARNESS",
                 "G0d: the leave-one-ROOM-out edge folds are not "
                 "room-disjoint / are degenerate",
                 {"fold_structure_bad": struct["bad_folds"]})
        if b is not None:
            return b
    if not fid_pass:
        b = bail("INVALID_STAGING",
                 "G0a: the staged scripts did not move >= 2/3 dials")
        if b is not None:
            return b
    if not cert_ok:
        b = bail("INVALID_STAGING",
                 "G0c: the staged carrier failed its liveness certificate "
                 "(dead or non-injective carrier, or the Arm-L mirror "
                 "check failed) — the arm tested nothing")
        if b is not None:
            return b
    if n_rooms < 8:
        b = bail("ABORTED",
                 f"only {n_rooms} rooms — grouped CV would be meaningless")
        if b is not None:
            return b
    if len(edge_idx) < 8:
        b = bail("ABORTED",
                 f"only {len(edge_idx)} field-edges — the edge probe would "
                 "be meaningless")
        if b is not None:
            return b

    if plumbing:
        X, Ylab, groups, lum, pix = fake_stills(knob_mat, labels)
        dev, model_used = "cpu(plumbing)", "none (plumbing — no model)"
        load_notes = {"plumbing": ("the 7-d label-free knob matrix stands in "
                                   "for the embedding; every number below is "
                                   "MEANINGLESS except as a code path")}
        log(f"plumbing: fake stills {X.shape} (no model, no GPU)")
    else:
        import torch
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        dev = "cuda" if torch.cuda.is_available() else "cpu"

        log(f"loading I-JEPA ({dev})...")
        try:
            model_used, model, processor, load_notes = load_encoder(dev)
        except Exception as e:  # noqa: BLE001
            b = bail("ABORTED", f"model load failed: {e}")
            if b is not None:
                return b
        log(f"using {model_used}")

        # E13's collector verbatim, on the Arm-L carrier (E12's staging). The
        # embeddings are E12's bank embeddings — the edges REUSE them, they
        # cost nothing extra: one render pass, 27 rooms x 12 stills.
        try:
            X, Ylab, _Yt, groups, lum, pix = collect_arm(
                "L", {"L": K_L}, bank, model, processor, dev, torch)
        except Exception as e:  # noqa: BLE001
            b = bail("ABORTED", f"frame/embed failed: {e}")
            if b is not None:
                return b

    # Room features: E12's convention — label-free PCA on the stills, then the
    # room mean taken IN that space.
    basis, evr = pca_basis(X, K_WIDE)
    Xrm = np.stack([X[groups == g].mean(0) for g in range(n_rooms)])
    Xr = Xrm @ basis
    zc = X @ basis[:, :K_PRIMARY]                 # still-level k=64 (E12 space)
    room_lum = np.stack([lum[groups == g].mean() for g in range(n_rooms)])
    room_pix = np.stack([pix[groups == g].mean(0) for g in range(n_rooms)])
    log(f"features: stills={X.shape} room_features={Xr.shape}")

    # G0b.1 — E12's sensitivity control verbatim (still-level luminance), and
    # G0e — in-run replication of E12's own still-level dial gate.
    lum_col = lum.reshape(-1, 1).astype(np.float64)
    pred_lum, _ = loro_predict(zc, lum_col, groups)
    r2_lum_still = float(r2_columns(lum_col, pred_lum)[0])
    pred_abs_still, _ = loro_predict(zc, Ylab, groups)
    r2_abs_still = r2_columns(Ylab, pred_abs_still)
    zc16 = X @ basis[:, :K_STRICT]
    pred_abs_still16, _ = loro_predict(zc16, Ylab, groups)
    r2_abs_still16 = r2_columns(Ylab, pred_abs_still16)
    e12_repl = {d: round(float(r2_abs_still[i]), 4)
                for i, d in enumerate(DIAL_NAMES)}
    e12_repl16 = {d: round(float(r2_abs_still16[i]), 4)
                  for i, d in enumerate(DIAL_NAMES)}
    e12_repl_pass = bool(sum(1 for d in DIAL_NAMES
                             if e12_repl[d] >= E12_REPL_FLOOR)
                         >= GATE_HIT_DIALS)
    log(f"G0b.1 luminance(still,k64)={r2_lum_still:.4f}  "
        f"G0e E12 repl(k64)={e12_repl}")

    # ---------------------------------------------------------------- #
    # Comparators (a) static single-room and (b) two-absolutes delta     #
    # (same room-level representation and width as the edge reader)      #
    # ---------------------------------------------------------------- #
    comp_label = {str(k): comparators(Xr[:, :k], labels, Y_edge_label,
                                      edge_idx, n_rooms)
                  for k in K_EDGE_SWEEP}
    comp_target = {str(k): comparators(Xr[:, :k], targets, Y_edge_target,
                                       edge_idx, n_rooms)
                   for k in K_EDGE_SWEEP}
    comp_primary = comp_label[str(K_EDGE_PRIMARY)]
    comp_primary_target = comp_target[str(K_EDGE_PRIMARY)]
    log(f"(a) static single-room abs R2@{K_EDGE_PRIMARY}="
        f"{comp_primary['single_room_abs_r2']}")
    log(f"(b) two-absolutes LOO R2@{K_EDGE_PRIMARY}="
        f"{comp_primary['two_abs_loo_r2']}")

    # ---------------------------------------------------------------- #
    # G0b.2 — the edge machinery's own control: the luminance DELTA     #
    # ---------------------------------------------------------------- #
    Y_lum_delta = gap_targets(room_lum.reshape(-1, 1), edge_idx)
    F_prim, pred_prim, lam_prim = edge_read(
        Xr[:, :K_EDGE_PRIMARY], Y_edge_label, edge_idx, n_rooms, PRIMARY_ARM)
    _F_lum, pred_lum_delta, lam_lum_delta = edge_read(
        Xr[:, :K_EDGE_PRIMARY], Y_lum_delta, edge_idx, n_rooms, PRIMARY_ARM)
    r2_lum_delta = float(r2_columns(Y_lum_delta, pred_lum_delta)[0])
    null_lum_delta = pair_perm_null(F_prim, room_lum.reshape(-1, 1),
                                    edge_idx, n_rooms, lam_lum_delta, PERMS,
                                    SEED + 31)
    null95_lum_delta = float(np.percentile(null_lum_delta[:, 0], 95))
    edge_sens_pass = bool(r2_lum_delta >= EDGE_SENSITIVITY_FLOOR
                          and r2_lum_delta > null95_lum_delta)
    log(f"G0b.2 luminance-DELTA(edge,k={K_EDGE_PRIMARY})={r2_lum_delta:.4f} "
        f"null95={null95_lum_delta:.4f} pass={edge_sens_pass}")

    if not (r2_lum_still >= SENSITIVITY_FLOOR and edge_sens_pass):
        b = bail("INVALID_HARNESS",
                    f"G0b: sensitivity failed (still-level luminance R2 "
                    f"{r2_lum_still:.4f} < {SENSITIVITY_FLOOR}, or edge-level "
                    f"luminance-delta R2 {r2_lum_delta:.4f} < "
                    f"{EDGE_SENSITIVITY_FLOOR}) — the probe cannot read a "
                    "signal certainly present in the frames",
                    {"g0b_sensitivity": {
                        "r2_luminance_still_k64": round(r2_lum_still, 4),
                        "floor_still": SENSITIVITY_FLOOR,
                        "r2_luminance_delta_edge": round(r2_lum_delta, 4),
                        "floor_edge_delta": EDGE_SENSITIVITY_FLOOR,
                        "null95_edge_delta": round(null95_lum_delta, 4)}})
        if b is not None:
            return b
    if not e12_repl_pass:
        b = bail("INVALID_HARNESS",
                 "G0e: E12's own still-level dial read did not replicate in "
                 "this run — the (a)/(b) comparators would be meaningless",
                 {"g0e_e12_replication": e12_repl,
                  "floor": E12_REPL_FLOOR})
        if b is not None:
            return b

    # ---------------------------------------------------------------- #
    # The arm sweep on the edge sample: label delta (primary),           #
    # design-target delta and SUM control (booked)                       #
    # ---------------------------------------------------------------- #
    Y_sum_label = sum_targets(labels, edge_idx)
    sweep: dict = {}
    for arm in ARMS:
        sweep[arm] = {}
        for k in K_EDGE_SWEEP:
            F = pair_features(Xr[:, :k], edge_idx, arm)
            pred, lam = pair_loro_predict(F, Y_edge_label, edge_idx, n_rooms)
            r2_delta = r2_columns(Y_edge_label, pred)
            pred_t, lam_t = pair_loro_predict(F, Y_edge_target, edge_idx,
                                              n_rooms)
            r2_delta_target = r2_columns(Y_edge_target, pred_t)
            pred_s, lam_s = pair_loro_predict(F, Y_sum_label, edge_idx, n_rooms)
            r2_sum = r2_columns(Y_sum_label, pred_s)
            # C8 — reverse-edge invariance: reversing every edge is a pure
            # relabelling (delta negates, feature blocks permute/sign-flip), so
            # the R2 must be reproduced exactly.
            rev = reverse_edges(edge_idx)
            F_rev = pair_features(Xr[:, :k], rev, arm)
            pred_rev, _ = pair_loro_predict(F_rev, gap_targets(labels, rev),
                                            rev, n_rooms)
            r2_rev = r2_columns(gap_targets(labels, rev), pred_rev)
            rev_gap = float(np.max(np.abs(r2_rev - r2_delta)))
            sweep[arm][str(k)] = {
                "n_features": int(F.shape[1]),
                "r2_delta_label": r2_dict(r2_delta),
                "r2_delta_target_booked": r2_dict(r2_delta_target),
                "r2_sum_control": r2_dict(r2_sum),
                "reverse_edge_invariance_max_abs_diff": round(rev_gap, 12),
                "lambda_median_delta": round(float(lam), 6),
                "mean_r2_delta": round(float(np.mean(r2_delta)), 4),
            }
            log(f"arm {arm} k={k}: mean_delta_r2="
                f"{sweep[arm][str(k)]['mean_r2_delta']} "
                f"delta={sweep[arm][str(k)]['r2_delta_label']} "
                f"sum={sweep[arm][str(k)]['r2_sum_control']}")

    primary = sweep[PRIMARY_ARM][str(K_EDGE_PRIMARY)]
    prim_delta = primary["r2_delta_label"]

    # Permutation null for the PRIMARY arm at the primary width.
    null = pair_perm_null(F_prim, labels, edge_idx, n_rooms,
                          primary["lambda_median_delta"], PERMS, SEED + 11)
    null95 = {d: round(float(np.percentile(null[:, i], 95)), 4)
              for i, d in enumerate(DIAL_NAMES)}
    perm_p = {d: round(float((null[:, i] >= prim_delta[d]).mean()), 4)
              for i, d in enumerate(DIAL_NAMES)}

    # C7 — stride buckets (the E16-specific scope read).
    buckets = stride_bucket_r2(Y_edge_label, pred_prim, strides)

    # C10 — the same reader on E18's all-pairs (arbitrary contrast) sample.
    allpairs = pairs_from_rooms(n_rooms)
    Y_all = gap_targets(labels, allpairs)
    F_all = pair_features(Xr[:, :K_EDGE_PRIMARY], allpairs, PRIMARY_ARM)
    pred_all, lam_all = pair_loro_predict(F_all, Y_all, allpairs, n_rooms)
    r2_all = r2_columns(Y_all, pred_all)
    allpairs_control = {
        "n_pairs": int(len(allpairs)),
        "r2_gap_all_pairs": r2_dict(r2_all),
        "lambda_median": round(float(lam_all), 6),
        "note": ("E18's C(27,2) sample through the SAME reader: a spatial "
                 "contrast between arbitrary rooms, not a walk step. Booked "
                 "scope read (different sample size and delta distribution) "
                 "for 'is the walk sample harder/easier than contrast?'"),
    }

    # C1 — raw-pixel edge control through the SAME probe, PCA-reduced
    # label-free to the same width so it stays apples-to-apples.
    pix_basis, pix_evr = pca_basis(room_pix, K_EDGE_PRIMARY)
    F_pix = pair_features(room_pix @ pix_basis[:, :K_EDGE_PRIMARY], edge_idx,
                          PRIMARY_ARM)
    pred_pix, _ = pair_loro_predict(F_pix, Y_edge_label, edge_idx, n_rooms)
    pix_delta = r2_dict(r2_columns(Y_edge_label, pred_pix))

    # C12 — booked leak probe (random edge split, never gated).
    leak = pair_split_leak_probe(F_prim, Y_edge_label, edge_idx, n_rooms,
                                 fraction=LEAK_SPLIT_FRACTION, seed=SEED + 3)
    leak["n_train_edges"] = leak.pop("n_train_pairs")
    leak["n_test_edges"] = leak.pop("n_test_pairs")
    leak["note"] = ("random EDGE split (e18's `pair_split_leak_probe`, "
                    "key-renamed) — rooms appear on BOTH sides (the column "
                    "above), which is why it is booked, not gated.")

    # C5 — E12's room-identity sanity check (half-split, chance 1/27), C2.
    id_acc = room_halfsplit_acc(zc, groups)
    lum_spear = {d: round(spearman(room_lum, labels[:, i]), 4)
                 for i, d in enumerate(DIAL_NAMES)}

    # ---------------------------------------------------------------- #
    # G1/G2/G3 — the pre-registered edge gate                            #
    # ---------------------------------------------------------------- #
    exceed, beat_base, beats_conservative, strict_pass = {}, {}, {}, {}
    for d in DIAL_NAMES:
        exceed[d] = bool(prim_delta[d] > comp_primary["single_room_abs_r2"][d]
                         and prim_delta[d] > comp_primary["two_abs_loo_r2"][d]
                         and prim_delta[d] > null95[d])
        beat_base[d] = bool(
            prim_delta[d] > comp_primary["two_abs_loo_r2"][d])
        beats_conservative[d] = bool(
            prim_delta[d] > comp_primary["two_abs_fold_r2"][d])
        strict_pass[d] = bool(prim_delta[d] > e12_repl[d])
    n_exceed = int(sum(1 for d in DIAL_NAMES if exceed[d]))
    n_beat_base = int(sum(1 for d in DIAL_NAMES if beat_base[d]))
    n_strict = int(sum(1 for d in DIAL_NAMES if strict_pass[d]))
    mean_delta = float(np.mean([prim_delta[d] for d in DIAL_NAMES]))
    mean_null = float(np.mean([null95[d] for d in DIAL_NAMES]))

    if n_exceed >= GATE_HIT_DIALS:
        verdict, why = "KEEP", (
            f"the field-edge (delta-dial) read beats BOTH the single-room "
            f"static R2 and the two-absolutes baseline (and its own null) on "
            f"{n_exceed}/3 dials — the walk carries signal the rooms do not")
    elif n_beat_base <= 1:
        verdict, why = "KILL", (
            f"the edge read beats the two-absolutes baseline on only "
            f"{n_beat_base}/3 dials — the change is just the two states "
            "differenced; static state is everything")
    else:
        verdict, why = "INCONCLUSIVE", (
            f"{n_beat_base}/3 dials beat the two-absolutes baseline but only "
            f"{n_exceed}/3 clear BOTH comparators and the null")

    deltas_abs = {d: round(prim_delta[d]
                           - comp_primary["single_room_abs_r2"][d], 4)
                  for d in DIAL_NAMES}
    deltas_base = {d: round(prim_delta[d] - comp_primary["two_abs_loo_r2"][d], 4)
                   for d in DIAL_NAMES}

    out = dict(base)
    out.update({
        "device": dev, "model": model_used, "load_notes": load_notes,
        "rooms": n_rooms,
        "walks": walk_report(walks),
        "edges": int(len(edge_idx)),
        "stills_per_room": N_STILLS, "cells": int(X.shape[0]),
        "emb_dim": int(X.shape[1]),
        "pca_evr_k16": round(float(evr[:K_STRICT].sum()), 4),
        "pca_evr_k64": round(float(evr[:K_PRIMARY].sum()), 4),
        "pca_evr_k256": round(float(evr[:K_WIDE].sum()), 4),
        "label_stats": {d: {"min": round(float(labels[:, i].min()), 4),
                            "max": round(float(labels[:, i].max()), 4),
                            "std": round(float(labels[:, i].std()), 4)}
                        for i, d in enumerate(DIAL_NAMES)},
        "harness_selftest": selftest,
        "fold_structure": struct,
        "cv_design": {
            "outer_unit": "room (leave-one-ROOM-out on walk edges)",
            "folds": n_rooms,
            "test_edges_per_fold": [struct["min_test_edges"],
                                    struct["max_test_edges"]],
            "train_edges_per_fold": [struct["min_train_edges"],
                                     struct["max_train_edges"]],
            "inner_lambda": ("grouped inner CV on the training rooms "
                             "(e18.pair_pick_lambda -> e12._ridge_path_pred, "
                             "6 lambdas)"),
            "pca_basis": ("label-free, fit once on all still embeddings, "
                          "frozen for every fold and arm (E12's convention)"),
            "null": (f"{PERMS} room-level label shuffles, edge deltas rebuilt "
                     "from the permuted triples, fixed fold-median lambda"),
            "edge_level_split": "forbidden (booked leak probe below)",
            "walk_ensemble": "frozen in the file: 4 local serpentines + 4 "
                             "seeded greedy walks, 8 x 26 = 208 directed edges",
        },
        "comparators_label_space": comp_label,
        "comparators_target_space_booked": comp_target,
        "primary": {
            "arm": PRIMARY_ARM, "k": K_EDGE_PRIMARY,
            "target": "label delta (elephant DialBank reading B - reading A)",
            "r2_delta": prim_delta, "n_features": primary["n_features"],
            "comparator_a_single_room_static_r2":
                comp_primary["single_room_abs_r2"],
            "comparator_b_two_absolutes_loo_r2":
                comp_primary["two_abs_loo_r2"],
        },
        "arms": sweep,
        "perm_null95_delta_primary": null95,
        "perm_p_delta_primary": perm_p,
        "deltas_vs_single_room_static": deltas_abs,
        "deltas_vs_two_absolutes": deltas_base,
        "edge_composition": edge_composition(targets, edge_idx, labels, strides),
        "controls": {
            "stride_buckets": buckets,
            "all_pairs_contrast": allpairs_control,
            "raw_pixel_edge_delta_r2": pix_delta,
            "raw_pixel_k_used": K_EDGE_PRIMARY,
            "raw_pixel_pca_evr": round(float(pix_evr.sum()), 4),
            "luminance_absolute_spearman_target": lum_spear,
            "r2_luminance_still_k64": round(r2_lum_still, 4),
            "r2_luminance_delta_edge_primary": round(r2_lum_delta, 4),
            "null95_luminance_delta_edge": round(null95_lum_delta, 4),
            "e12_still_k64_abs_r2": e12_repl,
            "e12_still_k16_abs_r2": e12_repl16,
            "e12_replication_floor": E12_REPL_FLOOR,
            "room_identity_acc": round(float(id_acc), 4),
            "room_identity_chance": round(1.0 / n_rooms, 4),
            "edge_split_leak_probe": leak,
            "extra_dials_booked": {
                d: {"min": round(float(min(r["extra"][d] for r in bank)), 4),
                    "max": round(float(max(r["extra"][d] for r in bank)), 4)}
                for d in EXTRA_DIALS},
        },
        "carrier_certificate": {"summary": cert, "per_dial": cert_dials,
                                "knob_ranges": knob_ranges(knob_mat),
                                "gate_used": ("liveness half only "
                                              "(injective + >=2/3 dials live) "
                                              "+ mirror check; non-affinity "
                                              "NOT gated — E12's linear "
                                              "carrier by construction")},
        "arm_L_mirror_check": mirror,
        "staging_fidelity_spearman_target_vs_label": fid,
        "gates": {
            "g0d_harness_selftest": {
                "pass": selftest["pass"],
                "signal_min": selftest["r2_delta_signal_min"],
                "shuffled_max": selftest["r2_delta_shuffled_max"]},
            "g0a_staging_fidelity": {"floor": 0.5, "measured": fid,
                                     "pass": fid_pass},
            "g0c_carrier_certificate": {
                "live_pass": cert["live_pass"],
                "injective": cert["injectivity"]["injective"],
                "mirror_match": mirror["match"],
                "mean_curvature": cert["mean_curvature"],
                "pass": cert_ok},
            "g0b_sensitivity": {
                "r2_luminance_still_k64": round(r2_lum_still, 4),
                "floor_still": SENSITIVITY_FLOOR,
                "r2_luminance_delta_edge": round(r2_lum_delta, 4),
                "floor_edge_delta": EDGE_SENSITIVITY_FLOOR,
                "pass": bool(r2_lum_still >= SENSITIVITY_FLOOR
                             and edge_sens_pass)},
            "g0e_e12_replication": {"measured": e12_repl,
                                    "floor": E12_REPL_FLOOR,
                                    "pass": e12_repl_pass},
            "g1_edge": {
                "exceed_both_and_null": exceed,
                "n_exceed": n_exceed,
                "beats_two_abs_baseline": beat_base,
                "n_beat_baseline": n_beat_base,
                "beats_conservative_baseline_booked": beats_conservative,
                "strict_pass_still_level_booked": {
                    "per_dial": strict_pass, "n_strict_pass": n_strict,
                    "note": ("whether the edge read also beats E12's "
                             "still-level k=64 headline (a different sample "
                             "unit: 12 stills/room vs 1 room mean) — reported, "
                             "NEVER gated")},
                "gate_dials_required": GATE_HIT_DIALS,
                "null_beats": NULL_BEATS,
                "mean_delta_r2": round(mean_delta, 4),
                "mean_null95": round(mean_null, 4),
            },
        },
        "verdict": verdict,
        "verdict_reason": why,
        "data_needed": [
            "ffmpeg ~/.local/bin/ffmpeg (lavfi chain, same as E12/E13/E18)",
            "facebook/ijepa_vith16_1k fp16 on the RTX 4050 (E9 loader, "
            "imported via E12/E13/E18)",
            "elephant package importable (DialBank = labels)",
            f"{n_rooms} rooms x {N_STILLS} stills = {n_rooms * N_STILLS} "
            "forwards ≈ 3-5 min GPU — the 208 edges REUSE these embeddings, "
            "no second render pass",
            "GPU free (guard preflight in-process)",
        ],
        "note": (
            "E16 changes the SAMPLE and the TARGET, nothing else: E12's bank "
            "and probe, E13's carrier/collector, E18's leave-one-ROOM-out "
            "pair probe, one frozen I-JEPA. A FIELD-EDGE is a step of a frozen "
            "8-walk ensemble over the 27-cell dial grid (208 directed edges, "
            "A = field_before -> B = field_after) and the target is the "
            "delta-dial label_B - label_A. KEEP = the edge read beats both the "
            "static single-room absolute R2 (same room-level representation "
            "and width) and the two-absolutes baseline (the endpoints' own "
            "out-of-fold reads, differenced), plus its own room-shuffle null, "
            "on >= 2/3 dials — the walk carries signal the rooms do not. "
            "KILL = it beats the baseline on <= 1 of 3 dials — the change is "
            "just the two states differenced. INVALID_STAGING (dead / "
            "non-injective carrier, or the scripts stopped moving the dials) "
            "and INVALID_HARNESS (blind probe, broken edge folds, or E12's own "
            "still-level read failing to replicate) are never KILLs. SCOPE: "
            "staged carriers (E12/E13's caveat unchanged) — a KEEP is a floor; "
            "target difficulty is NOT assumed (the measured delta/absolute std "
            "ratio and the stride-bucket split are booked per dial, and the "
            "room-shuffle null95 anchors every dial); the walk ensemble is a "
            "frozen design choice, and strided 'jumps' are separated out so a "
            "reader can see how much of the edge read is local-walk locality "
            "vs ordinary room-pair contrast. The SPOOL's identity-preserving "
            "paired-frame arm (same room, two dial sets) is pre-registered as "
            "E16b, out of scope here for cost + CV-sample reasons."),
    })
    if plumbing:
        out["verdict_computed_for_plumbing_only"] = out["verdict"]
        out["verdict"] = "PLUMBING_ONLY"
        out["verdict_reason"] = ("plumbing mode: the 7-d knob matrix stood in "
                                 "for the embedding — this is a CODE PATH "
                                 "test, not a claim")
        out["gate_notes_would_have_bailed"] = gate_notes
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
