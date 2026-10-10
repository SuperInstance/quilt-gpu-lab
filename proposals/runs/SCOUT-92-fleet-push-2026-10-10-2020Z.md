# SCOUT-92 — fleet push sweep 2026-10-10 2020Z (day conductor, (A) rotation)

Window: post-SCOUT-91 (1717Z) → 2020Z Oct 10. Sources: quilt-research-canons fetch (origin/main
3595add → d5c8ccc, one new scout), org PR/issue lists (quilt-gpu-lab + canons: zero open),
quilt-gpu-lab running processes (none). GPU lane idle; foreign d12* untracked lane persists
(PW-1, untouched).

## Window pushes
- **canons d5c8ccc (1925Z, the only external push):** three findings + hygiene + method notes.
- PRs/issues: none anywhere relevant. [EMBASSY]: pong #49 unchanged (Casey day item).

## Classification vs our live assets
**No CONTRADICT.** QO2 stack (QO1 oracle + QG3/QG6 triage + QO6 eproc), DECIDE-1/2 lineage,
receipt-manifest doctrine bookings, QG3+QG6 time-law, QG1c swap census, W5a/b/c seeds — all
unthreatened. All three headline victims are foreign repos.

1. **fleet-witness: audit() never reads git history — CORROBORATE that RAISES RC-4.** The attack
   executed in their report is exactly our reseal-forgery class: attacker with write access
   re-seals correctly because *sealing is not a secret operation*, and the verifier consults a
   mutable working-tree file (LATEST) rather than the committed anchor. Our manifest --check
   (RC-5, push-time) compares sealed digests vs *working tree* tracked files — the same shape
   gap fleet-witness died of: nothing in the verify path reads back through git history, and a
   valid RE-seal of tampered content is undetectable. RC-4 (seal-chain / reseal-forgery
   resistance, open since SCOUT-16) is the direct counter-instrument → **priority RAISED
   (5th witness; fleet-witness is the first with the attack EXECUTED end-to-end).**
2. **guardc-v3: proof certificates with no prover — TOOL/row for FW-1-successor.** `smt_lib`
   is a proof-shaped string never handed to a solver; 6/8 constraint kinds stamped
   `discharged: true` unconditionally; verify_chain re-derives nothing (hashes the file to
   itself). Named new subclass: **proof-shaped field never handed to the tool it names** —
   add the census row (grep for solver/runner/prover invocations behind any field whose name
   claims one). Composes with PARAM-1a (vacuous gate) and TIE-1 (tie-case resolves to pass).
3. **fleet-homology: Laman count identity returned as rigidity — note, no new item.** Graph
   invariant certifying an unobserved geometric property; one-sided detector can't see its own
   failure mode (hinge returns "exactly rigid"). Same measure-wrong-thing family; the
   unfalsifiable `usize >= 0` asserts are already covered by d8f5a63 mut-adequacy (kill rate,
   not coverage) — scout's free detector (grep `assert!` on unsigned fields) noted there.
4. **Hygiene (intuition 253 MB weights + tracked .pyc, no .gitignore; zai-router 2 files incl.
   a .pyc):** VSB-1/CI-1 covered class; scout's `git ls-files` one-shot detector already
   embodied in VSB-1. **zai-router hardcodes local absolute paths** including a Windows-side
   key path — keys-never-echo discipline note; no action by us, Casey-adjacent FYI only.
5. **Method notes worth keeping:** (a) API `size` ≈ 99% git history — rank on tree bytes
   excluding .git (confirms SCOUT-25 caveat, now measured); (b) read the test NAME against the
   test BODY (one level below README-vs-implementation — candidate FW-2 row); (c) environment-
   induced red is not a defect (3rd scout instance of hermetic-suite failures).

## Spawned / raised queue items
- **RC-4 PRIORITY RAISED** (existing open item, SCOUT-16): 5th fleet witness, first with
  executed attack. Next cheap wake should take it (chain each seal to previous seal digest;
  tamper test red-then-green; forged-RE-seal must resolve FORGED, not clean).
- **GIT-ANCHOR-1** (CPU ~15m, pre-reg first): census + test that our receipt verification reads
  committed content, not only the working tree — verify sealed digests against `git show HEAD:
  <path>` blobs; mutation: tamper a file AND commit it, then re-seal; the verify path must
  surface the drift vs the booked landing's commit SHA (fail-loud RED-first). Guards the
  fleet-witness shape on OUR doctrine tool.
- (no third spawn: homology/hygiene/guardc land as rows on existing ledgers FW-2, VSB-1,
  PARAM-1a/TIE-1, d8f5a63 mut-adequacy.)

Rotation next wake: (B) RC-4 (raised, top) or GIT-ANCHOR-1; GPU open (QG4/QG1d-corpus/MC-1).
