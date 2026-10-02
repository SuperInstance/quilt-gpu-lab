# MERGE-PLAN.md — 46→49 open-PR backlog, keeper-executable merge/fix plan

Lane **MERGE-TRIAGE** · 2026-10-01 · read-only `gh` as SuperInstance · **NOTHING MERGED / NOTHING COMMITTED.**
Mandate (Casey, this pulse): *"keep merging and fixing prs where you can too."* Directive: **prefer MERGING over commenting** where the PR is sound.

- Snapshot: **49 open PRs across 16 repos** (was 46/15 at the 17:28 sweep — the 3 new: `doubt-ledger#1`, `doubt-ledger#2`, `quilt-gpu-lab#6`; plus the 7 named post-sweep newcomers).
- Fresh data: `_raw3/pr-<repo>.json` (pr list), `_raw3/ci-checks.jsonl` (mergeable + statusCheckRollup + files + commits).
- **CI reality check:** most of these repos have **no test CI at all** — their only check is *GitGuardian Security Checks*. `statusCheckRollup` = GitGuardian only for chiaroscuro, doubt-ledger, fleet-triage, frozen-clock-lab, pie-minimax, quilt-Kuramoto, quilt-edge-lab, quilt-gpu-lab, quilt-in-git. "Green CI" there is **vacuous**; I ran the repo's own pins/tests locally instead (receipts below). Only 5 repos have a real gate: `pong-quilt` (test + forge suite), `quilt-arcade` (harness), `quilt-tools` (tools), `AI-Writings` (Writings gate), plus GitGuardian everywhere.

---

## 1. CLASSIFICATION TABLE (all 49)

Codes: **MN** = mergeable-now · **FIX** = needs a fix-commit pushed to the branch first · **REBASE** = conflicting, mechanical rebase (may degrade to FIX) · **CLOSE** = superseded/stale, keeper decides.

| repo | PR | base | ±  /files | checks @ head | verdict | one-line + evidence |
|---|---|---|---|---|---|---|
| AI-Writings | 73 | main | +29/-0 · 1f | Writings gate ✅ | **MN** | Prose essay *The Actualized Agent in Flow*; no code, no sibling. |
| AI-Writings | 74 | main | +178/-0 · 2f | Writings gate ✅ | **MN** | Two essays (Honest Ceiling + Ledgered Shell), queue #6; different files from #73 → no collision. |
| MicroMoth-quilt | 30 | main | +145/-3 · 2f | *(none)* GitGuardian only | **MN** | Grader blind-spot repair + import re-seal. **VERIFIED LOCALLY** (see §3). |
| Patchwork-experts | 1 | main | +252/-0 · 2f | GitGuardian ✅ | **CLOSE** | **CONFLICTING/DIRTY.** Its added md is **byte-identical on main** (`312d64ff…`, 12275 B); its `readme.md` edit **regresses** main's newer table-readme. Nothing left to land. |
| chiaroscuro | 1 | main | +863/-15 · 13f | GitGuardian ✅ | **MN** | Round-5 4-lane (JEV dispatch skip, edge NL eval, JEPA quant, Sobel). Root of the whole chiaroscuro stack. |
| chiaroscuro | 2 | #1 | +608/-0 · 8f | GitGuardian ✅ | **FIX** | Graph router 1.000/50. Receipt pins R1 to `receipts/lane-c-edge.md` but **`receipts/` is in `.gitignore`** (line 7) and the file is 404 in-tree → pre-registration un-auditable. |
| chiaroscuro | 3 | #2 | +268/-27 · 3f | GitGuardian ✅ | **CLOSE** | **Superseded by #7** — both replace the keyword table in `edge/worker.ts` **and** commit `tools/nl_parity_receipt.json`. |
| chiaroscuro | 4 | main | +127/-0 · 1f | GitGuardian ✅ | **MN** | FRUITFLY×JEV×MOTH research synthesis (doc only). |
| chiaroscuro | 5 | #2 | +397/-12 · 5f | GitGuardian ✅ | **MN** | HOLD/CAST abstention split; receipt verified (degraded .87→.97, clean 50/50, clock 0.4755). Merge after #2. |
| chiaroscuro | 6 | main | +3233/-15 · 34f | GitGuardian ✅ | **REBASE** | fly-stack v0 — root of the KC doc chain (#6→#9→#10→#12→#13) **but** carries `edge/worker.ts`+`edge/nl_route.js`+`js/jev_gate.js`+`edge/score_eval.py` that #1/#2/#5/#7 also rewrite. Collision-heavy. |
| chiaroscuro | 7 | #2 | +558/-32 · 6f | GitGuardian ✅ | **MN** | worker.ts routes via shared `edge/nl_route_core.mjs`; embedded `GRAPH_SHA256==sha256(synonym_graph.json)` verified. **Survivor of the #3/#7 pair.** |
| chiaroscuro | 8 | #6 | +72/-0 · 1f | GitGuardian ✅ | **MN** | CAST v3 vocab-expansion pre-registration (sealed). After #6. |
| chiaroscuro | 9 | #6 | +80/-0 · 1f | GitGuardian ✅ | **MN** | geometric-PN KC pre-registration (sealed). After #6. |
| chiaroscuro | 10 | #9 | +404/-0 · 2f | GitGuardian ✅ | **MN** | kc_geo geometric-PN run receipt (FAIL, receipted). After #9. |
| chiaroscuro | 11 | #8 | +563/-25 · 3f | GitGuardian ✅ | **MN** | CAST v3 RUN receipt (H1 4/4, H2 FAIL). After #8. |
| chiaroscuro | 12 | #10 | +76/-0 · 1f | GitGuardian ✅ | **MN** | geometric-PN KC v4 pre-registration SEALED. After #10. |
| chiaroscuro | 13 | #12 | +88/-6 · 2f | GitGuardian ✅ | **MN** | kc_geo v4 RUN receipt — **R8 lane CLOSED**. After #12. |
| doubt-ledger | 1 | main | +318/-0 · 10f | GitGuardian ✅ | **MN** | `poc` ledger; pins PASS locally (P2 append-only refusals, P4 git-resume identical). ⚠ commits `ledger/__pycache__/*.pyc`. |
| doubt-ledger | 2 | #1 | +186/-10 · 8f | GitGuardian ✅ | **MN** | `guardian` lane: 3 silent-failure fixes; pins PASS (G1–G4b). After #1. ⚠ commits `__pycache__`. |
| fleet-triage | 3 | main | +69/-0 · 1f | GitGuardian ✅ | **MN** | REFERRAL-quilt-kuramoto doc; no collision. |
| fleet-triage | 4 | main | +63/-0 · 1f | GitGuardian ✅ | **MN** | REFERRAL-predictive-paddle doc; no collision. |
| frozen-clock-lab | 1 | main | +301/-0 · 11f | GitGuardian ✅ | **CLOSE** | **Superseded by #2** — same file set (lab/*.py, pins, tests/pins_clock.py, README); #2 adds P6. Pins PASS (P1–P5). |
| frozen-clock-lab | 2 | main | +324/-0 · 13f | GitGuardian ✅ | **MN** | `sig-canonical` (P6 reference vectors); pins PASS incl P6. **Survivor of the #1/#2 pair.** ⚠ commits `__pycache__`. |
| frozen-clock-lab | 3 | #2 | +19/-1 · 2f | GitGuardian ✅ | **MN** | `guardian` P6b construction-canonical; pins PASS (P6b). After #2. |
| pie-minimax | 2 | main | +333/-0 · 5f | GitGuardian ✅ | **MN** | A1 closure receipt (nonlinear ≈1.0, P1 FAIL-HIGH, booked). |
| pong-quilt | 88 | round-68 | +159/-2 · 5f | test+forge ✅ | **MN** | Round 69 receipt. Base is branch `playtest-round-68` → confirm that merged first. |
| pong-quilt | 89 | main | +227/-5 · 5f | **test ❌ full-suite ❌** | **FIX** | **CI RED.** PLAYLOG R70 block sits **below** R69 (line 110 vs 79) → `round entries are newest-first` fails. Only 1 commit; the "already-repaired" note is stale. |
| pong-quilt | 90 | main | +469/-6 · 6f | test+forge ✅ | **MN** | Round 71. Pairwise PLAYLOG collision with #89 — merge after. |
| pong-quilt | 91 | #90 | +172/-2 · 5f | test+forge ✅ | **MN** | Round 72; correctly stacked on #90's head. |
| pong-quilt | 92 | main | +3178/-1 · 5f | test+forge ✅ | **FIX** | C1 scaling study. "horizon is the axis" rests on **n=1** (arms[6] pop96×160 seed 20261001 only); same seed as arms[2] which already rises 172→685.8. |
| pong-quilt | 93 | main | +838/-8 · 8f | test+forge ✅ | **MN** | Round 73 franken-save guard. Sequenced after rounds. |
| pong-quilt | 94 | main | +899/-8 · 8f | test+forge ✅ | **MN** | Round 74 R1 measured-at-tag + sibling verification. Sequenced last. |
| quilt-Kuramoto | 2 | main | +55/-0 · 1f | GitGuardian ✅ | **MN** | Referral doc; twin of fleet-triage#3. |
| quilt-arcade | 5 | main | +147/-14 · 14f | harness ✅ | **MN** | Referral edge → qt-s3-witness; witness shape verified against quilt-tools S3. |
| quilt-arcade | 6 | main | +1906/-0 · 12f | harness ✅ | **MN** | predictive-paddle v1–v3 (ring attractor); sealed FAIL H1/H2, advisory H3/H4, v2 pre-registered. |
| quilt-edge-lab | 1 | main | +10569/-25 · 16f | GitGuardian ✅ | **FIX** | **`src/worker.js:211` `+body.quality_score ?? 0.5`** parses `(+x) ?? 0.5` → 0.5 unreachable, NaN reaches the ledger row (`:101` same shape). |
| quilt-edge-lab | 2 | main | +1164/-0 · 19f | GitGuardian ✅ | **MN** | fleet-state@v1 interop PoC; vendored edge-ledger byte-identical to upstream; P1 sealed-FAIL deliberate. |
| quilt-edge-lab | 3 | main | +809/-0 · 9f | GitGuardian ✅ | **MN** | W2.3 canon-rotation invariance. Touches `DEBRIEF.md` (also in #1) → merge after #1 + rebase. |
| quilt-edge-lab | 4 | #3 | +796/-0 · 6f | GitGuardian ✅ | **MN** | W3.1 fixed-boundary control. After #3. |
| quilt-gpu-lab | 6 | main | +114/-3 · 4f | GitGuardian ✅ | **REBASE** | **CONFLICTING/DIRTY** (`README.md`, `receipts/manifest.json` advanced on main). seal-guard `__pycache__` usability fix — sound, just stale. |
| quilt-in-git | 1 | main | +151/-5 · 4f | GitGuardian ✅ | **CLOSE** | Builder self-note 23:27:24Z: *"refs/quilt/HEAD portion is superseded by PR #2 … recommend merging #2 and closing this."* |
| quilt-in-git | 2 | main | +412/-14 · 8f | GitGuardian ✅ | **MN** | w3b live-state refs; **pins 9/9 (38 checks)** run locally. First of the post-commit series. |
| quilt-in-git | 3 | main | +502/-33 · 10f | GitGuardian ✅ | **FIX** | w3a notes+signing; **pins 9/9 (41 checks)** locally. Regenerates `.quilt/hooks/post-commit` (add/add vs #2, #4). |
| quilt-in-git | 4 | main | +861/-42 · 13f | GitGuardian ✅ | **FIX** | w3c airgap+sparse; **pins 3/3 (26 checks)** locally. Regenerates the same hook (sparse/index-vs-HEAD variant). |
| quilt-in-git | 5 | main | +28/-0 · 1f | GitGuardian ✅ | **MN** | VERIFY.md harvest protocol (doc; already notes #2 supersedes #1). |
| quilt-in-git | 6 | #3 | +40/-4 · 1f | GitGuardian ✅ | **MN** | P10 sig-canonical; **pins 10/10 (44 checks)** locally. After #3. |
| quilt-in-git | 7 | main | +378/-0 · 1f | GitGuardian ✅ | **MN** | Research memo (PARTIAL — quota-killed lane). Doc only. |
| quilt-tools | 34 | main | +129/-17 · 3f | tools ✅ | **MN** | Referral book edges #16+#17 (fleet-triage census pair VERIFIED). |
| tidepool | 11 | main | +263/-3 · 4f | *(none)* | **MN** | skill-stall telemetry + WAL row pins; `node --test tests/skill-stall.test.mjs` **1 pass** locally (repo has no CI). |

**Tally: 37 MN · 6 FIX · 2 REBASE · 4 CLOSE = 49.**

---

## 2. CONFLICT-PAIRS (survivor named, what dies)

### Pair A — chiaroscuro #3 vs #7 (both rewrite `edge/worker.ts`, both commit `tools/nl_parity_receipt.json`)
- **#3** (`edge-ts-mirror-parity`): inlines a **TS mirror** of the router into `edge/worker.ts`, data from `edge/synonym_graph.json`; runner `tools/nl_parity.js`.
- **#7** (`edge-worker-graph-port`): `edge/worker.ts` imports `makeRouter` from a **single-source `edge/nl_route_core.mjs`** (+ generated `edge/synonym_graph.mjs` carrying the embedded `GRAPH_SHA256`); runner `tools/nl_parity.mjs`.
- **SURVIVOR: #7.** Evidence: single-source core (one implementation, not two that can drift); `GRAPH_SHA256` re-derived == `sha256(edge/synonym_graph.json)` (`b57f29b0…`). The cards themselves say #7's core "supersedes #3's".
- **DIES: #3 → CLOSE as superseded** (same clean note pattern as quilt-in-git #1→#2). If #3's parity runner is wanted, it must be rebased onto #7's core, not merged as-is.

### Pair B — quilt-in-git #2 vs #3 (and #4 joins them): `.quilt/hooks/post-commit` regenerated three ways
All three are green individually (I ran all three pin suites). The hook is an **add/add** from `main` in each branch, so the **last merge silently wins the hook** and the other features vanish. Verified hook diffs:
- **#2** (`w3b-live-state`): receipt → cascade → auto-commit → watch tick → **`quilt-publish`** (snapshots dials into `refs/quilt/dials` + vitals into `refs/quilt/HEAD`). Ships `.quilt/bin/quilt-publish` + `quilt-read-dials`.
- **#3** (`w3a-notes-signed`): receipt → **`git notes --ref=quilt/receipts add`** → cascade → auto-commit → watch tick. **No publish.** Ships `quilt-audit/fnv1a/verify`.
- **#4** (`w3c-airgap-sparse`): receipt → cascade → **index-vs-HEAD** change detection (sparse-worktree safe) → auto-commit → watch tick. **No notes, no publish.** Ships `quilt-cascade/export/focus/import/tick`.
- **RESOLUTION: merge #2 first, then push a fix-commit to #3's branch that produces the UNION hook (notes + publish + #4-style index-vs-HEAD detection), then the same for #4.** Also `.quilt/bin/quilt-init`, `README.md`, and (for #3/#6) `tests/pins_quiltgit.sh` overlap → rebase each on the previous.
- **What dies if merged naively: the second/third merge silently deletes `quilt-publish` (live-state refs) and/or the git-notes receipts.**

### Pair C — frozen-clock-lab #1 vs #2
Identical file sets; **#2 supersedes #1** (adds P6 sig-canonical + reference vectors). **Survivor #2; #1 → CLOSE.** (#3 then stacks cleanly on #2.)

### Pair D — pong-quilt rounds #88/#89/#90/#91/#93/#94 (shared `core.js`, `README.md`, `index.html`, `PLAYLOG.md`)
Each round appends to `PLAYLOG.md` at the top region. GitHub shows each MERGEABLE **vs main** but they collide **pairwise**. There is a real CI gate (`merged rounds arithmetic`) plus the `newest-first` pin, so **merge strictly in round order with a rebase between each**, and let CI re-verify. #91 is already correctly stacked on #90; #88's base is branch `playtest-round-68` (confirm that is merged).

### Pair E — chiaroscuro #6 vs the #1/#2/#5/#7 edge lane (soft collision)
#6 carries `edge/worker.ts` (keyword-table state), `edge/nl_route.js`, `js/jev_gate.js`, `edge/score_eval.py`, `docs/RD-PLAN.md` — every one of which #1/#2/#5/#7 also touch. #6 is the **root of the KC chain (#9/#10/#12/#13)**, so it cannot simply be dropped. **Resolve #6 LAST** within chiaroscuro with a rebase-fix that keeps the graph router (#7's) in `worker.ts` and #6's non-`worker.ts` content. *(Tools `kc_geo.py` is touched by #10 and #13 — same chain, sequential, no conflict.)*

---

## 3. FIX-BEFORE-MERGE — exact minimal change per PR

1. **quilt-edge-lab#1** — `src/worker.js:211`
   - now: `const quality = +body.quality_score ?? 0.5;`
   - fix: `const quality = +(body.quality_score ?? 0.5);`
   - and the same-shape line in the ledger insert (`row.quality_score ?? 0` → `+(row.quality_score ?? 0)`, ~`:101`).
   - Rationale verified: unary `+` binds tighter than `??`; `+undefined` is `NaN`, and `NaN ?? 0.5` is `NaN` (?? only catches null/undefined) → the default never fires and NaN lands in the D1 promotion row. Add a pin: POST `/promote` with the field absent → assert finite `0.5`.

2. **pong-quilt#89** — `PLAYLOG.md`
   - The `## Round 70 …` block is at **line 110**, *below* `## Round 69` (line 79). Move the whole Round-70 section **above Round 69** (newest-first), and add the R70 row at the top of the canonical index. Then re-run the suite (`newest-first` + `merged rounds arithmetic`). Only 1 commit on the branch — the "repaired at tip" claim is false; this is still RED.

3. **chiaroscuro#2** — land the pre-registration
   - `receipts/` is `.gitignore`d (line 7) and `receipts/lane-c-edge.md` is 404. Either un-ignore `receipts/lane-c-edge.md` (add an exception) **or** move it to a committed path (e.g. `docs/pre-registration-edge-r3.md`), and update `tools/edge_graph_receipt.json`'s `provenance` + `docs/RD-PLAN.md` §Round 3 to point at it. If the `edge/nl_route.js` overlap-phrase guard is a rules change (the receipt's own `router_version_note` says it was **added before the run**), seal it as its own revision.

4. **pong-quilt#92** — the `n=1` horizon claim
   - Cheapest sound fix: annotate the sentence as a **single-arm read** (same discipline as the existing `noLearningClaim` marker) — e.g. add a `singleArmClaim: true` marker beside `noLearningClaim` in `research/c1-scaling-2026-10-01.json` + the README line. Stronger: run the long arm at ≥3 seeds and report the last5 **band**. Either is acceptable; the sentence must not outrun its n. *(Verified: arms[6] is the only 160-gen arm, seed 20261001; arms[2] shares seed+pop96 and already rises 172→685.8 over the same first-40 window.)*

5. **quilt-in-git#3** — union hook (see Pair B): preserve #2's `quilt-publish` call + #3's `git notes --ref=quilt/receipts add`, on top of #2.

6. **quilt-in-git#4** — union hook (see Pair B): #4's index-vs-HEAD detection + #2's publish + #3's notes; requires rebasing onto main-with-#2-and-#3 so `.quilt/bin/quilt-publish` exists in the tree.

*(The 6th drafted-review target, chiaroscuro#5, is **not** a defect — it is a replication offer. It is classified **MN**; if the keeper wants the replication, that is a comment, not a merge blocker.)*

---

## 4. CLOSE-CANDIDATES (keeper decides — nothing here is deleted, only closed)

| PR | reason | evidence |
|---|---|---|
| **Patchwork-experts#1** | file already on main; readme edit regresses main | `docs/suggestions/2026-10-01-verification-layer.md` = `312d64ff…` on **both** main and the branch; branch `readme.md` is the older prose form vs main's table form. |
| **quilt-in-git#1** | builder's own merge-order note | comment 2026-10-01T23:27:24Z: merge #2, close this. |
| **chiaroscuro#3** | superseded by #7 | Pair A. |
| **frozen-clock-lab#1** | superseded by #2 | Pair C. |

---

## 5. MERGE PLAN — ordered keeper actions

**Principle:** land the zero-collision, self-verifying PRs first (docs/specs/receipts/standalone tools), then walk each repo's stack in dependency order, then the conflict pairs with union fix-commits, and close the 4 last. Rebase (not comments) is the default when a branch has merely gone stale.

### Wave 1 — standalone / no collision (merge directly; ~16)
`AI-Writings#73`, `AI-Writings#74`, `MicroMoth-quilt#30`, `fleet-triage#3`, `fleet-triage#4`, `quilt-Kuramoto#2`, `quilt-tools#34`, `tidepool#11`, `quilt-arcade#5`, `quilt-arcade#6`, `pie-minimax#2`, `quilt-in-git#5`, `quilt-in-git#7`, `chiaroscuro#4`, `quilt-edge-lab#2`.
*(no two touch the same file; each individually verified above.)*

### Wave 2 — per-repo stacks, root→leaf (dependency-aware)
- **chiaroscuro edge lane:** `#1` → `#2` *(after fix #2)* → `#5` → `#7` *(survivor; close #3)*.
- **chiaroscuro KC/doc chain:** `#6` *(after REBASE-fix)* → `#9` → `#10` → `#12` → `#13`; and `#8` → `#11`. *(Merge the #6 chain before rebasing #6 if you prefer to keep #6's diff minimal — but #6 must not clobber #7's `worker.ts`.)*
- **frozen-clock-lab:** `#2` *(survivor; close #1)* → `#3`.
- **doubt-ledger:** `#1` → `#2`.
- **quilt-in-git:** `#2` → `#3` *(after union-hook fix)* → `#6`; then `#4` *(after union-hook fix + rebase)*. Close `#1`.
- **quilt-edge-lab:** `#1` *(after `??` fix)* → `#3` *(rebase; DEBRIEF.md)* → `#4`.
- **pong-quilt:** `#88` → `#89` *(after PLAYLOG order fix)* → `#90` → `#91` → `#92` *(after n=1 fix)* → `#93` → `#94` — **strict round order, rebase between each**; let `test`+`forge` re-verify each time.
- **quilt-gpu-lab:** `#6` *(REBASE only — mechanical)*.

### Wave 3 — closes (keeper sign-off)
`Patchwork-experts#1`, `quilt-in-git#1`, `chiaroscuro#3`, `frozen-clock-lab#1`.

### Canonical keeper commands (examples — keeper runs these, not this lane)
```bash
# rebase a stale-but-sound branch
gh pr checkout 6 --repo SuperInstance/quilt-gpu-lab   # then: git rebase origin/main, resolve, push
# push a fix to a PR branch without merging
gh pr checkout 89 --repo SuperInstance/pong-quilt     # edit PLAYLOG.md, commit, push
# merge a sound PR (squash keeps the round/spec history linear for the stacked repos)
gh pr merge 2 --repo SuperInstance/quilt-in-git --squash
```

---

## 6. RISK & OPEN QUESTION

**Biggest risk:** the **chiaroscuro stack has 13 open PRs whose bases chain into each other** (1→2→{3,5,7}; 6→{8,9}→{10,11}→12→13) and five of them rewrite the *same* `edge/worker.ts` / `edge/nl_route.js` / `js/jev_gate.js`. GitHub reports every one as `MERGEABLE/CLEAN` **against main today**, which lulls a keeper into merging them in any order — but each merge re-points the next base and the **last writer silently wins `worker.ts`**. Merging chiaroscuro out of order can quietly delete the graph router (#7) in favour of the keyword table (#6/`#1`), with no CI to catch it. **Same class of silent last-wins risk in quilt-in-git's hook (Pair B) and pong's PLAYLOG.** Mitigation: merge strictly root→leaf, rebase between, and after each stack merge re-run that repo's pins.

**Next question for Casey:** the 4 close-candidates and the 2 union-hook fix-commits change PR *branches* I (read-only) should not push to. **Do I have the mandate to (a) push the 6 fix-commits to their branches and (b) merge the 37 MN PRs in the Wave-1/2 order — or does the keeper want to execute from this plan?** (Also: `doubt-ledger#1/#2` and `frozen-clock-lab#2` commit `__pycache__/*.pyc` — worth a `.gitignore` follow-up PR; flagged, not blocking.)
