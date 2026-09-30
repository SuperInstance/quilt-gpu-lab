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

## Coordination platform (lives in SuperInstance/quilt-i2i)

- **i2i-ledger worker** — live shared semantic memory:
  `POST /book`, `GET /near?q=`, `GET /since?ts=` at
  https://i2i-ledger.casey-digennaro.workers.dev — any agent with curl.
  Skill file: `skills/i2i-ledger/SKILL.md` (HTTP or plain-git transport).

- **HANDOFFS** — `docs/HANDOFFS.md`: delegable open questions with exact
  deliverables + claim protocol (`books_to: handoff:<id>`).

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
