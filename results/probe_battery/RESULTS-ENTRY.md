# PROBE-BATTERY — the cheap half (probes #4–#10 of pr_harvest/SUMMARY.md)

Lane PROBE-BATTERY (zcode) · 2026-10-01 · CPU-only (torch 2.14.1+cpu, numpy 2.4.6,
node 22) · seed 2718 (multi-seed arms: 2718/2719/2720; pie 5-fold arms use the
published 100–104) · every probe ≤3 min · scripts in `experiments/probe_<name>.py`
(+ `probe_ledger_hash.mjs`) · bookings in this directory · **no commit made**.

Verdict law applied throughout: `std==0` on a gated seed-mean → INCONCLUSIVE, never
PASS. Gates copied verbatim from the SUMMARY.md table into each script header.

| # | Probe | Verdict | The number that decided it |
|---|-------|---------|-----------------------------|
| 4 | distinct-board re-eval (pie-minimax #2) | **PASS** | top-1 on the 2,423 distinct boards **0.9992±0.0003** (composed-320 0.9990±0.0015), board-disjoint held-out 0.9916 — P1 FAIL-HIGH is **not** a duplicate artifact |
| 5 | second reader vs silent drift (fleet-triage #4) | **PASS** | self-path reader conf drop **−0.06** (gain, ≤5% clause met) while different-path agreement drops **0.738** (same-arch/diff-seed) and **0.737** (arch-diff) at 76% store drift |
| 6 | worktree-vs-index store-of-record (quilt-in-git #4) | **PASS** | under 50% materialization: worktree-style loader silently wrong **99/100**, index-style digest-exact **100/100**; store-damaged arm refuses loudly 99/100, never silently wrong |
| 7 | OUR ledger row-hash, cross-language (tidepool #11) | **FAIL** (on the letter) | agreement: node mirror **215/215**, natural-JS canonicalizer **0/215**; key-order perturbation flips **0/215** (scheme is order-INSENSITIVE — the table's flip channel doesn't exist); value perturbation flips 215/215; transplanted row still verifies (unkeyed path confirmed) |
| 8 | same-run baseline re-measurement (chiaroscuro #11) | **PASS** | state-space priors exact (180,361 / 2,423 / 320 — 0% drift); 5-fold prior 0.9811 vs published 0.9798 (**0.13%** ≤1%); linear prior 0.1807 → 0.1046 (42% drift, informational arm) |
| 9 | canon lex-min rotation + negative control (edge-lab #3/#4) | **PASS** | periodic: naive diverges **100%**, canon invariant **100%**; fixed-boundary: canon diverges **100%** (≥95% required); 500 distinct states/trajectories |
| 10 | dispatch-skip compute accounting (chiaroscuro #1) | **PASS** | counted-FLOPs saved == measured abstain fraction exactly at p∈{0.10,0.30,0.60} (gaps 0.0000); wall-clock gaps 0.032/0.069/0.019 (±10%); no-abstain output bitwise == dense |

**6 PASS / 1 FAIL.** The one FAIL is our own ledger's probe — and it is the most
useful result of the battery (below).

## What the numbers say

**#4 — the pie-minimax thesis question is settled on our iron.** Training/evaluating
on the 2,423 *distinct* boards (their exact protocol: 9-64-9 relu, set-valued loss,
Adam full-batch lr 0.01, patience 200) reproduces the 0.9996-class closure: the
published FAIL-HIGH was not inflated by the 180,361-row path duplication. The
board-disjoint held-out stays ≈0.99, consistent with both their supplementary 5-fold
(0.9798) and our own A1-PIE CV (0.9392 plateau / 0.979 lr1e-2).

**#5 — instrument diversity detects drift, self-consistency cannot.** With silent
drift injected through the reader's own write path (biased rewrites it then
re-consumes), the self reader's confidence *rises* (−0.06) while both differently
built readers see ≥20% agreement collapse. Honest boundary booked: an *external*
relabel corruption of the same size does hurt the self reader (conf → 0.61) — the
blindness is specific to drift the system itself generates. Adopt: re-scan gates
against a different-path reader.

**#6 — read the store-of-record, never the worktree.** The worktree-style loader
silently fabricated state (zeros prior) for un-materialized shards in 99/100 loads;
manifest + content-addressed store was digest-exact 100% and refuses loudly when the
store itself is damaged (never silently wrong). Direct analog of quilt-in-git #4's
sparse-checkout blindness, on our substrates.

**#7 — the FAIL that pays for the battery.** The subject: `probes.jsonl` rows hash as
`sha256(json.dumps(row_minus_hash, sort_keys=True))` (d5_probe_foundry.py:106 — the
ONE hash path; also drives the train/heldout hash-split and the sealed
reproducibility_hash). Findings:
1. *Cross-language agreement is achievable but not free:* an independently written
   node canonicalizer reproduces 215/215 digests **only** by mirroring python-json's
   exact byte format (`", "` / `": "` separators, ensure_ascii). The natural-JS form
   agrees on 0/215 — our "canonical" form is language-bound (the shared-format-law
   risk tidepool #11 pins; latent float-divergence risk booked: python `1.0` vs JS `1`).
2. *Key-order perturbation flips nothing* (0/215) — `sort_keys` canonicalizes order
   away. The table's flip clause assumed order-sensitivity; our scheme hasn't got
   that weakness. Non-degeneracy lives in value perturbation (215/215 flips).
3. *The real weakness is the one the harvest fold named:* the digest is unkeyed and
   unbound to path/actor/run-id — a row transplanted into any other context verifies
   intact (demonstrated). Cheapest fix available to us, per SUMMARY "STEAL #1":
   bind rows to (policy-version ‖ host ‖ run-id) and add the independent verifier.

**#8 — same-run baselines: cheap and discriminating.** Deterministic priors re-derive
exactly; protocol-matched statistical priors land 0.13%; a cross-lab prior measured
with an independent instrument lands 42% away (and our A1 parity arm showed 6.2%
drift even using their code). Reading: citation without the original validated
instrument is quote-only — adopt same-run re-measurement for any number a verdict
leans on.

**#9/#10 — both fleet primitives hold, bounded on both sides.** Lex-min rotation
canonicalization is exactly invariant where rotation is a dynamical symmetry and
refuses to collapse distinct dynamics where it isn't (the edge-lab #4 both-sided
bound). Ternary dispatch-skip saves exactly the abstain fraction in counted FLOPs,
wall-clock follows within ±7 points on CPU, and the no-abstain path is bitwise
identical to dense.

## Bookings

`distinct_board.json` · `second_reader.json` · `store_of_record.json` ·
`ledger_hash.json` · `baseline_remeasure.json` · `canon_rotation.json` ·
`dispatch_skip.json` — each carries gate (verbatim from the table), verdict, numbers,
seed, runtime, device.

Deviations booked honestly: torch CPU wheel was missing in this environment
(dist-info without package); installed `torch==2.14.1+cpu --user` to run the pie and
dispatch probes as specified. Probe #4 trains the 20k with-replacement draw as
draw-count-weighted unique boards (identical loss value, CPU speed). Probe #5's first
mechanism (external relabel) self-failed its own premise and was rewritten to
write-path drift before any verdict was booked; the external arm is retained as the
honest-boundary contrast. Probe #9's first lex-min implementation had a uint8
sentinel wrap bug (256→0 resurrected eliminated rotations) — caught because canon
invariance came out 0/1500 (mathematically impossible for equivariant rule 150),
fixed, and verified against brute force before booking.
