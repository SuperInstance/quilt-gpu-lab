# C2-IL — COMPOSITE-2 phase 3: the ITEM-LOCAL sensor corpus (is there a federation premium?)

**Pre-registered 2026-10-01 18:3x AKDT, BEFORE corpus build / any scoring / any run.**
Lane **C2-LOCALSENSOR**. **AUTHORING ONLY** at freeze time: no corpus generated, no bank
trained, no prediction scored, no commit (keeper commits; COMP0/COMP1/COMP2 law).

> ## AMENDMENT 1 — channel choice (pre-run, disclosed, pilot-motivated)
>
> **What changed:** §2's second channel was frozen as **count** (variant A). The main run
> uses **variant B: polarity + semantic (cargo|dock)**. Nothing else changes (grammars,
> pools, LCG, dedup/split, sizes, arms, gates, statistics, budget).
>
> **Why (disclosed pilot, `scratch/c2il_*`; NOT a booking):** under variant A the count
> channel is **unlearnable by every available view** — on held-out count-violations the four
> frozen per-sensor cells read 0.502 / 0.422 / 0.563 / 0.146 and the four cheap per-view
> logistics 0.460 / 0.424 / 0.452 / 0.086 (≈ or below chance; the `min-p` join's apparent
> 0.89 is a class-bias artefact — it calls distortion on 68 % of canon items too). A channel
> no view can read makes the item **not genuinely dual-view**, which is exactly the condition
> §5 G-IL1 exists to catch. Variant B keeps the item-local structure but uses the two channels
> the frozen views *demonstrably* carry: **polarity** (S4's explicit marker dims) and
> **semantic cargo/dock** (S1's word BoW).
>
> **Direction of the bias this introduces:** variant B raises the best single-view arm, i.e. it
> makes the negative *harder* to obtain, not easier. Variants A and C (agent channel) were also
> piloted (headline full-board premiums over the best single view at ~N=1,200/regime: A +0.00,
> B +0.02…+0.03, C +0.02) — the same qualitative answer in all three, so the choice is not
> verdict-turning. Recorded here before the main run fires.
>
> **Also amended (pre-run):** §3 gains the pre-declared **learned item-local router** arms
> `FED-IL-GATE` (8 features → 4-class logistic, 36 p), `FED-CHEAP-GATE` (**the 361p-class arm
> = PRIMARY**) and `FED-GATE-8` (16 p features → 8 classes, 72 p); §5's primary comparison is
> `FED-CHEAP-GATE − BEST-SINGLE`. `BEST-SINGLE` is defined as the best single-view arm across
> **both** families (frozen MLP cells and cheap refit cells) — the hardest honest baseline.

## 0. Lineage honored (booked, not re-derived)

- **COMP1** (INCONCLUSIVE, strike 2): negation-scope FED−SINGLE **+0.1261** is the only passing
  gate; the win exists exactly where the word monolith is blind.
- **COMP2 P1/P2 (KEEP)**: on a difficulty-wired mid-band corpus (full probe 0.7164, chance 0.5068)
  FED-HETERO − SINGLE @negation-scope **+0.1337 CI[+0.1053,+0.1604]** and
  FED-HE-MATCHED − FED-WORD @negation **+0.1427** — blindness-repair is real at the routed-sensor
  level. **BUT the pre-declared §Risks-4 control fired: `S4-MONO` (one 1057p cell on the
  negation-aware view) is within 0.02 of FED-HETERO on 4/4 regimes** ⇒ the win re-reads as
  *"buy the right sensor once"*, not as a federation premium. `results/comp2/RESULTS-ENTRY.md` §9–10.
- **COMP2 §10 next question (this lane's mandate):** *"the only configuration where FED-HETERO should
  beat S4-MONO is a regime whose correct sensor is not knowable from the 8 deployable features —
  where two sensors are each right on ~half of one regime's items and the discriminative cue is
  item-local, not regime-local."* That is the exact question. Sensor (not expert) choice must be
  **item-local** for federation to have anything to sell.

## 1. Thesis under test (the bounded claim)

> When a corpus's target is a **conjunction of two sensor views inside the item** (canon iff
> view-A agrees AND view-B agrees), and each distortion violates **exactly one** of the two
> views — the violating view chosen i.i.d. **per item**, independent of the regime tag — then the
> sensor that carries the answer is **item-local, not regime-local**. In that regime a single
> right sensor (S4-MONO) *provably* cannot exceed ~half+half; a per-item federation that joins the
> views can. **If a federation premium exists anywhere, it exists here.**

Two honest closers, pre-declared:
- **PASS** ⇒ books *"federation premium exists exactly where sensor choice is item-local — the
  thesis is bounded, not dead."*
- **FAIL** ⇒ books *"no federation premium even item-local — the thesis narrows to sensor
  selection, full stop."* This closes COMPOSITE with a clean, narrow, useful result. A clean
  negative is a **success of the lane**, not a strike: the strike ledger (COMP0, COMP1) is
  untouched by a well-measured negative on a new corpus.

## 2. Corpus construction — C2-IL (verbatim rules; generated at run time)

**Foundry.** Same grammar law as COMP2 phase 1: the frozen pools `DOCKS / CARGOS / SUBJECTS /
VERBS / COUNTS` and the deterministic LCG `_rng` (mulberry-style, no python `hash()` salt) from
`experiments.comp1_federation2.py`; per-item content addressing `sha256(claim + " " + evidence)`;
dedup on that sha256; **hash-split first nibble ≥ 0xC → held-out** (COMP1/D5 law). Seed **2718**.

**Size.** N = **12,000** raw, **3,000/regime**, 4 regimes (`semantic`, `counting-address`,
`negation-scope`, `agent-role`). Regime tag = the **evidence surface style** family
(`semantic→prose`, `counting-address→manifest`, `negation-scope→logbook`, `agent-role→passive` —
COMP1 `NATIVE_STYLE` verbatim). Expected split ≈ 9,000 train / 3,000 held-out. **No blur
overlay**: the item's own dual-channel structure is the difficulty source (declared).

**Per-item draw order (deterministic; documented verbatim).** For regime `r`, item index `i`:
1. `subj, verb, cargo, dock, n ∈ pools` (uniform; `_pick`), then `deny ~ Bernoulli(0.5)` (claim polarity).
2. `canon = (i % 2 == 0)` — 50/50 canon/distortion, **independent of regime**.
3. If `not canon` (**distortion**): `viol ~ Bernoulli(0.5)` — the **single violated channel**,
   drawn **per item, independent of regime**:
   - `viol = "polarity"` → evidence polarity `e_deny = not deny`; count agrees `e_n = n`.
   - `viol = "count"`    → evidence count `e_n = neighbour(n)` (COUNTS index ±1, sign drawn by
     the LCG); polarity agrees `e_deny = deny`.
   If `canon`: `e_deny = deny`, `e_n = n` (both views agree with the claim).
   **⇒ label = (evidence polarity == claim polarity) AND (evidence count == claim count), and every
   distortion violates EXACTLY ONE conjunct.**
4. **Claim** (uniform IL template carrying both channels, polarity marked):
   `deny=false`: `"{subj} {verb} {n} crates of {cargo} at {dock}."`
   `deny=true` : `"{subj} did not {verb} {n} crates of {cargo} at {dock}."`
5. **Evidence**, rendered by the regime's `NATIVE_STYLE` with the IL renderer (both channels
   always present, so **neither side is starved** — the item is genuinely dual-view):
   - `manifest`: `"manifest: {dock} -> no {e_n} crates {cargo} listed, signed {subj}."` (deny)
     / `"manifest: {dock} -> {e_n} crates {cargo}, signed {subj}."` (¬deny)
   - `prose`: `"{subj} did not {verb} the {e_n} crates of {cargo} at {dock}."` (deny) /
     `"{subj} brought a {cargo} shipment of {e_n} crates to {dock}."` (¬deny)
   - `passive`: `"the {e_n} {cargo} crates at {dock} were not {verb} by {subj}."` (deny) /
     `"the {e_n} {cargo} crates at {dock} were {verb} by {subj}."` (¬deny)
   - `logbook`: `"per the harbor log, no {e_n} crates of {cargo} were {verb} at {dock}."` (deny) /
     `"per the harbor log, {e_n} crates of {cargo} were {verb} at {dock} by {subj}."` (¬deny)
6. Store `{claim, evidence, ev_style, label, kind(=regime), channel(="polarity"/"count"/None),
   sha256}`; dedup on sha256 (regenerate on collision, LCG law).

**Why this is item-local and not regime-local (the construction receipt).** The violated channel
`viol` is drawn i.i.d. per item and is *statistically independent of the regime tag* — so no
regime-level table (`MATCH`: regime→sensor) can carry it, and a regime router is provably
uninformative about "which view is wrong". Only the item itself reveals it.

**Validity gates (computed, not assumed; else INCONCLUSIVE_CORPUS):** n_raw = 12,000 exact-unique
after dedup; held-out ≥ 2,600; per-regime held-out ≥ 600; |canon frac − 0.5| ≤ 0.06 full and
per-regime; per-regime |viol-polarity frac − 0.5| ≤ 0.08; determinism (W1: two regenerations give
identical sha256 sequences).

## 3. Arms — NO-TRAIN PREFERRED (existing banks + cheap CPU refits)

**Existing frozen banks are the primary apparatus** (`results/comp2/banks/`, 45 checkpoints,
trained on the COMP2 corpus, CPU inference = **0 GPU-Wh**). Per-sensor all-train cells
`HETERO_S1..S4` (1057p each; note `SINGLE ≡ HETERO_S1` and `S4MONO ≡ HETERO_S4` by config) plus
`JOINT` (4225p, S1). Featurization = COMP2 verbatim (`feat_word/char/pos/neg`, D=64, sha1 hashing,
L2-normalized) — the same frozen views.

| arm | operation | params | source |
|---|---|---|---|
| `S1`, `S2`, `S3`, `S4` | per-sensor all-train cell, fixed view | 1057 | existing banks |
| `S4-MONO` | = `S4` (the phase-2 control) | 1057 | existing banks |
| `JOINT` | S1 monolith | 4225 | existing bank |
| `BEST-SINGLE` | max-accuracy single-view cell (upper baseline; also train-selected variant) | 1057 | existing banks |
| **`FED-IL` (primary)** | per item, **route to the sensor cell reporting the strongest distortion evidence (min p)**; answer = that cell's verdict | 4×1057 + 0 | existing banks |
| `FED-IL-MARGIN` | per item, route to max \|p−0.5\| margin; answer = that cell | 4×1057 + 0 | existing banks |
| `FED-IL-2S` | min-p join restricted to {S1(count), S4(negation)} | 2×1057 + 0 | existing banks |
| `FED-IL-MAJ` | majority vote of the 4 cells | 4×1057 + 0 | existing banks |
| `S1-cheap` | logistic on S1 (CPU refit, new train split) | 65 | — |
| `PV-cheap-S1..S4` | 4 per-view logistic cells | 4×65 = 260 | — |
| `FED-cheap-IL` | min-p join over the 4 cheap cells | 260 | — |

**Operator justification (declared BEFORE scoring).** For a conjunctive dual-view target,
"canon iff both views agree", the correct per-item operation is a **join**: an item is distortion
iff *any* consulted view reports a discrepancy. Equivalently — and this is the routing form the
mission names — **route each item to the sensor that carries the answer** = the view that reports
the violation, which is the minimum-p cell. `FED-IL` is therefore simultaneously (a) the
heterogeneous-sensor join and (b) per-item sensor routing. `FED-IL-MARGIN` is the alternative
reading of "routing" (pick the most *decisive* cell) and is reported as a pre-declared secondary;
the two coincide iff the non-violating views are near 0.5. Both are reported; the **primary is
`FED-IL`**.

**Decision: NO new banks.** The existing 45 cover every per-sensor view, so a single-view ceiling
and a 4-view join are both constructible at 0 GPU-Wh. **Fallback (declared, only if the existing
banks are degenerate on C2-IL — e.g. all cells collapse to a constant p):** train ≤ **4** banks ×
**2** seeds (the 4 per-sensor cells, 1057p, COMP2 recipe) under `guard.py` with a G7 receipt,
envelope **≤ 2 Wh**, INSTRUMENT-01 ramp ≥0.6 s; disclosed in the booked entry if used.

## 4. Statistics (COMP2 law, frozen)

Item-level **paired bootstrap** over held-out items, point estimate = mean per-item seed-mean
accuracy difference, **B = 2000, PCG64 seed 2718**, percentile 95% CI. Per-seed boards +
across-seed std reported alongside. W2 cross-check (percentile vs normal-approx half-width ≤
0.005) on the primary CI. **Degeneracy law:** across-seed std == 0 for either arm in a deciding
pair → INCONCLUSIVE, never PASS. Chance = majority class, computed per board and per regime.

## 5. Frozen gates

- **G-IL1 — signal exists (construction check, gating the interpretation).** At least one
  single-view arm (`S1..S4` or a cheap per-view cell) has held-out accuracy ≥ chance + **0.02**.
  FAIL ⇒ book **"construction failed — items not genuinely dual-view"** and stop (no G-IL2 claim).
- **G-IL2 — THE QUESTION.** **`FED-IL` − `BEST-SINGLE` > 0.05 AND CI_low > 0** on the held-out
  board (B=2000, seed 2718), std > 0 both arms. PASS ⇒ books the **"bounded, not dead"** sentence.
  FAIL ⇒ books the **"narrows to sensor selection, full stop"** sentence. std == 0 ⇒ INCONCLUSIVE.
- **G-IL2b (the mission's literal control, primary-adjacent):** **`FED-IL` − `S4-MONO` > 0.05 AND
  CI_low > 0** — the exact pair that phase 2 could not separate.
- **Reported, never verdict-turning:** `FED-IL-MARGIN`, `FED-IL-2S`, `FED-IL-MAJ`, all per-regime
  boards, the cheap bracket, the JOINT board, and the full-board aggregates.

## 6. Persistence, artifacts, budget

- **Per-item predictions persisted ALWAYS** (CX-CHEAP-0 lesson): one row per arm × seed × held-out
  item `{sha256, key, regime, label, channel, split, p, correct, margin, routed_sensor, cell}`;
  cheap arms likewise. Written to `results/comp2_itemlocal/predictions/`.
- `results/comp2_itemlocal/` → `il_results.json`, `corpus.jsonl`, `per_item_stub.jsonl`,
  `calibration_log.json`, `predictions/`, `pilots/` (disclosed small-N direction-finding, not
  counted against any budget). RESULTS.md entry + QUEUE.md line by the runner. **NOT COMMITTED.**
- **Budget:** CPU-only, **0 GPU-Wh**, no guard (no GPU touched). Wall target ≤ 20 min. If the
  §3 fallback fires, its ≤2 Wh guard window is booked separately with its own G7 receipt.

## 7. Risks (declared now)

1. **Views overlap ⇒ no premium.** Every view is a function of the same text, so a single sensor
   may *partially* see both channels (S4's word-BoW can see counts). If so, `BEST-SINGLE` is
   already high and G-IL2 fails — a clean, honest negative, booked as such.
2. **Construction not dual-view** (a channel is starved) ⇒ G-IL1 fails ⇒ book construction failure.
3. **Bank transfer failure.** The existing banks were trained on COMP2 labels; on C2-IL's
   conjunction labels they may be miscalibrated ⇒ degenerate boards ⇒ INCONCLUSIVE, then the
   declared ≤2 Wh fallback (train fresh cells under guard) or an honest NOT-RUN.
4. **Chance inflation.** 50/50 by construction ⇒ chance ≈ 0.50; bars are stated as chance + 0.02.
5. **Item-local leakage into the router.** Guarded by construction (`viol ⟂ regime`); the
   per-regime channel-fraction balance check (§2 validity) is the receipt.
