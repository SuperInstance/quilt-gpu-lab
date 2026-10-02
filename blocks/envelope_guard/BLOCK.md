# envelope_guard

## WHAT IT DOES

The strict validation core for the pure `z_in -> z_out` cell envelope: a
standalone port of the XP-C Guard layer (`experiments/xp_c_envelope.py`). It
takes a provider's RAW output and a dispatch record, and either returns the
parsed envelope or raises a structured `Refusal` with a stable error code —
never a lenient accept, never an exception escape. Strict JSON parsing rejects
duplicate keys, `NaN`/`Infinity`, and any trailing content; the output schema
requires exactly the five envelope keys with exact types; and the binding
checks make the envelope a *receipt* rather than decoration: `z_in_digest`
must digest the DISPATCHED `z_in`, and `cell_id`/`provider`/`seed` must match
the dispatch. It also carries the input-schema check that refuses malformed
cells before any provider is called. The digest is FNV-1a-64, hand-rolled in
stdlib (no dependencies), rendered as 16 lowercase hex chars.

## INTERFACE

Inputs / outputs / contract:

- **`Dispatch(cell_id: str, z_in: str, provider: str, seed: int = 2718)`** —
  frozen record of what was dispatched; the envelope must bind to all of it.
- **`Cell(cell_id: str, z_in: str)`** — input-side cell; `cell.z_in_digest`
  is the guard digest of `z_in`.
- **`Guard(digest_algo: str = "fnv1a64")`** — construction with any other
  algo fails loud (`ValueError`); there is no lenient mode.
  - `guard.digest(text: str) -> str` (alias `digest_z_in`) — 16 lowercase hex
    chars of FNV-1a-64. `fnv1a64(data) -> int` is exported for known-answer
    tests.
  - `guard.validate_input(cell) -> None` — raises `Refusal`
    (`input.not_a_cell`, `input.bad_cell_id`, `input.empty_z_in`).
  - `guard.validate_output(raw: str, dispatch: Dispatch) -> dict` — returns
    the envelope dict (exactly the 5 keys) on accept; on ANY malformation
    raises **`Refusal(code, detail, raw_digest)`** with
    `as_dict() = {"refused": True, "error", "detail", "raw_digest"}`.
- **Stable refusal codes** (the contract — do not reword):
  - input: `input.not_a_cell`, `input.bad_cell_id`, `input.empty_z_in`
  - output: `output.not_text`, `output.empty`, `output.not_json`,
    `output.not_object`, `output.key_set`, `output.type.cell_id`,
    `output.type.z_in_digest`, `output.type.z_out`, `output.type.provider`,
    `output.type.seed`, `output.empty_z_out`, `output.bad_digest_format`,
    `output.digest_mismatch`, `output.cell_id_mismatch`,
    `output.provider_mismatch`, `output.seed_mismatch`
- **Envelope shape**: `{"cell_id", "z_in_digest", "z_out", "provider",
  "seed"}` — exactly those keys; `cell_id` matches `^[a-z0-9][a-z0-9_\-]{2,40}$`,
  `z_in_digest` matches `^[0-9a-f]{16}$`, `z_out` is a non-empty string,
  `seed` is a JSON int (`bool` rejected explicitly).
- **Adaptations from the XP-C source** (documented honestly): the source
  returned `(ok, env, err)` triples and used `sha256[:16]` digests; this block
  raises/returns via `Refusal`/`envelope` and uses a hand-rolled FNV-1a-64 in
  the same 16-hex shape. The refusal codes, key set, regexes, and check ORDER
  are ported verbatim, so the XP-C refusal receipts apply code-for-code.

**House contracts baked in:** seed 2718 default · single JSON verdict on the
final stdout line · fail loud (structured `Refusal`, no silent swallow) · no
subprocess in this block · no secrets are read, printed, or copied.

## THE RECEIPT

Cite: **RESULTS.md XP-C entry (2026-10-01)** (lines 4221–4348); full entry
`results/xp_c/RESULTS-ENTRY.md`; all numbers in `results/xp_c/xp_c_results.json`;
code `experiments/xp_c_envelope.py` (this block's source).

- **Gate A — malformed-envelope refusal: 20/20 = 1.000**, every refusal
  structured. The 20-case battery is ported label-for-label into this block's
  self-test and re-proven here.
- **Extra strictness 5/5** (markdown fences, JSON embedded in prose, `NaN`,
  bare scalar, whitespace-only) and **input schema 4/4** — also ported into
  the self-test.
- The receipt's own words: "The **Guard layer is the strongest part of the
  build**"; strict parsing is load-bearing (duplicate keys, `NaN`/`Infinity`,
  trailing content refused — no lenient path); the binding checks are "what
  make an envelope a receipt rather than decoration". The 3B local model
  "never faked a digest; it failed by **omission** — exactly the failure mode
  the guard is built for" (`output.key_set`).
- Arms the guard stood behind in the same run: STUB 30/30 well-formed + 3/3
  byte-identical replays; CLOUD (`glm-5.3-flash`) 30/30; LOCAL
  (`qwen2.5:3b`) KILLed at 0.9333 well-formed with determinism FAIL — a
  model/seat failure, not a guard bypass.
- Prompt note: prompt v1 scored 0/5 on a plumbing probe; frozen v2 (shape
  example + seed-is-number) scored 6/6 — recorded in the artifact's
  `prompt_version`/`prompt_notes`, not a post-hoc move.

## COMPOSITION

Downstream consumer: **provider_seam** imports this block (by inserting this
directory into `sys.path`) and calls `guard.validate_output(raw, dispatch)`
plus `guard.validate_input(cell)`; it reuses `Dispatch`, `Cell`, `Refusal`,
and `fnv1a64` over that same contract — raw string in, guard-validated
envelope out. Any future provider arm (cloud, local, or otherwise) validates
through this guard; nothing about the provider changes the refusal contract.
This block itself is standalone: stdlib only (`json`, `re`, `dataclasses`),
no GPU, no subprocess, no network, no secrets.

## SELF-TEST

Command (from the lab root, CPU-only, <10 s):

```
python3 blocks/envelope_guard/block.py
```

Checks booked in the `GUARD {...}` line:

- FNV-1a-64 known-answer vectors (`""`, `"a"`, `"foobar"`) + hex16 shape;
  `Guard("sha256")` fails loud at construction.
- The exact XP-C 20-malformation battery → **20/20 refused**, each with its
  expected stable code (incl. `output.not_json` for the duplicate-key case);
  the 4 block-only output codes (`output.not_text`, `output.type.cell_id`,
  `output.type.z_in_digest`, `output.type.provider`) exercised by their own
  triggers.
- 5/5 strictness cases; 5/5 input refusals (4 XP-C input cases +
  `input.not_a_cell`); a valid envelope accepted; each binding axis
  (digest/cell_id/provider/seed) refusing with its own code when the dispatch
  is wrong; a never-escape fuzz over non-str garbage (bytes, `None`, list,
  dict, float, `object()`) proving malformed anything → structured `Refusal`.

Expected verdict: **PASS**, final stdout line exactly `{"verdict": "PASS"}`,
exit 0.
