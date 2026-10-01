# REVISION BRIEF — patchwork-experts paper v0 → v1

*Source: 3-reviewer panel, 2026-09-30 (deepseek_stats, hermes_adversarial, seed_novelty — all: major revision). This brief is binding for the revision pass. Every fix must trace to a reviewer point or a booked receipt.*

## MUST-FIX (statistical validity — deepseek_stats)

1. **§5 headline comparison protocol violation.** 0.7437 (composition, single deterministic value) vs 0.7481 (d6, 3-seed mean) — stop subtracting across protocols. Fix: report BOTH arms under BOTH protocols (composition is deterministic → say so and give d6 at seed 0 alongside its 3-seed mean; label every score in the paper as SINGLE-DETERMINISTIC or SEED-MEAN±spread). Kill the "−0.4 points" framing; the honest statement is "at parity within seed noise, under a mixed-protocol caveat we now make explicit."
2. **§6 degenerate CI.** When the degeneracy guard fires, the bootstrap CI on agreement is meaningless. Relabel: "CI on a degenerate quantity, shown only to demonstrate the guard's necessity" — or suppress. Report raw counts everywhere near thresholds: 0.9167 = 88/96; blind_uniform = 96/96.
3. **§7 MI without uncertainty.** 0.5955 vs 0.1212 bits needs a permutation null (shuffle composition-correct labels, recompute MI, ~1000 shuffles) + Miller-Madow bias note + effective cardinality statement (15 observed signature values × 2 classes, not 64). Prefer COMPUTING the permutation test now (CPU numpy, seconds) via a new `experiments/px5_permtest.py` reading the PX5 per-state artifacts; if artifacts lack the join, book it as PX5b follow-up and say so — do not fabricate.
4. **§4 PX1b disclosure consequences.** State explicitly: which parts of PX1b were frozen pre-run (classes, branch table in docstring) vs not (commit ordering — committed post-run), and whether the ordering prediction was pre-stated. Move this disclosure from end-of-section parenthetical to a flagged box at §4's start (seed_novelty point).
5. **§5 adjudication bar under-specified.">0.5" direction-match is chance-level.** Fix: state the actual pre-registered bar (beat the blind endpoint 0.748/max-min band AND receipt-direction audit STRICTLY ABOVE chance with a stated threshold), and separate the blind-roster finding (veto specialist owns defense) from the live-arm bar in different paragraphs — no conflation.

## STRUCTURE (seed_novelty)

6. **Promote the routing-surface finding into abstract + intro** — it is the paper's most novel result (novelty 8/10) and it currently debuts in §7.
7. **Reader's Guide paragraph at the start**: map PX0→ceiling, PX1→linear collapse, PX1b→veto primitive, PX2→composition+immune, PX3→judge degeneracy, PX5→signature map, PX6→router KILL/routable-defense to the three core findings.
8. **Define jargon at first use**: top1-in-optimal, pinch cell, format gate, immune layer, MI. A terms box beats a glossary appendix here.
9. **Disclosure box up front (§3 start)**: all pre-registration deviations in one place — PX1b post-hoc commit, fire-5 crash/relaunch (flag-gate abort at move 21, relaunched armed — ADD THIS, it's new since v0), blind gardener budget violation.
10. **Label exploratory vs confirmatory per experiment**, especially PX5.

## HONESTY / COMPLETENESS (hermes_adversarial)

11. **Live arm**: keep as pending-with-bar (fire-5b still walking at brief-writing time); state the bar precisely; when adjudication lands it patches §5 as a numbered addendum — do not simulate results.
12. **Generalizability (§9)**: name the concrete scaling path for domains without exact solvers (cheap verifier ensembles, self-play label farms, the ActiveLedger doctrine) — one honest paragraph, no overclaim.
13. **Judge constancy (§6)**: acknowledge two synthetic fields is narrow; state the replication plan (real benchmark judges next).

## CONSISTENCY SWEEP (all reviewers)

14. BLOCK basin reconciliation: 2,392 all-6-wrong of 5,916 BLOCK states (40.4%) vs d6 BLOCK 0.57 — add the reconciling sentence (all-6-wrong ⊂ d6-wrong; stricter condition).
15. Percentages summing to 99.9% → state rounding.
16. Define "any-cell-correct" once, identical in §5 and §7 (including pinch or not — pick one, use everywhere).
17. "Spread 0.010" → state max−min explicitly (SD ≈ 0.0058 if SD intended).
18. Seed labeling: blind runs are seeds 1/2/3, tree seeds 0/1/2 — one sentence explaining why (seed 0 was the 10-move pilot).
19. Abstract 93–96/96 range → tie each number to its field name.
20. Account for the 51.9% of states neither all-correct nor all-wrong (partial overlap exists).
21. Oracle 0.8698: call it a measured upper bound consistently (abstract vs §7).

## CITATIONS

22. Fill the 12 [CITE-MISSING] ONLY where confident (well-known: Shazeer et al. 2017 sparse MoE; Jacobs et al. 1991 HME; Fedus et al. Switch Transformer; Zheng et al. MT-Bench). Everything else stays [CITE-MISSING] — a wrong citation is worse than a missing one. The cudaclaw spool's cite-guesses are cross-checks, not sources.

## VERSION DISCIPLINE

- v1 keeps every v0 number that survives; changed numbers only via receipts.
- The live-arm addendum after fire-5b adjudication = §5 patch, marked with its own timestamp — the paper reads honestly mid-experiment.
