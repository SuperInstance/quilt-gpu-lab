# SCOUT-40 — fleet push sweep, window post-SCOUT-38/39
Fired: 2026-10-04 03:11Z (day-conductor slice, Sat 19:11 AKDT). Read-only gh API. Window: since 2026-10-03T22:00Z.

## Window contents (14 repos swept)
- **fleet-triage e6c46aa/d721acb/0cc423d** — sign-off + gitignore purge. ALREADY BOOKED SCOUT-38 (we were the
  classifier of record there). No new delta.
- **jev-quilt 780671e** — 75th hourly wipe, 0 drift. CORROBORATE (QC-JEV untouched).
- **quilt-research-canons 21bc59f + 3fa5254 (NEW)** — **key-rotation event 2026-10-04**: CF-only regime,
  "key-loss != model-loss", 17 model families verified live; groq restored via CF relay; bun staged.
  Classify: OPERATIONAL / TOOL. No quil-gpu-lab asset touched (our instruments are repo-local, no keyed API
  in the pinned tool set). But our MMX/DeepInfra-adjacent lanes live on Casey's keys — if any future lane
  needs a keyed API, check canons key-rotation notes first. Spawned **KR-1** (one-line check, before any
  future keyed fire: read canons key-rotation part 2, confirm needed provider live).
- **quilt-research-canons f55e8cb (NEW)** — SCOUT 2230Z: conservation-law tautology, stub verifier,
  pytest||true, 2 verified gates. CORROBORATE — the failopen/decorative classes (RC-1b, CI-1 bill) stay
  non-vacuous; no new subclass beyond what SCOUT-37 caught (fa7504d).
- **quilt-ewitness fc0b3d6 (NEW, most substantive)** — issue #1 closed: src/witness.mjs was a STALE DUPLICATE
  with imports that do not exist in eproc.mjs (geometricGrid/makeDriftMixture/makeApproachMixture) — crashed
  both experiment runners; two incompatible witness() APIs. Archived by rename (archive-never-delete, our
  convention too). Classification vs our assets:
  - **CORROBORATE (strong)**: this is the DEL-1/witness_compartment class found INDEPENDENTLY upstream —
    dead code that reports itself as load-bearing. Second fleet witness of decorative-path class. Our RC-1b/
    DEL-1 bills non-vacuous again.
  - **QO6 threat check (CONTRADICT candidate → cleared)**: QO6's eproc.mjs port is lineage-pinned to
    61b9e04/aad90ac5. The fix retires witness.mjs and does NOT touch eproc.mjs exports at the pinned sha
    (eproc exports logsumexp/increments/eprocess/witness — exactly the surface we ported). The dead duplicate
    was never in our port. No booked result threatened. **EW-1 spawned** (5-min docs): append an
    upstream-delta note to the QO6 receipt citing fc0b3d6 + #1, so future re-ports don't resurrect
    witness.mjs.
- **pong-quilt issue #108 (NEW)** — Round 86 re-land receipt audit + fresh-checkout P1 repair addendum.
  Their lane, their discipline; read-only note. No action.
- **quilt-dba wave-69 (735f346/b0d882d/237d57b)** — sxc1 stitch chain of record + CI/spec-first gate.
  Already partially covered SCOUT-37; 237d57b "first CI + spec-first gate" = CI-1/spec_sha convergence
  corroborate (4th+ witness). No CONTRADICT.
- madlibs-jev (ee7b73a stack), xruntime-conformance, quilt-cell-harness, micrograd/MicroMoth, pie-minimax:
  nothing new in window (spec_sha stack booked SCOUT-36).

## Verdict
- **No CONTRADICT this sweep.** QO2 stack, receipt doctrine, QG3+QG6, QG1c, W5a/W5b, DEL-1 all unthreatened.
- Strongest finding: quilt-ewitness #1 = upstream independent discovery of the decorative-path class our
  DEL-1 audit targets — convergent-law corroboration.
- (C) not due: newest OURS booking DEL-1 already repro PASS (8061e61); HEAD since is spool/docs/foreign.
- Manifest re-seal: still deferred (foreign d12k2–d12r untracked live lane persists; sealer correctly refuses).
- [EMBASSY] pong #49 unchanged (Casey day item).
- Rotation next wake: (B) EW-1 docs then KR-1 gate line; GPU open (QG1d/QG4/MC-1).

## Spawned items
- [ ] **EW-1** (docs ~5m): QO6 receipt upstream-delta note — cite SuperInstance/quilt-ewitness fc0b3d6 + #1;
  pin "port surface = eproc.mjs exports only; witness.mjs was dead duplicate, retired upstream."
- [ ] **KR-1** (standing gate, 0 GPU): before any future keyed-API fire, read canons key-rotation part 2
  (21bc59f/3fa5254) and confirm the provider is live in the post-rotation regime.
