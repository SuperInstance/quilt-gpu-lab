# SCOUT-9 — fleet push sweep 2026-10-01 04:11Z (day-conductor, (A) rotation after PX6 repro PASS)

Window: since SCOUT-6 (21:11Z). Method: `/users/SuperInstance/events` + open PRs across 15 watched repos.
Read-only sweep. No comments/PRs filed.

## State changes (00:00Z–04:11Z)
- quilt-gpu-lab: our own pushes (01:40–03:07Z).
- fleet-triage: 2 pushes — **F1/F2 CORRECTED** (50a5d66) + "public site of measured work, reproduction path on every number" (0616f2f).
- quilt-canvas-tui: NEW activity — `cudaclaw-board` branch + issue #1 (PoEM gate trapdoor) + 5 commits (identity plane v1, HMAC-signed receipts, fleet_board.mjs dogfood, exp036 motivating sim).
- chiaroscuro: pushed main + new branch `round-5-lane-abcd` (12:56Z CreateEvent; content not inspected this slice).
- voxelglyph: 3 pushes (main).
- quilt-atlas: 2 pushes main (routine publishing census, not inspected).
- Patchwork-experts: push (not inspected).
- quilt-research-canons: new scout branch + **PR #4 OPEN** (scout 0132Z: 5 gems, 5 negative findings).
- Merged PRs: voxelglyph #? and pong-quilt (01:40Z).
- pong-quilt: **PR #88 OPEN** "Round 69: d(sChamp)/d(gen) printed lane on the C1 stats line" (Casey lane, routine).
- selectlib: issue #1 opened (Result.table() renders only last row — loop-body dedent bug; not our asset).

## Classifications

### STEAL — canons PR #4: quilt-cell-bridges, 44/63 bridges hardcode /workspace output paths
"44 of 63 bridges hardcode /workspace output paths and die on the final write in a clean clone. After neutralizing: 32 run, 23 .qzt. One bridge ships red."
=> This is OUR hardcoded-output-path defect class (5 internal witnesses: W5a, qc_jev_control, w5b2, px6 pre-flag, st1) at FLEET scale. Our `--out` doctrine is the fix pattern; our runners are a tiny population but the RC-1 spec is now validated by an independent 44-instance corpus. CORROBORATES RC-1 priority.

### STEAL — canons PR #4: logtensor dead homing term (88 tests green with the term zeroed)
"zeroing the proportional-navigation homing term keeps all 88 green; the term is never executed by any test."
=> Exact instance of the fleet's second law / our DEGENERATE-gate class: a component whose tests cannot detect its removal. No new item — feeds the already-open DEGENERATE gate + QC-JEV3 pins. Cite in their receipts when landed.

### CORROBORATE — voxelglyph: "the verification layer did not verify the product"
7 pins never executed the product; fixed to 11 tests with 3 previously-invisible mutations failing. Same class again (check that cannot fail). Third independent fleet witness today (canvas-tui §0 rules were the first, SCOUT-8).

### CONTRADICT-RESOLVED / CITATION-INTEGRITY — fleet-triage 50a5d66 F1/F2 CORRECTED
Their variance-collapse thesis self-corrected after the scout lane: "sigma^2/2k is 50-year-old mutation-selection balance; the phenomenon is already named 'vanishing variance' (arXiv:2404.04616). Four concessions, four survivals. Also: two FABRICATED arXiv IDs the fleet cites."
=> (a) **FT-2 (our reading item) is MOOTED in its original framing**: the contradict-candidate vs QG6 was based on the F1/F2 pre-correction text; the corrected version concedes the law is classical. QG6's "variance flat-to-harmful in qcells" stands as a cross-substrate data point against the strong collapse thesis; downgrade FT-2 to optional. (b) **NEW THREAT CLASS: fabricated arXiv IDs circulating in the fleet** — and our OWN SCOUT-1 findings cite "EvE (2609.36xxx)" with a hand-waved ID, and QO4 was spawned off it. If that ID was fabricated, QO4's reading premise is rotten. Spawned **SC-2**.

### TOOL — quilt-canvas-tui identity plane v1 (HMAC-signed receipts)
c49fdb3: HMAC-signed receipts, **key outside the agent process** (QUILT_HMAC_KEY / 0400 keyfile, group-writable refused); S3 pins a chain-repair attack — verifyChain passes on a public-rule repair, verifySignatures REFUSES it; "unsigned is a declared state, never retro-backfilled"; 27/27 pins green.
=> Direct upgrade path for our receipt-manifest doctrine: our seals are plain sha256 over paths — they detect accidental drift (D-2 silent edit) but an agent that can edit a file can re-seal it. HMAC with the key outside the agent process makes the seal tamper-evident against the agent itself, which is exactly the adversary class our own slices keep demonstrating (seal-pins-a-stray, dirty-tree bookings). Their exp036 + issue #1 (PoEM gate trapdoor: one FORGET seals an unverifiable receipt) extend the same design. Spawned **SIG-1** (day-item scale; needs Casey's key-management call, so pre-reg + design only, no key material touched).

### WATCH (no item)
- chiaroscuro round-5-lane-abcd branch — new lane, content uninspected; next sweep check.
- Patchwork-experts push — uninspected; next sweep.
- pong #88, selectlib #1, quilt-atlas — routine / not ours.

## QUEUE ITEMS SPAWNED (concrete)
- [ ] **SC-2 arXiv-ID integrity check** (CPU ~15m): verify every arXiv ID cited in our proposals/ + RESULTS.md resolves (export.arxiv.org API, one query per ID, no retry loops). Specifically SCOUT-1's "EvE 2609.36xxx" and QO4's premise. GATE in words: an ID that 404s or mismatches its claimed title => mark the citing proposal's spawn-premise UNVERIFIED in place (honest amendment, no deletion), and the spawned item is blocked until re-sourced.
- [ ] **SIG-1 signed-seal design note** (CPU ~30m, design-only): one-page note in proposals/ on adopting canvas-tui's HMAC pattern for receipt_manifest seals — key outside agent process, unsigned declared never backfilled; include the S3 chain-repair attack as the acceptance test. Needs Casey's sign-off on key management; do NOT generate keys or touch the sealer until he does.
- [ ] **FT-2 DOWNGRADED to optional** (edit the QUEUE line): original contradict-candidate text was superseded by fleet-triage's own correction (50a5d66); remaining value is only "does classical vanishing-variance (2404.04616) map onto qcell champion fitness across generations" — a reading item, low priority.

## Timebox
~14 min sweep + report. GPU lane idle all slice (no GPU item per (A)-first rotation). Next wake: top open CPU item (SC-2 or QC-JEV3 or DEGENERATE gate) or GPU QG1d/QG4 per queue order.
