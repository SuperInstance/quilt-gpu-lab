# COMPOSITE-2 phase 2 — ARMS (federation v3): 6 MLP banks × 3 seeds, heterogeneous sensors, learned sensor-picking router

**Ran:** 2026-10-01 18:1x–18:3x AKDT · `experiments/comp2_arms.py` (outer → guarded inner → CPU/cheap)
**Prereg:** `proposals/runs/COMPOSITE-2-federation3.md` (frozen 2026-10-01 17:2x, read as the spec)
**Phase 1 precondition:** corpus FROZEN + F-GATE GREEN at iteration 5 (`results/comp2_corpus/`, verify 21/21 PASS) — read read-only, not re-derived.
**Cost:** GPU **1.1113 Wh** measured (envelope **≤ 20 Wh**; prereg estimate ~16 Wh) · 813.4 s inner wall / 278.7 GPU-s · mean power 4.92 W · max temp **53 C** · min free VRAM 5,315 MiB · **seat free, no co-tenant**. CPU phases (router, bootstraps, cheap bracket) run **outside** the guard window at **0 added GPU-Wh**. **G7 receipt `g7-wr-composite-2-federation3-1790906923` VALID (PASS).** INSTRUMENT-01 ramp **0.609 s synced** before the measured window. **NOT COMMITTED.**

## VERDICT — **KEEP** (lattice: P1 ∧ P2 PASS) · **NARROWED by the pre-declared S4-MONO control**

| gate | reading | bar | verdict |
|---|---|---|---|
| **P1 (primary, blind regime)** FED-HETERO − SINGLE @negation-scope | **+0.1337** CI[+0.1053, +0.1604] | ≥ +0.08 ∧ CI_low>0 | **PASS** |
| **P2 (primary, sensor-not-just-expert)** FED-HE-MATCHED − FED-WORD @negation-scope | **+0.1427** CI[+0.1134, +0.1731] | > 0 ∧ CI_low>0 | **PASS** |
| **P3 (primary, LA at zero premium)** FED+LA − FED-HETERO @negation-scope | +0.0070 CI[−0.0026, +0.0164] | > 0 ∧ CI_low>0 | **FAIL** |
| **P4 (retirement, dual corpus)** G4a 0.1351 / G4b 0.1147 max\|Δ\| vs the 0.02 bar | both FAIL | G4a ∧ G4b | **NOT-RETIRED** |

No degeneracy: every seed-mean std in every deciding pair is **> 0** (0.0002–0.0159); no truncation (3/3 seeds); router bands all inside [0.40, 0.95]. **Neither strike-3 path fired** (P1 CI_high +0.1604 ≫ +0.08; wiring was green in phase 1) — the ledger holds at 2, thesis suspended-then-KEPT, not retired.

### The sentences this run books

- **P1 books:** *on a difficulty-wired mid-band corpus (full probe 0.7164, chance 0.5068), a bank of HETEROGENEOUS-SENSOR cells whose router picks the SENSOR beats the best same-view single cell on the pre-declared blind regime by +0.1337 (2.2× the +0.08 bar, CI excludes 0) — blindness-repair is real at the routed-sensor level.*
- **P2 books:** *the win is the SENSOR, not merely the expert partition: structurally-matched-sensor slice cells beat the same-partition same-view (S1) slice bank on the blind regime by +0.1427 (CI excludes 0).*
- **P3 books:** *LA buys **nothing** where the thesis needs it, so **LA is closed to a D1b footnote** regardless of KEEP (it does win +0.0258 on the full board and on semantic/counting/agent — the failure is specifically the blind regime, where the routed S4 cell is already right, so LA rarely fires).*
- **The narrowing books (prereg §Risks-4 rule, pre-declared):** *S4-MONO — one 1057p cell on the negation-aware view — is within 0.02 of FED-HETERO on **4/4** regimes (and **beats** it on negation 0.8002 vs 0.7713 and counting 0.6715 vs 0.6436), so the P1/P2 wins re-read as **"buy the right sensor once"**, not as a federation premium.* Honest narrowing, not a verdict change.
- **Full-board kill re-booked (secondary forever, never verdict-turning):** FED-HETERO − SINGLE full **−0.0267** CI[−0.0388, −0.0145]; FED-HETERO − JOINT full −0.0241; FED-HE-MATCHED − FED-WORD full **−0.0455** CI[−0.0579, −0.0332]. The negation win is bought by giving up semantic (−0.1119) and agent-role (−0.1105).

## 1. Corpus provenance (frozen, verified — not regenerated)

`results/comp2_corpus/corpus.jsonl`, 24,600 items, 7,584,332 bytes, file sha256 `e87c7e3c32e8fcde1bd85ee484b318e707069dc910310e4459eea0503e5a2959`. The **per-item sha256 sequence reproduces phase 1's booked `5bc6b78f0a4b5948…`** (sha of the concatenation of the 24,600 per-item hashes) ⇒ the arms were trained on the *frozen* corpus, not a regeneration. Split by hash nibble: **train 18,379 / held-out 6,221** (semantic 1,579 · counting 1,587 · negation 1,523 · agent 1,532) — matches phase 1 exactly. Majority chance computed: full 0.5068, semantic 0.5104, counting 0.5135, negation 0.5194, agent 0.5163.

## 2. Bank training headline (GPU, guarded)

**45 banks = 6 arm-families × 3 seeds** (per seed: JOINT, SINGLE, S4MONO, 4× FED-WORD slice cells, 4× FED-HETERO all-train sensor cells, 4× FED-HE-MATCHED slice cells). Sizes per prereg: JOINT 4225p (64→64→1), SINGLE / S4MONO / all cells 1057p (64→16→1), FED banks 4228 + 36p router.

- **14,886,990 item-updates** (prereg estimate ~13M) · Adam lr 1e-3, BCE, batch 16, fp32 CUDA · all-train 30 ep on 18,379 items (551,370 updates/cell), slice 30 ep on 4,563–4,627 items (136,890–138,810 updates/cell).
- **All 45/45 banks decreased their loss.** Examples: JOINT 0.6905→0.5649 · SINGLE 0.6912→0.5628 · S4MONO 0.6839→0.5206 · HETERO-S4 0.6815→0.5207 · HEMATCH-negation 0.6787→**0.1319** (the S4 negation slice is near-separable) · HEMATCH-agent 0.6929→0.6761 (hardest). **No NaN / divergence** — the fail-loud check (`non-finite loss → raise`, every 200 steps) never fired.
- **Energy: 1.1113 Wh** — well inside the envelope, and 10.6× below COMP1's booked 11.76 Wh for ~2.3× less work, because COMP1 ran with a co-tenant (min free VRAM 1,475 MiB) while this run had the seat (min free 5,315 MiB). Mean power 4.92 W reflects the launch-bound tiny-batch regime (batch 16 on 64-dim inputs); the run is Python/launch-bound (~1.1 ms/step, 18.3k item-updates/s), not compute-bound.

## 3. Boards (seed-mean over 3 seeds; per-seed + across-seed std in `comp2_results.json`)

| arm (params) | full | semantic | counting-address | **negation-scope** | agent-role |
|---|---|---|---|---|---|
| `JOINT` (4225) | 0.7184 | 0.8554 | 0.6593 | 0.6354 | 0.7211 |
| `SINGLE` (1057) | **0.7211** | **0.8619** | 0.6587 | 0.6376 | 0.7237 |
| `S4-MONO` (1057) | 0.7192 | 0.7488 | 0.6715 | **0.8002** | 0.6575 |
| `FED-WORD` (4228) | 0.7169 | 0.8446 | 0.6931 | 0.6529 | 0.6736 |
| `FED-HETERO` (4264) | 0.6944 | 0.7501 | 0.6436 | 0.7713 | 0.6131 |
| `FED-HE-MATCHED` (4264) | 0.6714 | 0.6470 | 0.6879 | 0.7956 | 0.5561 |
| `FED+LA` (0 premium) | 0.7202 | 0.7904 | 0.6604 | 0.7783 | 0.6521 |
| *chance* | *0.5068* | *0.5104* | *0.5135* | *0.5194* | *0.5163* |

Across-seed std (full): JOINT 0.0018 · SINGLE 0.0002 · S4MONO 0.0019 · FED-WORD 0.0013 · FED-HETERO 0.0022 · FED-HE-MATCHED 0.0064 · FED+LA 0.0013. **Note the monolith is NOT below regime chance here** (COMP1's failure mode is repaired): SINGLE beats the F1 probe (0.7211 vs 0.7164) and FED-HETERO clears chance everywhere.

## 4. Learned sensor-picking router (36p, CPU, TRAIN-only)

8 frozen features (4 per-sensor centroid-Pearson ⊕ 4 per-sensor TRAIN-fit cheap-logistic margins) → multinomial logistic (lbfgs, C=1.0, seed 2718) on regime labels. **36 params = 32 weights + 4 intercepts.**

- learned top-1 **held-out 0.6832** / train 0.6901 (chance 0.25) — **in band**.
- COMP1-verbatim 0-param per-regime S1 centroid top-1 (the FED-WORD router) **0.7491** — in band.
- per-sensor centroid top-1 alone **0.5343** — in band. **All three validity bands PASS** → corpus valid.
- **within-disagreement routing accuracy = 0.6007** (n = 4,292 items where the 4 sensors' answers differ) vs the ≥ 0.60 target — **clears the bar**, against CX-CHEAP-1's booked 0.5003 chance-within-disagreement. Reported, not gating.

## 5. Statistics receipt (frozen law)

Item-level **paired bootstrap** over the 6,221 held-out items, B = 2,000, PCG64 seed 2718; point estimate = mean of the per-item seed-mean diff; per-seed boards + across-seed std reported alongside. **W2 cross-check** (percentile vs normal-approx half-width, bar ≤ 0.005): P1 0.0009 · P2 0.0037 · P3 0.0001 — all PASS. **P1 was not borderline** (CI_low +0.1053 > 0), so the pre-declared B = 10,000 top-up was **not** invoked (`P1_topup: null`). Achieved half-width ±0.0275 vs the prereg's power model ±0.030 at N = 24,600 ✓.

## 6. Cheap-arm 361p bracket (P4, dual corpus, CPU, 0 GPU-Wh)

SINGLE-cheap = logistic on S1 (65p); FED-cheap-hetero = 4 logistic cells on S1–S4 (260p) + the SAME 36p router = **361p**.

| | G4a — frozen COMP1 corpus (1810/590) | G4b — in-corpus C2 (18,379/6,221) |
|---|---|---|
| `FED-cheap` full | 0.5712 | 0.6968 |
| `SINGLE-cheap` full | 0.5271 | 0.7172 |
| per-regime Δ (sem/count/**neg**/agent) | −0.0568 / −0.0407 / **+0.1351** / 0.0000 | −0.0808 / −0.0504 / **+0.1147** / −0.0600 |
| max\|Δ\| vs the 0.02 flatness bar | **0.1351 FAIL** | **0.1147 FAIL** |
| negation FED-cheap − SINGLE-cheap | **+0.2432** CI[+0.1554, +0.3243] (bar +0.126, CI excl 0) | **+0.1372** CI[+0.1077, +0.1641] (bar +0.126, CI excl 0) |
| verdict | **FAIL** | **FAIL** |

**P4 verdict: NOT-RETIRED** (G4a ∧ G4b both required; both fail on flatness). **The prereg's hypothesis is falsified:** the sensor-picking router does **not** supply regime-flatness in the cheap class — it *improves* negation (+0.135/+0.115) while *hurting* semantic (−0.057/−0.081) and agent (−0.06 in-corpus). This is a different failure mode from CX-CHEAP-0 (which failed the negation Δ itself at +0.054 over); here negation is comfortably cleared and the flatness bar is missed. **The 4228p MLP's unmatchable property stands** — regime-symmetry *and* the negation win *simultaneously*.

## 7. Harness revisions (disclosed, caught before booking)

1. **Router-label scramble (caught pre-run).** `sklearn`'s `classes_` is alphabetical, not `REGIMES` order; the first CPU pass indexed routing with `REGIMES[j]` and scrambled every routed arm (learned top-1 read 0.4144 instead of 0.6832; FED-HETERO/FED-HE-MATCHED boards wrong). Fixed to index with `clf.classes_` and re-smoked before the GPU run fired. No GPU time was spent on the wrong wiring.
2. **FED-WORD per-item dump (caught post-run, re-dumped at 0 GPU-Wh).** `write_predictions` dumped FED-WORD with the *learned* router's regime instead of the 0-param **centroid** router's (the gates/boards were computed in-memory and were always correct; only the persisted dump was wrong, so it would have violated the persistence mandate). Fixed; `--cpu` + `--cheap` re-run CPU-only. All 7 prediction files now reproduce the booked boards exactly (verified `max|Δ| < 1e-3` across all 35 arm×board cells), and P2 recomputes to +0.1427 from the dump.
3. **Centroid-feature definition (pre-run).** The first reading of "4 per-sensor centroid-Pearson scores" used one all-train centroid per sensor (top-1 0.2816, below band). Re-read as each sensor's centroid *of the regime that sensor is tuned to*, in that sensor's own space (0.5343, in band); the COMP1-verbatim per-regime S1 centroid router is kept separately for FED-WORD (0.7491, in band). Both are reported; the band gate requires **all three** centroid/learned readings in band.

## 8. Artifacts

`results/comp2/` → `comp2_results.json` (per-seed + seed-mean boards, all bootstrap CIs, W2 cross-checks, router audit, LA triggers/flips, τ, ramp receipt, power receipt, verdict + interpretation) · `inner_report.json` (45 bank loss traces, update counts, slice sizes, corpus sha, ramp) · `banks/*.pt` (45 checkpoints) · `raw/seed{2718,2719,2720}.npz` + `raw/features.npz` + `raw/router.npz` · `predictions/{JOINT,SINGLE,S4MONO,FED_WORD,FED_HETERO,FED_HE_MATCHED,FED_LA}.jsonl.gz` — **130,641 rows = 7 arms × 3 seeds × 6,221 held items**, every row `{sha256, key, regime, label, split, p, correct, margin, routed_sensor, cell, la_trigger, la_flip}`; keys align 1:1 with phase 1's `per_item_stub.jsonl` (verified) · `cheap/cheap_bracket.json` + `cheap/predictions_{comp1,c2}.jsonl.gz` · `guard/` (guard_summary + valid G7 receipt + ledger) · `wh_receipt.json`. Total 14 MB on `/home` ext4. Code: `experiments/comp2_arms.py`. **NOT COMMITTED.**

## 9. What this establishes, and what it does not

**Establishes:** on a corpus wired to mid-band difficulty *before* any arm fired, heterogeneous-sensor federation with a learned sensor-picking router **does** repair the pre-declared blind regime: +0.1337 over the best single cell (P1) and +0.1427 for sensor-matching over expert-partition alone (P2), both CI-excluding-0, with no degeneracy and with the router resolving the regime where the disagreement lives (0.6007 ≥ 0.60, the exact CX-CHEAP-1 gap). This is COMP1's negation-only win **reproduced on a corpus where the monolith is no longer at chance** — so the effect is not a floor artifact.

**Does not establish a federation premium.** The pre-registered §Risks-4 control fired: **S4-MONO alone (1057p, the right sensor bought once) matches FED-HETERO on all four regimes**, and the full-board aggregates are *negative* for every federation-vs-monolith contrast. LA is closed (P3 FAIL). The cheap 361p class is not retired (P4 NOT-RETIRED). The honest surviving claim is *"sensor choice, not federation, is the purchase"* — which is exactly the narrowing the prereg pre-declared rather than a new discovery.

## 10. Next question

Given the narrowing, the live question is whether **any** corpus makes the *router/ensemble* — rather than the single right sensor — the purchase: specifically, a regime whose correct sensor is **not knowable from the 8 deployable features** (e.g. where two sensors are each right on ~half of one regime's items and the discriminative cue is item-local, not regime-local), so that no single `S_k` cell and no regime-level assignment can capture it. That is the only configuration where FED-HETERO should beat S4-MONO, and it is testable at 0 GPU-Wh on the existing frozen features before any new training. Secondary: the FED-HE-MATCHED **agent-role collapse** (0.5561, below chance 0.5163+0.02, and −0.1175 vs FED-WORD) says the frozen MATCH table's agent→S3 assignment is actively wrong — worth a single read-out of whether it is the S3 featurization or the assignment.
