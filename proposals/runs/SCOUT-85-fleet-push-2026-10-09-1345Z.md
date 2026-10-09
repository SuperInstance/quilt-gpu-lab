# SCOUT-85 — fleet push window 11:45Z→13:45Z 2026-10-09 (post-SCOUT-84)

Swept: search/commits org-wide (committer-date>=11:30Z), open PRs across 9 repos, new issues.

## Window pushes
- **canons b87ae87 (13:19Z)** — `SCOUT-2026-10-09T1319Z-two-doors-that-never-open`: census re-derived
  paged to exhaustion, **5,208 repos PASS assert** (vs 5,202 in our SCOUT-76 note; RC-2 drift +6,
  ~11.9 repos/day — a 2-week census is ~170 stale). Three deep-dives:
  1. **quilt-canvas-tui**: flagship cross-language byte-equality test NEVER RUNNABLE — JS Fabric
     digest vs Python kernel port, but PY_PORT hardcodes `/tmp/quilt-canvas` AND `cell_api` lives in
     a different repo (`quilt-c`) entirely; 0 workflow runs ever. Same class as xruntime-conformance
     hardcoded /tmp but strictly worse (reference impl cross-repo). Everything else in the suite is
     honest (mutation-bites; correct FNV-1a64 with classic test vector).
  2. **constraint-theory-py** (new, pushed today): A2 covering-radius claim INDEPENDENTLY VERIFIED
     (20k random points, max err 0.57709 < 1/sqrt(3), never worse than brute force). Key method
     lesson — 4 mutations stayed 167/167-green and ALL were equivalent mutants (self-correcting 3x3
     search absorbs them); only the behavior-changing one (delete the candidate search) was caught.
     Their carry-forward: **"mutation → still green" is NOT evidence of a vacuous check until you
     show the mutant changes behavior.** Also: hygiene CI checks 3 of the 13 categories its own
     .gitignore lists and the repo violates one of the missing (5 tracked egg-info files) —
     enumerated-subset-gate defect; derive checks from the ignore list.
  3. **zero-innate**: swappable-model wooden horse, honest-scaffold framing; 19/19. Watch only.
- **rc-20260824-11 63057af (12:06Z) — q26**: q25's +1.13pp merge-union gain was a **capacity-pressure
  size artifact** (48-cell merged footprint evicting other questions at CAPACITY=70); INTERSEC
  (shared-core topup) is the best arm; q22 limit gate survives Q0 topology evolution by default once
  MERGE preserves footprint size. Opens q27 (footprint breadth ↔ flip cadence 4→1-2).
- quilt-atlas 43f9ed6 / plato-portal 4f55b48: scheduled auto-regens, routine.

## Classification vs our assets — **NO CONTRADICT**
- QO2 stack, DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c, W5a/b/c: unthreatened.
- **CORROBORATE**: rc q26 size-artifact law is fleet-side resonance of our **D12i** (width artifact —
  "universal" evaporates under correct sizing) and QG6 (footprint/width inert-to-harmful). Different
  substrate, same discipline: normalize the footprint before crediting the mechanism.
- **CORROBORATE (classes)**: quilt-canvas-tui = RT-D1 real-probe gap + CI-1 (no workflows) +
  RC-1b/hardcoded-path; no booked result of ours touches cross-language digests.
- **TOOL → spawned EM-1** (below): equivalent-mutant precondition for our mutation-lite rows.
- CI-1-AMEND gains the enumerated-subset-gate row (derive CI checks from .gitignore, not a YAML
  subset) — appended to the existing docs item, not a new spawn.
- Census 5,208: RC-2 drift note updated. Issues: zero-msg-test #19-#23 = API-noise class, ignore.
- [EMBASSY] pong #49 unchanged (Casey day item).

## SPAWNED
- **EM-1** (CPU docs ~15m, pre-reg not required — method note): amend TIE-1 + PARAM-1a receipts and
  the FW-1-successor spec with the equivalent-mutant precondition: a mutation-row may only be filed
  as a blind spot AFTER demonstrating the mutant changes measured behavior (output diff or harness
  counter); cite canons b87ae87 constraint-theory-py method correction. Gate: the amended receipts
  contain zero mutation-rows that lack a behavior-diff; TIE-1a's 22/22 census stands unchanged
  (its flips were behavior-checked by construction — verify, don't assume).

No GPU fired (scout slot per rotation). No PRs open anywhere swept; no 429s.
