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
- `C1-PLAYTEST` (deepseek, running) — local playtester across quilt-arcade games via engine API. On land: book, commit, then C2-CHAMPIONS unlocks.

**Launching now (GPU-light, co-tenant safe):**
- `A2-HARVEST` (deepseek) — ga4444 4×4 composition: data-gen harness + smoke arm. Does A1's composition-absorption finding hold at the 4×4 rung (complete ground truth)?
- `B1-DISTILL` (deepseek) — pong derived-law distillation: tiny MLP ← exact teacher traces, 3 seeds; receipts = per-tick action agreement + h2h vs law.
- `A5-PARITY` (kimi/tmux `lab-a5`) — quilt-mojo-lab CuPy parity receipt on 4050: bit-parity @16/512/1024², cells/s next to their datacenter numbers. Consumer-silicon conformance node.
- `D2-DESIGN` (GLM-5.3, serial flagship lane) — pre-register D2-STOCHASTIC: quilt-dba transfer-gap under 1000 seeded worlds; fold in XP-C serialization law.

**Queue (next waves, in order):**
1. `XP-C2` — serialized-seat determinism gate (7B + grammar/JSON-mode, ≥0.95 well-formed). Unblocked by XP-C; needs the seat after C1 releases it.
2. `C2-CHAMPIONS` (kimi/tmux) — pong trained champions vs derived law, h2h receipts. Needs C1 booked.
3. `G1e` — battery-v2 with the corrected key (from G1d commit: seat was RIGHT, key was WRONG).
4. `CM1 r4` — judge swap jev-latest, bigger GENs, roster diversity (in-house cell-mesh line).
5. `D2-STOCHASTIC` — execute the D2-DESIGN prereg (big; needs seat serialization respected).
6. `A3-CONNECT4` — set-valued rollout labels data-gen PoC (harvest, after A2 books).
7. `A4-DETERMINISM` — where GPU parallelism breaks bit-determinism (canon rule candidate; overlaps XP-C2 learnings — schedule after).

**Harvest ledger (fleet-triage RTX4050-WORKLIST):**
A1 ✅ KILL-of-prediction (d835e71) · C1 🔄 landing · A2/B1/A5/D2 🚀 this wave · A3/A4/D3 queued · B2-B6, C3, C4 unassigned backlog.

## Watch items

- `selftrain-scout` cron every 3h (deepseek, isolated) — standing lane at `~/.openclaw/workspace/scratch/selftrain-scout/`.
- z.ai payg endpoint 429/1113 persists — cloud arms use the coding endpoint (shape per G1c).
- moth-seal: pool=53, retry loop, n=4, direct; --stream=prf broken today.
- tmux: session `3` idle (10:40) — claim or kill next housekeeping; `canvas-ctl` is system.
