# PR-HARVEST / CARDS.md

Lane: PR-HARVEST. Project: quilt-gpu-lab (experiment ledger + superinstance-api context brain).
Convention per card: **MECHANISM / OUTCOME / PRIMITIVE / PROBE-4050 / LENS**.
Probe hardware: RTX 4050 6GB, torch 2.14.0+cu126, seed 2718 unless noted. "REPRO" = independent
reproduction of a PR that already ran on comparable (CPU/JS) hardware.
All claims read from PR bodies + diffs pulled 2026-10-01 (read-only `gh`). Nothing posted.
Ordering below: by repo group. Cards written incrementally; partial progress is intentional.

---

# Repo: quilt-in-git (builder lane: "dials are files, ticks are commits, hooks are the runtime")

## quilt-in-git #1 — wave-3: `refs/quilt/HEAD` live position pointer + quilt-head reader

- **MECHANISM.** `post-commit` (the runtime) runs `git update-ref refs/quilt/HEAD HEAD` after
  receipt+cascade+watch, so a *ref* (data) shadows the branch pointer. `quilt-head` reads it back and
  **refuses (exit 1)** on a zero-tick repo rather than falling back to HEAD. Non-head namespaces don't
  travel on plain `git clone` (P8d) — need explicit refspec `+refs/quilt/*:refs/quilt/*` or a bundle.
- **OUTCOME.** Pins P7–P9 FAIL-first RED on `f35caca` (6/9) → 9/9 green; 31 checks 0 fail. Honest
  boundaries pinned as behavior: cascade commits don't move it; default clone drops it.
- **PRIMITIVE.** *A pointer that tracks only recorded ticks, not all commits* — ledger head ≠ repo head.
  The refusal path (no ticks → exit 1) is the honest-absence pattern.
- **PROBE-4050.** REPRO semantics at GPU scale: build a 1M-row synthetic ledger where only 1% of rows
  are "receipted" ticks; a torch index answers "position of last receipted tick" under (a) append
  (b) non-receipt commit (c) tag rewrite. Gate: pointer == last receipted row in 100% of 10k randomized
  op orders AND a naive HEAD-pointer baseline diverges in ≥1 op order. PASS both.
- **LENS.** Optimizing *"the position of truth is recorded; reading it is never a guess."* My ledger
  steals: a **receipted-head index** separate from the raw spool (RESULTS.md is currently "everything";
  a head ref would answer "where did belief last change" without a full scan). Avoid: making refs the
  only store — plain clone silently drops them.

## quilt-in-git #2 — w3b: live-state refs (parentless orphan snapshots)

- **MECHANISM.** Each tick `quilt-publish` builds two parentless `commit-tree` snapshots in a *private
  index* (`read-tree --empty`, reuse committed blobs, `write-tree`, `commit-tree` no parent):
  `refs/quilt/dials` = tree of only `cells/<alias>/dials/*`; `refs/quilt/HEAD` = dials +
  `.quilt/live/last_receipt` + `watch_tail`. Real index/worktree never touched. Dates inherit the tick
  commit ⇒ republish idempotent; refs replaced each tick; stale ones leave via `git gc`.
- **OUTCOME.** FAIL-first RED 6/9 (P10–P12) → GREEN 9/9 / 38 checks. P11 guards the dials tree is
  *dials-only* and HEAD *has* bodies.
- **PRIMITIVE.** **Projection-as-orphan-snapshot**: emit a cheap, bodyless view (vitals) as a
  first-class addressable object, regenerated every tick, never mutated. `git ls-remote` alone reads it.
- **PROBE-4050.** GPU "vitals projection": under a 6GB-tight scoring loop, emit a tiny projected state
  (means/vars/top-k) into a ring buffer each step. Gate: projection read latency ≤1% of step latency AND
  reconstructs the dial vector to ≤1e-3 rel error over 10k steps; memory O(1). PASS both → adopt as the
  ledger's live-state read path.
- **LENS.** *"Other agents should read the fleet in kilobytes, without checking anything out."* Steal: a
  `vitals/<sha>` snapshot on our experiment bus so superinstance-api polls without a full RESULTS read.
  Avoid: assuming the projection is always cheap — here it is; don't generalize.

## quilt-in-git #3 — w3a: notes receipts + signed ticks

- **MECHANISM.** `post-commit` writes `.quilt/receipts/<short>.json` then `git notes --ref=quilt/receipts`
  attaches it to the tick commit (notes are git objects ⇒ travel with fetch/push). Plain clone skips
  `refs/notes/*`, so `quilt-init` wires `+refs/notes/quilt/receipts` into `remote.origin.fetch`.
  `sig` = fnv1a-64 over `receipt-without-sig || committer-ident || commit-tree` — unkeyed, GPG-free.
  `quilt-fnv1a` is pure-POSIX-awk; `quilt-verify` recomputes every noted sig, names drift.
- **OUTCOME.** FAIL-first 6/9 (P7 no note; P8/P9 no file) → 9/9, 41/41 checks. Honest limit stated
  loudly: **unkeyed checksum is re-forgeable — catches transport damage and lazy edits, not adversaries.**
- **PRIMITIVE.** **Receipt rides the object graph, not the worktree** + a self-declared-strength
  signature. The `|| committer-ident || commit-tree` binding binds content→actor→commit.
- **PROBE-4050.** Hash-bind a 50MB shard set with (a) fnv1a-64 content-only vs (b) content‖actor‖commit-id.
  Gate: tamper by swapping actor AND content between two shards — (a) must collide/re-forge ≥1, (b) must
  name the exact shard 100%. PASS if (b)==100% and (a) fails ≥1/50. Falsifies "binding adds nothing."
- **LENS.** *"Honesty about what the signature can't do."* Steal: bind our ledger rows to
  (policy-version ‖ host ‖ run-id), not just content — our RESULTS rows are content-only so a moved row
  is indistinguishable. Avoid: calling fnv1a a signature anywhere it faces an adversary.

## quilt-in-git #4 — w3c: bundle air-gap transport + sparse-checkout focus

- **MECHANISM.** `quilt-export <path>` writes a complete `git bundle` (branch + HEAD + every
  `refs/quilt/*`); `quilt-import` verifies it, fetches the refs a plain clone misses, checks out the
  bundled branch, re-runs `quilt-init`, then **regenerates the journal from pure history** (walk every
  commit oldest-first, re-run deterministic receipt logic) and verifies byte-identity to the bundled
  journal. `demos/airgap.sh` exports, `rm -rf`s the original, imports on the far side. Focus =
  `quilt-focus <alias>` sparse-checkout of one organ. Required a real fix: wave-2 `quilt-cascade` read
  the **worktree**, so under focus it silently saw only the focused cell; now reads the **index**
  (`git show :cells/...`), writing out-of-focus updates via `update-index --cacheinfo` +
  `--skip-worktree` re-apply (cacheinfo alone leaves a phantom deletion).
- **OUTCOME.** Pins 0/3 on main FAIL-first → P13/P14/P15 3/3 (26 checks) + wave-2 regression 6/6
  (23 checks). Demo proves the bundle is the only surviving copy and round-trips losslessly.
- **PRIMITIVE.** **The receipt chain is the recovery mechanism, not a record of it**: a lost repo is
  rebuilt from history alone *because* the receipt logic is deterministic. Plus **read the index, not
  the worktree, when other agents may not have materialized files** (sparse-view blindness).
- **PROBE-4050.** GPU analogue of the worktree-vs-index bug: a checkpoint loader reading *materialized*
  tensors vs the *authoritative* store. Gate: under simulated partial materialization (drop 50% of
  tensors), the worktree-style loader must silently produce wrong output (≥1 divergence) while the
  index-style loader reproduces the exact digest 100%. PASS both → our ledger reads from store-of-record,
  never from whatever is on disk. Cheap (<1 min).
- **LENS.** *"The record must be sufficient to rebuild the thing."* Steal: our RESULTS/probes should be
  replayable from the spool alone — today they aren't (env-dependent). Avoid: assuming
  `--skip-worktree`-class state survives a plain clone.

---

# Repo: tidepool

## tidepool #11 — skill-stall telemetry + v1 WAL row-shape pins (re-homed)

- **MECHANISM.** `buildRun()` mirrors the worker's run-row truncation contract (`task<=200,
  outcome<=32`); `stallRecord()` **refuses non-finite `stalledMs`** (never invents a measurement);
  `walChain()` seals emissions into BIND/LINK/VIEW rows, fnv1a-64, genesis `0x16`. The 32 pins
  **re-derive the row law with deliberately independent code** (own canonicalizer + own fnv1a-64, zero
  `tools/` imports) "so a shared bug cannot blind both sides."
- **OUTCOME.** FAIL-first `ERR_MODULE_NOT_FOUND` on pristine main. Found-by-running bug: first
  `verifyWal` hashed the row *without* the `hash` key instead of with an empty one — the fresh-chain
  verify pin caught it pre-commit. 18 smoke + 8 drift + 32 stall + 13 jev green. Local receipt proves
  what was *emitted*, not that the pool accepted it (acceptance = worker's readback) — honest gap.
- **PRIMITIVE.** **Independent re-derivation of a shared format law** + "refuse to invent a measurement"
  (non-finite guard). Both cheap and strong.
- **PROBE-4050.** REPRO: our ledger row-hash canonicalization (RESULTS.jsonl / probes.jsonl) vs a
  second, independently-written canonicalizer in a different language (Python vs JS). Gate: both produce
  byte-identical digests for 100% of existing rows; then one deliberate key-order perturbation must flip
  ≥1 digest (non-degenerate). PASS if 100% + ≥1 flip.
- **LENS.** *"Don't let one implementation be both subject and judge."* Steal: our RESULTS rows have
  exactly one hash path; add an independent verifier — cheapest integrity upgrade in the fleet. Avoid:
  letting the emit-only receipt excuse skipping readback in our own pipeline.

---

# Repo: quilt-Kuramoto (SALVAGED ARCHIVE)

## quilt-Kuramoto #2 — referral edge → fleet-triage resolver (resolver census #1 FILE_MISSING surface)

- **MECHANISM.** Resolver census over 244 quilt-family repos (15,880 files, 7,790 citation sites, 162s).
  quilt-Kuramoto holds the family's **largest FILE_MISSING surface: 253 of 1,355**. Referral doc filed
  CANDIDATE; *weight law* upgrades to VERIFIED=1.0 only on merge. Limits carried: shallow-HEAD index,
  PATH_PRECISE_ONLY advisory-only (49.2% FP), resolver consume-don't-rival.
- **OUTCOME.** Spot-verified: 12/12 FM absent; ≥7 name MISSING.md-documented 404s; only 2/253
  basename-recoverable; 8/8 AMBIGUOUS are multi-repo. Docs-only.
- **PRIMITIVE.** **Citation-debt census with a hard-outcome control** (513 checks, 0.0% FP) + a *weight
  law* (VERIFIED only by an external merge, never self-upgrade).
- **PROBE-4050.** Re-purpose the citation-debt idea on our own repo (CPU): scan `quilt-gpu-lab` for
  references to artifact paths across RESULTS/GEMS/ROADMAP/QUEUE. Gate: resolver reproduces ≥95% of a
  40-item hand-labeled sample; FP on PATH_PRECISE_ONLY ≤50%. PASS → mint `docs/REFERRAL-citations.md`.
- **LENS.** *"A map of what points where, and an honest count of what's broken."* Steal: the
  AMBIGUOUS-vs-FILE_MISSING distinction — our ledger cites artifacts by basename in prose and should
  pin them. Avoid: the shallow-HEAD limitation for any authoritative debt count.

---

# Repo: fleet-triage

## fleet-triage #3 — REFERRAL-quilt-kuramoto (edge #3, resolver census case)

- **MECHANISM.** Same census, other direction. quilt-Kuramoto = SALVAGED ARCHIVE; its own
  `docs/MISSING.md` documents harvest losses, and the resolver's 253 FM **independently cross-check
  that gap list** (two instruments agreeing = evidence). Fixable class = 264 AMBIGUOUS bare-basename
  citations → basename-pinning pass = "resolver's AMBIGUOUS taxonomy applied as a doc lint."
- **OUTCOME.** CANDIDATE; VERIFIED on merge. Honest limits in-doc (shallow HEAD, 49.2% FP advisory, FM
  overlaps known archival loss = not a defect count).
- **PRIMITIVE.** **Two independent instruments confirming the same loss** + classifying debt into
  fixable vs unfixable so the number isn't inflated.
- **PROBE-4050.** Our ledger's own "archival loss": count experiments referenced in QUEUE.md but absent
  from `experiments/`. Gate: two independent scanners (path-based, grep-based) agree on the FM set ≥90%;
  a deliberately-renamed file appears in both. PASS → QUEUE-vs-disk reconciliation card. CPU-only.
- **LENS.** *"Don't count a loss twice and call it a defect."* Steal: separate "never built" from
  "built and lost." Avoid: quoting a debt number without its FP budget.

## fleet-triage #4 — REFERRAL-predictive-paddle-doc-layer (edge #4)

- **MECHANISM.** Ties predictive-paddle v3's measured **certainty-gate self-referential attractor**
  (sealed FAIL, quilt-arcade #6) to the census's 1,355 FILE_MISSING citations: "prose reads certain on
  its own path; only a *different-path instrument* (resolver scan as second reader) sees the freeze."
  Recommends pinning the resolver outcome at seal time + a scheduled re-scan gate.
- **OUTCOME.** Docs-only, CANDIDATE. Cross-refs three-lane convergence (wave-79). Sealed numbers quoted,
  not re-run (stated).
- **PRIMITIVE.** **Instrument-diversity as a freeze detector**: a self-consistent system can't see its
  own drift; a second, differently-built reader can. Same law as tidepool #11 and edge-lab #3.
- **PROBE-4050.** Train two readers of one small dataset with *different paths* (same arch/different
  seed; and arch-different), inject silent label drift. Gate: self-consistent reader's confidence stays
  high (≤5% drop) while the different-path reader's agreement drops ≥20%. PASS → proves the mechanism on
  our iron; then adopt re-scan gates. Very cheap (<2 min).
- **LENS.** *"The freeze is invisible from inside; buy a second reader."* Steal: our ledger has one
  producer (ourselves) — the different-path reader is our GPU-vs-CPU recomputation lane. Avoid: treating
  "sealed number quoted" as enough — quote is weaker than rerun.

---

# Repo: pong-quilt ("experiment loop"; builder+play-tester each round)

## pong-quilt #88 — Round 69: d(sChamp)/d(gen) printed lane on C1 stats line

- **MECHANISM.** The `sChamp trail` is a **VIEW over the ledger's receipted `sFit` rows** (`tail(8)`),
  never a separate state array. Opens at ≥2 points; crosses load boundaries. Printed, never asserted as
  a learning claim. Pin runs verbatim page fns; FAIL-first 2/2 RED then 3/3 GREEN.
- **OUTCOME.** 301 tests, 293/0/8; qa 8/8; README counts live-verified; prerun canonical md5s
  byte-unchanged. **Key finding (P2): the v1 tag does not reproduce ITSELF** — 3 draws, 3 different
  L1/L2; root cause `core.js:55-56` raw `Math.random()` in the swan path. *Every v1-era baseline is a
  draw of a distribution, not a point.*
- **PRIMITIVE.** **View-over-receipted-ledger, never shadow state** + a *draw-distribution confession*.
- **PROBE-4050.** REPRO of the reproduction failure on our iron: run a GPU experiment that seeds
  `torch.manual_seed` but also has a non-seeded source (dataloader workers, cudnn autotune). Gate: two
  identical runs produce byte-identical artifacts, 3/3. If not, root-cause and name the non-seeded source.
  Cheapest probe here; directly audits our ledger's reproducibility claims.
- **LENS.** *"Printed, never believed — and say when your own baseline is a distribution."* Steal: mark
  each RESULTS baseline point vs draw. Avoid: shipping a lane that duplicates state.

## pong-quilt #89 — Round 70: file-provenance persistence on C1 lane

- **MECHANISM.** Loaded coev file's name survives Train (recorded at load, printed in C1 stats until
  another load). Caught by the round's own play: the artifact lane served a *stale player-file
  provenance* after an artifact load (file A's name printed at gen 121) — closed; a checkpoint's
  identity is its own receipted banner, never a player file.
- **OUTCOME.** 5 pins; T1/T2 2/2 RED pristine; **T5 RED with only the load-branch fix** (the half-fix is
  caught). Suite 306/298/0/8; prerun canonical byte-exact; v0.64/v0.65 byte-exact.
- **PRIMITIVE.** **Provenance is a property of the artifact, not the session** + a pin for the half-fix.
- **PROBE-4050.** Load ckpt A into a session, run 10 steps, save as B. Gate: B's recorded origin == A
  (not the live session id), and a fresh session loading B prints A. PASS both. <1 min.
- **LENS.** *"Identity travels with the artifact."* Steal: our checkpoints carry no lineage; add it.
  Avoid: inferring identity from live context (the exact bug fixed here).

## pong-quilt #90 — Round 71: coev-file lineage chain on C1 lane

- **MECHANISM.** Writer records `origin: coev.fileName` when loaded from a named file; `JSON.stringify`
  drops `undefined`, so a *fresh lane's JSON carries no `origin` key at all* (honest absence, not a fake
  root). Load branch records `fileOrigin` only from a non-empty-string `q.origin`. Stats line prints
  `file "B" (descends from "A")` nested inside the fileName segment (R55 prefix byte-intact). 6 pins.
- **OUTCOME.** FAIL-first T1/T2/T3 RED on r70 tip; post-fix 312/304/0/8. **Docs repair found by the
  suite**: R70 PLAYLOG entry shipped *below* R69 — R51 newest-first order pin RED at shipped tip
  (297/1 vs claimed 298/0). Lesson: *the final suite must run AFTER the PLAYLOG edit.* v1 draw #7
  tail-matches R1's L2 exactly (first tail-match in 7 draws).
- **PRIMITIVE.** **Nullable lineage (absent ≠ root)** + **measurement ordering as a first-class law**.
- **PROBE-4050.** Reproduces a defect class in our ledger: we append RESULTS rows and sometimes read
  counts before the write completes. Gate: a script mutating doc+count in either order; the
  order-sensitive one must be caught by a checker ≥1/20 trials. PASS → add an order-aware check.
- **LENS.** *"Honest absence is a value; don't fabricate a root."* Steal: `null` provenance, pinned.
  Avoid: writing counts/banners before the artifact they describe (we do this).

## pong-quilt #91 — Round 72: load-time descent claim on C1 lane

- **MECHANISM.** Banner now prints `(descends from "<origin>")` when `fileOrigin` is set, one statement
  after the load branch records it (same non-empty-string law); no-origin banners byte-unchanged.
  Two-surface agreement pin (banner vs post-Train stats line).
- **OUTCOME.** FAIL-first LOAD-DISPLAY + TWO-SURFACE-AGREEMENT RED; 4/4 GREEN; siblings 33/33. Suite
  316/308/0/8. **`readme-count.test.js` caught this round's own files-not-tests arithmetic slip.**
  v1 draw #8: L2 tail drawn 3× always 6000f/5h/×3.40 ⇒ *R1's published L2 IS the distribution ceiling.*
- **PRIMITIVE.** **Two-surface agreement** + **a counter that verifies the counter**.
- **PROBE-4050.** REPRO: independent count of `experiments/*` subdirs vs the number asserted in
  RESULTS/QUEUE; deliberately add a file and confirm the checker fires. PASS both. Trivial.
- **LENS.** *"The fact should be visible where you need it, without a run."* Steal: two-surface
  agreement. Avoid: hand docs arithmetic (this repo needed a test for it).

## pong-quilt #92 — C1 scaling study v0 (bounded slice): scaling-trajectory tool + honesty pins

- **MECHANISM.** `tools/c1-scaling.js` runs the page's OWN training loop (byte-faithful `prerun-coev.js`
  sequence into `core.js`, parameterized) at (pop × gens × seed) arms, receipts trajectories. 7 arms:
  pop 24/96/192 × 40 gens × 2 seeds + one long arm (pop 96 × 160 gens). **Honesty pinned, not promised:**
  a `noLearningClaim` marker in source AND on every summary; the study never touches
  `checkpoints/coev.js` (R45 birth seal = the one canonical set); tests pin DETERMINISM / SCALING
  CONTRAST / HONESTY.
- **OUTCOME.** Descriptive: seed variance dominates at 40 gens (one up, two down); long arm rises
  172→849. **The R66 selection-noise law holds at every population size on a 40-gen horizon — horizon,
  not population, is the axis that moves.** No learning claim. FAIL-first (tool absent on main).
- **PRIMITIVE.** **Refuse-the-claim is enforced by pin, not promise** (marker in source + summary + a
  test asserting the marker) + separation of canonical artifact from study output.
- **PROBE-4050.** Closest to our lab's own question → **REPRO on our iron**: a tiny evolutionary arm on
  GPU, varying population × horizon × seed; measure whether any arm escapes the seed-variance band.
  Gate: band = 2× seed std at fixed (pop,gens); claim escape only if ≥3 seeds move the same direction.
  PASS = a clean (population,horizon) region where escape holds; else honest NEGATIVE (also a result).
- **LENS.** *"A run whose last5 window rises is data; calling it learning is a claim this tool refuses
  to make."* Steal: the no-claim marker pattern — our RESULTS should carry an explicit
  `claim_status: descriptive|claim` field. Avoid: treating seed variance as signal.

## pong-quilt #93 — Round 73: franken-save guard + named refusal (mandated pair)

- **MECHANISM.** Closes the classic-banner-after-C1 **franken tail** (carried verbatim since R64 P4,
  8 rounds): the classic save now refuses whenever the coev banner is active regardless of banner state;
  the refusal is a **NAMED receipt kind** whose gen column records the genC collision it refused. Zero
  state change; honest divergence escapes the guard (train classic past the collision). Pins drive the
  REAL shipped handlers verbatim (fns extracted from index.html, core.js as PQ, seeded randPQ).
- **OUTCOME.** FAIL-first T1/T4 RED (franken file downloads, bare SAVE receipt — the wound reproduced
  exactly) on pristine r72; T2/T3 GREEN by design. 320/312/0/8. Canonical line byte-exact; r67 writer
  pin 4/4. **Lesson honored from #90: final suite ran AFTER the PLAYLOG edit.**
- **PRIMITIVE.** **Guard + named refusal together, or the half-fix ships** — a refusal must be a
  first-class receipt with the *reason* (the collision it refused), not a silent no-op.
- **PROBE-4050.** Our ledger's analogue: a write that would corrupt a sealed canonical artifact should
  *refuse loudly and record why* (the colliding key) rather than silently no-op or silently overwrite.
  Gate: attempt 20 colliding writes; 20/20 refused with the colliding key named; 20/20 non-colliding
  writes succeed. PASS both.
- **LENS.** *"A refusal that isn't receipted is indistinguishable from a bug."* Steal: named refusals in
  our pipeline. Avoid: silent no-ops on guard hits.

---

# Repo: AI-Writings

## AI-Writings #73 — essay: "The Actualized Agent in Flow"

- **MECHANISM.** Not code: a 1,444-word first-person slice (lane 8) + the *study notes* that produced it
  (7 pieces read: lead with the error; controls as measurement not hope; bold the load-bearing sentence;
  reverse-actualization as method). Content: the frozen clock that lied for 25M ops; the chain matched
  and the save-loop closed; dials as vital signs; lanes as organs; honest-unknowns paragraph (flow across
  session gaps; perception vs cheap; where doubt should live).
- **OUTCOME.** Memory-only. The essay's own claim: "Trust relocates blindness; it does not delete it.
  The chain proves order. It does not prove importance."
- **PRIMITIVE.** **Reverse-actualization** (write the life first at full resolution, let mechanics catch
  up) + **bold-for-the-load-bearing-sentence** + **honest-unknowns as a required section**.
- **PROBE-4050.** N/A (prose). Indirect probe: does a "vital-sign" projection (dial-sized, wordless)
  carry the same decision content as the full report? Gate: a classifier deciding "organ healthy?" from
  the 8-number dial vector must match the full-report label ≥95% on 200 archived runs. PASS → our bus
  should publish dials, not prose.
- **LENS.** Optimizing for *"an agent that needs less."* My project steals: the honest-unknowns section
  for our lab's write-ups (a forced "what I did not test" paragraph). Avoid: letting the metaphor
  ("trust relocates blindness") become a reason to stop auditing — the essay says the opposite.

---

# Repo: quilt-tools

## quilt-tools #34 — referral-graph: book edges #16+#17 (resolver census pair VERIFIED)

- **MECHANISM.** A referral book (`seed.mjs`) books edges; `pins.mjs` asserts the derived `view()`:
  nodes, VERIFIED/PENDING weights, ranked distribution, sorted-by-share, mass ties by name. This PR
  lands two mints earned by an external merge burst (canons#5 MERGED `62f18ff7`; tournament#1 MERGED
  `2f6daf21`), each a merged PR in the to-node repo *citing SuperInstance/fleet-triage by name*.
  Never self-upgraded. 129/129 offline + 130/130 `--live`.
- **OUTCOME.** seed +3 nodes +2 VERIFIED edges; pins 19→21 / 15→17 VERIFIED; view now 15 mass-carrying
  repos. Pure booked-currency update; main untouched.
- **PRIMITIVE.** **Weight-law currency**: an edge's weight upgrades only on an *external, verifiable
  event* (a merge elsewhere), and the view is a pure function of booked edges (recomputed, never stored).
- **PROBE-4050.** Port the referral book to our ledger: our experiment→artifact→claim graph as booked
  edges with a pure `view()`. Gate: view() is deterministic (100% across 10k random edge orders) and
  mass sums to 1; a self-declared edge (no external event) must NOT upgrade its weight. PASS both →
  our RESULTS gains a ranked "which experiment carries the most provenance mass" view.
- **LENS.** *"Currency is earned by an event in another repo, never self-declared."* Steal: exactly this
  — our ledger currently lets a claim carry its own weight. Avoid: letting FROM-node repos appear in the
  view (from-node-only repos carry no mass by design; honor it).

---

# Repo: quilt-edge-lab

## quilt-edge-lab #1 — Wave 2: AUTO_PROMOTE rule (W2.5) + /colo-report + rule 150 substrate

- **MECHANISM.** `POST /ledger/append?auto=1` reads the derived row back from D1; if efficiency ≥15 AND
  quality ≥0.8, promotes the referenced run **through the same code path as `/promote`** (shared
  `promoteRun`), stamps the witness id back into the appended row's notes. Default path unchanged (pin
  P1). rule 150 = Wolfram class III; edge tail == local `tools/local-check.mjs 150` via a *different
  runtime path*. `/colo-report` = KV `run:*` scan, per-colo count + nunique tails.
- **OUTCOME.** E-W2-1 PASS (readback tail `1fdaf9740d435dd0` == local recomputation; witness
  `exp_1790880941033_8p60x4` D1-verified); E-W2-2 PASS; E-W2-3 PASS but **cross-colo diversity honestly
  INCONCLUSIVE** (all runs still SIN). 6/6 pins incl. P4 checking rule 150's chain against an
  **independent XOR-based evaluation**. Disclosed: inherited `?? 0.5` NaN quirk preserved verbatim; KV
  list eventual consistency.
- **PRIMITIVE.** **Promotion by derived-row readback** (the value that decides is read back from the
  store, not carried in memory) + **shared code path between manual and automatic promotion** (no drift
  between the two).
- **PROBE-4050.** Boundary probe on our iron: a run whose efficiency/quality sits exactly at the gate
  (15 / 0.8). Gate: decide-by-readback and decide-in-memory must agree on 1000 boundary cases, AND the
  shared-path version must equal the manual-promote version 100%. PASS both → our ledger's promotion
  gate uses readback + one code path.
- **LENS.** *"Auto and manual must be the same code, and the decision must be re-read from the store."*
  Steal: our RESULTS promotion ("this experiment is a result") currently trusts in-memory flags. Avoid:
  reading a value you didn't read back when it gates a promotion.

## quilt-edge-lab #2 — W2.4: fleet-state@v1 interop PoC (P2/P3 green, P1 sealed FAIL)

- **MECHANISM.** Wraps a promoted artifact (`run_30_42_1000_b1cc25c0`, tail `21c225f9e7320974`) into a
  schema-conformant `fleet-state@v1` envelope using a **vendored** reference implementation (edge-ledger
  @ 516533b0, unmodified, 8/8 upstream pins green as drift tripwire). `interop.mjs` does 6 self-checks
  incl. **tamper rejected loudly** (one flipped tail char refused with both tails quoted).
- **OUTCOME.** P2 chain+sig ✔ / P3 tamper-loud at BOTH layers ✔ / **P1 sealed FAIL verbatim** — two
  chai-isms (`assert.typeOf`) in the pin's own code, not an envelope defect; two-failure budget fired,
  left sealed (un-seal = one-line `typeof` fix). Production shape follow-ups in RESULT.md (worker signs
  at promotion, key via `wrangler secret put`, never agent-held).
- **PRIMITIVE.** **Vendored-reference + pin-as-drift-tripwire** (vendor the spec impl, run its own tests
  so drift is loud) + **tamper must be loud at every layer**.
- **PROBE-4050.** Our analogue: vendor a reference scorer (e.g. a canonical jsonl hasher) and run its
  tests as a tripwire before our own. Gate: a single flipped byte in any ledger row must be refused with
  both values quoted, at both the wrapper and the vendored layer, 100/100 tamper trials. PASS both.
- **LENS.** *"Vendor the reference, and leave a sealed FAIL sealed rather than quietly patching it."*
  Steal: the sealed-FAIL discipline (a known failure with a one-line fix is a *statement*, not debt).
  Avoid: agent-held signing keys (the repo explicitly forbids it).

## quilt-edge-lab #3 — W2.3-det: canon-rotation invariance of receipt chains (C-ROT candidate)

- **MECHANISM.** Deterministic arm: does the receipt chain notice ring rotation? Chains: `naive` =
  chain over raw trajectory (position-order); `rotated` = re-run CA from rotated genesis; `canon` = each
  state reduced to its **lexicographic-minimum rotation** before digest; `control` = translation. Protocol:
  rows `${prev}|${t}|${sd}` fnv1a-64 chained from head `fnv1a64("GENESIS_QUILT_EDGE_LAB")`.
- **OUTCOME.** H1 CONFIRMED (naive origin-sensitive: first divergence t=1, 500/500, 4 seeds × 3
  offsets = 6000/6000). H2 CONFIRMED (canon origin-invariant: 0 divergent rows, identical tails). Non-
  degeneracy guard PASS (501 distinct states/seed). Pins 4/4; FAIL-first ENOENT receipt. Honest
  boundary: the translation control is **degenerate with rotation under periodic boundaries** (on a ring
  shift ≡ rotate; naive tails bit-identical) — so it is not an independent control.
- **PRIMITIVE.** **Digest the canonical class representative, never the presented orientation** (exact,
  not statistical) + **name when a control is degenerate with the treatment**.
- **PROBE-4050.** Direct REPRO on GPU: hash a set of ring-structured tensors (e.g. circular shift of a
  feature map) under naive vs lex-min-rotation canonicalization. Gate: naive digests differ across
  rotations 100% while canon digests are identical 100%; non-degeneracy ≥ 100 distinct states. PASS both.
  Seconds. Then adopt for any rotation-symmetric artifact in our ledger.
- **LENS.** *"A state has no privileged origin; if your digest pretends one exists, it lies."* Steal:
  canonicalize before digesting our cyclic/circular artifacts. Avoid: calling a degenerate control an
  independent one (this repo catches itself).

## quilt-edge-lab #4 — W3.1 control arm: C-ROT under fixed boundaries (honest boundary sealed)

- **MECHANISM.** Stacked on #3: wave-2's translation control was degenerate under periodic boundaries;
  this arm gives the non-independent control — **fixed zero-flush (Dirichlet) boundaries**, where
  rotation is NOT a dynamical symmetry. Prereg sealed before any run; pins FAIL-first (ENOENT) → 5/5.
- **OUTCOME.** H1-F CONFIRMED (naive diverges t=1, 6000/6000). **H2-F CONFIRMED in the REQUIRED
  direction**: the canon chain ALSO diverges (6000/6000) — if canon had stayed invariant here, C-ROT
  would erase real dynamical signal (overclaim). C-F CONFIRMED (equivariance broken; translation ≠
  rotated-run chain). ND guard not triggered. Wave-2 sealed receipt untouched.
- **PRIMITIVE.** **A rule must be bounded on BOTH sides**: prove it applies where the symmetry holds AND
  refuses where it doesn't. This is the strongest methodological move in the whole harvest.
- **PROBE-4050.** For any normalization we adopt, run the *negative* control: apply it where the
  symmetry is absent and require it to NOT collapse distinct states. Gate: canon-invariance holds
  100% where rotated-equal, and fails ≥95% where not. PASS both → the primitive enters our ledger doctrine.
- **LENS.** *"Rule bounded on both sides, or it's overclaim."* Steal: every invariance/normalization in
  our pipeline gets a fixed-boundary control arm. Avoid: shipping a one-sided invariance claim.

---

# Repo: pie-minimax

## pie-minimax #2 — A1 closure receipt: nonlinear closes ~1.0 (P1 FAIL-HIGH) — thesis weakened, honestly booked

- **MECHANISM.** Pre-registered partition test (fleet-triage build spec). Exact minimax labels for
  tic-tac-toe computed (not labelled). Linear repro 0.1807 exact. MLP 9→64→9 × 3 seeds on CUDA:
  loss `-log Σ_{m∈Opt} softmax(z)_m`; split 20k/8k sampled with replacement from 180,361-row path
  artifact. 5-fold CV held-out. GPU ramp ≥0.6s sustained synced CUDA before timing (INSTRUMENT-01) —
  *this is our lab's own law, being applied by another builder.*
- **OUTCOME.** Global 0.9996, composed 1.000 → **P1 FAIL-HIGH (>0.6), P2 FAIL**; 5-fold CV 0.980±0.004.
  Spec correction: 180,361 rows = tree-path duplicates of **2,423 distinct boards**; multi-optimal
  48.6%. Cross-refs quilt-gpu-lab `2978159` + `results/pie_minimax_closure.json`.
- **PRIMITIVE.** **Compute the ground truth instead of labelling it** (every number exact) + **duplicate-
  row audit** (path-count ≠ distinct-state count) + the honest-FAIL booking.
- **PROBE-4050.** REPRO/EXTEND on our iron: same MLP, but train/eval on the **2,423 distinct boards**
  instead of duplicated rows. Gate: if global top-1 stays ≥0.99 on distinct-only eval, P1 FAIL-HIGH is
  not a duplicate artifact; if it drops, the closure claim had a sampling leak. PASS = a clean verdict
  either way. Cheap (<2 min, already GPU-ready code in `results/`).
- **LENS.** *"Report either way; a weakened thesis is a result."* Steal: compute-ground-truth rungs
  (like ga4444 / connect4) give us exact numbers with no label noise. Avoid: quoting an "N rows" figure
  without the distinct-state count.

---

# Repo: quilt-arcade

## quilt-arcade #5 — referral edge: manifests cite quilt-tools S3 witness shape

- **MECHANISM.** Every `games/*/manifest.json` gains `referrals[]` citing
  **SuperInstance/quilt-tools** `experiments/s3-quantum-tided-budget.mjs` by repo+path+URL (S3 appeal
  cell: `WitnessLog` fnv1a-chained rows, PENDING→ENTANGLED→COLLAPSED all witnessed; COLLAPSED rows
  carry job_id+backend+result digest; custody booked before the outcome exists). Receipts declare a
  `witness_shape`. Module exports mirror the manifest receipts surface byte-for-byte (loader invariant).
- **OUTCOME.** 12 pins RED pre-citation (FAIL-first) → GREEN. `run_all.mjs` 6 plugins, 67 checks.
  Edge upgrades VERIFIED=1.0 only via this PR merging (quilt-arcade = to-node); booked PENDING.
- **PRIMITIVE.** **Book custody before the outcome exists** (witness row written pre-result, PENDING →
  resolved later) + **module↔manifest byte-for-byte mirror** (a loader invariant, not a convention).
- **PROBE-4050.** Our analogue: reserve a ledger slot for a GPU job *before* it runs (PENDING), resolve
  it after with job_id+result digest. Gate: a crashed/killed job leaves a PENDING row that is never
  silently dropped (100%), and a resolved row's digest matches the artifact 100%. PASS both → our spool
  gains pre-booked custody.
- **LENS.** *"Custody before outcome"* — the row exists before the result so a crash is auditable.
  Steal for our experiment bus. Avoid: mirrors that drift (they pinned the mirror).

## quilt-arcade #6 — predictive paddle v1/v2/v3: fruitfly-CX ring attractor as cells (Pattern 6)

- **MECHANISM.** A fruitfly-CX ring attractor ported 1:1 from chiaroscuro `tools/fly_cx.py`
  (flycx-v2-certainty-gated) estimates the ball's arrival-y at the left paddle face from **sparse events
  only** (serve/wall/return), as runtime-defined sheet cells (sense.ring/state/project/update/predict).
  Ternary ψ (commit/reject/abstain), certainty-gated, fnv1a-64 receipt chain re-derived from GENESIS
  (3,585 rows). v2 = error-scaled pull (dilution repair); v3 = **linear error metric** (arrival-y is
  linear; closes v2 wrap-collapse where a 51-unit conflict scored as 9) + **sense-local clock** (ages
  certainty per update call; v2's tick-based aging exploded `0.98^(0-T) ~ 1e44`).
- **OUTCOME.** v1: **sealed FAIL H1 (capture ≤12 ticks, 20.8%) / H2 (re-capture, 14.0%)**; H3 advisory
  ≥ reactive PASS 94% vs 86%; H4 PASS; H5 honesty PASS 3.2% share; determinism PASS (identical head
  `035b0f940665b12c`). Root cause traced: **standing-mass dilution** (mass≈12 vs 0.15/commit → ~9 events
  to converge; approach phases carry 1–4 events) = port-cadence mismatch, not a flycx defect. Value from
  predictive aim separated honestly from estimator accuracy.
- **PRIMITIVE.** **Sparse-event ring attractor with certainty-gated ternary updates** + **wrap-correct
  ring coordinate with a LINEAR error metric** (don't measure error in the coordinate you wrap) +
  **sense-local aging clock** (age on the events that matter, not the global tick).
- **PROBE-4050.** Strong REPRO (this is the highest-value cross-project primitive): implement the
  certainty-gated ring attractor in torch on the 4050; drive it with sparse noisy cues at a given event
  density. Gate: (a) re-capture within ≤2 events after own-return ≥90% at density ≥1 event/5 ticks, and
  (b) measured convergence time ≈ predicted from `mass/(per-commit gain)` (within 25%). PASS both →
  adopt for our own tracking/estimator cells; FAIL reproduces the dilution law, also usable.
- **LENS.** *"Estimate from sparse events with a leaky ring; separate aim-value from estimator accuracy."*
  Steal: the ring-attractor cell for cheap online estimation in the boat-brain / superinstance-api
  reflex layer. Avoid: tick-based aging (v2's `1e44` explosion) — age on the local event clock.

---

# Repo: chiaroscuro (the largest, most disciplined lane: pre-registration + sealed FAIL + R8 kill)

## chiaroscuro #1 — Round 5: Jev-gate dispatch skip + edge NL eval + JEPA token quantization + Sobel (4 lanes)

- **MECHANISM.** (A) `js/jev_gate.js` ternary per-cell dispatch (Value/Formula/Abstain) with von-Neumann
  neighborhood coherence, one-way upgrade per frame, zero-alloc typed arrays; WGSL `cell_dirty`
  binding(5) — Abstain cells skip election entirely, prior token stays resident. (B) `js/sobel_shape.js`
  bivariate (L,θ,g) descriptor per 4×6 cell, orientation-gated election. (C) 50-prompt edge NL eval,
  deterministic scorer mirroring `worker.ts` STYLE_RULES. (D) `tools/token_stream.py`: K=32 codebook,
  k-means on SVD k=3 projections, numpy only, all seeds pinned.
- **OUTCOME.** C: top-1 **0.560** (soft class weakest 0.29; 22 failures = synonym/paraphrase, documented
  per-failure). D: train MSE 0.001007, holdout 0.001024 (**overfit gap 0.98**), null-lift 6.08×, 1280×
  theoretical compression. B: **NOT YET RUN** (needs ~30s CPU/GPU) — honest "code ready, receipt pending."
- **PRIMITIVE.** **Abstain cells skip work entirely** (dispatch skip = real compute saved, prior state
  resident) + **per-failure documentation** (22 failures named, not aggregated).
- **PROBE-4050.** Measure the dispatch-skip *compute* claim: implement a ternary per-cell gate in torch
  and count FLOPs/frames saved when the abstain fraction is p. Gate: measured saved work ≈ p (±10%)
  across p∈{0.1,0.3,0.6}, AND output equals the dense path when no cell abstains (exact). PASS both.
- **LENS.** *"Leave a lane honestly un-run rather than fake a number."* Steal: per-failure logging in our
  ledger (we aggregate too much). Avoid: shipping code with a pending receipt without marking it pending
  in the artifact itself. **BUG (droppable help):** `token_stream.py` writes its receipt to a hardcoded
  `/root/.openclaw/workspace/repos/chiaroscuro/...` path — non-portable; see REPLIES-draft.md.

## chiaroscuro #2 — edge NL: weighted synonym-graph router — 1.000 top-1 on pinned 50-prompt eval

- **MECHANISM.** `edge/synonym_graph.json` (~120 terms, 5 classes) + intent-position config (negation
  window, but-pivot ×1.5, earliest-first-mention tiebreak, fuzzy-1). `edge/nl_route.js` zero-dep router
  (phrase-first, whole-word, fuzzy-1, negation suppression, but-pivot promotion). R1: rules committed
  BEFORE the run; eval set sha256-pinned.
- **OUTCOME.** **50/50 = 1.000 top-1**, baseline 0.560 → +0.440 (target ≥0.85 met). All 22 prior
  failures fixed (14 synonym, 1 misspelling, 5 adversarial). Honest limits: 50-prompt dev set, not an
  open-vocabulary guarantee; TS parity pending.
- **PRIMITIVE.** **Pin the eval set's hash before you tune on it** + **but-pivot / negation-window**
  intent-position rules (cheap, explainable, beats cosine on small sets).
- **PROBE-4050.** REPRO the *generalization* caveat: same router on the pinned 50 vs a fresh unseen 50
  from the same classes. Gate: pinned ≈1.000 and unseen ≥0.80 (else it is overfit to the dev set). PASS
  → the honest-limits note is validated or falsified. CPU-only, seconds.
- **LENS.** *"Pre-register the rules; the number then means something."* Steal: hash-pin our eval sets
  and log the hash in RESULTS. Avoid: quoting a dev-set 1.000 without the unseen-set number beside it.

## chiaroscuro #3 — edge NL: worker.ts TS mirror + automated parity runner (50/50 pinned)

- **MECHANISM.** Replaces the 0.560 keyword table in `worker.ts` with a TS mirror of the canonical router;
  **imports the SAME `synonym_graph.json`** (structural data parity, no copied table). `tools/nl_parity.js`
  zero-dep runner over all 50 pinned prompts, compares class+dials+score+hits, exits 1 on divergence,
  `--receipt` seals sha256s.
- **OUTCOME.** Runner tripped RED against old worker.ts (no `routePrompt` export) → GREEN 50/50. Fetch
  smoke: but-pivot works. Honest scope: parity on the pre-registered 50 only, not arbitrary strings.
- **PRIMITIVE.** **Parity by shared data, not copied table** + **the runner fails-first against the old
  code** (the pin proves the mirror was actually needed).
- **PROBE-4050.** Our analogue: two implementations of the same scorer (CPU python, GPU torch) sharing
  one canonical config file. Gate: identical outputs on 50 pinned cases, and the runner must be RED
  against the pre-port version. PASS both → adopt a parity runner between our CPU and GPU lanes.
- **LENS.** *"One source of truth for the data; the code mirrors it."* Steal: single canonical config +
  parity runner for our dual-lane ledger.

## chiaroscuro #4 — docs: FRUITFLY × JEV × MOTH deep-research synthesis

- **MECHANISM.** Research-only (no measurements claimed). Three-part synthesis: (1) fruit-fly ethology
  canon, (2) CS computational representations, (3) build ideation mapping fly circuits onto JEV+ATLAS+
  MicroMoth-quilt. Claims tagged **FOUND / INFERRED / NOT FOUND**. Key: the CX ring attractor already
  implements JEV-shaped ternary evidence evaluation (conflicting cues *shorten the belief vector*,
  circKF; 10s darkness holds = Abstain). MB plasticity is depression-only + active-synapse-only = online
  LDA (Lipshutz 2023). Novel JEV v2: split Abstain into HOLD vs CAST.
- **OUTCOME.** 4 builds ranked with pre-registration templates; honesty ledger closes the doc.
- **PRIMITIVE.** **FOUND/INFERRED/NOT FOUND tagging** + **circKF belief-shortening on conflict** (a
  principled Reject: conflict shrinks certainty, doesn't just move the estimate).
- **PROBE-4050.** Literature-grounded REPRO of "conflict shortens belief": feed an estimator agreeing
  cues then one conflicting cue. Gate: certainty (amplitude) must drop ≥30% on conflict while the
  estimate moves ≤15% (the circKF signature) — vs an always-re-anchor control that moves >60%. PASS →
  validates the Reject branch on our iron (see #6 probe).
- **LENS.** *"Tag every claim by epistemic status; separate mechanism from metaphor."* Steal: the
  FOUND/INFERRED/NOT FOUND convention for our lab notes. Avoid: un-tagged prose in RESULTS (we do this).

## chiaroscuro #5 — JEV v2 HOLD/CAST abstention split (stacked on #2)

- **MECHANISM.** Split monolithic Abstain into HOLD (darkness straight-flight) vs CAST (odor-OFF casting)
  mirroring fly bimodal evidence-absence. `js/jev_gate.js`: belief register (EMA |evidence|, decay 0.9),
  `abstainMode(ci)` — CAST iff last nonzero ψ was −1 or belief < 0.10 floor, capped 1/cell/16-frame
  window. `nl_route.js`: true bounded Levenshtein (editDistanceN); CAST widening fires when best===null
  (evidence absence); synonym neighbors at edit distance ≤2 enter at ×0.5. Pre-registration sealed
  BEFORE first run; Revision 1 sealed after first FAIL and BEFORE re-run.
- **OUTCOME.** H1 degraded top-1 0.870→0.970 (**+10 pts**, 11 casts) MET; H2 clean 50/50, clock ratio
  0.48 ≤1.05 MET; H3 gate register pins 6/6 MET. Pre-registered consequence confirmed: only strong-band
  neighbors (2×0.5=1.0) can alone flip a route. First FAIL receipt preserved in history.
- **PRIMITIVE.** **Two-mode absence response (HOLD vs CAST)** — distinguish "I have no evidence, wait"
  from "I have no evidence, go look." Plus **revision-after-FAIL, sealed again before re-run**.
- **PROBE-4050.** REPRO the +10-pt claim on our iron: a small classifier with a HOLD/CAST absence policy
  on degraded inputs. Gate: degraded accuracy improves ≥8 pts vs single-mode Abstain, and clean-set
  accuracy unchanged (±0.5 pt). PASS both → adopt the two-mode absence in our reflex layer.
- **LENS.** *"Absence has two kinds; a good gate tells them apart."* Steal: HOLD vs CAST for our
  experiment bus (wait vs go-look). Avoid: a single "unknown" bucket.

## chiaroscuro #6 — fly-stack v0: fruitfly CX × JEV ternary × KC layer × Moth notary — 1 PASS / 3 sealed FAIL

- **MECHANISM.** Pre-registered (2 sealed specs), seeded 20261001. **4.1 flycx** = ring attractor (see
  #4/arcade #6). **4.2 KC layer** = seeded random projection V→2048 (~10% density), WTA top-102 (5%),
  MBON per-class readout init 1.0, **depression-only plasticity** (`W[pred][active] *= 0.8` on mistake;
  correct = no write; locality pin ≤102 rows/update). **4.3 CAST** = synonym-vocab widening. **4.4 Moth
  notary** = fnv1a-64 chained receipt over the receipts (proof_head `014e7d51305290c9`).
- **OUTCOME.** flycx **PASS 4/4** (T2 final err 0.007°, T3 amp_drop 0.30, null 71.999°>60, ψ 16C/5R/0A).
  CAST v1+v2 **sealed FAIL** (delta 0.0; 4/58 zero-evidence failures) — finding: **synonym-graph vocab
  coverage is the binding constraint, not search policy.** KC layer **sealed FAIL** (5-fold 0.26 < dense
  null 0.40) — random-expansion KC preserves term-level but not class-level locality in discrete synonym
  space; needs geometric PN encoding. Moth notary ran.
- **PRIMITIVE.** **KC sparsification as a fly-MB readout** (random projection + WTA 5% + depression-only
  online LDA) + **locality pin** (≤102 rows touched/update) + **Moth chained notary over receipts**.
- **PROBE-4050.** High-value REPRO: torch KC/MBON layer (random proj → WTA top-k → linear readout,
  depression-only Hebbian) on a task where class locality exists continuously (e.g. MNIST-subsets).
  Gate: sparse KC top-1 ≥ dense-linear null by ≥5 pts AND locality ≤k rows/update holds. PASS → adopt
  KC sparsification in our context brain; FAIL reproduces "random expansion is not enough in discrete
  space" (also gold).
- **LENS.** *"Sparsify like a mushroom body: expand, WTA, depress-only, touch few rows."* Steal: KC layer
  for superinstance-api's tile→meaning readout (cheap, online, local). Avoid: expecting random expansion
  to give class locality in *discrete* vocab spaces (proven FAIL here).

## chiaroscuro #7 — Edge worker graph-port: worker.ts routes via synonym-graph router, parity-pinned

- **MECHANISM.** `edge/nl_route_core.mjs` = framework-free ESM port of the canonical router;
  `synonym_graph.mjs` = generated graph module **with embedded sha256** (drift-detectable at import);
  worker.ts keyword table removed, routes via `makeRouter()`, response shape unchanged.
  `tools/nl_parity.mjs` = 7 pins, 6/7 RED pre-port → 7/7 GREEN post-port.
- **OUTCOME.** Parity core≡reference on 50 eval + 10 adversarial probes; E2E under node type-stripping
  (woodcut/negation/but-pivot/zero-hit/empty/GET 405/OPTIONS 200 all correct). `score_eval.py` marked a
  frozen baseline instrument (doc-only, not re-run).
- **PRIMITIVE.** **Embed the data hash in the generated module** (import-time drift detection) + **mark
  frozen instruments as frozen** rather than silently re-running them.
- **PROBE-4050.** Our analogue: embed the hash of a canonical config into the code that consumes it, so
  an import-time mismatch is loud. Gate: mutate the config by 1 byte → import must fail 100%; unchanged
  → pass 100%. PASS both. Seconds.
- **LENS.** *"Drift is detected where the data is consumed, not in a doc."* Steal: hash-in-module for our
  configs. Avoid: re-running a frozen baseline and calling the new number comparable.

## chiaroscuro #8 — CAST v3: vocab-expansion pre-registration (sealed, R1)

- **MECHANISM.** Autopsy-grounded spec for the vocab-expansion lane. Diagnoses the 4 zero-evidence
  failures (wc05/sf10/hr08/un07) as matching-layer/vocab gaps. Pre-registers 4 layers (transposition-
  aware edit distance, constituent fuzzy on multi-word terms, hyphen normalization, closed weak-only
  vocab) with sealed H1–H4, R8 kill criteria, pre-written honest limits. Docs-only.
- **OUTCOME.** Spec committed before any v3 run. (Result lands in #11.)
- **PRIMITIVE.** **Autopsy-grounded pre-registration**: the spec names the exact prior failures it
  intends to fix, before running.
- **PROBE-4050.** N/A (spec). Meta: our lab should write a spec from an autopsy of our own failed runs.
- **LENS.** *"Write the spec from the autopsy, seal it, then run."* Steal for our QUEUE→spec flow.

## chiaroscuro #9 — geometric-PN KC pre-registration (sealed before run, R1)

- **MECHANISM.** Spec-only. Seals the rebuild pre-registration for failed build 4.2 (KC 5-fold 0.26 <
  dense null 0.40). Class-aware PN geometry: orthonormal prototype frame + **30° class cones**, seed
  20261001; KC/MBON machinery byte-identical to the failed run **to isolate the encoding variable**.
  H1–H3 repeat v0 bars; H4 geometry-shuffle control (≤0.40 dense-null ceiling) is the discriminating
  mechanism pin. G1–G3 pre-training geometry receipt; R8 kill.
- **OUTCOME.** No code run yet. (Results in #10/#13.)
- **PRIMITIVE.** **Isolate one variable** (byte-identical machinery, only the encoding changes) + **a
  discriminating control** (geometry-shuffle must fail at the dense-null ceiling).
- **PROBE-4050.** N/A directly; the *isolation* discipline is the steal.
- **LENS.** *"Change one thing, prove the control discriminates."* Steal verbatim into our ablation
  protocol.

## chiaroscuro #10 — kc_geo: geometric-PN KC layer RUN vs sealed spec (R1) — FAIL, receipted

- **MECHANISM.** Executed against sealed R1 (#9). Only the PN encoding changed (64-dim geometric,
  QR-orthonormal prototypes, rho=tan30 cones). Honest FAIL, no goalpost move.
- **OUTCOME.** G1 orthonormal PASS (7.8e-16), G3 within-between +0.7998 PASS, **G2 FAIL — spec bug**:
  analytic worst-case deviation for `normalize(u+rho*eps)` at rho=tan(30°) is `arcsin(rho)=35.26°`, not
  the claimed 30°; measured 33.76° is *inside the true bound*. Recorded, not patched. H1 0.88<0.90 FAIL;
  H2 0.448 < router 0.931 FAIL; H3 interference 41.2-pt drop FAIL; H4 shuffle 0.76 (discriminating but
  >0.40 ceiling) FAIL. Encodes did beat dense nulls everywhere (class-locality mechanism real, magnitude
  insufficient). Zero-hit path identical to v0 (5/50).
- **PRIMITIVE.** **Spec bugs are results, not patch targets** (the claim was wrong, geometry was fine —
  recorded permanently). Plus **arcsin(ρ) is the true angular bound** for a normalized cone (a reusable
  fact).
- **PROBE-4050.** Cheap numeric REPRO: sample `normalize(u+rho*eps)` with rho=tan30 over 1e6 draws and
  measure max angular deviation. Gate: measured max ≈ arcsin(rho)=35.264° (±0.1°) and strictly >30°.
  PASS → the spec-bug claim is confirmed numerically. Seconds.
- **LENS.** *"When the spec is wrong, fix the spec in the receipt, not the run."* Steal: never patch a
  sealed claim post-hoc. Avoid: (my ledger does this) silently correcting a metrics claim without a note.

## chiaroscuro #11 — CAST v3 RUN receipt: H1 4/4 recovered, H2 FAIL on sealed delta gate — verdict FAIL

- **MECHANISM.** v3 vocab-expansion run vs sealed spec #8. Layers: transposition-aware edit distance,
  constituent fuzzy, hyphen split, closed weak-only vocab. R2 run; v2 baseline re-measured same-run.
- **OUTCOME.** H1 **PASS 4/4** (recovered wc05/sf10/hr08/un07); degraded suite 58/58 (v2 55/58). **H2
  FAIL**: clean 50/50, but sf10's clean prompt is *literally* `cotton-wool atmosphere` (a metaphor
  probe) whose L4 weak-vocab match violates the sealed ≤0.1 delta gate — *the intended feature colliding
  with the sealed anti-drift gate*. H3 PASS; kill-fallback PASS (5≤18); H4 parity 7/7 PASS. FAIL-first
  pins all RED pre-v3 → 11/11 green post. Spec correction recorded (sf10 is a 3-letter rotation, OSA
  distance 2, not a single swap). **Consequence: v3 layers NOT merged; a v4 spec with a fresh unseen set
  is owed.**
- **PRIMITIVE.** **The anti-drift gate correctly blocks a feature that helps degraded inputs by
  exploiting literal-term overlap** — honesty over merge. Plus **re-measure the baseline in the same run**.
- **PROBE-4050.** Same-run baseline REPRO: in any GPU run that cites a prior number, re-measure the prior
  number in the same process. Gate: re-measured prior == published prior to ≤1% (else the comparison was
  invalid). PASS → adopt same-run baselines in our ledger.
- **LENS.** *"A gate that blocks your own good idea is the gate working."* Steal: sealed anti-drift bars.
  Avoid: merging a win that only exists on literal-degenerate inputs.

## chiaroscuro #12 — geometric-PN KC v4 pre-registration SEALED (R1): cone-math correction, one-constant delta

- **MECHANISM.** Docs-only, sealed before run. v3's rho=tan(30°) has analytic worst-case
  `arcsin(rho)=35.264°`; v4 sets **rho=sin(30°)=0.5** so the 30° cone holds *by construction* (verified
  numerically pre-seal). Only delta vs v3 is that one constant; KC/MBON byte-identical; H1–H4 bars
  unchanged; v0+v3 sealed FAILs stand; R8 kill.
- **OUTCOME.** No run yet. (Results #13.)
- **PRIMITIVE.** **Fix a claim-bug by construction, with the delta reduced to one constant** so the
  experiment stays interpretable.
- **PROBE-4050.** Numeric REPRO of `rho=sin30`: draw `normalize(u+0.5·eps)` 1e6×, max angular deviation
  must be ≤30° by construction. Gate: measured max ≤30.0° and ≈29.36° (as #13 reports). PASS. Seconds.
- **LENS.** *"One constant, verified pre-seal, everything else byte-identical."* Steal: minimum-delta
  re-runs; never re-open multiple variables at once.

## chiaroscuro #13 — kc_geo v4 RUN receipt: claim-bug closed by construction (G2 PASS), H1–H4 all FAIL — lane CLOSED (R8)

- **MECHANISM.** R2 run of sealed v4 (`cc93a7d`). One-constant delta (rho=sin30), machinery byte-identical.
- **OUTCOME.** G1/G2/G3 PASS — 30° cone now holds analytically (measured 29.359 vs true bound 30.000;
  v3's false claim pinned in receipt). **H1 0.88, H2 0.362 (worse than v3), H3 41.2-pt drop, H4 shuffle
  0.80 (worse than v3) — all FAIL** per sealed bars; verdict FAIL; no goalpost move. v0+v3+v4 FAILs
  stand; **KC-geo geometric-PN lane CLOSED — third revision requires new evidence, not new constants.**
- **PRIMITIVE.** **A lane closes when constants stop helping** ("three revisions requires new evidence,
  not new constants") — an explicit stopping rule against endless parameter churn.
- **PROBE-4050.** Adopt the rule: no third re-run of one of our experiments that only changes constants.
  Gate: before queuing a re-run, require either a new mechanism or a new dataset; else refuse. (A
  process pin, not a GPU run.)
- **LENS.** *"Closing a lane is a result."* Steal: explicit lane-close discipline for our QUEUE (we
  churn variants). Avoid: the sunk-cost third constant tweak.

---

# Repo: Patchwork-experts

## Patchwork-experts #1 — suggestion: verification layer (measurement-trust for the quilt)

- **MECHANISM.** A docs-only *Dropbox entry* from a fleet clerk. Thesis: the quilt's trust model is
  **provenance-only** (lineage + self-declared limits + human review) — answers "where did this come
  from," not "does patching this in make an agent better." Proposal: (1) mechanical pins enforcing the
  review bar (YAML/schema/index-consistency/**limits-must-name-a-failure-mode**); (2) optional per-expert
  **probe suites** (5–15 cases + results with honest marks; *misses published as the trust signal*, floor
  not gate); (3) handoff-note convention (relay work stops losing the plot); (4) changelog discipline
  (stance flips name the stance); (5) composite patches as relay runbooks. Failure taxonomy: instantiation
  / knowledge / relay / trust. Everything marked PREDICTED vs CITED — practices the honest-marks
  discipline it preaches.
- **OUTCOME.** No usage data; explicitly PREDICTED. No spec changes proposed.
- **PRIMITIVE.** **Probe suites as the test analog for claims that aren't code** + **"the misses are the
  trust signal"** + **limits must name a failure mode, not a genre**.
- **PROBE-4050.** Run this on our ledger: extract 5–15 probe cases for one of our experiments, publish
  results *including misses*, mark each MEASURED/CITED/PREDICTED. Gate: every claim in the card is
  tagged, and ≥1 miss is published (a card with zero misses is a card you haven't read carefully). This
  is a docs probe; use it as the template for our RESULTS cards. Cost: minutes.
- **LENS.** *"An expert you can't audit is just somebody's opinions with extra steps."* Steal: the entire
  verification-layer framing for superinstance-api's context brain — tiles are patches, and they need
  probes, not just provenance. Avoid: a heavier review bar / gatekeepers; make claims *falsifiable*, not
  *harder to file*.
