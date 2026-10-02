# seal-red analysis — import-baseline drift at HEAD 37c0608

Lane: GRADER-BLINDSPOT (r11 follow-up). Read-only against
`SuperInstance/MicroMoth-quilt`; analysis done in the scratch clone
`scratch/grader_blindspots/repo`. No upstream writes.

## Symptom

`tests/test_import_baseline.py::BaselineSealed::test_manifest_exists_and_matches`
is RED at HEAD. The manifest declares **487 sealed** files; git tracks
**497** (498 including the manifest itself, which is excluded from its own
map by construction). The drift-catcher drifted silently: nobody ran the
pin, so nothing tripped.

## The manifest

- Path: `receipts/import-baseline.json`
- Schema: `micromoth-quilt/import-baseline@v1`
- `generated_at`: `2026-09-30T03:23:25.146751+00:00`
- `baseline_commit`: `5106a14e04b04d73bb1239362b7f2671ad71a8b1`
  ("exp021 receipt: r31 tie-context autopsy", 2026-09-30 03:09 UTC)
- Doctrine in-file: *"regenerate via tools/import_manifest.py; never edit by
  hand"*.
- Re-derivation: `tools/import_manifest.py` hashes every `git ls-files`
  entry except `receipts/import-baseline.json` (sha256 fixed-point, cannot
  embed its own digest).

## Exact drift (HEAD = 37c0608, "overnight sync … auto-push 20261001T153342Z")

Method: `git archive HEAD` → hash every tracked blobs vs the manifest map.

- **10 tracked-but-unsealed files** (in git, absent from the manifest):
  1. `receipts/exp022-desert-break.json`
  2. `receipts/exp022-desert-break/exp022.results.json`
  3. `receipts/exp022-desert-break/exp022.telemetry.k3.jsonl`
  4. `receipts/exp022-desert-break/exp022.telemetry.k4.jsonl`
  5. `receipts/exp022-desert-break/exp022.telemetry.k5.jsonl`
  6. `receipts/exp022-desert-break/exp022.telemetry.k6.jsonl`
  7. `receipts/exp022-desert-break/exp022.telemetry.k7.jsonl`
  8. `receipts/exp022-desert-break/exp022_crossing_stream_census.py`
  9. `tests/test_exp022_receipt.py`
  10. `tests/test_lab_home_citation.py`
- **1 sealed file with drifted digest** (content changed post-seal):
  `AUDIT.md` (the qcells-lab-home provenance edit).
- 0 sealed-but-deleted files.
- 487 + 10 = 497 tracked non-self files; + manifest = 498. Checks out.

## Which commits added them (post-seal)

Manifest sealed at 03:23 UTC 2026-09-30. Introducers, all AFTER:

| commit | date (UTC) | adds |
|---|---|---|
| `2c03e1f` exp022 receipt (PR #28) | 2026-09-30 04:41 | the 8 `exp022` files (incl. `tests/test_exp022_receipt.py`) |
| `8bdae01` qcells lab home (PR #29) | 2026-09-30 08:01 | `tests/test_lab_home_citation.py` + `AUDIT.md` digest change |
| `950a6fe` merge PR #29 | 2026-09-30 09:27 | merge |
| `37c0608` overnight auto-push | 2026-10-01 15:33 | re-touched the whole tree (0-content-diff sweep) |

Note `2c03e1f`'s own manifest blob is *already* the 487-file one — PR #28
merged with the manifest untouched; PR #29 likewise. So the drift is not
from the overnight commit alone: the overnight auto-push is the loudest
event, but the seal was already stale by PR #28.

## Root cause (why it drifted silently — four compounding holes)

1. **The pin is passive.** `test_import_baseline.py` only trips when
   somebody runs `pytest`. It cannot trip by itself.
2. **CI never runs the battery.** `.github/workflows/build.yml` triggers
   only on `workflow_dispatch` / `release: published` and its one gate is
   the **C#/dotnet** smoke test. No Python job, so `test_import_baseline`
   is never consulted on PRs or pushes.
3. **The auto-push writer bypasses the seal contract.** The overnight
   commit is authored by `SuperInstance-agent <agent@superinstance.local>`
   and commits local artifacts without ever invoking
   `tools/import_manifest.py`. A writer that doesn't re-seal is, by
   definition, a drift generator.
4. **Re-seal is manual.** The doctrine says "regenerate WITH the change";
   PRs #28/#29 shipped file adds with no manifest regen, and nothing
   enforced the pairing.

Net: the "drift-catcher" is a latent pin with no enforcement path — silent
by design once a non-resealing writer reaches `main`.

## Re-seal procedure (PR-ready, do NOT run upstream)

Command (single step, deterministic):

```bash
cd <repo>
python3 tools/import_manifest.py
# prints: sealed: 497 tracked files @ <HEAD12>…
```

Then verify + commit:

```bash
python3 -m pytest tests/test_import_baseline.py -q          # must be GREEN
git add receipts/import-baseline.json
git commit -m "manifest regen: re-seal after exp022 (#28) + lab-home citation (#29) (487 -> 497 tracked files)"
```

Details / pins:

- **Which manifest version:** schema stays `micromoth-quilt/import-baseline@v1`.
  No schema change — same fields, more entries. Only `generated_at` and
  `baseline_commit` advance (to the re-seal commit's HEAD). Do **not**
  hand-edit; the tool is the only writer.
- **Expected count:** 497 (498 tracked − the self-excluded manifest).
- **Fixed-point note:** the manifest can never contain its own digest; the
  `self` field records the exclusion. Don't "fix" that.
- **Pairing rule:** regenerate in the *same* change-set as whatever moved
  the tree; if you regenerate after committing the code change, the
  `baseline_commit` should name the commit whose tree you sealed (the tool
  reads live `HEAD`, so seal at the tree you mean).
- **Prevention (the real fix):** add a cheap guard so a non-resealing
  writer can't reach `main` silently — e.g. a pre-push git hook or a
  minimal CI job running `python3 -m pytest tests/test_import_baseline.py -q`
  (stdlib-only, <1s). The auto-push agent should run the re-seal tool
  before committing local artifacts.
- **Interaction with exp015:** the re-seal also retires the one
  pre-existing RED the self-play instrument excluded from its catch deltas
  (`test_import_baseline` drift). After re-seal the instrument's baseline
  becomes fully green; the honest-negative note in `tools/selfplay.py`
  about "pre-existing manifest drift" should be updated in the same
  change-set (baseline failure set → empty).

## Status

Analysis complete and reproducible from the scratch clone. **No upstream
commit, no push, no branch, no deletion** — per the SuperInstance red lines.
