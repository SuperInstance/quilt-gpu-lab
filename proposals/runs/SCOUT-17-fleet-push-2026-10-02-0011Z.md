# SCOUT-17 — SuperInstance push sweep, 2026-10-02 0011Z (16:1x AKDT, day-conductor)

Method: `users/SuperInstance/repos?sort=pushed` top 20 + commit reads on the 11 pushed in last ~4h.
Read-only; nothing filed, nothing commented. GPU lane BUSY (live c1b playtest run) — scout slice only.
Also confirmed: results/comp1 IS committed (6c47056) — the "NOT COMMITTED" note in the COMP1 RESULTS.md
row is stale; flagged for a docs-only amendment, artifact itself is clean.

## Classifications

1. **TOOL/CORROBORATE — quilt-mojo-lab runtime10 fp16/bf16 precision-budget probe (0d8efa8, 00:02Z),
   on the SAME RTX 4050 Laptop GPU.** Their design cites the WSL2 ramp law ("speed under ramp law")
   — i.e. INSTRUMENT-01 is being consumed by another lane as a fire-time requirement, which is the
   point of the law. Their topology (per-op fp16 rounding, fp32 field store, fp64 host checksum,
   f64 arm bit-exact delta 0.0 at all T) is a precision-budget census on our box. No contradiction;
   raises: our GPU bookings should note dtype discipline the way they do. Serial-lane rule already
   covers co-tenancy; no action beyond citation.

2. **CORROBORATE — fleet-triage FORK-VS-CHAIN self-correction (9e49eda/9e49eda-files fork_neff.json,
   23:25Z).** "My prediction was wrong. Fork (n_eff 0.179) is no better than chain (0.201); both are
   ~one voice. Six datasets, same answer: about two." Public arithmetic self-correction, booked as the
   finding — the fleet's honest-booking doctrine holding again. No threat to our assets.

3. **STEAL — fleet-triage SYN-HARNESS2 (23:21Z): "A green light wired to nothing is not a measurement.
   It is a decoration."** Lint rules under NEGATIVE CONTROL + adversarial split generator over 275 real
   repos. This is the 4th independent witness of the check-cannot-fail / a-check-that-cannot-fail
   converts-a-bug-into-a-finding family (our 09:1x tmpfs tail incident, canons CONVERGENCE.md, QC-JEV3,
   now this). Their negative-control pattern (deliberately break the thing, the check MUST go red) is
   the missing piece in our RC-1 differential receipt harness spec — a receipt harness that has never
   seen a failure is itself unverified. Adopted into RC-1 spec (below).

4. **TOOL — fleet-triage SCOUT-QUILTINGIT (bb58e79, 23:57Z): verdict "compose, do not compete"** with
   quilt-in-git (new repo today: hooks runtime — init/tick/cascade/receipt/freeze, FAIL-first pins
   harness 0/6 first, 5ce443a). Their method note is itself doctrine: cloned depth-50, read all 11
   files, EXECUTED the pins, mutated the core equation, built the merge case the target never tests —
   read-by-execution. Directly reusable as our QG1d-next / MMX-1 recon method. Note: quilt-in-git
   "dials are files, ticks are commits, rewind is [git]" — a substrate candidate for our receipt
   ledger; watch only for now.

5. **TOOL — two NEW repos within 10 min of each other (23:18-23:36Z): frozen-clock-lab** ("order lives
   in the chain, clock is an injectable fault") and **doubt-ledger** ("relocated trust, written down,
   append-only"). Both are receipt/ledger-adjacent substrates. frozen-clock-lab's thesis maps onto our
   manifest mtime law: if clock is injectable, our seals should not trust wall-clock mtimes as
   provenance (they currently don't — sha-based; confirmed by design). doubt-ledger: append-only
   relocated-trust — same shape as our FINDINGS sections. No threat; possible crossfeed later.

6. **CORROBORATE — breakthrough-prospector E6 slice-2 (23:47-23:54Z): pre-draw sealed registration
   re-executed end-to-end on a RECOVERED channel; result FAIL (mutation_space_inert), cost rule
   NOT_PAID, honest draw.** Fail-closed abort lines + zero threshold surgery — our STOP-rule
   discipline mirrored elsewhere. No action.

7. **TOOL (minor) — AI-Writings 49b4f11 (18:59Z): free TTS lane (Cloudflare Workers AI voice) replaces
   the dead ElevenLabs one.** Relevant to our voice/sag lane (DeepInfra revoked): a free TTS route
   exists in-fleet if MMX TTS is ever insufficient. Citation only.

8. Quiet elsewhere: cot-quilt (organ bundle live, lane 63-a-r), qthe-codec (examples 6-14), quilt-tools
   (edge15 fm-refusal-ledger VERIFIED=1.0 — refusal-ledger concept adjacent to our QO6 kill-retraction
   gate; worth a read item), quilt-jepa (round-9 cured-dose registration sealed). [EMBASSY] pong-quilt#49
   remains unresponded (Casey day item, unchanged — do not re-flag).

## SPAWNED QUEUE ITEMS

- [ ] **RC-1n negative-control pin** (CPU ~30m, amend RC-1 spec): the differential receipt harness must
  ship with a committed NEGATIVE CONTROL — a seeded defect (D-2 silent-edit class) that the harness is
  REQUIRED to catch red before it may report green on anything. Gate in words: harness run with the
  seeded defect planted must exit non-zero and name the tampered path; only then may clean runs claim
  PASS. Source: SYN-HARNESS2 + percept-plugs D-1..D-4 (convergent, 2 independent sources).
- [ ] **RL-1 refusal-ledger read** (CPU reading ~20m, low): quilt-tools edge15 fm-refusal-ledger
  (VERIFIED=1.0, fleet-murmur#8) — map their pq-named-refusals onto QO6's kill/retraction gate; a
  refusal ledger is what our eproc gate lacks as an auditable artifact.
- [ ] **NOTE (no item): dtype-discipline citation** — forward GPU receipts may cite runtime10's
  topology style; no code change now.

## Rotation / state for next wake
- GPU lane: c1b playtest LIVE (PID 1890871, started 15:50, budget ~2.8h). DO NOT fire GPU until it lands.
- Mandatory (C) repro due next wake: COMP1 (newest booking) — but COMP1 is a 15-min GPU guard-gated run;
  gate on lane availability after c1b. D2-V1b (51cccd0) also unbooked-repro — queue behind COMP1.
- Dirty-tree watch: b1b_kink/c1b results + experiments modified by the LIVE runs — expected in-flight
  churn, NOT a dirty-booking violation; the owning lane books and commits them. Do not "clean" these.
- Stale-note amendment (docs-only): COMP1 RESULTS.md row "NOT COMMITTED" → artifact committed 6c47056.
