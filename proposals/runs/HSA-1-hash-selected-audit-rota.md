# HSA-1 — Hash-selected standing audit rota over booked results (pre-register)

Spawned: SCOUT-69 slice (jev-ideation four-briefs, brief 4 "hash-selected audits"), day-conductor (B) slot, 2026-10-07 20:2x AKDT.

## Failure class in our instrument
Audit-by-judgment is corruptible by attention bias: the bookings we re-verify are the ones we
happen to be looking at, and a booking whose instrument later drifted silently escapes the
rota forever. Brief 4's fix: selection must be a function of the artifact, not of attention.

## Design (frozen before any re-run)
1. **Population**: every receipt path cited in RESULTS.md via `proposals/runs/<name>.md`
   (regex-extracted, sorted, deduped) — 101 receipts at freeze time. Population list is
   committed WITH this prereg as `results/hsa1_rota/population.txt` (sorted, one per line)
   BEFORE any selection is computed or any repro fired.
2. **Selection**: `sha256(utf8(receipt_path))` hex digest; a receipt joins the rota iff the
   LAST byte of the digest == 0x2A. (8-bit prefix, fixed constant 0x2A chosen arbitrarily
   NOW and frozen; ~0.4 expected hits on 101 — sparsity is acceptable, the rota is standing.)
3. **Fallback**: if the prefix selects ZERO receipts, the deterministic fallback is the
   single lexicographically-smallest digest receipt in the population. Fallback membership
   is a function of the population only — still fixed before any re-run. Zero-selection with
   no fallback is INDETERMINATE for this wake.
4. **Rota semantics**: append-only. Each wake that runs (B)-slot audit work re-runs the
   FIRST not-yet-reverified member's committed instrument from the committed tree and appends
   the outcome to `results/hsa1_rota/rota.jsonl` (receipt, commit, verdict, timestamp).
   Never removes or edits prior entries.
5. **Suppression check (gate b)**: at freeze, diff each selected receipt's cited instrument
   path(s) against `git log --follow` SINCE the booking commit. Expect zero instruments
   changed post-booking; any hit is reported, not suppressed.

## Gates
- G1: population file exists, sorted, 101 lines, committed before selection output.
- G2: selected subset == recompute from committed population + frozen rule (bit-stable
  across two independent invocations in the same commit).
- G3 (suppression): zero selected bookings have a post-booking instrument change; any hit
  booked as a finding, not filtered.
- G4: this wake re-runs at most ONE rota member's instrument (the first member); cost cap
  15 min CPU; if a member's instrument is GPU or > cap, book DEFERRED (not FAIL) and stop.

## Claim under test
Our booked results can support a mechanical, attention-free audit rota: hash selection is
stable, the subset was not unconsciously curated, and no selected booking's instrument has
silently drifted since booking. PASS => standing rota adopted, one member per (B)-slot wake.
FAIL (any gate) => book honestly; suppression hits feed FW-1-successor rows.
