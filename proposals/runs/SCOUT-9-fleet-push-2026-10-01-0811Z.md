# SCOUT-9 — fleet push sweep, 2026-10-01 00:11 AKDT (08:11Z), window since SCOUT-8 (02:11Z)

Method: /users/SuperInstance/events (user account, not org) + per-repo commits + `gh search prs/issues`.
Our own 07:2x-07:49Z quilt-gpu-lab pushes (CM1-r5, 0936af9/afeb30f) are OUR mirror — no foreign writes to our repo.

## 1. PR #6 TO OUR REPO — Seal guard fix (RC-3 delivered by the fleet) — VERIFIED, CASEY-GATED
"Seal guard: __pycache__ usability fix + refusal-semantics pins (d23b follow-up)". Files:
tools/receipt_manifest.py, tests/test_seal_guard.py, receipts/manifest.json, README.md. NOT merged by me.
Verification (scratch clone /home/eileen/scratch/pr6_check, FETCH_HEAD = pull/6):
- Suite **10/10 OK** (includes 4 new seal-guard pins; deterministic per PR claim).
- **Live-fire observed**: default invocation on a dirty tree REFUSES and names `?? experiments/_probe_dirty.txt`.
- Mutation claim (4/4 mutation-caught) NOT independently re-tested.
- Caveat booked honestly: my `--allow-dirty` admission-phrase grep came up EMPTY in the clone run — pin 4
  unverified by me (likely my grep vs their wording/exit path; needs one clean re-check before merge).
- Real usability find inside it: the guard refused seals after ANY test run because tracked
  `tools/__pycache__/*.pyc` regenerates on import — a guard that refuses over its own cache. Fixes our RC-3 ask.
- **Day item for Casey**: merge decision on #6 (one re-check of the --allow-dirty admission wording first).

## 2. STEAL/ACTIONABLE — chiaroscuro (NEW active repo, 8 open PRs 03:47-08:03Z)
Fruit-fly CX × JEV ternary × KC layer × Moth notary stack. #6 fly-stack v0: 1 PASS / 3 sealed FAIL, all
receipted. #5 JEV v2 HOLD/CAST abstention split. #2/#3/#7 weighted synonym-graph router 1.000 top-1 on a
pinned 50-prompt eval (baseline 0.560), parity-pinned TS mirror. #8 CAST v3 vocab-expansion pre-reg (sealed).
=> JEV is being consumed as a COMPONENT in anger. Two touches on our assets:
(a) their JEV v2 abstention split interacts with CM1-r5's controlled finding (jev-latest gate judgment
degrades with judge-state size) — if their gate batches grow, our finding predicts their judgments dilute;
(b) our QC-JEV booking (jeff-0.8b discriminates, d_ptrue 0.936) is checkpoint-specific — their "JEV" is
presumably jev-latest, whose null-at-scale behavior WE documented in CM1-r5.

## 3. CHECK/CONTRADICT-CANDIDATE — pie-minimax #1 (issue, open): "Exp 2 DONE by quilt-gpu-lab:
linear = 19.8% of ceiling; the COMPOSED prediction flips sign." Our FT-1 result is quoted back at us
with a composition claim ("composed prediction flips sign") we did not book. If their composition
analysis implies our FT-1 booking misread the composed-vs-linear relationship, that is a CONTRADICT on
a booked result. Highest-value read next.

## 4. CORROBORATE — quilt-atlas wave-74 + study-72k
- 72k: "replicates expose rounds-1..3 ceiling as partly luck (Muse first-shot 0/3 at round-3 config),
  harness verdict stays INCONCLUSIVE (fail-closed)" — direct corroborate of our QG7 ensemble doctrine
  (subpopulation verdicts as >=4 reruns) and of DEGENERATE/fail-closed verdicts.
- 74-a "Jev System-One calibration vs 3-auditor majority" — another independent JEV calibration lane;
  folds into CH-1.
- Also 74-d: slackwater-lattice hex_distance iff-bug pinned+fixed with a RED receipt vs published 0.1.0
  (fail-loud holding fleet-wide).

## 5. TOOL/CORROBORATE — kev-substrate-mojo (revived after 9 days)
Mojo port of the substrate (FNV-1a canary, Cell chain, QuantumEther) compiles on Mojo 1.2.0 and matches
Python **bit-for-bit** on-box; snap/client/CLI still scaffold-broken. TOOL for the qcell stack: a native
lane for vendor-hardware GPU. Cross-runtime bit-agreement also corroborated by quilt-attention #1 /
quilt-nn #1 (11/11 + 23/23 digests agree; scalarSha/lossShaOf not portable) — WIT-1 witnesses #6/#7.

## 6. CORROBORATE — quilt-neighbourhood v0.5/v0.6: reconciliation events as DAG markers, DID-signed,
fail-closed applyReconciliation (id gate, parents-known gate, signed-sheet refusal, assert-or-rollback),
42/42 + 178/178 suites; atlas 74-d replays it natively 248==248/506==506/1017==1017. Receipt-doctrine
convergent evolution; nothing to amend.

## 7. Quiet: Projectionist (cinema UI), AI-Writings (minimax-music lane r1-r2), pong-quilt #88/#89
(Casey lane), dependency-bump PRs (elf/pincher), canons #4 scout PR. [EMBASSY] pong #49 STILL unresponded
(day item for Casey, unchanged since SCOUT-4). quilt-canvas-tui #1 (PoEM gate trapdoor) + quilt-ewitness #1
(stale duplicate witness.mjs) — candidates for our periphery but not ours to fix.

## QUEUE ITEMS SPAWNED (concrete)
- [ ] **CH-1** (CPU ~40m): chiaroscuro deep read (#4 synthesis, #6 fly-stack receipts, #5 abstention
  split). Question: does their sealed-FAIL receipt set or JEV v2 design contradict any QO2/QC-JEV/CM1-r5
  booking, and does CM1-r5's judge-state-size degradation threaten their batched gate? Gates in words:
  (i) if their JEV v2 ships a discriminating control at batch>=36 that passes, CM1-r5's dilution finding
  needs a scope amendment; (ii) if their fly-stack PASS depends on our jeff-0.8b discriminator, cite QC-JEV
  as upstream dependency; (iii) else CORROBORATE and move on.
- [DONE 02:1x] **FT-1b** (CPU ~20m, PRIORITY — CONTRADICT-class): read pie-minimax #1 composition claim ("composed
  prediction flips sign") against our committed FT-1 artifact. Gate: if their composed-sign claim follows
  from our own results.json, our booking was INCOMPLETE (amend in place); if it requires their added
  composition math, CORROBORATE-with-citation; if it contradicts the committed numbers, fail loud.
- [ ] **PR6-CHECK** (CPU ~10m): one clean re-check of PR #6's `--allow-dirty` admission output (my grep
  missed it); then PR #6 is merge-ready for Casey's sign-off.
- [day] Casey: PR #6 merge decision; [EMBASSY] pong #49 (unchanged); murmuration jev-1.13.0 receipt note
  for DECIDE-2 (unchanged).
- [next slice, C] MANDATORY REPRO of CM1-r5 (latest booking): re-run is farm/LLM — verification = farm
  receipts + scoring-stage re-derivation from rounds.jsonl, not a re-fire; also the two foreign untracked
  dirs (data/c5/, results/av1/*) still pending the commit-not-touch treatment per ef726a3/d2ffc7a precedent.
