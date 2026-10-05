# EP-1b — seal/event-prose census v2 (pre-registered BEFORE fire)

Spawned by EP-1 booking (17:2x Oct 4, SCOUT-42 lineage). Parent pre-reg:
`proposals/runs/EP-1-seal-prose-census-prereg.md`.

## Tool
`tools/ep1b_seal_census.py` (new file; EP-1's `tools/ep1_seal_census.py` stays frozen as-fired).

## Scope
Same corpus as EP-1: `RESULTS.md` + `receipts/*.md` digest claims (64-hex) and
seal/event-prose lines; `receipts/manifest.json` as seal reference.

## Resolution order (each claim, first match wins → resolved)
1. **Manifest arm**: token appears in `receipts/manifest.json`.
2. **Git-object arm**: `git cat-file -t <sha>` succeeds.
3. **Recursive artifact arm** (EP-1 gap fix): sha256 over EVERY file under
   `results/**`, `tools/**`, `experiments/**`, `receipts/**` (rglob, files only;
   skip `__pycache__`, `.pyc`; size cap 64 MiB/file, capped counts reported).
4. **Historical-blob arm** (new): for claims whose citing line names a tracked
   path, hash the blob of that path at every commit from
   `git log --all --format=%H -- <path>` (cap 200 commits/path, capped counts
   reported). Covers EP-1 RED #4 (seal-time snapshot of a since-modified tool).

## Classification of remaining unresolvables (frozen, in precedence order)
- **WARN_POINTER** — the citing line, or a committed receipt containing the sha,
  names a pointer: a repo-relative path (`results/`, `receipts/`, `tools/`,
  `experiments/`), or keywords `remote|recipe|regenerat|regen|ls-remote|manifest`
  (covers EP-1 RED #2 derived-data, #3 external-artifact, #6 historical-seal).
- **WARN_FOREIGN** — the sha is paired in the citing line or any committed
  receipt with a `SuperInstance/<repo>` reference (EP-1 RED #5 cross-repo pin).
  DEVIATION (declared before fire): the parent spec's `git ls-remote` network
  arm is NOT implemented in v2 — foreign pins resolve to WARN_FOREIGN on a
  committed remote+sha pointer, network resolution deferred to the RT-D1
  real-probe arm. No network calls in this tool.
- **WARN_SELFSCAN** — the citing line is census-narrative prose (matches
  `EP-1|census|REPRO`) quoting a historical anchor; EP-1's 7th self-referential
  RED class, made explicit instead of surprising.
- **RED** — none of the above. Verdict **GREEN iff RED=0** (WARNs allowed and
  counted; each WARN class total reported).

## Gates
- **G1** census counts printed, fail-loud on missing inputs.
- **G2** digest-claim resolution count (all arms).
- **G3** seal-prose resolution count.
- **G4** verdict GREEN iff RED=0. Expected at fire time: EP-1's six fired REDs
  reclassify as 1 resolved (recursive arm, #1 false positive) + WARNs (#2,#3
  POINTER; #4 historical-blob resolved or POINTER; #5 FOREIGN; #6 POINTER), and
  the census's own new booking prose classifies SELFSCAN/POINTER. Any NEW RED
  class = finding, booked honestly, no re-roll.

## Hazard fixes (mandatory, EP-1 repro finding)
- `--out PATH` argument; default NO canonical write — tool is read-only unless
  `--out` is passed explicitly.
- Refuse to overwrite an existing `--out` target (exit 2) unless `--force`.

## Cost
CPU only, ~10–20 min (historical-blob arm bounded at 200 commits/path).
