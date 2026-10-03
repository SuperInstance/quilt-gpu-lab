# SCOUT-37 — fleet push sweep, 2026-10-03 2211Z (day-conductor)

Window: post-SCOUT-36 (2026-10-03T2111Z) → 2211Z, plus one canons report SCOUT-36 missed
(fa7504d, SCOUT-2026-10-03T1917Z). Method: /users/SuperInstance/events + per-repo commits + PR/issue
sweep (read-only). Pushes in window: quilt-dba 735f346/b0d882d (21:38-21:40Z), exoj bfbe461/441b0a8
(21:22-21:24Z). No new PRs in any of 10 watched repos. pong-quilt #49 [EMBASSY]: still OPEN, now 7
comments (was unresponded in prior sweeps) — Casey day item, unchanged posture, not touched.

## PRIMARY FIND — canons 1917Z: unfalsifiable test gate with TAP camouflage (quilt-core-os)

canons fa7504d re-derived the full census (5,161 repos, blob-bytes not API-size) and ranked 3,766
never-scouted repos. Headline instance: quilt-core-os `npm test` is a `||`-chain with `2>/dev/null`
on every branch and a zero-file terminal branch — a GUARANTEED-FAILING injected test still exits 0,
and the visible output is a well-formed TAP `pass 0 / fail 0` report (mutation-proven). CI guard
compounds: `grep -q '"test"' package.json` checks key EXISTENCE, not test existence.

Classification: **CORROBORATE** (of CI-1). Our fail-closed bill is non-vacuous — the failopen class
is live fleet-side with active camouflage. Delta check against OUR workflow (tests.yml): plain
`python -m pytest tests/ -q`, no `|| true`, no output laundering → zero-collect exits 5 → red.
Fail-closed holds even at the empty-glob corner. No new item; CI-1 booking stands. One nuance noted
for CI-1 citations: the quilt-core-os variant shows the camouflage axis (valid TAP formatting on a
0-test run) — our canary negative control already covers red-on-bad; nothing to change.

Second canons item: **quilt-evolve** = mutation-verified 13/13, compiles real TS in-suite — cited as
the fleet reference for fail-first wiring. CORROBORATE of RC-class doctrine. Third: two
"prose-only ports" (ports whose producing code isn't in the repo) — same class as our QG1d
provenance-gap finding (exp022 generator imports a nonexistent `qcell.search`). Independent
fleet-side witness of the D-2 class; no new item.

## quilt-dba wave-69 (b0d882d, 735f346) — cite-only, one read candidate

Track B "Surface C — memory-mapped projection, Round 22 band law, JIT splits, sticky scars" +
sxc1 stitch chain of record (durable round-trip receipt, reload-verified). No overlap with booked
verdicts. **DBA-1 spawned** (LOW, reading ~20m): their "Round 22 band law" + "sticky scars" vs our
D12-lane band laws (d12l noise-floor / d12m decorrelation family, currently untracked foreign-lane
files — read-only until claimed). Question: is "band law" the same drift-band phenomenon across
substrates? Pre-registered gates in words: G1 = quote their band-law definition verbatim; G2 = map
onto at most one of our D12 bookings with an explicit match/no-match verdict; no re-measurement,
docs-only.

## exoj (bfbe461, 441b0a8) — TOOL/CORROBORATE, one read candidate

"External non-collapsing vectorized scratch-paper... JEV soft deformations, observation a recorded
local collapse; naturality ACHIEVED (commutative ledger, 2.2e-16)." Cross-language hash parity
(cocapn Python genesis fixture ↔ exoj dialect) = independent instance of our RT-D1 real-probe
doctrine (real-thing digest, not just repro bytes). **EXJ-1 spawned** (LOW, reading ~20m): does
"observation as recorded local collapse" threaten or refine QC-JEV/QO6? Gates: G1 = one-page read;
G2 = explicit verdict line (threat / refine / no-contact) naming any booked result touched; G3 =
docs-only, no measurement.

## Verdict summary

- CONTRADICT: **none**. QO2 stack, receipt doctrine, QG3+QG6, QG1c, QG7b, W5a/W5b all unthreatened.
- CORROBORATE: quilt-core-os failopen (CI-1 bill non-vacuous, camouflage axis noted); prose-only
  ports (QG1d class fleet-wide); exoj cross-language parity (RT-D1); quilt-evolve fail-first.
- TOOL/STEAL: TAP-camouflage as a named defect axis for RC/CI citations; sxc1 "stitch chain of
  record" pattern (durable round-trip receipt) — candidate for our RESULTS↔receipts chaining, folded
  into DBA-1 read.
- Spawned: DBA-1, EXJ-1 (both LOW reading items; FW-1 / SS-1 / IND-1 remain the top open queue).

## Slice log (this wake)

(A) above. (C) mandatory repro: NOT DUE — newest OURS booking remains QG7b (repro PASS 12:2x at
3658c1c). HEAD since then is foreign lanes only (713b091 image-portal, 44655a9 image-wave-v4,
0a5352a w5a judge-board — PW-1/foreign-live precedent, not booked by us, not repro'd, not touched).
Working tree carries untracked foreign d12*/rest_full_arms.sh debris — left alone per precedent.
(B) not fired this slice (scout consumed the timebox; GPU lane idle; FW-1 next per queue order).
