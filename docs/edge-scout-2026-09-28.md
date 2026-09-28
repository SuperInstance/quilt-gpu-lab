# Edge Scout — 2026-09-28 (flash)

Both edges mapped: the fleet's live build (PART 1) and the field's cutting edge
(PART 2), cross-referenced into a ranked GPU docket (PART 3) for the RTX 4050.

---

## PART 1 — Our Edge: the fleet's build map (SuperInstance, by push time 2026-09-28)

Top ~23 recently-pushed repos (known ones skipped: quilt-gpu-lab, chiaroscuro,
autoclaw, quilt-arcade, pincher, lever-runner, micromoth, polln, webgpu-profiler,
elephant). All times UTC.

| Repo | Pushed | What it is / latest commit |
|---|---|---|
| MicroMoth-quilt | 21:39 | PR #15 exp010-pop-scale-receipt — population-scale receipts on the Moth line |
| exoj | 21:38 | JEV scratch-paper: live typesafe oracle backing JEV emit, seed field from Moth comet-qrng; "naturalness ACHIEVED (commutative ledger, 2.2e-16)" |
| fleet-seeds | 21:35 | Tap Tavern sealed (stone-v1); 56-d contributions study, scanner-safe wording |
| AI-Writings | 21:35 | qthe-verify determinism defended + method lesson (d104) |
| Syzygy | 21:30 | Fused single-pass sensor-stream execution, register-resident (early: "Hello"→"Goodbye") |
| quilt-cloudflare | 21:28 | rate-component threat model + honest limitations (S17 audit finding) |
| PuddnHead | 21:12 | "The Fool is Ground Truth" — embeddings/cell-graph/projection as a detective-story theory artifact |
| pong-quilt | 20:54 | R57: Train+file-load breeds the LOADED population — streaming evaluator reset bug fixed |
| cellforge | 20:53 | Cellular-substrate ML training; gift-55 self-contained-test-killer PR merged |
| cns-substrate | 20:53 | CNS bus with hash-chained USCP substrate cells |
| mavis-essay-scout | 20:06 | Fleet tool POC (voices/README) |
| quilt-jepa | 20:06 | Round-5 (55-a): 11/11 validation at unchanged op point; R3L amplitude ladder SATURATES bit-exact at register precision |
| mavis-pincher(-pages) | 19:59 | Fleet tool POC (data/repos.json) |
| qthe-verify | 19:42 | Initial commit — determinism/verification wing of QTHE |
| jev-garden | 19:41 | a9 (55-b): fresh-memory serve law (grow-as-used), P-A9 PASS 4/4 under seal v12 |
| quilt-atlas | 19:30 | Scheduled 6h regen — living map of 4000+ repos |
| SmartCRDT | 18:58 | gift-53 shamir-repair PR — CRDT self-improvement |
| qthe | 18:10 | Wave-52 residue: hermetic CRAB resolution chain, strict receipt 54/54 |
| quilt-research-canons | 18:05 | pincher-round2-visions.md + zai-far-future.md wide ideation |
| glyphspace | 17:46 | Spatial reasoning over glyph grids (raycast/path-trace/multi-res) — proposal, receipt-gated |
| glyphcast | 17:46 | Next-frame prediction on glyph-domain video (chiaroscuro ASCII as token-array) — proposal, FAIL-first pins |
| coev | 17:37 | Adversarial coevolution engine, champion-integrity audit (extracted from pong-quilt C1) |
| duke-lab | 15:16 | docs-readme-zero-shot PR |

**Headline:** the fleet is converging on a *receipted, self-verifying cellular
runtime* — QTHE/jev/exoj (ternary embeddings + JEV), cellforge/cns-substrate
(cells as training substrate), quilt-jepa (latent world model in the cell mesh),
glyphcast/glyphspace (glyph video as the substrate's media), all wrapped in
stone receipts and fleet-level verification (qthe-verify, fleet-seeds, atlas).
The GPU lab's job in that picture: be the place cells get *trained and measured*.

---

## PART 2 — The Cutting Edge (headlines + links)

### (a) nanochat / modded-nanogpt speedrun scene
- **Record pace:** self-reported GPT-2-small 3.28 val-loss speedrun at **24.90 s** (2026-09-25); modded-nanogpt val_bpb now **0.71854** but on ClimbMix data (Mar 2026) — not comparable to FineWeb-era numbers. Leaderboards: <https://app.primeintellect.ai/speedrun/nanogpt>, <https://github.com/kellerjordan/modded-nanogpt>.
- **Winning mutations right now:** Muon (+Newton-Schulz) on hidden weights, FP8 head/MLP/attention, FA3 long-short sliding windows, `flex_attention` custom masks, value-embeddings, smear module, sparse per-head attention gates (kills BOS sink), document alignment (≥16 docs/step per GPU), extra skip wires. Walkthrough: <https://damek.github.io/random/modded-nanogpt-walkthrough-i/>.
- **Agents are speedrunning:** Karpathy's nanochat has absorbed **100+ agent-authored optimizations**; d24 baseline CORE 0.2585 in ~3.04 h (Jan 2026), d34 at CORE 0.3382 (<https://github.com/karpathy/nanochat/blob/master/dev/LEADERBOARD.md>). PrimeIntellect "auto-nanogpt" and AutoTrust claim recursive self-improving speedrun agents (<https://www.primeintellect.ai/research/nanogpt-speedrun>). METR measured this loop: <https://metr.org/notes/2026-04-21-ai-rd-nanogpt-progress/>.
- **Relevance to us:** the mutation loop (paired, fixed-budget, keep/kill at seed level) is now the field's unit of progress — and our D2 free-delta KEEP is exactly one of those. The field runs it on 8×H100; each mutation is expensive and curated. Volume is the scarce resource, and volume is what a free local GPU buys.

### (b) Small-model agent loops (sub-1B)
- Fine-tuned **Qwen2.5-0.5B** routers are an established pattern; **FunctionGemma**-style models emerging as agent routers/dispatchers. SLM-first orchestration cuts cost 30–85% (<https://developer.nvidia.com/blog/how-small-language-models-are-key-to-scalable-agentic-ai/>); vLLM "micro-agent frontier models" (Jun 2026): <https://vllm.ai/blog/2026-06-29-micro-agent-frontier-models>.
- Multi-agent-small beats single-large on tool benchmarks; **orchestrator capacity is the system bottleneck** — i.e., the judge/router quality is load-bearing, which is a training problem, not a prompting problem.

### (c) WebGPU / WGSL compute for cells
- Inference mature: Transformers.js v4 (Feb 2026, C++ core, 3–10×), LiteRT.js (Jul 2026), ~4 GB model ceiling, 90%+ desktop coverage (<https://web.dev/blog/webgpu-supported-major-browsers>).
- **Browser backprop is nascent and newsworthy** (Sept 2026 reports of in-sandbox backprop; `distmljs` PyTorch-like + autodiff on WebGPU: <https://github.com/mil-tokyo/distmljs>). Exactly the chiaroscuro-doors / browser-as-GPU-substrate thesis in our webgpu-profiler extraction — the field is arriving where our doors already live.

### (d) Text-as-vision research
- **ASCIIEval (ICLR 2026):** benchmarking LLMs/MLLMs on ASCII-art perception — proprietary models decent, open models trade off glyph-level vs global perception (<https://proceedings.iclr.cc/paper_files/paper/2026/hash/63f5c95b1e6364c42075f913d84ccb73-Abstract-Conference.html>).
- **"Text-priority bias":** models read character semantics over global visual pattern; adversarial ASCII bypasses VLM moderation (<https://arxiv.org/abs/2504.01589>).
- **The gap:** everyone is *consuming* ASCII-as-image (benchmarks, jailbreaks). Nobody has published a *generative* text-as-vision training loop — render→embed→train→predict-next-frame in glyph space. That is precisely chiaroscuro + glyphcast. The consumption-side attention makes the production-side territory claimable and citable.

---

## PART 3 — The Map: where the 6GB 4050 is THE decisive instrument

Lab state feeding this: the staged-elephant falsifier campaign swept the table
(X1 LICENSE; X3/X6/X9 KILL/FALLS; X2 renderer-bound → "the staged elephant
measured the staging"). What survived the week: **difference operators** — E18
diff super-additivity, D19/D20 ternary transitions, and **D2 free-delta
attention: first novel-model KEEP (val_bpb 1.6666 vs 1.6959 baseline, zero new
params, −2% tok/s)**. The theme that killed the illusion is the theme that won
in training. The GPU's decisive role follows: run the difference-mutation loop
at volume, in private, overnight — the one thing the fleet's CPU fleet and the
field's H100 clusters can't both do.

### Ranked GPU docket (OURS vs OTHERS' open questions)

1. **[OURS] D3 — free-delta seed replication + budget ladder.** The nursery's first KEEP is unhardened (1 seed, 1 budget). 4050-uniqueness: free paired 300 s runs → 5 seeds × 3 budgets ≈ overnight, $0. Value×uniqueness: ★★★★★ · ~2–3 h.
2. **[OURS] D4+ — delta-family mutation batch (k=2/3 diffs, value-delta, delta-gated heads).** Field does this loop on 8×H100 where each mutation costs real money → curated, slow. 4050 makes mutation VOLUME free: auto keep/kill overnight, D1's overhead lesson (−9% wall-clock ate a real signal) only measurable honestly at paired fixed-budget. ★★★★★ · nightly batches.
3. **[OTHERS — glyphcast/chiaroscuro] Train the first next-frame predictor on glyph-domain video.** Proposal is receipt-gated on exactly this: tiny tokenizer + predictor on chiaroscuro ASCII streams. 4050-uniqueness: model fits 6 GB, data is our renderer, and the field has benchmarks (ASCIIEval) but zero published generative glyph-space training — first-mover receipt. ★★★★★ · ~4–6 h first pass.
4. **[OTHERS — quilt-jepa round-5] Explain bit-exact amplitude-ladder saturation.** R3L saturates at register precision — a numerics question. 4050-uniqueness: free FP32/FP16/bf16/int8 sweep of the same ladder as a numerics microscope; no one else has the harness + a GPU idle overnight. ★★★★ · ~1–2 h.
5. **[OTHERS — fleet lane] Fine-tune a 0.5B fleet router/judge on stone-receipts.** Field SOTA is Qwen2.5-0.5B routers + FunctionGemma; the fleet's receipts are private (can't go to any cloud API). 4050-uniqueness: privacy + free LoRA iterations; serves pincher/exoj/jev routing. ★★★★ · ~3–5 h.
6. **[OTHERS→OURS — polln extraction] Plinko cell-router training (Gumbel-Softmax anneal sweeps).** The missing router organ needs gradient descent; τ-anneal + entropy-collapse detection is a sweep, and CPU can't hold the loop. ★★★★ · ~2–4 h.
7. **[OTHERS→OURS — polln extraction] DreamerV2-style super-cell simulator (VAE latent rollout).** The capstone equivalence test (cells vs super-cell) needs a small world model trained and rolled out thousands of times; fits 6 GB trivially, needs volume. ★★★★ · overnight rollouts.
8. **[OTHERS — webgpu-profiler/quilt-cloudflare] WGSL port of free-delta forward, receipted against the 4050 CUDA baseline.** Browser backprop is hitting the field's news cycle; our metric-honesty contract needs a reference oracle. 4050-uniqueness: it IS the reference GPU — the only hardware that can generate ground-truth receipts for the browser cells. ★★★ · ~2–3 h.
9. **[OURS] F1 manifold cartography of the dead elephant bank** (reverse-R², intrinsic dim, principal angles) — survives the postmortem with dignity; encoder sweeps are free on GPU vs tedious on CPU. ★★★ · ~1–2 h.
10. **[OURS — boat doctrine] int4/distill receipts for Liquid-LFM2.5 lane.** SPOOL wave-2 widen item (10k-param edge distillation, int4 eval): quantization eval receipts must come from real silicon; 4050 is the boat-brain proxy. ★★ · ~1 h.
11. **[OTHERS — coev/pong-quilt] GPU-side opponent populations for champion-integrity stress.** Currently JS-vs-JS; a small trained opponent net on the 4050 makes the audit adversarial for real. ★★ · ~2 h.
12. **[OTHERS — Syzygy] Fused sensor-stream kernel prototype.** Register-resident single-pass fusion needs *a* GPU to prototype against; the 4050 is the fleet's only one. ★· scoping.

**The one-sentence map:** the field's unit of progress is now the paid
fixed-budget mutation (H100 speedruns, agent-authored nanochat patches), and
the fleet's week proved the same unit — D2's KEEP — on a 4050; the decisive
instrument is therefore *mutation volume per dollar*, plus privacy for fleet
data (router training) and first-mover receipts in glyph-space video where the
field has benchmarks but no training loop. Slots 1–3 are the docket; everything
else queues behind D3's replication.
