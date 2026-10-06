# SCOUT-49 — fleet push sweep, 2026-10-06 04:15Z (20:1x AKDT day-conductor)

Window: post-SCOUT-48 (02:1xZ Oct 6). Method: /users/SuperInstance/events push feed + per-repo
commits since window + open PR/issue search. Read-only; nothing filed.

## HEADLINE — SCOUT-48's lobster-live watch FIRED: taskable-lobster is LIVE
- dafcf82d PoC deploy: **signed Git task queue** (`tasks/task_sign.py`) — HMAC-SHA256 over canonical
  JSON (sorted keys, compact, UTF-8), secret in env, "The signature is the leash: only signed tasks
  execute." Constant-time verify.
- a4166d1e user-vs-org repo-creation endpoint fix (honest fail-loud fix, no silent shim); 50d238b9
  run 37398497315 — **3 repos created and verified live**: brief-assembler ("morning briefing
  overnight research loop"), stream-curator ("gold/shit scoring, taste distillation"),
  ledger-continuity ("the ledger outlives the agent — minimal ledger pattern for agent crash recovery").
- Classification: **TOOL/STEAL**. The signed-task pattern is the same doctrine as our pre-registration
  (a frozen gate that cannot be silently edited between pre-reg and fire = D-2 silent-edit defense for
  prereg FILES, not just results). ledger-continuity is a fleet-side statement of our crash-recovery
  spool discipline (the 05:5x QO6 uncommitted-wake lesson, generalized).
- Spawned **SIG-1** (CPU ~20m, pre-reg-light): HMAC prereg seals — at prereg commit time, write
  `prereg.sig` (HMAC over canonical prereg bytes, key in env local-only); driver refuses to fire on
  mismatch (`--check` mode + fail-loud refusal; no new secret handling beyond env). Gate: negative
  control (tampered prereg refuses) fires RED-first before the green path lands.

## Everything else: QUIET
- lobster-live pushes above; MicroMoth-quilt / pong-quilt: zero commits in window.
- Open PRs fleet-wide: only dependabot groups (model-registry-archive #3, SmartCRDT #77-80). No new
  issues; [EMBASSY] pong #49 unchanged (Casey day item).
- No CONTRADICT this sweep — QO2 routing stack, DET lane, receipt-manifest doctrine, QG3+QG6 time-law,
  QG1c swap census, W5a/W5b/W5c edge-mine seeds all unthreatened. IONQ-2 pins were already confirmed
  third-party-consumed in SCOUT-46; nothing new touches them.

## (C) bookkeeping — DET-1c evidence gap FOUND AND CLOSED (same slice)
- Newest OURS booking = DET-1c (7f6d927, 19:2x). Mandatory repro: **full 6-arm re-run infeasible in a
  20-min slice** (multi-hour qlora fine-tune). Verdict-level: committed driver `experiments/det1c_replicate.sh`
  + `gen_task_pool_excluding` are the exact committed code that produced the booked numbers (fired under
  prereg 65a168c, both driver deaths logged in-spool); deterministic C2 arms make full repro cheap to
  schedule later, but NOT this slice.
- **D-2-class instance on OUR booking found during (C)**: commit 7f6d927 landed only RESULTS.md +
  det1c.log — the per-seed verdict JSONs (rest_em_s*_T/C2.json) and all 6 adapter dirs were left
  UNTRACKED. Gate evidence (per-seed Δ) lived only in uncommitted files. Closed this slice: all of
  results/det1c/ (18 MB) committed. Lesson for FW-1-successor: the booking-completeness check must
  verify that files CITED in the booking text are TRACKED at the booking commit, not merely present.
- Manifest re-seal: attempted post-commit; expected refusal if foreign untracked lanes persist
  (d12u4/d12u5 scratch files + foreign live lanes) — refusal is booked per d23b precedent either way.

Rotation next wake: (B) SIG-1 or DET-1d (needs new prereg first) or GPU QG1d/QG4/MC-1 per queue order.
