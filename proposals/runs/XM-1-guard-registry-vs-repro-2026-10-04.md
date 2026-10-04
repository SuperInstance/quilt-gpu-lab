# XM-1 — quilt-matrix cross-run guard registry vs our per-booking repro doctrine

Date: 2026-10-04 ~0511Z (conductor slice, day cron). Read-only recon; no GPU fired.
Source: SuperInstance/quilt-matrix commit 0cb7552 (night3 + THE GUARD BUGFIX), engine/guards.py, runs/guard_registry.jsonl. Spawned by SCOUT-41.

## What they built

`GuardRegistry`: append-only, hash-chained ledger (prev_hash chain, sha256 over sorted-key body) of guarded nodes across ALL runs. Per-run guards.csv is "muscle memory"; the registry is "the spine" — a guard minted in any run protects that node in every run. Sync-in at bootstrap (`sync_from_run`, dedup by node, first mint wins), append at mint time, consulted by every gate, `chain_ok()` verifies the chain.

The event that motivated it: `build_pool` dropped criteria → every GUARD oracle call 422'd since night1 → **all guard verdicts night1–3 were VOID and wholesale-revoked via the registry** (one data structure named every affected verdict instantly).

## Comparison with our stack

| dimension | quilt-matrix registry | our doctrine |
|---|---|---|
| enumerate affected verdicts after instrument bug | O(1) — the registry IS the index | manual walk of RESULTS.md + spool (FW-1 did this by hand, 9 verdicts) |
| tamper resistance | hash chain (chain_ok) | receipt-manifest seals (digests, not chained) |
| retraction | wholesale-void event, 0cb7552 | QO6 e-process retraction gate (per-stream, runtime) |
| bug detection | fail-loud 422 caught by census | mandatory (C) repro + FW-1 field-write census (found our radians class) |

Assessment: their registry's real lesson is not the hash chain (we have seals); it is **the verdict→instrument index**. When an instrument breaks, "which booked results does this taint?" must be a lookup, not an archaeology project. Our FW-1 tranche sweep was exactly that lookup done by hand — it exists nowhere as data.

## Spawned item

**VX-1** (CPU ~30m, docs+tool, pre-reg first): build `tools/verdict_index.py` — machine-readable mapping booking → producing script(s) + instrument files + pin commits, extracted from the 9 FW-1-censused bookings. Gate: for each of the 9, the index names the same verdict set FW-1 found (GREEN), and a synthetic instrument-taint query returns exactly the bookings citing that instrument. This is our registry equivalent; wholesale-void becomes `verdict_index --taint <tool>`.

## Threat check

No CONTRADICT against our live assets from this read: their bug was oracle-call plumbing, not a result that conflicts with QO2/QG-laws. The wholesale-void DISCIPLINE corroborates DEL-1's finding that retraction is load-bearing. KR-1 credential-drift analogy holds: credentials, seals, and guard registries all need the same property — revocation must name its blast radius.
