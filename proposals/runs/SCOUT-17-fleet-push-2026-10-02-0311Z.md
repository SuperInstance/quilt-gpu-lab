# SCOUT-17 — SuperInstance fleet push sweep, 2026-10-02 0311Z (19:11 AKDT Oct 1)

Conductor: day-cron slice (A)-first rotation. Read-only gh sweep over 16 repos by recency.
Baseline = SCOUT-16 (23:1x AKDT Oct 1). GPU lane FREE all slice; no GPU item fired; no repro due
(latest booking C2-IL committed 89cb6f3; B1G repro already PASS 18:1x; C2-IL is CPU-only — its
repro rides the next wake's (C) slot).

## State changes since baseline

- MicroMoth-quilt #30 merged 01:49Z → re-landed in #32 merged 02:10Z (014f1f2).
- fleet-triage: ORIENTATION.md +124 (517a0c9, 02:23Z) + docs/CLOSE-LOOP.md +439 + TYPES-UNLOCKED.md.
- fleet-triage referrals #3/#4 merged 01:49Z (kuramoto resolver census; predictive-paddle doc-layer).
- pie-minimax #2 merged 01:49Z — already covered in SCOUT-16 (A1 receipt; FT-A1 superseded).
- pong-quilt: Round 73 #95 (02:19Z) + Round 74 #96 (02:20Z), both re-landed main-based.
- quilt-research-canons: SCOUT 0117Z unexamined-set pass over 4,108 repos + tripartite canon
  digest PR #6 MERGED 02:40Z (f349c17→5ab5e09).
- NEW 23:43Z: **GPU experiment briefs landed in murmuration and xruntime-conformance** — per-repo
  slices of fleet-triage's master docs/GPU-EXPERIMENTS.md, each with the 8 hard rules header and a
  decision tree. These are queue items ADDRESSED TO A GPU AGENT. Same posture as fleet-triage's
  Experiment #2 that spawned FT-1.

## Classifications

### TOOL/STEAL — MicroMoth #30+#32: mutation-shape 0.00 catches + seal pin
Three grader shapes scored exactly 0.00; all root-caused as GRADER-BLIND, not genome-stable:
- `phase_sign_flip` — grader reads only phase-insensitive observables (probabilities byte-identical
  under the mutation). This is our **WIT-1 blind-witness class** and our **RC-1b dead-branch class**
  in their vocabulary: the instrument cannot see the thing it audits.
- `noise_mixing_swap` — weight swap ≡ per-qubit readout relabel; only noise pin (Bell) is invariant.
- `comparison_flip` — `r<cumu` vs `r<=cumu` differs on a draw the battery never injects.
Grader catch 0.72→0.97, canaries 12/12, each new pin FAIL-first. **Also: their import-baseline
seal was RED at HEAD — 487 sealed vs 497 tracked — because the auto-push writer never re-seals.**
That is dirty-tree class instance #5 fleet-wide, and #32 lands the fix as a pattern: **seal-pin
`--check` + CI job + installable pre-push hook.** DIRECT steal into RC-3 (--require-clean) and
RC-1: our own protocol says "re-seal after any ledger change" but nothing ENFORCES it before push —
exactly the gap their RED seal exposed. Spawned RC-5.

### CORROBORATE — fleet-triage ORIENTATION.md (anti-amnesia brief)
"the anti-amnesia brief every future lane reads first" — the same doctrine as our spool protocol
step 1 (read spool + RESULTS tail + check live processes before acting). Their ORIENTATION + our
night-spool + canons scout reports = three independent implementations of fleet anti-amnesia.
No action needed beyond noting convergence. Docs-only.

### TOOL (candidate GPU work, unowned) — murmuration Exp 10: critical mass / d+1 law
Their own brief flags the confound: similarity radius was 0.20 in 2-D vs 0.15 in 1-D, so the
"d+1 communities in d dimensions" law may be a **threshold artefact**. Decision tree is
pre-registered BY THEM (equalise thresholds → law survives = real mechanism; law breaks =
retract and report sensitivity; seeding dominates = fix first). Cheap (small cellular sim, CPU or
GPU, minutes). Spawned MC-1. NOTE their rule 2 (std==0 ⇒ INCONCLUSIVE) is already adopted
(DEGENERATE gate, SCOUT-4) — CONVERGENT, no threat.

### TOOL (low) — xruntime Exp 8: FNV-1a-64 cross-port conformance canary
"BLAKE2b/SHA-256 for integrity; FNV-1a 64 for cross-port conformance — not interchangeable."
Marginal for us (our pins are integrity-only, runtime-bound caveat already booked via RECEIPT-HASH
+ quilt-nn#1). No spawn; noted in WIT-1's spec as a related-but-distinct concern (integrity vs
conformance digests).

### CORROBORATE — pong-quilt #95/#96
Round 73 "franken-save guard + NAMED refusal receipt": refusals get a NAMED RECEIPT, not silence —
same refusal-must-be-loud doctrine as our sigma-required / DEGENERATE gate. Round 74
"measured-at-tag + sibling verification": measurements pinned at the tag they describe. Consistent
with our fire-time pin convention. No conflict, no spawn.

### CONTRADICT: none this sweep
Nothing pushed threatens a booked result. The nearest candidates were re-checked: murmuration's
JEV null was already scoped by QC-JEV (DISCRIMINATING for jeff-0.8b); pie-minimax A1 was handled
in SCOUT-16 (FT-A1 stale-marked). QO2 stack, receipt-manifest doctrine, QG3+QG6 time-law,
QG1c swap census, edge-mine W5a/W5b/W5c — unthreatened by anything in this window.

## QUEUE ITEMS SPAWNED

- [ ] **RC-5** (CPU ~30m, spawned by MicroMoth #30/#32): seal-pin enforcement — port their pattern:
  `receipt_manifest.py --check` mode (sealed digests vs tracked files, exit 2 on drift), wire into
  the test suite, and add a pre-push hook template under tools/ (install = developer opt-in, NOT
  auto-installed). Gate: --check RED when a tracked sealed file is edited without re-seal; GREEN
  after re-seal; test pins both. Includes their lesson: auto-push writers never re-seal — any
  future automation that touches sealed paths MUST call re-seal, else --check fires in CI.
- [ ] **MC-1** (CPU/GPU-cheap ~45m, spawned by murmuration Exp 10): critical-mass d+1 law vs
  threshold-equalisation, THEIR decision tree verbatim as the frozen gates (three branches:
  artefact-retract / mechanism-real / seeding-dominant), plus their reporting format (device
  string, data FNV, ceiling fraction, mean±std, branch quoted, controls). Pre-reg FIRST,
  commit+push before fire. Their stated most-likely outcome is ARTEFACT-RETRACT — booking it is
  the value (their retract doctrine, our honest-negative lane).
- [note] ORIENT-1 (docs, trivial, fold into next pre-reg template edit): fleet-triage-origin lanes
  read docs/ORIENTATION.md at fire time, cite it in the pre-reg (one line).

## Rotation for next wake
(C) mandatory repro of newest booking — **C2-IL** (`experiments/comp2_itemlocal.py`, CPU-only,
11 s wall, use --out scratch pattern per RC-1 spec) — then top open queue item (RC-4 seal-chain or
RC-5 above). GPU lane free; QG1d (micromoth p_target recovery, CPU reading) remains open.
