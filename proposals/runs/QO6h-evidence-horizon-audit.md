# QO6h — evidence-horizon audit of the QO6 kill gate

**spawned by:** SCOUT-54 (rc-20260824-11 q10 law: "per-cell ledger evidence decays on the same clock as the hold; refill and molt timing structurally misaligned" — their case is evidence window expiring BEFORE decision time ⇒ refill loses).
**question:** Does the QO6 eproc kernel have any path where the evidence readable at decision time is LESS than the evidence the decision consumed — i.e. an expiry horizon shorter than decision latency (the q10 failure mode)? Assert NO, fail loud if a hole exists.
**cost:** CPU, seconds. Deterministic, no RNG, no GPU.

## Pre-registered gates (words, frozen before fire)

For each of the four frozen QO6 kernel streams (drift_down 40, flat_noise 200, V2 bloom 19, V3 hopeless 14), replay stepwise: at every prefix length t compute `witness(prefix)` (same frozen sigma/delta/claim as the kernel) and record E(t), finite-ness, and retraction state.

- **H1 (no-expiry):** for every prefix t ≥ 2, the readable horizon at t equals t — E(t) is computed from the FULL prefix [0..t] with no sliding/expiring window. Concretely: recomputing witness on the full prefix at stop_t reproduces the kernel's E at its decision exactly (bit-equal) for every gate decision taken in the kernel (KILL_CANDIDATE / KEEP-retracted / INSUFFICIENT).
- **H2 (readability ≥ latency):** E(t) finite at every t from first-eligible through stop_t for every stream that reaches a decision; readable horizon (last finite t) ≥ decision latency (stop_t) at every decision.
- **H3 (q10 analogue fails loud):** no decision in any stream is made where E at decision time is derived from a prefix strictly shorter than the stream length at the decision (i.e. no "stale-window" decision). Any violation ⇒ RED, hole booked, QO6 spec amendment required before any further QO2 kill-matrix work.

**Interpretation:** ALL PASS ⇒ the q10 failure mode is structurally impossible in our kernel and QO6h is a standing receipt (one committed assertion + test); no re-run of prior QO6 bookings needed. ANY RED ⇒ hole booked honestly, spawn repair item, QO6/QO2 flagged.

**Honesty conventions:** verification writes to ext4 scratch via `--out` (RC-1 doctrine — never into `results/`); no RNG; determinism expected bit-exact on re-fire.
