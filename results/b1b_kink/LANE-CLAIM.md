# LANE CLAIM — B1b-KINK-HEAD (read before firing this lane)

Two independent B1b subagents were dispatched concurrently (orchestration defect).
Both targeted `results/b1b_kink/` with `task_id="B1b-kink-head"` and the same
`receipt_dir=results/b1b_kink/guard` — two guards would overwrite `guard_summary.json`
and break the first finisher's receipt `state_digest`.

Timeline (2026-10-01 AKDT):
- 14:56  Run A prereg frozen (alternate path; canonical path was clobbered at 14:57).
- 14:57  Run B (`experiments/b1b_kink.py`) overwrites `proposals/runs/B1b-kink-head.md`.
- 15:04  both fire.
- 15:07  Run A fire STOPPED to deconflict (its writes were clobbering Run B's models).
- 15:08  Run B crashes (JS/torch port broadcast bug) -> guard receipt
         `g7-wr-b1b-kink-head-1790896121.json`, self-declared **VOID**, no
         `agreement.json`, no `result.json`. Lane NOT landed.
- 15:10  Run A (`experiments/b1b_kink_head.py`, prereg
         `proposals/runs/B1b-kink-head-ALT-300ep.archived-20261001.md`) RESUMES into
         this dir as the sole writer, no gate/constant changed.

**Do not fire a third concurrent writer into this directory.**
