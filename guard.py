"""guard.py — the VRAM/thermal watchdog.

Every experiment runs under this. It polls nvidia-smi (WSL2 path) on a
background thread and terminates the experiment if the GPU is in
danger. This laptop has crash-looped before; the guard exists so it
never happens from this lab.

Policy:
  - preflight: refuse to start unless free VRAM >= FREE_FLOOR_MIB and
    temp <= TEMP_CEIL_C.
  - in-flight: sample every POLL_S; abort on free VRAM < FREE_FLOOR_MIB
    or temp > TEMP_CEIL_C.
  - hard wall-clock timeout (default 30 min) regardless of GPU state.
  - G7 (2026-10-01): same poll thread also samples power.draw and
    utilization.gpu; when the run names a task_id the guard seals a
    g7-watt-receipt@1 (fleet-seeds docs/G7-WATT-RECEIPTS.md) whose
    state_digest binds the guard_summary artifact. Adoption law:
    "no receipt → run VOID" — a verdict shipped without a schema-valid
    receipt is VOID regardless of result. Validator:
    ../fleet-seeds/scripts/g7_validate.mjs (selftest 16/16).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import time
from typing import List, Optional, Tuple

NSMI = "/usr/lib/wsl/lib/nvidia-smi"
FREE_FLOOR_MIB = 1024   # abort if less than 1 GB free
TEMP_CEIL_C = 80        # abort above 80 C
POLL_S = 5.0

# G7 watt-receipt constants (declared economics, not vibes).
GATE_RULE = "no receipt → run VOID"
GRID_RATE_USD_KWH = 0.23
GRID_RATE_SOURCE = ("host marginal grid rate $0.23/kWh (Alaska residential "
                    "average, quoted 2026-10-01); gifted compute priced, not billed")
DEFAULT_AGENT = "quilt-gpu-lab keeper (Lucineer, main Super Z)"
DEFAULT_SEED = "2718"


def sample() -> Tuple[Optional[int], Optional[int]]:
    """Return (free_mib, temp_c) or (None, None) if nvidia-smi fails."""
    try:
        out = subprocess.run(
            [NSMI, "--query-gpu=memory.free,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()[0]
        free_s, temp_s = [p.strip() for p in out.split(",")]
        return int(free_s), int(temp_s)
    except Exception:
        return None, None


def sample_power() -> Tuple[Optional[float], Optional[float]]:
    """Return (power_w, util_pct) or (None, None).

    Defensive parse: some driver builds emit "[N/A]" or append units
    despite nounits. Never raise — a failed power read is sampling data
    loss, not a guard breach.
    """
    try:
        out = subprocess.run(
            [NSMI, "--query-gpu=power.draw,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()[0]
        p_s, u_s = [p.strip() for p in out.split(",")]

        def num(s: str) -> Optional[float]:
            s = s.replace("[N/A]", "").replace("N/A", "").strip()
            m = re.match(r"^-?\d+(?:\.\d+)?", s)
            return float(m.group(0)) if m else None

        return num(p_s), num(u_s)
    except Exception:
        return None, None


def sample_full() -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float]]:
    """(free_mib, temp_c, power_w, util_pct).

    free/temp still flow through module-level sample() so harness
    selftests that monkey-patch guard.sample keep their semantics.
    """
    free, temp = sample()
    power, util = sample_power()
    return free, temp, power, util


class Guard:
    """Watchdog around one child experiment process."""

    def __init__(self, timeout_s: float = 1800.0, *, task_id: str = "ungated",
                 agent: str = DEFAULT_AGENT, seed: str = DEFAULT_SEED,
                 receipt_dir: str = "results/g7"):
        self.timeout_s = timeout_s
        self.task_id = task_id
        self.agent = agent
        self.seed = seed
        self.receipt_dir = receipt_dir
        self.samples: List[Tuple[float, Optional[int], Optional[int]]] = []
        self.power_samples: List[Tuple[float, Optional[float], Optional[float]]] = []
        self.breach: Optional[str] = None
        self.timed_out = False
        self._stop = threading.Event()
        self._t_first: Optional[float] = None
        self._t_last: Optional[float] = None
        self._device: Optional[dict] = None
        self._receipt: Optional[dict] = None
        self._receipt_path: Optional[str] = None

    # -- lifecycle ---------------------------------------------------------
    def preflight(self) -> bool:
        free, temp = sample()
        self.samples.append((time.time(), free, temp))
        if free is None:
            self.breach = "preflight: nvidia-smi unavailable"
            return False
        if free < FREE_FLOOR_MIB:
            self.breach = f"preflight: free VRAM {free} MiB < {FREE_FLOOR_MIB}"
            return False
        if temp > TEMP_CEIL_C:
            self.breach = f"preflight: temp {temp}C > {TEMP_CEIL_C}C"
            return False
        return True

    def _watch(self, proc: subprocess.Popen) -> None:
        deadline = time.time() + self.timeout_s
        while not self._stop.wait(POLL_S):
            now = time.time()
            free, temp, power, util = sample_full()
            self.samples.append((now, free, temp))
            self.power_samples.append((now, power, util))
            if self._t_first is None:
                self._t_first = now
            self._t_last = now
            if free is not None and free < FREE_FLOOR_MIB:
                self.breach = f"free VRAM {free} MiB < {FREE_FLOOR_MIB}"
            if temp is not None and temp > TEMP_CEIL_C:
                self.breach = f"temp {temp}C > {TEMP_CEIL_C}C"
            if self.breach:
                self._terminate(proc)
                return
            if time.time() > deadline:
                self.timed_out = True
                self.breach = f"wall-clock timeout {int(self.timeout_s)}s"
                self._terminate(proc)
                return

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def run(self, cmd: List[str], cwd: str, env: dict
            ) -> Tuple[int, str, str]:
        """Run cmd under watch. Returns (returncode, stdout, stderr)."""
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        watcher = threading.Thread(target=self._watch, args=(proc,), daemon=True)
        watcher.start()
        out, err = proc.communicate()
        self._stop.set()
        watcher.join(timeout=2)
        return proc.returncode, out, err

    # -- G7 energy integration ----------------------------------------------
    def _energy(self) -> dict:
        """Integrate the watch window: mean power x wall seconds, plus
        utilization-weighted GPU-active seconds. Idle floor NOT subtracted
        (receipt reports the whole window the job held the GPU)."""
        ps = [p for _, p, _ in self.power_samples if p is not None]
        us = [u for _, _, u in self.power_samples if u is not None]
        wall = 0.0
        if self._t_first is not None and self._t_last is not None:
            wall = max(0.0, self._t_last - self._t_first)
        mean_p = (sum(ps) / len(ps)) if ps else None
        joules_raw = (mean_p * wall) if (mean_p is not None and wall > 0) else 0.0
        joules = round(joules_raw, 4)
        # utilization-weighted GPU-active seconds (interval-weighted midpoint)
        gpu_s = 0.0
        used_util = False
        for (t0, _, u0), (t1, _, _) in zip(self.power_samples, self.power_samples[1:]):
            if u0 is not None:
                used_util = True
                gpu_s += max(0.0, t1 - t0) * (u0 / 100.0)
        if not used_util:
            gpu_s = wall  # declared fallback: wall seconds (sampling_method says so)
        return {
            "wall_seconds": round(wall, 3),
            "power_samples": len(ps),
            "mean_power_w": round(mean_p, 2) if mean_p is not None else None,
            "joules": joules,
            "watt_hours": joules / 3600.0,  # derived from rounded joules: exact 2% tolerance
            "gpu_seconds": round(gpu_s, 3),
            "util_samples": len(us),
        }

    def _device_info(self) -> dict:
        if self._device is None:
            try:
                out = subprocess.run(
                    [NSMI, "--query-gpu=name,memory.total,driver_version",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip().splitlines()[0]
                name, mem, drv = [p.strip() for p in out.split(",")]
                self._device = {
                    "model": name,
                    "vram_gb": round(int(mem) / 1024.0, 1),
                    "driver": f"{drv} / WSL2 (/usr/lib/wsl/lib/nvidia-smi)",
                }
            except Exception:
                # fail-closed: validator refuses vram_gb <= 0 -> gate refuses -> run VOID
                self._device = {"model": "unknown", "vram_gb": 0.0, "driver": "unknown"}
        return self._device

    def emit_receipt(self, verdict: Optional[str] = None,
                     void_reason: Optional[str] = None) -> Tuple[Optional[str], Optional[dict]]:
        """Seal guard_summary.json (the digest-bound artifact) + one
        g7-watt-receipt@1. Returns (receipt_path, receipt dict).

        verdict: None = derive (PASS iff no breach AND >=1 valid power
        sample; VOID otherwise). Explicit verdicts are honored for lanes
        that declare their own run void.
        """
        e = self._energy()
        measured = e["power_samples"] > 0
        if verdict is None:
            verdict = "PASS" if (self.breach is None and measured) else "VOID"

        os.makedirs(self.receipt_dir, exist_ok=True)
        summary = self.summary()  # legacy fields + g7 energy block
        summary_path = os.path.join(self.receipt_dir, "guard_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, sort_keys=True)
        with open(summary_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()

        fallback_note = ("no valid power.draw samples in window (instrument N/A or "
                         "nvidia-smi unavailable); 0 J booked is NOT an energy claim — "
                         "run VOIDed by sampling failure")
        sampling_method = (
            f"nvidia-smi --query-gpu=power.draw,utilization.gpu on the guard's poll "
            f"thread every {POLL_S:.0f}s across the run window under guard; integral "
            "= mean_power_W x wall_seconds; idle floor NOT subtracted — receipt "
            "reports the whole window the job held the GPU (WSL2 NVML)")
        if not measured:
            sampling_method += "; gpu_seconds fell back to wall seconds (no utilization samples)"

        receipt = {
            "schema": "g7-watt-receipt@1",
            "receipt_id": "g7-wr-{}-{}".format(
                re.sub(r"[^a-zA-Z0-9]+", "-", self.task_id).strip("-").lower()[:24] or "task",
                int(time.time())),
            "task_id": self.task_id,
            "agent": self.agent,
            "device": self._device_info(),
            "energy": {
                "joules": e["joules"],
                "watt_hours": e["watt_hours"],
                "source": "measured" if measured else "tdp_derived",
                "sampling_method": sampling_method,
                "instrument": "nvidia-smi (NVML power.draw counters) on the WSL2 host"
                             if measured else None,
                "derivation": None if measured else fallback_note,
            },
            "compute": {"gpu_seconds": e["gpu_seconds"]},
            "cost": {
                "currency": "USD",
                "amount": round(e["watt_hours"] / 1000.0 * GRID_RATE_USD_KWH, 6),
                "rate_source": GRID_RATE_SOURCE,
            },
            "determinism": {"seed": self.seed, "state_digest": digest},
            "gate": {"rule": GATE_RULE, "verdict": verdict},
        }
        if void_reason:
            receipt["void_reason"] = void_reason

        path = os.path.join(self.receipt_dir, f"{receipt['receipt_id']}.json")
        with open(path, "w") as f:
            json.dump(receipt, f, indent=2)
        self._receipt = receipt
        self._receipt_path = path

        ok, msg = self.validate_receipt()
        with open(os.path.join(self.receipt_dir, "ledger.jsonl"), "a") as f:
            f.write(json.dumps({"receipt_id": receipt["receipt_id"], "path": path,
                                "schema_valid": ok, "gate_verdict": verdict,
                                "validator": msg, "sealed_at": time.time()}) + "\n")
        return path, receipt

    def validate_receipt(self, path: Optional[str] = None) -> Tuple[bool, str]:
        """Run the fleet-seeds g7_validate.mjs against a receipt file.
        Fail-closed: missing validator or node failure returns False."""
        path = path or self._receipt_path
        if not path:
            return False, "no receipt emitted"
        here = os.path.dirname(os.path.abspath(__file__))
        cand = (os.environ.get("G7_VALIDATOR")
                or os.path.join(os.path.dirname(here), "fleet-seeds",
                                "scripts", "g7_validate.mjs"))
        if not os.path.exists(cand):
            return False, f"validator not found at {cand} (set G7_VALIDATOR)"
        try:
            r = subprocess.run(["node", cand, path],
                               capture_output=True, text=True, timeout=30)
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        except Exception as exc:
            return False, f"validator failed to run: {exc}"

    # -- reporting ----------------------------------------------------------
    def summary(self) -> dict:
        frees = [f for _, f, _ in self.samples if f is not None]
        temps = [t for _, _, t in self.samples if t is not None]
        return {
            "samples": len(self.samples),
            "min_free_vram_mib": min(frees) if frees else None,
            "max_temp_c": max(temps) if temps else None,
            "breach": self.breach,
            "timed_out": self.timed_out,
            "g7": self._energy(),
            "task_id": self.task_id,
        }
