# GPP-1 — git.pp judgment-log vs our booking schema (2026-10-09 10:4x AKDT, docs-only, read-only)

Source: SuperInstance/git.pp @ 41049a4/7a6de6e/9157c65, PR #1 (merged), PR #2 (open, read not filed).
Read: `jlog.py` (212 L), `pre-receive` (104 L, "the remote's only law"), `post-receive` (8 L), PR #2 body.
Spawned by SCOUT-85. Gate: every our-booking field has a jlog counterpart or a named reason it doesn't.

## What git.pp is (one paragraph)
Git as the database for agent coordination. `main` = append-only, signed, one-writer-per-path;
`refs/log/judgments/<body>` = per-agent append-only judgment logs (never checked out, plumbing-only
writes, add-only batch files); `refs/heartbeat/<body>` = liveness with policy lease. The pre-receive
hook is the trust root and is explicitly NOT part of the tree's authority.

## THE headline transferable rule
**"Every commit is judged by its PARENT's soul/allowed_signers and soul/policy, so no commit can
authorize itself."** This is prereg-before-fire (D-2/SS-1 lineage) as HOOK LAW: authorization comes
from state strictly before the claim. 5th fleet witness that decision receipts are converging on
enforced-not-voluntary (SCOUT-85 read confirmed by direct source read). Our analog would be: a
booking commit is only valid if its prereg blob (spec_sha pin) exists at the parent commit —
enforceable today by CI, not by a receive hook (we don't own the remote).

## Field mapping (our RESULTS/prereg booking schema → jlog v2 line)
`ts subject question judge neg zero pos sel prop [k=v ...]`

| our field | jlog counterpart | note |
|---|---|---|
| booking timestamp | `ts` (ISO8601, regex-validated) | exact |
| booking commit SHA | `subject` (blob hash, hex) | exact in spirit; theirs hashes content, ours cites commit |
| frozen prereg / spec_sha pin | `question` (blob hash) | exact — the frozen claim content, pinned by hash |
| instrument/tool digest (RECEIPT-HASH tool_pins) | `judge` — **v2 requires judge to be a BLOB HASH** (v0 allowed names) | exact and sharper: the judging instrument IS pinned by content in every line, not in a side manifest |
| verdict GREEN/RED/KEEP/INSUFFICIENT/INCONCLUSIVE | `neg/zero/pos` ternary probability triple, sum≈1 | PARTIAL/named gap: their verdicts are probabilistic ternary; our named verdicts carry row-semantics (STOP rule, retraction class, INSUFFICIENT≠FAIL) that don't compress to 3 numbers. Would live in `extra` (`verdict=...`) — lossy unless schema'd |
| honest caveats / anchors | `extra key=value` (lowercase-id regex, sorted) | exact shape |
| booked evidence files (results/*.json tracked) | no counterpart — jlog lines are self-contained; batch FILES are the storage but hold only lines | named gap: our bookings cite tracked artifacts; theirs cite nothing outside the log. Theirs is tamper-tighter, ours is evidence-richer |
| slot taxonomy (scout/GPU/docs/CPU) | `sel` ∈ stream/shadow/explore/audit/drill/appeal/flag | partial: `drill` maps to our red-first negative controls; `shadow` maps to arm-B controls; `appeal`/`flag` have no ours counterpart (retraction-in-place is our convention, no appeal lane) |
| proposer weight `prop` ∈ (0,1] | no counterpart | named gap: we have no per-claim confidence weight; QO7-adjacent |

## Enforcement inventory (what the hook enforces that we do socially)
- append-only logs, never deleted, must start from own root, add-only files, no merges = our
  archive-never-delete + fail-loud booking discipline, as machine law.
- batch names `YYYY/MM/DD/HHMMSS[-k].tsv` collision-free under races (cat-file existence probe) —
  clean concurrency pattern worth stealing for any future shared results lane.
- signed commits (`commit-tree -S`), identity = signing key principal, never author string =
  our PW-1 foreign-lane ambiguity SOLVED by design (we infer foreign lanes from author strings;
  they make identity cryptographic).
- empty-batch rejection; probabilities renormalized at format time; v0 lines read as sel=stream.

## PR #2 (open) — three instruments, read-only take
1. **Audit stream**: keyed-hash selection over content alone (suppressed verdicts sampled like any
   other; judge can't predict audits), seed revealed with log tips; blind FAULT DRILLS with per-
   reviewer catch-rate. → Directly composes with our HSA-1 (hash-selected audits) and adds a row we
   lack: drills (seeded-wrong bookings) with conductor catch-rate. Watch.
2. **Region gate**: conformal singleton, per-region **per-verdict** threshold (design fix forced by
   their e2e test: one threshold per region blurred unreliable −1 verdicts into unsure +1) — clean
   fleet-side restatement of our PARAM-1/TIE-1 tie-case class: gate granularity must match the
   failure axis. Also: track records score judges only on resolutions they didn't produce (our
   "a judge can't certify itself" / DIFFPORT-1 class, again).
3. **Ship gate**: churn-per-region blocking + verdict-diff-before-labels + world-vs-model drift
   decomposition. QO7-adjacent; note only.

## Classification
- **CORROBORATE** (enforced-not-voluntary convergence; D-2/SS-1/HSA-1 lineage; per-verdict gate
  granularity = PARAM-1a/TIE-1 sharpening). **TOOL** (batch-file concurrency, judge-as-blob-hash,
  parent-authorizes rule). **No CONTRADICT** — no booked result threatened (QO2 stack, receipt
  doctrine, QG3+QG6, DETERM-1 eps pins all untouched).
- [spawned, Casey day-item, not filed] **JLOG-1** (policy decision): whether our bookings gain a
  jlog-format sidecar (`sel`/`prop`/extra=verdict) or git.pp gains a projection of RESULTS.md —
  either direction is a schema/policy change on shared surfaces; Casey's call. Everything above is
  the mapping such a decision would start from.

Read-only throughout; nothing filed, no comments, no PRs. No GPU fired (docs slot per rotation).
