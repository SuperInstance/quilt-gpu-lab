#!/usr/bin/env python3
"""D2-V1 — guarded outer runner for the 54 twin trainings.
G7: no receipt = VOID. Preflight refuses below 1 GB free VRAM
(retry-once-after-60s-then-NOT-RUN; prereg F1/F9, co-tenant 7B ollama seat aware).
"""
import os, subprocess, sys, json, time
from pathlib import Path

LAB = Path("/home/eileen/projects/quilt-gpu-lab")
sys.path.insert(0, str(LAB))
import guard  # noqa: E402

OUT = LAB / "results" / "d2_v1"
VENV = "/home/eileen/venvs/elephant-gpu/bin/python"
INNER = str(LAB / "results" / "d2_v1" / "scripts" / "d2_v1_twins.py")
NSMI = "/usr/lib/wsl/lib/nvidia-smi"


def cuda_pids():
    try:
        r = subprocess.run([NSMI, "--query-compute-apps=pid,process_name,used_memory",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().splitlines()
    except Exception as e:
        return [f"probe failed: {e}"]


def main() -> int:
    log = {"co_tenants_before": cuda_pids()}
    g = guard.Guard(timeout_s=3600.0, task_id="D2-V1-twins",
                    agent="quilt-gpu-lab lane D2-V1 (subagent)", seed="2718",
                    receipt_dir=str(OUT / "guard"))
    if not g.preflight():
        print(f"PREFLIGHT REFUSED: {g.breach} — retry once after 60s", flush=True)
        time.sleep(60)
        g.breach = None
        if not g.preflight():
            print(f"PREFLIGHT REFUSED AGAIN: {g.breach}", flush=True)
            g.emit_receipt(verdict="VOID", void_reason=f"preflight refused: {g.breach}")
            log["result"] = "NOT-RUN (preflight, retry failed)"
            (OUT / "d2_v1_twins_guard.log.json").write_text(json.dumps(log, indent=1))
            return 2
    print(f"PREFLIGHT OK free={g.samples[-1][1]}MiB temp={g.samples[-1][2]}C", flush=True)
    rc, out, err = g.run([VENV, INNER], cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-6000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-2000:], flush=True)
    print(f"GUARD: {json.dumps(g.summary())}", flush=True)
    verdict = "PASS" if rc == 0 and g.breach is None else None
    path, receipt = g.emit_receipt(verdict=verdict,
                                   void_reason=None if verdict else f"inner rc={rc} breach={g.breach}")
    print(f"RECEIPT {path} verdict={receipt['gate']['verdict']}", flush=True)
    ok, msg = g.validate_receipt(path)
    print(f"G7 VALIDATOR ok={ok} {msg[:300]}", flush=True)
    log.update({"co_tenants_after": cuda_pids(), "inner_rc": rc, "guard": g.summary(),
                "receipt_path": path, "receipt": receipt, "validator_ok": ok,
                "validator_msg": msg, "gpu_seconds": receipt["compute"]["gpu_seconds"],
                "watt_hours": receipt["energy"]["watt_hours"], "result": "RAN"})
    (OUT / "d2_v1_twins_guard.log.json").write_text(json.dumps(log, indent=1))
    return 0 if (ok and verdict == "PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
