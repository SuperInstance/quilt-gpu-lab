# Scout report — 2026-10-01 push wave (fleet-triage, quilt-in-git, cot-quilt-lab)

Scout: GPU-lane subagent. Clones in /tmp/scout-*. No GPU run, no other files touched.
House style honored below: pre-register, seed 2718, fail loud, KEEP/KILL/INCONCLUSIVE.

---

## 1. SuperInstance/fleet-triage

### (a) What it claims
- **The synergy claim** (`experiments/synergy.py`, `synergy_results.json`): three
  unrelated-looking failure families are ONE mechanism —
  A. fail-open harnesses (12 repos, 11 sharing one try/except; worse: harnesses print
  `OK:` and exit 0 without ever calling the product — sprint-FAILOPEN corrected the
  count 13→12→10 and sharpened the mechanism);
  B. a resolver that returns 4,789 dead references as confident, specific "this resolves";
  C. FNV-1a-64 hash-observation scoring 0.9586 on a random 80/20 split vs 0.5045 honest
  by-ply — memorization through near-duplicate keys (1-NN over a leaky split).
- **The mechanism, verbatim:** "An instrument reports success unless it has been given a
  way to fail." The falsifiable prediction: *an instrument's power against a KNOWN
  failure predicts its power against an UNKNOWN failure* — if true, cheap trusted
  instruments can score expensive untrusted ones (the only affordable cross-check).
- Sim results (committed): broken harness recall 0.00, fixed 1.00, 85%-instrumented
  0.878; memorization gap sim +0.225 vs real +0.454; n_eff/k = 0.128 (REDUNDANT below
  the 0.5 line); monotone ordering held.
- **BOARD.md**: 7 lanes converged on the same shape — "a well-formed, checkable, wrong
  artifact, and no instrument that can say so." Includes their own retraction: they
  published "max over 4 learners" at n_eff=1.48 — the exact disease we booked in D18
  (REINFORCE-vs-correlation confound from inconsistent targets). Independent replication
  of our lesson, from the other side.
- ci-LANE.md: 23/174 workflows cannot fail (18 are `echo "No CI configured"`); GitHub
  Actions does not gate across workflows; ga4444's "2000/2000 PASS" differential compares
  two column-only solvers while 74% of the dataset has gaps (green differential ≠ correct
  claim); connect4 had a >900× uncommitted regression and a truncated ground-truth file;
  4/4 mutants killed only after assertions were added that *decide* the outcome.
- docs/GPU-EXPERIMENTS.md §0: eight measurement rules (std==0 → INCONCLUSIVE never
  PASSED; CPU-fallback-as-GPU = fabrication; controls must vary the audited thing by a
  different path) — our house style, independently derived. docs/RTX4050-WORKLIST.md is
  a full pre-written GPU docket (A1 pie-minimax closure is their #1; A4 determinism lab
  and D2 stochastic-world Cog thesis are novel to us) — harvest source, not urgent.

### (b) What's checkable locally (CPU, minutes)
- `synergy.py` re-runs on CPU, but `OUT = "/workspace/experiments/synergy_results.json"`
  is a hardcoded absolute path — dies on final write in a clean clone. **Same
  hardcoded-output-path class as quilt-cell-bridges 44/63** → add to our CORROBORATION
  LEDGER. (Committed results JSON exists, so the claim is checkable without a rerun.)
- **`canfail.py` is cited as the lane's artifact but is NOT in the pushed repo**
  ("written locally, nothing pushed" per ci-LANE.md §7). Claimed-artifact-not-in-clone —
  note, don't scold; the report is explicit about it.
- Reproducible from the clone: the ga4444 gap-carry mechanism is pure C arithmetic; the
  FNV leak result is pure CPU. `docs/GPU-EXPERIMENTS.md` rules are directly quotable
  into our G7/DEGENERATE specs.

### (c) Experiment — XP-A "instrument-transfer" (rank 1, value-per-watt)
- **Title:** Instrument-transfer: does known-failure detection power predict
  unknown-failure detection power on our own verdict machinery?
- **Plan:**
  1. Build ~10 seeded (2718) corrupt-receipt variants of our own RESULTS/verdict path:
     6 known ops (ST1-AUDIT's list: sign_flip, wins_over, verdict_flip, tau_off,
     seed_drop, denom_swap) + 4 held-out novel ops (NaN-injection, silent dtype cast,
     split-boundary off-by-one, receipt copied from a prior commit, plausible-truncation).
  2. Score each instrument — verdict_gate.py static pins, canfail-style step parsing
     (reimplemented, since canfail.py isn't pushed), and an optional tiny GPU classifier
     on receipt text — for recall on known vs held-out ops.
  3. KEEP iff Spearman(known-power, unknown-power) across the instrument×variant grid
     ≥ 0.7 AND every instrument beats chance on held-out ops; KILL if any instrument
     with high known-power flunks held-out ops (synergy mechanism dead → gates must be
     per-failure-class, no transfer).
- **Cost:** ~40 min CPU, ~10 min GPU (optional classifier), 0 API spend.
- **Feeds directly:** ST1-AUDIT (already "next queue item" — this is its falsifiable
  spine), DEGENERATE-gate spec, TRUNC-B; corroborates the synergy report with our own
  E4 (threshold said KEEP on a degenerate dataset) and D18 (max over confounded arms).

---

## 2. SuperInstance/quilt-in-git

### (a) What it claims
- 8-line README, that's the whole repo (single skeleton commit). "The Quilt lives inside
  Git": **dials are files, ticks are commits, rewind is checkout, hooks are the
  runtime.** Clone = full Quilt, bundle = air-gapped transport, branch/worktree =
  parallel exploration. Lane 7 (unbuilt) = hook runtime on branch `poc-hooks`.
- Implicit honesty claim: the repository *is* the Sheet, so git machinery (history,
  diffs, hooks) can enforce cell integrity instead of a separate runtime.

### (b) What's checkable locally
- Nothing executable — it's prose. But the design collides favorably with three things
  we already have: qthe/D10 receipts (digest-addressed cell state), G7 watt-receipt
  adoption law ("no receipt → run VOID" — a hook is its natural enforcement point),
  and SIG-1 (signed-seal design note, whose pinned attack is *verifyChain passes on
  public-rule repair, verifySignatures refuses* — i.e., chain-repair).

### (c) Experiment — XP-B "git-hook receipt gate vs corruption corpus" (rank 2)
- **Title:** A pre-commit hook enforces cell honesty: refuses every pre-registered
  corruption class, zero false rejects.
- **Plan:**
  1. Generate a seeded (2718) synthetic history of ~120 commits; each commit message
     embeds a qthe-style receipt = digest(cell state + seed + dial vector). Pure digests,
     **no keys** — stays outside SIG-1's Casey-gated key-management boundary while
     producing its acceptance evidence (the chain-repair attack, in hook form).
  2. Pre-register K mutation classes: dial-changed-without-receipt-update; receipt
     reused from an earlier commit (chain-repair); truncated receipt; FNV-1a-64
     collision pin (use fleet-triage's own L4 poor-avalanche finding as adversarial
     input); a GPU-derived cell (30-s tick, determinism-receipted like E4b/D10) replayed
     with a mutated seed.
  3. Hook refuses all K classes and accepts all clean commits. KILL if any class passes
     the gate or any clean commit is rejected. INCONCLUSIVE if FNV-64 collisions force a
     digest upgrade mid-run (report the collision rate — itself a finding about 64-bit
     cell addressing).
- **Cost:** ~25 min CPU, zero GPU, zero API.

---

## 3. SuperInstance/cot-quilt-lab

### (a) What it claims
- README + NOTES only (two skeleton commits). Stdlib-only cut of a sibling agent's
  "agent-321" design doc: **any API is a Provider, any pipeline is a list of stages,
  any cell is pure `z_in -> z_out`** — proven with FAIL-first pins (ENOENT receipt
  before implementation), receipts over claims.
- **The three lanes:**
  - A `engine-core` → core/{providers,guards,stages,cell}.py (Pipeline/Fan/Fold, Cell
    adapter, guards) + pins.
  - B `sheet-pens` → sheet/{model,pen_json,pen_tsv,algebra}.py: cell =
    id/kind/label/16 dials/4 neighbors/listens/emits/body/hash; three pens
    (python/JSON/TSV); FNV-1a-64; sheet algebra.
  - C `pipeline-stubs` → pipelines/cot_decompose.py end-to-end on stub providers +
    envelope pin.
- Deliberately deferred: real provider keys, semantic canon sort (W2.3, lives in
  quilt-edge-lab), TUI, Mothquantum/typesafe adapters ("interfaces land in core;
  adapters land when a key does"). Attribution in the source doc treated as INFERRED
  until verified (their own SC doctrine applied to themselves).

### (b) What's checkable locally
- Nothing runnable — no code yet. But lane C is the exact seam our queued **G1
  local-LLM-seat spike** needs: a Provider interface with guards/stages/envelope
  semantics, into which a local 4050 model (D15b-proven: Qwen2.5-3B 4-bit, 4.2 GB peak,
  fits 6 GB) or a cloud cell (GLM-5.3-flash, DeepSeek V4 Flash, typesafe.ai judgment
  cells) plugs without changing the contract. Building lane A/C first is shared
  infrastructure, not a fork of effort.

### (c) Experiment — XP-C "envelope contract through a real provider" (rank 3, most GPU-testable lane = C)
- **Title:** The pure z_in→z_out cell contract survives a real model as Provider —
  local GPU arm vs cloud arm vs stub ground truth.
- **Plan:**
  1. Implement the minimal lane-A/C envelope (prompt → guarded z_out receipt) with three
     provider arms: stub (exact function = ground truth), local Qwen2.5-3B-4bit on the
     4050 (seed-pinned), cloud GLM-5.3-flash.
  2. Gates: malformed-envelope refusal 100% (turn their ENOENT pin into a live guard);
     local arm byte-identical across 3 replays at seed 2718 (determinism receipt);
     well-formed-envelope rate ≥ 0.95 local, cloud rate reported beside it (no gate on
     cloud — it's the comparison, not the claim).
  3. Every run priced in watt via G7 receipt format (power.draw poll already specced in
     G7). KILL the "pure cell" claim if guard bypasses or nondeterminism appears at
     fixed seed.
- **Cost:** ~1 h GPU (≈5–8 Wh on the 4050), one cheap cloud lane (~$0.01).
- **Sequencing note:** this wants the G1 seat work (queued) as its local-serving layer;
  fire after G1 or as its first consumer, not in parallel with it.

---

## Ranking (value-per-watt) and queue fit

| rank | experiment | watts | feeds |
|---|---|---|---|
| 1 | XP-A instrument-transfer | ~0 (CPU, optional 10-min GPU) | ST1-AUDIT, DEGENERATE gate, TRUNC-B, G7 |
| 2 | XP-B git-hook receipt gate | ~0 (CPU) | SIG-1 acceptance evidence, G7 enforcement, D10/E4b determinism receipts |
| 3 | XP-C envelope local provider | ~5–8 Wh GPU | G1 seat harness, cot-quilt-lab lane C, cloud-cell pricing |

Cross-cutting corroborations for the ledger (no new runs needed):
- fleet-triage's retracted "max over 4 learners at n_eff=1.48" ≈ our D18 confound —
  same disease booked independently on both sides; cite both in the DEGENERATE spec.
- `synergy.py`'s hardcoded `/workspace/...` output path ≈ quilt-cell-bridges
  hardcoded-output class (CORROBORATION LEDGER entry).
- canfail.py claimed-but-not-pushed: benign (declared in-report), but the DEGENERATE
  spec should require artifact-presence checks on cited receipts.
- fleet-triage GPU-EXPERIMENTS.md §0 rules 1–8 are house-style-compatible; adopting
  rule 5 ("control varies the audited thing by a different path") verbatim in pre-regs
  costs nothing and would have caught D18.
- docs/RTX4050-WORKLIST.md is a harvestable pre-written GPU docket (their A1
  pie-minimax closure, A4/D3 determinism canon) — flag for the main queue's next
  scoping pass, not this wave.
