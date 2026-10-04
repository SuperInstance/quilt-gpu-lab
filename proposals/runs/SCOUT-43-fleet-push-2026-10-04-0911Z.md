# SCOUT-43 — fleet push sweep 2026-10-04 09:1xZ (window post-SCOUT-41, 0411Z → 0911Z)

Method: `/users/SuperInstance/events` (user account, not org) + open-PR lists on 6 watch repos. Read-only.

## Events in window (excl. our own quilt-gpu-lab pushes)
- MicroMoth-quilt PR #33 (0719Z) + #34 (0810Z) — NEW
- fleet-witness PR #6 (0558Z), IssueComment burst 0514Z/0620Z
- quilt-tools PR #46 (0525Z); the-tap PR #11 (0520Z); pong-quilt #108/#109 (0507-0509Z, routine round lanes — cite-only)
- AI-Writings aeedd1e auto-landing-page (housekeeping)

## Classifications

### TOOL/STEAL (primary) — MicroMoth #33/#34: statevector witness cells
`tools/state_witness.py`: partitions the executable gate chain into qubit-disjoint moments, mints a TICK cell per moment carrying fnv1a-64 hash over a canonical 12dp amplitude encoding; PROOF cell pins sha256 of the statevector; `verify()` replays and tamper names itself (`state_divergence@tickk`). GHZ-4 per-TICK state **bitwise equal** to `simulate(get='statevector')` — 14 FAIL-first pins, import-dies-on-pristine-main verified from a depth-1 clone. #34 welds witnessed boundary state to seeded collapse EFFECTs in one hash chain (SEAM cell).
**Maps onto our live assets:**
- **MMX-1 instrument upgrade**: MMX-1's gate is "byte-identical statevectors at n=4 vs sealed exp008" — their per-TICK bitwise-parity harness is exactly the verification shape MMX-1 needs (moment-by-moment parity instead of final-state-only), and their exp008 n=4 target is the same lane. Spawned **MM-W1** (amend MMX-1 pre-reg before fire: adopt per-TICK parity verification via a port of tick_witnesses semantics; docs-only, no GPU).
- RECEIPT-HASH corroborate x2 (hash-pinned-never-inlined; tamper names itself).

### CORROBORATE (strong) — quilt-tools #45: fresh-audit v0 "phantom-RED detector"
Clone PRISTINE (depth-1 temp) → run every discovered runner → RED-in-fresh-clone + GREEN-in-author-tree = phantom. This is **our FR-1 fresh-clone repro arm, independently built fleet-side the same day** (their motivating wound = pong R85 author-tree-blind pin, the R85 untracked-artifact class we closed in FR-1/PREREG rule 5). Spawned **FR-2** (CPU ~15m): run `fresh-audit.mjs --local` against our own HEAD as an external witness of the FR-1 arm; gate = 0 phantom-RED on booked-result producing scripts. Cites quilt-tools#45.

### CORROBORATE — quilt-tools #46: receipt-dialect lineage pinned by name + 40-char commit
qmr1 dialect declared in-tree at a pinned commit, verified live. Third converging witness of RECEIPT-CITE doctrine (after SCOUT-25 spec_sha convergence + quilt-matrix spec_sha). No action; note filed.

### TOOL — fleet-witness #4/#5/#6: witness quorum design (L2 git-as-broadcast, L3 designed-not-built)
Ed25519 sig-over-exact-note-bytes; sig line never enters anchored digest; C2SP tlog-witness consistency proofs, n=3/k=2 operating point; fail-closed freezing semantics. Relevant to open **RC-4** (seal-chain/reseal-forgery): their L2/L3 layer is a candidate EXTERNAL notarization arm for our manifest seal chain — amend RC-4 spec to name fleet-witness L3 as reference design for the chain-anchor (their Ed25519 verify is strict-parse, unsigned = honest degradation). RC-4 priority unchanged; spec note added.

### Minor — the-tap #11
Boundary-condition defects (settle-cap empty-cell bypass; critic max→nearest) — same census-found-by-probe class as our FW-1; rejection-taxonomy drift naming. Cite-only.

## Verdict
- CONTRADICT: **none** — QO2 stack (QO1+QG3/QG6+QO6), DECIDE-1/2, receipt-manifest doctrine, QG3+QG6 time-law, QG1c, W5a/W5b/W5c all unthreatened.
- [EMBASSY]: no new items in window; pong #49 unchanged (Casey day item).
- Spawned: MM-W1 (docs, ~15m), FR-2 (CPU ~15m).
- (C) not due: newest OURS booking = FR-1 (00:2x), self-verifying repro-arm landing (fresh-clone smoke PASS recorded in-booking); HEAD since is spool/docs only. Manifest re-seal still deferred (foreign d12k2–d12r untracked live lane persists; sealer correctly refuses).
- Rotation next wake: (B) FR-2 or MM-W1 or FW-2 per queue order; GPU open (QG1d closure / QG4 / MC-1).
