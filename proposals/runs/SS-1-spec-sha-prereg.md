# SS-1 — spec_sha pin tool for pre-registration files (pre-registration)

Spawned by SCOUT-36 (fleet-wide spec_sha prereg convergence: madlibs-jev ee7b73a,
unspoken-resonance 3ad67d4, quilt-dba, purpose-loops — canon-form sha256 pin of frozen
gates committed before implementation, --check never-writes, INDETERMINATE receipts stop
feeding learned state). No fleet repo of ours currently carries this instrument.

## Instrument
tools/spec_sha.py — canon-form sha256 over prereg files (UTF-8, CRLF->LF, trailing-
whitespace strip, blank-run collapse, final newline: cosmetic churn inert, word edits
move the pin). Modes: pin / --init (only writer) / --check (never writes).

## Gates (frozen, in words)
- G1 DETERMINISM: same file -> same pin across two invocations. Cosmetic-only edit
  (trailing whitespace, blank-line runs, CRLF) does NOT change the pin; a word-level
  edit DOES.
- G2 VERIFY-SWEEP: ledger receipts/spec_sha_pregen.json built over ALL
  proposals/runs/*prereg*.md (current bytes); --check over the whole ledger returns
  MATCH on every entry (exit 0). Honest scope note: this is a SNAPSHOT seal of the
  current prereg corpus (retroactive); forward convention = record spec_sha at the
  prereg commit. This validates the instrument, not historical immutability.
- G3 RED-FIRST: (a) tampered copy (one word changed) -> MISMATCH exit 2; (b) file
  deleted -> STALE exit 3; (c) file present but unpinned -> UNPINNED exit 4.
  All three loud, none pass.
- G4 NEVER-WRITE: --check run against the live tree leaves byte-identical tracked
  tree and ledger (digest before == digest after; ledger mtime unchanged).

## Verdict rule
GREEN iff G1-G4 all pass. Any silent pass on a G3 mutation = RED on this booking.

## Cost
CPU only, ~10 min. Serial, no GPU.
