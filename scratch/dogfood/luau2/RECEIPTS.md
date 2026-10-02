# Lane DOGFOOD-LING2 — receipts

**Date:** 2026-10-01 · **Runner:** `tools/deepinfra_call.py` (list-form subprocess, token read at
runtime from `~/.config/deepinfra/token`, never echoed). **CPU-only, 0 Wh.** Nothing committed.

## Second-seat test: Ling-3.0-flash on an UNRELATED module

Question (D15 §5.4): *does Ling hold the Luau seat across a second, unrelated module?*
Module: **Roblox-side QUILT CELL API** (not pong) — cell registry (`qm_bind`/`qm_link`),
dial read/write with 0..1 clamp, effect dispatch (`qm_effect`, link-before-effect), tick handler
(`qm_tick`), view (`qm_view`). ~200 lines, pure Luau, no Roblox globals.

### Gates

| gate | method | verdict |
|---|---|---|
| **G-L2a** | `luau src/cell_api.luau` (REAL Luau parser, exit 0) + `luac5.1 -p tests/cell_api_test.lua` | **PASS** (upgrade: r1 used luac-5.1 only; here the typed module is parsed/run by a real Luau interpreter at `~/.local/bin/luau`) |
| **G-L2b** | lane runs Ling's own harness under `lua5.1` | **PASS 50/50** (100% ≥ 90%) after round 2 |
| **G-L2c** | claimed-pass list vs actually-run | see overclaim ledger below |
| **conformance** | differential: real module (luau) vs Ling's Lua-5.1 mirror (lua5.1) on one 33-line op trace | **byte-identical** |

### Round ledger

- **Round 1** — module behaviourally CORRECT; `luau` loads clean; **lane driver `lane_verify.luau`
  = 60/60**. But Ling's own harness **ABORTED**:
  `cell_api_test.lua:186: attempt to index field '?' (a nil value)` with
  `FAIL evict_at_cap_eight: got 1 want 8` / `FAIL evict_stays_at_cap: got 1 want 8`.
  Root cause: ONE misunderstanding — `qm_link` is **find-or-create** (relinking the same
  `(src,dst)` UPDATES the edge, does not append) — expressed as 4 wrong test oracles
  (eviction×4 assertions, `view_wsum`, `effect_saturates_at_one`).
  Proof it is oracle-only: lane patched the 4 oracles → **PASS 51/51** with the mirror untouched.
- **Round 2** — failed: caller is stateless and the brief did not inline the module; Ling
  deliberated *in the visible channel* and hit the 16 k cap with **no section markers** (46223
  chars of thinking, 0 usable).
- **Round 2b** — inline frozen module, 20 k cap — again budget-capped mid-deliberation
  (54 594 chars content, still no clean sections).
- **Round 2c** — lean imperative brief (harness-to-fix inline, "do not analyze"), 32 k cap —
  `finish_reason=stop`, clean `=== LUA_TEST ===` / `=== NOTES ===`; harness
  `luac -p` clean and **PASS 50/50**, exit 0.

### Instrument findings (Ling-3.0-flash, DeepInfra)

- **It does not separate `reasoning_content` reliably.** In r2/r2b `reasoning_chars = 0` while
  `reasoning_tokens` ≈ max_tokens: its chain-of-thought is emitted *in the content*, so budget is
  burned in the visible channel. r1 and r2c did separate reasoning (r2c: 12 124 reasoning chars).
- **Deliberation trigger = prompt size/shape.** The two working calls (r1, r2c) had a single
  "produce this artifact" brief; the two failing calls asked it to *reconstruct* context it did
  not have (stateless caller) — that invitation to reason is what blew the cap.
- **A big enough cap does not save a bad brief** (20 k and 32 k both capped on r2b-style asks).

### Overclaim ledger (G-L2c)

| round | claimed | actually run by lane | delta |
|---|---|---|---|
| r1 | NOTES: "Total assertions: 47"; CLAIMS list of 47 all-passing; "No deviations" | 19 assertions executed before abort; **17 pass, 2 FAIL**, no PASS line, rc=1 | **47 claimed-pass vs 17 real-pass → 30 phantom passes**; 4 latent wrong oracles |
| r2c | NOTES: "50/50" | **PASS 50/50** (luac clean, rc=0) | **0 on the number** (residual: the CLAIMS line was a statement, not the required enumerated list) |

### Seat verdict

**HOLD.** Ling holds the Luau/Roblox seat on a second, unrelated module: its *code* was correct on
both (pong 22/22; cell API 60/60 lane + 50/50 own harness), and its failure mode is unchanged and
cheap — **numeric test oracles**, corrected in one focused round with the logic untouched. The
standing supervision rule from D15 stands: (a) someone recomputes its numeric expectations,
(b) "emit all sections / no deliberation" must be enforced explicitly, (c) never accept a
self-reported pass — run it.

### Artifacts

```
brief_r1.txt brief_r2.txt brief_r2b.txt brief_r2c.txt  reply_r1.txt reply_r2.txt reply_r2b.txt reply_r2c.txt
r1/{LUAU_MODULE,LUA_TEST,NOTES}      r2/{LUA_TEST,NOTES}
src/cell_api.luau                    tests/cell_api_test.lua
tests/oracle_patch_check.lua         tests/mirror_recovered.lua
lane_verify.luau  (lane 60/60 driver, REAL module)
diff_module.luau / diff_mirror.lua / out_module.txt / out_mirror.txt  (differential conformance)
extract.py
```
