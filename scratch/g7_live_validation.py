"""g7_live_validation.py — prove G7 watt-receipt instrumentation end-to-end.

Runs a real torch GPU load under the upgraded guard (power.draw sampling on),
seals a g7-watt-receipt@1, and validates it with the fleet-seeds validator.
Also exercises the VOID path (receipt with zero power samples).

No performance claims are made — whole-window energy integral only
(INSTRUMENT-01 ramp law applies to latency measurements, not energy windows).
Seed 2718. Pre-registered in QUEUE.md G7 line.
"""
import json
import os
import subprocess
import sys

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, LAB)

import guard  # noqa: E402

PY = "/home/eileen/venvs/elephant-gpu/bin/python"

# The child load: real CUDA matmuls, sync each step, ~25 s so the 5 s poll
# accumulates >= 4 power samples. Deliberately NOT a perf benchmark.
CHILD = (
    "import torch, time\n"
    "assert torch.cuda.is_available()\n"
    "a = torch.randn(4096, 4096, device='cuda', dtype=torch.bfloat16)\n"
    "b = torch.randn(4096, 4096, device='cuda', dtype=torch.bfloat16)\n"
    "t0 = time.time()\n"
    "steps = 0\n"
    "while time.time() - t0 < 25.0:\n"
    "    for _ in range(10):\n"
    "        c = a @ b\n"
    "    torch.cuda.synchronize()\n"
    "    steps += 1\n"
    "print(f'child done: {steps} synced steps')\n"
)


def main():
    print("=== 1. live measured run ===")
    g = guard.Guard(
        timeout_s=300.0,
        task_id="G7-watt-receipt-instrumentation",
        agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
        seed="2718",
    )
    assert g.preflight(), f"preflight refused: {g.breach}"
    rc, out, err = g.run([PY, "-c", CHILD], cwd=LAB, env=dict(os.environ))
    print(f"child rc={rc} out={out.strip()!r}")
    if rc != 0:
        print(f"child stderr: {err[-800:]}")
        sys.exit(2)
    s = g.summary()
    print("guard summary:", json.dumps(s))
    path, receipt = g.emit_receipt()
    ok, msg = g.validate_receipt(path)
    print(f"receipt: {path}")
    print(json.dumps(receipt, indent=2))
    print(f"validator: schema_valid={ok}\n{msg}\n")

    print("=== 2. VOID path (no power samples -> sampling-failure VOID) ===")
    g2 = guard.Guard(task_id="G7-void-path-control", receipt_dir="results/g7/void-control")
    g2.power_samples = []  # simulate total instrument failure
    p2, r2 = g2.emit_receipt()
    ok2, msg2 = g2.validate_receipt(p2)
    print(f"void receipt verdict={r2['gate']['verdict']} schema_valid={ok2}")
    print(f"validator: {msg2}\n")

    print("=== 3. gate law: validator refuses the canonical no-energy receipt ===")
    val = os.path.join(os.path.dirname(LAB), "fleet-seeds", "scripts", "g7_validate.mjs")
    ex = os.path.join(os.path.dirname(LAB), "fleet-seeds", "scripts", "g7", "examples",
                      "void-missing-energy.json")
    if not os.path.exists(ex):
        ex = os.path.join(os.path.dirname(LAB), "fleet-seeds", "scripts", "g7",
                          "void-missing-energy.json")
    r3 = subprocess.run(["node", val, ex], capture_output=True, text=True)
    print(f"canonical refusal example: exit={r3.returncode} (1 expected = gate refuses)")

    all_green = ok and ok2 and r3.returncode == 1 and receipt["gate"]["verdict"] == "PASS"
    print(f"\nG7-LIVE-VALIDATION: {'ALL GREEN' if all_green else 'FAILED'}")
    sys.exit(0 if all_green else 3)


if __name__ == "__main__":
    main()
