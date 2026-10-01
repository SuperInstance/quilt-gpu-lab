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

- `EST-FREEZE` (deepseek, 15:2x, Casey: "try different ways") — the D2 v1 blocker is an estimator disagreement between two independent builds; this lane builds ≥4 DIFFERENT determinacy estimators behind one interface, cross-validates on the W-DET canary (zero false variance required) + mini traces across alphabet sizes 2→6, and freezes whichever passes — or books loudly that H5/H6 thresholds need re-derivation.

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
