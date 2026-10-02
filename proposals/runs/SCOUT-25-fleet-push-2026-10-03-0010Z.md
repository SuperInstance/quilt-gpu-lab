# SCOUT-25 — fleet push sweep 2026-10-03 ~00:10Z (conductor day cron, slot (A); window since SCOUT-24 2039Z)

Sweep: 15 most-recently-pushed SuperInstance repos, commits since 20:40Z. Open PRs updated since window: NONE across 9 checked repos. New issues since 12:00Z: NONE (pong-quilt, quilt-gpu-lab, micrograd-quilt, fleet-seeds). [EMBASSY]: no new items; pong #49 unchanged (Casey day item). API caveat absorbed: dungeon-ml-zoo census found API `size` field broken fleet-wide (0 refs reported for a live repo) — canons' git/trees?recursive=1 blob-bytes method is the correct instrument; adopt for any future repo-size census.

## CONTRADICT: none.
QO2 routing stack, QO10 REGIME-DEPENDENT LADDER, receipt-manifest doctrine, QG3+QG6 time-law, QG1c, W5a/W5b, DECIDE-1 lineage — all unthreatened this window.

## CORROBORATE
1. **canons SCOUT-2235Z: failopen-CI census** (c136e01): 117/4331 source repos carry failopen CI constructs; **81 have the TEST RUNNER ITSELF failopen** (`pytest || true` etc.); one template (`ci-python.yml:34`) copied byte-identically 37×; fleet-triage's own FAILOPEN detector is "structurally blind" to CI-yaml failopen. quilt-gpu-lab is NOT in the failopen list (we have no workflows at all) — but that means we are UNGATED, not clean: no CI guard stands behind any booked result. Sharpened instance of the RC-1/RC-2 guard-gap class (3rd independent witness after canary-absence note + dirty-tree bookings).
2. **dungeon-jev v2 (f47427c)**: seal-before-run (9bf60d01 pushed before any model call), then honest P1 FAIL booked beside untouched seal ("scoring is a pure function of the pushed seal + local receipts, L20 verify-then-adopt"). Exact mirror of our pre-reg-then-fire doctrine holding fleet-side.
3. **jev-quilt 55th/56th-wipe hourly reports**: mean_p 0.6009-0.6068, 0 drift alarms — QC-JEV booking premise untouched, JEV oracle lane stable.

## TOOL / STEAL
1. **receiptd tipnotary slice 1.5 (5611f15)**: 3-valued tip check MATCH/STALE/FORGED, CF KV external chain anchor with `hash_spec` anchoring the spelling, verb split built/planned/d12-forced, and the **limit pin: a forgery PASSES verify but is named FORGED by the notary**. This is a live reference design for our open **RC-4 (seal-chain / reseal-forgery resistance)** — adopt the 3-valued + limit-pin pattern into the RC-4 spec. receiptd is now a SuperInstance repo (22:39) while a live `scratch/receiptd/receiptd.py serve` process runs in OUR tree (untracked, foreign-live per PW-1 precedent — do not touch, flag to Casey).
2. **fleet-kit fleetlint L9+L10 (e06f00a)**: canary canonicalisation + entry-point guard, same commit family as the failopen census. Candidate: point fleetlint at quilt-gpu-lab (we have no canary AND no CI).
3. **slackwater-lattice 0.1.1 on PyPI (697da52)** + wardroom RD-001 RETIRED: clean-venv math verification FROM pypi.org artifacts — the "verify the published artifact, not the source" pattern; candidate addition to RECEIPT-HASH convention if we ever publish.

## SPAWNED QUEUE ITEMS
- [spawned by SCOUT-25] **CI-1** (CPU ~30m): add a fail-closed test-runner GitHub workflow to quilt-gpu-lab (pytest, NO `|| true`, exit propagates) + the fleet canary per fleet-kit L9/L10 convention; run local suite green before pushing; cite canons SCOUT-2235Z (81-repo failopen class) as motivation. Improves: guard-standing of every booked result. NOTE: touches CI config — pre-reg the workflow file in the commit message, do not touch any existing scheduler/config.
- [spawned by SCOUT-25] **RC-4 spec amendment** (docs-only, fold into RC-4 when claimed): adopt receiptd 5611f15 pattern — 3-valued MATCH/STALE/FORGED + explicit limit pin test (forgery passes verify → named FORGED). Cite receiptd tipnotary slice 1.5.
