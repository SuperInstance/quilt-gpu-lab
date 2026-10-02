#!/usr/bin/env python3
"""g7_watt_wrapper — the guard/watt-receipt pattern as an importable context
manager. Standalone stdlib (+numpy unused here), GPU-optional.

Ported shape of the lab's guard.py (VRAM/thermal watchdog + G7 watt
receipts; RESULTS.md G7 watt-receipt instrumentation KEEP, 2026-10-01):

  - PowerProbe protocol: .sample() -> {"watts", "free_vram_mib", "temp_c",
    "util_pct"}. The real implementation shells out to nvidia-smi via
    LIST-FORM subprocess, never shell=True; FakePowerProbe covers tests.
  - preflight gate: refuses LOUD when free VRAM < floor or temp > cap —
    writes a refusal receipt (verdict KILL) AND returns False / raises
    GuardRefusal. Never a silent fail.
  - watt_window(...) context manager (the importable seal): preflight on
    enter, power sampling on an interval thread across the body, energy
    integrated as mean_power_W x wall_seconds (idle floor NOT subtracted —
    the receipt reports the whole window the job held the GPU), and ALWAYS
    a receipt on exit — PASS measured clean, KILL on breach/exception
    (traceback booked, then the exception re-raises), or VOID fail-closed
    when zero valid power samples exist (G7 law: "zero valid power samples
    -> verdict VOID — sampling failure declared, never faked").
  - run_window(fn) — the callable form of the same window.
  - Receipt schema "g7-watt-receipt@1": guard_summary.json written FIRST
    and sha256-bound as determinism.state_digest; integrity.receipt_sha256
    binds the receipt to itself; append-only ledger.jsonl per receipt dir;
    optional fleet validator via G7_VALIDATOR (list-form node call).
  - Integrity (E6 pattern, RESULTS.md 2026-09-27: "receipt drift
    detected"): verify_integrity() detects tampering with either the
    receipt or the summary artifact (fail closed).

Live proof at source (guard.py G7 entry): 25 s bf16 4096^2 matmul under
guard -> 5 power samples, mean 67.7 W x 21.493 s = 1455.1 J = 0.404 Wh =
$0.000093 @ $0.23/kWh; validator exit 0, gate PASS; VOID-path control
self-declares VOID. Adoption law live from that run forward: every GPU
verdict ships a schema-valid receipt or is VOID ("no receipt -> run
VOID").

House contracts: seed "2718" default; final stdout line of the self-test
is exactly one JSON object with exactly one top-level "verdict"; exit 0
iff PASS; list-form subprocess only, never shell=True; never print/copy
secrets (no environment is ever dumped into a receipt).

Self-test (__main__, CPU-only, FakePowerProbe injected — nvidia-smi is
never touched; receipts written to a tempdir that is removed): healthy
window -> PASS receipt with expected Wh; breached preflight -> GuardRefusal
+ refusal receipt; exploding body -> KILL receipt with traceback, exception
re-raises, file still valid JSON; dead probe -> VOID fail-closed; tampered
receipt -> verify_integrity detects it; ledger grows append-only.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SCHEMA = "g7-watt-receipt@1"
FREE_FLOOR_MIB = 1024          # refuse below 1 GB free VRAM
TEMP_CEIL_C = 80               # refuse above 80 C
POLL_S = 0.1                   # power-sampling interval inside a window
GATE_RULE = "no receipt → run VOID"
GRID_RATE_USD_KWH = 0.23       # host marginal grid rate, quoted 2026-10-01
DEFAULT_SEED = "2718"
DEFAULT_AGENT = "quilt-gpu-lab g7_watt_wrapper (standalone port of guard.py)"
WSL2_NSMI = "/usr/lib/wsl/lib/nvidia-smi"
# PASS  measured clean; KILL  gate breach / refusal / exception / timeout;
# VOID  fail-closed unmeasured (zero valid power samples — declared, never faked)
VERDICTS = ("PASS", "KILL", "VOID")


class G7Error(Exception):
    """Booked exception base — fail loud, never silent."""


class GuardRefusal(G7Error):
    """Preflight refused the run (breach + receipt path carried)."""

    def __init__(self, breach: str, receipt_path: str):
        super().__init__(f"preflight refused: {breach} (receipt: {receipt_path})")
        self.breach = breach
        self.receipt_path = receipt_path


# --------------------------------------------------------------------------
# Probes
# --------------------------------------------------------------------------
class PowerProbe:
    """Protocol. .sample() returns a dict:

        {"watts": float|None, "free_vram_mib": int|None, "temp_c": int|None,
         "util_pct": float|None}

    A failed read yields None values — sampling loss, never a raised error.
    """

    def sample(self) -> Dict[str, Optional[float]]:  # pragma: no cover - interface
        raise NotImplementedError


class NvidiaSmiProbe(PowerProbe):
    """Production probe: ONE list-form nvidia-smi query per sample.

    NEVER shell=True. Constructed only when the caller explicitly wants
    real GPU probing (the self-test never constructs it). Path resolution:
    G7_NSMI env override -> `which nvidia-smi` -> the WSL2 path guard.py
    uses (power.draw + utilization.gpu on the same poll, per the G7 entry).
    """

    QUERY = ["--query-gpu=memory.free,temperature.gpu,power.draw,utilization.gpu",
             "--format=csv,noheader,nounits"]

    def __init__(self, nsmi_path: Optional[str] = None, timeout_s: float = 10.0):
        if nsmi_path is None:
            nsmi_path = (os.environ.get("G7_NSMI")
                         or shutil.which("nvidia-smi")
                         or WSL2_NSMI)
        self.nsmi = nsmi_path
        self.timeout_s = timeout_s

    @staticmethod
    def _num(s: str) -> Optional[float]:
        # defensive parse: some driver builds emit "[N/A]" or append units
        s = s.replace("[N/A]", "").replace("N/A", "").strip()
        m = re.match(r"^-?\d+(?:\.\d+)?", s)
        return float(m.group(0)) if m else None

    def sample(self) -> Dict[str, Optional[float]]:
        blank = {"watts": None, "free_vram_mib": None, "temp_c": None, "util_pct": None}
        try:
            r = subprocess.run([self.nsmi, *self.QUERY],
                               capture_output=True, text=True,
                               timeout=self.timeout_s)  # list-form; never shell=True
            if r.returncode != 0:
                return blank
            parts = [p.strip() for p in r.stdout.strip().splitlines()[0].split(",")]
            if len(parts) != 4:
                return blank
            free_s, temp_s, watts_s, util_s = parts
            free_n, temp_n = self._num(free_s), self._num(temp_s)
            return {"watts": self._num(watts_s),
                    "free_vram_mib": int(free_n) if free_n is not None else None,
                    "temp_c": int(temp_n) if temp_n is not None else None,
                    "util_pct": self._num(util_s)}
        except Exception:
            return blank


class FakePowerProbe(PowerProbe):
    """Test probe: one constant sample, or a scripted list consumed FIFO with
    the last sample repeating. Injected in self-tests and CPU lanes."""

    def __init__(self, samples: Optional[List[dict]] = None, *,
                 watts: float = 65.0, free_vram_mib: int = 6000,
                 temp_c: int = 55, util_pct: float = 100.0):
        if samples is None:
            samples = [{"watts": watts, "free_vram_mib": free_vram_mib,
                        "temp_c": temp_c, "util_pct": util_pct}]
        self._samples = [dict(s) for s in samples]
        self._i = 0

    def sample(self) -> Dict[str, Optional[float]]:
        s = self._samples[min(self._i, len(self._samples) - 1)]
        self._i += 1
        return dict(s)


# --------------------------------------------------------------------------
# Wrapper
# --------------------------------------------------------------------------
class G7Wrapper:
    """Preflight gate + timed energy window + always-on receipt."""

    def __init__(self, probe: PowerProbe, *, task_id: str = "ungated",
                 agent: str = DEFAULT_AGENT, seed: str = DEFAULT_SEED,
                 receipt_dir: str = "receipts", timeout_s: float = 1800.0,
                 poll_s: float = POLL_S, vram_floor_mib: int = FREE_FLOOR_MIB,
                 temp_ceil_c: int = TEMP_CEIL_C):
        self.probe = probe
        self.task_id = task_id
        self.agent = agent
        self.seed = seed
        self.receipt_dir = Path(receipt_dir)
        self.timeout_s = timeout_s
        self.poll_s = poll_s
        self.vram_floor_mib = vram_floor_mib
        self.temp_ceil_c = temp_ceil_c
        self.samples: List[Tuple[float, Optional[int], Optional[int]]] = []
        self.power_samples: List[Tuple[float, Optional[float], Optional[float]]] = []
        self.windows: List[dict] = []
        self.breach: Optional[str] = None
        self.traceback: Optional[str] = None
        self._receipt_path: Optional[str] = None
        self._win_start = 0
        self._win_t0 = 0.0
        self._stop: Optional[threading.Event] = None
        self._watcher: Optional[threading.Thread] = None

    # -- recording ------------------------------------------------------------
    def _record(self, s: dict, t: Optional[float] = None) -> None:
        t = time.time() if t is None else t
        self.samples.append((t, s.get("free_vram_mib"), s.get("temp_c")))
        self.power_samples.append((t, s.get("watts"), s.get("util_pct")))

    def _check_breach(self, s: dict) -> None:
        free, temp = s.get("free_vram_mib"), s.get("temp_c")
        if free is not None and free < self.vram_floor_mib:
            self.breach = f"free VRAM {free} MiB < {self.vram_floor_mib}"
        if temp is not None and temp > self.temp_ceil_c:
            self.breach = f"temp {temp}C > {self.temp_ceil_c}C"

    # -- gate -------------------------------------------------------------------
    def preflight(self) -> bool:
        """Refuse loud on breach: return False AND write the refusal receipt."""
        s = self.probe.sample()
        self._record(s)
        free, temp = s.get("free_vram_mib"), s.get("temp_c")
        if free is None or temp is None:
            self.breach = "preflight: probe unavailable"
        elif free < self.vram_floor_mib:
            self.breach = f"preflight: free VRAM {free} MiB < {self.vram_floor_mib}"
        elif temp > self.temp_ceil_c:
            self.breach = f"preflight: temp {temp}C > {self.temp_ceil_c}C"
        if self.breach:
            self.emit_receipt(verdict="KILL", refusal=True)
            return False
        return True

    def preflight_or_exit(self) -> None:
        """CLI convenience: nonzero exit (2) when the gate refuses."""
        if not self.preflight():
            sys.exit(2)

    # -- window -------------------------------------------------------------------
    def _poll(self, stop: threading.Event) -> None:
        while not stop.wait(self.poll_s):
            s = self.probe.sample()
            self._record(s)
            self._check_breach(s)
            if self.breach:
                return

    def begin_window(self) -> None:
        """Start one energy window: immediate sample + interval thread."""
        if self._watcher is not None:
            raise G7Error("a window is already open (one window per wrapper, "
                          "or use run_window/watt_window)")
        self._win_start = len(self.power_samples)
        self._win_t0 = time.time()
        self._record(self.probe.sample())  # immediate sample: short windows covered
        self._stop = threading.Event()
        self._watcher = threading.Thread(target=self._poll, args=(self._stop,),
                                         daemon=True)
        self._watcher.start()

    def end_window(self) -> dict:
        """Stop the sampler and close the window (mean power x wall)."""
        if self._watcher is None:
            raise G7Error("no open window to end")
        assert self._stop is not None
        self._stop.set()
        self._watcher.join(timeout=2)
        self._watcher = None
        self._stop = None
        self._close_window(self._win_start, self._win_t0)
        return self.windows[-1]

    def _close_window(self, w_start: int, w_t0: float) -> None:
        """Snapshot one energy window: mean power x wall (gap-free), like
        guard.py's _close_window."""
        sl = self.power_samples[w_start:]
        if not sl:
            self.windows.append({"power_samples": 0, "joules": 0.0,
                                 "wall_seconds": 0.0, "gpu_seconds": 0.0})
            return
        wall = max(0.0, sl[-1][0] - min(sl[0][0], w_t0))
        ps = [p for _, p, _ in sl if p is not None]
        mean_p = (sum(ps) / len(ps)) if ps else 0.0
        gpu_s = 0.0
        for (t0, _, u0), (t1, _, _) in zip(sl, sl[1:]):
            if u0 is not None:
                gpu_s += max(0.0, t1 - t0) * (u0 / 100.0)
        self.windows.append({"wall_seconds": round(wall, 3),
                             "power_samples": len(ps),
                             "mean_power_w": round(mean_p, 2),
                             "joules": round(mean_p * wall, 4),
                             "gpu_seconds": round(gpu_s, 3)})

    def default_verdict(self) -> str:
        """PASS measured clean | VOID fail-closed unmeasured | KILL breach."""
        e = self._energy()
        measured = e["power_samples"] > 0 and e["wall_seconds"] > 0
        if self.breach is not None or self.traceback is not None:
            return "KILL"
        return "PASS" if measured else "VOID"

    def run_window(self, fn: Callable, *args, **kwargs):
        """Time fn, sample power on an interval, ALWAYS write the receipt.

        Exception -> verdict KILL + traceback booked, receipt written, then
        the exception re-raises (fail loud: the death is receipted AND seen).
        """
        self.begin_window()
        try:
            result = fn(*args, **kwargs)
        except BaseException:
            self.traceback = traceback.format_exc()
            self.end_window()
            self.emit_receipt(verdict="KILL")
            raise
        self.end_window()
        if self.timeout_s and (time.time() - self._win_t0) > self.timeout_s:
            self.breach = f"wall-clock timeout {int(self.timeout_s)}s exceeded"
        self.emit_receipt(verdict=self.default_verdict())
        return result

    # -- energy -------------------------------------------------------------------
    def _energy(self) -> dict:
        """Mean power x wall over all windows (idle floor NOT subtracted —
        the receipt reports the whole window the job held the GPU)."""
        win_wall = sum(w["wall_seconds"] for w in self.windows)
        win_j = sum(w["joules"] for w in self.windows)
        win_ps = sum(w["power_samples"] for w in self.windows)
        gpu_s = sum(w["gpu_seconds"] for w in self.windows)
        mean_p = (win_j / win_wall) if win_wall > 0 else None
        joules = round(win_j, 4)
        return {"wall_seconds": round(win_wall, 3),
                "power_samples": win_ps,
                "mean_power_w": round(mean_p, 2) if mean_p is not None else None,
                "joules": joules,
                "watt_hours": joules / 3600.0,
                "gpu_seconds": round(gpu_s, 3),
                "windows": len(self.windows)}

    def summary(self) -> dict:
        frees = [f for _, f, _ in self.samples if f is not None]
        temps = [t for _, t, _ in self.samples if t is not None]
        return {"samples": len(self.samples),
                "min_free_vram_mib": min(frees) if frees else None,
                "max_temp_c": max(temps) if temps else None,
                "breach": self.breach,
                "g7": self._energy(),
                "task_id": self.task_id}

    # -- receipt -------------------------------------------------------------------
    @staticmethod
    def _digest_of(obj: dict) -> str:
        payload = {k: v for k, v in obj.items() if k != "integrity"}
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def emit_receipt(self, verdict: Optional[str] = None,
                     refusal: bool = False) -> Tuple[str, dict]:
        """Seal guard_summary.json (digest-bound artifact) + one
        g7-watt-receipt@1. Returns (path, receipt)."""
        e = self._energy()
        measured = e["power_samples"] > 0 and e["wall_seconds"] > 0
        if verdict is None:
            verdict = self.default_verdict()
        if verdict not in VERDICTS:
            raise G7Error(f"unbooked receipt verdict {verdict!r}; use {VERDICTS}")

        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        summary = self.summary()
        summary_path = self.receipt_dir / "guard_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        digest = hashlib.sha256(summary_path.read_bytes()).hexdigest()

        sampling_method = (
            "probe.sample() on an interval thread across the run window; integral "
            "= mean_power_W x wall_seconds; idle floor NOT subtracted — receipt "
            "reports the whole window the job held the GPU")
        void_note = ("no valid power samples in window; 0 J booked is NOT an "
                     "energy claim — sampling failure declared, run VOID "
                     "(fail-closed, never faked)")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.task_id).strip("-").lower()[:24] or "task"
        receipt = {
            "schema": SCHEMA,
            "receipt_id": f"g7-wr-{slug}-{int(time.time())}",
            "task_id": self.task_id,
            "agent": self.agent,
            "seed": self.seed,
            "verdict": verdict,                     # single top-level verdict
            "refusal": refusal,
            "breach": self.breach,
            "traceback": self.traceback,
            "window_s": e["wall_seconds"],
            "energy_j": e["joules"],
            "energy_wh": e["watt_hours"],
            "mean_power_w": e["mean_power_w"],
            "power_samples": e["power_samples"],
            "gpu_seconds": e["gpu_seconds"],
            "energy": {
                "joules": e["joules"],
                "watt_hours": e["watt_hours"],
                "source": "measured" if measured else "unmeasured",
                "sampling_method": sampling_method,
                "derivation": None if measured else void_note,
            },
            "compute": {"gpu_seconds": e["gpu_seconds"]},
            "cost": {"currency": "USD",
                     "amount": round(e["watt_hours"] / 1000.0 * GRID_RATE_USD_KWH, 6),
                     "rate_usd_kwh": GRID_RATE_USD_KWH},
            "gate": {"rule": GATE_RULE, "verdict": verdict},
            "determinism": {"seed": self.seed, "state_digest": digest},
        }
        receipt["integrity"] = {"algorithm": "sha256",
                                "receipt_sha256": self._digest_of(receipt)}

        ok_builtin, msg_builtin = self._builtin_validate(receipt)
        path = self.receipt_dir / f"{receipt['receipt_id']}.json"
        path.write_text(json.dumps(receipt, indent=2))
        ok_ext, msg_ext = self._external_validate(path)

        with open(self.receipt_dir / "ledger.jsonl", "a") as f:
            f.write(json.dumps({"receipt_id": receipt["receipt_id"], "path": str(path),
                                "gate_verdict": verdict,
                                "builtin_validate": [ok_builtin, msg_builtin],
                                "external_validate": [ok_ext, msg_ext],
                                "sealed_at": time.time()}) + "\n")
        self._receipt_path = str(path)
        return str(path), receipt

    # -- validation / integrity -------------------------------------------------------
    @staticmethod
    def _builtin_validate(receipt: dict) -> Tuple[bool, str]:
        """Standalone structural check (the fleet's g7_validate.mjs is used
        instead when G7_VALIDATOR points at it). Fail-closed."""
        try:
            if receipt.get("schema") != SCHEMA:
                return False, "schema mismatch"
            if receipt.get("verdict") not in VERDICTS:
                return False, f"verdict not in {VERDICTS}"
            for k in ("energy_j", "energy_wh", "window_s", "receipt_id", "seed"):
                if k not in receipt:
                    return False, f"missing field {k}"
            if receipt["verdict"] == "PASS" and receipt["power_samples"] == 0:
                return False, "PASS with zero power samples — must be VOID"
            wh = receipt["energy_wh"]
            if wh is not None and abs(wh - receipt["energy_j"] / 3600.0) > 0.02 * max(wh, 1e-9):
                return False, "energy_wh inconsistent with energy_j/3600"
            return True, "builtin schema check ok"
        except Exception as exc:
            return False, f"builtin validate error: {exc}"

    @staticmethod
    def _external_validate(path: str) -> Tuple[bool, str]:
        """Run the fleet g7_validate.mjs when available (guard.py pattern).
        Fail-closed: missing validator -> (False, note), booked honestly."""
        cand = os.environ.get("G7_VALIDATOR")
        if not cand or not os.path.exists(cand):
            return False, "external validator not configured (set G7_VALIDATOR)"
        try:
            r = subprocess.run(["node", cand, path], capture_output=True,
                               text=True, timeout=30)  # list-form; never shell=True
            return r.returncode == 0, (r.stdout + r.stderr).strip()[-400:]
        except Exception as exc:
            return False, f"validator failed to run: {exc}"

    @staticmethod
    def verify_integrity(receipt_path: str) -> Tuple[bool, str]:
        """E6 pattern: detect receipt tampering + summary drift.

        1. recompute the receipt's own sha256 (any field edit is detected);
        2. recompute state_digest over guard_summary.json in the same dir
           (artifact drift is detected — 'receipt drift detected', E6 KEEP).
        """
        path = Path(receipt_path)
        receipt = json.loads(path.read_text())
        expect = (receipt.get("integrity") or {}).get("receipt_sha256")
        actual = G7Wrapper._digest_of(receipt)
        if expect != actual:
            return False, "receipt digest mismatch: receipt fields were tampered"
        summary_path = path.parent / "guard_summary.json"
        if not summary_path.exists():
            return False, "guard_summary.json missing (drift)"
        digest = (receipt.get("determinism") or {}).get("state_digest")
        actual_summary = hashlib.sha256(summary_path.read_bytes()).hexdigest()
        if digest != actual_summary:
            return False, ("state_digest drift: guard_summary.json does not match "
                           "the artifact this receipt sealed")
        return True, "integrity ok"


# --------------------------------------------------------------------------
# The context manager (the importable G7 seal)
# --------------------------------------------------------------------------
@contextlib.contextmanager
def watt_window(task_id: str = "ungated", probe: Optional[PowerProbe] = None,
                receipt_dir: str = "receipts", poll_s: float = POLL_S,
                timeout_s: float = 1800.0, seed: str = DEFAULT_SEED):
    """`with watt_window(task_id=..., probe=...) as g:` — preflight on
    enter, watt-sampled window across the body, ALWAYS a sealed receipt on
    exit:

      clean + measured            -> g7-watt-receipt@1, verdict PASS
      breach / exception in body  -> verdict KILL (traceback booked), and
                                     the exception RE-RAISES after sealing
      zero valid power samples    -> verdict VOID (fail-closed: sampling
                                     failure declared, never faked)
      preflight refusal           -> GuardRefusal raised (refusal receipt
                                     already written; breach + path carried)

    The yielded object is the live G7Wrapper (g.summary() mid-window, or
    fold your own fields before exit via g.windows).
    """
    w = G7Wrapper(probe if probe is not None else NvidiaSmiProbe(),
                  task_id=task_id, receipt_dir=receipt_dir, poll_s=poll_s,
                  timeout_s=timeout_s, seed=seed)
    if not w.preflight():
        raise GuardRefusal(w.breach or "unknown breach", w._receipt_path or "")
    w.begin_window()
    try:
        yield w
    except BaseException:
        w.traceback = traceback.format_exc()
        w.end_window()
        w.emit_receipt(verdict="KILL")
        raise
    w.end_window()
    if w.timeout_s and (time.time() - w._win_t0) > w.timeout_s:
        w.breach = f"wall-clock timeout {int(w.timeout_s)}s exceeded"
    w.emit_receipt(verdict=w.default_verdict())


# --------------------------------------------------------------------------
# Self-test (CPU-only; FakePowerProbe injected, nvidia-smi never touched)
# --------------------------------------------------------------------------
def selftest() -> dict:
    import tempfile
    tmp = tempfile.TemporaryDirectory(prefix="g7watt-selftest-")
    base = Path(tmp.name)
    checks: Dict[str, bool] = {}
    receipts: Dict[str, str] = {}

    # 1. healthy window via the CONTEXT MANAGER -> PASS receipt, expected Wh
    d = base / "healthy"
    with watt_window(task_id="g7-selftest-healthy",
                     probe=FakePowerProbe(watts=65.0, free_vram_mib=6000, temp_c=55),
                     receipt_dir=str(d), poll_s=0.02) as g:
        time.sleep(0.25)
        g_summary_mid = g.summary()
    r = json.loads(Path(g._receipt_path).read_text())
    receipts["healthy"] = g._receipt_path
    expected_wh = 65.0 * r["window_s"] / 3600.0
    checks["cm_healthy_pass_receipt"] = (
        r["schema"] == SCHEMA and r["verdict"] == "PASS"
        and r["seed"] == DEFAULT_SEED and r["energy"]["source"] == "measured"
        and r["power_samples"] >= 3 and r["window_s"] > 0.15)
    checks["cm_healthy_energy_expected_wh"] = (
        expected_wh > 0 and abs(r["energy_wh"] - expected_wh) <= 0.02 * expected_wh
        and abs(r["energy_wh"] - r["energy_j"] / 3600.0) < 1e-12
        and g_summary_mid["samples"] >= 1)

    # 2. breached preflight -> GuardRefusal raised + refusal receipt (KILL)
    d = base / "refused"
    probe = FakePowerProbe(free_vram_mib=500, temp_c=55)
    refused = None
    try:
        with watt_window(task_id="g7-selftest-refused", probe=probe,
                         receipt_dir=str(d), poll_s=0.02):
            raise AssertionError("body must never run on refused preflight")
    except GuardRefusal as exc:
        refused = exc
    r2 = json.loads(Path(refused.receipt_path).read_text())
    receipts["refused"] = refused.receipt_path
    checks["cm_refusal_raises_loud"] = (
        refused is not None and "VRAM" in refused.breach)
    checks["refusal_receipt_kill"] = (
        r2["verdict"] == "KILL" and r2.get("refusal") is True
        and r2["energy"]["source"] == "unmeasured" and r2["energy_j"] == 0.0)

    # 3. exploding body -> KILL receipt with traceback, exception re-raises,
    #    file still valid JSON
    d = base / "kill"
    raised = False
    try:
        with watt_window(task_id="g7-selftest-kill",
                         probe=FakePowerProbe(watts=65.0, free_vram_mib=6000,
                                              temp_c=55),
                         receipt_dir=str(d), poll_s=0.02):
            time.sleep(0.1)
            raise ValueError("boom")
    except ValueError:
        raised = True
    g3_path = sorted(d.glob("g7-wr-*.json"))[-1]
    r3 = json.loads(g3_path.read_text())  # parses => valid JSON
    receipts["kill"] = str(g3_path)
    checks["cm_exception_reraised_fail_loud"] = raised
    checks["kill_receipt_traceback_booked"] = (
        r3["verdict"] == "KILL" and "ValueError: boom" in (r3.get("traceback") or "")
        and r3["energy_j"] > 0 and r3["power_samples"] >= 1)

    # 4. dead probe (all-None samples) -> VOID fail-closed, never faked
    d = base / "void"
    with watt_window(task_id="g7-selftest-void",
                     probe=FakePowerProbe(samples=[
                         {"watts": None, "free_vram_mib": 6000, "temp_c": 55,
                          "util_pct": None}]),
                     receipt_dir=str(d), poll_s=0.02):
        time.sleep(0.1)
    g4_path = sorted(d.glob("g7-wr-*.json"))[-1]
    r4 = json.loads(g4_path.read_text())
    checks["dead_probe_void_fail_closed"] = (
        r4["verdict"] == "VOID" and r4["power_samples"] == 0
        and r4["energy"]["source"] == "unmeasured"
        and r4["energy"]["derivation"] is not None)
    ok_void, _ = G7Wrapper._builtin_validate(r4)
    checks["void_receipt_schema_valid"] = ok_void
    bad_pass = dict(r4)
    bad_pass["verdict"] = "PASS"
    ok_bad, _ = G7Wrapper._builtin_validate(bad_pass)
    checks["builtin_rejects_pass_with_zero_samples"] = not ok_bad

    # 5. callable API still works (run_window) and appends to the ledger
    d = base / "runwin"
    w5 = G7Wrapper(FakePowerProbe(watts=65.0, free_vram_mib=6000, temp_c=55),
                   task_id="g7-selftest-runwin", receipt_dir=str(d), poll_s=0.02)
    assert w5.preflight() is True
    w5.run_window(lambda: time.sleep(0.1))
    r5 = json.loads(Path(w5._receipt_path).read_text())
    ledger_lines = (d / "ledger.jsonl").read_text().strip().splitlines()
    checks["run_window_callable_pass"] = r5["verdict"] == "PASS"
    checks["ledger_append_only"] = len(ledger_lines) == 1 and \
        json.loads(ledger_lines[0])["gate_verdict"] == "PASS"

    # 6. tampered receipt -> integrity check detects it (E6 drift pattern)
    tampered = dict(r5)
    tampered["energy_j"] = r5["energy_j"] + 1.0
    Path(w5._receipt_path).write_text(json.dumps(tampered, indent=2))
    ok_tamper, _ = G7Wrapper.verify_integrity(w5._receipt_path)
    checks["tamper_detected"] = ok_tamper is False
    ok_clean, msg_clean = G7Wrapper.verify_integrity(receipts["healthy"])
    checks["clean_receipt_verifies"] = ok_clean is True

    tmp.cleanup()
    verdict = "PASS" if all(checks.values()) else "KILL"
    return {"verdict": verdict, "checks": checks,
            "receipts": {k: Path(v).name for k, v in receipts.items()},
            "integrity_note": msg_clean,
            "provenance": "guard.py G7 watt-receipt instrumentation KEEP "
                          "(RESULTS.md 2026-10-01) + E6 receipt-drift KEEP"}


def main() -> int:
    try:
        result = selftest()
    except BaseException:
        result = {"verdict": "KILL", "error": traceback.format_exc(limit=5)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
