# RC-5 — PUSH-TIME SEAL-PIN `--check` (narrowed scope, pre-registered 2026-10-02 06:1x UTC)

## Provenance
Spawned by SCOUT-17 (MicroMoth #32: their RED-at-HEAD seal came from an auto-push
that never re-seals after landing). NARROWED 19:2x: seal-time dirty refusal is
ALREADY LANDED upstream (`dirty_sealed_paths()` in tools/receipt_manifest.py +
4 FAIL-first refusal pins in tests/test_seal_guard.py, commits b2d24bb/585c893).
This run adds ONLY the push-time layer. Do NOT re-implement seal-time refusal.

## Claim under test
A `--check` mode that compares the sealed digests in receipts/manifest.json
against the live tree catches any post-seal drift to sealed paths, exit 0 on
clean / exit 2 on drift — making an un-resealed auto-push RED AT PUSH instead
of RED-ON-NEXT-CLONE.

## Frozen design
1. `check() -> list[str]` in tools/receipt_manifest.py: recompute ledgers +
   experiments + tools digests, diff vs receipts/manifest.json. Drift lines
   name the path and expected-vs-actual. Missing manifest => drift. No write,
   no --allow-dirty interaction (check is read-only).
2. `--check` CLI flag: print drift lines, exit 2 if any, exit 0 if clean;
   never writes manifest.json.
3. Test pin (tests/test_receipts.py, new class): (a) clean tree => check()
   returns no drift against the CURRENT committed manifest (green); (b) a
   tampered in-memory manifest copy (one flipped digest) => drift names the
   tampered path (FAIL-first: red against the pre-feature module).
4. Opt-in hook TEMPLATE at tools/hooks/pre-push (chmod +x): runs
   `python tools/receipt_manifest.py --check`, exits non-zero on drift,
   header comment instructs `cp` into .git/hooks (never auto-installed).

## Gates (words, frozen)
- G1: on the clean committed tree at fire time, `--check` exits 0.
- G2: one-byte tamper of RESULTS.md after seal => `--check` exits 2 and the
  drift line names RESULTS.md (demonstrated on a scratch copy, tree restored).
- G3: full unittest suite green (no regression to existing pins).
- G4: hook template executable-syntax-valid (bash -n).

## Cost
CPU only, ~20 min wall, 0 GPU-Wh, no guard window, no new banks.
