# jev-net self-play receipt — offline on local Ollama

2026-10-01/02. Repointed jev-net providers to local Ollama (no metered calls).
Cells: `qwen2.5:3b-instruct-q4_K_M`. Judge: `qwen2.5:7b-instruct-q4_K_M`.
Patch: `/tmp/jev-play/jevnet/providers.py` (added 'ollama' kind; guarded key read).
Harness: `/tmp/jev-play/selfplay.py`. State: `/tmp/jev-play/nets/state.json`.

3 rounds, seed=42, typesafe disabled. All 3 cells fired every round.

Round deltas (judge = ollama 7b):
- R1 score 7: builder=pivotal(+2), mechanism/skeptic=useful(+1); 7 edges moved.
- R2 score 8: all useful(+1); 8 edges moved; input→mechanism hit 1.0 clamp.
- R3 score 8: all useful(+1); 6 edges moved.

Final weight evolution:
| edge | initial | final | Δ | n_updates |
|---|---|---|---|---|
| input→mechanism | 0.80 | 1.00 | +0.20 | 6 |
| mechanism→builder | 0.75 | 0.93 | +0.18 | 6 |
| input→skeptic | 0.70 | 0.88 | +0.18 | 5 |
| input→builder | 0.60 | 0.74 | +0.14 | 6 |
| skeptic→builder | 0.70 | 0.70 | 0.00 | 0 |
| builder→skeptic | 0.50 | 0.50 | 0.00 | 0 |

Zero-move edges = no delivered-type overlap → no phantom credit (discipline verified).
