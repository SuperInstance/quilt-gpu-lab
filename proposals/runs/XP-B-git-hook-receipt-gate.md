# XP-B — git-hook receipt gate (pre-registered)

Spawned by scout §2c (pre-reg seed). Feeds SIG-1 acceptance evidence. CPU-only, digest-only, NO keys.
Runner: `tools/xpb_receipt_hook.py` (selftest mode builds a throwaway git repo in ext4 scratch, never
touches this repo's .git or index).

## Target
A pre-commit gate that refuses every pre-registered receipt-corruption class on `results/g7/`
artifacts (guard.py emit_receipt: `receipt_id.json` + `ledger.jsonl`), with ZERO false rejects on
clean staged changes. Digest-only (sha256 + git HEAD comparison); no HMAC, no secrets, no network.

## Frozen corruption classes (each must exit non-zero and NAME the class)
- **C1 receipt-reuse**: same `receipt_id` appearing twice in the staged ledger with divergent
  file content (or a ledger line re-adding an id already at HEAD).
- **C2 chain-repair**: any byte modification of a receipt file already tracked at HEAD
  (append-only convention enforced by HEAD-vs-staged sha256 compare).
- **C3 truncated-receipt**: staged new receipt that is invalid JSON or missing required fields
  (`schema`, `receipt_id`, `determinism.state_digest`, `gate.verdict`).
- **C4 digest-substitution (FNV-1a-64 collision-pin class)**: any ledger line or receipt carrying
  a digest that is NOT 64-hex sha256 (e.g. a 16-hex fnv-64 pin) — refuse by format, digest-only.
- **C5 GPU-cell seed mutation**: staged change to `determinism.seed` or `determinism.state_digest`
  inside a receipt vs HEAD (named subclass of C2; evidence-quality check).

## Frozen clean classes (each must exit 0 — zero false rejects)
- **P1 valid-append**: a new well-formed receipt file + one matching ledger append line.
- **P2 unrelated**: staged changes to files outside `results/g7/` pass untouched.

## Gates (red-first)
- **G1 REFUSE-LOUD**: every class C1–C5 → exit non-zero with the class name in stderr. PASS iff 5/5.
- **G2 CLEAN-PASS**: P1 and P2 → exit 0. PASS iff 2/2 (zero false rejects).
- **G3 NO-KEYS**: the hook script contains no secret reads (grep-audit: no env secret fetches beyond
  none; sha256 only). PASS iff audit clean.
- **G4 IDEMPOTENT-REENTRY**: re-running the selftest gives identical exit matrix. PASS iff 2 identical runs.

## Interpretation
Any RED on clean classes = KILL (false rejects are worse than no gate). Any GREEN on a corruption
class = the gate is VOID and must be fixed before any adoption claim. Adoption as an actual
`.git/hooks` install is a protocol change → Casey day item (same lane as SIG-1/LC-1 adoption).

## Honesty pre-commitments
No re-roll; exit matrix booked as measured; scratch repo under /home/eileen/scratch (ext4, not tmpfs);
no writes into results/.
