# ARCADE JUDGE LIVE — the first LIVING CHECK (2026-09-28)

**Vision-scout priority #5, wired.** The quilt-arcade judge slot (JEV) — until today
one of four NULL interfaces — now has a **local model living inside it**, and the
verdicts are real model output, fenced, counted, and receipted. This is Casey's
crystallization loop made executable: *the big model's call becomes a CHECK* — and
today a check executed on fleet hardware for the first time.

## What ran

| step | result |
|------|--------|
| Ollama health | `http://127.0.0.1:11434` up; model `qwen2.5:0.5b` (the only one pulled; LFM-2.5 not present on this box) |
| Slot contract | `quilt-arcade/slots/judge.mjs` v0.1.0: `createJudgeSlot(cfg)` → `{slot:'judge', name:'JEV', hooks:['scorePosition','reviewMove'], credentials:{env:'QUILT_SLOT_JUDGE_KEY', configured}}`; `scorePosition(snapshot) → {score, why}|null`, `reviewMove(move, verdict) → {agree, why}|null` (null = "no opinion"; games stay playable with all slots null) |
| Adapter | `arcade-judge/judge_local.mjs` — sidecar, **zero quilt-arcade tracked files modified**; mirrors the stub's export shape exactly, passes `assertSlotsValid` invariants (self-validated in-run) |
| Live game | `arcade-judge/arcade_judge_live.mjs` — full 9-ply minimax-vs-minimax tictactoe on the real engine (imported unmodified) → **draw**; judge reviewed **all 10 verdicts** (9 moves + 1 deliberate R2 refusal probe) and scored **all 9 positions** |
| Judge stats | **19 model calls, 19 opinions, 0 refusals, 0 exceptions**; latency 151–295 ms/call warm; Ollama JSON mode, temp 0 |
| Live checks | **5/5 green** (game completed · judge actually called · fence held — agree boolean/confidence∈[0,1]/score∈[−100,100] · refusal probe refused by R2 *and* adjudicated · board integrity: probe changed nothing) |
| ALL GREEN holds | `node run_all.mjs` (quilt-arcade, unmodified): **6 plugins smoke-clean, 67 checks across 6 games, exit 0** |

Note on the fleet's "node tests/arcade.js, 22/22": that path does not exist on this
box (searched `$HOME`); the repo's own gate is `run_all.mjs` — that is the ALL GREEN
asserted above, now earned on fleet hardware per the vision-scout gap.

## How the wiring works (the constraint honored)

The arcade's slots activate via config, not code change: `createSlot(name, cfg)`
threads `cfg.apiKey` into the stub, and games only *declare* slots in manifests
(run_all Phase A validates resolution + credential honesty). No hook has ever been
invoked by a game — so the sidecar imports the engine and the stub's interface,
rebinds the hooks to local Ollama calls, and drives the game exactly the way the
repo's own `games/tictactoe/play.mjs` does (`move.request` → `rules.verdict`).
The arcade remains 100% unmodified (`git status` clean apart from pre-existing
run-emitted `experiments/*.json` dirt); when the arcade grows a real slot-injection
point, this module drops in as `createJudgeSlot` unchanged.

Fence doctrine inherited from the repo's own `experiments/llm_advisor.mjs`:
referee stays the law, model output is opinion, every failure mode (provider down,
HTTP error, malformed JSON) collapses to `null` = "no opinion" — counted honestly
in `judge.stats.refusals`, never thrown into the game loop.

## What the judge actually returned

Structure: perfect. Every opinion well-formed; agreed with the referee on all 10
reviews; scores ranged −100…+100. Example (ply 9, the closing draw verdict):

```
JEV review C3 → {"ok":true,"rule":"R4",...} ⇒ agree=true conf=1
  why="The move was legal and applied, but the referee REFUSED it (rule R4)."
```

Substance: **tiny-model mush, honestly reported.** The 0.5B model returned
`confidence=1` on every call and its `why` notes frequently contradict their own
`agree` flag (the example above "agrees" while narrating a refusal). The slot is
alive; the brain is 494M parameters. That is the finding, not a failure: the
CHECK path — prompt in, fenced JSON verdict out, refusal counted — works
end-to-end and costs nothing. Swapping in a larger local model is
`QUILT_JUDGE_MODEL=<name>`; the interface does not change.

## Files

- `arcade-judge/judge_local.mjs` — the living judge (sidecar slot implementation)
- `arcade-judge/arcade_judge_live.mjs` — the live-adjudication runner (5 checks)
- `arcade-judge/arcade-judge-live-2026-09-28.json` — full machine receipt: every adjudication, verdict, opinion, latency
- Commit: pathspec-scoped to the four files above in **quilt-gpu-lab only**

*Receipts over stories: every claim above re-derives from the JSON and a rerun of
`node arcade-judge/arcade_judge_live.mjs`.*
