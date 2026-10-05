# Grabbable Tools — the lab's catalog

Doctrine (Casey, 2026-09-29): **not a monolithic application — a collection
of grabbable tools and platforms.** Every discovery ships as a standalone
piece others can lift. Grab = copy the file; everything here runs alone.

## GPU / VLM tools

- **vlm-sanity-probe** — `experiments/c2_probe_vision_path.py`
  3-cell probe (text-only / image+no-think / image+think) that localizes a
  VLM's failure to vision-tokens vs text-path vs sampler in one run, on any
  VLM, with VRAM/temp guard and fail-loud JSON receipts. Swap MODEL_ID.

- **skip-tower-quantizer** — `experiments/c2_probe_skip_tower.py`
  PROVEN on-silicon (attempt-5b KEEP): NF4-quantize the LM while holding the vision tower + projector
  in bf16 (`llm_int8_skip_modules`). If this restores image coherence, the
  recipe is "never quantize the tower on small GPUs" — lift the loader block.

- **nf4-vlm-loader** — the C1 recipe inside any `c2_*` script:
  `BitsAndBytesConfig(load_in_4bit, nf4, double-quant, bf16 compute,
  device_map="auto")`. Runs a 4B-class VLM on a 6GB card (17.5 tok/s text).

## Experiment discipline (pattern tools)

- **pre-registration** — `proposals/runs/*-plan.md`: frozen delta + gate
  written BEFORE code runs. No post-hoc loosening; overrides get booked
  honestly as KILL.

- **guard + fail-loud receipts** — every script's `preflight()`/`main()`:
  VRAM ≥1024 MiB free, temp ≤80°C, and a JSON receipt written even when the
  run dies (exception traceback booked, verdict KILL). Never a silent fail.

- **honest-booking culture** — mechanical gates can pass while frozen
  clauses fail; the clause wins (see attempt-2 booking). Both KEEP and KILL
  are first-class results.

- **floor-law-fit** — `tools/floor_law_fit.py`
  Fit + validate a discovery-floor power law (D12p/D12n pattern): log-log
  regression of C(p)=C0*(2p-1)^-beta on a designated fit subset, then
  HELD-OUT coverage check — does the fitted constant predict floors at
  p values it never saw, without refitting? G1 fit quality (R^2 >= 0.8),
  G2 coverage + non-vacuous bound; fail-loud JSON receipt either way.
  Stdlib-only. `python tools/floor_law_fit.py --points pts.json --fit 0.3,0.4 --heldout 0.6,0.7 [--alpha 1.92 --w 8 --out receipt.json]` (or `--example` self-test). Smoke 2026-10-03: PASS, R^2=1.0, held-out ratio 1.0.

- **corr-floor-probe** — `tools/corr_floor_probe.py`
  Paired-stream discovery-floor prober (d12q pattern): N paired agents, W
  questions/step, correlation p + noise eps — finds the T at which max-|corr|
  discovery recovers partners >= acc bar, and emits C_emp = W*T_floor*|2p-1|(1-2eps)^alpha.
  Stdlib-only, deterministic, fail-loud JSON receipt.
  `python tools/corr_floor_probe.py --p 0.45,0.55 [--t-grid ... --n 32 --w 8 --out r.json]` (or `--example`). Smoke 2026-10-03: PASS.

## Coordination platform (lives in SuperInstance/quilt-i2i)

- **i2i-ledger worker** — live shared semantic memory:
  `POST /book`, `GET /near?q=`, `GET /since?ts=` at
  https://i2i-ledger.casey-digennaro.workers.dev — any agent with curl.
  Skill file: `skills/i2i-ledger/SKILL.md` (HTTP or plain-git transport).

- **HANDOFFS** — `docs/HANDOFFS.md`: delegable open questions with exact
  deliverables + claim protocol (`books_to: handoff:<id>`).

## GPU instrument tools

- **gpu-ramp-receipt** — `tools/gpu_ramp_receipt.py`
  Measures the WSL2 GPU idle-ramp slowdown curve (INSTRUMENT-01 law: every
  GPU measurement on a ramping box reports a ramp receipt — no exceptions),
  verifies recovery (>=0.6s synced load restores >=97% of hot), and writes a
  fail-loud JSON receipt even on KILL. Run with the elephant-gpu venv:
  `/home/eileen/venvs/elephant-gpu/bin/python tools/gpu_ramp_receipt.py --delays 0,5,10,20 --out receipt.json`. Smoke 2026-10-02: CLEAN, recovery 0.989 of hot.

- **control-ladder** — `tools/control_ladder.py`
  Generic POS + expect-red negative-control harness (stdlib-only), lifted from
  tonight's PROVEN CAN-1 pattern (canary.py control_ladder, BOOKED PASS G1-G4).
  A detector is trusted only after it fires on tampered input (red rungs) and
  stays quiet on clean input (POS); raising counts as fired; a ladder with no
  red rungs is VOID (tautology), never PASS. Library API or CLI
  (`--selftest`, or `--rungs file` of `name|red|expr` lines). Exit 1 = FAIL,
  fail-closed JSON receipt.
  `python tools/control_ladder.py --selftest` — smoke 2026-10-03: PASS, tautology & blind-spot both FAIL exit 1.

- **law-floor-check** — `tools/law_floor_check.py` — checks measured sample-size
  T floors against a `C/s^alpha` scaling-law bound (s = (2p-1)(1-2eps)) with the
  D12o gate battery (G1 coverage / G1b looseness / G2 W-monotonicity); fails loud
  at degenerate p=0.5. Verdict KEEP/KILL, honest receipt.
  `python tools/law_floor_check.py --results results/d12o_law_p_generalization.json --p 0.7 --out r.json | --selftest`

- **judge-chunk** — `tools/judge_chunk.py` — chunked batched rule-judge with
  stimulus-major interleave (pattern lifted PROVEN from CM1-r6, booked
  2026-10-04: monolithic 36-item judge batch scored pass 0.0 while the SAME
  items in 3x12 stimulus-major chunks scored 0.67 — judge-state SIZE is a real
  failure mode). Items JSON + rule -> interleaved chunks (round-robin over
  stimulus groups, spread never slab) -> one batched typesafe/System One call
  per chunk (retry-once, fail-loud) -> per-item gate booleans, per-chunk and
  overall pass rates, r6 cost bar (chunk wall sum <= bar x est monolith wall,
  booked honestly), one JSON receipt. Token at use-time from
  ~/.config/typesafe/token, never echoed. Stdlib-only. Exit 0=KEEP / 1=FAIL
  (cost bar or zero pass) / 2=fail-loud.
  `python tools/judge_chunk.py --items items.json --rule rule.txt [--chunk-size 12 --model jev-latest --cost-bar 1.5 --out r.json] | --selftest`
  TEST receipt 2026-10-04: selftest OK (chunking spread/coverage/slab-split,
  gate parsing, fail-loud inputs) — selftest caught two real interleave bugs
  live before any API call (index round-robin and group-dealing both produced
  single-stimulus slabs; fixed to group round-robin item-by-item then slice);
  live 2-item smoke vs jev-latest: both gates true, walls 0.45/0.25s, receipt
  written (cost bar honestly tripped at chunk-size 1 — overhead dominates
  tiny workloads).

- **law-ks-gate** — `tools/law_ks_gate.py` — two-sample KS law-fidelity gate (pattern lifted from the
  W8b/W9a law-check doctrine + PIDFIRE-1's self-KS tau bracket: when you own the generator, drift is
  exactly measurable — resample the reference and gate on KS): observed sample vs generator-resampled
  reference -> KS statistic D (sup |ECDF diff|, exact-equal-value handling, scipy-cross-checked) +
  seeded permutation p (exact when C(na+nb,na) small, add-one MC otherwise); KEEP iff D <= bar AND
  p >= alpha (both clauses, either failing books FAIL). Stdlib-only, fail-loud rc=2, JSON receipt.
  `python tools/law_ks_gate.py --a ... --b ... [--bar 0.4 --alpha 0.05 --out r.json] | --a-file/--b-file | --selftest`
  TEST receipt 2026-10-05: selftest 6/6 — selftest caught three of its own bugs live (KS loop stopped
  at first pointer exhaustion, mid-jump evaluation on shared values broke identical-D=0, non-finite
  check only in the parser not the library entry); then caught a wrong CONTROL pin (expected D>0.8 on
  a 2-sigma shift, scipy-confirmed truth 0.7 — pin fixed, gate untouched); live example KEEP rc=0
  (D=0.125, p=1.0), shifted/bimodal FAIL rc=1, receipt results/law_ks_gate_example_2026-10-05.json.

- **reloc-gate** — `tools/reloc_gate.py` — semantic-identity gate for relocated code
  blocks (pattern lifted PROVEN from EP-1d, commit 5fbf882 2026-10-05: the G-DRY
  block moved wholesale with "no semantic delta" claimed in the message — this
  mechanizes that claim): extracts a named block (start/end substrings) from a file
  at two git refs via `git show`, normalizes (blank/comment/trailing-ws lines
  dropped), requires EXACT line-sequence identity. Read-only, never mutates the
  repo. Exit 0=IDENTITY / 1=RED / 2=fail-loud (bad ref, missing marker — caught
  live: a path that only exists at the new ref rc=2s honestly).
  `python tools/reloc_gate.py --file F --start "S" --end "E" [--ref-old HEAD~1 --ref-new HEAD] | --selftest`
  TEST receipt 2026-10-05: selftest 3/3 — selftest caught its own PASS-control bug
  live (fixture excluded a content line, tool correctly RED'd it; fixture fixed, not
  the gate); live EP-1d move 5fbf882~1 -> 5fbf882 on the G-DRY block: IDENTITY rc=0,
  26 content lines match exactly; tamper control RED; missing-ref/path rc=2.

## When you add a tool

Append it here with: name — path — one line on what it does. If it needs
more than a copy to use, it's not grabbable yet.

- **fleet_board.mjs** — `tools/fleet_board.mjs` — project work lanes onto a
  quilt-canvas as fabric cells (grid address, receipt dials, dependency
  links). Needs a quilt-canvas-tui clone for `fabric.mjs`
  (`CANVAS_FABRIC=/path/to/bridge/fabric.mjs`); optional
  `LANES_FILE=your-lanes.json` to project your own lanes. Dogfood receipt
  2026-09-29: drove the live canvas ONLINE, both chiaroscuro modes, live
  EFFECT through the socket — and found two upstream bugs (argv/env drift,
  peer divergence) reported with receipts.

- **typesafe-batch** — `tools/typesafe_batch.py` — one-call batched
  typesafe/System One judge: state + named questions JSON -> answers, with
  the retry-once / fail-loud / flat-latency pattern from cm1_relay_r4/r5.
  `python tools/typesafe_batch.py --state s.json --questions q.json [--model jev-latest] [--out r.json]`
  Token read at use-time from ~/.config/typesafe/token (never echoed).
  LIVE receipt 2026-10-01: 2-question smoke vs jev-1.13.0, 0.41s, both noul returned.

- **checkpoint-guard** — `tools/checkpoint_guard.py` — reusable
  embedding-checkpoint save/verify/resume (pattern lifted from
  `experiments/c5_paired_action.py`): atomic fsync'd save, exact-key match
  before resume (input fingerprint, key-order insensitive), archive-by-rename
  invalidation, corrupt-file fails safe to full run. Stdlib-only.
  `CheckpointGuard(path, key).try_resume()` / `.save(records)`;
  CLI `--path ck.json --info | --invalidate | --selftest`.
  SELFTEST receipt 2026-10-01: selftest OK + live save/resume/example + info.

- **farm-queue-flip** — `tools/farm_queue_flip.py` — safe `farm/queue.json` entry
  flipper: JSON validation, atomic write + archive copy, `--set-farm-fired`, `--note`,
  `--list`, `--dry-run`, and the doctrine as a gate — experiments can't be armed
  (`blocked` -> `queued`/`running`) unless their `prereg` is committed in git
  (exit 2, refuses loudly). Stdlib-only.
  `python tools/farm_queue_flip.py --id <id> --status queued [--note n] [--dry-run|--list]`
  TEST receipt 2026-10-01: live flip on copy of real queue (gate pass), uncommitted-prereg refused rc=2, malformed JSON refused rc=1, queue stayed valid JSON.

- **perm-ci** — `tools/perm_ci.py` — two-sample significance in one stdlib-only
  file (pattern lifted from E3 perm-exact + COMPOSITE-0 bootstrap lanes):
  permutation p-value (exact when C(n,na) small, else seeded Monte-Carlo with
  add-one so p never claims 0) + percentile bootstrap CI on mean/median diff,
  with a KEEP/KILL/NULL-BOOKED verdict — nulls are first-class, non-finite
  input fails loud (rc=2). Seeded, deterministic, booked receipts.
  `python tools/perm_ci.py --a 1,2,3 --b 10,11,12 [--stat median] [--out r.json]` | `--selftest`
  TEST receipt 2026-10-01: selftest OK (4 checks incl. honest-null + p=1/3 exact
  small-n + NaN rc=2); worked example live, receipt written.

- **fresh-clone-witness** — `tools/fresh_clone_witness.py` — verify the sealed
  manifest from a pristine clone of HEAD (pattern lifted PROVEN from tonight's
  FR-2/VX-1/MR-1 lane): clones the ref into a throwaway tempdir, re-derives
  every sealed digest from the cloned bytes — the phantom-seal class (green
  locally, RED from the outside) is invisible in the working tree and glaring
  here. Optional `--run-pins` runs the clone's own unittest suite. Never
  mutates the repo; exit 0=PASS / 1=RED / 2=fail-loud; `--selftest` carries a
  GOOD control (HEAD clean) + RED control (tampered sealed ledger tripped).
  `python tools/fresh_clone_witness.py --ref HEAD [--run-pins] [--out w.json] | --selftest`
  TEST receipt 2026-10-04: selftest 2/2 (GOOD @9ca04e5 0-drift, tamper RED
  witnessed); live witness HEAD -> PASS 0 drift, receipt
  results/fresh_clone_witness_2026-10-04.json.
- **holdout-gate** — `tools/holdout_gate.py` — held-out prediction gate for
  power-law bounds (pattern lifted PROVEN from D12o/D12p): fit C on the FIT
  subset only (conservative max, y <= C/x^alpha), then gate held-out points on
  G1 coverage + G2 non-vacuousness (min ratio 0.02) — a bound that predicts
  everything is VOID, booked FAIL, never PASS. Seeded bootstrap CI on the
  tightest ratio, one JSON receipt, exit 0/1/2. Stdlib-only.
  `python tools/holdout_gate.py --pairs '[{x,y,role},...]' --alpha 1.92 [--out r.json] | --pairs-file f.json | --selftest`
  TEST receipt 2026-10-03: selftest 6/6 (clean-law PASS + CI bracket,
  law-break FAIL on coverage, vacuous FAIL on G2, no-hold VOID rc=2,
  negative-x rc=2 — pins caught two real bugs live: min() crash and missing
  positivity guard in run_gate); live both directions: law-consistent data
  (C=800, a=1.92) -> PASS tightest=1.000 rc=0; law-violating data -> FAIL
  coverage rc=1. Note: gate is strict — round held-out y DOWN, rounding up
  trips coverage honestly.

- **ensemble-corr-census** — `tools/ensemble_corr_census.py` — rerun-ensemble
  correlation census (pattern lifted PROVEN from QG7b, booked INTERMEDIATE rho
  0.787): given per-run score vectors from R reruns of the same computation
  (+ optional subpop masks / binary labels), computes mean pairwise Spearman
  on mask intersections (primary), ragged-subpop label agreement vs run0
  (secondary), and books ENSEMBLE~1-2-DRAWS / REFUTED / INTERMEDIATE per
  pre-reg bands (default 0.9/0.5). Stdlib-only Spearman — scipy cross-checked
  500/500 exact. Run it before quoting any best-of-R ensemble as R-fold
  robustness.
  `python tools/ensemble_corr_census.py --runs runs.json [--hi 0.9] [--lo 0.5] [--out r.json]` | `--selftest`
  TEST receipt 2026-10-03: selftest 8/8 (ties/mono/anti/mask-intersection/ragged
  labels/NaN rc=2); worked example rc=0 INTERMEDIATE rho 0.8333, receipt written.

- **floor-scan** — `tools/floor_scan.py` — T-floor extractor for accuracy-vs-T
  curves with the D12q lesson built in: a floor at the grid edge is a quantized
  bound, not a measurement, so it's flagged PINNED_LOW (or NEVER) instead of
  silently entering a fit. Optional C_emp = W*T*s^alpha with the D12q-corrected
  signal s = p*(1-2eps), plus an optional law gate (C_emp <= bound on RESOLVED
  floors). JSON receipt, exit 0=KEEP / 1=FAIL / 2=fail-loud input.
  `python tools/floor_scan.py --curves c.json --bar 0.9 --w 8 --p 0.3 --eps 0.1 --alpha 1.92 [--c-bound 60 --strict --out r.json] | --selftest`
  TEST receipt 2026-10-03: selftest 8/8 (selftest caught its own wrong-layer
  degenerate-s check live — fixed to pin run_scan's rc=2 refusal); worked
  example: T_floor=40, C_emp=20.66 @ s=0.24, KEEP rc=0.

- **soc-probe** — `tools/soc_probe.py` — avalanche-susceptibility critical-point
  prober (pattern lifted from PIDFIRE-1's ternary-fire core): seeded forest-fire
  CA sweep over per-step ignition prob p, chi = Var(size)/<size> per point,
  KEEP only on an interior peak (edge peak = grid didn't bracket = honest KILL).
  Stdlib-only, O(grid) memory, fail-loud rc=2.
  `python tools/soc_probe.py --n 32 --ts 0.05,0.2,0.5,0.8,0.95 --t-total 4000 --t-transient 1000 [--growth 0.02 --draws 2 --out r.json] | --example | --selftest`
  TEST receipt 2026-10-04: selftest 4/4 (interior-peak KEEP, edge-kill honest KILL,
  chi finite, same-mean variance pin) — selftest caught three of its own bugs live
  (bytearray -1 state, mid-pass grid mutation breaking synchronous spread, run()
  dropping the growth arg -> forest death, all fixed); worked example rc=0 KEEP,
  peak p=0.8 chi=1.61, 0.38s, receipt results/soc_probe_example_2026-10-04.json.

- **nullvar-calib** — `tools/nullvar_calib.py` — one-parameter null-variance
  floor calibrator (pattern lifted PROVEN from D12u1, booked KEEP 2026-10-04:
  k=0.657 closed a ~400x model-vs-harness floor gap on ONE lumped parameter,
  4/4 held-out covered): given cells {name, mu, scale, floor, role}, sigma =
  k*scale/sqrt(T) with the discovery prob P(N(mu,sigma) > max-of-n-nulls)
  computed analytically over a cached seeded null-max stream (bit-identical
  reruns); fits k by worst-cell |log ratio| on the FIT subset (coarse grid +
  golden-section), then gates G1 held-out coverage (band 1.5x) and G2
  fit-spread — if one k can't serve the fit cells, the gap is structural and
  books honest FAIL. Stdlib-only, fail-loud rc=2, JSON receipt.
  `python tools/nullvar_calib.py --cells cells.json [--n-nulls 31 --cover 1.5 --spread 1.3 --out r.json] | --example | --selftest`
  TEST receipt 2026-10-04: selftest 9/9 (D12u1 reproduction k_hat=0.6532 vs
  booked 0.657, holdout-break FAIL, structural-spread G2 FAIL, determinism,
  4 fail-loud inputs) — selftest caught two real bugs live (sigma grew as
  k*scale*sqrt(T) instead of /sqrt(T); cached standard-unit null draws were
  compared against mu without scaling by sigma — both flagged by
  everything-inf before any verdict); worked example rc=0 KEEP, g1 4/4,
  g2 worst 1.128, receipt results/nullvar_calib_example_2026-10-04.json.

- **worstcase-calib** — `tools/worstcase_calib.py` — one-parameter worst-case (minimax) calibration fit
  (RENAMED 2026-10-04 from minimax-calib / tools/minimax_calib.py: "minimax" named the optimization
  criterion, not the MiniMax provider — name collision confused humans, Casey asked for de-branding.
  The minimax criterion remains; NO AI provider is involved — stdlib-only, no network, no keys.
  Pattern lifted PROVEN from d12u++, booked CALIBRATED 2026-10-04: kappa=0.246 closed a 2.7x
  worst-cell gap on 12 cells with ONE lumped parameter): given cells {name, skeleton, measured},
  fits model = skeleton * kappa**exp by minimizing worst-cell |log(model/measured)| over a
  deterministic coarse log-grid + golden-section refine — no RNG, bit-identical reruns. Gates:
  G1 worst-cell ratio <= band (1.3 default, both sides), G2 kappa in sane band; unfittable gaps
  book honest FAIL, never PASS. Stdlib-only, fail-loud rc=2, JSON receipt.
  `python tools/worstcase_calib.py --cells cells.json [--exp 1.0 --lo 0.1 --hi 1.0 --band 1.3 --out r.json] | --example | --selftest`
  TEST receipt 2026-10-04: selftest 10/10 (scale-recovery kappa~=0.25, unfittable FAIL, exp=2
  sqrt recovery, determinism, 4 fail-loud inputs) — selftest caught a real golden-section bug
  live: (sqrt(5)-1)/2 is 0.618 not 0.382, points were swapped so the fit converged to a
  non-optimal kappa; worked example rc=0 CALIBRATED kappa_hat=0.2515, worst ratio 1.019,
  historical receipt (pre-rename): results/minimax_calib_example_2026-10-04.json.

### onboard.py — fleet-standard credential onboarding (Casey 2026-10-04)
Every grabbable tool that touches a provider registers itself in `tools/onboard.json`
(var name, keyfile name, optional extracted-config path) and inherits the onboarding CLI:

    python tools/onboard.py --tool typesafe-batch   # status + paste-ready fixes for one tool
    python tools/onboard.py --all                   # doctor: the whole fleet, rc=1 if anything required is missing
    python tools/onboard.py --tool i2i-ledger --json receipt.json

Status resolution per variable: env → keyfile (name-only grep, values never read) →
extracted config copy → MISSING with a fix hint. **Values are NEVER printed** — output
is statuses and paths only; the selftest plants a fake secret and asserts it never leaks.
House rules this encodes: keys read at use-time only; declaring a tool in the registry
is part of "done" for any provider-touching tool; new env vars go in onboard.json, not
in per-tool folklore.

### qcell_sim.py — exact small-circuit cell evaluator (GPU, batched)
Batched statevector evaluator for qcell genomes (n<=12 qubits). Returns exact p(targets), balance,
best_target, union, and optional shot samples with a sha256 receipt_id. One file, one job, cell-slot ready.
Conventions are receipt-calibrated (see proposals/runs/QG1-exact-census.md): balance = min(p000,p111);
angles in units of pi; q0 = MSB; gates h,x,rx,rz,cx,crx,swap.
Usage: `python tools/qcell_sim.py --genome '[["h",0],["cx",0,1]]' --shots 512` | `--selftest` | `--receipt out.json`
- `qcell_oracle.pt`: QO1 MLP (64x3) predicting P(stream crosses bar 0.45 | champion state: gen/len/v/cv + 67-gate hist). Val AUC 0.9510. Input norms: gen/12, len/6, hist/6; v,cv raw. See results/qo1_oracle/.
- systemone_proxy.py — System One API wrapper; every teacher call HMAC-booked to ~/.config/systemone/call-ledger.jsonl (state, questions, answers, probabilities, latency). ask()/ledger_stats(); CLI --stats / --state. The distillation corpus grows by using the teacher (wide-scope P-1).
- `deepinfra_ideate.py` — multi-model ideation rounds over the DeepInfra cheap/cached roster (prompt in, JSONL out; captures reasoning_content for reasoning-channel models; token read at use-time). LIVE lane 09-30 (Casey-directed): rounds in scratch/ideation/. Do NOT archive as stray.

- **corpus-filter** — `tools/corpus_filter.py` — validity filter for results-corpus
  receipts (pattern lifted from the S6a two-witness reconciliation): scans a dir of
  JSON receipts, excludes harness-invalid/KILL files, bad JSON, and non-finite (NaN/Inf)
  values — every exclusion booked with a reason, never silent. Tolerant row extraction
  (grid: / probe: like s6a), `--min-rows` fail-loud gate (exit 2), `--selftest`. Stdlib-only.
  `python tools/corpus_filter.py --dir results --out corpus.json [--min-rows 40] [--selftest]`
  TEST receipt 2026-10-01: selftest OK (1 kept / 3 excluded incl. NaN + KILL) + live run
  on results/ — 1243 rows kept, 60 files excluded, corpus JSON written.

- **ci-gate** — `tools/ci_gate.py` — paired bootstrap CI gate for KEEP/KILL
  calls (pattern lifted from B1H-CODA's tail gate): two paired score vectors ->
  bootstrap mean-delta CI, PASS only if CI clears 0 in the positive direction
  (a fully-negative CI books FAIL, not PASS). Fail-loud FAIL-INPUT on length
  mismatch / n<min_n / non-finite scores. Stdlib-only (no numpy), seeded,
  deterministic. Exit codes: 0=PASS, 1=FAIL, 2=FAIL-INPUT.
  `python tools/ci_gate.py --base 0.61,0.55,0.70 --treat 0.65,0.53,0.82 [--alpha 0.05 --n 5000 --seed 7]` (or `--pairs-file scores.json`, `--selftest`)
  TEST receipt 2026-10-01: selftest OK (up-shift PASS / down-shift FAIL — caught
  and fixed the signed-CI bug live: constant negative delta must FAIL, not PASS)
  + 2x5-question smoke: mean_delta 0.05, CI [0.008, 0.092] excl 0 -> PASS rc=0.

- **skill-store** — `tools/skill_store.py` — grabbable Voyager-style verified-skill
  library (pattern lifted from `experiments/skill_library.py`, VOYAGER-SKILLLIB
  purity 39/39): JSON-backed store of prompt+code+family skills. **Retrieval is
  semantic by default** — at store time the skill's name+description+when-to-use
  text is embedded once with Cloudflare Workers AI `@cf/baai/bge-m3` (1024-d,
  free tier) and the vector is cached inside the record via the same atomic
  temp+fsync+rename write; **if CF is unreachable the record is written with
  `vector: null` and the write is NEVER blocked on the network** (`--embed`
  backfills later, resume-safe: it skips already-embedded skills). At search time
  the query is embedded once and ranked by cosine. **Ranking contract (blend
  rule): cosine primary, Jaccard token-overlap as tiebreak — and as the sole
  score when embeddings are unavailable.** If embeddings fail (offline / no
  credential / no cached vectors) retrieval falls back to the pre-upgrade
  deterministic Jaccard ranking transparently, and the output line is marked
  `MODE: JACCARD-FALLBACK (<reason>)` so a caller can never mistake a fallback
  for a semantic result. `--no-semantic` forces the Jaccard-only control path.
  Credentials read at use time and never echoed/hardcoded: env `CF_API_TOKEN` ->
  `/mnt/c/Users/casey/key.txt` -> wrangler OAuth (auto-refresh on 401); every
  error string is scrubbed of any credential read. Stdlib-only (urllib for CF),
  no pip deps, no ollama, runs anywhere; O(batch) memory (48-text embed batches).
  Dedupe by sha256, atomic fsync'd writes, archive-by-rename `--reset`,
  fail-loud rc=2. Verification stays the caller's gate (store only what passed).
  `python tools/skill_store.py --db sk.json --add "prompt" --file skill.py --family text [--when "..."] [--tag t] | --search "q" --k 3 [--no-semantic] | --embed | --get id | --list | --reset | --selftest`
  TEST receipt 2026-10-02 (semantic upgrade): selftest OK 6/6 hermetic +
  `tools/test_skill_semantic.py` 6/6 FAIL-FIRST pins PASS (each pin carries a
  positive control that exhibits the failure it guards). Pin 1 live-CF proof:
  query "keep receipts honest" ranks "verify claims against re-executed evidence"
  above a "receipt format" keyword decoy under semantic mode (cos 0.633 vs 0.585)
  while the Jaccard-only control inverts the ranking (decoy first) — the upgrade
  is real, not cosmetic. Pins also cover offline fallback marking, store-with-
  network-down (`vector: null`), no-token-leak on error paths, resume-safe embed
  cache, and the mixed cosine/Jaccard blend rule. **Honest boundary: semantic
  ranking *quality* is probed, not gated, here** — the evidence base for bge-m3
  intent->artifact retrieval is pinch0's 10/10 rank-1 probes (commit b639aea);
  this tool ships the retrieval path + fallback semantics, not a quality gate.

- **wt-floor** — `tools/wt_floor.py` — bandwidth-time partner-discovery floor
  prober (pattern lifted from `experiments/d12l_noise_floor.py`): seeded
  simulation of N channels / W streams, greedy argmax-correlation partner
  identification, reports per-T accuracy, T_floor at the 0.9 bar, and the
  D12l law check — s=(2p-1)(1-2eps), floor within W*T <= 600/s^2. Noise
  hurts (J1) pinned in selftest. Stdlib-only, fail-loud rc=2.
  `python tools/wt_floor.py --p 0.6 --eps 0.05 --w 4 --n 16 --ts 25,50,100 --draws 3 [--out r.json] | --selftest`
  TEST receipt 2026-10-02: selftest OK (4 checks incl. J1 noise-hurts);
  live run p=0.6/eps=0.05/W=4/N=16 -> T_floor=25, within_bound=True, receipt written.

- **sym-verify** — `tools/sym_verify.py` — standalone executable answer
  verifier for generate-then-check loops (pattern lifted PROVEN from
  `experiments/rest_em_loop.py`: 8/8 accept + 12/12 reject smoke). No LLM
  judge: regex `Answer:` extraction, strict int equality (arith) or sympy
  simplify + frozen rational-probe property test (symb, optional dep).
  One JSON receipt, exit 0=accept / 1=reject / 2=FAIL-INPUT, `--selftest`
  negative-control battery, stdin mode.
  `python tools/sym_verify.py --kind arith --target 132 --text 'Answer: 132' | --kind symb --target '4*x - 3' --text 'Answer: 4x-3' | --stdin | --selftest`
  TEST receipt 2026-10-02: selftest OK (8 accept / 12 reject, 0 failures);
  live examples: arith exact rc=0, symb exact_simplify rc=0 ('-3 + 4*x' ==
  '4*x - 3'), off-by-one wrong_value rc=1.
- **lit-sweep** — `tools/lit_sweep.py` — fabricated-benchmark sweep (pattern lifted PROVEN from
  HB-1/SCOUT-26, booked 2026-10-02): extracts numeric literals from source and flags exact
  cross-matches with booked receipt metrics, plus degenerate-stat detectors (zero-variance
  arrays, p==1.0/0.0, metric identical across every receipt in the sweep). Advisory only —
  FINDINGS means "needs eyes", the human books the verdict. Stdlib-only, fail-loud rc=2.
  `python tools/lit_sweep.py --code experiments/ --results results/ [--out r.json] | --selftest`
  TEST receipt 2026-10-02: selftest 10/10 (cross-match, degenerate p, zero-variance, unanimous
  metric, clean control CLEAN, bad-JSON skipped, missing-dir rc2); live run experiments/ vs
  results/ -> FINDINGS rc=1, 441 literals, 402 receipts parsed, 4 skipped — reviewed: hits are
  benign config constants + honest single-draw arrays, no fraud class present. Receipt:
  results/lit_sweep_2026-10-02.json.

- **corr-exponent** — `tools/corr_exponent.py` — exact + empirical decorrelation
  exponent for paired ±1 streams (pattern lifted PROVEN from D12m/D12n:
  r = p_corr·(1-2eps)², alpha_emp = 1.92 OOS-validated). Seeded sim vs closed
  form per eps, log-log slope fit -> alpha_empirical vs alpha_exact, KEEP/
  ALPHA>1.5 verdict, fail-loud rc=2. Stdlib-only, ~0.1s.
  `python tools/corr_exponent.py --p 0.3 --eps 0.0,0.05,0.1,0.2 --n 16 --t 8000 --out r.json | --selftest`
  TEST receipt 2026-10-03: selftest 5/5; live run n=16 t=8000 — empirical |corr|
  tracks exact to <0.005 at every eps (0.8102 vs 0.81, 0.3630 vs 0.36),
  alpha_empirical 1.983 vs exact 2.0; receipt written.

- **hash_dut.py** — hash customs officer: canary vectors x6 primitives; check any impl (py/js/url) for NAME-COLLISION vs canonical spelling. Found: quilt-dba fnv1a64 is utf16-charCodeAt; UTF-16 itself has two byte-spellings. selftest 13/13.
- **calib-gate** — `tools/calib_gate.py` — proper-scoring calibration battery (pattern lifted from ST3-calibrated-noul / QC-JEV doctrine): given a list of (p, y) predictions, computes ECE (10 bins), Brier, accuracy@0.5, AURC + E-AURC (selective risk-coverage), with an optional KEEP/FAIL gate on ECE/Brier bars. Fail-loud rc=2 on p outside [0,1], bad labels, or empty input. Stdlib-only, deterministic, one JSON receipt.
  `python tools/calib_gate.py --preds preds.json [--ece-bar 0.05 --brier-bar 0.25 --out r.json] | --preds-json '[...]"' | --selftest`
  TEST receipt 2026-10-04: selftest 5/5 (calibrated clean-KEEP, overconfident decoy FAIL, p>1/bad-label/empty rc=2) — selftest caught two of its own control bugs live (perfect predictor at conf 0.9 is honestly ECE 0.1; AURC<0.02 clause impossible for a 0.75-acc control), both fixed; worked example rc=1 FAIL booked honestly (5-item sample, conf 0.7-0.9 at 100% acc -> ECE 0.2).

- **prereg-stamp** — `tools/prereg_stamp.py` — bind run receipts to the committed
  pre-registration plan (mechanizes the pre-registration doctrine, which was
  prose until now): sha256-stamp the plan at run start, embed the stamp in the
  receipt's `prereg` block (`prereg_block(plan)` helper), then at booking time
  `--check` re-derives the stamp AND requires the plan to be committed clean in
  git — post-hoc plan edits, uncommitted, and untracked plans all book FAIL.
  Stdlib-only, fail-loud rc=2. Library: `check(plan, receipt) -> (ok, why)`.
  `python tools/prereg_stamp.py --stamp PLAN.md | --check PLAN.md --receipt r.json | --selftest`
  TEST receipt 2026-10-04: selftest 5/5 (committed-clean PASS, post-hoc-edit
  FAIL, untracked FAIL, dirty FAIL, missing-block rc=2 — selftest caught the
  cwd/git-repo bug live, fixed with explicit cwd); live: real committed plan
  C1-cosmos-edge-boots-plan.md -> PASS rc=0, tampered-stamp receipt -> FAIL rc=1.
