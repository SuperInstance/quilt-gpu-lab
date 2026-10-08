# SCOUT-77 — fleet push sweep, window 2026-10-08T20:15Z → 2026-10-08T22:15Z (fired 22:15Z)

Conductor: day cron, (A) slot per rotation (last: A SCOUT-76 12:1x, C 13:1x, B ENDO-1c 11:1x).
Sweep: org-wide pushedAt scan + per-repo commits since 20:15Z. Census: 15 repos pushed today.

## Window pushes (3 external; quilt-gpu-lab ours)
- **deckboss-ai-pages ef76208/0d648d8** (21:56Z, 22:10Z): DeckBoss PWA prototype on deckboss.ai
  replacing log-engine demo; Google Drive not-configured state. UI/Casey territory — WATCH only,
  not a research push.
- **zero-poc 9d28513** (21:27Z): routine autonomous think cycle. No content action.
- **rc-20260824-11 72c4a72** (21:06Z): q22 — the horizon-knob closure. Full classification below.
- Open PRs: unchanged (dependabot-only trains). No new/updated issues in window.

## [EMBASSY] — pong RENAMED to pong-quilt (mystery closed)
`SuperInstance/pong` now 404s; the repo lives at **SuperInstance/pong-quilt** (last push Oct 5,
merged #118/#119/#120). Issue **#49 is intact there**: state=open, 7 comments, updated
2026-09-28 — genuinely unchanged, exactly as every prior scout recorded. Prior slices' "pong #49
unchanged" lines were valid against the renamed path. **RC-2 census drift note:** repo-rename
produced a 404 window that looked like deletion; watched-repo lists must follow redirects
(`gh api` does not follow repo renames). Watched-list update: pong → pong-quilt.
taskable-lobster still 404 (known RC-2 drift, stands).

## CLASSIFY: CONTRADICT COUNT: ZERO
QO2 stack, ENDO-1/1b/1c, EXIT-1, HSA-1b, DETERM-1, PARAM-1, receipt doctrine, QG3+QG6, W5a/b/c
all unthreatened.

## Findings

1. **rc-20260824-11 q22 — horizon knob CLOSED: the optimal gate is the resume clause alone.**
   Limit gate (H=DWELL=20, arm at dwell≥1, no fixed horizon; only observable coverage<SAT
   resume-on-break ends a skip) saves 357/400 dice passes (89.25%) vs H16's 232 at +0.12pp —
   monotone to the boundary, no saturation knee, no inversion. At the limit the gate arms on the
   FIRST saturated tick; safety rides entirely on the resume clause (hash-eviction sawtooth
   guarantees a dip below SAT). Flips unchanged (7-8) across the whole sweep: dice pressure is
   NOT the flip driver, the plateau is. Exo contrast arms 0 at LIMIT — fourth reproduction of
   "anticipation is free only when the universe answers back."
   → **CORROBORATE x2:**
   - **PARAM-1** (gate-parameter validation census): q22 is a worked exemplar of exactly our
     G-class "sweep the parameter to its boundary and prove no inversion" — their boundary-
     monotonicity receipt is the shape PARAM-1 asks us to produce for eproc sigma/budget,
     DETERM-1 eps, verdict_gate thresholds. Cite 72c4a72 in the PARAM-1 pre-reg as the
     reference methodology (pre-registered sweep grid, contrast arm at every point, receipted).
   - **ENDO-1c / QO7a**: "optimal gate = observable-only resume clause, no fixed horizon"
     directly supports our probe-derived-thresholds row (q19 lineage) — threshold should be a
     regime observable, never a clock. New data point for the QO7 pre-reg amendment: their
     limit-gate is dice-silent 89% of the time and recovery still holds (t+0 on sawtooth dip),
     evidence AGAINST a minimum-coverage floor objection. Spawned **QO7a-AMEND** (docs, LOW):
     add the resume-clause-alone row + the "exogenous layer arms 0 times" 4th-reproduction cite
     to the QO7a pre-reg notes.
   - Opens their q23 (are non-dice layers needed on a plateau at all / does recovery-at-t+0
     depend on fixed every-tick pressure elsewhere) — WATCH; if answered, maps onto our
     graceful-degradation sweep gate (ENDO-1b row 4).
2. **pong-quilt rename** — bookkeeping, not research; see EMBASSY section above.
3. deckboss-ai-pages PWA — out of research scope, WATCH.

## Rotation next wake
(C) not due (newest scripted booking HSA-1b REPRO PASS 13:1x same day; census static n=104).
Rotation next wake: (B) PARAM-1 (top cheap, now with q22 methodology cite) or QO7a-AMEND
(cheap docs); GPU open (QG4/QG1d-corpus/MC-1). Foreign d12 untracked lane persists (PW-1);
manifest re-seal still correctly refused/deferred.
