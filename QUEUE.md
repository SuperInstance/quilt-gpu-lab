# QUEUE — the chip's standing worklist. Runner claims the first unchecked item.

- [x] E1 real-glyph-contrast (2026-09-27 KEEP) — real ffmpeg frames through elephant's contrastive encoder, heldout separation vs untrained baseline
- [x] E2 flow-beat-vs-pool (2026-09-27 INCONCLUSIVE) — 40x20 flow+beat L0 tokens vs mean-pool floor on real frames (pyramid-contract test)
- [x] E3 cast-heldout control (2026-09-27 KEEP) — elephant's full vmf pipeline on real frames with cast-heldout split (does separation survive unseen content?)
- [x] E4 next-room transformer (2026-09-27 INCONCLUSIVE — dataset too thin, E4b revision needed) — <2M-param model predicting next-room from room-history over glyph-cell logs (JEV-temporal probe, 10 min budget)
- [x] E7 vjepa2-in-cells (retry after pillow+torchvision install) — V-JEPA 2 ViT-L (Meta, downloaded) embeddings through the same cell contract; judged on separation, drift-gate, and surprise vs local heads — 2026-09-27 ABORTED — 2026-09-27 KEEP
- [x] E5 quantization probe — int8 vs fp16 embedding drift: does room-sense survive quantization for portable deployment?
- [x] E6 harness self-test — guard breach paths, torn-queue resilience, results append integrity
- [x] E2b flow-beat-revision (2026-09-27 KILL — hand-crafted L0 dead, learned L0 next) — per-clip temporal-delta correlation only + within-texture clip pair (two moving sources); E2's cross-clip pairing conflated static-content distance with the temperature axis
- [x] E4b next-room-revision — 60s clips (~240 cells), interleaved walk, blocked split, constant+markov-1 baselines reported alongside

- [x] E8 encoder-swap leaderboard — aggregate E1/E3/E7 (+E9) readings into one table: separation gap, drift-gate, surprise dims per encoder. The scoreboard for the swap-and-hunt protocol. — 2026-09-27 INCONCLUSIVE
- [x] E9 ijepa stills — 2026-09-27 KEEP
- [x] E10 invariance race — ternary gate vs a stateless sign-tracker (persistence/dead-reckoning) on the SAME frames; does the gate beat a lookup table, or is it a fancy debounce circuit? The ground-truth pole.
- [x] E11 debounce kill — pre-registered adversarial test: run the gate on held-out sign-patterns and see if it loses to a 2-bit dead-reckoning baseline; a loss here kills the 'ternary = learning substrate' thesis honestly.
- [x] D1 look-again-scale (reach-bound fold sweep) — jev-quilt G21 Law-7 effect at scale — 2026-09-27 KEEP
- [x] D1b look-again sweep (bundled corpus, oracle/safe-fold/Look-Again, scaling by items+readers) — ready-to-run packaging of D1 for tonight's RTX 4050 pass: committed item set (no network needed for a smoke pass), GPU-accelerated dense readers with a clean CPU/offline hashing fallback. Run: `python -m experiments.d1b_lookagain_sweep` (smoke) or `D1B_FULL=1 python -m experiments.d1b_lookagain_sweep` (docket-scale) — 2026-09-28 INCONCLUSIVE (smoke; full-scale D1B_FULL=1 ready)
- [x] D2 qthe ternary matmul kernel — parity + speedup vs fp16 (prices C1) — 2026-09-27 KEEP
- [x] D3 statevector ceiling — GPU executor for micromoth — 2026-09-27 KEEP
- [x] D6 fun scorer + seed bank — cargo-line-tycoon — 2026-09-27 KEEP
- [x] D7 quant-drift probe — fp16/int8/NF4 reader portability — 2026-09-27 KEEP
- [x] D5 probe foundry — seeded canon/distortion triples, content-addressed, hash-split — 2026-09-27 KEEP
- [x] D10 cudaclaw cell kernel — n-qubit cell + ternary passband — 2026-09-27 KEEP
- [x] D4 canon-lora (smoke INCONCLUSIVE; full-scale recipe ready) — 2026-09-27 INCONCLUSIVE
- [x] D14 qthe timbre channel proof — zero-bit-cost context-keyed ternary embedding — 2026-09-27 KEEP
- [x] D12 substrate falsification (relational vs isolated) — 2026-09-27 KEEP
- [x] D13 relational intelligence growing (learned addressing) — 2026-09-27 KILL (naive Hebbian reward does not converge)
- [x] D13b relational addressing (confidence-weighted reward) — 2026-09-27 KILL (stronger signal, still no convergence)
- [x] D13c relational addressing (REINFORCE with baseline) — 2026-09-27 KILL (3rd RL variant fails)
- [x] D13d shared-key discovery (correlation, not reward) — 2026-09-27 KEEP (1.0, cracks what 3 RL variants couldn't)
- [x] D16 embedder readability (tiny MLP reads tone class) — 2026-09-27 KEEP (0.93)
- [x] D17 compiler compression at scale — 2026-09-27 KEEP (0.789, momentum 0.034; invisibility vs compressibility tension)
- [x] D15 read-the-channel (VLM LoRA reads tone channel) — 2026-09-27 INCONCLUSIVE (full: 0.351 vs 0.266, positive but under gate)
- [x] D15b read-the-channel v2 — 2026-09-27 KEEP (full: tuned 0.9413 vs base 0.0781, margin 0.8632)
- [x] D19 transitional-jepa (relational transition kernel) — 2026-09-27 KEEP (ternary 0.0101 vs markov1 0.0179; ternarization cost -0.0009 ≈ free)
- [x] D20 transitional-jepa ablation (nonlinear + identity) — 2026-09-27 KEEP (linear sufficient: nonlinear -3%, identity -0.2%)

- [x] D1b look-again sweep (full-scale) — 2026-09-27 KEEP (look-again 0.8569 vs best-single 0.6884, lift +0.1684)
- [x] D21 perception=ledger (kernel on real receipt-chain data) — 2026-09-27 KILL (imbalance ≡ d_mu is conditional, not unconditional)
- [x] D22 ternary-forgiveness (backfilled 2026-09-30: RESULT existed, QUEUE line was missing — same drift class as D18/c9b39b4) — 2026-09-27 KILL (forgiveness-via-privacy-noise falsified)
- [x] D15c tone-channel generalization (held-out tone classes) — 2026-09-27 KILL (tuned fails held-out class -0.0516; adapter memorizes seen-class patterns)
- [x] D18 correlation-discovery scaling (does D13d generalize? N∈{8,32,100,300} × corr strength sweep) — 2026-09-28 INCONCLUSIVE (correlation CONFIRMED at all scales; the contrast half FALSIFIED) — [backfilled 2026-09-28: ran without a QUEUE claim, flagged by the music-study lane's RED test]
- [x] E12 room-dial reader (JEPA reads elephant dials: mood/volume/presence) — 2026-09-28 KEEP (R² 0.81/0.96/0.95; frozen I-JEPA reads staged dials beyond luminance)
- [x] E13 nonlinear-carrier dial read (backfilled 2026-09-30: RESULT existed, QUEUE line missing — drift class of D18/c9b39b4) — 2026-09-28 INCONCLUSIVE
- [x] E13b nonlinear-reader dial read (backfilled 2026-09-30: RESULT existed, QUEUE line missing — drift class of D18/c9b39b4) — 2026-09-28 INCONCLUSIVE (partial recovery)
- [x] E25 fold-phase transition (where does the dial read die under carrier nonlinearity? sweep N2 fold amplitude, per-dial critical point) — pre-registered in SPOOL.md — 2026-09-28 INCONCLUSIVE (monotone decay real; distinct criticals volume 1.0/mood 1.5/presence 2.2; mood not longest on k16 clause)
- [x] E18 sauna/plunge contrast (is the walk between rooms more readable than the rooms? pairwise gap vs two-absolutes baseline) — pre-registered in SPOOL.md
- [x] E15 encoder-swap dial read (is I-JEPA special? DINOv2/CLIP/V-JEPA 2 leaderboard) — pre-registered in SPOOL.md — 2026-09-28 KEEP
- [ ] G7 watt-receipt instrumentation — extend guard.py's nvidia-smi poll to also sample power.draw (same query, same 5 s cadence) and integrate mean-power × wall-seconds into the guard_summary every RESULTS entry already logs, plus emit one g7-watt-receipt@1 per run (schema: fleet-seeds docs/G7-WATT-RECEIPTS.md; validator: fleet-seeds scripts/g7_validate.mjs, selftest 16/16, independent live-verify by lane 56-f: pass-measured admitted, void-missing-energy refused); adoption law "no receipt → run VOID" — a verdict that ships without a schema-valid receipt is VOID regardless of result; makes every run this chip does pricable in watt-hours the way API spend is pricable in dollars
- [ ] G1 local-LLM-seat spike — 7B–8B Q4_K_M instruct model (Qwen2.5-7B-Instruct class, ~4.4 GB GGUF) served locally on the 4050 (fits the 6.1 GB ceiling; start 4k ctx + Q8 KV cache, 8k is the stretch goal), probed ollama → llama.cpp → fail-closed: run fleet-seeds scripts/g1_seat_harness.mjs (stdlib-only, selftest 8/8, no-seat path exits 2 with a g1-void-record@1 — both live-verified by lane 56-f) over a moth-seal-certified battery registered before the run, testing the 10 predictions sealed pre-hardware in fleet-seeds docs/g1/predictions.json (sha256 fb98ca29…, registered 2026-09-28 with zero seat traffic: 7 new S1–S7 + 3 carried playbook predictions) — converts the 45-c gateway starvation KILL (0/96 answered @2000 tokens) into a completion-rate-vs-budget curve (2000/4000/8000): no token ceiling, transcript-on-disk, AS-SAID per house seat protocol
- [ ] G3 quantization-erosion vs exact twins — same weights, fp16 exact twin vs Q8/Q5/Q4 GGUF at one fixed certified seed: capability-erosion curve (fixed-text perplexity + one reasoning battery) priced per quant level, KILL where the quantized twin stops being the same model — cheapest first G-lane run since D7's quant plumbing (fp16/int8/NF4 reader portability) already exists; G3 adds the matched-seed exact-twin control D7 does not claim

- [x] D23b hidden-angle relational semantics (deep n-qubit cell semantics lane) — 2026-09-30 KILL (0.75 at T=200 vs 0.90 bar; non-monotone; angles = degraded mirror of coupling, not the memory) [backfilled: booked in RESULTS.md, never claimed in QUEUE — D18 precedent c9b39b4]

- [x] QG1-residual localize the 28/1920 anchor misses — 2026-09-30 NAME (swap/wire-order convention, Fisher 7.0e-19; BH 28/28; census script's radians bug exposed en route — pi-units reproduces booking bit-exactly); QG1c spawned
- [x] QG1c swap-convention search — 2026-09-30 NONE (C0 current best 0.9854; no frozen candidate improves; residual is swap-ONLY, x spurious). Not a convention typo. Spawned QG1d (source-level recon: read micromoth exp022 simulator swap)
- [ ] QG1d source-level swap recon — read micromoth-quilt exp022 simulator swap implementation, reconcile byte-level against our census map; read-only, cheap
- [x] F1 DeltaF-admission falsifier (CPU): ternary-* cluster's entropy-budgeted scheduling claim — priority-FIFO vs DeltaF admission (T from budget trits); frozen gates: mean wait within 5%, queue variance -40%, no 3x depth-4 blowups, slack-extreme +1 >=15% slower. Source: mining proposal 07:30 + ternary-{thermodynamics,budget,depth,scheduling} — 2026-09-30 **PREMISE-ABSENT** (G1 passes only degenerately: df == pfifo to 9 sig figs / identical frac_started; G2 variance -40% FAIL at ratio 0.9999994; premise r_pfifo 1.001 < 3.0 so nothing to eliminate; G4 CONTRADICTED — slack 6.5% FASTER not >=15% slower). Load-saturated sim (55% of jobs start); admission key numerically inert. Regime does not reproduce.
- [x] W5a reobserve-vs-trace (CPU) — 2026-09-30 **REFUTED** (budget-matched fresh re-observation does NOT beat trace-reading: 0/24 cells fresh >2pp, overall 0.01pp, no consistent direction) — QO6 loses the claim to generalize to mildly-lossy traces, keeps its substrate claim. METHODOLOGY FLAG: the verdict function scored det_err only, and det_err is saturated (max-statistic detector fires ~always: ~1.0 false alarms at mu=0, 0.0 under drift); audit on the pre-reg's other two registered metrics (sign +0.42pp, |t0| +0.12pp, mixed direction) corroborates REFUTED — low-power but honest. pre-reg proposals/runs/W5a-reobserve-vs-trace.md
- [x] W5b lifetime-precision (GPU): lifetime-ranked vs uniform vs random HP allocation on a ternarized GRU (2% exact slots, equal budget, shared warmup fork) — 2026-09-30 **KILL** (mean_rel **-1.05%** vs the +0.5% gate; lifetime wins **1/3** seed-pairs, and is the BEST arm at 4241 (+10.0%) but the WORST at 4242 (-9.97%) and 4243 (-3.19%) — a sign flip, not a near-miss; mean order antirank 9.522 < random 9.758 < lifetime 9.818 < uniform 9.957). Secondary (pre-registered exploratory, no gate): **antirank beat random 3/3** (+2.51/+1.65/+3.01%) and lifetime 2/3 — instability, not persistence, may mark precision-worthiness; spawned W5b2 (5 fresh seeds, gates >=0.5% and >=4/5, in flight). pre-reg proposals/runs/W5b-lifetime-precision.md

## IN FLIGHT 2026-09-30 08:4x (do NOT double-fire — conductor take note)
- [ ] W5b2 antirank-primacy confirmation (GPU) — firing 08:4x, pre-reg proposals/runs/W5b2-antirank-primacy.md; spawned from W5b KILL (primary lifetime seed-dependent 1/3) + antirank secondary win 3/3 (+1.6/+2.5/+3.0%)
- Booked 08:5x AK by the 08:55 booking one-shot: W5a REFUTED, F1 PREMISE-ABSENT (see RESULTS.md).
- Booked 09:1x AK by the 09:15 booking one-shot: **W5b KILL** (lifetime allocation is seed-unstable — best arm at 4241, worst at 4242/4243; mean_rel -1.05%, wins 1/3; antirank secondary 3/3 over random, ungated). Still armed: 10:25 AK W5b2 (in flight, do NOT double-fire).

## IN FLIGHT 2026-09-30 09:2x — CPU double-fire (Casey: keep experiments hot)
- [ ] H1 judgment holonomy audit (CPU): can symmetry-loop inconsistency localize a corrupted field region with ZERO teacher calls, beating the kNN-margin baseline? KEEP = AUC>=0.80 AND paired baseline win on >=4/5 seeds; INDIFFERENT if mean gap <0.02. pre-reg proposals/runs/H1-judgment-holonomy.md — wide-scope #3
- [ ] FD1 frontier distillation (CPU): frontier-only student vs uniform, plus eval-time hybrid (field easy / student hard); KEEP = frontier >= uniform-0.5pp AND hybrid >= uniform+1.0pp on >=4/5 seeds; HALF if only frontier-safe. pre-reg proposals/runs/FD1-frontier-distillation.md — wide-scope #1
