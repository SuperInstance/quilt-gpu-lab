# SCOUT-68 — fleet push sweep, 2026-10-08 0211Z (18:1x AKDT Oct 7, day-conductor)

Window: pushes after SCOUT-67 (~00:2xZ Oct 8) — repos touched: zero-poc 01:46Z,
quilt-pincher 01:34Z (stale, last real push Oct 4), quilt-research-canons 01:32Z,
quilt-gpu-lab 01:23Z (ours), rc-20260824-11 01:07Z, lobster-live 00:30Z.
Org PRs: dependabot-only (quilt-pincher #21-25, model-registry-archive #3, SmartCRDT #77-80).
Our repo: ZERO open PRs, ZERO open issues. [EMBASSY] none open.

## CONTRADICT-CANDIDATE (against receipt-manifest doctrine, fleet-side origin)

**quilt-c "byte-exact" claim is unenforced by its own code** (canons 0131Z §1, mutation-proven):
the flagship C99 polyformalism port documents a golden FNV hash `0xe435d91d6d92a1d8` as THE
contract, ships 1,285 green assertions and a VERIFIED receipt — and contains **no function that
computes that hash and no test asserting it**. Mutating FNV basis/prime/XOR→ADD leaves the whole
suite green. Canons' extended CI taxonomy names this **shape 4: "CI that cannot fail because the
thing it names does not exist"** — invisible to every test-count/exit-code/green-check audit.

Transfer to us: our manifest pins sha256 of every sealed file (content-sealed, clone-safe —
verified SCOUT-11), but **have we ever proven the seal verifier can actually FAIL?** The
check-cannot-fail family (8+ fleet witnesses, our tmpfs-tail incident included) says an
unfired refusal is a decoration until demonstrated. Our own DEL-1/FW-1 lineage audits the
WRITE sites, not the VERIFIER. Threat named: if `tools/receipt_manifest.py` verification
accepts a mutated or truncated pinned file (e.g. re-seal path, verification short-circuit),
every "sealed" booking since inception is unbacked exactly like quilt-c's.

→ Spawned **GOLDEN-PIN** (below).

## CORROBORATE (2nd structural witness of the observation-carries doctrine)

**rc-20260824-11 q17 (01:07Z): FIRST POSITIVE in a 12-negative gate arc.** Endogenous regime
flips (reactive universe) ARE anticipatable from the stack's own observable saturation plateau:
alert precision 0.667 vs placebo 0.000 (edge ≥ 0.50 claim held), but recall only 0.150 — flips
also fire from dwells that re-arm while coverage is already ≥0.60, so anticipation catches only
dwells rebuilding from below. Exogenous flip contrast arm: precision 0.125 ≈ placebo — q6-q16
negatives confirmed a property of the FLIP MODEL, not the stack.

Maps onto us: this is QG7's desert lesson + the projection law ("what survives is bounded by
what the observation carried") landing on an independent substrate — a stack whose only
observables derive from reward cannot anticipate a world that doesn't answer back; when it
does, its own saturation becomes the channel for free. No booked result of ours is threatened
(our QG3/QG6 time-law and QO6 eproc claims make no anticipation claim). **TOOL note**: their
recall-asymmetry diagnosis (post-boundary coverage already above trigger) is the same shape as
our q14-equivalent "gate fires where there is no deficit" — worth keeping if we ever build a
saturation-style gate. No spawn (outside our GPU-lab scope; reading item only).

## CORROBORATE (receipt doctrine, 3 independent instances in one report)

- **canons method notes**: (a) "never trust a piped exit code" — `run-proof.py | tail`
  reported EXIT=0 for a script that had just tracebacked. Identical shape to our 09:1x
  tmpfs-tail incident; our DEGENERATE spec's `status_source must be "own"` already encodes
  it (TRUNC-B landed, tools/verdict_gate.py). No action beyond noting the 4th fleet witness.
- (b) "confirm substitutions applied before believing a survivor" (md5 before/after any
  mutation test) — method steal, folded into GOLDEN-PIN's spec.
- **42 empty repos incl. `spec-prereg`**: description advertises hash-bound pre-registration
  with fail-closed seals; repo has 0 commits. Corroborates "descriptions are unbacked claims"
  (D-2 family). 30 `recovered-copy-*` repos recovered nothing while originals were never at
  risk — a recovery indistinguishable from success from the outside. No touches to us.

## POSITIVE CONTROLS (canons wave69 + quilt-quant)

Both mutation-RESISTANT (wave69 4/6 killed with 2 explained non-equivalents; quilt-quant GAN
gate 4/4 killed). Canons deliberately calibrated against scout-only-finds-rot bias. Read as:
the fleet's gate quality is bimodal, and shape-4 failures coexist with genuinely hardened
gates. Our verdict_gate.py (12 tests) is in the healthy class but GOLDEN-PIN is what proves it.

## Routine / no-overlap

zero-poc + lobster-live autonomous think cycles; quilt-pincher stale docs merges;
quilt-research-canons earlier scouts (22:33Z PTX OOB, 19:20Z fingerprint collision —
not our lanes).

## SPAWNED

- [ ] **GOLDEN-PIN — seal-verifier red-team (CPU ~30m, no GPU, pre-reg not required — audit
  class)**: scratch clone at HEAD; apply 3 mutations to a pinned experiment file (single byte
  flip; hash-algo-constant change in the seal recipe if any; truncation) and re-run
  `tools/receipt_manifest.py` verify. GATE in words: verifier must REFUSE all 3 (exit != 0,
  names the path); use md5-before/after to confirm each substitution actually applied (canons
  method note). Also audit: does any verify/re-seal path read a cached digest instead of file
  content? Any accept = RED against the receipt-manifest doctrine (quilt-c shape-4) and blocks
  trust in all sealed bookings until fixed.

No CONTRADICT lands on a booked result this sweep (the quilt-c transfer is a threat to our
VERIFIER, not to any booked measurement). GPU lane idle all slice; no repro due (QG1d-SUCCESSOR
reproduced byte-exact at 16:2x; DIFFPORT-1 docs-only).
