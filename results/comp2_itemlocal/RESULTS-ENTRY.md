# COMPOSITE-2 phase 3 — C2-IL: the ITEM-LOCAL sensor corpus (lane C2-LOCALSENSOR)

**Ran:** 2026-10-01 18:3x–18:4x AKDT · `experiments/comp2_itemlocal.py` (CPU-only)
**Prereg:** `proposals/runs/C2-item-local.md` (frozen 18:3x **+ AMENDMENT 1**, pre-run, disclosed)
**Cost:** **CPU-only, 0 GPU-Wh**, no guard window, **no new banks trained** (prereg §3 no-train path held). Wall **10.9 s**. `wh_receipt.json`. **NOT COMMITTED.**

## VERDICT — **FAIL** (no federation premium even item-local)

| gate | reading | bar | verdict |
|---|---|---|---|
| **G-IL1** (signal exists) | 8/8 single-view arms above chance+0.02 (best **0.7783**) | ≥ chance+0.02 | **PASS** |
| **G-IL2 (THE QUESTION)** `FED-CHEAP-GATE` − `BEST-SINGLE` | **+0.0022** CI[+0.0004, +0.0040] | > +0.05 ∧ CI_low>0 | **FAIL** |
| **G-IL2b** `FED-CHEAP-GATE` − `S4-MONO` | +0.1045 CI[+0.0894, +0.1190] | > +0.05 ∧ CI_low>0 | PASS (calibration effect — see §4) |

No degeneracy (every deciding std > 0: 0.0016–0.0091). No truncation (3/3 seeds).

### The sentence this run books

> **"No federation premium even item-local — the thesis narrows to sensor selection, full stop."**

This is the mission's pre-booked FAIL clause, and it **closes COMPOSITE**: sensor *choice* is the
purchase; federation *over* sensors is not, even on the one corpus built to favour it. It is a
**clean negative**, not a strike — the strike ledger (COMP0, COMP1) is untouched (prereg §1).

## 1. What a dual-view item IS (construction headline)

Same grammar law as COMP2 phase 1 (COMP1-A1 pools / renderer family / LCG / sha256 content
addressing / dedup / hash-split ≥0xC → held-out), regime tag = the evidence surface style.
**The target is a conjunction of two sensor views inside the item: canon iff the polarity channel
agrees AND the second channel agrees; every distortion violates EXACTLY ONE channel, and the
violated channel is drawn i.i.d. PER ITEM, independent of the regime tag** — so no regime-level
sensor table (`MATCH`) can carry the answer. Verbatim held-out examples:

```
[semantic | canon      | channel=None]      ← both views agree
  claim   : the launch delivered the herring crates at dock-5.
  evidence: the launch brought a herring shipment of five crates to dock-5.

[semantic | distortion | channel=polarity]  ← ONLY the negation view is violated (cargo/dock agree)
  claim   : the trawler did not secured the kelp crates at berth-9.
  evidence: the trawler brought a kelp shipment of three crates to berth-9.

[semantic | distortion | channel=dock]      ← ONLY the semantic view is violated (polarity agrees)
  claim   : the launch did not stowed the halibut crates at berth-9.
  evidence: the launch did not stowed the eight crates of halibut at dock-5.
```

An item is **answerable by the negation view alone** (polarity case) or **by the word view alone**
(dock/cargo case) — the correct sensor is **item-local**, mixed within every regime. That is exactly
COMP2 §10's demanded configuration.

## 2. Corpus (frozen, deterministic; N=12,000, seed 2718)

- 12,000 items, **3,000/regime**, **12,000 exact-unique** after dedup (82 LCG regen collisions);
  split **8,918 train / 3,082 held-out** (semantic 763 · counting-address 762 · negation-scope 786 ·
  agent-role 771).
- canon frac **0.5026** (per-regime 0.4928–0.5158; |Δ−0.5| ≤ 0.02 ✓); **polarity share of each
  regime's distortions 0.4677–0.5230** ⇒ the item-local channel draw is regime-independent ✓.
- **W1 determinism identical**; sha256-sequence `b1886f9de868e11a08c6ed74dd5c1e091da8572ff45a42b43f43486fedb06b93`.
- Majority chance (computed): full **0.5026**.

## 3. Boards (seed-mean over 3 seeds; full board)

| arm (params) | full | semantic | counting-address | negation-scope | agent-role |
|---|---|---|---|---|---|
| `S1` (frozen MLP, S1 view) | 0.5831 | 0.6330 | 0.5735 | 0.5390 | 0.5880 |
| `S2` (frozen MLP, S2 view) | 0.5676 | 0.5374 | 0.5621 | 0.5649 | 0.6057 |
| `S3` (frozen MLP, S3 view) | 0.5459 | 0.5902 | 0.5262 | 0.5174 | 0.5504 |
| `S4` = `S4-MONO` (frozen MLP, S4 view) | 0.6760 | 0.6645 | 0.6929 | 0.7010 | 0.6450 |
| `JOINT` (4225p, S1) | 0.5860 | 0.6378 | 0.5787 | 0.5365 | 0.5923 |
| `PV-cheap-S4` = **`BEST-SINGLE`** (65p logistic, S4 view) | **0.7783** | 0.7549 | 0.7997 | 0.7740 | 0.7847 |
| `FED-IL` (min-p join, 4 frozen cells) | 0.5837 | 0.6064 | 0.5949 | 0.5148 | 0.6204 |
| `FED-IL-2S` (min-p over S1,S4) | 0.6767 | 0.7309 | 0.7244 | 0.5556 | 0.6995 |
| `FED-IL-MAJ` | 0.6393 | 0.6837 | 0.6553 | 0.5517 | 0.6688 |
| `FED-IL-MARGIN` (0-param argmax-margin) | 0.6966 | 0.7165 | 0.7060 | 0.6874 | 0.6770 |
| `FED-IL-GATE` (20p learned router, 4 frozen cells) | 0.6735 | 0.6697 | 0.6916 | 0.6870 | 0.6455 |
| `FED-GATE-8` (72p router, 4 MLP + 4 cheap cells) | 0.7525 | 0.7436 | 0.7944 | 0.7125 | 0.7609 |
| **`FED-CHEAP-GATE` (20p; PRIMARY)** | 0.7804 | 0.7588 | 0.8014 | 0.7761 | 0.7856 |
| `FED-CHEAP-STACK` (5p logistic combiner, secondary) | 0.8022 | 0.8143 | 0.8163 | 0.7922 | 0.7864 |
| *chance* | *0.5026* | *0.5072* | *0.5157* | *0.5038* | *0.5058* |

**Every routing operator is ≤ +0.024 over the best single view.** Diffs vs `BEST-SINGLE`:
`FED-CHEAP-STACK` **+0.0239** CI[+0.0127,+0.0356] (best federation arm — a *combiner*, not a router);
`FED-GATE-8` −0.0257; `FED-IL-MARGIN` −0.0817; `FED-IL-2S` −0.1016; `FED-IL-GATE` −0.1048;
`FED-IL-MAJ` −0.1390; `JOINT` −0.1923; `FED-IL` −0.1946. The primary bar (+0.05) is missed by
**2× on the best arm and by 20× on the primary arm.**

## 4. Why G-IL2b PASSes but G-IL2 FAILs — the calibration, not the routing

`FED-CHEAP-GATE` beats `S4-MONO` by **+0.1045** — but **`FED-CHEAP-GATE` (0.7804) is statistically
the same as the single best cheap cell `PV-cheap-S4` (0.7783): +0.0022 CI[+0.0004,+0.0040]**.
So the whole +0.1045 over `S4-MONO` is the gap between a **refit** logistic on the S4 view
(calibrated to this corpus) and the **frozen** COMP2 MLP cell (0.6760, miscalibrated for the
conjunction label). **Buying the right sensor once — and recalibrating it — is the entire purchase.**

## 5. The decisive diagnostic: the premium exists but is not resolvable

| quantity | value |
|---|---|
| best **fixed** single-view arm | 0.7783 |
| **oracle** per-item best single-view cell (8 arms) | **0.9974** |
| **perfect-router headroom** | **+0.2191** |
| 0-param argmax-margin router's pick-agreement with the oracle pick (4 MLP cells) | **0.7070** |
| items where the fixed best view is wrong but *some* view is right | **0.2771** |

**The item-local structure is fully present** — a per-item oracle over the same eight cells reaches
0.9974, and on 27.7 % of items the fixed best view is wrong while another view is right. **What is
absent is any deployable per-item signal that resolves *which* view is decisive**: the margin router
agrees with the oracle only 70.7 % of the time, and every learned router over the frozen deployable
features (per-cell p / margins) lands within ±0.03 of the best fixed view. The premium is real;
the **routing is not readable from the sensors' own outputs.**

## 6. Per-channel boards (why the join fails and the single cell wins)

| arm | canon | dist_cargo | dist_dock | dist_polarity |
|---|---|---|---|---|
| `BEST-SINGLE` (`PV-cheap-S4`) | **0.9664** | 0.1087 | 0.2547 | **1.0000** |
| `S4-MONO` (frozen MLP S4) | 0.8801 | 0.1875 | 0.2727 | 0.7124 |
| `S1` (frozen MLP word view) | 0.7420 | 0.3904 | **0.6036** | 0.3408 |
| `FED-IL` (min-p join) | **0.2359** | **0.8759** | **0.9509** | **0.9556** |
| `FED-IL-GATE` | 0.8563 | 0.2101 | 0.3071 | 0.7216 |
| `FED-CHEAP-GATE` | 0.9636 | 0.1268 | 0.2654 | 1.0000 |

The complementarity the corpus was built for **is there**: the S4 view is a near-perfect
polarity+canon detector and near-blind to cargo (0.109) and dock (0.255); the S1 view is the best
semantic detector (0.390/0.604) and *anti*-polarity (0.341). But the join that captures the
distortions (0.876/0.951/0.956) does so by firing on 76 % of canon items — **the sensors' false-positive
rates are the binding constraint, and no router recovers the canon cost.**

## 7. Harness revisions (disclosed, pre-run or post-hoc)

1. **AMENDMENT 1 (pre-run, disclosed in the prereg).** §2's second channel was frozen as **count**;
   the main run uses **polarity + semantic**. Pilot evidence (`pilots/variantA_polarity_count.json`):
   under the count channel **every** view is at chance on count-violations (frozen cells
   0.502/0.422/0.563/0.146; cheap cells 0.460/0.424/0.452/0.086) — the item is then only *nominally*
   dual-view, which G-IL1 exists to catch. Variants A/B/C (count / semantic / agent) were all piloted
   (headline premiums over the best single view ≈ +0.00 / +0.02–0.03 / +0.02) — the same qualitative
   answer, so the choice is not verdict-turning. **The amendment raises the best-single baseline,
   i.e. biases toward the negative**, not toward PASS.
2. **Router param count (post-hoc).** The prereg's amendment guessed "8 features → 36 p"; the shipped
   `FED-CHEAP-GATE`/`FED-IL-GATE` use the **4 per-cell p values** as features → **20 p** (4 classes ×
   4 features + 4 intercepts). `FED-GATE-8` uses 8 p values → 8 classes → **72 p**. Params are the
   *smaller* side of the guess; the bar is unchanged.
3. **No new banks were trained** — the no-train path held, so the ≤2 Wh fallback (prereg §3) did not fire.

## 8. Artifacts

`results/comp2_itemlocal/` → `il_results.json` (boards per-seed + seed-mean, all CIs, G-IL1/2/2b,
secondary + within-family, routing diagnostics, per-channel, validity, W1) · `corpus.jsonl` (12,000) ·
`per_item_stub.jsonl` (12,000, uniform keys, prediction fields null) · `predictions/*.jsonl.gz`
(**20 arms × 3 seeds × 3,082 held items = 184,920 rows**; `{sha256,key,regime,label,channel,split,seed,arm,p,correct,margin,routed_sensor,cell}`;
boards recompute from the dump, max|Δ| < 5e-5) · `wh_receipt.json` (0 GPU-Wh) ·
`pilots/` (disclosed direction-finding, **not** a booking). Code: `experiments/comp2_itemlocal.py`.
**NOT COMMITTED.**

## 9. What this establishes, and what it does not

**Establishes:** on a corpus whose target genuinely requires two sensor views inside the item, with
the violated channel drawn item-locally and independently of the regime tag, **a per-item federation
of the available per-sensor cells does NOT beat the best single view** — best routing arm +0.002
(primary) / best combiner +0.024, against a +0.05 bar. The item-local premium **exists** (oracle
headroom +0.219) but is **not resolvable from the deployable sensor outputs** (margin router agrees
with the oracle only 70.7 % of the time; 27.7 % of items need a view other than the fixed best).
COMP2's narrowing ("buy the right sensor once") survives its strongest challenge.

**Does not establish** that no corpus could ever reward routing — only that in the COMP2 sensor
space, routed over the frozen banks and the cheap per-view logistics, item-local sensor choice buys
nothing once the right sensor is bought (and recalibrated). The count and agent channels were
independently piloted with the same qualitative answer (variants A/C), so the negative is not an
artefact of the semantic channel choice.

## 10. Next question

The routing signal, not the corpus, is the wall: the oracle says +0.219 is available and the margins
recover none of it. Two live follow-ups, both cheap: **(a)** give the router a *non-deployable-wrong*
feature — the frozen per-sensor **cheap-logistic margins on the raw view** are already 70.7 %
oracle-agreeing, so ask whether a 2-way *calibration* of those margins per channel (a 2-parameter
isotonic/Platt rescale) closes the gap, which would recast the failure as a *calibration* failure
rather than a routing failure; **(b)** re-ask the question in a view space that is **structurally
complementary by construction** (an order-only view vs a bag-only view, where one view is at chance
on the other's channel by geometry, not by luck) — that is the only setting in which "the sensor that
carries the answer" is *identifiable*, and it is a corpus-design question, not a federation one.
