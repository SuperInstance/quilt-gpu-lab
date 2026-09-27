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
"""
from __future__ import annotations

import subprocess
import threading
import time
from typing import List, Optional, Tuple

NSMI = "/usr/lib/wsl/lib/nvidia-smi"
FREE_FLOOR_MIB = 1024   # abort if less than 1 GB free
TEMP_CEIL_C = 80        # abort above 80 C
POLL_S = 5.0


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


class Guard:
    """Watchdog around one child experiment process."""

    def __init__(self, timeout_s: float = 1800.0):
        self.timeout_s = timeout_s
        self.samples: List[Tuple[float, Optional[int], Optional[int]]] = []
        self.breach: Optional[str] = None
        self.timed_out = False
        self._stop = threading.Event()

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
            free, temp = sample()
            self.samples.append((time.time(), free, temp))
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
        }
