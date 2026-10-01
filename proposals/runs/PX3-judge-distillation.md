# PX3 — selectlib judge distillation: 576 judgment-cell calls → one local forward pass

**Status: FROZEN 2026-09-30 17:16 AKDT, before any build or collection. Commit-first.**
Parents: selectlib-readonly @ (read-only clone) `docs/GPU-EXPERIMENT.md` Experiment 5, `FINDINGS.md`,
`JUDGE-RUN.txt`. Format donor: PX2-patchwork-3x3.

## Objective

The stored headline: a real jev judge **≈ noise** on both blind fields at every budget
(288 calls/field, 5/5 controls fired). GPU-EXPERIMENT.md's own follow-up asks whether a
**learned local student** — trained on the judge's per-cell labels — can replace the 288
API calls with one forward pass. PX3 answers it, and in doing so also measures *what the
judge's labels are a function of*: scene structure or field identity.

Core claim under test: **the judge is a function of scene structure, not field identity** —
a student trained only on `blind_split` states transfers to `blind_uniform` states.

## Terrain (verified by running, not by trusting)

- `run_judge.py` judges every cell (8×12 = 96) of each field via a windowed state string;
  the harness rebuilds the field per budget, so 96 unique states × 3 budgets = **288 calls
  per field, 576 total**, same content asked 3×.
- `jev_client.py` → `https://api.typesafe.ai/v1/systemone`, model **jev-1.13.0**, choice
  question (criteria `correct`/`needs_fix`); answer is `p(needs_fix)` ∈ [0,1].
- Key line in `/mnt/c/Users/casey/key.txt` is **`TYPESAFE_AI_KEY=`** (verified 17:16 AKDT;
  the briefed name `TYPESAFEAI_KEY` does not exist in the file). Read at runtime only,
  injected via `os.environ`, never echoed, never written to any artifact.
- Known defect honored: `Result.table()` drops all rows but the last — raw rows/receipts
  only, never pretty tables.

## Collection protocol (fixed)

- Fields: `blind_split(seed=1)`, `blind_uniform(seed=1)` — the exact run_judge protocol,
  seeds=(1,), BUDGETS=[6,12,24], state-string builder byte-identical to run_judge.py's ask().
- `control_suite()` (5 controls) fires BEFORE any number, per harness contract.
- Every call logged to `results/px3_distill/judge_calls.jsonl` as
  `{field, seed, state_string, raw_response, parsed_label, latency_ms, call_index}`.
- Call errors after jev_client's own 4 retries → logged, run continues; **fail loud if
  >5% of calls error**.
- Expected: 288 calls/field, 5/5 controls, judge ≈ noise deltas matching JUDGE-RUN.txt
  (split: −0.0052/−0.0050/−0.0111; uniform: +0.0000 ×3). **Disagreement with the stored
  headline is a FINDING (instrument drift), reported, not hidden.**

## Distillation design (fixed)

- **Student:** state string → nomic-embed-text via local ollama (127.0.0.1:11434, 768-d)
  → L2-regularized logistic regression in numpy, CPU. Zero init, full-batch gradient
  descent, train-only standardization ⇒ fully deterministic; no seed needed for the head.
- **Dedup:** 3 asks per unique state (per-budget field rebuilds). Train label = first
  successful call's binary label (`p(needs_fix) ≥ 0.5`). Duplicate triples retained as a
  free instrument-stability number (fraction of triples with identical binary label).
- **Eval (a) within-field** (weak baseline): 5-fold CV per field, fold = i mod 5 over
  state strings sorted for reproducibility.
- **Eval (b) cross-field** (the real claim): train on all `blind_split` states,
  test on all `blind_uniform` states.
- **Metrics, always together:** agreement + per-class F1 + n. Logistic head is
  deterministic ⇒ uncertainty = **bootstrap CI over test states, 1000 resamples, seed 0**.
  Bootstrap std == 0 → **INCONCLUSIVE**.

## Pre-registered branches (cross-field agreement A; refined from GPU-EXPERIMENT.md's table, house standards kept)

| Result | Ruling |
|---|---|
| A ≥ 0.85 | **WIN**: the judge is compressible — one local forward pass replaces the judge's view of a field; judge ≈ function of scene structure, not field identity. |
| 0.70 ≤ A < 0.85 | **PARTIAL**: transfer is real but lossy; report what the student loses. |
| A < 0.70 | **KILL**: the judge is not a function of the local representation at all — a statement about the information content of the observation, reported plainly. |
| Degeneracy guard | If the test field's label distribution is single-class (std == 0), A cannot distinguish the student from a constant ⇒ that ruling is **capped at INCONCLUSIVE** (house rule 4: non-degeneracy is a precondition, not a result); within-field numbers still reported. |

## Controls

1. **Harness controls fire first** (5/5) — oracle_fires, noise_fires, oracle_is_ceiling,
   free_statistic_is_blind, split_differs_from_clean. Any refusal ⇒ no numbers.
2. **Reproduction control:** fresh judge run must reproduce the JUDGE-RUN.txt headline
   (calls/field, controls, per-budget judge−noise deltas). Drift = finding.
3. **Non-degeneracy:** label variance asserted per field before any relational claim;
   single-class test ⇒ INCONCLUSIVE cap above.
4. **Provenance:** jev model string + base URL, field seeds, embed model name, FNV-1a-64
   digest of judge_calls.jsonl, per-eval n. Booked to `results/px3_distill/px3_result.json`
   ONLY. RESULTS.md untouched; selectlib-readonly untouched.

## Deliverables & freeze order (commit order IS the freeze)

1. This pre-reg (frozen) → commit.
2. `experiments/px3_distill.py` (`--collect`, `--distill`; subprocess list-form only,
   no shell=True, fail loud) → commit.
3. `--collect` run → `results/px3_distill/judge_calls.jsonl` + `collect_meta.json` → commit.
4. `--distill` run → `results/px3_distill/px3_result.json` → commit → push everything.
