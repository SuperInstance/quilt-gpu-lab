# XP-B PRE-REGISTRATION — "git-hook receipt gate vs corruption corpus"

Lane: XP-B (quilt-gpu-lab pushwave §2c). Seed: **2718**. Date: 2026-10-01.
Written **before** any corpus generation or gate run. Fail loud.

## Claim under test
A commit-time hook can enforce cell honesty: it **refuses every pre-registered
corruption class** with **ZERO false rejects** on clean commits.

## Design (frozen)
- Synthetic history: **120 commits**, seeded 2718, in a fresh git repo.
- Each commit stages cell file(s) `cells/cell_NNN.json`:
  `{id, kind, dials:[16 ints], seed, body}`.
- **Canonical state** for a commit = compact sorted-key JSON of, for every staged
  cell (sorted by path): `{cell_id, kind, dials, seed, body_sha256}` **plus**
  `corpus_seed=2718` and `prev_receipt` = parent commit's receipt digest
  (`GENESIS` for the root). Chain-linked.
- **Receipt digest = sha256** (256-bit) of the canonical state bytes.
  FNV-1a-64 of the same bytes is ALSO recorded in the receipt line (audit arm only;
  its adequacy is exactly what M4 tests).
- Receipt line embedded in the commit message, one per commit:
  `qthe-receipt@1 seed=2718 sha256=<64 lower hex> fnv64=<16 lower hex> prev=<64hex|GENESIS>`
- Gate: recompute the canonical state from **staged** cell files (`git diff --cached`),
  recompute sha256 + fnv64 + chain link, compare to the receipt line found in the
  commit message. Any mismatch / malformed field ⇒ **refuse, exit 1, named reason**
  (fail loud). No keys, pure digests.

### Hook-stage rule (pre-registered because it was discovered during setup)
Git does **not** expose the pending commit message to `pre-commit`
(`.git/COMMIT_EDITMSG` is either absent on the first commit or holds the *previous*
commit's message — verified empirically before build). Therefore the gate is
installed at **both `pre-commit` and `commit-msg`**:
- `pre-commit` mode: structural validation of staged cell files only.
- `commit-msg` mode: full receipt/chain/digest validation (message file = `$1`).
Enforcement is judged at commit time (the commit must be refused). This hook-stage
fact is itself reported as a gate-design finding, not hidden.

## Pre-registered mutation classes (K=5)
- **M1** dial changed without receipt update — mutate one dial in a staged cell;
  keep the old receipt line. Expect REFUSE (sha256 mismatch).
- **M2** receipt reused from an earlier commit (chain-repair attack) — use commit
  k-1's full receipt line for commit k (different state). Expect REFUSE (state +
  chain mismatch).
- **M3** truncated receipt — truncate sha256 to 40 hex / drop `fnv64`. Expect REFUSE
  (format check).
- **M4** FNV-1a-64 collision, documented honestly at 64-bit. Measured by:
  (a) genuine collision construction exploiting FNV-1a last-byte linearity
      (two prefixes whose states agree in the top 56 bits, patched with one suffix
      byte each) — birthday cost ~2^28, verified by direct recomputation;
  (b) full-output avalanche (1-bit input flip → output bits changed) FNV-1a-64 vs
      sha256;
  (c) birthday model + observed collision count at the largest feasible N.
  Gate op: stage a cell whose recorded FNV-64 is a genuine collision of the honest
  one, keep the old receipt. Expect REFUSE (pinned sha256 + full 96-bit receipt).
- **M5** GPU-derived cell replayed with a mutated seed — one 10 s torch matmul tick
  under `guard.py` (`Guard(task_id="XP-B-hook-gpu-cell")`; preflight/run/emit_receipt)
  at seed 2718 ⇒ clean commit must be ACCEPTED; then replay at seed 2719 with the
  seed-2718 receipt retained. Expect REFUSE. Determinism control: the seed-2718 tick
  runs twice; dials must be byte-identical or the GPU-cell class is reported
  NOT-DETERMINISTIC (and M5 booked accordingly). The ONLY GPU use allowed (~30 s).

## Gates (pre-registered)
- **KEEP** iff every class in {M1..M5} is REFUSED **and** every clean commit
  (all 120 history commits + explicit clean re-commit) is ACCEPTED.
- **KILL** if any class passes the gate, or any clean commit is rejected.
- **INCONCLUSIVE** if FNV-1a-64 collisions force a digest upgrade **mid-run**
  (report the collision rate — itself a finding).
  Note: the gate is pre-registered on **sha256**, so an FNV collision does not
  upgrade this gate. Should M4 find that an *FNV-primary* gate would have been
  forced to upgrade, that is recorded as a finding and the sha256-primary verdict
  stands; the FNV-primary counterfactual is reported explicitly.

## Budget
~25 min CPU, ≤30 s GPU (M5 only), zero API. Repo work in `/tmp/xpb-hook-lab`.
Final artifacts copied to `experiments/xp_b_hook/`; raw results to `results/xp_b/`.
No commit — keeper commits.
