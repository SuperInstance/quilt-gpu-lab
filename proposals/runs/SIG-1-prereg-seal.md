# SIG-1 — HMAC prereg seal + refuse-to-fire (spawned SCOUT-49, priority RAISED SCOUT-53)

## Motivation
taskable-lobster vanished from the SuperInstance account within ~20h of its HEADLINE push
(SCOUT-53). If fleet repos can disappear, our prereg/proposal files (the thing that makes a
booking honest) have no durable defense short of a local sealed copy. Signed-frozen-gate
pattern (taskable-lobster: HMAC-SHA256 over canonical JSON, "the signature is the leash").

## Deliverable
`tools/prereg_seal.py` — seal / verify subcommands over a prereg file:
- **seal**: sha256 of the file, wrapped in canonical JSON, HMAC-SHA256 with key from env
  `QUILT_SEAL_KEY` (fail loud if unset); writes `<file>.seal.json` next to it.
- **verify**: recompute digest; MATCH / TAMPERED (exit 2) / MISSING (exit 3).
- Never echoes the key; never writes the key anywhere.

## Pre-registered gates
- **G1 roundtrip**: seal a scratch prereg -> verify returns MATCH, exit 0.
- **G2 tamper RED-first**: flip one byte of the sealed file -> verify returns TAMPERED, exit 2.
  (RED-first: run tamper case BEFORE trusting any PASS.)
- **G3 key discipline**: seal with `QUILT_SEAL_KEY` unset -> refuses, exit nonzero, no seal file
  written. Seal file contents contain NO key material (grep negative).
- **G4 repo integration**: the committed prereg files under proposals/runs/ that we seal as the
  pilot (this file + SCOUT-49 spawn note) verify MATCH from the committed tree.

## Cost
CPU only, ~20m. No GPU.

## STOP rule
If canonical-JSON key ordering makes digests platform-fragile (verify fails on re-run in a
fresh process), STOP and book the fragility rather than patching mid-fire.
