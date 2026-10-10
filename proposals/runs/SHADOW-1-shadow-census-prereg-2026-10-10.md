# SHADOW-1 pre-registration — last-definition-wins shadow census
Spawned by SCOUT-91 (fe5948a higher-abstraction-vocabularies double-method shadowing witness).
Committed BEFORE firing. Date: 2026-10-10 19:2x UTC.

## Instrument
`tools/shadow_census.py` — AST walk over every tracked `experiments/*.py` and `tools/*.py`:
1. Module-scope names defined ≥2× in one file (def/class/assign) → each later definition is a
   shadow; record line numbers and which definition is live.
2. Module-scope names rebound by a later module-level `import X as <existing-name>`.

## Gates (frozen words, pre-registered)
- **G1 (coverage):** census traverses every tracked .py under experiments/ and tools/ and
  reports a per-file count; zero files silently skipped (parse errors are RED-flagged, not
  skipped).
- **G2 (shadow set):** enumerate all live shadows. For each: name, file, killed-line, live-line,
  and whether any BOOKED verdict's producing script cites the live binding.
- **G3 (verdict impact):** a shadow feeding a booked verdict's producing tool = RED, owning
  booking named. Shadows in non-verdict paths may be booked benign WITH the named non-verdict
  role; unclassifiable = YELLOW, listed.
- **G4 (determinism):** re-run produces identical output (pure static analysis, no GPU).

## Verdict rule
RED only on G3 live-verdict shadow. GREEN = zero shadows or all benign-with-named-role.
YELLOWs get follow-up items, not silent pass.
