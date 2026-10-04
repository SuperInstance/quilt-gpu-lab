# scratch/dogfood — DEEPINFRA ITERATOR EXPERTISE LANE (DOGFOOD-ITERATORS)

Casey directive 17:35 (2026-10-01): "pick a few of your deepinfra iterator models
to dog-food to expertise for niche development where your systems need it."

Four DeepInfra models driven against REAL niche work products (not benchmarks).
CPU-only, 0 Wh. NOTHING COMMITTED; no pushes.

| model | niche seat | work product | verdict |
|---|---|---|---|
| ibm-granite/granite-4.2-30b | Rust / exact ℤ[ω] arithmetic | `rust/` — conformance vectors + Rust test module | arithmetic 5/5, Rust hygiene 2/5 |
| inclusionAI/Ling-3.0-flash | Luau / Roblox (suspended-Kimi seat) | `luau/` — typed Luau pong-law module + lua5.1 harness | strong, 2 rounds to correct |
| XiaomiMiMo/MiMo-V2.6-Flash | TS / CF Workers | `workers/` — fix patch + node regression pin (+ sweep) | patch+pin 5/5, sweep fabricated |
| nvidia/NVIDIA-Nemotron-3.5-Lightning | stats / adjudication audit | `stats/` — audit checklist + concrete catches | catches real, precision low |

Runner: `../../tools/deepinfra_call.py` (list-form subprocess, token read at
runtime from `~/.config/deepinfra/token`, retry-once, fail loud).
Extractor: `extract_sections.py`.

## Layout
- `rust/`    — brief(s), `canonical_ref.py` (independent ℤ[ω] reference),
               `canonical_vectors.json`, `rscheck/` (control crate wrapping the
               REAL slackwater-rust `eisenstein.rs`), `granite_check/` (compiles
               granite's module), `r1/` `r2/` (model output).
- `luau/`    — `src/pong_law.luau` (final typed module), `tests/pong_law_test.lua`
               (final, `lua5.1` PASS 22/22, `luac -p` clean), `r1/` `r2b/`.
- `workers/` — `edge-lab/` (read-only clone, branch `dogfood/promote-precedence-fix`,
               patch applied UNCOMMITTED), `edge-lab-fixed/` `edge-lab-buggy/`,
               `promote_fix.diff`, `pin_promote.mimo.mjs` (model), 
               `pin_promote_ref.mjs` (lane control), `grounded_sweep.py`, 
               `SWEEP-grounded.md`, `r1/` `r2/`.
- `stats/`   — `verify_cp.py` (CP vs scipy), `r1/` `r2/`.

## Ground truth used
- Python `canonical_ref.py` + `canonical_vectors.json` (hand-derived ℤ[ω]).
- `scipy.stats.beta.ppf` for Clopper-Pearson.
- `rustc 1.97.1` / `cargo`, `luac`, `lua5.1`, `node v22.23.3`.
- `grounded_sweep.py` (deterministic regex; models cannot read files).

Deliverable: `../../blocks/D15-deepinfra-iterator-expertise.md`.
