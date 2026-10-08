# HSA-1b — Population refresh policy for the hash-selected audit rota (pre-register)

Spawned: SLICE 01:2x Oct 8 (day-conductor), from HSA-1 member-check #2 — the frozen 101-receipt
population is drifting from the live RESULTS.md citation census (~320 cited path-strings, 102
unique `proposals/runs/*.md` receipts at this writing). Frozen-epoch population means every
receipt booked after HSA-1's freeze can NEVER be audited by the rota, and member selection is
computed over a stale set. This is a coverage decay bug in a standing instrument.

## Question
What population should the hash-selected rota use going forward — the frozen HSA-1 manifest, an
amended frozen manifest, or a re-censused rolling population — and can the choice be made
mechanically so that selection stays attention-free and reproducible?

## Decision (frozen BEFORE any member #2 verdict is booked)
Adopt **versioned rolling epochs**:

1. **Census rule (unchanged from HSA-1)**: population = sorted-unique set of
   `proposals/runs/<name>.md` paths regex-extracted from `RESULTS.md` at census time.
2. **Epoch identity**: `epoch_id = sha256(utf8("\n".join(sorted_paths) + "\n")).hexdigest()[:16]`.
   The population for each epoch is snapshotted to `results/hsa1_rota/population-<epoch_id>.txt`
   (append-only; a snapshot is never edited). The original `results/hsa1_rota/population.txt`
   is retained untouched as epoch `hsa1-freeze` (101 lines) for provenance.
3. **Selection rule (unchanged)**: receipt joins the rota iff last byte of
   `sha256(utf8(receipt_path))` == 0x2A. Fallback unchanged (lexicographically-smallest digest
   receipt if zero hits).
4. **Refresh cadence**: a new epoch is snapshotted when (a) the census adds >=1 previously-absent
   receipt AND (b) a (B)-slot audit wake is running; the snapshot + selection output are committed
   in the SAME commit as the pre-reg that consumes them, BEFORE that wake's member verdict lands.
5. **Rota semantics**: append-only `rota.jsonl`. Member identity = (epoch_id, receipt). A receipt
   already audited in a prior epoch is NOT re-audited merely because the epoch id changed; the rota
   advances to the first member in the current epoch not yet present in any prior entry.
6. **Suppression check**: unchanged — any selected receipt whose cited instrument changed since its
   booking commit is booked as a finding, never filtered.

## Gates (pre-registered in words)
- G1 (census): refreshed census is sorted-unique; snapshot file committed with this pre-reg; line
  count and epoch_id recorded in the rota ledger.
- G2 (bit-stability): selection recomputed from the committed snapshot is bit-identical across two
  independent invocations and equals the selection recorded in this pre-reg.
- G3 (no-regression): epoch refresh must not silently change membership of the prior epoch's
  members beyond additions; specifically RC-5 remains selected (its digest is path-only, epoch-
  independent).
- G4 (cost cap 15 min CPU; GPU member => book DEFERRED, not FAIL): run the first not-yet-audited
  member of the current epoch; if none exists (all current members already audited), book
  NO-NEW-MEMBER with the membership proof and stop.

## Claim under test
The rota's population can be refreshed mechanically without attention bias creeping in: the epoch
is a pure function of the committed census, selection stays stable under the frozen hash rule, and
coverage no longer decays with new bookings. PASS => rolling-epoch refresh adopted; HSA-1 prereg's
Population clause is superseded by this document. FAIL => book honestly; revert to frozen manifest.

## Cost
~15 min CPU, no GPU, no network.
