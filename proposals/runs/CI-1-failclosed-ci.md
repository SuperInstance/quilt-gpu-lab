# CI-1 — fail-closed pytest workflow + fleet canary (quilt-gpu-lab)

Spawned by SCOUT-25 (cite quilt-research-canons SCOUT-2235Z failopen census: 117 repos,
81 test-runner failopen — `|| true` laundering; quilt-gpu-lab is UNGATED, no workflows
at all — 3rd witness of the guard-gap class). Priority raised SCOUT-26. CPU ~30m.
Spec: proposals/runs/SCOUT-25-fleet-push-2026-10-03-0010Z.md.

## Pre-registered design (frozen before fire)

1. **Workflow** `.github/workflows/tests.yml`:
   - `fetch-depth: 0` (pong-quilt #84 shallow-checkout receipt-completeness lesson).
   - `python3 -m pytest tests/ -q` — NO `|| true`, no `continue-on-error`, exit propagates.
   - Python 3.11 on ubuntu-latest; deps: none for tests (pytest only). torch is not
     required by the three existing test modules (receipts/seal_guard/verdict_gate).
2. **Fleet canary** per fleet-kit fleetlint L9/L10 convention, template verbatim-adapted
   (SuperInstance/fleet-kit fleetlint/templates/python-package, MIT):
   - `tools/canary.py`: `fnv1a64`, `CANARY_HEX='café Δ 日本語'`,
     `FLEET_CANARY=0x024A555471370B18D` (integer compare — never text; 17-digit class),
     `ACCENTED_TRAP=0xFEE91CF40962B966` (unaccented twin, never a canary),
     `alphabet_canary(opcodes)` = FNV-1a64 over sorted-joined '|'.
   - Our canon = qcell gate vocabulary from tools/qcell_sim.py header:
     {h, x, rx, rz, cx, crx, swap} → pin **0xCA289D4829D9A834** (computed 2026-10-03).
   - `tests/test_canary.py`: byte canary, accented-trap inequality, alphabet pin,
     NEGATIVE CONTROL (rename cx→cxr ⇒ pin moves; rename back ⇒ pin restored).
     The negative control is what makes the check fail-capable (L9 canary-inert).
3. **Gates:**
   - G1: local `pytest tests/ -q` green (existing 3 modules + new canary tests) before push.
   - G2: canary pin self-consistency — computing alphabet_canary over the canon returns
     the pinned integer, and the negative-control rename returns a DIFFERENT integer
     (fail-capable, not inert).
   - G3: workflow file contains no `|| true` / `continue-on-error` (grep-zero).
   - G4 (post-push): Actions run on push goes green (observed if runner available; else
     booked as PUSHED-UNVERIFIED, honestly flagged).
4. **Scope guard:** no scheduler/config touched beyond the new workflow file; no existing
   test modified; docs-only otherwise. No verdict bookkeeping depends on this landing.

## Result

(filled after fire)
