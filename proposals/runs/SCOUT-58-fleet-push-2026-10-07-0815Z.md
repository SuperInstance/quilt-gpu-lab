# SCOUT-58 — 2026-10-07 08:15Z (00:15 AKDT day-conductor slice). Read-only sweep.

## Window
Pushes since 2026-10-07T06:15Z across 13 watched repos + SuperInstance events.
Single external state change: **quilt-research-canons 917e627** — SCOUT 2026-10-07T0726Z
"the canary primitive is not the fleet's". PRs: quiet (0 open in 8 checked repos).
Issues: only zero-msg-test noise (#2-#11, self-escalation spam). [EMBASSY] pong #49 unchanged.

## The finding (canons 917e627, classify: TOOL + CORROBORATE + a SELF-CATCH)
- Fleet canary FNV-1a 64 over **UTF-8 bytes**; `saddle/src/hash.ts:26` and
  `jev-garden/src/canon.mjs:21` mask per code unit (`charCodeAt(i) & 0xff`).
- The mask is a **collision generator**: any U+0080..U+FFFF char has 255 single-char
  aliases with identical masked bytes. Demonstrated: `本` ↔ `,` same digest under saddle.
  Tamper-evident → tamper-UNDETECTABLE for trivially constructible substitutions.
- Blast radius: saddle field-trial-1 ledger is 506/506 unverifiable by a canonical verifier.
- Why no test caught it: both suites ASCII-only — the happy-path blindness class again.

## Classification vs OUR live assets
- **SELF-CATCH (the valuable part):** our own `tools/proj_lattice.py:62` fnv1a64 iterates
  `ord(ch)` — code-unit variant, the SAME dialect family the scout condemns (ASCII-only
  inputs are accidentally fine, non-ASCII diverge). `tools/canary.py` and
  `tools/hash_dut.py` are correct (UTF-8) — the alphabet pin 0xCA289D4829D9A834 is sound.
- Exposure check: NO booked verdict cites a proj_lattice/genome_digest value (grep over
  RESULTS.md + results/ + proposals/runs/ = zero bookings; tool is doc-referenced only,
  docs/lattice-projections.md). Latent, not live. Still a D-2-class trap waiting for the
  first non-ASCII genome.
- No CONTRADICT: QO2 stack, receipt doctrine (sha256-based, not FNV), QG3+QG6, QG1c,
  W5a/W5b/W5c, DECIDE-1/2 all unthreatened. CI-1's alphabet pin CORROBORATED as exactly
  the instrument that would have caught saddle/jev-garden at commit time.
- STEAL candidate: scout's per-implementation-vs-canonical table method (run all dialect
  variants on the fixture string, diff) — fold into the queue item's gates.

## Spawned queue item
- **AL-1** (CPU ~15m, pre-reg first): fix proj_lattice.py fnv1a64 to UTF-8 bytes
  (`text.encode("utf-8")`); gate G1 = ASCII genomes bit-identical before/after (no silent
  re-addressing of anything already published); G2 = non-ASCII fixture string ("café Δ
  日本語") now yields fleet-canonical 0x24A555471370B18D via proj_lattice's own fnv1a64;
  G3 = dialect table (utf8 / charCodeAt / &0xff) printed and pinned in a test, RED-first
  (old code fails G2 before fix). Update docs/lattice-projections.md digest note.
