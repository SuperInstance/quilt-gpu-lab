# SIG-1 — HMAC prereg seal (prereg)

Spawned by SCOUT-49 (2026-10-06): taskable-lobster's signed Git task queue ("the signature is the leash") =
transferable D-2 defense for OUR PREREG files. Docs-only + tool + test; no GPU; CPU seconds.

## Frozen gates (words)
- G1 SEAL DETERMINISM: `tools/prereg_seal.py seal <file>` with env secret produces a seal record
  (hmac-sha256 over canonical bytes, key-id = sha256(secret)[:8] — never the secret itself). Two seals of the
  same file+secret are byte-identical. A missing/empty secret REFUSES to seal (exit 2, fail-loud).
- G2 VERIFY CLEAN: `verify <file> <seal>` on untouched file returns MATCH (exit 0).
- G3 TAMPER RED-FIRST: flipping ONE byte of the sealed file (or the seal digest) must return TAMPERED (exit 1).
  Test asserts RED behavior against the sealed original before any green check.
- G4 REFUSE-TO-FIRE hook: `check` subcommand is the gate a runner calls before firing; on missing seal or
  TAMPER it exits nonzero and prints the prereg path. Documented in file header.

## Cost
CPU only, seconds. Secret sourced from env `PREREG_SEAL_SECRET`; never written, never echoed, not committed.
Adoption (wiring into runner pre-fire) is a protocol change → deferred to Casey (day item), same as LC-1.
