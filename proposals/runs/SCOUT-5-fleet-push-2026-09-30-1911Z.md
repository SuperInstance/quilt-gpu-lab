# SCOUT-5 — fleet push sweep, 2026-09-30 ~19:11Z (day-conductor, non-GPU)

Method: `/users/SuperInstance/events` (pushes, last ~8h) + commits API on the 5 hot repos
(jev-fusion, murmuration, voxelglyph, xruntime-conformance, Syzygy) + open PRs on 5 repos +
pong-quilt open issues. Read-only; nothing filed, nothing commented.

## State changes

- **jev-fusion — NEW REPO, being pushed LIVE during this sweep** (commits landing 19:11:27–36Z,
  seconds before the sweep). Contains STEELMAN.md, ideation batch, exp4_selective + results,
  jev_check.py. Self-described: judge cell-selection vs free local-noise heuristic on fields.
- **murmuration — heavy push burst 17:44–18:58Z** (jev_probe.json, jev_probe2.json,
  jev_control.json, exp9, selfdecay, swarm.py/cell.py).
- **voxelglyph — NEW REPO 18:25Z**: syzygy_port.py + luma-collision exps + site. PR #1 OPEN
  (independent stdlib receipt for exp1's provable luma claims, 7 pins) — receipt doctrine again.
- **xruntime-conformance**: parts 3–5 landed 14:45–15:07Z (part 5: eleven undefined canon
  opcodes in substrate-foundation, live defect found+fixed; part 4: tape-vs-cell-graph fork).
  Already covered in SCOUT-4; nothing new beyond 15:07Z.
- **Syzygy**: wave-69 Pages deploy, MARK 219-check refresh. Housekeeping-scale.
- **pong-quilt**: PR #85 OPEN (round 67, coev-quilt writer). PR #84 unchanged since 06:4x sweep.
- No new issues; pong-quilt #49 [EMBASSY] still unresponded (day item for Casey, unchanged).

## Classifications against our live assets

### CORROBORATE (strong) — jev-fusion STEELMAN.md point 3 → QO2/QO6 blind-spot threat
Their steelman: a judge emitting one independent scalar per cell is a **sparse signal that
cannot represent grouped error** ("these twelve cells are wrong *together*"). Their exp4
scattered defects uniformly (least favorable to a per-cell judge) and the judge lost to a free
heuristic; their proposed exp5 = defects in a contiguous cluster.

**This is a named threat to QO2/QO6, not just their problem.** Our oracle scores per-STREAM
(one scalar per stream: cv/v/gen features; QO6 kill gate is per-stream evidence). But QO5
proved all 4096 streams share ONE skeleton draw (g0 states byte-identical) — the failure
structure in our substrate IS grouped at the lane level. If trapping is a lane/landscape
property (QG2 "desert is STRUCTURAL"), then per-stream gen-1 oracle signal may be reading a
lane-level variable with per-stream noise, and per-stream kill decisions may be structurally
blind exactly the way their judge is. Conversely, our QO2 law already routes budget at the
cell/lane level for the desert subpopulation — the doctrine may survive, but nobody has
tested WHERE the signal lives (stream vs lane).

### CORROBORATE — murmuration jev_probe2.json
Their probe2 now shows perfect discrimination (argmax true/false, max 1.0, gap 0.667) while
jev_control.json (jev-1.13.0) still shows the all-unclear null. Consistent with our QC-JEV
verdict: discrimination is artifact-dependent, the null is about jev-1.13.0, not the family.
Our QC-JEV booking needs no amendment.

### STEAL — the STEELMAN.md doctrine itself
"Ask for the best version of the case against us, generated from our own published numbers."
They found their own weakest point (56% below oracle ceiling, noise-equivalence) by
steel-manning against their own dossier. Maps 1:1 onto our pre-reg discipline: a pre-reg
should carry a steelman section BEFORE firing, so the refutation arm is pre-registered, not
post-hoc. Their honest response pattern ("points 1-2 are our own numbers → don't build it,
find the task where it wins") is also exactly our STOP-rule culture — independent
convergence.

### CORROBORATE (minor) — voxelglyph PR #1
Another fleet lane shipping independent stdlib-only receipt verification for its own claims.
Receipt doctrine now near-universal across the fleet.

### WATCH — jev-fusion exp5 (pending; repo mid-push)
If their clustered-defect experiment shows the judge beating the free heuristic ONLY on
grouped errors, that is direct evidence for the QO9 test below (grouping is where per-unit
signals die or live).

## QUEUE ITEMS SPAWNED

- [ ] **QO9 (CONTRADICT-candidate, highest priority; CPU, ~30m, existing data):** WHERE does
  the oracle signal live — stream or lane? Using committed QO3/QG7 per-gen rollout data:
  compute gen-1 oracle AUC (a) across all streams poolwise, vs (b) within-lane only
  (stratify by lane/skeleton). GATES: if within-lane AUC < 0.60 (vs pooled 0.88), the signal
  is LANE-level → QO2 routing must move between cells, per-stream kill evidence (QO6)
  inherits a grouped-error caveat; if within-lane AUC >= 0.80, stream-level routing stands
  and the jev-fusion sparse-signal objection is answered for our substrate. Pre-reg before
  touching data. Threatens bookings: QO3 horizon, QO6 gate, QO7 routing law.
- [ ] **ST-STEEL (pre-fire steelman gate; CPU docs ~20m):** adopt jev-fusion's STEELMAN
  doctrine — every new pre-reg in proposals/runs/ gains a "steelman" section: the strongest
  case against its own premise, derived from our own prior bookings, written BEFORE fire.
  Applies forward; retro-fit only QO9 and W5b2's successor if any.
- [ ] **JF-1 (reading item, low):** when jev-fusion stops pushing, read exp5 clustered-defect
  results + ideation_batch.json; map their judge-vs-free-heuristic operating characteristics
  onto QO6 eproc thresholds. Watch only unless their exp5 flips their own verdict.

## Notes
- GPU lane occupied by ST1 (PID 38353, live) the whole slice — CPU/reading only, per rotation.
- jev-fusion mid-push: do NOT pin hashes from this sweep; everything re-read at JF-1 time.
