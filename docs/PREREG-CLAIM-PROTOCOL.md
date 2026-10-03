# Pre-reg claim protocol (2026-10-01, after the D12j race)

Context: the D12j pre-reg (0b2df86) was implemented and fired twice within ~30 minutes — once by a
wheel lane, once by Lucineer — on the same file paths. Git kept everything and the double run became
a two-witness KEEP (see the reconciliation section in RESULTS.md), but the outcome was luck, not design.

## RT-D1: real-vs-repro differential pin (2026-10-03, from fleet-triage b04b1e6 REAL-PROBE)

A **bit-exact repro proves the committed code produces the committed result. It does NOT prove the
committed code describes the real thing.** Whenever a booking depends on a REIMPLEMENTATION of an
external system (their model, their simulator, their fitness rule), the booking is incomplete until
a second pin exists: the REAL thing, running headlessly, probed directly, with its output recorded
next to the repro.

Rule (effective now):
1. Any pre-reg whose instrument reimplements an external system MUST include a **real-probe arm**:
   invoke the real artifact in place (its repo, its wheel, its checkpoint) headlessly, on at least
   one shared input, and record its output digest alongside the reimplementation's.
2. Agreement => the booking cites both. Disagreement => the repro pin is VOID for external claims;
   book the delta, name which side is stale (per fleet-triage: this probe class "refuted my own
   recommended fix" — that is it working).
3. If the real thing cannot run headlessly (heavy UI, license, hardware), the booking must carry an
   explicit `real-probe: UNRUN — <reason>` line. No silent omissions.

Applies to: **MMX-1** (MiniMoth→CUDA statevector must be probed against real micromoth.py on the
same genome, not just sealed exp008 bytes) and **QG1d** (the rebuilt p_target must be probed against
any recoverable real definition; if unrecoverable, QG1d books `real-probe: UNRUN` and the exp022
reproducibility gap stands as the finding).

## Rules (effective now)

1. Every pre-reg carries an `owner:` line at the top:
   - `owner: farm` — the farm/wheel owns firing. Main session MUST NOT self-fire it.
   - `owner: lucineer` — Lucineer self-fires. Wheel lanes MUST NOT grab it (check owner before
     implementing).
   - `owner: any` — explicitly raceable. Double runs are welcome; both MUST be preserved and the
     result booked as two-witness.
2. Defaults: GPU/lane work → `owner: farm`. Instrument laws and cheap independent probes that benefit
   from a second witness → `owner: any`.
3. Collision recovery (if it happens anyway):
   - Never overwrite a committed artifact in the working tree.
   - Restore the owner's files from their commit; preserve your copy as `<name>-<side>.py` /
     `<name>-<side>.json`.
   - Book a reconciliation section in RESULTS.md; commit message says "reconciliation".
4. `tools/farm_queue_flip.py` already refuses to arm anything whose prereg is not committed
   (exit 2, refuse-loud). Keep that gate.

— Lucineer, 2026-10-01, after spending the morning untangling a race we happened to win twice.
