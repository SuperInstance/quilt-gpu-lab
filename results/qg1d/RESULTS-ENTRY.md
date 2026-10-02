# QG1d — source-level recon: fleet-triage assignment/swap machinery vs our cell contract

- lane: QG1d (read-only recon; NO GPU, NO clone of fleet-triage, no pushes)
- date: 2026-10-01
- method: `gh api .../contents/<path> --jq .content | base64 -d` into `results/qg1d/src-snapshots/` (see MANIFEST.md for shas)
- scope: fleet-triage root (`resolver.py`, `lanes.py`, `triage.py`, BOARD/CORRECTION/D1 docs) + `experiments/` + `sim/`
- seed: 2718 (nothing was sampled; seed pinned for the ported self-test)
- **not committed — keeper folds. Not appended to RESULTS.md (parallel lanes live).**

## 0. Recon premise correction (read this first)

The brief expected "a resolver with swap/repair logic **we have never source-read**"
inside fleet-triage's `experiments/`. That is not where it is:

- `experiments/` holds the **projection-doctrine degeneracy** (`projection_doctrine.py`,
  `positive_control.py`) and the **n_eff / instrument-transfer** work (`synergy.py`).
- The citation resolver with the repair ladder is at **repo root**: `resolver.py`
  (1,815 lines). The lane/assignment machinery is `lanes.py` (root and `tools/`,
  byte-identical size).
- There is **no literal "swap" routine** anywhere in fleet-triage. `swap` appears
  exactly once, as a *bug description* (`lanes.py:100`). "Repair" appears zero times.
  The closest real machinery is: (a) the resolver's **candidate repair ladder**,
  (b) the lane **four-beam assignment/verdict**, (c) the tileset **assignment +
  collision** metric, (d) **Kish n_eff**.

So this lane reports what is actually present, not the expected artifact.

## 1. Q1 — WHY their max-over-4 was degenerate (the mechanism, not the label)

**Mechanism = max-selection over a correlated arm-set, then a leaky split.**

1. **The selection is a max over learners.** `experiments/projection_doctrine.py:336-338`:
   ```python
   def best(name):
       v = [r for (n, _), r in results.items() if n == name]
       return max(v) if v else float("nan")
   ```
   The four arms are stored at `:306` (`logreg`), `:312` (`knn`), `:319` (`mlp`),
   `:326` (`rf-logreg`). The published number per observation is `best(...)`
   (`:343-345`). The **same pattern reappears** in the control harness —
   `positive_control.py:199` (`best0 = max(rows_out["L0 lossless"])`) — so the defect
   is systemic, not one line.

2. **The four arms are not independent.** `synergy.py:69-79` (`n_eff`, Kish effective
   sample size = `k / Σ normalised correlation mass`) and the sibling `doctrine-RECHECK`
   lane computed **n_eff = 1.48 over the four learners** (`BOARD.md:23,59,83`;
   `CORRECTION-PROJECTION.md:4-8`). So "max over 4" is a max over **≈1.5 effective
   votes**. A max over correlated arms is upward-biased by roughly the arm spread.

3. **The spread exceeds the gap, so the ordering is a property of the selection.**
   `CORRECTION-PROJECTION.md:14-38`: L0 spread across the four learners **0.3209**,
   reported L0>L1 gap **0.0112** — the spread is **29× the gap**. Under the **median**
   the ordering **reverses** (L1 0.8947 > L0 0.8831). Their rule, verbatim:
   *"No gap smaller than the spread is a finding."*

4. **Secondary degeneracy: the split leaked.** `projection_doctrine.py:293`
   (`RNG.shuffle(idx)` random 80/20) vs `:295` (by-ply, honest). Their own
   `synergy.py:12-15` records the smoking gun: a **64-bit irreversible hash scored
   0.9586 on the random split vs 0.5045 by-ply** — pure memorisation. The
   max-over-learners table was read on the optimistic split.

**Mechanism in one sentence:** the reported ordering was `max` over ~1.5 effective
arms whose selection noise (0.32) swamped the between-observation gap (0.011); the
max is an upward-biased estimator, and the rank flipped when the biased estimator
was removed (median).

**Relation to our contract:** this is **not** the same clause as our `verdict_gate`
DEGENERATE law (`tools/verdict_gate.py:20-27` — *zero variance* may never PASS). It is
the **complementary** clause the fleet-triage correction supplies: **variance so large
relative to the gap that the max is not a measurement.** Our law catches std==0; their
retraction catches `spread >> gap`. Both belong in the same gate. That gap is the
substance of §3.

## 2. Mechanism → our cell contract map

Our contract (per `experiments/common.py:1-6`, `experiments/d10_cell_kernel.py:1-15`,
`experiments/d11_don_contract.py:1-16`): a **cell** = pure `z_in→z_out`, seedable
(2718), deterministic, receiptable (state hash), no hidden state across the boundary.
A **instrument** = a ways-to-fail detector (its value is that it can go red).

| fleet-triage mechanism | cite | class | disposition |
|---|---|---|---|
| Kish `n_eff` | `synergy.py:69-79` | **(a) cell-shaped** (pure, no RNG, deterministic) | **port** |
| `detection_power` (recall over known-fail) | `synergy.py:52-58` | (a) cell-shaped | port-ready; our XP-A already has the idea |
| spread-vs-gap **rule** | `CORRECTION-PROJECTION.md:26-40` | **(a) gate, cell-shaped** | **port** (§4) |
| `max` over learners | `projection_doctrine.py:336-338`, `positive_control.py:199` | **(c) neither** — it is the *defect*, not a tool | do **not** port; adopt the ban |
| repair ladder (`_suffix_match`/`_name_lives_elsewhere`/`_near_miss`) | `resolver.py:652-733`, `736-750`, `829-856` | **(c) neither as-shipped** — needs the 477-repo index + live fs + GH API; **(a) once reduced to the pure contract** | port the reduced pure form (§4) |
| four beams EXISTS/SAYS/REPRODUCES/CONTROL | `lanes.py:45-105`, `134-186` | **(b) instrument-shaped** (a ways-to-fail detector; B4 is the whole point) | port as an **instrument**, and it is the gap in XP-A (§3) |
| `beam_reproduces` (list-form subprocess) | `lanes.py:77-88` (`subprocess.run(cmd, ...)` at `:80`) | (b) instrument | law-compliant already (list form, no shell) |
| `triage.py` `api()` rate-limit gate + `inspect()` | `triage.py:52-73` / `:75-…` | **(c) neither** — network/IO glue (`urllib`, 403-vs-finding discipline) | no port; note the discipline |
| tileset `assign_nn` + `roundtrip` (assignment + collision count) | `sim/tileset_sim.py:159-163`, `145-157` | (a) cell-shaped (nearest-slot assign + collision metric) | optional; closest thing to a literal "assignment" primitive |

**Key finding for Q2:** fleet-triage has **no cell-shaped swap/repair primitive to
copy verbatim.** Its repair logic is **index glue** (it cannot run without the repo
index + filesystem), and its "swap" is a documented branch-order *bug*, not a routine.
**Our own `experiments/d11_don_contract.py` already IS the cell-shaped swap/repair
primitive** — propose a swap of discovered edges → validate on holdout → commit iff
strictly better else revert with **bit-identical revert fidelity** (docstring
`:1-16`). fleet-triage adds nothing to that cell. What it *does* add is a **labelling
discipline** for repairs (§4) that D11 should adopt for its `revert` label.

## 3. Port call (Q2) — **PARTIAL YES** (lint/grab tool, not a cell)

Port **no swap/repair cell** (we already own the better one, D11). Port the three
**reduced pure contracts** as a grabbable tool, because each is pure, deterministic,
dependency-free and receiptable, and two of them close real holes in our lab:

- `kish_n_eff(corr)` — the **mechanism** of Q1 as an executable (not a slogan).
- `spread_vs_gap(gap, spread)` — the **rule** ("no gap smaller than the spread is a
  finding") + a zero-variance DEGENERATE arm; complements `tools/verdict_gate.py`.
- `repair_label(cited, candidates)` — the resolver's ladder reduced to a pure
  contract: `EXACT | REPAIRED_PRECISE | AMBIGUOUS | MISSING`, **never silently
  upgrading AMBIGUOUS → repaired** (`resolver.py:652-733`).
- `control_beam(...)` — `lanes.py:91-105` + the tautology guard at `:143-157`.

**Written to** `experiments/ft_grab_swap_repair.py`
(sha256 `b80ae4f1c4f6baedc09288c40094d6bad8e45c05ba0876156a42437ab986ee43`,
6,98x B, self-test `python3 experiments/ft_grab_swap_repair.py`, rc=0). No subprocess,
no RNG, no I/O in the primitives — nothing to trap the shell-reparse law.

Demo output (captured):
```
n_eff over 4 correlated learners = 0.29 (of k=4)     # 4 fully-coupled arms collapse
their retraction: NOT_A_FINDING                       # 0.0112 gap < 0.3209 spread
exact-path ladder : EXACT
one-candidate     : REPAIRED_PRECISE
ambiguous         : AMBIGUOUS
unfailable control: CONTROL_UNFAILABLE
tautology control : CONTROL_TAUTOLOGY
honest control    : CONTROL_OK
```

**Recommended adoption (keeper's call):** wire `spread_vs_gap` into
`tools/verdict_gate.py` as a fourth refusal class beside DEGENERATE / TRUNC-B /
status-source — a **max-selection / spread guard** (`verdict_gate.py:8-27`). This is
the one change that would have blocked fleet-triage's published table *and* would
have flagged our own XP-A rho gate (§below).

## 4. Q3 — does BOARD.md's dependency graph imply an instrument our XP-A grid lacks?

**Yes — two.** Our XP-A grid (`experiments/xp_a_instrument_transfer.py:20-45`:
instruments A `verdict_gate pins`, B `step parser`, C `classifier`; 6 known ops ×
4 held-out ops; frozen gates at `:46-62`) measures **detection power**. It has **no
instrument that audits the other instruments' controls**, and **no gate on the gate's
own precision**.

BOARD.md's weight sits in the **dependency edges**, not the counts
(`BOARD.md:41-52`): `syn-AUDITORS → "the method that found the above"` and
`syn-HARNESS → "one rule for all three 'cannot fail' families"`. The missing
instruments those edges imply:

1. **Control-arm integrity instrument** (`lanes.py:91-105` + `:143-157`). XP-A
   instrument A scored **known 0.567 / held-out 0.000** (`RESULTS.md` XP-A entry) —
   A is the "fixed-pin" instrument that **cannot fail** on held-out classes. No control
   arm in the grid was required to be shown **red on deliberately-broken input**, so
   A's inertness was discovered only by the outcome, not pre-fire. `control_beam`
   refuses `CONTROL_UNFAILABLE` and `CONTROL_TAUTOLOGY` (repro==control) up front.
   This is, precisely, our XP-A applying fleet-triage's own lesson to itself: *"an
   instrument reports success unless it has been given a way to fail."*

2. **Precision / n_eff instrument on the grid's own statistic.** XP-A flagged, as a
   caveat, that **at n=3 instruments Spearman has 4-value support {−1,−0.5,0.5,1}, so
   `rho ≥ 0.70 ⟺ rho = 1.0`** — i.e. the frozen gate is **binary/degenerate** by our
   own `verdict_gate` DEGENERATE definition. The grid had no instrument to say so
   before fire. `kish_n_eff` + `spread_vs_gap` are exactly that instrument (their
   `CORRECTION-PROJECTION.md` is the same failure, caught after publication instead of
   before).

**Missing-instrument candidates (ranked):**
(i) control-arm integrity beam on each XP-A instrument (highest value; blocks the
"known≥0.65 but held-out 0.000" shape pre-fire);
(ii) n_eff / spread-vs-gap guard on the grid's own gate statistic (would have moved
XP-A from a confusing INCONCLUSIVE to a correctly-scoped **DEGENERATE gate** finding);
(iii) an **ambiguity-frontier** score: their `PATH_PRECISE_ONLY` carried **9.0% false
positives** while hard outcomes carried 0.5% (`sprint-RESOLVER.md` §4) — i.e. repair
labels are systematically noisier and must be scored as a *separate* population, not
folded into "resolved". Our QG1c residual is an ambiguity frontier of exactly this kind.

## 5. GPU follow-up? (QG1e) — **NO GPU lane implied; a CPU lane is**

Every finding above is **analysis/CPU**: n_eff is arithmetic, spread-vs-gap is a gate,
the repair ladder is pure, XP-A is already a booked CPU lane (`xp_a_instrument_transfer.py`
docstring, `--skip-gpu`), and QG1c's swap residual was resolved without new GPU work.
**Do not pre-register a GPU QG1e on this evidence.**

The natural successor is **CPU** and would be pre-registerable cheaply:
- **QG1e-CPU (proposed, not fired):** apply `control_beam` + `spread_vs_gap` as an
  audit *over* the existing `results/xp_a/` grid (no re-run): (1) for each of A/B/C,
  require a demonstrated red control or label it `CONTROL_UNFAILABLE`; (2) recompute
  the rho gate's support size and flag DEGENERATE. Kill-gate: the audit must be
  reproducible byte-identical x2 at seed 2718.
- **QG1f-CPU (optional):** decompose QG1c's 28 swap-only misses using `repair_label`
  to test whether they are `AMBIGUOUS` (two swap maps both admissible) or
  `REPAIRED_PRECISE` — QG1c found the residual is swap-only at Fisher 7.0e-19
  (`results/qg1c_swap_convention/results.json`, `C0_current`), so labelling the
  ambiguity, not a GPU sweep, is the next honest step.

**GPU is only justified if** QG1f surfaces a *new* swap family requiring batched
exact-state recompute beyond QG1c's six candidates — state that as the explicit
trigger, and keep the lane parked until it fires.

## 6. Artifacts

- `results/qg1d/src-snapshots/` — 22 fetched sources (root/experiments/sim/lineage), shas in `MANIFEST.md`.
- `results/qg1d/RESULTS-ENTRY.md` — this file.
- `experiments/ft_grab_swap_repair.py` — the ported grabbable tool (sha `b80ae4f1…`).
- `results/qg1d/src-snapshots/root/resolver.py` — the citation resolver whose repair ladder (`:652-733`, `:829-856`) was source-read here.

## 7. Honesty notes (booked)

- **Class-mapping is a judgement, not a measurement.** The (a)/(b)/(c) columns in §2
  are my reading of the code against our contract; a second reader could class the
  resolver ladder differently. Flagged, not hidden.
- **Recon premise was partly wrong** (§0). I did not manufacture a "swap routine" to
  match the brief; there isn't one.
- **Not committed, not appended to RESULTS.md** — the keeper folds and re-seals.
- `results/qg1d/src-snapshots` is a *snapshot*; fleet-triage may move under it (their
  own `RESOLVER-DEFECT.md` went stale within one sprint — the tool flagged its own
  auditor, `RESOLVER-FINAL.md` §"Corrections I owe" #3).
