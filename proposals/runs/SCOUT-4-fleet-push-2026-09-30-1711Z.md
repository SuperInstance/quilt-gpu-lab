# SCOUT-4 — fleet push sweep, 2026-09-30 ~17:11Z (day-conductor, read-only)

Scope: SuperInstance account (USER account; `/users/SuperInstance/events` works, `/orgs/...` 404s),
20 repos by push recency, canons scout commits, open PRs across 8 repos. Read-only; no comments,
no PRs, no issues filed. Classification against live assets: QO2 routing stack (QO1 oracle +
QG3/QG6 triage + QO6 eproc), DECIDE-1/1b/1c/1d + DECIDE-2, receipt-manifest doctrine,
QG3+QG6 time-law, QG1c swap census, edge-mine seeds W5a/W5b/W5c.

## New since SCOUT-2 (08:0x): 3 repos + 1 version jump

- **`murmuration`** (created 15:26Z today) — swarm consensus by local deference, k-NN cells, no
  central authority, no objective. Ships `jev_probe.py` / `jev_control.py`. **Highest-value find.**
- **`quilt-neighbourhood`** — v0.1.0 → v0.2.0 (numeric merge) → v0.3.0 (DID-signed diffs) all today.
- **`cellgraph`**, **`subleq-fabric`**, **`edge-ledger`** — wave-67 CI seeding (same one-line
  pattern in three repos).
- **`percept-plugs` v0.4** — EKN e-calibrated kNN (P13), supersedes v0.3's witness sheet.

## CONTRADICT (highest value) — the JEV oracle is NULL, and it is our class of failure

`murmuration/experiments/jev_control.json` runs jev-1.13.0 (the same "jeff" family our DECIDE lane
is built on) against two arithmetic controls, and it **does not discriminate**:

| control | claim | argmax | distribution |
|---|---|---|---|
| `control_positive_arithmetic` | "2 + 2 = 4" | **unclear** | unclear 0.74, unsupported 0.20, supported 0.06 |
| `control_negative_arithmetic` | "2 + 2 = 5" | **unclear** | unclear 0.79, supported 0.07, unsupported 0.14 |

A positive control that scores 0.74 "unclear" and a negative control that scores 0.79 "unclear"
are **the same reading**. The oracle cannot separate a trivially true statement from its
negation. `murmuration/README.md` states it plainly: *"TYPESAFEAI_KEY=... python3 jev_control.py
# the JEV probe does not discriminate"*, and the repo description itself advertises **"a null
result for JEV as an oracle."**

**What booked result this threatens:** our DECIDE-1 line treats jeff-0.8b's answer distribution as
a readable *signal* — DECIDE-1b fitted a temperature (1.1289) to its logits, DECIDE-1d named a
"representation-locked argmin" from its 0.844–0.891 consistency, and DECIDE-2 (the day item queued
for Casey) proposes **representation surgery on its hidden states**. If the parent oracle's
calibration is degenerate on trivially-decidable controls, then:
(a) DECIDE-1's below-chance G2 (5/64) may be a property of a *broken calibrator*, not of an
inverted decision mechanism — the "representation-locked argmin" name could be naming an artifact;
(b) the fitted-temperature boundary pin (TEMPERATURE pinned at the 6.0 boundary, logged as an honest
note in the DECIDE-1 booking) is **exactly what a non-discriminating logit distribution produces**;
(c) DECIDE-2's premise ("does the argmax signal exist upstream of the routing?") assumes a signal
exists to find.

This is the **fourth independent instance of the same defect class** in the fleet this week
(qcell_sim's missing `crx` gate; substrate-foundation's eleven undefined opcodes; our own DECIDE-1d
"instruction-blind lock"). Two of them are ours. It is now a fire-time PIN candidate, not a lesson.

**Caveat, stated honestly:** `murmuration`'s control used jev-**1.13.0**, our DECIDE lane used
jeff-**0.8b**. Different checkpoints. The contradiction is a **threat, not a refutation** — the
discriminating-control test may have to be run on *our* checkpoint before DECIDE-2 fires.
Cost of the test: one lane, ~5 min, no GPU (inference only) — see spawned QC-JEV below.

## STEAL — murmuration's `std == 0 ⇒ INCONCLUSIVE, never PASSED` rule

`README.md`: *"A relational claim over a constant measurement is vacuously true. Any claim resting
on a signal with `std == 0` is scored INCONCLUSIVE, never PASSED — and that rule cuts both ways."*
It refused three of the author's own numbers (a no-seed control at exactly 0.000, a broadcast sd of
0.000 across ten seeds, a flat sortedness metric).

**Our mirror instance is already booked:** QO5's g0 finding was `cv std 0, frac_identical 1.0` →
g0 AUC **exactly 0.500**; and F1's G1 passed **degenerately** (df == pfifo to 9 significant
figures, identical `frac_started`). Both are exactly the "vacuous pass over a constant" the rule
forbids. We booked *interpretations* of these (birth lottery; load-saturated regime) rather than
*flagging them as degenerate passes at gate time*. **Steal the gate-time refusal**: any gate whose
statistic has zero variance across arms must return DEGENERATE, not PASS. Directly upgrades the
W5a/F1/W5b verdict-function class — W5a's REFUTED was already declared "forced by saturation"
(det_err false-alarm rate ~1.0 in one direction, 0.0 in the other), which is the same disease.

## STEAL — cellgraph's witness-width defect (our receipt doctrine, sharpened)

`cellgraph` commit f37873c: *"tensor_digest now uses the NATIVE dtype and puts the dtype inside the
digest. Casting to f32 before hashing made the witness blind to everything the cast rounded away
— a 9.8e-10 activation change reported as 'no fault'."*

A witness whose **hash input is narrower than the computation** reports "no fault" while a real
fault passes. Maps directly onto our receipt layer: our `tools/receipt_manifest.py` hashes tool and
weight **files** — but we have now twice recorded that hash identity is *runtime-bound*
(quilt-nn#1: `lossShaOf` not portable cross-runtime; our own QG7 torch-nondeterminism ensemble
lesson). **The receipt's input domain is narrower than the computation it claims to witness.**
Cellgraph's fix is the general one: put the domain (dtype / runtime / device) **inside** the digest
so a witness cannot be blind to it by construction.

## STEAL — canons `pagination_cap_hit: false` (bounds that declare themselves)

Canons' SCOUT-1624Z method note: paging the 4,892-repo census by `sort=pushed` is **not monotonic**
and silently returned 4,119 unique names out of 4,892 rows (**773-repo overlap**). The fix they
enforce: page by `sort=full_name&direction=asc` and **assert `unique == rows_returned`**.
`quilt-atlas` independently carries `pagination_cap: 120` + `pagination_cap_hit: false` — "my own
completeness is bounded, and here is whether the bound bound me."

**Applies to us directly:** QO3's bootstrap IQR, QG7's 4-rerun ensemble, and any sweep we publish.
Adopt a **completeness-bounds field** on receipts: a result that pages, samples, or reruns must
declare its bound and whether the bound was hit. This is the same family as the W5a denominator
discrepancy (pre-reg said 12 primary cells; runner evaluated 24 — declared in-place, verdict safe)
and RC-1's mandate. Spawned as RC-2 below.

## TOOL / CORROBORATE — three wave-67 CI seeds landed in one pattern

`cellgraph` c9d441b, `subleq-fabric` b753171, `edge-ledger` 516533b — identical commit message:
*"wave-67 CI seeding: build-and-test workflow running the repo's real suite (README 'What runs' /
documented pins) on push and PR; suite verified green locally first; **history-independent so
shallow checkouts pass like full clones**."*

The parenthetical is the fix for the exact defect we root-caused in pong-quilt PR #84 (shallow
checkout → `receipt-completeness` CLI REFUSED, exit 2 vs 0). **Three repos independently adopted
history-independence as a CI design constraint within hours of our diagnosis.** CORROBORATE: our
`fetch-depth: 0` recommendation is the weaker fix; **history-independence is the better one** — it
removes the dependency rather than satisfying it. Also note `cellgraph` 3b46dbc: first workflow run
failed on the runner (numpy undeclared) *despite a green local suite* — green-local ≠ green-CI,
exactly our dirty-tree lesson transposed to CI.

## CORROBORATE — canons mutation-tested OUR receipt layer and it passed

Canons SCOUT-1624Z §2 cloned us and **mutation-tested the receipt layer**: appended one HTML
comment to `RESULTS.md` → suite went **RED** with a precise diff (`58f9d1dc…` vs `6829867a…`);
restored → green. Verdict: *"A control that cannot fail is not a control; this one can."*

Two things to bank: (a) our receipt doctrine is now **independently verified by a stranger**, the
same status pong-quilt r37 got from erised-mirror — strengthen the doctrine's standing; (b) their
follow-up candidate is **correct and we should take it**: *"teach the sealer `--require-clean`,
converting pin-caught-after-the-fact into refused-at-seal-time."* That is precisely our dirty-tree
booking class (3 instances today: d23b phantom seal, QG1 census radians, booking-from-uncommitted-
variant). **Spawned RC-3 below.** They also note our structural gap: **no CI** (`workflows: []`) —
a self-verifying suite that only runs when someone remembers.

## Other (notable, lower priority)

- `percept-plugs` **v0.4 EKN** — e-calibrated kNN over shape space (P13, 13/13). *"ML layer answers
  the realm-ml 0.510 lesson: calibrated evidence, not scores."* Three forced findings: RLE regime
  features, disjoint calibration corpus, **Weber-level magnitude-relativity boundary**. Directly
  relevant to QO1 oracle calibration (Brier 0.087) — an e-calibrated readout is the natural next
  oracle layer. **Spawned QO8 below.**
- `quilt-neighbourhood` **v0.3.0 DID-signed diffs** — ed25519 + `did:key:z`; sig is an **overlay
  excluded from id/canonical** so *revisions stay value-pure*; signed sheets reject unsigned diffs
  with `reject-sig`; **NC5 receipts the unsigned-sheet downgrade asymmetry honestly**. Clean example
  of a signature that does not contaminate content-addressing — directly applicable to our
  receipt-manifest (separate the seal from the signed envelope).
- `quilt-neighbourhood` v0.2.0 **trained-replica merge**: 4 MLP replicas' weight cells merge
  byte-identical in all 24 orders; phase 1 **honest semantic FAIL** (independent inits, cross-basin
  averaging void: merged 0.3614 vs per-replica ~0.0068); phase 2 shared-basin positive control HELD
  its pre-registered bound. **This is an independent corroboration of our QG3/QG2 basin structure**:
  averaging across basins is void, within a basin it's fine — same shape as our desert/trapping law.
- `canons` **lucineer-system** — *our own map-room repo*, verified by a stranger: 161 tests pass in
  1.79s (claim exact), 502,015 words (claim "400k+" conservative). README leads with its own
  failure: *"the system has processed four real jobs in its lifetime, and zero have reached a
  player."* Their structural note: 597 MB, **1 commit** → honesty real, **provenance not
  inspectable**. Worth Casey knowing.
- `canons` **superinstance-api** — half-fix confirmed: `.gitignore` now lists `.wrangler/` but
  `git ls-files` still returns `.wrangler/cache/wrangler-account.json` with a **real account email**.
  *"A mitigation that does not change the tracked tree is not a mitigation."* Remedy is
  `git rm --cached` + history scrub. **Not our repo — flag only, no action.**
- `canons` **fleet canary text-form inconsistency** — the integer `0x24a555471370b18d` is correct
  (independently re-derived), but the *string* appears both as 16-digit and 17-digit
  (`0x024a555471370b18d`) across the fleet; the 17-digit form is not representable in 64 bits.
  **Compare the integer, never the text.** Note: of 10 repos cloned, only 1 carries the canary —
  **quilt-gpu-lab is not among them.** Adoption decision for Casey (cheap: docs-only).

## Status changes vs SCOUT-2
- New repos: murmuration, quilt-neighbourhood, cellgraph (+ wave-67 CI seeds ×3).
- percept-plugs v0.2/v0.3 → **v0.4** (EKN).
- Open PRs (unchanged from 08:0x sweep): quilt-gpu-lab#6 (seal guard, ours), delta-shape#1,
  quilt-tools#29/#30, fleet-murmur#8, pong-quilt#84.
- `quilt-research-canons` **is the fleet's scout organ** — 4 scout reports today (07:32Z, 10:30Z,
  13:33Z, 16:24Z). Adopting SC-1 (consume, don't re-sweep) was correct; this sweep confirms it.

## SPAWNED QUEUE ITEMS

- [ ] **QC-JEV discriminating-control pin** (CPU, ~5 min, no GPU): run the murmuration control
  pair (positive "2+2=4" / negative "2+2=5") against **our jeff-0.8b checkpoint** — the exact one
  DECIDE-1 used. **Gate:** if argmax is identical AND both max-probs are within 0.10, the oracle
  is non-discriminating on trivially-decidable controls ⇒ DECIDE-2 premise is void, and DECIDE-1's
  below-chance G2 is re-read as a calibrator defect, not an inverted mechanism. If it DOES
  discriminate, the contradiction is specific to jev-1.13.0 and our lane stands. **must fire
  before DECIDE-2.**
- [ ] **RC-2 completeness-bounds field** (CPU, ~30m): add `bound` + `bound_hit` to result receipts
  (canons `pagination_cap_hit` pattern); require it for any booked result that pages, samples, or
  reruns. Improves: W5a denominator class, QO3 bootstrap IQR, QG7 ensemble claims.
- [ ] **RC-3 sealer `--require-clean`** (CPU, ~30m): `receipt_manifest.py` refuses to seal when the
  working tree is dirty on any sealed path — converting pin-caught-after-the-fact into
  refused-at-seal-time. Spawned independently by canons SCOUT-1624Z §2; two independent asks = do it.
- [ ] **DEGENERATE gate verdict** (CPU, ~30m): verdict functions return DEGENERATE (not PASS) when
  a gate statistic has zero variance across arms (murmuration `std == 0 ⇒ INCONCLUSIVE`). Applies
  to F1's G1 and any future gate of that shape.
- [ ] **QO8 e-calibrated oracle readout** (GPU, read-first): read percept-plugs v0.4 EKN; test
  whether an e-calibrated kNN over (cv, v, gen) improves on the QO1 MLP (AUC 0.951, Brier 0.087)
  or clears 0.80 earlier than QO3's g1. Improves: QO2 routing.
- [ ] **WIT-1 witness-width digest** (CPU, ~30m): extend receipts so the digest's input domain
  (dtype/runtime/device) is INSIDE the hash — cellgraph's fix for a witness blind to what its own
  ingress rounded away.
