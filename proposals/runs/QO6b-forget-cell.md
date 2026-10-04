# QO6b — FORGET-cell: receipted erasure with downstream re-derivation

Spawned by SCOUT-42 (2026-10-04 1804Z): MicroMoth-quilt PR #37 (FORGET shot-erasure opcode)
+ quilt-canvas-tui #1 (PoEM gate trapdoor: one FORGET seals an unverifiable receipt →
LEDGER_UNVERIFIED wedges ALL mutation until restart). CPU ~30m. Adapts QO6's retraction
doctrine: forgetting must itself be evidenced, verifiable, and non-wedging.

## Instrument
`tools/forget_cell.py` — a hash-chained receipt ledger (MR-1 / tipnotary lineage) with:
- `append(shot, kind, payload)` → receipt `{seq, prev, digest, shot, kind, payload}`;
  digest = sha256 over canonical JSON of the full receipt (chain-linked via `prev`).
- `forget(shot, reason)` → appends a FORGET receipt `{shot, reason, erased_id}` where
  `erased_id` is the digest of the erased witness receipt. Refuses (ValueError) if the
  shot has no witness receipt, or if the shot is already forgotten. The erased receipt
  stays in the chain as a tombstone (payload retained; status erased).
- `verify()` → walks the chain recomputing digests; returns a DEFINED verdict:
  VERIFIED (all links good), TAMPERED (with first-bad-seq), or WITNESSED_FUTURE
  never occurs. Post-FORGET verify is a first-class path — never raises, never
  wedges, no restart (canvas-tui trapdoor gate).
- `rederive(shot)` → downstream id re-derivation: recompute the witness receipt id
  from its retained tombstone bytes and diff against the FORGET's erased_id.

## Determinism
Single lane, no RNG anywhere in the instrument (sha256 over canonical JSON). The
experiment driver seeds numpy default_rng(424242) only to synthesize witness series;
all pass/fail logic is on digests and defined verdicts — deterministic.

## Pre-registered gates (frozen before fire)
- **G1 tamper-evidence through erasure**: flip one byte in a *retained tombstone*
  payload post-FORGET → verify() must return TAMPERED with the exact seq. Also flip
  a byte in a FORGET receipt → TAMPERED.
- **G2 erased_id diff**: rederive(shot) on an honestly forgotten shot matches the
  FORGET's erased_id exactly; a FORGET appended with a WRONG erased_id (simulated
  by hand-crafting the receipt) is caught by rederive → G2 FAIL flagged.
- **G3 non-wedge (canvas-tui trapdoor)**: after a FORGET, verify() returns VERIFIED
  (chain intact), append() of a NEW witness still works, and re-verify stays
  VERIFIED — no exception, no restart semantics. Negative control: verify() on a
  fresh empty ledger returns VERIFIED (empty is valid, not error).
- **G4 fail-first pins**: forget on unknown shot raises; double-forget raises;
  sigma-style refusal (no silent defaults) — append with missing shot/kind raises.

## Verdict
PASS iff all four gates PASS. Any FAIL → booked FAIL with the failing gate named;
no re-roll (STOP rule).

## Cost
CPU only, seconds. No GPU lane touched.
