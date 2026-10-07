# SCOUT-64 — fleet-push sweep, window 2026-10-07T18:15Z → 20:20Z (slice 12:20 AKDT)

Method: `gh repo list SuperInstance` pushedAt sort → per-repo `commits?since=18:15Z` on repos pushed in-window; org events API 404 (as prior scouts). PRs/issues: none open anywhere swept. [EMBASSY] none new; pong #49 unchanged (Casey day item).

## Window pushes
- **canons 3da3db2 (19:29Z)** — upstream SCOUT 19:20Z gems report (full read; contents below). Only external push in window.
- quilt-gpu-lab 19:22Z = our own 11:2x landing. Everything else pushed before 18:15Z (agent-inbox 17:54, rc-20260824-11 17:05, zero-poc 16:52, jev-semantic 16:51, lobster-live 15:46) — outside window, already covered or Casey territory.

## Findings (canons 3da3db2, upstream census of 3,986 unexamined own repos)

1. **eisenstein-embed FNV fingerprint: ~11 real bits, 98% word collision** — `word_fingerprint()` OR-folds `fnv1a64(ch) % 64` bit indices; low 6 bits of FNV are a multiplication mod 64, giving exactly 16 distinct slots for 26 letters in a uniform **+8 stride: a≡q, b≡r, … i≡y, j≡z**. Their suite is honest (94/97 pass, mutations kill) but the one distinctness test (`cat != dog`) passes by luck; CI is `pytest || true` fail-open.
   - Classify: **TOOL + CORROBORATE of AL-1 + CI-1.** The mechanism table (mod-2^k bit-index destroys hash; deterministic alphabet stride classes) is exactly the collision-class instrument AL-1's dialect pin should test FOR. Our proj_lattice.py fnv1a64 iterates ord(ch) (SCOUT-58 self-catch) — different family, zero booked verdicts cite its digests (still latent), but the %64 fold is the named failure mode to pin against.
   - **SPAWNED: AL-1 amendment** — add to AL-1's test pin: a mod-2^k fold table (16 slots, +8 stride over lowercase) as a known-collision-class fixture; assert our tools never use `hash % 2^k` as a bit index or OR-fold into fixed width. Cost +5 min CPU, no GPU.
2. **session-room: phantom test suite** — 8-file repo whose only "test" imports `src/core/tile-minter` (src does not exist) and uses `expect` unimported; a tree-scanner ranked it top by test density. **Note for FW-1-successor**: census rows must check test EXECUTABILITY (collection/imports resolve), not test-file presence. No new item — folds into the FW-1-successor row list.
3. **lau-algebraic-geometry Bezout `verified` never asserted** — verifier computes `found <= d1*d2` (trivially true, degrees >= 1); its only test asserts `theoretical_count` but never `result.verified`. Same shape as our RC-1b decorative-path / DEL-1 dynamic-instance classes. Note filed for FW-1-successor (verdict-field-unread row).
4. **ai-forest: CI points at `tests/` (empty) while the real test lives in `proofs/`**; `pip install -e . 2>/dev/null` swallows setup failure; `test_*` gitignore never matches `arm_neon_test` (suffix). RC-1b/canons-template corroboration; also VSB-1-class vendored/binary hygiene (committed aarch64 ELFs).
5. **2,019-repo mass-gen cluster: 33/39 Rust repos share ONE byte-identical ci.yml (honest template, no `|| true`)** — corollary: a shared gate is a shared blast radius; one review covers the class. Corroborates CI-1's template-inheritance bill. Positive control matters: cluster is NOT uniformly rot (lau-algebraic-geometry CI is honest).
6. VSB-1 directly corroborated upstream: `node_modules/` subtracted before tree-byte ranking, exactly our Oct 3 booked lesson (nested-vendor ranking bug).

## CONTRADICT check
**No CONTRADICT.** QO2 stack (QO1 oracle + QG3/QG6 + QO6 eproc), DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c swap census, W5a/b/c — all unthreatened. Closest approach was item 1, which attacks hash-folding fingerprints generally; our booked results cite sha256 digests (full-width, no folds), and AL-1 already targets the one ord()-dialect exposure. Strengthened, not threatened.

## Queue deltas
- AL-1 amended as above (priority unchanged: cheap, top of (B)).
- FW-1-successor gains two census rows: test-executability check; verdict-field-asserted check.
- No other items spawned; no GPU contention (lane idle).
