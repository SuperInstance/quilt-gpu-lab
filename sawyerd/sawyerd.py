#!/usr/bin/env python3
"""sawyerd — the always-on local orchestrator ("Tom Sawyer"). P1 skeleton.

Sawyer owns no compute; it holds *leases*. Every unit of work is a
PREEMPTIBLE, RESOURCE-DECLARED JOB CONTRACT (claw.json.schema.md), never a
bare process — so the ramp is just "how many contracts do we honour", and a
missing receipt means the job never happened.

Two lanes: local silicon is FREE and harvested; LLM calls are METERED —
guides and nudges, never grinders, capped per epoch.

Stdlib only. O(queue) memory. Seed 2718. subprocess LIST form, never
shell=True. State on ext4. P2 hook: actually launching workers.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Optional

SEED_DEFAULT = 2718
TICK_S = 1.0             # sensor + scheduler tick
EMA_ALPHA = 0.30         # signal smoothing
DWELL_S = 45.0           # minimum dwell in a level before any transition
HYSTERESIS = 0.08        # idle-score margin required to cross a boundary
VRAM_RESERVE_MB = 1792   # standing headroom: foreground work never stalls
DEFAULT_ROOT = Path(os.environ.get(
    "SAWYERD_ROOT", str(Path.home() / "projects/quilt-gpu-lab/sawyerd")))
LANE_FREE, LANE_METERED = "free", "metered"
LOCAL_KINDS = {"cudaclaw", "chipbot", "chiaroscuro"}
NVML_CANDIDATES = ("/usr/lib/wsl/lib/nvidia-smi", "nvidia-smi")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] sawyerd: {msg}", file=sys.stderr, flush=True)


# ------------------------------------------------------------------ the ramp
class Ramp(IntEnum):
    PARKED, TRICKLE, CRUISE, HARVEST = 0, 1, 2, 3


class RampGovernor:
    """Parked->Trickle->Cruise->Harvest with EMA smoothing + dwell debounce.

    THRESHOLDS are the entry idle-scores for Trickle/Cruise/Harvest. A change
    commits only once the smoothed score clears the boundary by HYSTERESIS and
    the level has been held DWELL_S — a ramp with detents, so it never flaps.
    """

    THRESHOLDS = (0.30, 0.60, 0.85)
    CAPACITY = {Ramp.PARKED: 0, Ramp.TRICKLE: 1, Ramp.CRUISE: 3, Ramp.HARVEST: 8}

    def __init__(self, now: Optional[float] = None) -> None:
        self.level = Ramp.PARKED
        self.ema: Optional[float] = None
        self.since = time.monotonic() if now is None else now

    def target(self, score: float) -> Ramp:
        for i, t in enumerate(self.THRESHOLDS):
            if score < t:
                return Ramp(i)
        return Ramp.HARVEST

    def step(self, raw: float, now: Optional[float] = None) -> Ramp:
        now = time.monotonic() if now is None else now
        self.ema = raw if self.ema is None else EMA_ALPHA * raw + (1 - EMA_ALPHA) * self.ema
        want = self.target(self.ema)
        if want > self.level:                       # ramp up: clear the entry band
            ok = self.ema >= self.THRESHOLDS[want - 1] + HYSTERESIS
        elif want < self.level:                     # ramp down: fall below the exit band
            ok = self.ema <= self.THRESHOLDS[self.level - 1] - HYSTERESIS
        else:
            ok = False
        if ok and (now - self.since) >= DWELL_S:
            log(f"ramp {self.level.name} -> {want.name} (ema={self.ema:.3f})")
            self.level, self.since = want, now
        return self.level

    @property
    def capacity(self) -> int:
        """How many contracts may be honoured right now."""
        return self.CAPACITY[self.level]

    def throttle(self) -> float:
        """Control value 0.0..1.0 written to cooperative claws at chunk boundaries."""
        return (0.0, 0.35, 0.7, 1.0)[int(self.level)]


# ------------------------------------------------------------------- sensors
@dataclass
class Sensors:
    gpu_util_pct: Optional[float] = None
    vram_used_mb: Optional[float] = None
    vram_total_mb: Optional[float] = None
    gpu_temp_c: Optional[float] = None
    loadavg_1m: Optional[float] = None
    cpu_count: int = 1
    telemetry: str = "degraded"      # "ok" | "degraded" (WSL2 NVML is quirky)


def _run(argv: list[str], timeout: float = 4.0) -> Optional[str]:
    """subprocess LIST form only — shell re-parsing is a banned bug class."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def _nvml() -> Optional[str]:
    for exe in NVML_CANDIDATES:
        out = _run([exe, "--query-gpu=utilization.gpu,memory.used,memory.total,"
                          "temperature.gpu", "--format=csv,noheader,nounits"])
        if out:
            return out
    return None


def sense() -> Sensors:
    s = Sensors(cpu_count=os.cpu_count() or 1)
    try:
        s.loadavg_1m = float(Path("/proc/loadavg").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        pass
    out = _nvml()
    if out:
        try:
            util, used, total, temp = (float(x) for x in out.splitlines()[0].split(",")[:4])
            s.gpu_util_pct, s.vram_used_mb = util, used
            s.vram_total_mb, s.gpu_temp_c = total, temp
            s.telemetry = "ok"
        except (ValueError, IndexError):
            pass
    return s


def idle_score(s: Sensors) -> float:
    """0.0 = the human owns the machine; 1.0 = deep idle.

    Conservative: degraded telemetry (we cannot see the GPU) scores 0.0, so
    Sawyer parks and only sensors until real measurement returns.
    """
    if s.telemetry != "ok":
        return 0.0
    parts: list[float] = []
    if s.gpu_util_pct is not None:
        parts.append(1.0 - min(1.0, s.gpu_util_pct / 100.0))
    if s.vram_used_mb is not None and s.vram_total_mb:
        parts.append(max(0.0, (s.vram_total_mb - s.vram_used_mb) / s.vram_total_mb))
    if s.loadavg_1m is not None:
        parts.append(1.0 - min(1.0, s.loadavg_1m / max(1, s.cpu_count)))
    return sum(parts) / len(parts) if parts else 0.0


# ------------------------------------------------------------- job contracts
@dataclass
class JobContract:
    """The unit of orchestration: a contract, not a process."""

    job_id: str
    claw: str
    lane: str = LANE_FREE                 # "free" | "metered"
    vram_ceiling_mb: int = 0
    duration_class: str = "ms"
    seed: int = SEED_DEFAULT
    io: dict[str, Any] = field(default_factory=dict)   # {"in": {...}, "out": {...}}
    priority: int = 0
    submitted_by: str = "sawyerd"
    state: str = "queued"                 # queued|running|preempted|done|failed
    progress: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def lane_for(kind: str) -> str:
    """The free-vs-metered rule: local silicon is free; LLM calls are metered."""
    return LANE_FREE if kind in LOCAL_KINDS else LANE_METERED


class Ledger:
    """Free lane is harvested; metered lane is capped per epoch."""

    def __init__(self, metered_cap: int = 24, epoch_s: float = 3600.0,
                 now: Optional[float] = None) -> None:
        self.metered_cap, self.epoch_s = metered_cap, epoch_s
        self.epoch_start = time.monotonic() if now is None else now
        self.metered_used = 0
        self.free_runs = 0

    def _roll(self, now: float) -> None:
        if now - self.epoch_start >= self.epoch_s:
            self.epoch_start, self.metered_used = now, 0

    def allow(self, contract: JobContract, now: Optional[float] = None) -> bool:
        if contract.lane == LANE_FREE:
            return True
        self._roll(time.monotonic() if now is None else now)
        return self.metered_used < self.metered_cap

    def charge(self, contract: JobContract) -> None:
        if contract.lane == LANE_FREE:
            self.free_runs += 1
        else:
            self.metered_used += 1


# ----------------------------------------------------------- registry + spool
REQUIRED_CLAW_KEYS = ("name", "version", "duration_class", "input_schema",
                      "output_schema", "determinism_policy")


def load_claw_json(path: os.PathLike[str] | str) -> Optional[dict[str, Any]]:
    """Parse one claw manifest. Malformed => None, and it never gets recruited."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    missing = [k for k in REQUIRED_CLAW_KEYS if k not in raw]
    if "vram_ceiling_bytes" not in raw and "vram_ceiling_mb" not in raw:
        missing.append("vram_ceiling_bytes")
    if missing:
        log(f"claw manifest {path} missing {missing} — skipped")
        return None
    return raw


class Registry:
    """Self-describing workers: glob claws/*/claw.json. No central registration."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.workers: dict[str, dict[str, Any]] = {}

    def scan(self) -> dict[str, dict[str, Any]]:
        if not self.root.is_dir():
            return self.workers
        for manifest in sorted(self.root.glob("*/claw.json")):
            data = load_claw_json(manifest)
            if data:
                data["_path"] = str(manifest)
                self.workers[str(data["name"])] = data
        return self.workers

    def ceiling_mb(self, claw: str) -> int:
        w = self.workers.get(claw, {})
        if "vram_ceiling_mb" in w:
            return int(w["vram_ceiling_mb"])
        return int(w.get("vram_ceiling_bytes", 0)) // (1024 * 1024)

    def admits(self, contract: JobContract, vram_free_mb: int) -> bool:
        """Best-fit by declared ceiling; the standing reserve is untouchable."""
        return self.ceiling_mb(contract.claw) + VRAM_RESERVE_MB <= vram_free_mb


class Spool:
    """Append-only JSONL job log on ext4. Resumable, idempotent, one line per event."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, contract: JobContract, **extra: Any) -> None:
        rec = {"ts": time.time(), **contract.as_dict(), **extra}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def pending(self) -> list[JobContract]:
        """Replay the log; last state per job_id wins. Absent receipt = never happened."""
        latest: dict[str, dict[str, Any]] = {}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        latest[rec["job_id"]] = rec
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        except OSError:
            return []
        live = {"queued", "preempted"}
        return [JobContract(**{k: v for k, v in rec.items()
                               if k in JobContract.__dataclass_fields__})
                for rec in latest.values() if rec.get("state") in live]


# ---------------------------------------------------------------- the daemon
class Sawyer:
    """Holds leases. Runs the tick loop. Owns no compute."""

    def __init__(self, root: Path = DEFAULT_ROOT, tick_s: float = TICK_S) -> None:
        self.root = Path(root)
        self.tick_s = tick_s
        self.spool = Spool(self.root / "spool/jobs.jsonl")
        self.registry = Registry(self.root / "claws")
        self.gov = RampGovernor()
        self.ledger = Ledger()
        self.running: dict[str, JobContract] = {}
        self._stop = False

    def install_signals(self) -> None:
        def handler(signum: int, _frame: Any) -> None:
            log(f"signal {signum} — draining, no new leases")
            self._stop = True
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, handler)
            except ValueError:
                pass   # not the main thread; fine when imported/embedded

    def step_once(self, now: Optional[float] = None) -> dict[str, Any]:
        """One tick: sense -> ramp -> admit/preempt -> publish state. O(queue)."""
        now = time.monotonic() if now is None else now
        s = sense()
        score = idle_score(s)
        level = self.gov.step(score, now)
        vram_free = (None if s.vram_total_mb is None or s.vram_used_mb is None
                     else int(s.vram_total_mb - s.vram_used_mb))
        admitted = self._admit(level, vram_free)
        status = {"ts": time.time(), "level": level.name,
                  "target_capacity": self.gov.capacity, "throttle": self.gov.throttle(),
                  "idle_score": round(score, 4),
                  "ema": None if self.gov.ema is None else round(self.gov.ema, 4),
                  "vram_free_mb": vram_free, "telemetry": s.telemetry,
                  "gpu_temp_c": s.gpu_temp_c, "running": len(self.running),
                  "admitted": admitted, "metered_used": self.ledger.metered_used,
                  "free_runs": self.ledger.free_runs}
        self._write_state(status)
        if level is Ramp.PARKED and self.running:
            self._preempt_all("parked: foreground owns the machine")
        return status

    def _admit(self, level: Ramp, vram_free_mb: Optional[int]) -> list[str]:
        """Lease spare capacity from the spool, honouring the lane rule + reserve."""
        started: list[str] = []
        spare = self.gov.capacity - len(self.running)
        if spare <= 0 or level is Ramp.PARKED:
            return started
        for contract in sorted(self.spool.pending(), key=lambda c: -c.priority):
            if spare <= 0:
                break
            if contract.job_id in self.running:
                continue
            if not self.registry.admits(contract, vram_free_mb or 0):
                continue
            if not self.ledger.allow(contract):
                log(f"metered lane capped; {contract.job_id} waits for next epoch")
                continue
            # P2 hook: launch the worker by contract, one process per job.
            # P1 leases only — the spool is the record of intent.
            self.ledger.charge(contract)
            self.running[contract.job_id] = contract
            self.spool.append(contract, state="running", leased_at=time.time())
            started.append(contract.job_id)
            spare -= 1
        return started

    def _preempt_all(self, reason: str) -> None:
        """Cooperative eviction: SIGTERM -> checkpoint -> requeue."""
        for job_id, contract in list(self.running.items()):
            log(f"preempt {job_id} ({reason})")
            self.spool.append(contract, state="preempted", reason=reason)
            self.running.pop(job_id, None)

    def _write_state(self, status: dict[str, Any]) -> None:
        try:
            target = self.root / "state/ramp.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(target)          # atomic
        except OSError as exc:
            log(f"state write failed: {exc}")

    def run_forever(self, max_ticks: Optional[int] = None) -> int:
        """Main loop: blocks, ticks every tick_s with drift correction. Returns tick count."""
        self.install_signals()
        log(f"sawyerd up — root={self.root} workers={sorted(self.registry.scan())} "
            f"tick={self.tick_s}s")
        ticks = 0
        while not self._stop and (max_ticks is None or ticks < max_ticks):
            began = time.monotonic()
            self.step_once(began)
            ticks += 1
            if self._stop:
                break
            time.sleep(max(0.0, self.tick_s - (time.monotonic() - began)))
        log(f"sawyerd down after {ticks} ticks")
        return ticks


def main(argv: Optional[list[str]] = None) -> int:
    """sawyerd.py [--once] [--ticks N] [--root PATH]"""
    args = list(sys.argv[1:] if argv is None else argv)
    root, max_ticks = DEFAULT_ROOT, None
    if "--root" in args:
        root = Path(args[args.index("--root") + 1])
    if "--ticks" in args:
        max_ticks = int(args[args.index("--ticks") + 1])
    daemon = Sawyer(root)
    if "--once" in args:
        print(json.dumps(daemon.step_once(), indent=2, sort_keys=True))
        return 0
    daemon.run_forever(max_ticks=max_ticks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
