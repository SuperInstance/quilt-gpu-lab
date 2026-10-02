# G1d — battery key repair (keeper lane; entry by keeper)

- date: 2026-10-01
- trigger: G1c's LOUD key defect — 19/96 shipped labels contradict prompt text (contra 11/16, count 8/16)
- scope: generator fix + corrected key for the BANKED @1 prompts + rescore of all three banked arms + structural finding
- artifacts: results/g1d/{corrected-key.json, rescore-v-corrected-key.json}; fix in experiments/g1_battery_build.py

## The two generator bugs (source-pinned)

1. **contra (experiments/g1_battery_build.py p_contra):** non-corrupt pairs were labeled SUPPORTED, but B ("X is NOT on the locker list") names a LISTED item there — B is false, so A and B are inconsistent → REFUTED. Corrupt pairs were labeled REFUTED, but when B names the dropped item, B is true → SUPPORTED. Truth now derived from set membership (B-item absent from A's list ⇒ consistent).
2. **count (p_count):** the manifest builder scattered `target` via rng.choice(FILLER), so the true count was a random variable — the claim "exactly claimed times" was almost always false regardless of the jitter. Fixed: target appended exactly k times.

## Corrected scores on the BANKED @1 responses (no new model traffic)

| arm | overall | arith | seq | xref | contra | count | date |
|---|---|---|---|---|---|---|---|
| LOCAL seat | **0.6979** | 9/16 | 9/16 | 15/16 | 16/16 | 13/16 | 5/16 |
| JEV | **0.9688** | 15/16 | 16/16 | 16/16 | 16/16 | 16/16 | 14/16 |
| GLM-5.3-flash | **1.0000** | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 |

## THE HEADLINE CORRECTION — the seat was right, the key was wrong

G1's "0.5208 = chance" and G1c's "seat 0.594 on sound classes" both under-credited the seat: against the corrected key it scores **0.6979**, with contra 16/16 (was booked 0.312!) and xref 15/16. The seat was correctly REFUTING the "consistent" claims the generator mislabeled.

## BUT — second-order finding: contra/count are structurally degenerate in @1

Corrected balance: contra **1 S / 15 R**, count **0 S / 16 R** (date 4/12 borderline). A majority-class solver scores 15/16 and 16/16 there — the seat's 16/16 contra and 13/16 count are NOT verifier evidence, and JEV's 16/16s on those classes aren't either. The only sound-evidence classes: arith (9S/7R), seq (6S/10R), xref (9S/7R), date (4S/12R, borderline).

**Seat on sound classes:** arith 0.5625 · seq 0.5625 · xref 0.9375 · date 0.3125. The honest verdict restated: **the seat is a class-dependent verifier — strong on explicit-context retrieval (xref), weak on arithmetic/sequence/date reasoning — and @1 cannot say anything about contra/count.** "Completer, not verifier" is retracted as too strong; the corrected claim is narrower and better-evidenced.

## Routing table v2 (≥0.75 bar, cost order LOCAL < JEV < GLM)

- xref → LOCAL (0.9375)
- arith, seq, date → JEV (0.9375 / 1.0 / 0.875)
- contra, count → **NO ROUTING CLAIM** (degenerate classes; G1e battery v2 decides)
- GLM: 1.0 everywhere = escalation tier (and the only arm proven on degenerate classes)

## Generator fix validation + next

- Fixed p_contra/p_count regenerate balanced classes (50/50 by construction); validated mechanically on a fresh seed-2718 build: all 96 labels re-derive from prompt text 96/96 (audit pattern, results/g1d/).
- **G1e (queued): battery v2** — certified moth-seal master, balanced classes, all 3 arms re-run; THIS becomes the standing witness-claim battery. @1 is retired to history (responses banked, corrected key shipped, nothing deleted).
