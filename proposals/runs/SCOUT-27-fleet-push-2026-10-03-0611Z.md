# SCOUT-27 — SuperInstance sweep, 2026-10-03 06:11Z (day-conductor slice, ~20m)

Sweep basis: users/SuperInstance events (window since 2026-10-01T06:11Z, primary window post-SCOUT-26
04:39Z), open PRs, open issues. NOTE: events-API commit payloads came back empty (jq got nulls/empty
messages) — per-repo `repos/.../commits?since=` used as fallback; added to scout recipe.

## State changes since SCOUT-26 (04:39Z)
- wardroom: 798929d philosophy post ("when your habits compile, who is the player?") + c8d1c2b exocortex
  fleet-funded revisit. Narrative; no asset contact.
- quilt-jepa round-11 SEALED: verdict 24/31 (CARRIER11 PASS, SAT11 FAIL, DIP11 PASS); round-10 claims
  carried BY REFERENCE — run10.json chain re-derived from genesis, 22/28 verbatim, ZERO re-execution.
- PR doubt-ledger #19 (docs): adjudication-client #16 × receiptd-hedge consistency review, CONSISTENT
  on 5 load-bearing axes, one non-blocking citation gap. Docs hygiene lane; corroborates review doctrine.
- PR pong-quilt #103 (Round 81): **headline find — receipt-claims-vs-artifact drift across a re-land.**
  R74 receipt claimed the R1 entry gains "### Measured at the tag …" but re-land cab770c (#96) DROPPED
  the entry edit while KEEPING the receipt text; five rounds of cap-cluster specs (R77–R81) carried
  against a ghost; suite green; no pin fired. Root-caused, entry restored, new glue pin tests shipped.

## Classification vs our live assets
- **No CONTRADICT** — QO2 stack (QO1+QG3/QG6+QO6), DECIDE-1/2 lineage, receipt-manifest doctrine,
  QG3+QG6 time-law, QG1c, W5a/W5b all unthreatened.
- **CORROBORATE (D-2 class, new variant)** — pong #103's ghost is D-2 silent-edit via RE-LAND: the
  receipt SURVIVES the rebase while the artifact it describes is dropped. Our analog surface: receipts
  cite commit hashes (good), but no check asserts the CLAIMED ARTIFACT (section/file/pin) still exists
  at the canonical tip. HB-1 checks literals, not receipt-anchor existence. → spawned **RE-1**.
- **TOOL/STEAL (verification tier)** — quilt-jepa's chain re-derivation from genesis (verify a claim
  chain by digest arithmetic, no re-execution) is a cheap tier BETWEEN "trust the receipt" and "full
  committed-script repro". Not a substitute for RC-1 mandatory repro (chain proves lineage, not that
  the code produces the numbers) but a fast pre-filter for multi-receipt chains (receipt-manifest,
  tool_pins). → spawned **JT-1** (reading/design, LOW).
- doubt-ledger #19: docs-only consistency review; nothing to act on.

## Spawned queue items
- [ ] **RE-1 receipt-anchor check** (CPU ~30m): for every booked receipt in results/, extract artifact
  anchors it claims (file paths, RESULTS.md section headers, named pins/tests) and assert each exists
  at HEAD; missing anchor = RED (pong #103 class). Fold the check into tools/receipt_manifest.py as a
  `--anchors` pass (sealer refuses on RED).
- [ ] **JT-1 chain-derivation tier** (CPU reading ~30m, LOW): read quilt-jepa round-10→11 carry-by-
  reference mechanics (genesis chain re-derivation); write 1-page note on whether a digest-chain
  pre-verify tier is worth adding ahead of full repro for chained receipts; explicit non-substitution
  caveat vs RC-1.
