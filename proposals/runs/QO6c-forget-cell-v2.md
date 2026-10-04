# QO6c — forget_cell v2: tombstone-by-append

Spawned by QO6b's booked FAIL (2026-10-04 19:1xZ): tombstone-by-mutation is
chain-breaking by construction — `forget()` edited the witness receipt's `status`
in place after its digest was computed, so every honest verify() returned TAMPERED
(erasure-as-edit is indistinguishable from D-2 silent edit). LESSON booked: erasure
evidence must be APPENDED, never substituted.

## Change from QO6b (single delta)
- `forget()` no longer mutates the witness receipt. The witness receipt's bytes
  (including `status: "witness"`) are frozen forever; the appended FORGET receipt
  (`{shot, reason, erased_id}`) is the sole erasure evidence. Forgetting is a
  property derived from the presence of a FORGET receipt, not a field edit.
- `rederive()` re-computes the witness digest from the untouched bytes (no status
  reconstruction hack — the QO6b `base["status"] = "witness"` patch is deleted).

## Gates (frozen, inherited verbatim from QO6b pre-reg)
- **G1 tamper-evidence through erasure**: flip one byte in a witness receipt
  payload post-FORGET → verify() = TAMPERED with exact seq; flip the FORGET
  receipt's reason → TAMPERED.
- **G2 erased_id diff**: honest forget → rederive(shot) == erased_id; attacker
  re-seals a FORGET with a WRONG erased_id → caught by rederive.
- **G3 non-wedge (canvas-tui trapdoor)**: after FORGET, verify() = VERIFIED;
  append of a NEW witness works; re-verify = VERIFIED. No exception, no restart.
  Empty-ledger control: verify() = VERIFIED.
- **G4 fail-first pins**: unknown-shot forget raises; double-forget raises;
  append with missing shot/kind raises; append under an erased shot raises.

## Verdict
PASS iff all four gates PASS. Any FAIL → booked FAIL with gate named; no re-roll.

## Cost
CPU only, seconds. No GPU lane touched.
