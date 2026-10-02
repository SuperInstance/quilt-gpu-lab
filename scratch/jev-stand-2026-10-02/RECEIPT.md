# jev-net standing self-play — 7 rounds, offline (qwen2.5:3b cells / 7b judge)

Extended the 3-round play to 7 varied prompts (incl. credit-assignment + verifier-vs-judge
questions). Weights moved monotonically and SATURATED the load-bearing edges:

| edge | initial | final | Δ | n_upd |
|---|---|---|---|---|
| input→mechanism | 0.80 | 1.00 | +0.20 | 12 |
| mechanism→builder | 0.75 | 1.00 | +0.25 | 14 |
| input→skeptic | 0.70 | 1.00 | +0.30 | 13 |
| input→builder | 0.60 | 0.88 | +0.28 | 13 |
| builder→skeptic | 0.50 | 0.52 | +0.02 | 1 |
| skeptic→builder | 0.70 | 0.70 | 0.00 | 0 |

- skeptic→builder stayed 0.00: the skeptic's delivered types (counter/risk/claim) never
  overlapped builder's accepts → no phantom credit, discipline held across all 7 rounds.
- builder→skeptic fired once (round 7's credit-assignment prompt) — the varied prompt set
  finally exercised the reverse edge.
- Trajectory: trajectory.jsonl (per-round score/cells/weights). State: state.json (bootable).
- Standing-lane recipe: rerun `python3 /tmp/jev-play/jev-stand.py` (or fold jev-play into
  the lab for permanence). Zero metered spend.
