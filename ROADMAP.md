# ROADMAP — crew, sessions, and the hot chip

*2026-10-01 14:15 AKDT — Lucineer. Review each wave; archive-by-rename when stale.*

## Doctrine (this week's laws)

1. **Ship as yard:** many lanes in flight; Lucineer is keeper (commits, books verdicts, pushes). Lanes never commit.
2. **Seat serialization law (XP-C KILL, 64b9269):** byte-identity at fixed seed is a property of the *serving window*, not the model. GPU seat lanes (ollama qwen7B etc.) run ONE at a time; build/data-gen/tiny-net lanes run beside freely. G7 watt receipts mandatory — no receipt = VOID.
3. **Serial z.ai lanes:** GLM got rate-limited on parallel dispatch twice today (0-token lanes). One GLM lane at a time; deepseek-v4-flash takes parallel builder load (6 lanes proven today).
4. **Harvest don't invent:** fleet-triage `docs/RTX4050-WORKLIST.md` is a pre-written docket aimed at our card. Work its list; book corroborations to our ledger.

## Crew & tooling

| Crew | Tool | Job |
|---|---|---|
| Builders (parallel) | `deepseek/deepseek-v4-flash` subagents | pre-registered experiment build+run lanes, GPU-light by design |
| Flagship (serial) | `zai/glm-5.3` subagent | high-level design spikes, preregs, synthesis — ONE at a time |
| Test runner | `kimi -p` in tmux session | run-existing-script-and-receipt jobs (conformance, tournaments) |
| Keeper (me) | main session | dispatch, review, commit+push, RESULTS/QUEUE bookkeeping, memory |

## Wave board (2026-10-01 ~14:15)

**Landing:**
- `C1-PLAYTEST` ✅ PARTIAL (14:39) — 7/40 games, **law 7/7** (all shutouts-ish: 7-0×3, 7-1×3, 7-2), agreement 0.0917, zero parse-fails/violations/crashes, 21.09 Wh PASS. Gate NOT adjudicated (CI [0.61,1.00]). Root cause of partial: OLLAMA_MAX_LOADED_MODELS=1 + concurrent XP-C 3b/7b probe forced reloads in early attempts (archived); clean-rate is ~4 min/game ⇒ full gate ≈ 2.5–3 h. → **C1b queued: finish 33 games in a fleet-clean serialized-seat window.** C2-CHAMPIONS still unlocks on the booked h2h harness.

**Launching now (GPU-light, co-tenant safe):**
- `C1b-FINISH-GATE` (deepseek, ~2.5 h, owns the seat) — remaining 33 pong games in the clean window; N=40 adjudication of the ≥90% gate.
- `B1b-KINK-HEAD` (deepseek, tiny) — honest-tolerance re-prereg + ReLU/kink head + per-region breakdown.
- `D2-FIRST-BUILD` ✅ DONE 15:08 (939590c) — wiring receipt ALL PASS: W-DET canary reproduces E-D1 exact hash (var=0, byte-identical), F3/F8/F6 clean, 18 twins in 46.4 GPU-s, H3 widened via reflex (GPU-SEED LAW: reflex std==0 → INCONCLUSIVE), H-GROWTH PARTIAL w/ seed-vacuity datum, 0.756 Wh. v1 requirements booked (freeze 6 socket channels, fix reflex twin target, 200 worlds × 6 sockets × 54 twins w/ bootstrap-ρ).
- `A2-HARVEST` ✅ DONE 14:28 (4635d8d) — INCONCLUSIVE at the gate (natural-walk boards starve double-threats) but three real findings: R1 trajectory-mixing gives the exact ordering; R2 ceiling intact (93.5% on generated double-threat boards); R3 **ga4444 upstream bug** (7.5% self-play wins contradicts their exact-solver receipt). → A2b queued.
- `A5-PARITY` ✅ DONE 14:18 (kimi/tmux lab-a5) — bit-parity 0.0 at 16²/512²/1024² (stronger than their P1 claim), 3.06G cells/s @1024² = within 1.3% of receipt; INSTRUMENT-01 ramp receipted on independent harness (13× @16²); **kimi honesty catch: wave-73 was 4050-class, not datacenter** — our box matches their hardware class. Booked + PUSHED (f805ef8).
- `D2-DESIGN` ✅ DONE 14:17 — prereg frozen (H1-H6 gates, F1-F10 failure modes, W-DET canary 8c8a54a43f10); D2-FIRST-BUILD executing the wiring scope now.
- `BLOCKS-HARVEST` (kimi/tmux `lab-blocks`, 14:58) — Casey directive: pieces from successful runs as building blocks. 8-12 proven pieces → blocks/<name>/{BLOCK.md, block.py + passing self-test} + composition map in blocks/README.md. CPU-only.
- `COMPOSITE-0` ✅ DONE 15:2x (992269e) — INCONCLUSIVE honest: all pairwise directions held (FED>SINGLE +0.040, FED+LA>FED +0.025, FED>JOINT +0.015 at matched budget) but 66-item granularity → std==0 law fired (law caught the metric, not the model). Routing saturated 1.0 (unstressed), LA +2-3 items net to semantic cell.
- `COMPOSITE-1` (GLM-5.3, fired 15:2x) — re-run where it can be judged: ≥200-item eval + item-level bootstrap CIs, K≥4 regimes w/ blurred boundaries, capacity-starved board, LA-v2 with different featurization, per-regime primary gates.
- `SEER-0` ❌ CANCELLED (Casey correction 15:04: seedream-5-0-flash is an IMAGE model, not text — no seer seat there). Brief archived: scratch/SEER-0-brief.cancelled-20261001. **Reassignment: big-picture ideation/synthesis = GLM-5.3 flagship seat** (SYNTH-0, staged after COMPOSITE-0 — reads all booked results + open questions, ideates highest-leverage directions with bet/probe/kill discipline). Scope law remains: seedream-5-0-flash is the ONLY OpenRouter model, unused for now.

- `HY3-CACHE` ✅ DONE (585e126 superinstance-api, 4e15cf2 lab) — **Hy3 KEEP as standing expert, B+** (expansion A−, design B, self-critique A, factual B−; rider: verify quotas/columns, no unprompted trigger/cron authoring). - `HY4-TRIAL` ✅ DONE (14:55, superinstance-api) — **PROMOTE Hy4-preview for economics surfaces as fact-bearing author (0 fabricated facts vs Hy3 2✓/4✗, unprompted abstention + self-red-team); Hy3 STAYS for bulk/cost.** Punchline: Hy4 costs 6.4× in / 4.7× out / **1.27× cache-read** — better at reasoning about cache economics, worse as a cache-read unit. Arch null: 1M ctx never exercised (5.7k prompt); delta is post-training not architecture. Riders: ≥12k output budget (15k hidden reasoning chars), diff schemas vs schema.sql, re-test on a 2nd surface before standing routing rule. Lane "terminated" post-write — deliverable complete, keeper verified + committed.

- `EST-FREEZE` ✅ DONE 15:2x (8a18341) — the D2 A/B disagreement was the ENCODER, not the estimator (fire|salience impure, purity 0.833; fire|full-channel pure, spread 0.000). FROZEN-V1=NONE honest; synthetic control proved real spread is input-distribution sensitivity — H5 as written conflated the two. E3 frozen primary / E0 reserve; H6 UNBLOCKED (0.648 ≥ 0.5 with declared encoders). All three D2-V1 prerequisites met.
- `D2-V1` (deepseek, fired 15:2x) — the payoff run: 200 worlds (140/60 F5) × 6 sockets × 54 twins, E3 estimator + declared frozen encoders, bootstrap-ρ CI, H6 re-adjudicated, H5 re-derived. 1000-world extension only if H4 passes + CI width > 0.40.

**Queue (next waves, in order):**
1. `B1C` — different ways to close value fidelity now that kink heads lost (ensembles of tanh nets, capacity, deadzone-loss reweighting, binned targets). B1b's falsification defines the arms.
1. `XP-C2` — serialized-seat determinism gate (7B + grammar/JSON-mode, ≥0.95 well-formed). After C1b releases the seat.
2. `A2b` — generated double-threat boards + matched controls (fixes the degenerate-natural-walk defect A2 exposed).
3. `HY3C-rederive-coherence` — the re-derive-test-as-cache-proof probe, prereg seed from HY3-CACHE.
4. `C2-CHAMPIONS` (kimi/tmux) — pong trained champions vs derived law, h2h receipts. Needs C1b booked.
3. `G1e` — battery-v2 with the corrected key (from G1d commit: seat was RIGHT, key was WRONG).
4. `CM1 r4` — judge swap jev-latest, bigger GENs, roster diversity (in-house cell-mesh line).
5. `D2-STOCHASTIC` — execute the D2-DESIGN prereg (big; needs seat serialization respected).
6. `A3-CONNECT4` — set-valued rollout labels data-gen PoC (harvest, after A2 books).
7. `A4-DETERMINISM` — where GPU parallelism breaks bit-determinism (canon rule candidate; overlaps XP-C2 learnings — schedule after).

**Harvest ledger (fleet-triage RTX4050-WORKLIST):**
A1 ✅ KILL-of-prediction (d835e71) · A2 ✅ smoke INCONCLUSIVE-gate/BREAKS-secondary (4635d8d — linear does NOT collapse at 4×4; COMPOSED class near-degenerate by construction; follow-up = *designed* double-threat boards, A2b) · C1 🔄 landing · B1 🚀 running · A5 🚀 running · D2 ✅ prereg committed (b1a98d9) · A3/A4/D3 queued · B2-B6, C3, C4 unassigned backlog.

## Watch items

- `selftrain-scout` cron every 3h (deepseek, isolated) — standing lane at `~/.openclaw/workspace/scratch/selftrain-scout/`.
- z.ai payg endpoint 429/1113 persists — cloud arms use the coding endpoint (shape per G1c).
- moth-seal: pool=53, retry loop, n=4, direct; --stream=prf broken today.
- tmux: session `3` idle (10:40) — claim or kill next housekeeping; `canvas-ctl` is system.

- `KIMI SUSPENDED` (Casey 15:26, until further notice) — roles re-homed (deepseek lanes; zcode added as third runner per Casey 15:29).
- `D2-V1` ✅ DONE 15:5x (lane d2_v1b) — 200 worlds × 6 sockets × 54 twins, receipt PASS 0.586 Wh valid (+4.4 Wh VOID-run cost booked). **VERDICT INCONCLUSIVE, honestly:** H1 FAIL (ρ=−0.37 CI[−0.60,0.60] — reflex determinacy does not buy sim→real transfer at v1 scope) · H2/H3/H4 PASS · H6 PASS strong (range 0.880 > amended bar 0.648) · H5 INCONCLUSIVE (measure unstable 4/6 sockets; policy.action op-det 0.901 but spread 0.924 → static I/O-determinacy construct suspect near 1). **H-GROWTH R2 KILLED independently** (guided 0.83 vs unguided 0.88 — seed-vacuity confirmed). 1000-world trigger MET but frozen (repair H5 measure first). NEXT: H5-measure-repair lane (is H5 instability the KEEP-grade finding?).
- `COMPOSITE-1` ✅ DONE 16:0x (lane comp1_r2, GLM-5.3) — federation thesis re-judged properly: 590 held-out + item-level bootstrap (std==0 eliminated). **Verdict INCONCLUSIVE 1/5 gates — but G1R negation PASS (+0.126 CI[+0.034,+0.219])**: federation's win is regime-localized exactly where the monolith sensor is structurally blind (negation=polarity=word-order, invisible to BoW; SINGLE/JOINT drop BELOW regime chance there, FED holds 0.554). LA-v2 refinement: a second sensor that shares the first's blindness is worth ~nothing (+0.0017) — independent reach = seeing what the first MISSES. New issue: floor effect (all arms 0.547-0.562 on 0.517 chance) — COMP0's ceiling inverted. COMPOSITE-2 spec booked: VIEW as manipulated variable (heterogeneous sensors, router picks sensor not just expert) + mid-band difficulty 0.65-0.85. Receipt 11.76 Wh. r1-VOID preserved.
- `INFRA-EVENT 15:45` — all 5 subagent sessions terminated at once (runner-side, not lane verdicts; lanes' last words were mid-work). Recovery: d2_v1b survived + its nohup'd guard run3 landed a PASS receipt; BLOCKS-FINISH (zcode) had already completed (2 BLOCK.md + README composition map + honest COST_TOL fix booked; 6 dirs flagged pending-harvest); c1b_r2 + b1c_r2 + comp1_r2 re-fired on free slots; PROBE-BATTERY re-fired on zcode. Lesson: lanes' GPU runs survive via nohup+guard, but session-bound loops die with the session — long lanes should nohup their drivers early.
- `PR-HARVEST` ✅ DONE 15:4x (245caf8) — 37 PRs/12 repos, mechanism map (5 recurring machines), 13 drafts held, our ledger hash gap found. Follow-ups: `PROBE-BATTERY` RUNNING on zcode (probes 4-10, ≤3 min each, incl. our-own-ledger hash audit); top-3 probe cluster (ring-attractor × ternary × KC-sparsification) queued as bench day; 13 review comments await keeper+Casey review before posting.
- `BLOCKS-FINISH` RUNNING on **zcode** (tmux lab-zblocks, 15:31) — exact_minimax_labels + ternary_transition_kernel BLOCK.md/self-tests + blocks/README.md composition map. CPU-only, no commit.
