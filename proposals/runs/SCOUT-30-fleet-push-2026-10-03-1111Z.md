# SCOUT-30 — fleet push sweep, 2026-10-03 11:11Z (03:11 AKDT)
Window: since SCOUT-29 (10:15Z commit 879c91b) — 1h. Method: users/SuperInstance/events + targeted fetches.

## State changes in window
- fleet-triage PR #10 (open, docs-only): edge-watch 2026-10-03E — **cites our SCOUT-29 canary-canon drift** as "4th canary-doctrine adoption + canon-rot hazard". CORROBORATE: our CI-1 doctrine consumed fleet-side within 12h. No action.
- fleet-triage PR #9 (open, docs-only): canon cross-ref L9/L10 provenance line, cite-only. No action.
- jev-quilt: 64th wipe (10:06Z, **1 noisy alarm q18 -0.060**) then 65th wipe (11:04Z, clean, 0 alarms). QC-JEV booking untouched; q18 flagged as transient — worth a glance only if a third consecutive alarm appears. WATCH, no item.
- quilt-research-canons scout 1017Z (bf4a425): "mutation-verified gate spectrum (5 gems, 5161-repo census)". See steals below.
- No new PRs on pong-quilt/micrograd-quilt/murmuration in window. [EMBASSY]: no new items; pong #49 and substrate-llm-client #1 / moth-runner #2 remain Casey day items (do not file).

## Classifications
- **CORROBORATE**: fleet-triage #10/#8 consuming our CI-1/SCOUT-29 doctrine; canons census methodology hardened again (vendor-stripped tree bytes — matches their earlier "size is a lie" fix we already adopted).
- **TOOL/STEAL (1)**: `crab-traps` 47b-self-test.mjs — two-reader witness lane with 8 negative controls + positive control + CLI end-to-end controls, **mutation-verified by the scout (1 hex flip → EXIT=1)**. This is the best-in-fleet executable-negative-control template. Directly upgrades our CI-1 canary: our canary pins canon text (L9/L10) but has no tamper-the-input negative controls beyond the single cx→cxr pin. Canons' structural note — "re-running the self-test rewrites the committed receipt → dirty tree" — is our D-2 class live elsewhere.
- **CORROBORATE (2)**: `fleet-bench` cross_validate.py — "verify Rust crates" title, zero Rust ever invoked (no subprocess/cargo/ctypes). Fresh instance of the RC-1b never-executed-branch / validator-is-a-decoration class. Science half is real (measured, volatile sinks) — a rare honest-bench-with-fake-validator split worth citing when RC-1b fires.
- **CONTRADICT**: none. QO2 stack, receipt doctrine, QG3+QG6, QG1c, W5a/W5b/W5c, CI-1 all unthreatened this window.

## Queue items spawned
- **CAN-1** (CPU ~40m, pre-reg first): upgrade tools/canary.py from single negative control to a crab-traps-style control ladder — (T1 tamper-expectation, T2 wrong-pin-tip, T3 tamper-input-bytes, POS positive) each asserted to flip the verdict fail-closed; port the "self-test must not dirty the tree" --check mode (already specced in RC-5 push-time layer; merge, don't duplicate). Gate: every control RED before any green; tree byte-identical after check-mode run.
- **RC-1b note (no new item)**: add fleet-bench cross_validate.py as 4th cited witness instance in RC-1b's evidence list at fire time.

## Rotation
(B) next: RC-6 (input-pin) or CAN-1. GPU idle this slice (scout slot). (C) this slice: CI-1 verdict-level repro.
