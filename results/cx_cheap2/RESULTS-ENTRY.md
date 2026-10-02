# CX-CHEAP-2 — zero-parameter surface regime repair of the unreachable signal (CPU, ~2.2 s, 0 Wh)

- lane: CX-CHEAP-2 (FINAL move of the cheap-gate thread; follows cx_cheap0/1) · device: **CPU only,
  numpy+sklearn** (no GPU, no torch) · seed 2718 · **~2.2 s wall, 0 Wh** · reuses
  `experiments/cx_cheap1.py` harness wholesale (COMP1 featurization, margins, 2-arm FED/SINGLE, the
  within-set FED≠SINGLE restriction, the per-item win label) via `experiments/cx_cheap0.py` +
  `experiments/ring_cx0.py` helpers.
- **BOOKED QUESTION:** CX-CHEAP-1 found the oracle's TRUE-regime signal *inside* the disagreement set
  (negation one-hot AUC 0.6223; true-regime 4-way logistic **0.6173**) while the frozen 0-param router reads
  **chance (0.5003)** there — *the signal exists but is unreachable*. Can a **ZERO-PARAMETER regime repair**
  make it reachable **for free**?
- **KEY INSIGHT EXPLOITED:** the regimes are NAMED after **surface structure** (negation markers / count
  words / role nouns / residual), so a handcrafted surface classifier over the raw item text needs **zero
  training**.
- wiring: router held-out top-1 **0.735593 → 0.7356 == booked 0.7356** (match at 4 dp, wiring green, 4th
  consecutive lane). Split 1810 / 590. Within-set: **n_disagree = 184, n_win = 103**, win-rate|disagree
  **0.5598** (matches CX-CHEAP-1 exactly). Reference arms re-derived here reproduce cx_cheap1 to the digit:
  **TRUE-regime oracle 0.6173**, **frozen router 0.5003**.

## The 0-parameter surface classifier (preregistered rule order — first hit wins)

Deterministic regex/token heuristics over the raw item text; **0 parameters, 0 training, no labels**.

| rule | cue (claim text) | ⇒ regime |
|---|---|---|
| **R1 NEGATION** | `\bnot\b` \| `n't` \| `\bnever\b` \| `\bno\b` | negation-scope |
| **R2 COUNTING-ADDRESS** | a count word (number-word `one..twelve` or digit) directly quantifying the cargo noun (`N crates`) **or** `crates of` | counting-address |
| **R3 AGENT-ROLE** | the cargo/role noun `crates` (no count) | agent-role |
| **R4 RESIDUAL** | otherwise | semantic |

Tie-break order preregistered R1→R2→R3→R4 (documented before the held-out pass). Rules fixed from **TRAIN**
surface statistics only. Note (booked): a first-fire version let bare digit tokens fire R2 — location ids
(`berth-9`, `pier-1`) made *every* claim "numeric" and collapsed agent-role recall to 0; fixed to a
**number+CARGO-NOUN phrase** cue (`N crates`).

## G-R1 — 0-param regime ID accuracy (need ≥ 0.70 held-out)

- **HELD-OUT accuracy 0.8729 → PASS** (TRAIN 0.8862). Per-regime held-out recall:
  semantic **1.000** · counting-address **1.000** · agent-role **1.000** · **negation-scope 0.493**.
- **within-disagreement accuracy 0.8098** (the subset that matters) vs the **frozen router's within-set
  regime-ID accuracy 0.6522** — and vs the router's within-set **win-prediction AUC 0.5003** (the 0.500 the
  mission quotes; reproduced exactly).
- **Confusion headline (held-out, rows=true):** the classifier is **perfect on 3 of 4 regimes**; *every*
  error is **negation-scope → semantic** (75 held-out; 35 inside the disagreement set). These are the
  negation-scope items whose negation marker lives in the **evidence** ("no X load listed", "was not logged")
  rather than the claim — the claim's only negation cue is then absent, so R1 misses and the item falls to
  the R4 residual bucket.

## G-R2 — repaired labels through the CX-CHEAP-1 oracle machinery (need within-set AUC ≥ 0.60)

Plug the surface classifier's **repaired regime one-hots** into the cx_cheap1 oracle path (logistic fit on
TRAIN-disagreement, evaluated on HELD-OUT-disagreement, label = FED correct AND SINGLE wrong):

| arm | within-set AUC | verdict |
|---|---|---|
| **repaired one-hots — logistic** | **0.5334** | FAIL |
| **repaired one-hots — tree(d2)** | **0.5403** | FAIL (best) |
| reference: TRUE-regime one-hots (oracle) | 0.6173 | (the bar) |
| reference: frozen-router one-hots | 0.5003 | (chance) |

- **G-R2 FAIL** (best 0.5403 < 0.60). G-R1 PASS but G-R2 FAIL.
- **Sensitivity (post-hoc, NOT preregistered):** a *richer* surface cue — negation-scope's own cargo form
  `load` + negation marker anywhere in the item — lifts board accuracy to **0.9339** (negation recall 0.493 →
  0.736) and within-set accuracy to **0.8913**, yet within-set AUC only reaches **0.5826 — still FAIL**.
  Ceiling with *perfect* labels is the oracle's **0.6173**. So the failure is **robust**, not an artefact of
  the literal rule set.
- **Why (booked mechanism):** the win-signal lives on the **negation-vs-rest axis** (true win-rate|disagree
  negation **0.754** vs semantic 0.400 / counting 0.500 / agent 0.510). The surface repair's residual error
  sits on *exactly that axis*: within-set negation recall is only 22/57 = **0.386**, and the misassigned
  negation items land in the semantic bucket (win-rate 0.40), diluting the repaired negation win-rate to
  **0.636** (from 0.754). The AUC gradient is steep — within-set acc 0.810 → 0.533 · 0.891 → 0.583 ·
  perfect → 0.617 — so the oracle bar is reachable **only** with near-true labels. A realistic 0-param
  surface repair lands **below** it.

- **win-rate|disagree, TRUE vs REPAIRED (held-out disagreement set):**

| regime | TRUE win-rate | REPAIRED win-rate |
|---|---|---|
| semantic | 0.400 | 0.600 |
| counting-address | 0.500 | 0.500 |
| negation-scope | **0.754** | **0.636** |
| agent-role | 0.510 | 0.510 |

## G-R3 — bootstrap std over 5 refits

- boot AUCs **[0.5334, 0.5543, 0.5334, 0.5471, 0.5471]**, **std 0.0083 > 0 → PASS** (not a frost-law
  artefact; the near-chance result is real).

## VERDICT

**G-R1 PASS · G-R2 FAIL · G-R3 PASS ⇒ the repaired labels do NOT carry the win-signal: regime identity is
NOT the structure the oracle read.**

The surface classifier proves regime identity is *nearly* free — **0 parameters, 0 Wh, 0.87 board accuracy,
perfect on 3 of 4 regimes** — and it reads the regime **far better than the deployable router where it
matters (within-set 0.810 vs 0.652)**. But the win-signal is concentrated on the single negation axis, and the
surface repair's residual error lands precisely there (within-set negation recall 0.386), diluting the one
regime-modulated win-rate the oracle exploits. A richer surface cue (~0.93 board) recovers only to AUC 0.583;
the 0.60 bar is cleared only by the **true** labels (0.6173). So the unreachable signal is **not** made
reachable for free: it is reachable only with labels the surface cannot supply at that precision — the
residual error is on the axis that matters.

**Cheap-gate thread closure (RING-CX-0 → CX-CHEAP-2):** the untrained ring fires on corpus geometry, not the
blind regime (RING-CX-0/1); a *cheap trained* gate detects the REGIME but not the per-item win (RING-CX-2);
no deployable feature predicts the per-item win *within* disagreement (CX-CHEAP-0/1); and a **0-parameter
surface repair** recovers regime identity for free yet still cannot carry the win-signal (this lane). **The
whole thread closes negative: cheapness buys the boundary and the labels, never the per-item answer win.**

- **Artifacts:** results/cx_cheap2/{cx_cheap2_results.json, RESULTS-ENTRY.md}. Code: experiments/cx_cheap2.py.
  Repro lineage: experiments/cx_cheap1.py → cx_cheap0.py → ring_cx2.py → ring_cx0.py. **NOT COMMITTED.**
  ~2.2 s wall, 0 Wh, CPU numpy+sklearn, no GPU, no torch.
- **Next question:** none inside this thread — **thread closed** (RING-CX-0 through CX-CHEAP-2). Standing
  follow-ups live elsewhere: the MLP-retirement gap (regime-symmetry AND the +0.126 negation win in one cheap
  arm) and the per-regime board target question (is the negation win the only board worth chasing?).
