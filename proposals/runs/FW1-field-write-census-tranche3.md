# FW-1 FIELD-WRITE CENSUS — tranche 3 (CI-1, VSB-1, QG7b)

Pre-registered BEFORE the audit ran. Same census rule as tranche 1
(proposals/runs/FW1-field-write-census-tranche1.md). Spawned-by lineage: SCOUT-24 → FW-1;
tranches 1-2 booked 2026-10-02 (6/6 GREEN). This tranche covers the three bookings landed
since (Oct 3): CI-1, VSB-1, QG7b. Uncovered verdict-feeding write path => RED.

## Scope

### CI-1 — fail-closed pytest workflow + fleet canary (booked 01:3x Oct 3, commit 69faafc)
- Producing artifacts: .github/workflows/tests.yml, tools/canary.py, tests/test_canary.py.
- Verdict reads: control_ladder() rungs (expect_red/observed_red), ladder_verdict() ok,
  alphabet_canary(CANON_GATES) == ALPHABET_CANARY, workflow exit code on empty-glob collect.
- Write sites: ladder is IN-MEMORY (writes nothing — declared in-code, pre-reg gate G2).
  External state read: workflow file + gate names in tools/qcell_sim.py. No mutable state
  feeds the verdict.
- Coverage: tests/test_canary.py pins byte canary, L9(d) canonical text, unaccented twin,
  alphabet pin + rename. Negative control verified in booking (our gate FAILS at the
  empty-glob corner — SCOUT-37 corroborated). Actions run 37112598464 green.
- Anticipated: GREEN.

### VSB-1 — tools/vendor_strip_census.py ls-tree vs batch-check (booked 07:2x Oct 3)
- Verdict reads: G1 two-method agreement flag, per-path byte sizes from BOTH methods,
  vendor classification (is_vendor on path strings), raw/real/vendored totals.
- Write sites: census_ls_tree + census_cat_file internal parsing; the batch-check loop
  writes the positional name→oid map (the booked RESOLVED-oid lesson — verdict READS this
  map, so map-construction is verdict-feeding). results.json write is output-only.
- Coverage: tests/test_vendor_strip_census.py (committed); booking itself was a full run
  over 3539 files with EXACT agreement. Nested-vendor strip bug was caught BY the census
  (evidence the detector branch fires).
- Anticipated: GREEN.

### QG7b — tools/ensemble_corr_census.py (booked 11:1x, repro PASS 12:2x)
- Verdict reads: pairwise Spearman matrix over per-run frozen-oracle score vectors
  (intersection-aligned mask), spearman_mean, band gates hi=0.9 / lo=0.5, selftest anchors.
- Write sites: _avg_ranks/_pearson/spearman internal, all deterministic (stdlib, no RNG);
  runs loaded from JSON on disk (read-only input); --out write is receipt-only.
- Coverage: selftest() (nomask-high, anti branches) + committed verdict-level repro
  (results/qg7b_rerun_correlation/repro-20261003-1215/). Both verdict-gating band branches
  exercised (INTERMEDIATE booked; DRAWS/REFUTED branches pinned by selftest).
- Anticipated: GREEN.

## Execution plan (~15 min, CPU only, no GPU)
1. Run the committed selftests/tests for all three tools (scratch output, no tree dirtying).
2. Grep-verify no other write site touches the verdict-feeding fields (quick manual pass).
3. Book in RESULTS.md + spool; commit+push. Manifest re-seal only if ledger change requires
   (deferred per standing foreign-live-lane note otherwise).
