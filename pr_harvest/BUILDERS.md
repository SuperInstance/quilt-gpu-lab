# PR-HARVEST / BUILDERS.md

Per-repo reading: builder philosophy (3 lines) / best move / blind spot / ONE concrete helpful action.
Helpful actions are **drafted** in `REPLIES-draft.md`; nothing was posted to GitHub.

---

## quilt-in-git — "dials are files, ticks are commits, hooks are the runtime"
1. The repository is the runtime; git objects are the only storage primitive worth trusting.
2. "Now" lives in refs, "history" lives in commits, "integrity" lives in notes — three layers, each
   honest about what it can't carry.
3. Every feature is paired with a **refusal** (no ticks → exit 1) and a pinned honest boundary.
- **Best move.** The air-gap round-trip (#4): a bundle is the *only* surviving copy, and the journal is
  **regenerated from pure history** and verified byte-identical. The receipt logic being deterministic
  *is* the disaster-recovery mechanism. That is the single best idea in this repo.
- **Blind spot.** The whole edifice assumes a POSIX shell + git and *pins* that it doesn't travel on a
  plain clone — but there is no stated migration path for a consumer that only ever clones. The
  honest-limit is documented, not mitigated.
- **Helpful action (drafted).** Offer an **independent replication** of the air-gap round-trip on our
  side (`git bundle` → delete origin → import) with a *different* git version, reporting byte-identity
  of the regenerated journal — closes "verified only on the builder's git".

---

## tidepool — "the row law is a contract, verified by a stranger's code"
1. A shared format is only as good as a second implementation that can catch the first.
2. Never invent a measurement (non-finite guard); a receipt states what was *emitted*, not what was
   accepted.
3. FAIL-first against pristine main, then let the fresh-chain pin find its own bugs pre-commit.
- **Best move.** Writing the 32 pins with **deliberately independent code** (own canonicalizer, own
  fnv1a-64, zero `tools/` imports) — the only way to avoid a shared-blind-spot bug in both subject and
  judge. The found-by-running bug (hashing with vs without the empty `hash` key) proves it pays.
- **Blind spot.** Independence is *claimed* but both implementations live in one language, one repo,
  one author — a cross-language check is the stronger version and is not done.
- **Helpful action (drafted).** Offer a **cross-language independent canonicalizer** (Python) that we
  run against their JS row law and report digests for all emitted rows — a genuinely independent judge.

---

## quilt-Kuramoto — the salvaged archive that became the fleet's best census instrument
1. An archive with documented loss is a *calibration target*, not an embarrassment.
2. Citizen-instrument: it does not rival the resolver, it consumes it.
3. Every number ships with its FP budget and its indexing limitation.
- **Best move.** Turning its own `docs/MISSING.md` gap-list into an **independent cross-check** for the
  resolver's 253 FILE_MISSING — two instruments that never shared code agreeing is real evidence.
- **Blind spot.** The census (and this referral) rides a **shallow-HEAD index**; the debt number is
  therefore a lower bound that will be quoted as if it were absolute.
- **Helpful action (drafted).** Offer our lab to run the **full-history (deep) citation census** on
  quilt-Kuramoto and report the delta vs the shallow number — directly closes their stated limit.

---

## fleet-triage — "classify the debt before you count it"
1. A count without a class taxonomy becomes a scare number; taxonomy first, count second.
2. Two independent instruments agreeing is evidence; one instrument is a claim.
3. Docs-only referrals; currency upgrades only on an external merge.
- **Best move.** #4's cross-domain link: predictive-paddle's self-referential attractor **is** the
  mechanism behind stale citation prose — "only a different-path instrument sees the freeze." Naming a
  shared mechanism across a game PR and a doc-census is the fleet's strongest reasoning move.
- **Blind spot.** Referrals depend on the resolver's own health; if PATH_PRECISE_ONLY is 49.2% FP,
  the *fixable* class inherits that noise and the "12/12 spot-verified" sample is small.
- **Helpful action (drafted).** Offer to **independently re-run the AMBIGUOUS sample** (the 264-class)
  with a differently-built matcher and report agreement — closes the single-instrument risk on the
  class they actually recommend fixing.

---

## pong-quilt — "the experiment loop is the product; the game is the substrate"
1. Every round = builder + play-tester; the round *plays its own fix* and reports what it caught.
2. Baselines are draws of a distribution, not points — say so, and mark the ceiling when you find it.
3. Honesty is architecture, not tone: no-claim markers in source + summary + a test.
- **Best move.** #88's discovery that **the v1 tag does not reproduce itself** (raw `Math.random()` in
  the swan path) — it invalidates a whole class of "baseline" numbers and the round *chose* to publish
  it rather than paper over it. Then #91/#93 turn that into a distribution-ceiling statement.
- **Blind spot.** Round-count/PLAYLOG/README bookkeeping is now a second full-time job (order pins,
  files-not-tests arithmetic, docs edited after the suite). The loop's bureaucracy is approaching the
  experiment's cost — and #93's own sizing ("one guard line + 4 pins + registry/README/PLAYLOG")
  shows the ratio is unflattering.
- **Helpful action (drafted).** Offer an **independent reproduction** of the v1 draw distribution
  (run the v1 tag N times on our node, report the L1/L2 spread) — a second machine confirming "no
  point value exists" is exactly the evidence the round can't produce for itself.

---

## AI-Writings — "the essay is a data structure for what the substrate learned"
1. Write the essay from the run; the run's numbers are the spine, the metaphor is optional.
2. Reverse-actualization: write the life first, let mechanics catch up.
3. Every piece ends with honest unknowns — the thing not yet tested.
- **Best move.** "Trust relocates blindness; it does not delete it" — the essay argues *against* its own
  metaphor's comfort, which is rare and correct.
- **Blind spot.** The dialect can launder an unverified mechanism into a memorable sentence ("dials are
  perception") — the study notes are the only thing tethering it to evidence, and they are prose.
- **Helpful action (drafted).** One **probe offer**: test whether a dial-sized vector carries the
  decision content of the full report (≥95% label match) — turns "dials are perception" from a claim
  into a measured statement. (Only if it fits their lane; low priority.)

---

## quilt-tools — "currency is earned by an event in another repo"
1. The referral graph is a pure function of booked edges; the view is recomputed, never stored.
2. Weight upgrades only on an external, verifiable merge — never self-declared.
3. Pins assert the *distribution* (mass, ranking, tie-breaks by name), not just edge existence.
- **Best move.** The **weight law**: an edge's mass can only come from a merge event in the *to-node's*
  repo, booked CANDIDATE → VERIFIED on merge. It makes the fleet's provenance currency unfakeable.
- **Blind spot.** Every VERIFIED upgrade is asserted by the pins as a hand-maintained number in
  `seed.mjs`; the link from "merged PR exists" to "edge upgraded" is manual, so a silent drift between
  reality and the book is possible and unpinned.
- **Helpful action (drafted).** Offer a **checker that verifies each VERIFIED edge against its recorded
  merge SHA** (does the cited PR really exist, is it merged, does it cite the from-node by name?) —
  turns the weight law from discipline into a pin.

---

## quilt-edge-lab — "pre-register, receipt, and bound the rule on both sides"
1. Every claim is a receipt; every rule gets a control that can kill it.
2. A control that is *degenerate with the treatment* is not a control — say so and build the real one.
3. Deterministic chains are how a distributed edge proves what happened.
- **Best move.** #4: proving C-ROT invariance holds where rotation *is* a symmetry (wave 2, 0/6000)
  **and** refuses where it is not (wave 3, 6000/6000). A rule bounded on both sides — the harvest's
  best methodological move, bar none.
- **Blind spot.** #1's `/colo-report` is honestly INCONCLUSIVE (all runs still SIN) — the cross-colo
  diversity claim the feature exists to make has never been observed; the infrastructure is built
  ahead of any evidence it discriminates.
- **Helpful action (drafted).** Offer an **independent re-run of the C-ROT pins on a second substrate**
  (our torch CA implementation) — they explicitly write "adopt only after re-running these pins on the
  target substrate", so this is directly requested work.

---

## pie-minimax — "compute the optimum, don't label it"
1. Ground truth computed, not labelled, so every number is exact.
2. A weakened thesis is still a result; book it either way.
3. GPU ramp (INSTRUMENT-01) before any timing — borrowed from our lab, applied correctly.
- **Best move.** The **duplicate-row audit**: discovering 180,361 rows are tree-path duplicates of
  2,423 distinct boards (48.6% multi-optimal) *after* the run, and reporting it as a spec correction
  rather than burying it.
- **Blind spot.** The MLP closure (~1.0) was measured on the duplicated split; the distinct-board
  evaluation that would decide whether "nonlinear closes ~1.0" is a real statement or a sampling
  artifact is owned but not yet run.
- **Helpful action (drafted).** Offer the **distinct-boards re-evaluation** (2,423 boards) on our
  4050 — cheap, and it settles P1 FAIL-HIGH cleanly. This is a true independent replication request.

---

## quilt-arcade — "novel ML, quarantined in experiments/, cited across the mesh"
1. Port the mechanism 1:1, then let your substrate falsify it (or not).
2. Separate aim-value from estimator accuracy — a system can win for the wrong reason.
3. Book custody before the outcome exists; mirrors must be byte-for-byte.
- **Best move.** #6: publishing v1's **sealed FAIL** with the traced root cause (standing-mass dilution,
  ~9 events to converge) while the *advisory* still wins (94% vs 86%) — the value came from predictive
  aim, not estimator accuracy, and they said so.
- **Blind spot.** Three versions of the same experiment in one PR (v1 FAIL / v2 / v3) with two
  unrelated deltas each; the lane is iterating constants and mechanisms at once, which is exactly the
  churn chiaroscuro's R8 exists to stop.
- **Helpful action (drafted).** Offer an **independent reproduction of the H1/H2 dilution law** in
  torch on the 4050 (predict convergence time from `mass / per-commit gain`), so the "port-cadence
  mismatch, not a flycx defect" conclusion is verified off the builder's own harness.

---

## chiaroscuro — "pre-register, seal, FAIL honestly, close the lane"
1. Rules committed before the run; FAILs kept in history; R8 kill honored; no goalpost moves.
2. Isolate one variable; require a distinguishing control; bound the rule both ways.
3. A lane closes when constants stop helping — "new evidence, not new constants."
- **Best move.** The **sealed anti-drift gate that blocked their own good feature** (#11: H1 4/4
  recovered but H2 FAIL on the literal-term overlap) — the gate refused a merge that would have
  inflated the score on degenerate inputs. Culture over win.
- **Blind spot.** The discipline is now heavy enough to slow learning: #9→#10→#12→#13 is four PRs to
  fix one constant and close one lane. Correct, and *expensive*; any claim that quibbles with a
  constant risks a four-PR investigation. Also a real portability bug: `token_stream.py` writes its
  receipt to a hardcoded `/root/...` path.
- **Helpful action (drafted).** Two: (a) a **correctness/portability note** on the hardcoded receipt
  path (#1), and (b) an **independent numeric verification** of the `arcsin(rho)` bound that closed
  the KC-geo lane (#10/#12/#13) plus the un-run Sobel agreement test (#1 lane B) — real value, cheap,
  and it's the kind of replication their own doctrine demands.

---

## Patchwork-experts — "provenance-trust is not measurement-trust"
1. Patches are claims; claims need a test analog (probes), and the misses are the trust signal.
2. Limits must name a failure mode, not a genre.
3. Practice the honesty you preach: tag every claim PREDICTED / CITED / MEASURED.
- **Best move.** The **failure-class taxonomy** (instantiation / knowledge / relay / trust) with the
  prediction that trust failures arrive last and do the most damage — building the measurement layer
  *before* the quilt is big enough to be worth gaming.
- **Blind spot.** It is a suggestion doc with no runtime in the repo; every mechanism is PREDICTED and
  the pins (P1–P5) are proposed, not implemented — so it cannot yet demonstrate its own thesis.
- **Helpful action (drafted).** Offer to **implement P1–P5 as a working check script in a fork** (we
  run a verification-heavy fleet and can show the pins firing on the repo's current tree) — converts
  their PREDICTED proposal into a MEASURED one, which is the whole point of the doc.
