# SCOUT-14 — fleet push sweep, 2026-10-01 15:11Z (day-conductor, non-GPU per rotation)

Method: `/users/SuperInstance/events` PushEvents (48h window), then per-repo commit/PR reads for
everything that moved after the SCOUT-13 sweep (~13:1xZ). Read-only; no comments/PRs filed.
Repos examined: taps-creative-break, jev-quilt, quilt-mojo-lab, reverse-actualization, quilt-arcade,
slackwater-lattice, Projectionist, quilt-gpu-lab (own), + open-PR scan across 8 repos.

## Findings (classified against live assets)

### TOOL — quilt-gpu-lab PR #6 (OPEN, author SuperInstance, 2026-09-30T15:24Z): seal-guard usability fix + refusal pins
Follow-up to the d23b phantom-seal repair (b2d24bb): the `--require-clean` guard currently refuses
seals after ANY test run because tracked `tools/__pycache__/*.pyc` regenerates on import —
"a guard that refuses over its own cache is unusable." PR adds `__pycache__` to the dirty-path
ignore, plus `tests/test_seal_guard.py` (4 pins: guard-live, dirty-path named, exit-2 REFUSED +
manifest untouched, `--allow-dirty` explicit `sealed_from_dirty_tree` admission), FAIL-first by
mutation (4/4). Manifest resealed on branch; main untouched; **Casey-gated**.
- Classifies TOOL against our receipt doctrine. It is exactly the missing half of RC-3: our
  10:1x note recorded "`--require-clean` already satisfied by existing behavior" — true, but the
  PR documents a live usability hole (we never noticed because our slices didn't run tests between
  dirty-check and seal; the moment the mandatory (C) repro runs tests then seals, the guard will
  false-refuse). The tracked-.pyc detail is verifiable from the diff; manifest digest change on
  branch is `receipt_manifest.py` 6b3c8c5d → c71be759.
- Action: do NOT merge (Casey's call). Spawned **RG-6** (verify PR #6's claim on a scratch clone:
  reproduce the false-refuse on main, confirm the branch fixes it, report verdict to the spool for
  Casey's gate). Cheap CPU ~15m.

### CORROBORATE — jev-quilt 41st-44th wipes (through 15:06Z): JEV oracle STABLE, 0 drift
Hourly probes r001-r060: 7/7-9/9 bedrock-strength, mean_p 0.5996-0.6203, "0 drift, 7th
consecutive session." Their oracle is the JEV `/v1/systemone` endpoint via a 14-probe battery
(5 voice / 5 doctrine / 4 misquote / substance / alignment), verdict ACCEPT/REVIEW/DISCUSS/REJECT.
- Relationship to the murmuration null (SCOUT-4) and our QC-JEV KEEP: a THIRD witness showing a
  JEV-family oracle reading stably and discriminatively (bedrock vs mean_p separation) — against
  murmuration's single-artifact jev-1.13.0 null. Corroborates our QC-JEV booking; further narrows
  the murmuration finding to artifact-version-specific.
- STEAL (secondary): their drift-across-wipes protocol = QC-JEV2's missing design. Their
  ambiguous/misquote probe classes (catch inversions, catch typos like "15 ports") are ready-made
  probes for pinning WHERE jeff-0.8b's unclear band sits — better than the single "2+2≈4" control
  QC-JEV2 sketched. Amended QC-JEV2 spec (below).

### TOOL/STEAL — quilt-mojo-lab wave-73 (14:26Z): CuPy GPU substrate KEEP + **WSL2 GPU burst-timing law**
Bit-parity 0.0, 3.10G cells/s @1024²; banked law: **on WSL2/RTX-4050, idle ≥10s → GPU bursts
2-10× slow; sustained ~0.6s load ramps.** This is OUR BOX (RTX 4050, WSL2). Direct consequence for
our lab: any of our wall-clock/latency gates (G3-style "54 ms" anchors, VRAM preflight-adjacent
timing) measured after an idle gap will read slow by up to 10× — timing gates need a warmup commit
or they will flake. Spawned **TW-1** (audit our runners for cold-GPU timing gates; add warmup
commits where timing is gated; docs note). CPU+light GPU ~30m.

### (minor, no action) — taps-creative-break: hourly creative round commits ("3/3 voices OK,
cells are the bruises of the substrate") — prose/lore lane, no measurement content, not our assets.
reverse-actualization wave-79: "iterative re-anchoring FAILS honestly — same-model loop keeps its
attractor; lexical and semantic channels independent" — honest-FAIL doctrine corroborated; no
action. quilt-arcade: judge-result refresh (games lane). slackwater-lattice wave-74d: pinned a
published PyPI defect with an exhaustive property suite — same vendor-defect-pinning doctrine we
already carry. Projectionist pushes: housekeeping.

## Spawns (concrete)
- **RG-6** (CPU ~15m): clone PR #6 to scratch, reproduce the `.pyc` false-refuse on main, verify
  the branch's 4 pins + fix, book a verdict for Casey's merge gate. Gate: verdict is INVALID if the
  false-refuse cannot be reproduced on main (then the fix is speculative and pins-only).
- **TW-1** (CPU+light GPU ~30m): sweep experiments/*.py for timing gates (wall-clock asserts,
  ms anchors); add GPU warmup commits before any gated timing; note the WSL2 idle-burst law in
  tools/README. Improves: all future G3-style gates.
- **QC-JEV2 spec amendment**: adopt jev-quilt's misquote/ambiguity probe classes (4 inversion
  probes + typo probe) instead of the single "2+2≈4" control; add a drift-across-wipes read if a
  second jeff checkpoint exists locally.

## Rotation next wake
RG-6 (CPU, serves Casey's gate) or FT-1 (pie-minimax DT ceiling, still open); GPU lane free —
QG1d recon follow-up or QG4 phase diagram.
