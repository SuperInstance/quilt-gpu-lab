# SCOUT-21 — fleet push sweep (A-slot, day-conductor 2026-10-02 ~1011Z AKDT)

Read-only gh sweep, 20 repos by pushed_at (last 48h commits) + open PRs (all target repos: ZERO open
PRs anywhere). GPU lane BUSY (live rest_em_loop.py treatment/hard lane, fired 02:05, not ours —
untouched); tree carries that lane's in-flight bytes — seal deferred on in-flight bytes per 359a32a
precedent. No GPU item fired. Events feed capped at Sep 30 (stale) — pushed_at census used instead.

## HEADLINE — CORROBORATE/TOOL: fleet-triage a798ed6 "JEV CONTRACT RECOVERED"
- SCOUT-20 spawned QC-JEV3b on the `confidence != argmax` contract gap; fleet-triage then RECOVERED
  the real contract from the author's own client (achimala/jev-paint web/jev.mjs) and confirmed with
  a live 200. Details: request `model` MUST be `jev-latest` (jev-1.13.0 is response-only id);
  `criteria` values are `null` not descriptions; `type` is a required discriminator (`choice`/
  `noul`/`score`). Their example shows choice=grey, confidence=0.61, probabilities grey .74 —
  confidence is NOT the argmax prob. Their own words: "The distinction between the two fields has
  to be established before any n_eff or selective-risk claim is made on JEV output."
- Threat check against our assets: our DECIDE-1 lineage reads LOCAL logits from jeff-0.8b, not the
  JEV API — NOT threatened. QC-JEV (jeff-0.8b discriminating control) unaffected. QC-JEV3b spec is
  CONFIRMED and can now cite the recovered contract verbatim. CORROBORATE, no CONTRADICT.
- Nuance worth keeping: they say a 503/EOF is transport failure, NOT evidence about the request —
  "retry before concluding anything" — distinct from our NO-retry-on-429 rule (rate-limit vs
  transport-health are different failure classes; note for RC-1 harness design).

## TOOL/STEAL — quilt-organ-workers 51969e0 tip-anchor (wave-66, DEPLOYED + live-tested)
- External witness worker: POST /anchor (chain_id, tip, seq) → HMAC-signed KV row, never deleted;
  GET verifies. "An anchored tip cannot be tail-truncated silently." Live test caught a real bug
  (URL-encoded chain id not decoded on read path) because fleet chain ids contain `:`.
- DIRECT RC-4 prior art: anchoring receipts/manifest.json's seal digest externally at seal time
  makes RESEAL-FORGERY detectable (a forged fresh seal won't match the external anchor). Honest
  scope note (their own): trusted-timestamp witness, not a blockchain. Amend RC-4 spec; optional
  opt-in anchor step; secret discipline per their .env.keys pattern (keys never echoed).

## CORROBORATE — pong-quilt R75/R76 (d9ee1b2, d408d69)
- c1-scaling producer ported to main + durable reproduction pin (#97); R76 v1 draw ledger (#98).
  The #92 scaling-trajectory tool we flagged for the C1b lane is now ON MAIN — steal unblocked.

## MERGED/CONSUMED — MicroMoth-quilt
- #30 (grader 0.00 mutation shapes) and #32 (seal pin + selfplay widening, re-land) merged.
  Both already handled: RC-5 closed (push-time --check landed), 0.00-shapes folded into WIT-1
  class. No new spawn.

## META/CORROBORATE — fleet-triage 77b25af VALUE-LEDGER
- "5,471 issues opened, zero adoption" — their own adoption postmortem. Corroborates our
  book-in-files + no-filing doctrine: production beats ticket volume. Reading only.
- 80ddf89 GIFT-ORACLE (1998 technique for the fleet's failure) — reading item, LOW (spawned below).
- doubt-ledger wave-2/wave-3 (Ed25519 root signing, selective disclosure, qmr1-compatible export):
  additional RC-4 prior art (already noted SCOUT-20); wave-3 naming-alignment hedge worth a glance
  if we ever export receipts fleet-wide.
- quilt-tools referral-graph edges #14-#18 booked VERIFIED=1.0 — the fleet now has a booking graph
  for cross-repo consumption. Our QO6-consumes-delta-shape#1 edge is real and unbooked there
  (day item for Casey if he wants visibility; we do not file).
- fleet-seeds wave-66 synthesis + SEED-TOOLKIT charter (10 geometric primitives): consume later.
- tidepool #11 (skill-stall telemetry + WAL row-shape pins re-homed), backward-holdem v0
  (receipt-WAL breeding), quilt-in-git w3 union/wave4-query, Projectionist deploy spam, murmur
  (quiet since Sep 30 brief): no asset threat.

## CONTRADICT STATUS
**No CONTRADICT this sweep.** QO2 stack, receipt-manifest doctrine, QG3+QG6 time-law, QG1c census,
W5a/W5b/W5c edge-mine seeds, DECIDE post-mortems all unthreatened. QC-JEV3b's premise is now
CONFIRMED upstream, which strengthens (not threatens) the DECIDE-lane re-read.

## QUEUE ITEMS SPAWNED
- [ ] **SC-2** (CPU ~20m, amends QC-JEV3b before it fires): fold the recovered JEV contract into the
      QC-JEV3b pre-reg — cite a798ed6 verbatim (jev-latest alias, criteria:null, type discriminator,
      confidence-vs-argmax distinction, shuffle-control gate, transport-vs-schema failure class).
      Gate: QC-JEV3b must not fire citing the rotted contract.
- [ ] **RC-4a** (amend RC-4, CPU ~45m): seal-chain + external tip-anchor prior art — at seal time,
      optionally POST manifest digest to quilt-tip-anchor (opt-in, secret from .env.keys, never
      echoed); verification test: tamper → external anchor mismatch → RED. Honest scope: trusted
      timestamp witness. RC-4 remains the owner item; this is the anchor extension.
- [ ] **GO-1** (reading, LOW, ~30m): read fleet-triage GIFT-ORACLE (80ddf89) — the named 1998
      technique; check whether it maps onto QO2 budget triage or QG7 ensemble law or is their-local.
