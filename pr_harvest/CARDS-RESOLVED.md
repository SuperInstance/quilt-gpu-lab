# PR-HARVEST / CARDS-RESOLVED.md

Lane PR-CARDS-RESOLVE · 2026-10-01 · read-only `gh` (as SuperInstance) · **NOTHING POSTED / NOTHING COMMITTED.**
Scope: every card in `CARDS.md` **not** already covered by the 13 resolved drafts (5 posted + 8 skip-decided,
`REPLIES-final.md`). Fresh sweep: **46 open PRs across 15 repos** (the 15:4x harvest covered 33/12).

Cards covered by the 13 resolved drafts (excluded here): chiaroscuro #1/#6/#10/#12/#13, quilt-edge-lab #3/#4,
quilt-arcade #6, tidepool #11, Patchwork-experts #1, pie-minimax #2, quilt-tools #34, quilt-in-git #4,
pong-quilt #88, fleet-triage #3/#4.

State re-verified per target at current head this pulse. **No target draft collides with an existing comment**
(5 of 6 targets have 0 issue-comments/reviews; the 6th, quilt-in-git #3, has 0). Two PRs carry a builder
self-note, not a review (see Stale surprises).

---

## VERDICT TABLE — 21 uncovered cards

| Card | PR state @ head | Verdict | One-line basis |
|---|---|---|---|
| **quilt-edge-lab #1** | open, 2 commits, 0 comments | **reply-drafted (HIGH)** | `src/worker.js:211` `+body.quality_score ?? 0.5` parses as `(+x) ?? 0.5`; 0.5 unreachable, NaN flows into the promotion ledger row. |
| **pong-quilt #92** | open, 1 commit, 0 comments | **reply-drafted (HIGH)** | "horizon, not population, is the axis" rests on one long arm (pop96×160, seed 20261001) — the same seed already rising at 40 gens. |
| **chiaroscuro #2** | open, 2 commits, 0 comments | **reply-drafted (HIGH)** | Receipt pins R1 to `receipts/lane-c-edge.md`, but `receipts/` is in `.gitignore` and the file is absent; receipt also admits a pre-run router guard. |
| **chiaroscuro #3** | open, 1 commit, 0 comments | **reply-drafted (MED)** | #3 and #7 both replace `edge/worker.ts` and both commit `tools/nl_parity_receipt.json`; #7's core supersedes #3's. |
| **chiaroscuro #5** | open, 3 commits, 0 comments | **reply-drafted (MED)** | Clean falsifiable HOLD/CAST gate (receipt verified: degraded .87→.97, clean 50/50, clock 0.4755) → offer independent replication. |
| **quilt-in-git #3** | open, 1 commit, 0 comments | **reply-drafted (MED)** | #2 and #3 each regenerate `.quilt/hooks/post-commit` from `quilt-init`; the two generated hooks differ, so the second merge drops a feature. |
| **quilt-in-git #1** | open, 2 commits, **1 builder self-note** | **stale-with-evidence** | Builder comment 2026-10-01T23:27:24Z: "refs/quilt/HEAD portion is superseded by PR #2 … recommend merging #2 and closing this." Dead. |
| quilt-in-git #2 | open, 1 commit, 0 comments | no-reply-warranted | Verified clean: README documents `git fetch origin refs/quilt/dials` explicitly; no missing-refspec defect. (Its *merge collision* with #3 is drafted on #3.) |
| quilt-Kuramoto #2 | open, 2 commits, 1 builder self-note | no-reply-warranted | Builder self-note: target-side twin of fleet-triage #3 (bidirectional edge pair). Docs-only; census card already skip-decided (D13). |
| pong-quilt #89 | open, 1 commit, 0 comments | no-reply-warranted | Round receipt; "provenance travels with artifact" — no live defect, card probe is our-side. |
| pong-quilt #90 | open, 2 commits, 0 comments | no-reply-warranted | Self-caught order-pin RED (R70 PLAYLOG below R69) already repaired at tip (2nd commit). |
| pong-quilt #91 | open, 1 commit, 0 comments | no-reply-warranted | Round receipt; readme-count test already caught its own slip. |
| pong-quilt #93 | open, 4 commits, 0 comments | no-reply-warranted | franken-save guard + named refusal; wound reproduced FAIL-first, self-contained, no external gap. |
| AI-Writings #73 | open, 1 commit, 0 comments | no-reply-warranted | Prose essay; no falsifiable defect; card probe marked N/A. |
| quilt-edge-lab #2 | open, 1 commit, 0 comments | no-reply-warranted | Verified clean: `vendor/edge-ledger/*` byte-identical to upstream `516533b0` (5/5 files SAME); P1 sealed-FAIL is deliberate discipline. |
| quilt-arcade #5 | open, 1 commit, 0 comments | no-reply-warranted | Verified clean: cited `quilt-tools/experiments/s3-quantum-tided-budget.mjs` exists and its `WitnessLog` **matches** the declared shape (PENDING→ENTANGLED→COLLAPSED, job_id+backend+digest). |
| chiaroscuro #4 | open, 1 commit, 0 comments | no-reply-warranted | Research synthesis (FOUND/INFERRED/NOT-FOUND); no cheap falsifiable defect. |
| chiaroscuro #7 | open, 1 commit, 0 comments | no-reply-warranted | Verified clean: embedded `GRAPH_SHA256==sha256(edge/synonym_graph.json)` at head. Supersedes #3 (drafted there). |
| chiaroscuro #8 | open, 1 commit, 0 comments | no-reply-warranted | Spec-only pre-registration; nothing to falsify yet. |
| chiaroscuro #9 | open, 1 commit, 0 comments | no-reply-warranted | Spec-only; already inside D4's skip scope (KC lane closed, R8). |
| chiaroscuro #11 | open, 1 commit, 0 comments | no-reply-warranted | Receipt re-verified consistent with card (v3 58/58, v2 55/58; H2 FAIL on sf10 delta=1; H4 7/7 via #7's tool). |

**Counts: 6 reply-drafted · 1 stale-with-evidence · 14 no-reply-warranted = 21.**

---

## POST-READY DRAFTS (6)

Order = signal-to-noise. One ask each, evidence-pinned file/line, builder-respectful, no internal details.

---

### 1. SuperInstance/quilt-edge-lab#1 — dead `?? 0.5` fallback → NaN reaches the ledger row [HIGH]

> On the disclosed `+body.quality_score ?? 0.5` quirk in `/promote` (`src/worker.js:211`) — I think it's worth a fix rather than carrying it verbatim, because the intended default never fires and the NaN does reach the store.
>
> Unary `+` binds tighter than `??`, so the line parses as `(+body.quality_score) ?? 0.5`. With `quality_score` absent, `+undefined` is `NaN`, and `NaN ?? 0.5` is `NaN` — `??` only triggers on `null`/`undefined`, and NaN is neither. (Confirmed in node: `+{}?.quality_score ?? 0.5 → NaN`.) That NaN is passed as the defined `qualityScore` into `promoteRun` → `ledgerInsert`, where `row.quality_score ?? 0` (`:101`) has the same shape and can't catch it either — so the **promotion ledger row records NaN (NULL in D1)**, while an *append* row that omits the field records `0` (undefined *is* nullish). The auto path is indeed unaffected (it reads the stored row, as you say); the manual path's row is not.
>
> Ask: parenthesize the default — `+(body.quality_score ?? 0.5)` (and `+(row.quality_score ?? 0)`) — so the fallback applies; a pin that POSTs `/promote` with the field absent and asserts a finite `0.5` would lock it against regression.

---

### 2. SuperInstance/pong-quilt#92 — the horizon axis rests on one seed [HIGH]

> One sentence in the C1 scaling read I'd like to see nailed before it hardens: *"horizon, not population, is the axis that moves."* At head, the horizon axis rests on a single arm — `research/c1-scaling-2026-10-01.json` arms[6] = pop 96 × 160 gens at seed **20261001 only**.
>
> That seed is also arms[2]'s (pop 96 × 40 gens), and the two share `rallyFirst5 = 172`; arms[2] already rose 172 → 685.8 across the same first-40-gen window. So the long arm's 172 → 849.4 is one seed continuing a run that was already climbing — it can't separate *horizon* from *this seed rises*. The seed band is wide at 40 gens (arms[0] 351→694 and arms[4] 419→750 rise; arms[1] 455→333 and arms[5] 481→271 fall) — exactly why the `noLearningClaim` marker exists on the learning axis.
>
> Ask: run the long arm at ≥3 seeds (the two 40-gen seeds plus one) and report the last5 **band**, so the sentence is a band statement — or annotate it as a single-arm read, same as the no-claim marker does elsewhere. Either is fine; the conclusion just shouldn't outrun its n.

---

### 3. SuperInstance/chiaroscuro#2 — R1 pins provenance to a gitignored pre-registration [HIGH]

> The number is clean (1.000/50, eval set hash `32a35de2…` matches across receipts); it's the **provenance** I can't check, and it's an R1 question.
>
> `tools/edge_graph_receipt.json` pins `provenance: "receipts/lane-c-edge.md R2 pre-registration (graph + intent-position rules committed BEFORE the measured run, R1)"`, and `docs/RD-PLAN.md` §Round 3 says the replacement design is "pre-registered in receipts/lane-c-edge.md." But `receipts/` is listed in `.gitignore`, there is no `lane-c-edge.md` anywhere in the tree (code search: 0 hits), and the directory isn't in the repo — so the ruleset that R1 claims was *committed before the run* isn't in version control and can't be audited from the PR.
>
> It sharpens because the receipt's own `router_version_note` records the overlap-phrase single-count guard being **added to `edge/nl_route.js` before this run** — i.e. the router that produced 1.000 differs from the pre-registration's description, and that change is a receipt footnote rather than a sealed revision.
>
> Ask: land the pre-registration (un-ignore `receipts/lane-c-edge.md`, or move it to a committed path) and, if the guard is a rules change, seal it as its own revision — then the 1.000 is auditable end-to-end.

---

### 4. SuperInstance/chiaroscuro#3 — superseded by #7; both touch worker.ts + the same receipt [MED]

> Merge-order note: #3 and #7 both replace the keyword table in `edge/worker.ts`, and both commit `tools/nl_parity_receipt.json`, so they can't both land as-is.
>
> #7 (`edge/nl_route_core.mjs` + generated `edge/synonym_graph.mjs` carrying the embedded `GRAPH_SHA256`, runner `tools/nl_parity.mjs`) supersedes this PR's mirror (`edge/nl_route.js` + runner `tools/nl_parity.js`) — different core, different runner extension, same worker file and same receipt path. Whichever merges second silently wins both `worker.ts` and the receipt.
>
> Ask: land #7 and close this one as superseded (the same clean note you posted for quilt-in-git #1 → #2), or rebase #3's runner onto #7's core if both surfaces are wanted. (For what it's worth, I re-derived `sha256(edge/synonym_graph.json)` against #7's embedded `GRAPH_SHA256` — matches, `b57f29b0…`.)

---

### 5. SuperInstance/chiaroscuro#5 — independent replication of HOLD/CAST [MED]

> The HOLD/CAST split is the cleanest falsifiable control in this batch — `docs/HOLDCAST-pre-registration.md` sealed first, `tools/holdcast_ab_receipt.json` at head reads degraded 0.87 → 0.97 (11 casts), clean 50/50 held, `clock_ratio_clean 0.4755 ≤ 1.05`. A single-run +10 pts on a dev set is exactly the shape that deserves a second implementer, so I'd rather replicate it than take it on trust.
>
> Plan: an independent small classifier with the same two-mode absence policy (HOLD = wait on low |evidence|; CAST = go-look when best candidate is null), scored seed-pinned, gated on **degraded top-1 ≥ +8 pts vs single-mode Abstain** and **clean top-1 within ±0.5 pt**. Different code, same gate — informative whether it reproduces or not.
>
> Ask: post the degraded-input generator (or its seed + transform) you scored against, so the two runs share a distribution — or say the word and I'll pin my own and report both.

---

### 6. SuperInstance/quilt-in-git#3 — #2 and #3 regenerate different post-commit hooks [MED]

> Merge-order note across the wave-3 set: #2 and #3 each **regenerate `.quilt/hooks/post-commit` from `.quilt/bin/quilt-init`**, and the two generated hooks are different programs. #2's runs `quilt-receipt → quilt-cascade → quilt-publish` (refs/quilt/dials + HEAD) and carries no notes refspec; #3's runs `quilt-receipt → git notes --ref=quilt/receipts add → quilt-cascade` and wires `+refs/notes/quilt/receipts` in `quilt-init`. Both PRs commit the *generated* hook file, so whichever merges second wins `post-commit` and silently drops the other's step (either the publish, or the notes attach + refspec).
>
> Ask: state the intended order and rebase the later one's `quilt-init` heredoc to emit **one** hook carrying both — `receipt → notes add → cascade → (commit-if-changed) → watch line → publish` — with the notes refspec kept. One generated hook, both features, so the merge order stops being load-bearing.

---

## SKIP LIST (14) — no-reply-warranted, with reason

| Card | Reason |
|---|---|
| quilt-in-git #2 | Clean: one-shot `git fetch origin refs/quilt/dials` is documented in README; no refspec defect. Its collision with #3 is drafted on #3. |
| quilt-Kuramoto #2 | Docs-only; builder already self-noted it as the target-side twin of fleet-triage #3; census card is inside D13's conditional skip. |
| pong-quilt #89 | Round receipt, nothing open; the card's probe (ckpt lineage) is our-side work, not a PR defect. |
| pong-quilt #90 | Its only live item (R70 PLAYLOG ordering RED at the shipped tip) is already repaired by the branch's 2nd commit. |
| pong-quilt #91 | Round receipt; the readme-count slip was self-caught. No open gap. |
| pong-quilt #93 | Self-contained; wound reproduced FAIL-first, guard+receipt named. Nothing to add without duplicating their pins. |
| AI-Writings #73 | Essay; no measurable claim; card probe explicitly N/A. |
| quilt-edge-lab #2 | Vendored reference verified byte-identical to upstream `516533b0` (5/5); P1 sealed FAIL is intentional discipline with a known one-line fix they chose to leave. |
| quilt-arcade #5 | Citation resolves and the witness shape matches the cited file; pins RED-first; weight-law bookkeeping is correct. |
| chiaroscuro #4 | Research doc (FOUND/INFERRED/NOT-FOUND); no cheap falsifiable defect; probes are our-side. |
| chiaroscuro #7 | Verified clean (embedded hash matches the JSON). Supersession of #3 handled in draft 4. |
| chiaroscuro #8 | Spec-only pre-registration; nothing to falsify. |
| chiaroscuro #9 | Spec-only; already inside D4's R8-closed skip scope. |
| chiaroscuro #11 | Receipt re-derived and consistent with the card (v3 58/58, v2 55/58, H2 FAIL sf10 delta=1, H4 7/7). |

---

## STALE SURPRISES / STATE DELTAS

1. **quilt-in-git #1 is already self-superseded.** Builder comment at head (2026-10-01T23:27:24Z): its `refs/quilt/HEAD` portion "is superseded by PR #2 … recommend merging #2 and closing this." Card #1 is stale — do not reply.
2. **quilt-Kuramoto #2 is already self-paired.** Builder comment (22:13:49Z): target-side twin of `fleet-triage#3` (bidirectional edge). Complementary, zero collision — no reply.
3. **7 new PRs landed after the 15:4x sweep** (no cards): `AI-Writings#74`, `MicroMoth-quilt#30`, `frozen-clock-lab#1/#2/#3`, `pong-quilt#94`, `quilt-in-git#5/#6/#7`. `quilt-in-git#7` is explicitly **PARTIAL (quota-killed)**. Not in scope here; flagged for a second wave.
4. **Fresh open count: 46 PRs / 15 repos** (harvest saw 33/12). Extra repos beyond the harvest's 12: `MicroMoth-quilt`, `frozen-clock-lab`, and `quilt-in-git`'s extra #5–#7.
5. **The 5 posted comments are live**, on exactly `chiaroscuro#1`, `quilt-edge-lab#4`, `quilt-arcade#6`, `tidepool#11`, `Patchwork-experts#1` (all show `updatedAt 2026-10-02T01:23:xxZ`).
6. **quilt-edge-lab #1's INCONCLUSIVE persists at head**: live `/colo-report` still reads `{SIN: {count: 8, tails: 8}}` — all runs one colo, so cross-colo diversity remains unproven.
7. Two PRs are on branches that cross-reference each other: `chiaroscuro#11`'s H4 parity ran `tools/nl_parity.mjs @ edge-worker-graph-port` **in a worktree** (i.e. #11 depends on #7's tool without #7 being merged) — worth remembering when sequencing chiaroscuro's merges.

---

## BIGGEST FIND

**quilt-edge-lab#1 — the `?? 0.5` default is dead code.** `src/worker.js:211` `+body.quality_score ?? 0.5` parses as `(+x) ?? 0.5`; `NaN` is not nullish, so the fallback never applies and a **silent NaN reaches the promotion ledger row** (with the same shape repeated at `:101`). It's disclosed in the PR body as a harmless "NaN quirk preserved verbatim," which is the part worth correcting: node-confirmed, one parenthesization to fix, and it's the exact genre — a numeric default that doesn't apply — that a receipts-over-claims repo should not ship. Second: **chiaroscuro#2's pre-registration is gitignored**, so its R1 "rules committed BEFORE the run" is unverifiable from the PR at head.

---

## NEXT QUESTION

Post the 6 drafts (highest first: quilt-edge-lab#1, pong-quilt#92, chiaroscuro#2, then #3/#5, quilt-in-git#3)? And do we extend the harvest to the **7 new post-sweep PRs** now, or keep this lane closed at the 37-card set?
