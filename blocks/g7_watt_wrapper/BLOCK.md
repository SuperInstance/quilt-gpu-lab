# g7_watt_wrapper

## WHAT IT IS

The guard/watt-receipt pattern as an **importable context manager**: a
VRAM/thermal preflight gate, a power-sampled energy window across the
`with` body, and an ALWAYS-sealed `g7-watt-receipt@1` on exit — the G7
adoption law ("every GPU verdict ships a schema-valid receipt or is VOID;
no receipt → run VOID") in one `with` statement. Standalone port of the
lab's `guard.py` (RESULTS.md "G7 watt-receipt instrumentation — KEEP",
2026-10-01); the production probe shells out to `nvidia-smi` via
LIST-FORM subprocess only, and the self-test never touches it
(`FakePowerProbe` injected).

```python
with watt_window(task_id="my-lane", probe=NvidiaSmiProbe(),
                 receipt_dir="results/my-lane/guard") as g:
    ... GPU work ...          # g.summary() mid-window if needed
# exit ALWAYS seals:
#   clean + measured          -> verdict PASS
#   breach / body exception   -> verdict KILL (traceback booked; the
#                                exception re-raises AFTER sealing)
#   zero valid power samples  -> verdict VOID (fail-closed: sampling
#                                failure declared, never faked)
# preflight refusal           -> GuardRefusal raised; refusal receipt
#                                (KILL, refusal=true) already written
```

## WHY (the booked receipts)

- **G7 instrumentation KEEP** (RESULTS.md, 2026-10-01): guard.py now
  samples `power.draw` + `utilization.gpu` on the same 5 s poll; seals one
  `g7-watt-receipt@1` per run — `guard_summary.json` written first and
  sha256-bound as `state_digest`, fleet validator
  (`../fleet-seeds/scripts/g7_validate.mjs`) executed at seal time,
  receipt + validator output appended to `results/g7/ledger.jsonl`.
  Fail-closed by construction: zero valid power samples → VOID; unknown
  device → validator refuses → run VOID. Live proof: 25 s bf16 4096²
  matmul → 5 samples, mean 67.7 W × 21.493 s = 1455.1 J = 0.404 Wh =
  $0.000093 @ $0.23/kWh, validator exit 0, gate PASS; VOID-path control
  self-declared VOID.
- **E6 harness self-test KEEP** (2026-09-27): guard refuses low-VRAM
  (<1 GiB) and high-temp (>80 C) preflights, accepts healthy ones;
  receipt-integrity check detects a tampered digest ("receipt drift
  detected") — the `verify_integrity` here is that check.
- **Receipts in the wild** (every one validator exit 0): A1-PIE closure,
  A2-GA4444 (4×4), COMP0 (0.939 Wh / 60.7 gpu-s), COMP1 (11.76 Wh, 741.2
  gpu-s, max 78 C, min-free 1475 MiB), B1C/B1E/B1F (3.75 Wh),
  c1-playtest-pong (21.09 Wh), plus the COMP1 r1 VOID receipt
  (`g7-wr-comp1-federation2-1790897485` — guard breach free VRAM
  1018 < 1024 MiB, evidence preserved, VOID booked honestly): the
  wrapper's refusal path has teeth in production.

## INTERFACE

```python
watt_window(task_id="ungated", probe=None, receipt_dir="receipts",
            poll_s=0.1, timeout_s=1800.0, seed="2718")
    # probe=None -> NvidiaSmiProbe() (G7_NSMI override -> which -> WSL2 path)
    # yields the live G7Wrapper

G7Wrapper(probe, task_id=..., receipt_dir=..., poll_s=...,
          vram_floor_mib=1024, temp_ceil_c=80, timeout_s=...)
    .preflight() -> bool          # False AND a refusal receipt (KILL)
    .preflight_or_exit()          # CLI form: sys.exit(2) on refusal
    .begin_window() / .end_window()
    .run_window(fn, *a, **kw)     # callable form; KILL+re-raise on exception
    .emit_receipt(verdict=None)   # default_verdict: PASS/KILL/VOID
    .summary() -> dict            # samples, min-free, max-temp, breach, g7
G7Wrapper.verify_integrity(path) -> (ok, msg)   # receipt + summary drift
FakePowerProbe(samples|watts=, free_vram_mib=, temp_c=, util_pct=)
GuardRefusal(breach, receipt_path)
```

Receipt contract: schema `g7-watt-receipt@1`; single top-level `verdict`
(PASS | KILL | VOID); flat `energy_j / energy_wh / window_s` fields with
`wh == j/3600` exact; `energy.source` measured/unmeasured (an unmeasured
0 J is explicitly NOT an energy claim); `determinism.state_digest` =
sha256 of the sealed `guard_summary.json`; `integrity.receipt_sha256`
binds the receipt to itself; append-only `ledger.jsonl`; optional fleet
validator via `G7_VALIDATOR` (list-form `node` call; fail-closed when
unset, booked honestly in the ledger). Energy = mean_power_W ×
wall_seconds, idle floor NOT subtracted (the receipt reports the whole
window the job held the GPU). `_builtin_validate` refuses a PASS with
zero power samples — that shape is VOID, by law.

## PROPERTIES

- Fail loud: breach/exception → KILL receipt THEN the exception
  re-raises; preflight refusal → `GuardRefusal` with receipt path; a
  window left open / double-closed raises `G7Error`. Never a silent
  fail, never a silent fallback.
- Fail closed: unmeasurable energy is VOID, never a faked 0 J PASS.
- Receipts are tamper-evident both ways (fields and the bound summary
  artifact); the ledger is append-only.
- stdlib only; subprocess appears solely as LIST-FORM calls
  (`nvidia-smi` probe, optional `node` validator) — never `shell=True`;
  no environment or secret ever enters a receipt.

## COMPOSITION

- **Receipts everything**: the spine's `[everything]--receipted-to-->
  RESULTS.md` edge runs through this block — `format_first_gate`'s
  `GateReceipt.to_dict()`, lane stats, and verdicts fold into the
  receipt's task payload (the r4/r5 pattern: pinch states and token
  ledgers must survive into the wrapped receipt untruncated).
- CPU lanes do NOT need it (EST-FREEZE / RING-CX-2 booked `0 Wh, no
  receipt required`) — the wrapper is the GPU-lane seal.

## SELF-TEST

From the lab root, CPU-only, ~1.5s, receipts in a tempdir that is
removed:

```
python3 blocks/g7_watt_wrapper/block.py
```

(1) healthy `with` window → PASS receipt, Wh == J/3600 and matches
65 W × window within 2%, ≥3 samples, mid-window summary readable;
(2) low-VRAM preflight → `GuardRefusal` with breach text, refusal
receipt KILL/refusal=true/unmeasured, body never ran; (3) exploding body
→ exception re-raised AND KILL receipt with `ValueError: boom` booked,
file still valid JSON; (4) dead probe (all-None samples) → VOID
fail-closed with the derivation note, schema-valid, and
`_builtin_validate` rejects the same receipt relabeled PASS; (5)
`run_window` callable API still PASSes and the ledger appends exactly one
line; (6) tampered `energy_j` → `verify_integrity` fails, clean receipt
verifies. Final stdout line is exactly one JSON object with one top-level
`"verdict"`; exit 0 iff PASS.
