# SIG-1 prereg — HMAC prereg seals (SCOUT-49 variant), 2026-10-06 05:1xZ

Scope (SCOUT-49 spec, CPU ~20m): prereg FILES get a D-2 silent-edit defense. Tool
`tools/prereg_seal.py`:

- `sign <prereg.md>`: HMAC-SHA256 over the file's raw bytes, key from env
  `QUILT_PREREG_KEY` (local-only, never echoed, never written by the tool). Writes
  `<prereg>.sig` containing the hex digest + timestamped comment line. Refuses (exit 3)
  if key unset — fail-loud, no fallback.
- `check <prereg.md>`: recompute and compare; exit 0 match, exit 2 MISMATCH, exit 3
  missing/unset key, exit 4 missing sig file. Constant-time compare.

Gates (pre-registered, in words):
- **G1 (RED-first)**: tamper control fires BEFORE the green path is booked. Take a signed
  prereg, flip one byte in a scratch copy, `check` must exit 2. If the green path is
  observed before the tamper refusal, this run is void (RED-first rule).
- **G2 (green path)**: `check` on the untouched signed prereg exits 0.
- **G3 (fail-loud)**: `check` with key unset exits 3 (not 0, not a silent pass); `sign`
  with key unset exits 3 without writing any `.sig`.
- **G4 (no-leak)**: key material never appears in any output, sig file, or stderr.
- **G5 (scope)**: the tool touches ONLY the given prereg path's sibling `.sig` — it does
  NOT touch tools/receipt_manifest.py or the results sealer (SCOUT-9's SIG-1 design note
  remains Casey-gated; this run generates no persistent key material; the test key is a
  throwaway env value set per-invocation).

Threat named: the D-2 silent-edit class on pre-registrations (a prereg edited between
commit and fire silently changes frozen gates). SCOUT-49 source: taskable-lobster dafcf82d
signed task queue (HMAC-SHA256 canonical bytes, env secret, refuse unsigned).
Tamper-evidence boundary: an agent that can read the env key can forge — accepted for this
scope; the out-of-agent-process keyfile design stays in the Casey-gated note.

Timebox: 20 min. If exceeded, book partial with whatever gates passed, marked PARTIAL.
