# RSI AUDIT — is the standing scout recursive self-improvement, or accumulation of random stuff?

**Commissioned:** Casey, 2026-10-04 15:04 AKDT (first answer cut off by session error; this is the full study).
**Auditor:** selftrain-scout-audit lane (isolated subagent).
**Scope:** the standing-scout complex — `selftrain-scout` cron (SELFTRAIN-SCOUT.md, 30 rounds), `ternary-synergy-miner` journal (research/ternary-synergy-miner.md, 21 entries), `edge-mine` scout → GEMS.md waves 0/5–10 (47 abstractions assayed, 16 gems seeded), growth-landscape scout (Oct 1 catalog) — and their consumption by quilt-gpu-lab (SPOOL.md → RESULTS.md).

---

## 1. What the loop actually is (measured, not assumed)

Four mining organs feed one furnace:

| Organ | Product | Volume (Sep 27 – Oct 4) |
|---|---|---|
| selftrain-scout cron (every 3h, deepseek, isolated) | SELFTRAIN-SCOUT.md rounds: repo reads w/ file:line refs, transferable mechanisms, `Next` chains | 30 rounds, ~90 repo-reads, 71 clones, 608 KB |
| ternary-synergy-miner | journal entries: 3-repo compositions, each with a falsifiable claim | 21 entries |
| edge-mine scout + assayer | GEMS.md waves: mined abstractions scored N×U×F, ≥27 promotes to SPOOL pre-reg seed | 47 assayed, 16 seeded |
| growth-landscape scout (one-shot, Oct 1) | ranked catalog of demonstrated self-growth mechanisms | 10 ranked, top-4 actionable |

Furnace: SPOOL.md pre-regs → fired experiments → RESULTS.md bookings (279 booked verdict headers total; 39 D-line). All fires pre-registered, gated, G7-receipted, repro'd.

## 2. CONVERSION — mined → developed → booked (the number)

Booked verdicts traceable to scout/miner output (provenance verified in RESULTS.md / pre-regs):

1. **D22** — synergy-miner entry #1 (forgiveness-via-privacy-noise) → KILL, booked+pushed `0ce9c15` (Sep 28).
2. **G3 framerate** (wave-0 gem) → booked; part of the G1–G5 arc ("first architecture in the fleet derived end-to-end by its own experiment sequence", RESULTS.md:2432).
3. **W5a** (wave-6 gem M10) → REFUTED, booked Sep 30 08:5x — same morning the wave landed.
4. **W5b** (wave-6 gem M11) → KILL, booked Sep 30 09:1x.
5. **W5b2 + W5B2-REPRO** (W5b's pre-declared two-sided arm) → KEEP (+8.35% mean, 5/5 seeds), repro booked Oct 2, spawned RC-6.
6. **PIDFIRE-1** — synergy-miner "pid-tuned criticality" (Oct 3 (3)) → FAIL booked 23:0x same day; pre-reg names the source verbatim: *"Composition: ternary-pid × ternary-fire × ternary-irradiate (mined 2026-10-03 (3), journaled uncommitted — now real)"*; repro PASS `b78218f`; PIDFIRE-2 revision seeded.
7. **VOYAGER-SKILLLIB** — landscape catalog #1 → booked Oct 4 12:2x (retrieval PASS / reuse saturated / purity PASS).
8. **REST-EM-001** — landscape catalog #3 → fired, booked INCOMPLETE-HELD + overnight retries (Oct 2–3).

**Totals:** ~9 booked verdicts from ~120+ mined idea-objects ≈ **7–8% raw conversion**. Graded the charitable way (of things the loop itself ranked as promote-worthy: 16 GEMS gems + 21 synergy entries + top-4 catalog): **9/41 ≈ 22%**. The RSI bar was ~30%. **Under the bar on both readings.**

**Timing asymmetry (the tell):** 8 of 9 conversions landed Sep 28–30 — the window when the main agent was actively aiming the furnace at the mine (D-line dispatches, same-day wave-6→W5a/b/b2). Since Oct 1 the lab fired plenty (B1/COMP2/CM1/d12u/VX/FR lines — 279 headers) but almost none of it from scout output; the mine kept producing at full rate. Mining and firing decoupled.

**selftrain-scout specifically: 0%.** Thirty rounds, zero fired experiments, zero design artifacts, zero ledger bookings (0 `selftrain*` entries in i2i over 6 days), zero references to SELFTRAIN-SCOUT.md anywhere outside its own directory (memory files, quilt repo — quilt's last main-repo commit predates the scout). Not one mined mechanism this week became a fired experiment. The scout is structurally forbidden from writing anywhere (protocol: READ-ONLY, append-only journal) and no harvester was ever wired. It is a sealed room producing excellent notes nobody reads.

## 3. SELECTION — is there pressure picking better ideas?

**Yes, genuinely — this is the loop's strongest property.**

- The assayer kills with named reasons per wave ("U-starved", "F-starved", "corroboration, zero new question") and promotes ~1–3 of 5–8. No gate loosened in 7 waves (each wave's rubric-honesty note says so, and the scores corroborate: wave 9 promoted 1/5).
- **The assayer learned from its own data:** from wave 6 on it documents the rule "our ≥27 scores come almost exclusively from literature×receipt collisions, never from raw novelty — the mine's query budget should keep targeting our asset list," and re-targeted queries accordingly. That is a real selection-rule update driven by the loop's own history.
- Rounds chain: R5 answers R4's Q1–Q3 by name; R26–R29 each open with "Round N−1's Next targeted 1–3; all covered." Round 30 audited its own backlog and **caught R28/R29 citing phantom repos that don't exist** (`gh repo list` verification) — self-correction of the miner's own bookkeeping.
- Synergy-miner bounces directions per its direction map and marks substrates "unused until now" — anti-redundancy sampling, not uniform random.

**Doom-pile check (backlog vs consumption):**

| Backlog | Now | Consumed | Trend |
|---|---|---|---|
| SPOOL seeds from GEMS | 12 unfired (Z1, W5c, S6a, S6b, W8a, W8b, W9a, W10a–c + wave-0 rest) | 3–4 fired, all Sep 30 | **growing +~2/day, zero fires since Oct 1** |
| synergy journal | 19 of 21 unfired | 2 | growing ~2.6/day |
| scout inventory | 217 of 300 org repos unmentioned (72%) | ~3/round | growing faster than consumed (org grows; scout samples depth-first) |
| scout journal | 608 KB / 7,390 lines | 0 | +~120 KB/day, no compaction |

Every backlog grows faster than it is consumed. The mine out-produces the furnace ~10:1.

## 4. SELF-IMPROVEMENT — has the scout's own process changed from its findings?

**Partial.** Process-level: yes (assayer's collision rule + query re-targeting; scout's phantom-repo verification discipline; protocol adaptation — `npm i` into clones so mined tools can actually run, R26–27; honesty instruments like pre-registered reproducibility gates being adopted as content). Tooling-level: no — same 6 lenses since Round 1, same manual read loop, no scripts, no retrieval, no embedding index over its own 608 KB. And **the product-level loop is absent**: nothing the scout found has changed any system that changes what the scout does next. The engine the scout was commissioned to design ("self-training under receipts", Casey 09-30 10:09) does not exist after 30 rounds — no proposal, no prototype, no decision. Improvement of the miner, none of the mined-for.

## 5. VERDICT: **HYBRID — real finds, real selection, conversion-starved. Not RSI.**

The loop is not accumulating random stuff — the ore is assayed, chained, and honestly killed; every one of the 9 conversions was pre-registered, gated, receipted, and reproducible, and two of them (W5b2 antirank KEEP, G3→G5 arc) are load-bearing doctrine in RESULTS.md. But recursion requires the furnace to feed back into the mine, and it doesn't: conversion is 7–22% (bar: ~30%), concentrated in one 72-hour window when a human-aligned agent happened to aim the furnace at the mine; since then the complex produces ~15 promote-worthy ideas/day and fires ~0/day of them; all four backlogs grow monotonically; and the flagship organ (selftrain-scout, 30 rounds) runs at exactly 0% conversion in a sealed read-only room — hoarding, with excellent notes. RSI would look like: mined finding → fired verdict → *changed mining policy or engine behavior* → better next finding. We have the first arrow, a flickering second, and no third.

## 6. The one structural fix

**Close the mine-to-furnace gap with a conversion gate; stop mining faster than you fire.** Concretely:

1. **Wire a harvester into the existing `gpu-lab-tick` cron** (no new infrastructure): each tick, take the oldest un-dispositioned entry from each journal (synergy entry / GEMS gem / scout `Next`), and force a binary disposition — promote to a SPOOL pre-reg seed, or park/kill with a named reason (same discipline the assayer already uses). No entry may sit >72h without a disposition. This alone converts the selftrain-scout from a sealed room into a feed.
2. **Backpressure rule:** no new mining wave while >3 seeded-unfired gems wait in SPOOL. The mine idles before the furnace chokes.
3. **Give selftrain-scout a write path with a budget:** one booked mechanism per round (its own top pick) filed to the ledger/SPOOL as a pre-reg seed — or fold the scout into the assayer and spend its 3h-slot on firing instead of reading.

The quality of what it mines is not the problem; the absence of a mouth is.

---
*Evidence: SELFTRAIN-SCOUT.md (30 rounds, 7,390 lines), research/ternary-synergy-miner.md (21 entries), quilt-gpu-lab GEMS.md (waves 0,5–10 + assays), SPOOL.md (git history 1c95322→6900fcb), RESULTS.md (279 headers; D22:923, G3:2419, W5a:2978, W5b:3031, W5b2:3043, W5B2-REPRO:5500, PIDFIRE-1:5703, REST-EM:5426, VOYAGER:5867), i2i ledger /since (0 selftrain entries, 6d), memory/2026-09-28..10-04, MEMORY.md:37.*
