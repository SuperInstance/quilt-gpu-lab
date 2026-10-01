# SCOUT-15 — fleet push sweep 2026-10-01 16:11Z (day-conductor, (A)-first rotation, non-GPU)

Scope: `/users/SuperInstance/events` (user account, not org) + open PRs + [EMBASSY] search. Read-only, nothing filed.

## State changes since SCOUT-14 (~1311Z)

1. **fleet-triage PR #1 UPDATED 16:08Z — "RTX 4050 worklist — GPU-only work for the fleet's consumer-GPU agent".**
   Per Kimi directive 10/1. Three buckets + think-big trio, each with smallest-first build + receipt format,
   adopting GPU-EXPERIMENTS §0 as standing rules. This is a DIRECT HANDOFF to this lab. Classifications:
   - (CONSUME/STEAL — B3) **MiniMoth→CUDA statevector, bit-exact vs sealed exp008, n=4→16-20.** This is the
     exact instrument QG1d needs: our provenance-gap finding (exp022's generator imports a nonexistent
     `qcell.search`; recorded train_p/verify_p not reproducible) could be CLOSED by a bit-exact CUDA
     reimplementation of micromoth's simulator — rebuild a failing genome in it and separate "recorded values
     stale" from "fitness definition differs". Spawned **MMX-1** (pre-reg before fire).
   - (STEAL — D1) **GPU-native cell runtime (100-1000x ticks)** — direct successor to our D12h/i/j lane: the
     W·T product law (T_floor ~ C(N,p)/W, floor ≤2 at W=128) predicts what a 1000x-tick runtime buys; a
     batched runtime would let QG4 (budget/gens phase diagram) run at real scale. Spawned **FT-D1** (design
     note first, GPU later).
   - (CONSUME — A2) xruntime-conformance at scale + DETERMINISM LAB: aligns with open XR-1; our QG1 census
     radians incident is the local instance of their determinism canon. No new item (XR-1 already open).
   - (CONSUME — A6) murmuration ensembles: QC-JEV already dismissed the jev-1.13.0 null for jeff-0.8b;
     QC-JEV2 (second checkpoint + unclear band) is the standing bridge item. No new item.
   - (CONSUME — B1/C1) pong derived-law distillation + C1 pop-eval batching: not our assets; leave to
     pong/quilt-nn lanes. (C) play-tester bucket: day item for Casey (needs Qwen weights + his priorities).

2. **jev-quilt 44th/45th-wipe (15:06Z, 16:08Z): mean_p 0.6014-0.6024, 7/7 bedrock, 0 drift, 7th consecutive
   session.** (CORROBORATE) An oracle whose positive-probe mean_p sits ~0.60 is a WEAK discriminator — same
   family as murmuration's jev-1.13.0 unclear band (0.74/0.79) and far from our jeff-0.8b d_ptrue 0.936
   (QC-JEV). Cross-artifact contrast is now three-witness: checkpoint identity dominates oracle quality.
   Sharpens QC-JEV2: the unclear-band pin should be per-checkpoint, and any DECIDE-2 head-retrain receipt
   must carry a discriminating control (already flagged for Casey).

3. **Overnight-sync auto-pushes only (no substantive deltas):** crab-traps (15:33Z, last real content
   47-b two-reader rule from 9/28), qthe (wave-52 residue, CRAB resolution chain + mtime-witness law —
   (TOOL) note: their npm-mtime-normalization receipt is another runtime-bound-pin instance, same class as
   our RECEIPT-HASH caveat and quilt-nn#1; RC-2/WIT-1 already cover it), quilt-playtest, codespace-worker,
   MicroMoth-quilt (15:33Z sync; last real content = #29 merge, already handled).

4. Projectionist / taps-creative-break: Casey's creative lanes (pocket cinema, voice-wipe rounds). Not lab
   material, no action.

5. **[EMBASSY] unchanged:** pong-quilt#49 (stranger-verified r37 chain) still unresponded — day item for
   Casey, unchanged since SCOUT-8.

## Queue items spawned
- **MMX-1** (GPU ~45m after ~20m CPU recon): MiniMoth→CUDA statevector bit-exact vs sealed exp008;
  primary purpose = QG1d closure instrument. Gate: byte-identical statevectors vs exp008 pins at n=4
  before any n=16-20 scaling claim.
- **FT-D1** (design note first, non-GPU): GPU-native cell runtime spec, sized by the D12h/i/j W·T law;
  success gate = QG4 phase-diagram cell at W=128/gens=100 in <10 min wall on the 4050.

## Rotation note
Non-GPU slice per (A)-first. GPU lane free; untracked INSTRUMENT-01/S6a/S6b pre-regs in the tree are NOT
mine (farm/foreign-live precedent, PW-1) — untouched, flagged for the owning lane's wake.
