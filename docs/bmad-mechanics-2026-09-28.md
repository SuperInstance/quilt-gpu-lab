# BMAD Mechanics — Scout for the Breakthrough-Transformer Program

*2026-09-28 · lane: bmad-mechanics · sources at bottom · feeds breakthrough-transformer program design*

BMAD = Breakthrough Method of Agile AI-Driven Development (`bmad-code-org/BMAD-METHOD`, MIT, ~tens of
thousands of users). It went through a full rewrite: **v4** (agent personas + story files) → **v6**
(skill-based, right-sized process). Both matter to us: v4 for the *mechanics of context packing and
role separation*, v6 for the *unattended worker contract* — which is nearly a spec for what our
runner lane wants to become. Note the v6 "forge-idea" skill ("pressure-test an idea until it
hardens, proves out, or dies cheaply; a report every run; an artifact only when the idea hardens")
is independently convergent evidence that our assayer/falsifier loop is the right shape.

---

## 1. The structure: roles and artifacts

### v4 pipeline (the classic form)

Roles, each a persona with a YAML dependency manifest (loads **only** the templates/tasks/data it
needs — lean context by construction):

| Role | Does | Produces |
|---|---|---|
| **Analyst** (Mary) | brainstorm, market/competitor research (optional) | project brief |
| **PM** (John) | requirements discovery, FRs/NFRs, epic+story outline | PRD |
| **UX Expert** (Sally) | front-end spec (optional) | UX spec |
| **Architect** (Fred) | technical decisions from PRD | architecture doc |
| **QA / Test Architect** (Quinn) | early test strategy on high-risk areas; later, full review | risk profiles, test designs, gates |
| **PO** (Sarah) | master checklist ("are the docs aligned?"), then **shards** PRD + architecture into per-epic/per-story files | sharded docs, sign-off |
| **SM** (Bob) | drafts next story from sharded epic + architecture + *previous story's Dev/QA notes* | story file (hyper-detailed, self-contained) |
| **Dev** (James) | sequential task execution inside one story | code + tests + completion notes |
| **BMad-Master / Orchestrator** | any-task generalist / web-bundle dispatcher | — |

Artifact chain: **idea → brief → PRD (FRs, NFRs, epics) → architecture → sharded epics/stories →
story → code+tests → QA review → gate → done**, with paths conventionally `docs/prd.md`,
`docs/epics/`, `docs/stories/`, `docs/qa/assessments/`, `docs/qa/gates/`.

The v4 core dev cycle is a *conveyor with notes passed through the story file*: SM reviews the
**previous story's Dev/QA notes** before drafting the next one → draft → (high-risk? QA `*risk` +
`*design` on the draft) → approval → Dev executes tasks sequentially → Dev marks "ready for review"
with notes → QA reviews (and may refactor when safe) → **commit** (the workflow diagram screams
"COMMIT YOUR CHANGES BEFORE PROCEEDING") → QA gate update → story done → loop.

### v6 skill set (the current form)

Roles dissolved into right-sized skills; the artifact chain is the same but every hop is optional:

`bmad-brainstorming` / `bmad-forge-idea` / `bmad-deep-recon` → `bmad-product-brief` / `bmad-prfaq`
→ `bmad-prd` → `bmad-ux` → `bmad-architecture` (produces `ARCHITECTURE-SPINE.md`) → `bmad-spec`
(produces **SPEC.md**, the implementation contract) → `bmad-ticket` (epic envelope + ordered
`tickets.toml`) → `bmad-build` / `bmad-build-auto` per story → `bmad-retrospective` at epic close.

**SPEC.md anatomy** (the whole planning layer condensed into one contract): *Why · Capabilities
with success conditions · Constraints · Non-goals · Success signal.*

---

## 2. The key mechanisms

### 2.1 Plan-first, right-sized ("the expand pattern")
- Two-phase doctrine: planning (cheap, big-context, even in web UI on subscription models) is
  **separated** from execution (IDE agents). Planning inconsistency and context loss are named as
  *the* two failure modes BMAD exists to kill.
- Right-sizing is the core law: "use the smallest amount of BMad that safely fits the change."
  Clear intent → straight to build. Epic-sized → spec + stories. Multi-epic → full planning stack.
  The process **expands only when scope, risk, architectural reach, or coordination demands it** —
  and contracts otherwise. (This is the "expand" planning pattern: intent is progressively expanded
  brief → PRD → spec → stories, each layer answering a narrower question set, never all at once.)
- v6's routing rule after investigation: report **three facts** — *intent gaps* (things you didn't
  say that you'd notice in the result), *irreversible actions*, *footprint*. Clean on all three →
  light path (minimal plan, build, review after). Anything flagged → full written plan first.
- "Fixing the plan is cheaper than fixing the code."

### 2.2 Story-file context engineering (the v4 crown jewel)
The SM packs **everything the Dev agent needs into the story file**: full context, implementation
details, architectural guidance, acceptance criteria, prior-story learnings. The Dev opens *one*
file and needs nothing else. Supporting machinery:
- `devLoadAlwaysFiles` in core-config.yaml: a **tiny** always-loaded decision set (coding
  standards, tech stack, project structure) — kept deliberately lean, pruned as patterns stabilize,
  because "as your project grows... only the standards the agent still needs enforced" belong there.
- Agent YAML dependencies: each role loads only its own templates/tasks/data. Context is a budget.
- Web-planning output is **sharded** (PO agent) so IDE dev agents receive per-epic slices, not the
  whole PRD.

### 2.3 The story/status machine (v6 build-auto worker contract)
This is the most directly stealable artifact. `bmad-build-auto` = one unattended run:
clarify → create/resume **plan file** → implement → review → **terminal status**. Rules:
- **One ticket per invocation. Never picks the next ticket.** Backlog policy and dispatch belong to
  an orchestrator (human or coding session); the worker "owns only its implementation run."
- Plan-file frontmatter is the machine state: `draft → ready-for-dev → in-progress → in-review →
  built → done`, plus `blocked` and `dropped`. The worker **never marks done** — an orchestrator
  or human does (`tickets.py mark <ref> done`). Build leaves the plan at `built`.
- **Orchestrator-owned checkpoints**: `plan_checkpoint` (person approves the story/plan before
  dispatch) and `done_checkpoint` (person pauses after the run). The worker never reads these
  fields; the dispatcher honors them by *when it dispatches*.
- **blocked_reason taxonomy**: unclear intent · intent gap · no subagents · ticket not resolved ·
  version-control metadata not writable · plan failed ready-for-dev standard · missing plan file ·
  implementation verification failed · **review repair loop exceeded 5 iterations
  (non-convergence)** · blocked plan supplied. Blocked is "a routing signal, not a failure signal" —
  it usually means unattended execution became unsafe and a higher layer should take over.
- **baseline_revision**: the canonical revision *before* implementation is pinned in the plan. A
  ticket's commits are exactly `baseline_revision..<next baseline_revision>`. (Capsule commits,
  formalized.)
- **Intent-gap preservation**: if review halts on an intent gap, the tree is reverted *but the
  attempted change is saved as a patch file beside the plan* — concrete evidence of which reading
  was implemented. If the reading was right, `git apply` and resume review instead of re-running.
- **Deferred findings**: real findings that are not this run's problem, written to frontmatter as
  machine-readable data — `summary / evidence / location / severity`, with maybe-false entries
  carrying an if-true grade **+ "(unverified)"** and recorded evidence of what would settle them.
  Explicitly "not a backlog" — the orchestrator decides what happens to them. v6 `bmad-build` also
  writes unrelated findings to `deferred-work.md` instead of scope-creeping.
- "The workflow always tries to leave behind a durable artifact describing what happened."
- Every worker needs subagents for internal review; without them it halts `blocked/no subagents`.

### 2.4 QA as an independent role with its own artifacts (v4 Quinn, carried into v6 review)
Quinn is not a code reviewer; it's a **Test Architect** with a command suite, each producing a
dated artifact:
- `*risk` — probability × impact scoring (1–9); **risks ≥9 trigger FAIL, ≥6 CONCERNS** — run on the
  *draft*, before development.
- `*design` — test strategy per acceptance criterion, P0/P1/P2 priority, before development.
- `*trace` — mid-development: map every acceptance criterion to the test that validates it;
  Given-When-Then traceability matrix; coverage gaps get severity ratings.
- `*nfr` — evidence-based check of the core four (security, performance, reliability,
  maintainability); failures feed the gate.
- `*review` — full assessment **plus active refactoring when safe**, ending in a gate decision.
- `*gate` — PASS / CONCERNS / FAIL / WAIVED. **Advisory, not blocking** — "teams choose their
  quality bar." WAIVED requires reason, approver, expiry date. QA "owns" the gate files in
  `docs/qa/gates/` — parallel authority with Dev, separate artifact trail.
- Enforced test standards: no flaky tests, no hard waits, stateless/parallel-safe, self-cleaning,
  explicit assertions.

### 2.5 Review = triage, and regenerate from the broken layer
"Review is triage, not a dump of every possible note." Findings that belong to this change get
fixed; pre-existing unrelated ones get deferred. And crucially: **if the code is wrong because the
plan was weak, or the plan is wrong because the goal was wrong, it goes back to that layer and
regenerates from there — not patch-the-diff.**

### 2.6 Modes: web planning / interactive build / unattended worker
- **Web bundles** (Gemini Gems / Custom GPTs): run planning agents on big-context subscription
  models cheaply, then carry artifacts into the IDE. Explicitly a cost arbitrage.
- **Interactive build** (`bmad-build`): human checkpoints at plan approval and at done; incremental
  (step-by-step) vs YOLO (rapid, minimal interaction) modes.
- **Unattended worker** (`bmad-build-auto`): the §2.3 contract, dispatched per ticket.
- Plus `bmad-loop` (third-party orchestrator building on the same contract) and
  `bmad-retrospective`: judge the **combined epic result against the evidence it left behind** —
  acceptance verdict + action items, run at epic boundaries.

### 2.7 The attention economy doctrine
Stated outright in the v6 docs: "Human attention is by far the most expensive resource, and the
productivity bottleneck in AI-backed software development... spend your attention where it is
irreplaceable." The whole checkpoint system is an attention-ratioing device: plan approval and
done-marking are where humans are required; everything between is machine territory. Also: fresh
chat per run ("reusing a session can mix contexts and confuse the run"), and v4's BMad-Master
advice to compact context after every story.

---

## 3. What actually works vs. what's ceremony (honest cut)

**Where BMAD beats plain subagent dispatch:**
1. **The story file / plan file as the context boundary.** Plain dispatch ("do X") makes the worker
   re-derive intent or silently invent it. BMAD's packed story file is why dev output aligns —
   the worker never has to guess scope, and prior-run learnings ride forward structurally instead
   of living in chat scrollback.
2. **The status machine + blocked taxonomy.** Plain dispatch has two states: claimed/done. BMAD's
   `blocked` with a *reason enum* converts failures into routing data. The 5-iteration
   non-convergence block is a real discovery — it's the escape hatch from agent repair loops.
3. **baseline_revision pinning.** Turns "what did this run change" from archaeology into a
   revision range. This is capsule-commit discipline with a pointer, not just a message string.
4. **QA before the run, not just after.** Risk-profiling the *draft* (≥9 = don't proceed) catches
   under-specified work before it burns compute. Most dispatch loops only discover this in review.
5. **Deferred findings as data.** The discipline of recording "real, but not this run's problem"
   with evidence and an unverified marker is what keeps reviews from either scope-creeping or
   losing findings.
6. **Intent-gap patches.** Preserving the attempted reading as a diff when a run halts is genuinely
   clever — halts become resumable evidence instead of waste.
7. **Right-sizing as law.** Most framework failure is applying the full ceremony to a small change.
   BMAD hard-codes the escape hatch (light path / Quick Flow) at every layer.

**Where it's ceremony (and admits it):**
1. **Documentation overhead** — the docs' own trade-off list: PRDs, specs, architecture, stories
   all need maintenance; "overusing artifacts can turn useful structures into bureaucracy."
   The 4-phase full pipeline is for ~20+ session projects; our *experiments* are 1-session items.
2. **Persona theater** — Mary/John/Fred/Bob/James/Quinn are prompts, not independent agents; the
   separation that matters is *which context and which checklist each pass loads*, not the voices.
   Pay for the separation, skip the characters.
3. **Advisory gates can rot into rubber stamps** — PASS/CONCERNS/FAIL/WAIVED with "teams choose
   their quality bar" means the gate is only as honest as the operator. (Our answer is stricter:
   pre-registered KEEP-iff/KILL-iff with "never loosen a gate" — don't regress to advisory.)
4. **No idea-selection filter at all** — BMAD assumes the work is chosen. Nothing in it scores
   novelty, uniqueness, or falsifiability. Our assayer (product of three axes, a 1 anywhere kills)
   is genuinely *ahead* of BMAD here.
5. **Trusts prose** — plans and reviews are markdown; nothing is hash-sealed or re-derivable.
   BMAD would fail our own receipt doctrine ("a verdict the ledger cannot re-derive is a claim").
6. **Human-must-mark-done** is right for software products but wrong for a pure experiment loop
   whose gates are already pre-registered — the pre-registered gate *is* the standing approval.

**Practitioner signal (HN):** heavy users report the payoff is real but front-loaded — "tech
speccing and multiple cycles of elicitation are what deal with all the edge cases you normally
only encounter during coding... it does front-load all of the planning brainwork; condensing that
into a couple days of solid speccing is far more productive than spreading it out over months."
And the environment caveat: "most of the time what the agent does will be a product of its
environment" — the harness is the product.

---

## 4. Mapping to our loop

Our loop: **proposer** (proposals/PROPOSER.md) → **assayer** (novelty × local-uniqueness ×
falsifiability, gate drafted) → SPOOL.md pre-registration (claim + KEEP-iff/KILL-iff + feasibility,
sealed before hardware) → **runner** (claims first unchecked QUEUE.md item under guard.py) →
**receipts** (manifest sha256 seals, unittest re-derivation, FAIL-first) → **RESULTS.md**
append-only honest ledger (KEEP/KILL/INCONCLUSIVE/ABORTED all kept) → **falsifier discipline**
(pre-registered gates outrank gem-hunger) → GEMS.md mining.

| BMAD mechanism | Our current equivalent | Delta |
|---|---|---|
| Brief → PRD → spec contract | SPOOL entry (Q / claim / gate / feasibility) | We have it, thinner; v2 fields below |
| Architecture spine + devLoadAlwaysFiles | Contract docs scattered (pyramid contract, cell contract, drift-gate semantics live in per-experiment docs) | **No lean always-loaded decision block** — each run re-derives or inherits nothing |
| Story file (packed context) | QUEUE line (one sentence + gate pointer) | **Thin.** Runner gets intent, not packed context |
| Plan file + status machine | QUEUE checkbox (binary) + verdict | **No in-flight states**, no resume, no machine-readable frontmatter |
| blocked_reason enum | ABORTED (free-text) | No taxonomy; blocked runs aren't routing data |
| baseline_revision pin | Capsule commits (message-scoped) | No revision-range pinning per run |
| Intent-gap patch preservation | INCONCLUSIVE entries note the confound | No artifact of *the attempted reading* |
| Deferred findings | SPOIL of SPOOL ad-hoc; "failures en route (booked)" notes | No formal deferred lane with severity + unverified marker |
| QA `*risk` on drafts | Nothing pre-run (guard is resource-only) | **Under-specified runs can burn the 30-min slot unattended** |
| QA `*trace`/`*nfr` | Falsifier checks gate post-hoc; G7 watt-receipt pending | No mid-run traceability criterion; NFR lane nascent |
| Independent QA role w/ own artifacts | Assayer (independent scorer) — strong | We're ahead; keep |
| Retro at epic close | None — RESULTS grows, nobody judges the arc | **Missing** |
| Receipt sealing + re-derive | **We're ahead** (BMAD trusts prose) | Keep; this is our export |
| Pre-registered gates before hardware | **We're ahead** (BMAD ACs are pre-code but not adversarial) | Keep |
| Idea-selection filter | **We're ahead** (assayer) | Keep |
| Resource watchdog | **We're ahead** | Keep |
| Human attention checkpoints | Cron, fully unattended | Intentional — but see adopt #7 |

## 5. ADOPT / SKIP

| # | Practice | Verdict | Wiring |
|---|---|---|---|
| 1 | **SPEC.md contract anatomy** (Why / Capabilities+success conditions / Constraints / Non-goals / Success signal) | **ADOPT** | SPOOL entry v2 gains two fields: `non-goals:` (excluded confounds — E2's cross-clip pairing bug is the canonical lost war) and `success-signal:` (the verdict rule in one line, distinct from the gate math). Cheap, kills ambiguity at promotion time. |
| 2 | **Plan-file status machine per run** (`draft → ready-for-run → running → judging → built(kept in ledger) → done / blocked / dropped`) | **ADOPT** | When runner claims a QUEUE item it materializes `proposals/runs/<ID>-plan.md` with frontmatter: `status`, `experiment`, `baseline_revision` (git rev-parse HEAD at claim), `gate_id` (the SPOOL entry), `started_at`. Runner writes terminal status; QUEUE box gets checked only at `done`. Gives resume-after-crash for free (plan status survives the guard's abort). |
| 3 | **blocked_reason enum** | **ADOPT** | Extend ABORTED with a reason token: `unclear-gate` · `intent-gap` · `harness-fail` · `resource-guard` · `non-convergence` (repair loop >3). RESULTS schema already takes JSON; add `"blocked_reason"` field. Blocked = routing signal: `intent-gap` items route back to proposer, `unclear-gate` back to assayer. |
| 4 | **baseline_revision pinning** | **ADOPT** | In the run plan (from #2); RESULTS entry cites `baseline: <sha>`. Capsule = `baseline..HEAD`. Makes the manifest's job easier and crash forensics trivial. |
| 5 | **Intent-gap patch preservation** | **ADOPT** | If a run aborts mid-experiment with partial code, runner stashes the attempted diff to `proposals/runs/<ID>-attempted.patch` and references it in the RESULTS entry. The attempted reading becomes evidence, not waste (D13→D13d would have left a trail). |
| 6 | **Deferred findings lane** | **ADOPT** | RESULTS entries gain `## Deferred` bullets: `summary / evidence / severity / (unverified)`; assayer's next pass ingests them as candidate abstractions (deferred ≠ dead). This is SPOOL's missing feeder pipe. |
| 7 | **Pre-run risk pass on high-risk items** (`*risk` analog) | **ADOPT (light)** | Not a persona — a checklist in the run plan: "does the gate decide in ≤1 run? are inputs pinned? is the failure mode a clean INCONCLUSIVE or a muddy one?" Any ≥9-equivalent → `plan_checkpoint`: item waits for eyes before dispatch. Applies to first-of-kind harness only (D1b full-scale, G-lane seats). |
| 8 | **Epic retro** | **ADOPT** | Every N results (or lane close, e.g. after G7+G1+G3): one retro doc — "does the combined evidence still support the story the ledger tells?" Feeds GEMS mining with the arc, not just the atoms. |
| 9 | **Architecture-spine / always-loaded decision block** | **ADOPT** | `docs/SPINE.md`: the ≤40-line set of standing decisions every experiment inherits (cell contract, pyramid contract, drift-gate semantics, verdict taxonomy, receipt law). Runner prompt includes it verbatim; it's sealed in the manifest like the rest. Prune as patterns stabilize. |
| 10 | **"Regenerate from the broken layer"** | **ADOPT (doctrine line)** | Write into assayer spec + runner: an INCONCLUSIVE caused by a badly-specified gate means the *SPOOL entry* gets revised and the run re-derived — never a re-run of the same code hoping for different noise. We already do this by hand (D13→d); make it law. |
| 11 | **Attention checkpoints** (plan approval / done-marking) | **PARTIAL** | Keep the loop unattended (that's the point), but import the *ratio*: human attention only at gate-writes (SPOOL edits — already doctrine) and at `plan_checkpoint` items from #7. Runner never loosens a gate; that's our "never marks done." |
| 12 | Personas (Mary/John/Fred/Bob/James/Quinn) | **SKIP** | Role separation without characters. We have the separation: proposer ≠ assayer ≠ runner ≠ falsifier. |
| 13 | PRD/epic/sprint-status yaml machinery | **SKIP** | QUEUE/RESULTS/SPOOL already are the epic tracker; adding a yaml tracking layer is ceremony with no consumer. |
| 14 | Web-bundle planning | **SKIP** | We're CLI-native; GLM subagents are our cheap big-context lane already. |
| 15 | Advisory gates (PASS/CONCERNS/WAIVED) | **SKIP** | Regression risk. Pre-registered KEEP-iff/KILL-iff with "never loosen a gate" outranks it. WAIVED is the exact shape of a loosened gate. |
| 16 | Expansion packs, UX/creative modules, `refine=true` ticket UX | **SKIP** | Domain mismatch; our story-drafting already happens at SPOOL→QUEUE promotion. |

## 6. The fusion recipe — far-future backcasting × BMAD × receipt discipline

Casey's directive: "think of the breakthrough transformer using a mix of far future
reverse-actualization and BMAD." The synthesis writes itself once you see that **BMAD's PRFAQ is a
backcast** ("stress-test a product concept working backwards from the press release") and our
**receipt is a forensics-grade RESULT entry**. The far future is the PR; the ledger is the proof.
Recipe, per breakthrough target:

1. **Backcast (the reverse-actualization hop).** Write the future RESULTS.md entry first — dated
   far-future, verdict **KEEP**, with the JSON numbers already in it, the exact gate that was
   satisfied, and the one-line note the future-us would write. This is the PRFAQ move applied to
   our ledger instead of a press release. (Template: `"## <ID> — <name> (<far date>)" / verdict
   KEEP / result: {…} / note: "<what this cracked>"`.) If you cannot write a *specific* future
   receipt, the target is not yet an experiment — it's a vibe. The PRD law applies: "complete
   enough that someone else could build it without guessing, and no longer than that."
2. **Extract the gate-set from the receipt (PRD-as-gate-set).** The future receipt *is* the SPEC:
   Why = the note line; Capabilities + success conditions = the JSON fields with their KEEP-iff
   thresholds; Constraints = hardware/seed/token ceilings; **Non-goals = the confounds you're
   refusing to let in (E2's lesson, made structural)**; Success signal = the verdict rule. This is
   SPOOL entry v2, drafted backwards from the receipt rather than forwards from an idea.
3. **Assay it (our export, BMAD's gap).** Assayer scores it (novelty × local-uniqueness ×
   falsifiability, product — a 1 anywhere kills). BMAD has no equivalent; this stays ours.
4. **Expand to the story (BMAD mechanics).** Break the receipt into the ordered run sequence with
   `bmad-ticket` discipline: each run = one session, one goal, gate decidable; the ticket tree
   keeps order and prerequisite edges (`after:` fields); early runs settle the harness patterns
   (give those eyes — plan_checkpoint), later repeats run unattended (build-auto mode). Update the
   spec and re-slice remaining runs "when earlier work reveals a missing constraint" — the
   breakdown is an execution plan, not a promise.
5. **Run under the worker contract (adopt #2–#5).** Claim → run plan with `baseline_revision` →
   status machine → blocked-as-routing → attempt-patch on halt → receipts sealed.
6. **Falsify and judge (independent role, our gates).** KEEP-iff/KILL-iff from step 2, never
   loosened. Deferred findings to the lane (adopt #6). Non-convergence → blocked, back a layer.
7. **Retro the arc (adopt #8).** At the lane's close, judge the *combined* runs against the
   original backcast receipt. The question the retro asks is exactly the reverse-actualization
   loop-closer: **"is the ledger converging on the receipt we wrote, or did the future move?"** —
   and if the future moved, that finding (the delta between backcast and ledger) is itself a
   mined abstraction for GEMS.

The three disciplines interlock: **backcasting supplies the target receipt, BMAD supplies the run
machinery that turns a receipt into an ordered sequence of gated sessions, and our receipt
discipline guarantees the ledger that retro judges is re-derivable, not narrative.** Far-future
supplies the *why*; BMAD supplies the *how*; the manifest supplies the *true*.

## Sources

- BMAD-METHOD README, main (v6): `raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/README.md`
- BMAD-METHOD v4 README + User Guide, tag v4.43.1 (planning workflow, core dev cycle, Quinn QA, devLoadAlwaysFiles)
- docs.bmad-method.org: Choose a Planning Path · Build a Change · Autonomous Development Loops
- SaM Solutions, "Spec-driven development with BMAD Method" (4-phase synthesis, trade-offs table)
- HN threads via Algolia (practitioner reports incl. "Agentic Coding Is a Trap" comments)
- Local: `README.md`, `docs/assayer-spec.md`, `QUEUE.md`, `RESULTS.md`, `guard.py`, `proposals/` (quilt-gpu-lab)
