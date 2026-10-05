# SCOUT-45 — fleet push sweep, 2026-10-05 19:15Z (11:15 AKDT day-conductor, (A) slot)

Window: since SCOUT-44 (~2026-10-04 17:10Z). Method: `gh api repos/.../commits?since=` across 14 repos; open-PR + open-issue sweep; pong #49 comment count. Read-only; nothing filed.

## HEADLINE — MicroMoth-quilt wave-69 merge stack #33-#41 (21:42-21:48Z, 7 PRs in 6 min)
Witness-collapse-seam architecture landed: LINK -> TICK*(state_witness) -> SEAM -> EFFECT* as ONE hash chain; seeded collapse outcomes chained to the witnessed pre-collapse boundary; `verify()` re-derives every cell id + replays witness + re-samples seeded outcomes ("tamper names itself"). Refusal doctrine: no noise_model, no unseeded collapse, unmeasured circuits refused; **"header fields that outvote the on-chain witness are refused, not laundered"** (#38 emit-artifact); "the file is never trusted unread" (emit then verify in same run). FAIL-first pins verified from depth-1 clones, import-baseline manifests resealed each PR.
- Classification: **TOOL/STEAL** (maps onto our RC-4 seal-chain + receipt-manifest doctrine). Our sealer refuses dirty paths but does not REPLAY-VERIFY the sealed artifact on read; their witness-outvote refusal is the exact guard against a stale-but-valid seal. Spawned **MM-SEAM** (docs, ~20m).
- CORROBORATE: spec_sha-style FAIL-first-from-pristine-clone provenance now fleet-standard (3rd/4th independent repo).

## MicroMoth #44 IONQ rung-2 SIM pre-flight (18:46Z) — **CORROBORATE, IONQ-2 booking non-vacuous**
Their shot-measured rung-2: calibration transfer = sin²(θ/2) within band (2π/3: pred 0.750000, meas 0.751135); additivity crx(π/3)² measured 0.749435; cancellation discriminator PASSES (forbidden sum ~0, "flagged" exact-zero caveat). Our IONQ-2 booking (exact CPU statevector: transfer 1e-9 at every θ, additivity 0.75 exactly, cancellation EXACTLY 0.0) is the coherent-limit upper bound their seeded shots are converging to. **No CONTRADICT** — qcell_sim crx convention now independently stressed both sides of the same bridge. No new item.

## jev-quilt r6 live battery #50-#53 (Oct 4 19:21Z -> Oct 5 18:47Z) — **G1/F1 BIMODALITY GENERALIZED**
run5 (#52): F1 same-window voting probe bimodal — REJECT mode then ACCEPT x5 **on identical bytes**; G1 bimodality generalized (run3: 8 verbatim re-runs, 7/8 stable + graft flip; run4/run6 stability points 3/5). All record-only.
- Classification: **CORROBORATE of QG7 lesson** (lane nondeterminism is MATERIAL; never verdict on a single draw) — but also a **CONTRADICT-candidate for our repro protocol**: D12u1/u2/u3 and IONQ-2 repros all happened to be deterministic (statevector/exact arithmetic), but our committed-repro gate has no explicit determinism witness requirement. A bimodal lane booked from a single draw would false-green. Spawned **DET-1** (CPU census ~30m).

## pong-quilt: rounds 80-96 PR stack open (#114-#119), R91 merged (21:56Z)
R91 test loosening: lag-count regex 1→\d+ — "the count is a garnish; the contract under test is the lag NAMED + faithful + not a finding." **TOOL**: contract-over-garnish assertion lesson — same class as our FW-1 field-write census (verify the claim's load-bearing field, not a proxy). Note filed for FW-1 successor; no spawn (class already covered).
[EMBASSY] pong #49: still 7 comments, unchanged since SCOUT-37 (Casey day item).

## fleet-triage / canons / quilt-mcp-receipts / quilt-research-canons
Batch edge-watch merges #5-#22 (21:41-21:58Z, archival of Oct 3-4 edge-watch branches — content already consumed via SCOUT-38/40/44 windows). wave-69 knowledge-package docs commits across 4 repos (20:58Z, docs-only). quilt-matrix quiet this window. No new issues of note; jev-quilt #42 (G-credential ↔ W3C VC) predates window, untriaged fleet-side.

## CONTRADICT SCORE: none.
QO2 stack, receipt-manifest doctrine, QG3+QG6, QG1c, W5a/W5b, DECIDE-1/2, IONQ-2 all unthreatened. Closest call: jev-quilt bimodality (resolved to CORROBORATE-with-gap → DET-1).

## SPAWNED QUEUE ITEMS
- [ ] **DET-1** (CPU ~30m, pre-reg first): determinism-witness census — for every BOOKED verdict, classify its lane as (a) exact/arithmetic (statevector, integer) → deterministic by construction, (b) seeded-RNG with committed seed → deterministic IF seed+generator pinned, (c) torch-GPU nondeterministic → verdict MUST be an ensemble (QG7 law) or carry a nondeterminism receipt. Gate: every booked verdict lands in exactly one class; any class-(c) single-draw booking = RED (candidate: none known, census decides). Cite jev-quilt #52 bimodality.
- [ ] **MM-SEAM** (docs ~20m): RC-4 seal-chain spec amendment — adopt MicroMoth #33/#38 refusal doctrine: (1) re-seal must replay-verify content, not just hash; (2) sealed header/manifest fields may not outvote on-chain (committed artifact) content — mismatch = named refusal; (3) "file never trusted unread": read paths verify. Cite PRs #33-#41, #38 pins.
