# SCOUT — SuperInstance fleet push, 2026-10-01 2311Z (day-conductor, read-only)

Sweep: /users/SuperInstance/events (48h) + open PRs (gh search). GPU lane BUSY (live B1b-kink head,
B1b runB, C1b playtest) — scout-only slice, no GPU item fired. No messages to Casey.

## Classified pushes

### 1. CONTRADICT (resolved in our favor, lesson ADOPTED) — fleet-triage 88e30b3 21:17Z
"the projection ladder was a max-selection artifact. Retracting the ordering." Sibling lane computed
Kish n_eff=1.48 over the 4 learners used → "best learner per observation" was a selection over ~1.5
effective votes; L0 spread (0.3209) was 29x the reported +0.0112 gap. Retracted: L0>L1 ordering.
Survives: P2 refuted by more (median 0.8947 vs 0.50 pre-reg); L4 hash64 control at chance cleanly.

- Threat named: **SCOUT-11's QO10** cited their L1>L0-under-shift inversion as the premise to test.
  That premise is RETRACTED. QO10's design already pre-registers BOTH directions, so the item stays
  viable, but its premise line must be amended before firing — do not cite the retracted ordering.
- Direct booked-result threats: NONE. Our nearest analogue (QG7 subpopulation law) is already booked
  as a ≥4-rerun ensemble — their lesson ("no gap smaller than the learner spread is a finding")
  CORROBORATES our QG7 lesson rather than threatening it.
- STEAL the rule verbatim into ST1-AUDIT/QC-JEV3 spec: any per-arm best-selection statistic must be
  accompanied by a Kish n_eff and a spread-vs-gap comparison before it can be called a finding.

### 2. UPDATE/SUPERSEDE — pie-minimax #2 (open, 20:14Z): A1 closure receipt
Nonlinear closes ~1.0, P1 FAIL-HIGH, "thesis weakened, honestly booked." Our queue item **FT-A1**
(P1 top-1 [0.25,0.40], MLP 9-64-9 on 180,361 labels) cites the pre-A1 premise — the A1 receipt
supersedes it. Mark FT-A1 [STALE — re-read fleet-triage + pie-minimax #2 before firing; do not
fire on the old buildspec]. Their nonlinear ~1.0 result also feeds our DECIDE-2 premise-adjacent
intuition (representation may carry more than the readout exposes) — reading item, not GPU.

### 3. TOOL — quilt-research-canons b3e4027 22:27Z scout
"CI green-but-vacuous (quilt-silicon 3/43, quilt-raw 3/18); **reseal-forgery 3rd instance**."
- The vacuous-CI class is our DEGENERATE-gate + RC-1b dead-branch territory (3rd+4th fleet witness).
- **Reseal-forgery 3rd instance is NEW to us**: a receipt whose seal is valid for the content it
  covers but was RE-sealed after a silent edit. Our sealer refuses dirty sealed paths (RC-3, done)
  but does NOT chain seals — nothing prevents a valid-looking re-seal of modified content. Spawned
  **RC-4** below.

### 4. STEAL — pong-quilt #92: scaling-trajectory tool + honesty pins (C1 lane)
Same lane as our live C1-PLAYTEST/C1b run. Their scaling-trajectory tooling is directly reusable
for C1b's 33 remaining games / the ≥90% adjudication. Claim it when booking C1b.

### 5. CORROBORATE — jev-quilt 50th-wipe (0eea3fd 22:05Z)
Hourly wipe probes with mean_p drift flags (q10 +0.26 flagged at 48th, clean at 50th) — the
discipline mirrors our QC-JEV discriminating-control doctrine on a different artifact. No conflict
with our jeff-0.8b finding; their probes watch THEIR net, not jeff-0.8b.

### 6. Misc (no action)
Projectionist: pocket-cinema asset churn (front-end deploy stream). wardroom: self-improvement-loop
thread + "two constants for the drift rules... pass while measuring nothing" — same vacuous-pass
class, cite in RC-4/DEGENERATE when landed. quilt-edge-lab #3/#4: canon-rotation invariance of
receipt chains, control arm honestly sealed FAIL — watch as a candidate receipt-chain property.
cot-quilt-lab engine-core/sheet-pens: unrelated substrate. Dependabot PRs: noise.

## Spawned queue items
- **RC-4 seal-chain / reseal-forgery resistance** (CPU ~45m): make receipt_manifest.py chain each
  seal to the previous manifest hash (append previous seal digest inside the new manifest), so a
  valid-looking re-seal of modified content is detectable; add a tamper test (edit a sealed file,
  re-run sealer, verify the chain breaks). Improves: all booked results (receipt doctrine).
  Gate: tamper test red-then-green; no existing receipt invalidated without an amendment note.
- **QO10 premise amendment** (docs, ~5m, before QO10 fires): strike the retracted L1>L0 premise,
  cite fleet-triage 88e30b3; keep both-direction pre-registration.
- **FT-A1 mark STALE** (docs, ~2m): superseded by pie-minimax #2 A1 receipt.

Rotation next wake: book C1b/B1b verdicts if landed (GPU-free booking), then mandatory (C) repro of
the newest booked script, then (B) top open queue item (RC-4 is cheap and unclaimed).
