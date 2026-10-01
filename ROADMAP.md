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
- `A2-HARVEST` (deepseek) — ga4444 4×4 composition: data-gen harness + smoke arm. Does A1's composition-absorption finding hold at the 4×4 rung (complete ground truth)?
- `A5-PARITY` (kimi/tmux `lab-a5`) — quilt-mojo-lab CuPy parity receipt on 4050: bit-parity @16/512/1024², cells/s next to their datacenter numbers. Consumer-silicon conformance node.
- `D2-DESIGN` (GLM-5.3, serial flagship lane) — pre-register D2-STOCHASTIC: quilt-dba transfer-gap under 1000 seeded worlds; fold in XP-C serialization law.

- `HY3-CACHE` ✅ DONE (585e126 superinstance-api, 4e15cf2 lab) — **Hy3 KEEP as standing expert, B+** (expansion A−, design B, self-critique A, factual B−; rider: verify quotas/columns, no unprompted trigger/cron authoring). - `HY4-TRIAL` ✅ DONE (14:55, superinstance-api) — **PROMOTE Hy4-preview for economics surfaces as fact-bearing author (0 fabricated facts vs Hy3 2✓/4✗, unprompted abstention + self-red-team); Hy3 STAYS for bulk/cost.** Punchline: Hy4 costs 6.4× in / 4.7× out / **1.27× cache-read** — better at reasoning about cache economics, worse as a cache-read unit. Arch null: 1M ctx never exercised (5.7k prompt); delta is post-training not architecture. Riders: ≥12k output budget (15k hidden reasoning chars), diff schemas vs schema.sql, re-test on a 2nd surface before standing routing rule. Lane "terminated" post-write — deliverable complete, keeper verified + committed.

**Queue (next waves, in order):**
1. `B1b` — re-prereg at 1e-2/5e-2 tol (stated rationale) + ReLU/learned-kink head; per-region deadzone/ramp/saturation/clamp agreement breakdown. (B1 KILL-at-1e-3 but step-direction 1.0000 exact.)
2. `C1b` — finish the 33 remaining pre-registered games in a clean serialized-seat window (~2.5–3 h lane, overnight-shape); adjudicate the ≥90% gate at N=40.
1. `XP-C2` — serialized-seat determinism gate (7B + grammar/JSON-mode, ≥0.95 well-formed). Unblocked by XP-C; needs the seat after C1 releases it.
2. `C2-CHAMPIONS` (kimi/tmux) — pong trained champions vs derived law, h2h receipts. Needs C1 booked.
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
