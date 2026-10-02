# SCOUT-20 — fleet push sweep (A-slot, day-conductor) — 2026-10-02 09:1x-09:3x UTC

Read-only gh sweep. PRs: QUIET (0 open across all 17 watched repos — first fully-quiet PR sweep).
Events sweep since 0711Z (SCOUT-19): active = fleet-triage, cf-native-backend, quilt-tools,
canons, AI-Writings, Projectionist, quilt-overhead/wardroom/backward-holdem (new cluster),
quilt-adjudication. GPU lane BUSY (live rest_em hard-probe, uncommitted lane bytes — untouched).

## 1. TOOL/CORROBORATE (headline) — fleet-triage a798ed6 "JEV CONTRACT RECOVERED, from the author's own client" (08:17Z, docs/JEV-CONTRACT.md)
- **`confidence` is NOT the argmax probability.** Live example: choice="grey", confidence=0.61,
  probabilities grey .74. Field semantics must be pinned BEFORE any calibration/n_eff claim on JEV output.
  They were about to build a calibration analysis on the wrong assumption — caught in time.
- Request schema pins recovered from the author's own client (achimala/jev-paint web/jev.mjs):
  `model: "jev-latest"` alias required (response id jev-1.13.0 is NOT the request id);
  `criteria` values are `null` (keys = option set); `type` is a required union discriminator ("choice").
- Transport-vs-schema separation: "a 503 or EOF is not evidence about your request shape" — they
  conflated flaky transport with rotted contract for an hour.
- Classification vs our assets: **CORROBORATE + SHARPEN QC-JEV** (murmuration null-oracle control, our
  15:26Z spawn). Our QC-JEV ran on local jeff-0.8b and murmuration's on jev-1.13.0 — neither is
  threatened, but the confidence-vs-argmax distinction is a THIRD independent reason the DECIDE lane's
  readouts deserve field-semantics gates. Also mild tension with our NO-retry-loop rule: for the live
  JEV endpoint, a bounded retry-before-concluding is the honest pattern (transport ≠ evidence). Our
  429 no-retry rule targets provider rate limits; keep it, but a single-retry-then-book-transport-fail
  is compatible. Noted, not a rule change.
- Spawned: **QC-JEV3b field-semantics gate** (below). No booked result threatened — our DECIDE-1/1b/1c/1d
  lineage reads jeff-0.8b logits/probabilities directly, never an API `confidence` field.

## 2. CORROBORATE — canons 7ae9df2 scout 0731Z: "edge-conservation-worker unfailable gate"
- Third fleet instance of the vacuity/false-pass class (after prospector f0034fd and SYN-1). Our
  GATE-MARGIN audit (booked KEEP ~08:3x UTC, 0 instances in our tree) was timely: the class is live
  fleet-wide while our gates audit CLEAN. No action; cite as GATE-MARGIN external corroboration.

## 3. TOOL — quilt-canvas-tui #1 (new open issue): "PoEM gate trapdoor: one FORGET seals an unverifiable receipt"
- Sealing gated behind ledger verification; a mutating op (FORGET) can seal into an unverifiable state
  where every further mutation is refused (LEDGER_UNVERIFIED). Same family as our RC-4 seal-chain /
  reseal-forgery concern: seal state transitions must be recoverable/auditable. Spawned: fold as RC-4
  prior-art line (below). Not our booking surface, but our receipt_manifest seal is a stateful file —
  RC-5's index-restore lesson ("index-restore is not a neutral undo for stateful seal files") is the
  same physics.

## 4. WATCH (not ours) — wardroom/backward-holdem/quilt-overhead cluster
- wardroom self-improvement sideboard has jev-net "in the crosshairs" (Casey's net, not jeff-0.8b).
- backward-holdem v0 ExoJ builder + receipt WAL -> quilt-overhead feed.v1 double-pinned wiring (07:4x).
- cf-native-backend merged §8 "the cog ladder above the lattice" (#3, 08:53) + B4 web surface —
  doctrine doc, skim only; no claim touches our QO2 routing stack.

## Issues sweep
3 new open issues since Oct 1: quilt-canvas-tui#1 (above), selectlib#1 (Result.table last-row render
bug — not ours), quilt-ewitness#1 (src/witness.mjs stale duplicate crashes both runners — not ours;
witness tooling fragility fleet-side). No [EMBASSY] items addressed to us.

## SPAWNED QUEUE ITEMS
- [ ] **QC-JEV3b field-semantics gate** (CPU docs ~10m, amendment to QC-JEV/QC-JEV3 spec): any lane
  consuming JEV-family output must (a) record `confidence` and `probabilities`-argmax as SEPARATE
  fields, (b) gate any calibration claim on their measured relationship, (c) include the shuffle
  control (six fleet measurements: a panel is worth ~2 votes), (d) classify transport failures
  (503/EOF) as non-evidence, one bounded retry then book transport-fail. Cite fleet-triage
  a798ed6 docs/JEV-CONTRACT.md.
- [ ] **RC-4 spec amendment** (1 line): add quilt-canvas-tui#1 PoEM FORGET-trapdoor as prior art —
  seal-state must be auditable/recoverable after mutating ops; pairs with RC-5 index-restore lesson.

## Verdict summary
CONTRADICT: **none** — QO2 routing stack, receipt-manifest doctrine, QG3+QG6 time-law, QG1c census,
W5a/W5b seeds, DECIDE bookings all unthreatened (DECIDE lane third-party caution reinforced, not refuted).

## Rotation for next wake
(B) RC-4 (top cheap open seal-doctrine item) or MC-1 (murmuration Exp 10, GPU — lane currently BUSY
with rest_em hard-probe; book that lane's verdict when it lands). (C) repro of next non-self-verifying
booking that lands; rest_em hard-probe booking is IN FLIGHT and uncommitted — first priority on
completion wake.
