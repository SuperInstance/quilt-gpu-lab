# PX0 round 1 — patchwork-experts gardener: three-lane ideation
# fired 2026-09-30 ~16:0x AKDT; lanes: seed_mini, hermes_405b, h3_wildcard

## seed_mini — ByteDance/Seed-2.0-mini  (ok=True, 38.0s)
1. Falsifiable Experiment: Build a patchwork-experts tic-tac-toe optimal move agent with 0.3B–2B local cells; test on 5k non-terminal boards. Metric: % of moves leading to a 3-ply guaranteed win. Prediction: ≥90% accuracy (within 80% of the 92% depth-3 DT benchmark score). Kill condition: Accuracy ≤38% (equal/worse than linear baseline) OR gardener fails to generate a valid chain after 5 attempts.
2. Silent Failure + Control: Silent failure: Semantically broken cell outputs that pass format checks (gardener’s CoT only logs syntax). Cheapest control: Mandatory pre-cataloged 0.1B sanity cell running 5 precomputed tic-tac-toe ground-truth tests on all upstream outputs, adding failure logs to receipts.
3. Novel Cell Type: Webcam-backed physical board-parsing cell — non-NN, hardcoded WSL cell that captures a physical tic-tac-toe board frame via video4linux, uses OpenCV to map X/O pixels to a standardized CSV board state, and feeds it to downstream experts (no local model weights, bridges physical input to the patchwork’s symbolic format).

## hermes_405b — NousResearch/Hermes-3-Llama-3.1-405B  (ok=True, 6.3s)
1. Prediction: A depth-4 patchwork-expert will beat a 6B end-to-end model on few-shot math word problems, measured by accuracy. Metric: % problems solved correctly. Death result: Patchwork-expert scores below 6B model -5% at p<0.05.

2. Silent failure: Cells decay over time as the data distribution shifts. Cheapest control: Periodically re-judge a fixed validation set and track drift in cell outputs/accuracy. 

3. Novel cell type: "Consequence predictor" - given a state change, predict knock-on effects 2+ steps out. Trains on diverse state-change-consequence pairs.

## h3_wildcard — tencent/Hy4-preview  (ok=False, ERROR: HTTP 429: b'{"error":{"message":"Model busy, retry later","type":"invalid_request_error","param":null,"code":"engine_overloaded"}}')

## h3_wildcard — tencent/Hy3  (ok=True, addendum re-fire, 5.2s)
1. FALSIFIABLE EXPERIMENT
- Setup: On 200 held-out tic-tac-toe positions, build a patchwork of 3 depth-3 tree judges + 1 format gate + gardener wiring. Compare vs single linear model baseline.
- Prediction: Patchwork reaches >=2.0x baseline win-rate at optimal play within 50 gardener moves, using <=4B local judges.
- Metric: win-rate ratio vs baseline, gardener move count, local VRAM peak.
- Kill condition: ratio <1.3x after 200 gardener moves, or 4050 OOM/serializes to >30s/cell avg.

2. SILENT FAILURE
- Failure: gardener's receipts log "rearranged cells A->B" but its API CoT is post-hoc rationalization; actual move was driven by prompt drift / cached prior receipt, not real local-judge signal. Receipts look valid, judges unchanged.
- Cheap control: shadow randomizer — 5% of gardener moves are auto-rejected and replaced by no-op; if receipt quality/distillation score doesn't drop vs accepted moves, gardener is not causally earning its wiring.

3. UNTHINKABLE CELL
- "entropy-leak probe": a 0.3B cell that does nothing but watch token-loss of neighboring cells' INPUTS over time and flags when a judge silently rots (distribution shift) before any wrong output appears.
