# SCOUT-9 — SuperInstance fleet push sweep, 2026-10-01 22:11Z (day-conductor, non-GPU)
Delta window: since SCOUT-5 (19:11Z) to 22:11Z. Method: /users/SuperInstance/events + open-PR/issue search (read-only).

## Classifications

**CORROBORATE (direct cross-ref of OUR booking) — pie-minimax PR #2 "A1 closure receipt: nonlinear closes ~1.0 (P1 FAIL-HIGH)":**
independent MLP 9→64→9 × 3 seeds reaches global 0.9996 / composed 1.000 (P1 FAIL-HIGH > 0.6), linear repro 0.1807 exact,
5-fold CV 0.980 held-out; confirms the spec correction (180,361 rows = tree-path duplicates of 2,423 distinct boards).
They explicitly cross-ref quilt-gpu-lab commit 2978159 + results/pie_minimax_closure.json — i.e. our A1-PIE
KILL-of-prediction (commit d835e71, "MLP absorbs minimax composition 0.9643 vs linear 0.1429") is INDEPENDENTLY
REPLICATED upstream. No threatened booking; the strongest corroborate of the day. (Minor gap to note honestly: their
composed number 1.000 vs our 0.9643 — different seeds/architecture, same conclusion; no action.)

**TOOL/STEAL — quilt-edge-lab (NEW repo 18:43Z, Wave-1 receipts sealed + PRs #1-#4):** seeded CA receipt chains,
conservation ledger (gamma/eta), save-when-useful R2 promotion; W2.4 wraps promoted artifacts into fleet-state@v1
envelopes with vendored-pin drift tripwire (VENDORED-PIN.md, unmodified, 8/8 upstream pins green), 6/6 self-checks,
**tamper-loud at BOTH layers** (flipped tail char refused with both tails quoted), and — the gem — **P1 sealed FAIL
VERBATIM kept sealed because the failure is in the PIN'S own code (two chai-isms), with "un-seal = one-line typeof fix"
deliberately left undone**. That is our archive-never-delete / honest-verdict doctrine applied to a test harness:
they refuse to retro-fix a sealed pin mid-wave. Steal candidate: the vendored-pin drift tripwire pattern for any
edge-ledger/eproc consumption (QO6 uses eproc.mjs lineage-pinned by hash already — pattern matches, no change needed).

**TOOL — cot-quilt-lab (NEW repo 20:17Z):** "envelope/provider/stage/cell pipeline runtime + quilt sheet three-pens
(agent-321 experiment ideas)" — this is the direct consumer of XP-C's seam. XP-C booked KEEP-the-seam / KILL-the-local-
claim at 14:0x; cot-quilt-lab's lane C interface is now being built against it fleet-side. Watch item: their runtime
choices (serialized seat? grammar mode?) are the natural XP-C2 testbed — if they ship a serialized-window determinism
gate first, we consume their numbers instead of re-running.

**NOISE — Projectionist:** Casey's own app pushes (pocket cinema Level-3 assets, ~20 pushes today). Not agent
research; no classification beyond "captain's lane, do not analyze."

**HOUSEKEEPING (fleet-wide) — dependabot wave:** quilt-rag #12-15, quilt-fleet #16-20 (eslint/vitest/typescript bumps).
Upgrade-plan issues (#11-#76 across quilt-elf/swarm/SmartCRUD/rag/fleet) — tooling lane, no research signal.

**Open issues:** pie-minimax #1 (our FT-1 lineage — already DONE-VERIFIED by us, they closed the loop);
quilt-ewitness #1 (stale duplicate witness.mjs — corroborates our runner_sha256 provenance push);
[EMBASSY] items unchanged: moth-runner#2, substrate-llm-client#1, pong#49 (all still Casey day items, unresponded).

## CONTRADICT scan
None this sweep. The one candidate worth naming: pie-minimax#2's composed=1.000 vs our booked 0.9643 — direction
agrees (nonlinear ≫ linear), magnitude differs; classified CORROBORATE with a numeric caveat, not a contradiction,
because both are far above the pre-registered P1 threshold and the claim booked was KILL-of-prediction (thesis
weakened), which both results support.

## Queue items spawned
1. **EDGE-1** (CPU ~30m, LOW): read quilt-edge-lab Wave-1 receipts + W2.4 interop PoC in full; extract the
   vendored-pin drift-tripwire pattern into a one-page spec for any future vendored consumption in quilt-gpu-lab
   (candidate first consumer: eproc.mjs / edge-ledger in the QO6 gate). Gate: spec names every sealed pin it would
   wrap and the drift-tripwire cost.
2. **XPC-W (watch, zero-cost):** cot-quilt-lab's runtime is the XP-C2 testbed. Check their pushes next sweep BEFORE
   proposing any serialized-seat determinism re-run of our own; consume their numbers if they run it first.
3. **PIM-1 (close-the-loop, docs-only, ~10m):** our A1-PIE receipt should cite pie-minimax#2 as independent
   replication (and note the 1.000-vs-0.9643 magnitude caveat). Docs-only, no re-run.

## Session findings (this slice's (C) — booked in spool + RESULTS)
- Manifest RED: RESULTS.md drifted from sealed digest (6d3a11… sealed vs 80f8b9… on disk) — the XP-C/W5b2-era
  bookings landed without a re-seal. Re-seal BLOCKED by live foreign run (c1_playtest untracked files streaming);
  foreign-live precedent says don't touch. Seal deferred to first wake after the c1 run completes.
- Provenance gap (RC-1 family, XP-C instance): xp_c_results.json embeds no runner_sha256/args (code list exists in
  artifacts.code, but no hash binding). Behavioral re-fire is non-verifying anyway per XP-C's own KILL (local seat
  not byte-reproducible; co-tenancy flake) — so static audit is the correct (C) for this booking: verdict/gates
  re-read from the committed artifact and consistent with the booking text (A 20/20 refusal PASS, B byte_identical
  false FAIL, C local_rate 0.9333 < 0.95 FAIL, cloud 30/30). KILL booking reproduces as documented.
