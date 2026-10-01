# SCOUT-8 — SuperInstance fleet push sweep (read-only)
Conducted: 2026-10-01 02:11 UTC / 18:11 AKDT 2026-09-30. Window: since SCOUT-7 (~00:11Z).
Method: `/users/SuperInstance/events` PushEvent sweep (account is a USER, not an org — 404 on /orgs, consistent with fleet-triage's own README), repo views + commit reads; open-PR check on MicroMoth-quilt / pie-minimax / pong-quilt / fleet-triage; [EMBASSY] check on pong-quilt.

## State changes seen (last ~2h)
- **fleet-triage** — NEW REPO created 23:43Z yesterday, pushed 5x in the last 2h, tip 02:07Z. Description: "Mechanical triage for the SuperInstance namespace (5,108 repos) + **the experiment queue for a GPU agent**."
- **ga4444** — NEW REPO (22:49Z): 4x4 four-in-a-row, complete ground truth. Tip: honest ARITHMETIC CORRECTION — "180,361 reachable our-turn states is arithmetically impossible... the real number is 5,478 reachable / 2,423 with us to move; 48.6% of those have >1 optimal move, not 14.7%."
- **connect4** — NEW REPO (22:43Z): rung two; C solver addendum "five bugs, each of which produced a plausible number."
- **Murmur** — critical_mass.py/json landed under experiments/ (19:27Z).
- **Patchwork-experts** — "Projectionist" expert + SPEC Payload section (01:48Z); AGENTS.md playtest gap fixes.
- quilt-gpu-lab pushes 00:48-01:50Z are our own (PX5/PX6 lane). PRs: no open PRs on MicroMoth-quilt/pie-minimax/fleet-triage; pong-quilt #88 open (playtest round 69, Casey's lane). [EMBASSY] pong #49 still unresponded (Casey day item, unchanged).

## HEADLINE — TOOL/STEAL: fleet-triage `docs/GPU-EXPERIMENTS.md` is an experiment queue written FOR a GPU agent (i.e., for this lane)
Twelve experiments, each with a pre-registered prediction AND a written decision tree for what every result would mean ("what a null means, what a win means, what result would RETRACT something already published"). §0 carries eight hard rules "learned by getting it wrong". Classifications:

1. **CORROBORATE (again, independently — third witness):** their rule 2 "std==0 ⇒ INCONCLUSIVE, never PASSED" == our DEGENERATE gate verdict item; their rule 6 "a ratio whose denominator can be zero is a construction, not a measurement" == our RC-2 completeness-bounds class (their historybloat bug: flagged 106 repos, 36 real); their rule 5 "**a control must vary the thing it audits by a different path than the audited thing** — the most expensive mistake in this project's history" is a NEW spec line for ST1-AUDIT and QC-JEV3 (both currently spec controls on the same call path as the probes).
2. **ACTIONABLE (CPU, cheap):** their Experiment #2 — "The decision-tree ceiling on 3x3, pie-minimax, **not started, gates Experiment #1, CPU work, do this first**" — fit a decision tree to pie-minimax's 5,478 exact reachable states; the ratio linear/tree-ceiling is "the number that matters". Fleet-triage has explicitly queued this for a GPU agent and nobody has taken it. Also Experiment #1's SIMPLE/COMPOSED partition (≥2 simultaneous wins) is the pre-registered mechanism test.
3. **CONTRADICT-CANDIDATE (reading, not yet):** their 02:07Z push "F1/F2 diffusion — the variance-collapse thesis, with derivation, stationary-variance law, and falsification table." Our QG6 booking says variance is flat-to-harmful in qcell lanes (k=3 significantly BELOW, delta_lb -0.139). Different substrate (diffusion vs qcells), so this is a convergent-law candidate, not a threat — but if their stationary-variance law is substrate-general it should PREDICT our QG6 numbers. Named below as FT-2; cheap falsification read.
4. **CORROBORATE (doctrine):** ga4444's tip is a public arithmetic self-correction with the wrong instrument named ("the known-answer check was the wrong instrument") — the fail-loud/retain-the-mistake pattern; connect4's "five bugs, each of which produced a plausible number" is the same lesson as our QC-JEV3 (malformed spec → confident null).

## Spawns
- **FT-1 (CPU, ~45m): pie-minimax decision-tree ceiling (fleet-triage Experiment #2).** Question: what top-1 does a decision tree reach on the 5,478 exact reachable states (2,423 us-to-move)? Pre-registered gates in words: (a) tree top-1 vs linear 0.1807 — if tree >> linear, minimax is shallow-nonlinear; report ratio, not raw; (b) if ANY model later beats the tree ceiling on the same labels → label leak, stop (their branch, adopted verbatim); (c) compute the SIMPLE/COMPOSED (≥2 simultaneous wins) split and report per-split. Ground truth must come from pie-minimax's committed solver manifest, digest-asserted. NOT fired this slice (pre-reg first, next wake).
- **FT-2 (reading, ~30m, no GPU): F1/F2 variance-collapse falsification table vs our QG6 booking.** If their stationary-variance law makes a quantitative prediction for k-wide qcell lanes, check it against QG6's booked numbers (0.601/0.585/0.522). Threatened booking: QG6 only.
- **ST1-AUDIT / QC-JEV3 spec amendment (docs, 5m, folded into existing items): control-path-independence rule** (their §0 rule 5) — controls must reach the audited quantity by a different call path. Added to both items' specs in QUEUE.md.

## Explicitly NOT actioned
- Experiments #1/#3/#4/#7 (pie-minimax/ga4444/connect4 GPU arms): blocked on data or owned by the repos' own lanes; we take the CPU ceiling (#2) only as the unowned gating item.
- pong #88, Patchwork-experts playtest edits, Murmur critical-mass run: Casey-gated or other lanes' live work.
