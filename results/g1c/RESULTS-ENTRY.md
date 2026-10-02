# G1c — seat-vs-instrument verdict routing

**Lane:** G1c (QUEUE.md line 56) · **Date:** 2026-10-01 · **Seed:** 2718
**Question:** the local seat (qwen2.5:7b Q4_K_M, G1) scores 0.5208 = chance on the
96-claim battery. Does an *instrument* clear the bar the seat fails?

**Verdict: KEEP (provisional) — with a booked key defect.** Instrument arms clear
0.75; the seat does not. But 19/96 labels in the certified key are inconsistent
with the prompt text, so the headline "0.5208 = chance" is partly a key artifact.

---

## 1. Arms (blind; key read only after both arms answered)

| arm | what | call | answered |
|-----|------|------|----------|
| LOCAL | qwen2.5:7b Q4_K_M via ollama | (G1 run1, reused) | 96/96 |
| JEV | typesafe `jev-preview` System One, one `noul` call per claim, thr=0.5 (fleet PINCH default) | `api.typesafe.ai/v1/systemone` | 96/96, 0 errors |
| GLM | z.ai `glm-5.3-flash`, **exact** battery text, temp 0, seed 2718 | coding endpoint (see §6) | 96/96, 0 errors, no 429 |

Arm I presented the claim body (reply-format boilerplate stripped) as `state`, one
graded question (`noul`, threshold 0.5 → SUPPORTED/REFUTED). Arm II got the byte-
identical prompt the local seat saw, so the three arms are comparable.

## 2. Gate results

Frozen gate: **JEV arm is KEEP-material iff overall accuracy ≥ 0.75.**

| | vs shipped key | vs recomputed truth (§4) |
|---|---|---|
| LOCAL | 0.5208 | 0.6979 |
| **JEV** | **0.7708 — PASS** | **0.9688** |
| GLM | 0.8021 | 1.0000 |

`noul` threshold is not the lever: sweep vs recomputed truth peaks 0.9688 over
thr ∈ [0.4, 0.8]; the shipped-key sweep peaks 0.7812 at thr 0.6–0.7. The doc's
default 0.5 is kept.

## 3. Routing table (cheapest arm ≥ 0.75 per class; cost LOCAL < JEV < GLM)

Against the shipped key:

| class | LOCAL | JEV | GLM | winner |
|---|---|---|---|---|
| arith | 0.5625 | 0.9375 | 1.0000 | **JEV** |
| date | 0.3125 | 0.8750 | 1.0000 | **JEV** |
| seq | 0.5625 | 1.0000 | 1.0000 | **JEV** |
| xref | 0.9375 | 1.0000 | 1.0000 | **LOCAL** (seat already clears) |
| contra | 0.3125 | 0.3125 | 0.3125 | — none (defective labels) |
| count | 0.4375 | 0.5000 | 0.5000 | — none (defective labels) |

Against recomputed truth (§4), which is the one to route on:

| class | LOCAL | JEV | GLM | winner |
|---|---|---|---|---|
| arith | 0.5625 | 0.9375 | 1.0000 | **JEV** |
| date | 0.3125 | 0.8750 | 1.0000 | **JEV** |
| seq | 0.5625 | 1.0000 | 1.0000 | **JEV** |
| xref | 0.9375 | 1.0000 | 1.0000 | **LOCAL** |
| contra | 1.0000 | 1.0000 | 1.0000 | **LOCAL** |
| count | 0.8125 | 1.0000 | 1.0000 | **LOCAL** |

**Routing recommendation:** route verdicts by claim class — **LOCAL for
xref / contra / count**, **JEV for arith / date / seq**. GLM is ≥ JEV on every
class but never the cheapest passing arm; keep it as the escalation tier for
classes or items where both LOCAL and JEV fall below 0.75.

## 4. Booked defect — the key, not the arms

Recomputing every claim's truth from its prompt text (pure arithmetic / sequence /
date math / roster lookup / enumeration):

| class | n | shipped-key labels inconsistent with text |
|---|---|---|
| arith | 16 | 0 |
| seq | 16 | 0 |
| date | 16 | 0 |
| xref | 16 | 0 |
| **contra** | 16 | **11** |
| **count** | 16 | **8** |
| total | 96 | **19** |

- **contra:** Statement B reads "The {item} is NOT on the locker list" while
  {item} *is* enumerated in A (15/16 rows) — as rendered these are lexically
  REFUTED, yet 10 are labelled SUPPORTED.
- **count:** recomputed from the rendered manifest, **all 16 claims are REFUTED**
  (claimed count ≠ actual count every time), yet 8 are labelled SUPPORTED.
- Every arm answers REFUTED to nearly all contra/count claims — including GLM,
  which is 100% correct on all four sound classes. The unanimous collapse is the
  tell that the labels, not the judges, are broken (a perfect judge caps at
  77/96 = 0.802 against the shipped key).

Consequence for G1: the local seat's 0.5208 is contaminated. Against recomputed
truth it is 0.6979 overall and 0.5938 on the four sound classes — still well
below the 0.75 bar, so the G1 conclusion (completer, not verifier) stands on the
sound classes alone; the contra/count columns of the G1 score should be struck.

## 5. Per-claim agreement (shipped key, 96 rows)

`truth` marginal: 50 REFUTED / 46 SUPPORTED.

- local_vs_truth: 50/96 (28 R-R, 22 S-S, 24 R→S, 22 S→R)
- jev_vs_truth: 74/96 (46 R-R, 28 S-S)
- glm_vs_truth: 77/96 (49 R-R, 28 S-S)
- jev_vs_glm: 93/96 agree (both REFUTED 64, both SUPPORTED 29; 3 S↔R)

JEV's confident errors on sound classes: `g1b-arith-0000` (noul 0.95 SUPPORTED;
truth REFUTED), `g1b-date-0508` (0.51), `g1b-date-0509` (0.80). JEV is
over-confident when it errs; no abstain channel was available.

## 6. Honesty notes

- **GLM endpoint:** the z.ai pay-as-you-go endpoint returns 429 code 1113
  ("Insufficient balance") on this key; the account's live plan is the **coding
  plan**, and `https://api.z.ai/api/coding/paas/v4/chat/completions` answers 200
  with `glm-5.3-flash`. Not an improvisation — same provider, same key, the
  base URL the plan is registered on. Booked here so future lanes don't burn
  10 minutes on 1113.
- Arm II was NOT booked NOT-RUN: no rate-limit wall was hit (0 × 429).
- Recomputing truth reimplements the battery builder's logic from the prompt
  text; where a prompt form was unrecognised the row is left `null` (none in
  contra/count).
- Not committed, not appended to RESULTS.md — the keeper folds.

## 7. Artifacts

- `experiments/g1c_verdict_routing.py` — harness (`collect` blind → `score`).
- `experiments/g1c_key_audit.py` — key-consistency recompute + rescore.
- `results/g1c/arm_jev_raw.json`, `arm_glm_raw.json` — raw arm outputs.
- `results/g1c/score_g1c.json` — blind scoring, agreement matrices, noul sweep.
- `results/g1c/key_audit.json` — recomputed truth vs shipped key, rescored arms.
- `results/g1c/routing_table.json` — the frozen routing table (both key variants).
