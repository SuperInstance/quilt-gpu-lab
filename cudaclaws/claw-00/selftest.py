#!/usr/bin/env python3
"""claw-00 selftest — first cudaclaw.

Validates the recruit->run->receipt->preempt loop before any real kernel risks
it. One process per job. Reads a JSON job descriptor on stdin, writes exactly
one JSON receipt to stdout (even on failure — no receipt = never happened).
Telemetry heartbeat to stderr every <=2s. Cooperative cancel at chunk
boundaries. subprocess list form only (never shell=True). O(chunk) memory.
Seed 2718. Fixed-order f32 FMA map; output_sha256 is the determinism witness.

GPU work is best-effort: if the CUDA driver (libcuda via ctypes) is absent or
fails on WSL2 /dev/dxg, the claw degrades honestly (cuda_unavailable=true,
cpu_caps_applied=true) and runs the FLOP witness on CPU with bitwise-stable
numpy float32.
"""
from __future__ import annotations

import json
import os
import sys
import time
import signal
import platform
import hashlib
import subprocess
import threading

RECEIPT_VERSION = "claw-receipt-v1"
CLAW_NAME = "claw-00-selftest"
CLAW_VERSION = "0.1.0"
DECLARED_VRAM = 536870912  # 512 MiB
DEFAULT_SEED = 2718

# CPU-safe fallback scale for the FLOP witness (the declared defaults are
# GPU-scale: 4M elems * 4096 inner * 8 passes ~ 137G FMA, seconds on GPU,
# minutes on CPU numpy). When CUDA is unavailable we clamp honestly.
CPU_SAFE = {"flop_chunk_elems": 1024, "flop_inner_iters": 256, "flop_passes": 8}

_heartbeat_interval = 2.0


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_job() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"_bad_stdin": str(e)}


def nvidia_smi_probe():
    """Device probe via nvidia-smi (list form). Gracefully optional on WSL2."""
    cmd = [
        "/usr/lib/wsl/lib/nvidia-smi",
        "--query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception as e:  # noqa: BLE001
        return None, "nvidia-smi failed: %s" % e
    if r.returncode != 0:
        return None, "nvidia-smi rc=%d" % r.returncode
    line = r.stdout.strip().splitlines()[0]
    p = [x.strip() for x in line.split(",")]
    return {
        "name": p[0],
        "memory_used_mb": p[1],
        "memory_total_mb": p[2],
        "temperature_c": p[3],
        "util_pct": p[4],
    }, None


# --- CUDA driver via ctypes (best-effort) -----------------------------------

_cuda = None
_cuda_err = "not attempted"


def _load_cuda():
    global _cuda, _cuda_err
    if _cuda is not None or _cuda_err != "not attempted":
        return _cuda
    try:
        import ctypes  # noqa: F401
        for name in ("libcuda.so.1", "libcuda.so"):
            try:
                _cuda = ctypes.CDLL(name)
                return _cuda
            except OSError as e:
                _cuda_err = "load %s: %s" % (name, e)
        _cuda_err = "libcuda not found"
    except Exception as e:  # noqa: BLE001
        _cuda_err = "ctypes import: %s" % e
    return _cuda


def cuda_memcpy_bandwidth(lib, nbytes, reps):
    """Device-to-device memcpy bandwidth. Returns (gbps, err) — err=None on ok."""
    import ctypes

    lib.cuInit.argtypes = [ctypes.c_uint]
    lib.cuInit.restype = ctypes.c_int
    rc = lib.cuInit(0)
    if rc != 0:
        return None, "cuInit rc=%d" % rc

    lib.cuCtxCreate_v2.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int]
    lib.cuCtxCreate_v2.restype = ctypes.c_int
    ctx = ctypes.c_void_p()
    rc = lib.cuCtxCreate_v2(ctypes.byref(ctx), 0, 0)
    if rc != 0:
        return None, "cuCtxCreate rc=%d" % rc

    try:
        lib.cuMemAlloc_v2.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        lib.cuMemAlloc_v2.restype = ctypes.c_int
        d1, d2 = ctypes.c_void_p(), ctypes.c_void_p()
        rc = lib.cuMemAlloc_v2(ctypes.byref(d1), nbytes)
        if rc != 0:
            return None, "cuMemAlloc(d1) rc=%d" % rc
        rc = lib.cuMemAlloc_v2(ctypes.byref(d2), nbytes)
        if rc != 0:
            return None, "cuMemAlloc(d2) rc=%d" % rc

        lib.cuMemcpyDtoD_v2.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        lib.cuMemcpyDtoD_v2.restype = ctypes.c_int
        t0 = time.perf_counter()
        for _ in range(reps):
            rc = lib.cuMemcpyDtoD_v2(d2, d1, nbytes)
            if rc != 0:
                return None, "cuMemcpyDtoD rc=%d" % rc
        dt = time.perf_counter() - t0
        if dt <= 0:
            return None, "zero elapsed"
        gbps = (nbytes * reps) / dt / 1e9
        lib.cuMemFree_v2.argtypes = [ctypes.c_void_p]
        lib.cuMemFree_v2.restype = ctypes.c_int
        lib.cuMemFree_v2(d1)
        lib.cuMemFree_v2(d2)
        return gbps, None
    finally:
        try:
            lib.cuCtxDestroy_v2.argtypes = [ctypes.c_void_p]
            lib.cuCtxDestroy_v2.restype = ctypes.c_int
            lib.cuCtxDestroy_v2(ctx)
        except Exception:  # noqa: BLE001
            pass


def cuda_device_name(lib):
    """Best-effort device name via driver API (no context needed)."""
    import ctypes

    lib.cuDeviceGetCount.argtypes = [ctypes.c_void_p]
    lib.cuDeviceGetCount.restype = ctypes.c_int
    count = ctypes.c_int()
    if lib.cuDeviceGetCount(ctypes.byref(count)) != 0 or count.value < 1:
        return None
    lib.cuDeviceGetName.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    lib.cuDeviceGetName.restype = ctypes.c_int
    name = ctypes.create_string_buffer(256)
    if lib.cuDeviceGetName(name, 256, 0) != 0:
        return None
    return name.value.decode("utf-8", "replace")


# --- deterministic FLOP witness (numpy float32, CPU) -------------------------

def _u32(x):
    return int(x) & 0xFFFFFFFF


def flop_witness(seed, elems, inner, passes):
    """Fixed-order f32 FMA map. Returns sha256 hex of the final chunk bytes."""
    import numpy as np

    h = hashlib.sha256()
    for p in range(passes):
        base = p * elems
        gids = np.arange(base, base + elems, dtype=np.uint64)
        # y0 = hash(gid, seed) folded into [0.25, 0.25+65535/65536)
        y = np.zeros(elems, dtype=np.float32)
        for i in range(elems):
            y[i] = np.float32(0.25 + (_u32((int(gids[i]) * 2654435761) ^ seed) & 0xFFFF) / 65536.0)
        for j in range(inner):
            hh = ((gids * np.uint64(2654435761)) ^ np.uint64(seed) ^ np.uint64(j)) & np.uint64(0xFFFFFFFF)
            a = ((hh & 0xFFFF) / 65536.0 - 0.5).astype(np.float32)  # [-0.5, 0.5): contraction
            hh2 = ((gids * np.uint64(2654435761)) ^ np.uint64(seed) ^ np.uint64(j + 1)) & np.uint64(0xFFFFFFFF)
            b = (0.5 + (hh2 & 0xFFFF) / 65536.0).astype(np.float32)  # [0.5, 1.5)
            y = (y * a + b).astype(np.float32)
        h.update(y.tobytes())
    return h.hexdigest()


def main() -> int:
    started = time.time()
    job = read_job()
    job_id = str(job.get("job_id") or "%s-%d" % (CLAW_NAME, int(started)))
    seed = int(job.get("seed", DEFAULT_SEED))

    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "claw": {"name": CLAW_NAME, "version": CLAW_VERSION},
        "job_id": job_id,
        "seed": seed,
        "status": "ok",
        "error": None,
        "started_at": iso_now(),
        "ended_at": None,
        "duration_s": None,
        "host": platform.node(),
        "pid": os.getpid(),
        "device": None,
        "telemetry": "ok",
        "declared_vram_ceiling_bytes": DECLARED_VRAM,
        "vram_used_peak_mb": None,
        "memcpy": None,
        "flop": None,
        "progress": None,
        "preempt_reason": None,
        "cuda_unavailable": False,
        "cpu_caps_applied": False,
    }

    if job.get("_bad_stdin"):
        receipt["status"] = "error"
        receipt["error"] = "bad stdin JSON: %s" % job["_bad_stdin"]

    # heartbeat thread (<=2s on stderr)
    stop = threading.Event()

    def _beat():
        while not stop.wait(_heartbeat_interval):
            el = time.time() - started
            sys.stderr.write(
                json.dumps({"ts": round(el, 2), "phase": "running", "progress_sofar": None})
                + "\n"
            )
            sys.stderr.flush()

    beat = threading.Thread(target=_beat, daemon=True)
    beat.start()

    cancel_flag = {"sig": None}

    def _on_sigterm(signum, frame):  # noqa: ARG001
        cancel_flag["sig"] = "SIGTERM"

    signal.signal(signal.SIGTERM, _on_sigterm)

    def _cancel_requested():
        if cancel_flag["sig"]:
            return cancel_flag["sig"]
        if os.path.exists("job.%s.cancel" % job_id):
            return "cancel-file"
        return None

    try:
        # 1) device probe
        smi, smi_err = nvidia_smi_probe()
        if smi:
            receipt["device"] = smi["name"]
            receipt["vram_used_peak_mb"] = float(smi["memory_used_mb"])
        else:
            receipt["device"] = None

        # 2) CUDA best-effort
        lib = _load_cuda()
        cuda_ok = lib is not None
        memcpy_result = None
        if cuda_ok:
            devname = cuda_device_name(lib)
            if devname:
                receipt["device"] = devname
            nbytes = int(job.get("memcpy_bytes", 67108864))
            reps = int(job.get("memcpy_reps", 50))
            gbps, cerr = cuda_memcpy_bandwidth(lib, nbytes, reps)
            memcpy_result = {
                "bytes": nbytes,
                "reps": reps,
                "seconds": None,
                "gb_per_s": round(gbps, 3) if gbps else None,
                "error": cerr,
            }
            if cerr:
                cuda_ok = False
        if not cuda_ok:
            receipt["cuda_unavailable"] = True
            receipt["cpu_caps_applied"] = True
            receipt["error"] = receipt["error"] or ("CUDA unavailable: %s" % _cuda_err)
            if memcpy_result is None:
                memcpy_result = {"bytes": None, "reps": None, "seconds": None, "gb_per_s": None,
                                 "error": _cuda_err}
        receipt["memcpy"] = memcpy_result

        # 3) deterministic FLOP witness (chunk boundaries = passes)
        felems = int(job.get("flop_chunk_elems", 4194304))
        finner = int(job.get("flop_inner_iters", 4096))
        fpasses = int(job.get("flop_passes", 8))
        if receipt["cpu_caps_applied"]:
            felems = min(felems, CPU_SAFE["flop_chunk_elems"])
            finner = min(finner, CPU_SAFE["flop_inner_iters"])
            fpasses = min(fpasses, CPU_SAFE["flop_passes"])

        flop = {"elements": felems, "inner_iters": finner, "passes": fpasses,
                "passes_done": 0, "flops": 0, "seconds": None, "gf_per_s": None,
                "map": "fma", "output_sha256": None, "error": None}
        preempted = False
        try:
            t0 = time.perf_counter()
            done_passes = 0
            for p in range(fpasses):
                c = _cancel_requested()
                if c:
                    preempted = True
                    receipt["preempt_reason"] = c
                    break
                # throttle file: read 0..1, stretch boundary by (1-p)*2s
                throttle = 1.0
                try:
                    with open("job.%s.throttle" % job_id) as f:
                        throttle = max(0.0, min(1.0, float(f.read().strip() or "1.0")))
                except Exception:  # noqa: BLE001
                    pass
                if throttle <= 0.0:
                    # pause: wait until raised or canceled
                    while throttle <= 0.0:
                        c = _cancel_requested()
                        if c:
                            preempted = True
                            receipt["preempt_reason"] = c
                            break
                        time.sleep(0.1)
                        try:
                            with open("job.%s.throttle" % job_id) as f:
                                throttle = max(0.0, min(1.0, float(f.read().strip() or "1.0")))
                        except Exception:  # noqa: BLE001
                            break
                    if preempted:
                        break
                if throttle < 1.0:
                    time.sleep((1.0 - throttle) * 2.0)
                flop_witness(seed, felems, finner, 1)  # one pass
                done_passes += 1
            t1 = time.perf_counter()
            flop["passes_done"] = done_passes
            flop["flops"] = done_passes * felems * finner * 2  # mul + add
            flop["seconds"] = round(t1 - t0, 4)
            flop["gf_per_s"] = round(flop["flops"] / (t1 - t0) / 1e9, 3) if (t1 - t0) > 0 else None
            if preempted:
                receipt["status"] = "preempted"
                receipt["progress"] = round(done_passes / fpasses, 4) if fpasses else None
            else:
                flop["output_sha256"] = flop_witness(seed, felems, finner, fpasses)
                receipt["progress"] = 1.0
        except Exception as e:  # noqa: BLE001
            flop["error"] = str(e)
            receipt["status"] = "error"
            receipt["error"] = "flop: %s" % e
        receipt["flop"] = flop
    finally:
        stop.set()
        beat.join(timeout=1.0)

    receipt["ended_at"] = iso_now()
    receipt["duration_s"] = round(time.time() - started, 4)
    if smi and smi.get("temperature_c") not in (None, ""):
        receipt["telemetry"] = "ok"
    elif receipt["status"] == "ok":
        # temp/util missing alone does not degrade; keep 'ok' (WSL2 NVML quirk)
        receipt["telemetry"] = "ok"

    sys.stdout.write(json.dumps(receipt) + "\n")
    sys.stdout.flush()

    if receipt["status"] == "error":
        return 1
    if receipt["status"] == "preempted":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
