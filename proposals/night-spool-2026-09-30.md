# NIGHT SPOOL — 2026-09-30 (conductor queue; grows; each insight feeds the next)

## PROTOCOL (every wake, ~20 min timebox)
1. Read this file + `tail -40 RESULTS.md`. Check running work (`process list`), never duplicate an IN-PROGRESS item.
2. Take the top OPEN item. New experiment => pre-register in proposals/runs/ FIRST (commit+push before firing).
3. GPU python: /home/eileen/venvs/elephant-gpu/bin/python. Physics conventions: tools/qcell_sim.py (balance=min(p000,p111), angles in pi-units).
4. Book honestly in RESULTS.md (fail-loud anchors; wrong guesses get amended in place, never silently). Commit+push every landing.
5. Append findings below; add new queue items the moment an insight spawns one. Mark statuses so no wake repeats work.
6. ROTATION: after a GPU item, do a PR-SWEEP or SCOUT item next (alternate). PR sweep = `gh pr list -R SuperInstance/<repo>` + read new ones (repos: MicroMoth-quilt, delta-shape, syzygy-lattice, edge-ledger, subleq-fabric, zeroclaw-dissertation) — steal insights, cite PR#, add queue items. SCOUT = web_search for cutting-edge ideas worth rebuilding/forking into SuperInstance paradigms.
7. Do NOT message Casey (asleep). If local time >= 07:00 AKDT: book state, mark NIGHT COMPLETE, start nothing new.

## DOCKSIDE
- [DONE 04:3x QO5 BOOKED (birth lottery)]: g0 states byte-IDENTICAL across all 4096 streams (cv std 0, frac_identical 1.0, len_unique [2]) — g0 AUC 0.500 is trivial, nothing to distinguish at birth. Fate diverges at first selection round. QG2 tension resolved. Free QO3 replicate in the overwrite (rate in ±0.006 band, g0 0.500 again). Retroactive pre-reg declared (analysis-only; fired during QO3 wake). Commit 0df921d.
- [DONE 03:5x PR-SWEEP #3 (quiet)]: only state change = MM #29 merged (already handled in #2). micrograd-quilt #3-#7 all previously-seen mirrors, no updates. No steals, no new items. 6 repos, zero new PRs since 02:2x.
- [DONE 02:2x PR-SWEEP #2 + RECEIPT-CITE]: only MM #29 merged (docs citation pin). Applied convention to QG1/QG2/QO1 receipts (cite SuperInstance/micrograd-quilt, labs/qcells tree; PRs #5-#7 mirror). Docs-only, pushed.
- [DONE 02:3x] **DECIDE-1c BOOKED (REFUTES flip)**: instruction word largest->smallest changes NOTHING — 5/64 identical accuracy, argmin consistency 0.891 unchanged. Model is instruction-BLIND on this lane, not sign-flipped. STOP rule honored, no re-roll.
  - [spawned by DECIDE-1c] DECIDE-1d (instruction-ablation census): sweep instruction variants {largest, smallest, "highest", "lowest", neutral "Choose one edit.", superlative-only no-definition-sentence} x 64 questions. Map: does ANY phrasing move pred off argmin? If none do, the argmin lock is absolute in the representation -> name it and move on. Cheap (~6 lanes x 2 min).
- [DONE 01:3x] **DECIDE-1 FIRED + BOOKED**: G1 control PASS (16/16=1.0); G2 lane FAIL decisively BELOW chance (5/64=0.078; zero-shot and shipped trained readout give IDENTICAL predictions); G3 PASS (3.31 GiB, 54 ms); G4 exploratory (fitted-T pinned at boundary, fitted head 0.3125 not significant vs 0.25). Per protocol: STOPPED on G2 FAIL, no re-roll.

## QUEUE (top = next)
- [DONE 05:5x QO6 BOOKED (retractable kill-evidence gate)]: eproc.mjs ported (lineage pinned 61b9e04/aad90ac5); ALL V1-V4 PASS — late-bloomer fires (E 581) then retracts -> KEEP; hopeless -> KILL_CANDIDATE; sigma-honesty refusals verified. QO2 routing fully specified in components (oracle + budget triage + gate). Fired by 05:3x wake (died unbooked); replicated then booked this wake.
- [DONE 05:1x RECEIPT-HASH (tool/weight digest seal)]: manifest extended to 17 tool/weight files, test pin added, retroactive snapshot receipts/tool_pins_2026-09-30.md, 10 night receipts amended w/ Pinned-instruments blocks. Forward convention: receipts pin at fire time. Bonus: pins exposed QUEUE drift (D22/E13/E13b booked-not-claimed) — backfilled per c9b39b4 precedent, tests OK.
- [DONE 01:5x] **DECIDE-1b BOOKED (P1 INVERTED FIRED)**: predicted option is argMIN-balance on 0.891 of questions; argmin-prob acc 0.375 (lower CP95 > 0.25); pred_kinds delete=42 vs label_kinds insert=42; shuffle test content_following 0.78 vs letter_stickiness 0.375 (reads CONTENT, not position). The cell answers "smallest balance" — inversion lives in the backbone (both readers identical).
  - [spawned by DECIDE-1b] DECIDE-1c (confirmatory flip): re-run the SAME lane with instruction "...gives the smallest balance?" — prediction: argmax accuracy jumps toward the same 0.89 consistency (mirrored). If it does, the mechanism is a signed-superlative flip, fully characterized. Pre-register before firing.
- [DONE 00:0x] **DECIDE-1 pre-reg + tool + driver WRITTEN** (`tools/decision_cell.py`, `experiments/decide1.py`, `proposals/runs/DECIDE-1-decision-cell.md` + AMENDMENT 1): jeff mechanism fully reverse-engineered — 255x1024 readout head, temperature 1.1289, exact prompt template, answer formulas. Firing blocked only on the 1.7 GB weight download.\n- [DONE 00:0x] **Recons landed**: `proposals/physicalcoding-recon-2026-09-30.md` (1288w) + `proposals/jeff-recon-2026-09-30.md` (1004w + addendum).\n- [DONE 00:0x] QC: `tools/qcell_sim.py` gained the missing `crx` gate + receipt-anchored selftest (k4 champion 0.4268).\n- [DONE 00:0x] QG2 desert-break law: **desert is STRUCTURAL** — exact-arm 57.9% ~= shot-arm 58.2%; ~42% of streams landscape-trapped; G1 FAIL (lane fills desert 0.023 vs recorded 0.017); G2 rate caveat (reimpl 58% vs recorded 3/8; P~0.26 at N=8). results/qg2_desert_law/
- [DONE 01:1x] **QO1 qcell-oracle BOOKED**: G1+G2 PASS, oracle AUC 0.9510 vs baseline 0.8860 (Brier 0.087); features cv>v>gen >> gates. First trained fleet component. Lane torch-nondeterminism ±0.006 noted (all runs in CP95). WAS: train a tiny MLP on QG2 rollouts -> P(cross | champion state: len, balance, gate histogram, gen). Save tools/qcell_oracle.pt + README. First TRAINED fleet component on this substrate. Data: instrument run_lane to dump per-gen champion states + outcomes (4096 streams = 400k+ rows free).
- [DONE 05:3x GPU] **QG6 BOOKED**: no variance rescue. k=1 0.601 (replicate PASS), k=2 0.585 (indist.), k=3 0.522 (sig BELOW, delta_lb -0.139; too-hot). Median crossed_gen 2->4->5: big moves DELAY crossing. QG3+QG6 law: trapping is a TIME problem — only more generations rescue; width inert, variance flat-to-harmful. Spawned QG7. Commits 269b561 / 5df2739.
  - [spawned by QG6] QG7 (generation-asymmetry routing test): run gens=24 lanes; check whether oracle at gen 1 (QO3, AUC 0.88) separates streams that cross only-at-24 from hopeless-at-24. If yes, QO2 routing = oracle + budget triage fully specified.
- [DONE 07:1x GPU] **QG1-residual BOOKED: verdict NAME** — the 28 misses are swap/wire-order convention mismatch (swap Fisher 7.0e-19; BH 28/28; signed dev -0.205), NOT noise. META: committed census script exposed (radians vs declared pi-units; never produced its own 1892 booking; pi-unit variant reproduces bit-exactly). See RESULTS.md. Spawned QG1c (fix swap semantics, re-census, decompose swap-vs-x).
- [DONE 00:2x PR-SWEEP #1] see FINDINGS.
- [DONE 03:2x SCOUT #1]: see FINDINGS 03:2x. Web search API degraded (503/timeout) — fell back to arxiv API (export.arxiv.org), which worked. Note for future scouts: use the arxiv API directly, no retries on the search provider.
- [open] SL-G1: syzygy-lattice e-process martingale Monte Carlo (port LR rules to torch; operating-characteristic curves: kill-on-impossible, impostor late-cross; validate truth@10/impostor@112 pins first).
- [open] SCOUT #1 (see rotation).
- [open] SF-G1: subleq VM in torch (Int32Array machines, batched) -> program-space census; validate vs subleq-fabric pins.
- [open] DS-G2: change-point GPU engine, synthetic boat telemetry first (the 5-min predictor line = trail() membrane).
- [DONE 03:5x GPU] **QG3 BOOKED**: traps OPEN with generations — C(W6,g24)=0.755 ~= B(W8/g24)=0.763, D(W8,g12)=0.568 ~= A(W6/g12)=0.578. Width is INERT; trap = slow-climb fence (refutes my P1; QG2 structural-desert sharpened: passable at 2x gens). Basin edit-distance metric INCONCLUSIVE (degenerate on short champions; no claim either way).
  - [spawned by QG3] QG6 (variance rescue): DONE 05:3x — see QUEUE mark + FINDINGS.
  - [spawned by QG3] QG3b (basin observable fix, cheap): re-cluster stuck champions by champion STATEVECTOR distance (unitary output overlap) instead of genome edit distance. Only if QG6/QO2 needs basin identity.
- [DONE 04:5x GPU] **QO3 BOOKED**: g*=1 stable (bootstrap IQR [1,1]); AUC 0.500(g0) -> 0.880(g1) -> 0.913(g2) -> 0.931(g3) -> ... -> 0.999(g12). HEADLINE: birth state carries ZERO signal (g0 AUC exactly 0.500 both models); one selection round exposes fate. Tension w/ QG2 desert-at-birth: desert is landscape property, not stream-observable at birth. Feeds QO2: route at gen 1 (0.88) or gen 3 (0.93).
  - [spawned by QO3] QO5 (birth-state insufficiency probe): WHY is g0 AUC exactly 0.500? All streams share one skeleton draw + fresh mutation, so birth states may be near-identical across streams (check state diversity at g0: var of len/v/hist across streams). If g0 states ARE diverse but uninformative -> landscape decides, stream state irrelevant; if g0 states are near-identical -> desert-at-birth means birth LOTTERY, and gen1 selection is the first observable branch point. Cheap (data already in results/qo3_horizon).
- [spawned by QG2] QG4: budget/gens phase diagram (W x gens grid, 1024 streams/cell) — map the crossing frontier. Directly serves "cells are dedicated; routing happens between cells".
- [spawned by PR-SWEEP #1] RECEIPT-CITE: amend QG1/QG2 receipts (proposals/runs/*.md) to cite SuperInstance repos by name (weight law; see MicroMoth-quilt PR #29). Docs-only, no re-run.

## FINDINGS (append-only)
- 00:0x CONDUCTOR-0 (main): QG2 headline above. qcell-sim gained crx + receipt-anchored selftest. Vectorized lane = gathers + bmm chains; ANCHOR-VEC 2e-34.
- 00:2x PR-SWEEP #1 (conductor): 6 repos swept; only MicroMoth-quilt active. **PR #29 OPEN** — docs-only provenance: qcells lab canonical home = SuperInstance/micrograd-quilt; cite repo not local path in receipts. Clean (fail-first pins, 248/249; 1 pre-existing main-tip manifest drift, remedy already in PR #25 stack). Merged highlights: #28 exp022 train-visible crossing census (tie-break-invariant), #27 rate-not-wall + desert-extends-to-cloud, #26 tie-band-diversity replicated, #25 archive-assembly + manifest regen, #24 fitness desert at birth cloud (29/31/37). **Steals:** (a) weight-law by-name citation -> spawned RECEIPT-CITE item; (b) exp018 desert-at-birth-cloud independently corroborates QG2 structural-desert — desert is upstream of selection, now two lanes agreeing; (c) note bookkeeping discipline: my first spool edit clobbered the QG4 queue line; caught + restored same wake. Always re-read the file after structural edits.
\n- 00:45 CONDUCTOR-0 (main): PhysicalCoding + jeff recons landed; DECIDE-1 armed behind the weight download; qcell_sim crx fix (tool had been missing a gate the telemetry uses since QG1 — caught by the QG2 anchor).\n- 01:1x CONDUCTOR slice (night cron): QO1 landed (see RESULTS.md). Two spawned items:
  - [spawned by QO1] QO2:
- [spawned by QO1] QO3: early-forecast horizon — at which gen does oracle AUC first clear 0.80? (train per-gen classifiers). If gen<=3, crossing is near-deterministic early -> desert streams are visible at birth, feeding QG3.
- 01:3x CONDUCTOR slice (night cron): DECIDE-1 fired on landed weights and booked. Headline: jeff-0.8b's decision
  mechanism is intact (control 16/16) but the balance-edit lane reads BELOW chance (0.078 vs 0.25 random) — and the
  shipped trained readout and zero-shot head give byte-identical wrong predictions on the lane. Below-chance
  symmetric failure is information: the backbone encodes a consistent-but-wrong decision signal for this question
  family. Spawned DECIDE-1b (diagnosis before anything else on this lane). Fail-loud trail: 3 mechanical crashes
  fixed in place pre-scoring (chat-template fallback bypassed in arm C, device split, str-vs-int labels); honest
  note: the fitted-T optimizer pinned at the 6.0 boundary — flag for any future temp-fitting on near-zero-signal
  logits. 20-min slice complete; ~02:00 next wake should take DECIDE-1b (GPU) then PR-SWEEP per rotation.
- 01:5x CONDUCTOR slice (night cron): DECIDE-1b landed. Headline: **the below-chance lane is INVERTED, not
  broken** — jeff-0.8b picks the argmin-balance (worst) edit on 89% of questions, prefers delete-type
  options (42/64) where truth is insert-type (42/64), and follows option CONTENT under shuffling (0.781)
  rather than letter position (0.375). Both readouts identical => inversion is in the backbone representation.
  Hypothesis (untested): superlative-direction flip — the cell tracks "balance" but answers "smallest" when
  asked "largest". Spawned DECIDE-1c (instruction-flip confirmatory). Next wake per rotation: PR-SWEEP #2
  (GPU item just landed), then DECIDE-1c.
- 02:2x CONDUCTOR slice (night cron): PR-SWEEP #2 (only MM #29 merged; citation convention applied =>
  RECEIPT-CITE DONE, QG1/QG2/QO1 receipts amended docs-only) + DECIDE-1c fired and booked. Headline: the
  superlative word in the instruction has ZERO causal effect on jeff-0.8b's choice (identical 5/64 across
  largest/smallest); the argmin-balance lock is instruction-blind while the numeric control lane reads
- [DONE 02:5x] **DECIDE-1d BOOKED (lock ABSOLUTE)**: argmin consistency 0.844-0.891 across all 6 phrasings (largest/smallest/highest/lowest/neutral/no-def); argmax acc 0.078-0.125; neutral = identical to largest. Named **representation-locked argmin**. DECIDE lane CLOSED tonight per STOP rule.
  - [spawned by DECIDE-1d, day-item for Casey] DECIDE-2 (representation surgery, NOT a night item): linear probe on pre-readout hidden states — does the argmax-balance signal exist upstream of the routing? If yes, LoRA/head-retrain fix is cheap; if no, the ordering itself is encoded inverted. Needs new instrumentation in decision_cell.py.
  superlatives fine. Signed-flip hypothesis dead. Spawned DECIDE-1d (instruction-ablation census).
- 02:5x CONDUCTOR slice (night cron): DECIDE-1d fired and booked (census: lock absolute across 6 phrasings,
  named representation-locked argmin; DECIDE lane closed per STOP). Spawned DECIDE-2 (representation surgery,
  day item — needs Casey's eyes + new instrumentation). Rotation for next wake: non-GPU per rotation
  (PR-SWEEP #3 or SCOUT #1), then QG1-residual/QG3/QO3 per queue order.
- 03:2x CONDUCTOR slice (night cron): SCOUT #1 landed (non-GPU per rotation; last slice was DECIDE-1d GPU). Source:
  arxiv API fallback (search provider 503 — one alternate route, no retry loop). Six live steals, ranked:
  1. **EvE "An Alternate Optimizer to Adam" (2609.36xxx)** — configs ranked CHEAPLY and pruned EARLY in search
     budgets. Maps directly onto QO2/QO3: oracle-guided pruning is the same doctrine; steal any early-ranking
     metric ideas for oracle features. Spawned QO4 below.
  2. **CMDO: Cognitive Memory-Driven Optimization** — population search retaining the CONTEXT where behaviors
     succeeded/failed. Mirrors QO1 oracle + QG3 desert clustering: routing should remember *why* streams died,
     not just that they died. Feeds QG3 design (basin memory features).
  3. **"Where Does Randomness Matter in Neural Cellular Automata?"** — separates train-time vs execution-time
     update randomness. Directly relevant to qcells: our structural-desert law says trapping is upstream of
     selection; this paper's train/exec randomness split is a ready-made ablation frame. Spawned QG5 below.
  4. **KACS: Kolmogorov-Arnold Classifier Systems (IEEE TEVC 2026)** — rule count O(m^n)->O(mn^2) via
     dimension-wise decomposition; first LCS universal-approximator proof. Speaks to "cells are dedicated;
     routing happens between cells": per-dimension dedicated rulesets + superposition. Candidate frame for
     qcell rule-space scaling. Spawned QC-KA below (reading item first).
  5. **"Evolving Towards Better Codes: LLM-Guided Search"** — record-breaking combinatorial constructions via
     LLM-driven evolutionary search. Directly relevant to subleq-fabric program-space census (SF-G1): the
     harness pattern (LLM proposes mutations, exact verifier accepts) is exactly our lane. Read before SF-G1.
  6. (minor) iSOMA-AR adaptive rotation — learns a basis from successful migration displacements; long-shot
     idea for qcell routing if basins show shared geometry.
  Spawned queue items: QO4, QG5, QC-KA. Rotation honored (GPU last, non-GPU this). Next wake: GPU — QG3
  (marked NEXT GPU) or QG1-residual per queue order; pre-register before firing.

  New queue items spawned by SCOUT #1:
  - [spawned by SCOUT #1] QO4 (early-ranking steal): read EvE paper; extract its cheap early-ranking signal
    and test as an oracle FEATURE alongside cv/v/gen (does EvE-style momentum of champion fitness improve
    QO1 AUC 0.951? Does it clear 0.80 earlier than QO3's per-gen horizon?).
  - [spawned by SCOUT #1] QG5 (train-vs-exec randomness in qcells): NCA-paper ablation frame — does desert
    trapping depend on update-randomness at roll-in vs roll-out? Instrument run_lane with a deterministic-
    rollout arm (fix champion stream RNG at eval). Cheap, feeds QG3.
  - [spawned by SCOUT #1] QC-KA (reading, non-GPU): read KACS paper + repo (YNU-NakataLab/KACS); write a
    1-page note on whether Kolmogorov-Arnold dimension-wise decomposition applies to qcell rule space.

- 03:5x CONDUCTOR slice (night cron): QG3 booking landed (was uncommitted — committed+pushed ba565d8 first).
  PR-SWEEP #3 (rotation: non-GPU after QG3 GPU): QUIET — 6 repos, only MM #29 merge as state change, no new
  PRs since 02:2x, micrograd-quilt #3-#7 stale mirrors. No steals. Rotation for next wake: GPU — QO3
  (early-forecast horizon, marked NEXT GPU) or QG1-residual per queue order; pre-register before firing.

- 04:3x CONDUCTOR slice (night cron): QO5 landed (booked by prior wake's opportunistic probe —
  verified sound, pre-reg declared retroactively, committed 0df921d). Then PR-SWEEP #4 (non-GPU
  rotation honored): **delta-shape PR #1 NEW+OPEN** (first PR outside micrograd-quilt all night) —
  "Drift significance layer (E1-E5): e-witness bridge consuming SuperInstance/quilt-ewitness".
  3-score lines: WHERE (shape, content-addressed) / WHETHER (Ville-bound e-process) / signatures
  (HMAC). Steals: (a) **retraction doctrine** — "a process that cannot retract is a p-value in
  disguise"; our QO2 oracle kill-decisions are irrevocable tail predicates — an e-process evidence
  layer with retraction should gate stream-killing (spawned QO6); (b) **sha256-pinned vendored
  consumption** — hash IS the identity, mismatched bytes refuse to run; applicable to our
  weight/tool receipts (spawned RECEIPT-HASH); (c) **pre-registered sigma, no silent defaults**
  — tool refuses to run without it; matches our pre-reg discipline, steal the refusal-pattern.
  Also: SL-G1 priority RAISED — quilt-ewitness is now consumed in anger by delta-shape #1;
  its LR-rule validation pins serve a live consumer. Other 5 repos: quiet (MM #29 last state
  change, as sweeps #2-#3). Rotation for next wake: GPU — QG6 (variance rescue) or QG1-residual
  per queue order; pre-register before firing.

- 04:5x CONDUCTOR slice (night cron): QO3 landed (GPU, per rotation after PR-SWEEP #3). Headline:
  horizon g*=1 (bootstrap-stable IQR [1,1]); AUC path 0.500 -> 0.880 -> 0.913 -> 0.999; gen-0
  AUC EXACTLY 0.500 for both MLP and cv-logit — birth champion state is uninformative about
  eventual crossing, one selection round reveals ~0.88 (cv-only logit alone 0.811). Sharpest
  framing for QO2: routing decision is cheap and reliable from gen 1; nothing to decide at
  birth. Spawned QO5 (why is g0 exactly uninformative — state-diversity census on existing
  data, near-zero cost). One crash en route (importing oracle1 executes QO1's training —
  module-not-found caught, lane copied verbatim, declared in code). Rotation for next wake:
  non-GPU (PR-SWEEP #4 or SCOUT/QC-KA reading), then QO5 or QG6 per queue order.

- 05:1x CONDUCTOR slice (night cron): RECEIPT-HASH landed (non-GPU, rotation honored after
  QO3/QO5 GPU slices). tools/receipt_manifest.py now seals tools+weights (17 files) alongside
  experiments; test_receipts.py pins the tools section; retroactive snapshot in
  receipts/tool_pins_2026-09-30.md (seal-time hashes, fire-time declared un-captured);
  10 night receipts amended with Pinned-instruments pointer blocks; forward convention =
  pin at fire time. FAIL-first observed: extending pins immediately exposed 3 pre-existing
  QUEUE drift entries (D22, E13, E13b booked in RESULTS, never claimed in QUEUE) — backfilled
  per the c9b39b4 D18 precedent, manifest re-sealed after each ledger change, all tests OK.
  Rotation for next wake: GPU — QG6 (variance rescue, top GPU item) or QG1-residual per
  queue order; pre-register before firing.

- 05:5x CONDUCTOR slice (night cron): QO6 BOOKED (CPU, non-GPU — rotation honored after QG6 GPU).
  Found the 05:3x wake had fired QO6 (pre-reg daf7db7 committed) but died before booking —
  untracked eproc.py + experiment + results dir. Replicated (deterministic, ALL_PASS identical)
  before booking. Headline: the retraction gate works — late bloomers keep, hopeless kill,
  flat insufficient; QO2 is now fully specified in components (oracle + triage + gate).
  Bookkeeping lesson: when a wake dies mid-slice, its artifacts land uncommitted+untracked —
  `git status` + `process list` on every wake catches this (protocol step 1 already says so;
  this is the first time it fired in anger). Rotation for next wake: GPU — QG7
  (generation-asymmetry routing test, top GPU item, gens=24 lanes ~2x QG3 cost; budget check
  against remaining night) or QG1-residual per queue order; pre-register before firing.

- [DONE 06:4x GPU] **QG7 BOOKED (ensemble)**: gens=24, S=2048. **P1 FAIL** — gen-1 signal cannot reliably
  separate late-bloomers from hopeless (AUC 0.546/0.663/0.636/0.580 across 4 identical-seed reruns, mean 0.606,
  only 1/4 clears 0.65 = luck). **P2 PASS weak** — frozen QO1 oracle ranks late>hopeless (0.566-0.581),
  miscalibrated as expected. **QO2 routing law finalized**: forecast (g1 AUC 0.88) for the cross-by-12 majority;
  desert subpopulation (~42%) governed by QO6 e-process retraction gate — evidence, not tail predicates.
  Commit 9a93858. NEW LESSON: lane torch-nondeterminism is MATERIAL for subpopulation questions — always book
  subpopulation verdicts as rerun ensembles (>=4), never single draws.
  - [spawned by QG7] QO7 (day-item for Casey, needs his eyes): assemble the QO2 routing system end-to-end as a
    runnable component (oracle + budget triage + eproc gate + gen-1 router) over a fresh 24-gen lane with a
    budget scoreboard: streams saved (late kept) vs wasted (hopeless funded to 24) vs wrongly killed. All
    pieces exist and are pinned; this is integration + one scoreboard run. NOT a night item — the QO2
    stop/kill thresholds deserve pre-registration with Casey's judgment on the cost matrix.
Rotation for next wake: non-GPU (PR-SWEEP #5 or SCOUT #2), then QG1-residual or QG4 per queue order.

- 06:4x CONDUCTOR slice (subagent): PR-SWEEP #5 (non-GPU per rotation after QG7 GPU). **pong-quilt main red +
  PR #84 failing check ROOT-CAUSED**: single test — receipt-completeness CLI refuses on shallow checkout
  ("no merge commits reachable from HEAD — fetch-depth must be 0", exit 2 vs 0; tests/receipt-completeness.test.js:75).
  277/287 pass, 9 honest-SKIP; merge-gate full suite PASSES the same branch (it uses fetch-depth 0) ⇒ environmental
  red in the build-and-test workflow, NOT a regression; fix = fetch-depth: 0 in test.yml. #84 otherwise green
  (forge + merge-gate + GitGuardian), MERGEABLE, no review yet. quilt-nn#1 (issue, untriaged): lossShaOf not
  portable cross-runtime, forward can't be called cold — corroborates RECEIPT-HASH caveat (pins are runtime-bound).
  [EMBASSY] pong-quilt#49: erised-mirror strand stranger-verified the r37 stone-v1 chain 5/5 from published
  arithmetic alone — independent-reimplementation-verify doctrine corroborated; still unresponded (day item for
  Casey). Only other state change: pong-quilt round-66 branch pushed (forge green, no PR yet). Full detail in
  workspace memory/superinstance-watch-log.md 06:45 entry. Sweep ~6 min ⇒ QG1-residual fires this slice
  (pre-reg pushed before firing).

- 07:1x CONDUCTOR-0 (main, morning): QG1-residual booked (see RESULTS + QUEUE mark). Rotation: QG1c pre-reg (CPU, tight scope) or PR-SWEEP #6; chip free.
