# VX-1 — VERDICT→INSTRUMENT INDEX (pre-register; gates frozen before fire)

Spawned by XM-1 (quilt-matrix guard-registry read, commit 0cb7552): their transferable lesson is
that **wholesale-void must be a LOOKUP, not archaeology** — a verdict→instrument index so that a
tainted instrument names every booking resting on it in O(1). FW-1 (9/9 GREEN, tranches 1-3)
produced that mapping as prose; VX-1 compiles it into a machine-readable index with taint queries.

## Scope (fixed)
The 9 FW-1-censused bookings, exactly as censused in proposals/runs/FW1-field-write-census-{tranche1,tranche2,tranche3}.md:
QO10, QO6 (eproc), QC-JEV, D12i, W5b2, QG7, CI-1, VSB-1, QG7b.
Source of truth = the committed FW-1 tranche pre-reg texts + RESULTS.md tranche bookings.
Index lives at `receipts/verdict_index.json` (committed, receipt-manifest-sealed); tool at `tools/verdict_index.py`.

## Index record per booking (fields, verbatim-class from FW-1)
- booking id, RESULTS.md commit, producing artifact(s)
- verdict_reads[]: state fields/values the verdict function reads
- write_sites[]: write paths feeding those fields (internal / external classified)
- coverage[]: committed test pins + repro runs covering those write paths
- fw1_status: GREEN|RED|YELLOW (all 9 are GREEN|YELLOW-with-caveat per tranches; recorded as booked)

## Frozen gates (evaluated by tools/verdict_index.py selftest + one CLI query arm)
- G1 COMPLETENESS: index contains exactly the 9 bookings above; every fw1_status matches the
  booked FW-1 tranche verdict (8 GREEN + W5b2 GREEN-with-caveat recorded with its caveat note).
- G2 ROUND-TRIP: for each booking, taint-query(booking.any verdict-feeding write site/field)
  returns that booking id (and only bookings that genuinely share the instrument, per index).
- G3 NEGATIVE CONTROL: taint on a deliberately unrelated field ("vx1_negative_control_field")
  returns the empty set; mutating a copy of the index (one coverage entry removed) flips G2 RED.
- G4 COST: CPU-only, <5 s, no GPU, no network; index sealed in manifest after booking.

## Claim under test
A taint query over the index reproduces FW-1's verdict sets exactly: querying any field of the
FW-1 lesson classes (e.g. "positional name→oid map" → VSB-1; "E trajectory" → QO6) returns the
booking(s) FW-1 says rest on it, and nothing else. PASS => verdict→instrument lookup exists;
future wholesale-void is one query. FAIL => index/spec divergence, book honestly, no re-roll.
