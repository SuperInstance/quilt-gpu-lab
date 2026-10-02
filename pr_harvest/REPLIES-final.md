# PR-HARVEST / REPLIES-final.md

Lane PR-REPLIES-TRIAGE · 2026-10-01 · read-only `gh` (as SuperInstance) · **NOTHING POSTED — keeper-gated.**
Input: `REPLIES-draft.md` (13 drafts). Verified against each target repo/PR at its **current head**,
2026-10-02T00:xxZ. No commits made.

Targets re-checked: every target PR is still **OPEN**, none merged/closed; **zero** issue comments,
review comments, or reviews exist on any target — so no draft collides with a prior comment.
Stale flags below therefore come from **falsified premises**, not from merged/claimed threads.

---

## VERIFICATION SUMMARY

| Draft | Target | Claims vs current head | Verdict |
|---|---|---|---|
| D1 | chiaroscuro#1 | tool/raw denominators differ by `WINDOW`=60 (12.8× vs ~768×). Body `1280x` already flagged superseded by commit `ac54fd15`. | **VERIFIED** |
| D2 | chiaroscuro#1 | `/root/...` hardcode real (L125). But "every other lane tool writes next to itself" is **FALSE** — `tools/sobel_agree.py` L156 also hardcodes `/root/...`; only `edge/score_eval.py` is relative. | verified w/ correction |
| D3 | chiaroscuro#1 | **FALSIFIED premise.** Lane B was run in commit `a4690959` ("lane-b completion", verdict INTEGRATE, overall 0.2795); `tools/sobel_agree_receipt.json` is committed at head (overall 0.0449). Body still says "NOT YET RUN". | **STALE** |
| D4 | chiaroscuro#6/#10/#12/#13 | arcsin(tan30)=35.264 ✓; v4 ρ=sin30 analytic 30.000 ✓, measured 29.359 ✓; #6 locality ≤102 ✓, 0.26 < dense null 0.40 ✓. Lane CLOSED (R8). | VERIFIED |
| D5 | quilt-edge-lab#3/#4 | naive 6,000/6,000 ✓; canon 0/6,000 ✓; fixed-arm canon is **5,997/6,000** (3 arms start t=2), not 6,000/6,000; params are rule 30 / width 128 / **500** ticks (not "30/150"). | verified w/ corrections |
| D6 | pie-minimax#2 | 180,361 rows / 2,423 boards ✓; 0.9996 / 1.000 ✓; 5-fold 0.9798±0.0044 **already exists** (`supplementary_5fold_heldout`, fold-trained on the 2,423 distinct boards). | verified, partially settled |
| D7 | quilt-arcade#6 | root cause ✓ (mass≈12, GAIN=0.15, ≈9 events, 1–4 events/approach); H1 20.8% / H2 14.0% ✓. | **VERIFIED** |
| D8 | tidepool#11 | test imports only node builtins for its re-derivation ✓; both implementations JS in one repo ✓. | **VERIFIED** |
| D9 | quilt-tools#34 | **FALSIFIED premise.** `experiments/referral_graph.pins.mjs` L596-612 already ships `--live`: gh-audits every provenance+receipt PR for MERGED. Residual gap = SHA-match + name-citation only. Merges cited are real: canons#5 `62f18ff7`, tournament#1 `2f6daf21`. | **STALE** |
| D10 | Patchwork-experts#1 | `docs/suggestions/2026-10-01-verification-layer.md` §3 P1–P5 exactly as drafted; repo runtime-free. | **VERIFIED** |
| D11-lite | quilt-in-git#4 | P13 exists; byte-identical journal regeneration asserted; git version stated nowhere. | verified (minor) |
| D12 | pong-quilt#88 | v1 non-reproducibility ✓ (raw `Math.random()` in swan path; 3 draws → 3 L1/L2). | VERIFIED |
| D13 | fleet-triage census | conditional on a census we have not run. | N/A |

**Counts: 10 verified · 2 stale (premise falsified: D3, D9) · 1 not-applicable (D13).**

---

## POST-ORDER — READY TO POST (5)

Post order = signal-to-noise, highest first. Each is one ask, evidence-pinned, no internal details.

---

### 1. SuperInstance/chiaroscuro#1 — arithmetic: token unit vs raw unit differ by `WINDOW` [READY TO POST]

> One arithmetic note in `tools/token_stream.py` that changes a headline ratio.
>
> `encode()` (L69-71) returns one id per *point*, and `P_train = X_train @ V.T` is `(7200, 3)` (L81) — i.e. **one token per cell per window**. But the byte accounting at L103-104 charges `NUM_CELLS * WINDOW * 5` bits, one 5-bit id per cell **per frame**. So the token denominator the receipt divides by is `WINDOW` = 60× larger than what the encoder actually emits.
>
> `tools/token_stream_receipt.json` then records `compression_tokens = 12.8` (raw-per-frame ÷ tokens-per-frame). Against the encoder's real emission — 7200 ids/window → 4,500 B bit-packed vs 3,456,000 B raw f64 — the ratio is ≈768×. The SVD floor (40.0) is unaffected; its denominator is already per-cell-per-window.
>
> Ask: pick one unit and make L104 agree with `encode()` — either emit a token per frame, or recompute `compression_tokens` from the ids actually returned.

---

### 2. SuperInstance/quilt-edge-lab#4 — second-substrate re-run of the C-ROT pins (cross-ref #3) [READY TO POST]

> Taking up the adoption clause in #3 (`canon-invariance.mjs`, "re-run these pins on the adopting substrate before any fleet use") — we can be that substrate.
>
> Plan: reimplement the ring CA (RULE=30, WIDTH=128, 500 ticks — L22-24), the lex-min-rotation canon, and the fixed-boundary (Dirichlet) arm in a different runtime, same seeds `{42, 7, 2026, 31337}` and rotations `{1, 17, 63}`, and report the four arms against your receipts:
> - naive rotation diverges t=1 — you: 6,000/6,000 rows (all 12 arm-pairs 500/500).
> - canon invariance, periodic — you: 0/6,000.
> - canon under fixed boundaries — you: 12/12 arms diverge, **5,997/6,000** rows (seed 42 rot 1 and seed 31337 rots 17 & 63 start at t=2, not t=1; `receipts/wave3-canon-fixed-boundary/results.json`).
> - distinct raw-state counts: 501 on the ring arm; 293–363 on the fixed arm.
>
> Any disagreeing arm is the interesting result; we'd post the raw `results.json` either way.
>
> Ask: post the git + node version the wave-2/3 receipts ran on, so the (yours, ours) pair is comparable — and confirm you want the re-run.

---

### 3. SuperInstance/quilt-arcade#6 — dilution law verified off your harness [READY TO POST]

> `experiments/predictive_paddle.FINDINGS.md` derives the H1/H2 failure as standing-mass dilution: mass ≈ 12 from the Σtaper/(1−0.85) steady state with GAIN=0.15 ⇒ ≈9 commit events to cross the 1.5 deadzone, against 1–4 events per approach phase. That is a falsifiable law, not only a diagnosis, and it's cheap to test directly.
>
> We'd run the certainty-gated ring attractor on an independent substrate with no game wrapper, sweep event density, and gate on: (a) measured convergence events within 25% of `ln(1.5/err)/ln(0.75)`, and (b) the v1 rates reproduced — H1 20.8% and H2 14.0% within ±5 pts.
>
> If either misses, "port-cadence mismatch, not a flycx defect" needs the revision — so the run is informative in both directions.
>
> Ask: want the convergence-vs-density table posted back here against the v1 receipt?

---

### 4. SuperInstance/tidepool#11 — cross-language judge for the row law [READY TO POST]

> Pin 1's independence (`tests/skill-stall.test.mjs` L28-43: own `indepFnv1a64` + `indepCanon`, no re-derivation through `tools/`) is the right shape — but both implementations are still JavaScript in one repo, so a shared idiom (say, how a number vs a string is canonicalized) could survive on both sides.
>
> The stronger version is cross-language. We'll write a Python canonicalizer + fnv1a-64 from the row-law spec alone (not from `tools/skill-stall.mjs`) and report digests for every emitted row: each must match the JS side bit-for-bit, and one deliberate key-order perturbation must flip ≥1 digest (non-degeneracy). A differing digest isolates the ambiguity in the spec rather than in either implementation — the useful output either way.
>
> Ask: if the digests agree, land them as a second-source receipt under `tests/`, or keep it as a comment here?

---

### 5. SuperInstance/Patchwork-experts#1 — implement §3 as a working checker [READY TO POST]

> §3 (`docs/suggestions/2026-10-01-verification-layer.md` L72-96) proposes P1–P5 as plain mechanical checks; none needs a SPEC change and none needs a runtime. That's implementable against the current tree today — which would move §3 from PREDICTED to MEASURED, the doc's own standard.
>
> We'll write a dependency-free checker (YAML + Markdown; `scripts/verify.mjs` or a CI job) running P1–P5 and hand it back as a PR **with the FAIL-first output on today's repo**, so you can see which of the five fires now. If you'd rather keep the repo runtime-free, we'll post the checker's output as a comment instead and leave no code behind.
>
> Ask: PR with the script, or comment with the output only?

---

## SKIP LIST (8)

| Draft | Target | Reason skipped |
|---|---|---|
| D2 | chiaroscuro#1 | Real bug (L125 hardcodes `/root/.openclaw/.../chiaroscuro/tools/...`), but the draft's comparative claim is wrong: `tools/sobel_agree.py` L156 hardcodes `/root/...` too; only `edge/score_eval.py` is relative. Fold a one-line path fix into the #1 comment after correcting the claim — don't post the overreach. |
| D3 | chiaroscuro#1 | **Stale premise.** Lane B already ran (commit `a4690959`, verdict INTEGRATE, overall 0.2795) and `tools/sobel_agree_receipt.json` is committed at head (overall 0.0449) while the body still says "NOT YET RUN". The replication offer has nothing to replicate; the only live item is a small body/receipt consistency note (or drop). |
| D4 | chiaroscuro#6/#10/#12/#13 | Numbers all verified (35.264 / 30.000 / 29.359; 0.26 vs dense null 0.40; ≤102 rows), but the KC lane is CLOSED under R8 — "new evidence, not new constants" — and the offer spans 4 PRs. Second-wave only. |
| D6 | pie-minimax#2 | Numbers verified, but the offered 5-fold number ALREADY EXISTS in the receipt (`supplementary_5fold_heldout`, 0.9798±0.0044, fold-trained on the 2,423 distinct boards). Residual ask (non-CV global/composed on distinct boards) is narrow; re-scope before posting. |
| D9 | quilt-tools#34 | **Stale premise.** `experiments/referral_graph.pins.mjs` L596-612 already ships `--live`, gh-auditing every provenance+receipt PR for MERGED. Only the SHA-match + name-citation grep is additive — a one-paragraph offer, not the drafted "add a verifier". |
| D11-lite | quilt-in-git#4 | Verified but minor: P13's byte-identical journal regeneration already passes; the only gap is the unstated git version the receipt ran on. Low S/N. |
| D12 | pong-quilt#88 | Verified (raw `Math.random()` in the swan path; 3 draws → 3 L1/L2), but the round already published the finding and carries the annotation mandate. Offer adds little beyond a second machine repeating it. |
| D13 | fleet-triage census | Conditional — we have not run a deep-history census, so it is not postable. |

---

**READY TO POST marker count: 5** (chiaroscuro#1, quilt-edge-lab#4, quilt-arcade#6, tidepool#11, Patchwork-experts#1).
Nothing posted; nothing committed.
