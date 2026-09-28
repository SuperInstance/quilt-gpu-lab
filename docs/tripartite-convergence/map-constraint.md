# Map: the "Constraint Satisfaction" Agent onto the Running Fleet

*Part of the tripartite-convergence series. The tripartite agent splits into three
postures; this doc maps the **engineer** — the one whose only question is
"are all constraints satisfied RIGHT NOW?" — onto what the fleet actually runs
today (2026-09-27).*

The engineer is not a planner and not a dreamer. It doesn't ask "could this be
better?" and it doesn't ask "what should we want?" It asks one question —
**is anything violated at this instant?** — and it answers by *acting*: commit
the min-error state, or abort. Ties go to the current state. Below, five
running artifacts, each named, each pinned to the slice of the engineer it
instantiates.

---

## 1. The constraint stepper — `eos-seed/exoj_kernel/src/optimization.rs`

**What it enforces:** total tracking error — `Σ_rows |score(row) − target(row)|`,
integers only — must never increase. Every cell commit is the argmin over the
three switch states {Blocked → Muted → Positive}, scored against the *whole
stored log* before the state is "permanently committed."

**Which part of the engineer:** this is the question and the enforcement, in
one loop.

- `Objective::total_error` **is** "are all constraints satisfied RIGHT NOW?" —
  a single integer, recomputable at any moment, no gradient, no history
  dependence beyond the log itself.
- `run_pass` is commit-min-error: flash the candidates, score, keep the
  minimum. The strict inequality (`if err < best_err`) means **ties keep the
  current state** — hysteresis, which is itself a second-order constraint
  ("thou shalt not oscillate"). The engineer never flips a switch without a
  strictly better world.
- `run_to_convergence` halts when error stops improving — the engineer stops
  honestly when no further satisfaction is available, rather than churning.
- `run_pass_cached` / `InstanceLogicOptimizer::sweep` is the per-frame form:
  the same question, asked continuously over a *bounded cache* of historical
  rows — O(chunk), not O(corpus). The constraint check is cheap enough to run
  every frame forever, which is what "RIGHT NOW" demands.

## 2. The constraint compiler — `eos-seed/exoj_kernel/src/inverse_physics.rs`

**What it enforces:** targets must be *derivable from the log itself* (the
identity compiler — no human labels) and must sit *inside the quantizer's
reachable set* (per-sign medians rounded to power-of-two steps "so targets
sit inside the quantizer's reachable set").

**Which part of the engineer:** the precondition half. Before the stepper can
check satisfaction, someone must state constraints that *can* be satisfied.
`infer_targets` makes the constraint set honest twice over: derived from
evidence (the fabric's own structure), and rounded into reachability. An
unsatisfiable target is a compile-time refusal here, not a runtime lament.
The engineer checks the world against constraints; inverse physics guarantees
the constraints were never fantasy.

## 3. The immovable evidence — `eos-seed/quilt_storage/src/fabric.rs`

**What it enforces:** append-only history (rows are memcpy'd in and never
rewritten; `append` is the only mutator), format integrity (`bad magic — not
an EOS fabric` on open), schema integrity (`vector width must match fabric
cols` panics), and single-writer / never-blocking-reader concurrency (mmap,
"the file IS the database," header is the only metadata).

**Which part of the engineer:** the evidentiary constraint. A satisfaction
check is only as honest as the log it scores. Because the fabric is
append-only, the stepper's error metric cannot be gamed retroactively —
"RIGHT NOW" is always measured against what actually happened, byte-for-byte,
in the order it happened. The fabric converts the engineer's question from an
opinion into a measurement.

## 4. The floor — `quilt-gpu-lab/guard.py`

**What it enforces:** the physical envelope — free VRAM ≥ 1024 MiB, temp ≤
80 °C, wall clock ≤ 1800 s. Preflight refuses to *start* unless the envelope
holds; in-flight it samples `nvidia-smi` every 5 s and **terminates the
experiment** on any breach; the 30-minute wall stands "regardless of GPU
state."

**Which part of the engineer:** "RIGHT NOW" made literal. This is the
engineer's physical half: the constraint check is a live sensor poll on a
background thread, not a hope or a budget. And the enforcement matches the
stepper's exactly — violation means the commit never lands (process
terminated), with the breach string recorded. E6 (harness self-test, 2026-09-27)
proved the bite: guard refuses low-VRAM and high-temp preflights, accepts a
healthy one, and the receipt manifest detects tampering. The floor is not
decorative.

## 5. The frozen ruler — `quilt-gpu-lab/RESULTS.md`, D7 quant-drift

**What it enforces:** the *portability* constraint — satisfaction must survive
transformation. Concretely: probe verdict-flip rate < 0.05 ceiling, with the
similarity threshold tau taken "from fp16 cal split only, frozen for all
precisions." The constraint is fixed *before* the treatments run, then
checked — the same fix-then-check shape as commit-min-error.

**Which part of the engineer:** the constraint set's own survival. D7's answer
is the cleanest result in the ledger: **NF4 at 4 bits holds flip-rate 0.0**
(0/240 probes at every precision; mean cos drift 0.984 at NF4, pair-sim
delta 0.017). The engineer's constraints compress from 32 bits to 4 without
one verdict flipping — satisfaction is portable.

D7 also stands for the whole ledger's discipline, which is the engineer's
posture at fleet scale: every experiment pre-registers its acceptance
constraint *before* running (D2's 1.10× margin, D4's +0.15 bar, E10's +0.05,
E11's +0.30, D12's 0.10) and reports KEEP/KILL/INCONCLUSIVE honestly —
including KILLs (E2b, E10, D13/d/b/c) that were booked, not dressed up. The
lab is one long commit-min-error loop where the target is written down first
and the error is scored against a log no one can edit afterward.

---

## The claim

**The fleet's Constraint agent is now a pre-registered, hardware-floored,
evidence-locked hysteresis loop.** It writes its constraints down before it
acts (preregistered margins in RESULTS.md; tau frozen from the fp16 cal split;
targets compiled into the quantizer's reachable set by `infer_targets`), it
checks them continuously against evidence it cannot rewrite (the append-only
fabric scored by integer error; `nvidia-smi` sampled every five seconds
against the 1 GB VRAM floor and 80 °C ceiling), and it enforces at every
commit boundary with the same two rules — commit only on strict improvement,
tie keeps the current state — from a single 2-bit ternary cell all the way up
to killing a live GPU process on breach. And as of D7, its constraints are
known to survive 8× compression without a single flip: the engineer's answer
to "are all constraints satisfied RIGHT NOW?" is not just *yes* — it is *yes,
and it stays yes at 4 bits.*
