# MANIFEST — qg1d fleet-triage source snapshots (read-only recon)

Fetched 2026-10-01 by lane QG1d. Method: `gh api repos/SuperInstance/fleet-triage/contents/<path> --jq .content | base64 -d`.
**No clone, no push, no writes to fleet-triage.** Original repo paths are preserved under
`src-snapshots/root/`, `src-snapshots/experiments/`, `src-snapshots/sim/`, `src-snapshots/lineage/`.
Snapshot = the tree at `fleet-triage` default branch as of fetch time; sha256 (first 16) recorded.

| original path | local path | sha256[:16] |
|---|---|---|
| resolver.py | root/resolver.py | 231a94a0c08c3f60 |
| resolver_selftest.py | root/resolver_selftest.py | bc52be6f765c21fb |
| test_resolver.py | root/test_resolver.py | 7bea28ca0fea9362 |
| lanes.py | root/lanes.py | 774285debfbe4541 |
| triage.py | root/triage.py | 6b29b44c16dfe81d |
| BOARD.md | root/BOARD.md | 611eaaf1154aebb1 |
| CORRECTION-PROJECTION.md | root/CORRECTION-PROJECTION.md | 8dc6db8be8bf56e5 |
| D1-INVENTORY.md | root/D1-INVENTORY.md | 917c32f07000a536 |
| RESOLVER-DEFECT.md | root/RESOLVER-DEFECT.md | 723113f0235f03e9 |
| RESOLVER-FINAL.md | root/RESOLVER-FINAL.md | 496ecf0e05a0a6c3 |
| sprint-RESOLVER.md | root/sprint-RESOLVER.md | 7c759c5a69963063 |
| d1_inventory.json | root/d1_inventory.json | 28baf6195b7f2b54 |
| experiments/positive_control.py | experiments/positive_control.py | 0fc6146f63bb796e |
| experiments/projection_doctrine.py | experiments/projection_doctrine.py | bf760dec284d6e7f |
| experiments/synergy.py | experiments/synergy.py | 38f86af474ee138f |
| experiments/synergy_results.json | experiments/synergy_results.json | a74a37fd6d2e4cef |
| experiments/RESULTS.log | experiments/RESULTS.log | 64babfa91c72544b |
| experiments/CONTROL.log | experiments/CONTROL.log | 125994151eeec992 |
| sim/tileset_sim.py | sim/tileset_sim.py | ad092d18f2519ea8 |
| sim/collapse_sim.py | sim/collapse_sim.py | d6bdb174db336f2a |
| sim/RESULTS.md | sim/RESULTS.md | 50dfcc0cbe93eafb |
| lineage/loop_test.mjs | lineage/loop_test.mjs | 130d3d2ca33d40c3 |

## Directory listing at fetch (context)

- repo root: `resolver.py` (79,920 B, 1,815 lines), `lanes.py`, `triage.py`, `resolver_selftest.py`, `test_resolver.py`, `fleetlint_failopen.py`, plus the BOARD/CORRECTION/RESOLVER/D1/SPRINT doc set.
- `experiments/`: `positive_control.py` (8,580 B), `projection_doctrine.py` (14,516 B), `synergy.py` (9,081 B), `synergy_results.json`, `RESULTS.log`, `CONTROL.log`.
- `sim/`: `tileset_sim.py` (11,171 B), `collapse_sim.py` (2,724 B), `RESULTS.md`.
- `tools/lanes.py` (12,245 B) is byte-identical in size to `root/lanes.py` (same file, two locations).
- `lineage/loop_test.mjs` == `lineage/syzygy-lattice-loop-test.mjs` (both 1,302 B).

## Note on the recon premise

The task brief expected "a resolver with swap/repair logic" inside `experiments/`.
What is actually there: `experiments/` holds the **projection-doctrine** (degeneracy)
and **synergy** (n_eff / instrument-transfer) work. The citation `resolver.py` with the
repair ladder lives at **repo root**, and the lane/assignment machinery (`lanes.py`) at
root + `tools/`. The swap/assignment/repair mechanisms are therefore reported from root,
not experiments/ — see RESULTS-ENTRY.md §2.
