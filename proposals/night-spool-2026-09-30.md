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

- [DONE 07:2x GPU] **QG1c BOOKED: verdict NONE** — all 6 frozen candidates: C0 current best (0.9854); nothing improves; the 28 misses are swap-ONLY (x spurious). Not a wire-order/order/CNOT-substitution typo. Spawned QG1d: read micromoth's exp022 simulator swap source (byte-level recon, read-only, cheap).

- [PARTIAL 07:2x recon] **QG1d first finding (provenance gap)**: micromoth-quilt's exp022 generator
  (receipts/exp022-desert-break/exp022_crossing_stream_census.py) imports `qcell.search`
  (Candidate, fitness, p_target, mutate, random_gate) and that module does NOT exist anywhere in the
  tree (not micromoth-quilt, not micrograd-quilt, not under ~/projects) — the generator cannot run,
  so exp022's recorded train_p/verify_p are not reproducible from the committed receipts (same
  systemic class as the dirty-tree bookings: the producing code is not in the repo). Also verified:
  micromoth.py's own swap arithmetic is a CORRECT transposition (b01<->b10), so the residual 28 is
  not a swap-arithmetic typo in their simulator either. NEXT for QG1d: recover/reimplement p_target
  (fitness definition unknown — may not be min(p000,p111)) and rebuild one failing genome directly in
  micromoth.QuantumCircuit to separate "recorded values stale" from "fitness definition differs".

## SCOUT-2 (morning, Casey-directed) — what the fleet is pushing 2026-09-30, classified
Sweep: SuperInstance account (it's a USER account, not an org — `/users/.../events` works, `/orgs/...` 404s),
14 repos pushed in the last 48h. quilt-gpu-lab is the most-active repo this morning (our own pushes), plus
percept-plugs, xruntime-conformance, substrate-foundation, consul-client, AI-Writings, Syzygy,
quilt-research-canons, quilt-atlas, pong-quilt.

**STEAL — percept-plugs v0.2/v0.3 (witness sheet + multi-runtime differential fuzz)**
v0.2: JS/Python/C++ agree byte-for-byte on 2000 seeded adversarial series; the pins CAUGHT 2 real bugs
(stream null-vs--1 contract; zero-surround ratio edge). v0.3: witness-sheet layer with P12 pinning the
canon-chain defect classes D-1 splice / D-2 silent edit / D-3 reorder / D-4 truncation, bundle sha256 re-pinned.
=> Their D-2 "silent edit" IS our dirty-tree booking class (3 instances found today: d23b phantom seal,
qg1 census radians, and the booking-from-uncommitted-variant pattern). The multi-runtime differential harness
is the same doctrine that caught our census bug by accident — they've made it a first-class layer.

**STEAL/CONSUME — quilt-research-canons is a RUNNING fleet scout organ**
Scout commits at 07:32Z / 10:30Z / 13:33Z today. They ALREADY flagged (10:30Z): "quilt-gpu-lab receipt layer
RED on main" (our phantom seal — since repaired), and (13:33Z) "superinstance-api .wrangler STILL TRACKED
despite .gitignore" (a half-fix from an earlier pass), plus measurement-trap and size-is-a-lie findings.
=> We should CONSUME their reports as queue input instead of re-sweeping from scratch, and cross-check their
findings against our assets. They are the fleet's scout organ; we should be the fleet's GPU lab consuming it.

**CORROBORATE — substrate-foundation "all eleven canon opcodes were undefined at runtime"**
Same defect class as our qcell_sim missing the `crx` gate (caught by the QG2 anchor): the tool's vocabulary
did not cover the corpus's. Two independent instances => make it a fire-time PIN, not a habit.

**CHECK/CONTRADICT-CANDIDATE — xruntime-conformance parts 4-5**
"micrograd-quilt records the same six opcodes as a TAPE, not a cell graph — and that difference decides whether
fault localisation is even possible." If fault localisation is impossible in cell-graph form, our cell-mesh
ledger + QO2 routing claims need an explicit caveat. Worth a deep read before it bites a booking.

**CORROBORATE — pong-quilt CI red root-caused as ENVIRONMENTAL** (build-then-test ordering; fresh site/dist
seal required before the suite). Matches the scout lane's earlier note. Not our bug, not our action item.

**OTHER** — AI-Writings d155 "ML-in-quilt: the forward pass as a priced cell graph" (steal candidate for the
cell-mesh economics); quilt-atlas wave-66/67 publishing census (5106 repos, releases status); Syzygy wave-69
Pages deploy; consul-client housekeeping only. quilt-gpu-lab PR #3 (merged) added G7/G1/G3 to OUR queue —
other agents are feeding us; keep the handshake lane warm.

**QUEUE ITEMS SPAWNED (concrete):**
- [ ] **RC-1 differential receipt harness** (CPU, ~1h): for every booked result, run the COMMITTED script against
  the COMMITTED results automatically (the manual check that found the census radians bug), and wire the
  percept-plugs D-1..D-4 defect classes into our manifest guard. Closes the experiment-booking gap (dirty-tree
  class). Improves: receipt doctrine, all booked results.
- [ ] **SC-1 consume quilt-research-canons** (CPU, ~30m): pull their scout commits, extract every finding that
  touches our assets, convert to queue items; stop duplicating full-org sweeps. Improves: scout efficiency,
  cross-fleet leverage.
- [ ] **VP-1 vocabulary-completeness pin** (CPU, ~30m): at fire time, assert tool gate vocabulary >= corpus gate
  vocabulary (fail loud). Improves: qcell_sim class (crx miss), substrate-foundation's eleven-opcode class.
- [ ] **XR-1 tape-vs-cell-graph fault-localisation read** (CPU, ~45m): read xruntime-conformance parts 1-5;
  test whether our cell-mesh ledger admits fault localisation; write the caveat or the counter-argument.
- [IN-PROGRESS 08:1x] **W5b** (pre-reg 0757ad6): FIRED 07:35 by prior wake, run STILL LIVE (PID 20070,
  ~37 min elapsed, seed 4243 pending, ETA ~08:35). Next wake: check completion, book honestly vs the frozen
  gates (margin 0.5% lifetime-vs-random, antirank secondary), re-seal manifest. DO NOT re-fire.
- [IN-PROGRESS] RC-1 / SC-1 / VP-1 / XR-1 (spawned by SCOUT-2, unclaimed).

## DAY BOOKKEEPING 08:1x (conductor)
- W5b found live-and-unbooked (QO6 pattern #2): prior wake fired pre-reg 0757ad6 and died before booking.
  Smoke gate PASS (nn.GRU equivalence 2.8e-16). Left running; booking deferred to completion (next wake).
- Mandatory reproduction check (C): QG1c committed script re-run -> results.json IDENTICAL to committed
  booking (bit-exact). First clean bill under the new mandatory rule. Prior dirty-tree instances stand.
- Stray `results/qg7_gen_asymmetry_run.log` (untracked debris from the QG7 crashed fire-1) archived to
  `_archive/qg7_gen_asymmetry_run.log.stray-20260930` (archive-never-delete).
- GPU lane occupied by W5b all slice; no new GPU item fired. Rotation next wake: book W5b (GPU-free, just
  verdict vs frozen gates), then PR-SWEEP #6 or SCOUT item per queue order.

- [DONE 08:3x GPU] **W5b BOOKED-pending (results.json written; 09:15 cron books): verdict KILL** — lifetime-ranked precision allocation is seed-dependent (4241 +10.0% best arm; 4242/43 WORST arm, mean_rel -1.05%, wins 1/3). M11's abstraction does NOT transfer to from-scratch ternary in our regime. BUT pre-registered secondary: antirank beat random 3/3 (+2.5/+1.65/+3.0%) — instability, not persistence, may mark precision-worthiness. W5b2 (antirank-primacy, 5 fresh seeds, gates >=0.5% and >=4/5) FIRED 08:4x as a new pre-reg — two-sided design paying off exactly as designed.

- [DONE 08:5x CPU] **W5a BOOKED: verdict REFUTED** — at MATCHED observation budget, trace-reading matches fresh re-observation (0/24 primary
  cells fresh beats trace by >2pp; overall 0.01pp; no consistent direction). QO6 keeps the substrate claim (accumulators over tail predicates)
  but LOSES the claim that trace-reading is strictly dominated in the mildly-lossy regime. Honest flag booked: the frozen verdict function scored
  det_err ONLY and det_err is saturated (max-|stat| detector fires ~always — false-alarm rate ~1.0 on the 4 no-drift cells, 0.0 on every drift
  cell), so REFUTED was forced by saturation; the audit over the pre-reg's other two registered metrics (sign +0.42pp, |t0|>10 +0.12pp, both mixed
  direction) corroborates it => low-power REFUTED, no re-roll. Signal that survives: the FULL-power freshfull arm beats trace by 4.0pp mean on
  |t0|>10 — the advantage is bought by budget, not by re-observation (exactly the REFUTED clause). Pre-reg proposals/runs/W5a-reobserve-vs-trace.md.
- [DONE 08:5x CPU] **F1 BOOKED: verdict PREMISE-ABSENT** — the mined DeltaF-admission composition's regime does not reproduce. G1 passes only
  DEGENERATELY (df == pfifo to 9 sig figs, identical frac_started — the u - T*z_d key essentially never changed the served job); G2 FAIL
  (variance ratio 0.9999994 vs <=0.6); premise r_pfifo 1.001 << 3.0 (no depth-4 blowup to eliminate under FIFO); G4 CONTRADICTED (slack 6.5%
  FASTER, not the claimed >=15% slower). Diagnosed cause: the frozen sim is load-saturated (~24.1k arrivals vs ~13.3k completions; 55% start;
  mean wait ~6756 ticks) so policy differences are invisible in the mean. Slack did redistribute wait hard by depth (r=6.48) — real tradeoff,
  opposite sign to the claim. Carry forward: fix the load (or report per-depth) before any admission-policy measurement. Pre-reg
  proposals/runs/F1-df-admission.md. QUEUE lines marked, RESULTS.md booked, manifest re-sealed.

- [DONE 09:1x SCOUT-4 (day-conductor, non-GPU — rotation honored; GPU lane occupied by live W5b2)]
  Fleet push sweep, 20 repos by recency + canons scout reports + open PRs. Full text:
  proposals/runs/SCOUT-4-fleet-push-2026-09-30-1711Z.md. **HEADLINE — CONTRADICT: the JEV oracle is
  NULL.** New repo `murmuration` (created 15:26Z today; "a null result for JEV as an oracle") ships
  jev_control.json where **positive "2+2=4" and negative "2+2=5" both return argmax=unclear at
  0.74/0.79** — a positive control and its negation read the SAME. Our whole DECIDE-1 lineage reads
  jeff's answer distribution as signal (DECIDE-1b fitted temp 1.1289; DECIDE-1d named
  "representation-locked argmin"; DECIDE-2 proposes surgery on its hidden states). Threat named:
  the below-chance G2 (5/64) and the temperature pinned-at-6.0 boundary may be a BROKEN CALIBRATOR,
  not an inverted mechanism. Caveat: their control is jev-1.13.0, ours jeff-0.8b — threat, not
  refutation. Spawned **QC-JEV** (must fire before DECIDE-2).
  Other finds: STEAL murmuration `std==0 ⇒ INCONCLUSIVE never PASSED` (our mirror instances: QO5 g0
  AUC exactly 0.500, F1 G1 degenerate pass, W5a saturation) → spawned **DEGENERATE gate verdict**;
  STEAL cellgraph witness-width (hash input narrower than computation ⇒ blind witness) → spawned
  **WIT-1**; STEAL canons `pagination_cap_hit` completeness-bounds (their sort=pushed census
  silently overlapped 773 repos!) → spawned **RC-2**; canons mutation-tested OUR receipt layer and
  it FAILED correctly (RED on one comment, restored green) — independent stranger verification, and
  their follow-up == our dirty-tree class → spawned **RC-3 sealer --require-clean** (two independent
  asks, do it); 3 repos adopted wave-67 history-independent CI (better than our fetch-depth:0 fix
  for pong-quilt#84); percept-plugs v0.4 EKN e-calibrated kNN → spawned **QO8**; quilt-neighbourhood
  v0.2/v0.3 (basin-merge honest FAIL corroborates our QG3 basin law; DID overlay keeps revisions
  value-pure). Also: canons verified OUR lucineer-system (161 tests exact, 502k words) but flags
  1 commit / no inspectable provenance. quilt-gpu-lab has NO fleet canary (1-of-10 repos carry it).
  GPU: W5b2 live all slice (PID 21187); no GPU item fired. Rotation next wake: book W5b2 verdict
  (10:25 AK), then QG1d or QG4.

## SCOUT-4 SPAWNED ITEMS (concrete)
- [ ] **QC-JEV discriminating-control pin** (CPU ~5m, no GPU): run "2+2=4" vs "2+2=5" against OUR
  jeff-0.8b. GATE: if argmax identical AND both max-probs within 0.10 → oracle non-discriminating,
  DECIDE-2 premise VOID, DECIDE-1 G2 re-read as calibrator defect. MUST fire before DECIDE-2.
- [ ] **RC-2 completeness-bounds field** (CPU ~30m): `bound` + `bound_hit` on result receipts
  (canons pagination_cap_hit pattern).
- [ ] **RC-3 sealer `--require-clean`** (CPU ~30m): refuse to seal dirty sealed paths at seal time.
- [ ] **DEGENERATE gate verdict** (CPU ~30m): zero-variance gate statistic → DEGENERATE, not PASS
  (F1 G1, QO5 g0, W5a saturation all this shape).
- [ ] **WIT-1 witness-width digest** (CPU ~30m): digest input domain (dtype/runtime/device) INSIDE
  the hash — cellgraph's blind-witness fix.
- [ ] **QO8 e-calibrated oracle readout** (GPU, read-first): percept-plugs v0.4 EKN over (cv,v,gen).

## DAY BOOKKEEPING 09:1x (conductor) — ENVIRONMENTAL RED: /tmp tmpfs FULL
- **FAIL-LOUD ANCHOR: `/tmp` is a 7.9G tmpfs at 100% used, 0 avail.** Root mount `/` is fine
  (1007G, 14%, 825G free). Culprits all transient installer debris, none of it results:
  `/tmp/ollama-new{,.tgz,.tar.zst}` = 4.5G (ollama 0.35.1-rc0 already installed at
  ~/.local/bin/ollama — the payload is spent), `/tmp/cuda12` 1.2G + `/tmp/cudanvcc` 979M (conda
  CUDA extracts, Sep 29 22:0x), `/tmp/jparts` 644M (download fragments, Sep 30 00:4x).
- **How it bit us:** the mandatory (C) reproduction check on W5a died mid-write with
  `tail: No space left on device` — i.e. **the bookkeeping regime itself is now exposed to disk
  exhaustion**, and worse, the first attempt **partially overwrote the committed
  `results/w5a_reobserve_vs_trace/results.json` (mtime 09:13) before failing.** `git diff` confirms
  the content is byte-identical to HEAD (no drift landed) — but this is the dirty-tree class again,
  this time *caused by the verification step*.
- **Mitigation applied (no deletion, per archive-never-delete + shared-machine caution):** the
  re-run was redirected to the WORKSPACE (ext4, 825G free) instead of results/, with a saved
  reference copy of the committed results.json (`/home/eileen/w5a_committed_ref.json`, sha
  ad99c3d6395bbc8d) to diff against. **NOT deleting tmpfs debris** — it is outside the workspace,
  ephemeral by nature, and belongs to the machine owner's session (Casey's ollama/CUDA work from
  last night). Flagging for Casey rather than clearing: reclaim would be ~7G from the four paths
  above and is his call.
- **Recommendation for the protocol:** the reproduction check must write its output OUTSIDE the
  results tree (or to a scratch dir on ext4) and diff — never let a verification run write over the
  artifact it is verifying. Adding to RC-1's spec.

### (C) MANDATORY REPRODUCTION CHECK — 09:1x: **W5a PASS (bit-exact)**
- Re-ran the COMMITTED `experiments/w5a_reobserve_vs_trace.py` (sha256 271a6251f592acb0…,
  the pin in the booking). Output `results/w5a_reobserve_vs_trace/results.json` sha256
  **ad99c3d6395bbc8d1c75** — **identical to the committed reference** (deep-compared: verdict
  REFUTED, overall_pp 0.01, 0/24 cells, all 24 per-cell values equal). Second clean bill under the
  mandatory rule (QG1c was the first).
- **Tooling defect exposed:** the script **hardcodes its output path** into `results/`, so
  redirecting stdout does not keep a verification run off the artifact it verifies — my first
  attempt (killed by the full tmpfs) had already touched the committed results.json before dying.
  Content survived (git diff empty), but the safe pattern is a `--out` flag or a scratch dir in
  RC-1's spec. Added.
- Manifest re-sealed after the ledger change: `sealed: RESULTS.md e73cf253… QUEUE.md 2c197fa9…,
  121 experiment file(s), 18 tool/weight file(s)`; `unittest discover -s tests` → **6 tests OK**.

- [DONE 09:1x GPU] **W5b BOOKED: verdict KILL** — booking one-shot verified results.json against the frozen pre-reg and booked honestly. Gate arithmetic: mean relative bpb improvement of lifetime over random = **-1.05%** (needs >= +0.5%), wins **1/3** seed-pairs (needs >=2/3). Pairs: 4241 +10.00% (lifetime best arm) / 4242 **-9.97%** / 4243 **-3.19%** (lifetime worst arm in both) => direction failure, not a margin near-miss. Mean bpb order: antirank 9.52182 < random 9.75758 < lifetime 9.81828 < uniform 9.95739 (uniform worst 3/3 — the layout-stride confound the pre-reg flagged). Pre-registered SECONDARY (exploratory, NO gate): antirank beat random 3/3 (+2.51/+1.65/+3.01%) and lifetime 2/3 (bpb deltas +0.774/-1.049/-0.614) — the predicted inversion is visible (instability, not persistence, marks precision-worthiness in this regime), but it carries no verdict from W5b; W5b2 (5 fresh seeds, gates >=0.5% and >=4/5) is the confirmation and is in flight. Honest notes: 161 warmup commits make change_count coarse; HP budget identical (19345) across arms so budget equality is clean; no re-roll, no blind re-run. Pre-reg proposals/runs/W5b-lifetime-precision.md. QUEUE line added (backfill class of D18/c9b39b4 — W5b was spooled but never claimed in QUEUE), RESULTS.md booked, manifest re-sealed.

- [DONE 10:2x CPU] **QC-JEV BOOKED: verdict DISCRIMINATING** — jeff-0.8b separates "2+2=4" (p_true 0.9606) from
  "2+2=5" (p_true 0.0243), d_ptrue 0.936; both choice probes follow CONTENT with options swapped/letters fixed.
  **The murmuration JEV null (jev-1.13.0, pos and neg both argmax=unclear) does NOT transfer to our checkpoint.**
  SCOUT-4's CONTRADICT threat to DECIDE-1 is DISMISSED for jeff-0.8b; **DECIDE-2 premise STANDS**; DECIDE-1 G2
  stays booked (below-chance balance-edit read on a demonstrably-discriminating head is lane information, not a
  broken calibrator). Standing flag narrowed: temp-1.1289 / fitted-T-at-6.0 boundary is now a BALANCE-EDIT-LANE
  flag only, not an oracle-wide doubt. 1 mechanical crash pre-scoring (noul branch returns scalar, not dict),
  fixed in place (802bae1). Pre-reg proposals/runs/QC-JEV-discriminating-control.md; RESULTS.md booked.
  - [spawned by QC-JEV] **QC-JEV2** (CPU ~10m, LOW priority): same 4 probes against a SECOND jeff checkpoint
    (jeff-2b/jeff-1b if present locally) + one ambiguous control ("2+2≈4" / a genuinely unclear claim) so we
    can pin WHERE the unclear band sits. Only if local weights exist — no new downloads for a sanity pin.
  - [NOTE for Casey, day item] murmuration's jev-1.13.0 null is a REAL finding about that artifact and it lands
    on DECIDE-2's design too: any head-retrain must ship a discriminating control in its own receipt. Add to
    DECIDE-2's spec before firing.
  - Rotation: QC-JEV was CPU, so next wake takes a non-GPU PR-SWEEP/SCOUT or an open CPU item (RC-3 sealer
    --require-clean and DEGENERATE-gate-verdict are both cheap and unclaimed); GPU lane free all slice.

## DAY SLICE 10:1x-10:4x (day-conductor) — QC-JEV BOOKED; bookkeeping yielded the real find
- **(B) TOP ITEM: QC-JEV fired + BOOKED — DISCRIMINATING.** The SCOUT-4 CONTRADICT (murmuration's jev-1.13.0
  null: positive and negative arithmetic probes both argmax=unclear) does **NOT** transfer to jeff-0.8b:
  p_true 0.9606 ("2+2=4") vs 0.0243 ("2+2=5"), d_ptrue 0.936, both letter-fixed choice probes follow content.
  **DECIDE-2 premise STANDS; DECIDE-1 G2 stays booked as lane information, not a broken calibrator.** The
  temp-1.1289 / fitted-T-6.0 boundary flag is narrowed to the balance-edit lane only. Spawned QC-JEV2 (low).
- **(C) BOOKKEEPING — TWO REAL FINDS, both the silent-edit class the fleet keeps hitting:**
  1. **The sealer refused to seal** (dirty RESULTS.md + two untracked strays) — working exactly as designed;
     the 09:1x `--require-clean` ask is already satisfied by existing behavior in this repo (worth noting in RC-3).
  2. **`results/qc_jev_control/` was UNTRACKED while I sealed the manifest** — the seal had pinned a runner
     whose result artifact was never committed. Caught by checking `git status` after the seal. Committed,
     re-sealed. This is the D-2 silent-edit class appearing in MY OWN slice: the seal does not verify that
     the artifacts it names are tracked. **New RC-3 spec item: seal must assert every referenced artifact is
     tracked at the sealed commit.**
- **Reproduction check (mandatory): QC-JEV verdict + all gates reproduce; byte-identity claim WITHDRAWN honestly**
  (my reference copy was taken after an earlier same-sweep re-fire had already overwritten the artifact, so the
  diff was uninformative by construction). The artifact's embedded `runner_sha256` does equal the committed
  script's hash, and `_latency_ms` demonstrably varies between fires ⇒ the artifact is not byte-stable, and I
  did NOT claim otherwise. **Tooling defect (3rd instance): hardcoded results/ output path — the verification
  run overwrote the artifact under test.** RC-1 spec item stands: every runner needs `--out`; verification
  writes to ext4 scratch, never into results/.
- Strays handled (archive-never-delete): `tools/deepinfra_ideate.py` (DeepInfra revoked) → archived to
  `_archive/deepinfra_ideate.py.stray-20260930`; `tools/local_jev_bench.py` (serves the live JEV question)
  → COMMITTED rather than archived, with an honest commit message naming it as not-mine.
- **GPU lane free the whole slice; no GPU item fired (rotation: QC-JEV was CPU).** Next wake: non-GPU per
  rotation — PR-SWEEP #6 or the cheap unclaimed CPU items (RC-3 sealer `--require-clean`+tracked-artifact
  assert, DEGENERATE gate verdict, RC-2 completeness-bounds). GPU: QG1d recon follow-up or QG4 phase diagram.
- Commits: 10b661f (pre-reg+runner), 802bae1 (crash fix), 73377fd (booked+result artifact), a75b2fb (re-seal).

## DAY SLICE 10:25 (booking cron) — W5b2 BOOKED: **KEEP** (confirmation-grade); missing spool row backfilled
- **Idempotent check FIRST (no double-book).** RESULTS.md + QUEUE.md already carry the W5b2 booking from the
  09:44 wake (commit 7706ec7, "BOOKED: W5b2 KEEP (+8.35% 4/5, confirmation-grade — antirank default)").
  `results/w5b2_antirank_primacy/{results.json,run.log,smoke_results.json}` + the runner are all tracked,
  the manifest is in sync (`unittest discover -s tests` → **6 tests OK**), tree clean at HEAD 90a36b1 with
  nothing unpushed. So: **no re-book, no re-run, no re-fire** — verified against the frozen gates instead.
- **Gate arithmetic re-derived independently from the committed results.json: verdict KEEP, honestly.**
  Frozen gate (proposals/runs/W5b2-antirank-primacy.md): KEEP iff mean rel bpb improvement antirank-over-random
  >= 0.5% AND wins >= 4/5. Measured: mean_rel = **+8.35%** (gate >= +0.5%) and wins **4/5** (gate >= 4/5).
  Pair detail (rel = (random − antirank)/random): 5291 **+20.76%**, 5292 **+15.39%**, 5293 **−3.59%** (the
  only loss; also the worst warmup fork, bpb 6.488 — booked as an observation, never adjusted for), 5294
  **+4.00%**, 5295 **+5.21%**. Budget equality clean: hp == 19345 for every arm, identical data order/fresh
  optimizer per seed. No re-roll, no blind re-run.
- **Tie-back to W5b (the two-sided design paying off):** W5b KILLed the *primary* (lifetime/persistence
  allocation) at mean_rel **−1.05%**, wins **1/3**, and seed sign-flip (lifetime was the BEST arm at 4241
  +10.0%, the WORST at 4242 −9.97% / 4243 −3.19%), while its pre-registered *ungated secondary* showed
  antirank over random **3/3** (+2.51/+1.65/+3.01%). W5b2 is that secondary promoted to a NEW directional
  pre-reg on fresh seeds (5291–5295, zero overlap with 4241–4243) — and it confirms: **instability, not
  persistence, marks which weights deserve the exact slots** in our regime. Doctrine landing: precision
  allocation defaults to commit-count-ASCENDING (shortest-lived first).
- **Fail-loud / honest notes:**
  1. **The spool row for this booking was MISSING.** The 09:44 wake booked RESULTS.md + QUEUE.md and skipped
     the append-only FINDINGS/DAY log; caught by re-reading the spool instead of trusting the commit message
     (same "check, don't assume" reflex as the QO6 live-unbooked and the QC-JEV untracked-artifact finds).
     This cron backfills it; the booking itself needed nothing.
  2. **4th witness of the hardcoded-output-path defect:** `experiments/w5b2_antirank_primacy.py` writes to a
     fixed `OUT = results/w5b2_antirank_primacy` with no `--out`, so any verification re-run would overwrite
     the artifact it verifies (after W5a and qc_jev_control, which did overwrite). RC-1 spec item stands:
     every runner takes `--out`; verification writes to ext4 scratch, never into `results/`.
  3. Scope honesty: one corpus, one architecture (GRU-384) — the KEEP claims "reproducible in OUR regime,"
     not generality. 161 warmup commits keep change_count coarse (the pre-reg's accepted risk).
- No re-roll, no re-run, no re-fire. GPU lane free after this slice.
