# SIG-1b — keyless verify mode for prereg_seal (spawned by SIG-1 repro PARTIAL 06:1x)

## Motivation
SIG-1's committed repro in cron was key-blocked: `verify` requires QUILT_SEAL_KEY, which
lives only in Casey's env. A keyless mode must still catch the D-2 silent-edit class
(content drift) even though the HMAC layer is untestable without the key.

## Deliverable
`verify --keyless FILE` subcommand: skips the HMAC comparison, compares the file's current
sha256 against the digest recorded INSIDE the seal envelope. Output names the unverified
layer explicitly (HMAC UNVERIFIED — never a silent downgrade to MATCH).

## Pre-registered gates
- **G1 digest roundtrip (keyless)**: `verify --keyless` on a sealed, unmodified file →
  `DIGEST-MATCH` + explicit `HMAC UNVERIFIED`, exit 0.
- **G2 tamper RED-first (keyless)**: flip one byte of the sealed file → TAMPERED, exit 2,
  keyless (RED-first: tamper case run before any PASS is trusted).
- **G3 unchanged legacy behavior**: keyless on missing seal → exit 3; bad usage → exit 4;
  keyed verify unchanged (flag not required when key present).
- **G4 committed-tree integration (keyless)**: the committed sealed prereg
  `proposals/runs/SIG-1-prereg-seal.md` verifies DIGEST-MATCH keyless from the committed
  tree — this is the cron-runnable repro arm for every future sealed prereg.

## Cost
CPU only, ~20m. No GPU.

## STOP rule
If keyless verify could be confused with a full HMAC MATCH (exit-code or wording ambiguity),
STOP and book the ambiguity rather than shipping a downgrade-in-disguise.
