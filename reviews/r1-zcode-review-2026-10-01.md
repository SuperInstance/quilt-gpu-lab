ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
ZCode Built-in skipped (not-due)
Audit complete. All five runners read line-by-line against their frozen preregs, with the load-bearing claims verified by executing the actual code (CPU probes from `/tmp` — **no repository files were modified**).

# Second-witness audit — staged runners vs frozen preregs

**TL;DR: Do not fire.** Three of the five are dead-on-arrival or silently void as written: **XQ0 crashes at the first training step of the first arm AND its flow kernel is an exact no-op**, **S6b crashes at the first training step of the first arm**, and **S6a's corpus is contaminated by a known-invalid receipt while the frozen families silently fall out**. The instrument and cupy runners are runnable with medium/low findings.

## CRITICAL

**C1. XQ0 — every arm is shape-fatal at step 0 (fail-loud, wasted run).**
`xq0_substrate_consolidation.py:209` hardcodes `n_channels=128`, so `XQNet.inp = nn.Linear(in_dim, d)` with `in_dim = 128 (+256 for quilt arms)` (`:131`). But training corners have N ∈ {32, 64}, so at the very first step (NOMEM, corner (8,32,0.3)) `tok_in = ev[:, t]` is `(bs, 32)` into a 128-wide Linear. Verified by execution: `RuntimeError: mat1 and mat2 shapes cannot be multiplied (2x32 and 128x64)`. Three more independent shape bugs stack on top for the quilt arms: `QuiltField(BATCH, 128, …)` hardcodes the evidence-block width at 128 while train corners feed N=32/64 (`:211`, `:99` — verified RuntimeError); the write head is `Linear(d, 256)` assigned into a `(256−N)`-wide slice (`:135`, `:103` — verified RuntimeError); and eval builds `QuiltField(1, N=64)` making `tok_in` 320-wide vs the 384-wide Linear (`:245`, `:143` — verified RuntimeError). A single input projection cannot serve varying N — the evidence vector must be zero-padded to a fixed width (or embedded per-channel). The run dies into a KILL-harness receipt, burning the slot and booking a false harness-kill.

**C2. XQ0 — the flow kernel is an exact no-op; QFLOW ≡ PASSIVE mechanically (silent wrong-result path).**
`quilt_step` builds its four neighbors with the wrong pad sides (`:77-80`): `F.pad` takes `(left, right, top, bottom)`, so `up = pad(g[:, :-1, :], (0,0,0,1), 1e4)` yields *g with its last row masked*, not the shifted north neighbor — and likewise for `down`/`left`/`right`. Every "neighbor" equals the cell itself almost everywhere, so `d = g − nb = 0` and the `d > res` gate never fires. Verified by execution: `quilt_step` returns its input bit-identically (`torch.equal → True`, max delta 0.0), while a correctly-wired control with the same constants moves the field by up to 6.5. Consequence: even after fixing C1, four flow steps do literally nothing — QFLOW and PASSIVE differ only by init seeds (33 vs 44), and the top-priority gate **SUBSTRATE_THINKS ("QFLOW floor < PASSIVE floor at ≥2/3 corners") would be read on pure seed noise**, with no crash and nothing in the receipt revealing it. Note the intent elsewhere is right: snapshot diffs, k=0.22, res=0.4, and the S,N,E,W application order (`:82`) all match the cupy oracle (`cupy_quilt_fp16.py:69-72`) — only the pad construction is broken. Fix is to swap the pad sides (e.g. `up = pad(g[:, 1:, :], (0,0,0,1))`, etc.).

**C3. S6b — all arms crash at the first training step.**
`DiscoveryNet` input projection is `nn.Linear(1, d)` (`s6b_memory_tokens.py:102`) but the forward feeds it `ev[:, t:t+1]`, which is `(bs, 1, N)` (`:115`). Linear applies to the last dimension, so N=32 hits a 1-wide weight — verified by execution: `RuntimeError` raised at `:115` with a faithful batch. The "single token per timestep" reading (which the T-pooled readout and mask shape confirm was intended) needed `Linear(N, d)` — which then hits the same varying-N problem as XQ0 (train N ∈ {32,64}, so a fixed `Linear(128, d)` still breaks; the evidence must be padded). The alternative per-channel reading doesn't rescue it either (memory-state slicing and the `(bs,T,1)` mask pooling both go shape-invalid). Fail-loud KILL receipt, wasted slot.

## HIGH

**H1. S6a — corpus contaminated by a known-invalid receipt.**
The prereg freezes the corpus to D-line receipts; the runner globs **all** `results/*.json` with no D-line and no validity filter (`s6a_delta_direction.py:99`). Running its own extractor over the real directory shows `d12j_gpu_width.harness-invalid-r1.json` is ingested as its own family with 216 rows, all acc ≈ 0 (a dead-harness rerun, not physics misses). It's single-class, so it's excluded as a *fold* — but its rows sit in **every** LOFO **training** fold: at `:131`, `mu_m` (the miss-class mean that defines the contrastive direction `u`) is composed 69–83% of invalid-harness rows, and the permutation null (`:164-168`) inherits the same skew. The GEOM arm's direction and p-value are both fitted against a majority of bogus misses.

**H2. S6a — the frozen families silently don't parse; what remains is 3 folds including a twin pair.**
Per-execution inventory: only 4 families parse, 936 rows (prereg expects n ≈ 200–400). D12h — named in the frozen corpus — drops **all** rows because its grid entries carry no `"W"` key (`:40` raises per-row and the try/except swallows it); D12f/D12e/D12g/D13*/D1/D21 likewise fail the `{"W","N"} ⊆ keys` requirement (`:65`). The prereg's second corpus source, "RESULTS.md D-line bookings", is never read (RESULTS.md does contain D12h/D12i/D12j bookings). The usable folds end up as {d12i, d12j_gpu_width, d12j_gpu_width_lucineer-r2} — and the latter two cover the **identical 9-corner grid**, so holding out one leaves its twin in train. Since GEOM embeds the family name, twin leakage inflates GEOM's held-out AUC relative to the scalars — biasing precisely toward **GEOM_WINS**. Also, single-class-excluded families (including the invalid one) are not reported anywhere in the receipt, though the prereg requires "excluded from folds **and reported**" (`:124-125`).

**H3. XQ0 — the S6b cross-check clause is void before it starts.**
The prereg requires "NOMEM here must reproduce S6b's NOMEM floors (**same seeds/code**)". But XQ0's NOMEM seed is 11 (`xq0:29`) while S6b's NOMEM seed is 22 (`s6b:41`) — init, training-stream, and eval-draw seeds all differ — and the architecture isn't the same code either (XQNet vector-input `:127-162` vs DiscoveryNet scalar-input `:98-129`). The declared replication is impossible by construction, so any floor mismatch gets auto-booked as "variance evidence" that is actually architecture+seed confounding. Either the seeds/architecture must be aligned or the cross-check clause should be struck before firing.

## MEDIUM

**M1. XQ0 — CAPACITY_CONFOUND gate weakened vs frozen.** Prereg: "MATCH ≤ every quilt arm **everywhere**". Runner requires only ≥2/3 corners per arm (`xq0:199`). A capacity confound appearing at 2 of 3 corners now books the gate that the prereg reserves for the everywhere case.

**M2. S6a — GEOM arm content silently amended.** Prereg freezes the embedding as "params + gates + runner docstring"; the runner embeds structural fields only (`s6a:118-119`). This is the right call — embedding gate outcomes would leak the label directly and make GEOM_WINS vacuous — but it's a deviation from the frozen arm text and belongs in a prereg amendment, not just the runner docstring.

**M3. Instrument-01 — R1 protocol deviation.** Prereg freezes "**mean of 3 bursts per idle draw**"; the runner times a **single** burst per idle (`instrument_ramp_law.py:70`). Since burst #1 partially re-heats the box, the frozen mean-of-3 statistic is systematically less sensitive than what's implemented — the R1 gate (>1.5× at ≥2/3 of the 4 idle≥10s draws, `:73-75`, threshold ceil(2/3·4)=3, which is a defensible reading) will be evaluated on a noisier and more-sensitive statistic than registered.

**M4. cupy_quilt_fp16 — accumulation dtype contradicts the frozen topology.** Prereg P1: "half intermediates, **float32 accumulate**, float32 store". The kernel holds the running `adj` in `math_t` (half precision) across the four neighbor updates (`cupy_quilt_fp16.py:67-73`), re-quantizing the accumulator after each subtraction — a strictly more lossy topology than frozen, so the delivered divergence curve isn't the registered one.

**M5. S6b + XQ0 — eval ladder extrapolates into untrained positional embeddings, asymmetrically in XQ0.** Training draws T~U{1..16} (`s6b:173`, `xq0:219`), so `pos.weight[16..31]` are never trained; eval floors are read at T up to 32. In S6b this contaminates the pooled readout of all three arms roughly symmetrically. In XQ0 it is **asymmetric across the gate comparison**: NOMEM/MATCH mean-pool per-step outputs (garbage tokens at t≥16 averaged in) while PASSIVE/QFLOW read a final token re-encoded at trained `pos.weight[0]` (`xq0:154-158`) — an undeclared penalty on exactly the arms the EXTERNAL_HELPS gate compares against, active whenever a floor lands above T=16.

**M6. S6b — budget-bust path violates the frozen protocol.** Prereg: "Budget bust → DOWN-SCALE the model and declare it". The runner just stops at 3h and proceeds to read floors off the under-trained model, recording only a `budget_capped` flag (`s6b:171`, `:184`; same pattern in `xq0:217`, `:232`). Gates would then be evaluated on an undeclared under-trained run.

## LOW / BORDERLINE

- **cupy receipt robustness:** writes to relative `outputs/…` which exists only at the quilt-mojo-lab root (`:195`); run from `python/`, the main write fails *and the KILL handler writes to the same missing path* (`:205`), so the fail-loud receipt is itself lost. The bf16 arm, when compilation fails, silently vanishes from P1 and `_bf16_err` is never surfaced in the receipt (`:83-88`). The "ramp receipt embedded in the JSON" is only the nominal `ramp_s: 0.6`, not a measurement (`:179`).
- **cupy P2 realism:** the flow kernel is memory-bound (~12 MB/step regardless of math dtype), so the ≥1.4× fp16 speedup is unlikely; booking the failure is the sanctioned P3 outcome, but expectations should be set.
- **S6b gate edge:** WRITE_NEUTRAL requires both floors non-None at **all** corners (`:148-150`); any None (arm never reaches bar) forces MIXED_OR_FAIL even where |Δ|≤1 holds wherever defined. Also each arm evals on different draws (per-arm eval seeds, `:188`) — unpaired floor comparisons add noise to ±1-rung decisions, and a floor from 5 single-sample draws is 5/5-or-nothing (correct per the 0.9 bar, and declared, but very noisy at the rung granularity the gates turn on). `gen` at `:162-163` is dead code.
- **S6a statistics:** the CHANCE null permutes labels globally, ignoring family-clustered label structure (anti-conservative p); p=0.0 is reported unsmoothed. Gate arithmetic itself (`:176-181`) maps the prereg's three outcomes correctly, including the SPLIT fall-through.
- **Instrument-01 R3:** lighter than frozen (single 20s idle point rather than the shape sweep; torch `add_` rather than the declared cupy elementwise kernel; ~8× longer burst than the standard 30 ms). Exploratory/no-gate, so cosmetic — but it no longer answers "is the law kernel-agnostic across the idle curve?" as written. Minor: `hot_ew` uses min-of-3 (`:64`) where the matmul baseline uses median-of-5.

## What checked out clean (verified, not just read)

`make_batch` implements d12j semantics correctly in both GPU runners (partner evidence mean ≈ p, non-partners ≈ 0, self pinned to 0, first-index argmax tie-break); arm dims/seeds/corners/ladder/bar/steps/optimizer/3h budgets match the frozen preregs; S6b param counts (8.58–9.39M) sit in the declared ~8–12M band; both `_verdict` priority orderings otherwise track their preregs; `_auc` is a correct tie-handling Mann-Whitney; S6a's LOFO/SCALAR-1/SCALAR-2 constructions match the frozen arms; the cupy kernel's snapshot semantics, S/N/E/W order, k=0.22/res=0.4, `--fmad=false`, and inject range (±3) match the declared topology and the XQ0 constants; all five runners have fail-loud KILL-harness wrappers and VRAM preflights (instrument: 512 MiB vs ~67 MB needed; the 2 GiB GPU preflights are adequate once the shape bugs are fixed).

**Recommendation:** hold the morning batch. XQ0 and S6b need code fixes (input projection over varying N, quilt pad sides, cross-check seed alignment) plus prereg amendments for the deviations they embody; S6a needs a corpus filter (D-line + validity) and a decision on the twin/invalid files before its gates mean anything. Instrument-01 and cupy_quilt_fp16 are fireable once the mean-of-3 and accumulate-dtype deviations are either reconciled or declared.
ZCode Built-in skipped (not-due)
