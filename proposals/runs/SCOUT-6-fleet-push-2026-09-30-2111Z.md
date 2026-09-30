# SCOUT-6 — fleet push sweep, 2026-09-30 21:11Z (day-conductor, read-only)

Window: since SCOUT-5 (19:11Z). Method: `gh api users/SuperInstance/events` + per-repo commits
+ open PRs. No writes to any other repo (no comments, no PRs filed).

## State change in the window
- **jev-fusion** — the mover. Two near-identical push WAVES (20:53Z and 20:56Z) of the same file
  list (one commit per file: README/ROADMAP/STEELMAN/PRIOR-ART/FINDINGS/CONVERGENCE + exp4-7 +
  jev_check/ideation_*). Wave pattern = whole-tree re-push; treat as one content state.
- **pong-quilt PR #87 OPEN** ("Round 68: file provenance on the C1 receipts", base r67 tip
  2a00c14, R66/R67 unmerged Casey-gated). #85 open (R67), #86 CLOSED (fetch-depth fix — matches
  our SCOUT-4 root-cause).
- **AI-Writings** — three new "audit lane" slices: "The Beam Finds the Sea" (a control sharing
  its code path cannot detect a fault in that path), "The Smoke Detector With No Battery In It"
  (silent vs broken look identical until something is required), "The Dial That Resolves Less"
  (quantisation is a decision about walls, from the murmuration lane).
- **quilt-research-canons** — scout 19:55Z: vendor-filter correction, "59 empty recovered-copies",
  atlas undercount, **sunset security-workflow unfailable**, 2 verified positives; earlier:
  **sailor-workspace CI neutered by `|| true`**, flux-tensor-midi 3/4 mutations survive.
- quilt-gpu-lab 20:17Z push = our own 12:1x slice. No new PRs against us.

## Classification vs our live assets

### STEAL — pre-experiment verifier gate that REFUSES to run (jev-fusion, FINDINGS.md)
jev-fusion **retracted its own published null** ("the discrete judge does not discriminate") and
diagnosed the cause as a **malformed request**: `state` was an object not a string, and a separate
`options` list was sent alongside `criteria`; there is no `options` field — the option set IS the
criteria keys. Key sentence: *"A malformed spec does not error; it returns a well-formed,
confidently unhelpful answer."* Their remedy: `jev_check.py` re-verifies 5/5 **before every
experiment**, and an experiment **refuses to run if the check fails**.
- Directly ours: this is the fire-time-pin doctrine we booked (VP-1 vocabulary-completeness pin,
  RECEIPT-HASH) but with a sharper failure mode — **a malformed input yields a confident, silent,
  well-formed null, not an exception.** Our QC-JEV booking is *supported* (the murmuration null was
  an artifact; jeff-0.8b discriminates at d_ptrue 0.936) and now has a named mechanism.
- Spawned **QC-JEV3** below.

### CORROBORATE — "a check that cannot fail converts a bug into a finding" (jev-fusion CONVERGENCE + canons 19:55Z)
CONVERGENCE's second law names **eight** instances in three shapes: (1) a control sharing the call
path of the thing it audits (their retracted JEV null — and, independently, AI-Writings' "The Beam
Finds the Sea"); (2) a control shuffling rows that carry their own labels (a tautology reported as
a real result — a false negative); (3) **a pipeline ending in `tail`, which reports the exit code of
the last command — a background task reported SUCCESS having written no file.**
- Our instances of the same class, already booked: F1 G1 degenerate pass; QO5 g0 AUC exactly 0.500;
  W5a det_err saturation; and **the 09:1x tmpfs incident where the reproduction check died mid-write
  with `tail: No space left on device` while the booking was being written**. The `tail` instance is
  not a metaphor for ours — it is ours.
- canons' independent finds are the same law in CI form: **sunset security-workflow unfailable**,
  **sailor-workspace CI neutered by `|| true`**, **3/4 mutations surviving** in flux-tensor-midi.
- Our open item **DEGENERATE gate verdict** is now corroborated by two external lanes (jev-fusion
  and canons) plus three of our own instances. Priority raised; spec widened to include
  "check whose exit code is not the check's" (tail/`|| true` class).
- VP-1 (vocabulary-completeness pin at fire time) gains a second independent rationale.

### CORROBORATE-CONTRADICT-CANDIDATE — the projection law, applied to OUR oracle (jev-fusion CONVERGENCE)
CONVERGENCE states one law: *"What survives is bounded by what the observation carried, and every
observation is a projection. No downstream cleverness recovers what the projection discarded."*
Their instance that touches us: **"one scalar per cell ⇒ the judge cannot represent 'these twelve
cells are wrong *together*'."**
- Applied to us: our QO1/QO3 oracle reads a **per-stream** projection of the champion
  (len, balance, gate histogram, gen). If the desert subpopulation's failure is **grouped at the
  lane level** (all streams share one skeleton draw — QO5), then per-stream features cannot
  represent it, and no downstream cleverness in the oracle recovers it.
- **Does this threaten a booked result?** Checked against the bookings: QO3 booked AUC 0.880 at
  gen 1 rising to 0.999 — signal IS recoverable, so the law does **not** refute the forecast lane.
  But QG7 booked a **P1 FAIL** precisely on the desert subpopulation (gen-1 AUC 0.546–0.663 across
  4 reruns, mean 0.606). Read together: the projection law and QG7 are the SAME finding from two
  directions — **the desert subpopulation is not representable in a per-stream projection**, which
  is why we routed it to the QO6 e-process gate ("evidence, not tail predicates") instead of the
  oracle. **No amendment needed; QO2's architecture is vindicated, and QO9's framing is sharpened.**
- Caveat kept honest: their projection instance is a *rendered image* (much narrower than our
  champion-state vector), so the transfer is analogical, not proven. QO9 is the test.

### STEAL — exp5/exp7: build the control so it CAN fire (jev-fusion)
- **exp5** tested their own steelman ("a sparse per-cell signal cannot represent grouped error")
  with a pre-declared decision rule — judge wins iff it is at-or-below the free heuristic in the
  clustered column. Result: **the steelman's prediction did not hold** (judge better on clustered,
  ~3× the scattered margin), but the honest size is small (0.002–0.006, two seeds, one exact tie).
- **exp7** then attacked their own experiment: the "free" statistic was not actually blind because
  seam cells read the leak. Fix = bilinear upsample from a coarse grid so local disagreement has
  literally nothing to read. Result: **the control fired — the judge wins ~equally on SPLIT and
  CLEAN (split −0.0076/−0.0093 vs clean −0.0060/−0.0082)**, so cross-seam structure is NOT the
  mechanism; the advantage is a general advantage on smooth fields.
- This is the ST-STEEL doctrine already in our queue, executed twice in one repo, and exp7 is the
  strongest worked example of "make the free baseline actually blind before you claim a win."
  Feeds ST-STEEL's spec directly.

### TOOL/CORROBORATE — pong-quilt #87: provenance column asserting a generation the lane never used
Round 68: a receipt row's own **gen column recorded the classic slot while the C1 lane never sets
it** — load a gen-5 coev file at a fresh page, save, and the SAVE row **silently asserts gen 0**.
Their fix scopes the column to the lane and names the file in the LOAD banner. FAIL-first pins
written against the real shipped code (4/4 RED then GREEN); full suite 298 tests / 290 pass / 8
honest skips.
- This is our **D-2 silent-edit class** (three instances booked today), and it is the receipt
  doctrine again: **a provenance field that can assert something the instrument never did.**
  Added to RC-3's spec (assert the claim the receipt makes is one the runner actually produced).

## Queue items spawned
- [ ] **QC-JEV3 — malformed-spec / confident-null pin** (CPU ~30m, pre-reg first): the jev-fusion
  retraction says a malformed request returns a *well-formed, confidently unhelpful* answer. Test on
  OUR jeff lane: send the DECIDE-1 prompt with (a) the option set omitted from the criteria keys and
  (b) a stringified/objectified `state`, and check whether we get a confident wrong answer **with no
  error**. GATE: if a malformed spec silently produces a plausible reading, then every DECIDE-1
  receipt must ship a request-shape assertion (schema-validate the prompt), and the below-chance G2
  (5/64) must be re-examined for request-shape rather than representation-locked argmin.
  Cost ~30m CPU, no GPU.
- [ ] **QO9 (priority RAISED, framing sharpened)** — oracle signal stream-vs-lane stratification.
  Now backed by two independent lanes: jev-fusion's projection law (per-cell scalar cannot represent
  grouped error) + our own QG7 P1 FAIL on the desert subpopulation. Pre-reg question, gates in
  words: measure AUC of the frozen QO1 oracle on a **lane-held-out** split (streams from lane L
  scored by an oracle never trained on L) vs the recorded within-lane AUC; GATE-1: if lane-held-out
  AUC is materially below within-lane (drop > 0.05), the gen-1 signal is partially lane-memorised and
  QO3's horizon claim is a within-lane claim only — book the caveat on QO3/QO7. GATE-2 (secondary,
  exploratory): separately report the desert subpopulation. Existing data, CPU ~30m, no GPU.
- [ ] **DEGENERATE gate verdict (priority RAISED, spec widened)** — add the third shape from
  CONVERGENCE: **a check whose reported status is not the check's own** (pipeline ending in `tail`;
  CI neutered by `|| true`; unfailable security workflow). Plus the zero-variance DEGENERATE rule
  already specified (F1 G1, QO5 g0, W5a saturation). CPU ~30m.

## Not ours / no action
- AI-Writings slices are prose exports of the same audit-lane findings (no code to read).
- canons vendor-filter/59-empty-recovered-copies/atlas-undercount: census completeness bound (feeds
  RC-2's `bound`/`bound_hit` field, already spawned at SCOUT-4); no new item.
- pong-quilt #85/#86/#87: #86 closed (our SCOUT-4 root-cause confirmed by their fix); #85 and #87
  are Casey-gated rounds, untouched.
- [EMBASSY] pong-quilt #49 still unresponded — unchanged day item for Casey, no action taken.

## Rotation note
This slice was (A) SCOUT-6 (non-GPU). GPU lane free all slice; no GPU item fired — correct per
rotation (last GPU item was ST1v2). Next wake: **ST1-AUDIT (CPU, top open item)** or a GPU item
(QG1d follow-up / QG4 phase diagram) if the audit's pre-reg work is claimed first.
