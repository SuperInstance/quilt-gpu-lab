#!/usr/bin/env python3
"""parity_harness — cross-implementation conformance harness, standalone numpy.

Shape ported from results/a5_parity/a5_parity_repro.py (A5-PARITY, 2026-10-01):
run TWO implementations of the same spec over a size grid {16^2, 512^2}
(1024^2 optional), and compare in two modes:

  BIT — exact float equality: max|delta| = 0.0 AND checksum match (the A5 bar:
        bit-parity 0.0 at 16^2/512^2/1024^2, checksum 0.4000000059604645
        matched exactly at all sizes).
  TOL — max abs diff <= frozen tolerance, for cross-precision ports; the
        tolerance is a parameter fixed BEFORE the run and recorded in the
        receipt. No post-hoc loosening.

Plus the INSTRUMENT-01 ramp gate (RESULTS.md 2026-10-01): after >= ~10s idle,
first probes measure 2-10x slow (13x observed: 165k -> 2.20M cells/s after a
0.6s ramp) — so:
  - the harness warms up before ANY timing it reports (>= warmup_iters untimed
    bursts AND >= ramp_window_s of sustained load, both parameterized), and
  - a diagnostic first probe is compared against sustained timing and the
    ramp factor (first/sustained) is BOOKED in the receipt; consuming timing
    before the ramp is cleared is fail-loud: timing_verdict INCONCLUSIVE.

House contracts baked in: seed 2718 default; single JSON verdict; fail loud
(NaN/Inf in either output -> KILL receipt booked + NonFiniteOutput raised;
size grid not pairwise-aligned -> ParityHarnessError); std == 0 across timing
repeats -> INCONCLUSIVE (degenerate-statistic pin, verdict_gate doctrine —
the A5 receipt itself noted per-point numbers are single-draw statistics);
list-form subprocess only (this block shells out to nothing); never
print/copy secrets.

Self-test (__main__, CPU, <10s): bit-identical port A' -> parity PASS at all
sizes with checksum match; deliberately-different impl B -> parity KILL with
max|delta| booked; synthetic 13x-slow timing source -> ramp factor booked,
timing INCONCLUSIVE until warmup clears it, then PASS; std==0 repeats ->
INCONCLUSIVE; misaligned grid -> exception. Final stdout line is exactly one
JSON object with exactly one top-level "verdict"; exit 0 iff PASS.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

SCHEMA = "parity-harness-receipt@1"
DEFAULT_SEED = 2718
DEFAULT_SIZES = (16, 512)
RAMP_LAW = ("INSTRUMENT-01: idle >= ~10s -> short bursts measure 2-10x slow "
            "(13x observed); warm up (untimed bursts + >= 0.5s sustained "
            "load) before any timed claim or the first measurements lie")


class ParityHarnessError(Exception):
    """Fail loud: size grid not pairwise-aligned, bad mode, etc."""


class NonFiniteOutput(ParityHarnessError):
    """Fail loud: NaN/Inf in an implementation's output (KILL booked)."""


# --------------------------------------------------------------------------
# Reference spec + three demo implementations (the self-test's subjects).
# An "implementation of the spec" is any callable
#     impl(size: int, steps: int, seed: int) -> float32 ndarray (size, size)
# --------------------------------------------------------------------------
INJECT: Tuple[Tuple[int, int, float], ...] = ((1, 1, 4.8),)
THRESHOLD = 0.6


def _spec_init(size: int, inject=INJECT) -> np.ndarray:
    pot = np.full((size, size), np.float32(0.25), dtype=np.float32)
    for r, c, p in inject:
        pot[r, c] = pot[r, c] + np.float32(p)
    return pot


def make_impl(*, gather: str = "roll", hot_weight: np.float32 = np.float32(0.6),
              steps_default: int = 10) -> Callable:
    """Factory: two gather strategies (roll vs wrap-pad+slice) that produce
    BIT-IDENTICAL arithmetic, and a hot_weight knob for a deliberately
    divergent implementation."""

    def impl(size: int, steps: int = steps_default, seed: int = DEFAULT_SEED) -> np.ndarray:
        pot = _spec_init(size)
        hw, cw = np.float32(hot_weight), np.float32(1.0) - np.float32(hot_weight)
        lw = np.float32(1.0) - np.float32(hot_weight) * np.float32(0.5)  # cold mix
        for _ in range(steps):
            if gather == "roll":
                n = np.roll(pot, 1, 0)
                s = np.roll(pot, -1, 0)
                e = np.roll(pot, 1, 1)
                w = np.roll(pot, -1, 1)
            else:  # wrap-pad + slice: same neighbors, different code path
                p = np.pad(pot, 1, mode="wrap")
                n, s = p[:-2, 1:-1], p[2:, 1:-1]
                e, w = p[1:-1, :-2], p[1:-1, 2:]
            avg = (n + s + e + w) * np.float32(0.25)
            hot = pot > np.float32(THRESHOLD)
            pot = np.where(hot, pot * hw + avg * cw, pot * np.float32(0.9) + avg * np.float32(0.1))
        return np.ascontiguousarray(pot, dtype=np.float32)

    return impl


def checksum(pot: np.ndarray) -> float:
    """Host-side float64 accumulation over the float32 output, fixed
    reduction order (A5 shape: checksum accumulated host-side)."""
    return float(np.add.reduce(np.ascontiguousarray(pot, dtype=np.float64).ravel()))


# --------------------------------------------------------------------------
# Ramp gate (INSTRUMENT-01)
# --------------------------------------------------------------------------
class RampGate:
    """Warm-up rule + ramp detector for one timing consumer.

    clear() must run before timed_repeats() will stand behind a number:
    >= warmup_iters untimed bursts AND >= ramp_window_s of sustained load.
    A diagnostic probe taken before clear() is booked and compared with the
    first sustained probe: ramp_factor = first_wall_ns / sustained_wall_ns
    (>1 means the first probe lied). Timing consumed before clearing ->
    timing_verdict INCONCLUSIVE, fail loud.
    """

    def __init__(self, *, warmup_iters: int = 3, ramp_window_s: float = 0.5,
                 clock: Optional[Callable[[], int]] = None):
        if warmup_iters < 1:
            raise ValueError("warmup_iters >= 1 required")
        self.warmup_iters = warmup_iters
        self.ramp_window_s = ramp_window_s
        self.clock = clock or time.perf_counter_ns
        self.cleared = False
        self.first_probe: Optional[dict] = None
        self.sustained_probe: Optional[dict] = None
        self.ramp_factor: Optional[float] = None

    def probe(self, burst: Callable[[], None], cells: float) -> dict:
        t0 = self.clock()
        burst()
        t1 = self.clock()
        wall = max(1, t1 - t0)
        return {"cells_per_s": round(cells / (wall / 1e9), 1), "wall_ns": int(wall)}

    def diagnostic_probe(self, burst: Callable[[], None], cells: float) -> dict:
        self.first_probe = self.probe(burst, cells)
        return self.first_probe

    def clear(self, burst: Callable[[], None], cells: float) -> dict:
        """The warm-up rule: untimed bursts, at least ramp_window_s of
        sustained load, then a sustained probe that books the ramp factor."""
        t0 = self.clock()
        for _ in range(self.warmup_iters):
            burst()
        while (self.clock() - t0) < self.ramp_window_s * 1e9:
            burst()
        self.cleared = True
        self.sustained_probe = self.probe(burst, cells)
        if self.first_probe and self.sustained_probe["wall_ns"] > 0:
            self.ramp_factor = round(
                self.first_probe["wall_ns"] / self.sustained_probe["wall_ns"], 3)
        return self.sustained_probe

    def timed_repeats(self, burst: Callable[[], None], cells: float,
                      repeats: int = 3) -> dict:
        """Official timing. Refuses to stand behind numbers taken before the
        ramp is cleared (INCONCLUSIVE), and pins std==0 across repeats as a
        degenerate statistic (INCONCLUSIVE, verdict_gate doctrine)."""
        if repeats < 2:
            raise ValueError("repeats >= 2 required (variance of a single draw is undefined)")
        if not self.cleared:
            return {"timing_verdict": "INCONCLUSIVE",
                    "reason": "timing consumed before ramp cleared (INSTRUMENT-01)",
                    "ramp_cleared": False}
        rows = [self.probe(burst, cells) for _ in range(repeats)]
        cps = [r["cells_per_s"] for r in rows]
        std = statistics.stdev(cps)
        timing_verdict = "PASS" if std > 0 else "INCONCLUSIVE"
        reason = None if std > 0 else "std==0 across timing repeats (degenerate statistic)"
        return {"timing_verdict": timing_verdict, "reason": reason,
                "ramp_cleared": True,
                "cells_per_s_best": max(cps),
                "cells_per_s_std": std,
                "repeats": repeats,
                "ramp_factor": self.ramp_factor,
                "pre_ramp_cells_per_s": self.first_probe["cells_per_s"] if self.first_probe else None,
                "post_ramp_cells_per_s": self.sustained_probe["cells_per_s"] if self.sustained_probe else None}


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------
def compare(impl_a: Callable, impl_b: Callable, *,
            sizes: Tuple[int, ...] = DEFAULT_SIZES, mode: str = "BIT",
            tolerance: Optional[float] = None, steps: int = 10,
            repeats: int = 3, warmup_iters: int = 3, ramp_window_s: float = 0.5,
            seed: int = DEFAULT_SEED,
            clock: Optional[Callable[[], int]] = None,
            receipt_dir: Optional[str] = None,
            task_id: str = "parity") -> dict:
    """Run impl_a vs impl_b over sizes; parity + timing + ramp gate.

    Returns the receipt dict (schema parity-harness-receipt@1) with a single
    top-level "verdict": PASS only if every size parity-passes and every
    timing claim survived the ramp gate and the std-degeneracy pin.
    """
    if mode not in ("BIT", "TOL"):
        raise ParityHarnessError(f"mode must be BIT|TOL, got {mode!r}")
    if mode == "TOL" and tolerance is None:
        raise ParityHarnessError("TOL mode requires a frozen tolerance (set before the run)")
    if not sizes:
        raise ParityHarnessError("size grid is empty")
    if len(set(sizes)) != len(sizes):
        raise ParityHarnessError(f"size grid not pairwise-aligned: duplicates in {sizes}")

    rows: List[dict] = []
    overall = "PASS"
    for size in sizes:
        pa = np.asarray(impl_a(size=size, steps=steps, seed=seed))
        pb = np.asarray(impl_b(size=size, steps=steps, seed=seed))
        if pa.shape != pb.shape:  # pairwise alignment is a hard contract
            raise ParityHarnessError(
                f"size {size}: grid not pairwise-aligned {pa.shape} vs {pb.shape}")
        for name, arr in (("A", pa), ("B", pb)):
            if not np.issubdtype(arr.dtype, np.floating) or not np.isfinite(arr).all():
                row_kill = {"size": size, "parity_verdict": "KILL",
                            "reason": f"NaN/Inf in implementation {name}'s output"}
                rows.append(row_kill)
                _write_receipt(task_id, mode, tolerance, seed, sizes, steps,
                               repeats, rows, "KILL", receipt_dir)
                raise NonFiniteOutput(row_kill["reason"])
        csa, csb = checksum(pa), checksum(pb)
        diff = np.abs(pa.astype(np.float64) - pb.astype(np.float64))
        max_d = float(diff.max()) if diff.size else 0.0
        if mode == "BIT":
            parity_ok = (max_d == 0.0 and csa == csb)
        else:
            parity_ok = (max_d <= tolerance)
        pv = "PASS" if parity_ok else "KILL"

        # Timing under the ramp gate (impl_a is the timed runtime, like A5's
        # GPU runtime; the reference is host-side and untimed).
        gate = RampGate(warmup_iters=warmup_iters, ramp_window_s=ramp_window_s,
                        clock=clock)
        cells = float(size * size * steps)
        burst = lambda: impl_a(size=size, steps=steps, seed=seed)  # noqa: E731
        gate.diagnostic_probe(burst, cells)
        gate.clear(burst, cells)
        timing = gate.timed_repeats(burst, cells, repeats=repeats)

        row = {"size": size, "steps": steps, "mode": mode,
               "checksum_a": csa, "checksum_b": csb,
               "checksum_diff": abs(csa - csb),
               "max_abs_diff": max_d,
               "tolerance": tolerance,
               "parity_verdict": pv,
               "timing": timing}
        rows.append(row)
        if pv != "PASS":
            overall = "KILL"
        elif timing["timing_verdict"] != "PASS" and overall == "PASS":
            overall = "INCONCLUSIVE"

    receipt = _write_receipt(task_id, mode, tolerance, seed, sizes, steps,
                             repeats, rows, overall, receipt_dir)
    return receipt


def _write_receipt(task_id: str, mode: str, tolerance: Optional[float],
                   seed: int, sizes: Tuple[int, ...], steps: int,
                   repeats: int, rows: List[dict], verdict: str,
                   receipt_dir: Optional[str]) -> dict:
    receipt = {"schema": SCHEMA, "task_id": task_id, "seed": seed,
               "mode": mode, "tolerance_frozen_before_run": tolerance,
               "steps": steps, "timing_repeats": repeats,
               "size_grid": list(sizes),
               "ramp_law": RAMP_LAW,
               "degeneracy_pin": "std==0 across timing repeats => INCONCLUSIVE",
               "sizes": rows, "verdict": verdict}
    if receipt_dir:
        d = Path(receipt_dir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{task_id}-receipt.json"
        path.write_text(json.dumps(receipt, indent=2))
        receipt["receipt_path"] = str(path)
    return receipt


# --------------------------------------------------------------------------
# Synthetic timing source for the ramp self-test: simulates INSTRUMENT-01's
# 13x-slow first probes without sleeping.
# --------------------------------------------------------------------------
class _FakeClock:
    """Deterministic clock standing in for perf_counter_ns.

    Time advances only on burst boundaries (each timed probe = 2 clock
    reads; the first read of a pair starts a new burst). The first
    `slow_bursts` bursts cost `factor` x the fast cost; optional per-burst
    jitter keeps repeat statistics non-degenerate (jitter=False reproduces
    the std==0 degeneracy on demand).
    """

    def __init__(self, *, steps: int = 10, fast_ns: int = 1000, factor: float = 13.0,
                 slow_bursts: int = 1, jitter: bool = True):
        self.steps = steps
        self.fast_ns = fast_ns
        self.factor = factor
        self.slow_bursts = slow_bursts
        self.jitter = jitter
        self.t = 0
        self.calls = 0
        self.burst = -1

    def __call__(self) -> int:
        if self.calls % 2 == 0:
            self.burst += 1
            cost = self.fast_ns * (self.factor if self.burst < self.slow_bursts else 1.0)
            if self.jitter and self.burst >= self.slow_bursts:
                cost += self.burst % 5
            self.t += int(cost)
        self.calls += 1
        return self.t


def _noop_burst(steps: int = 10) -> Callable[[], None]:
    counter = {"i": 0}

    def burst() -> None:
        for _ in range(steps):
            counter["i"] += 1

    return burst


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------
def selftest() -> dict:
    base = Path(__file__).resolve().parent / "selftest_out"
    checks: Dict[str, bool] = {}
    receipts: Dict[str, str] = {}

    impl_a = make_impl(gather="roll")
    impl_a2 = make_impl(gather="slice")          # bit-identical port
    impl_b = make_impl(gather="roll", hot_weight=np.float32(0.59))  # divergent constant

    # 1. A vs A' (BIT) -> parity PASS at all sizes, checksums match exactly.
    sizes = (16, 512, 1024)
    r1 = compare(impl_a, impl_a2, sizes=sizes, mode="BIT", repeats=3,
                 warmup_iters=2, ramp_window_s=0.25, steps=10,
                 receipt_dir=str(base / "bitpass"), task_id="parity-bit-pass")
    receipts["bit_pass"] = r1.get("receipt_path", "")
    checks["bit_identical_pass_all_sizes"] = (
        r1["verdict"] == "PASS"
        and all(row["parity_verdict"] == "PASS" and row["max_abs_diff"] == 0.0
                and row["checksum_a"] == row["checksum_b"]
                and row["timing"]["timing_verdict"] == "PASS"
                for row in r1["sizes"]))

    # 2. A vs B (BIT) -> parity KILL with max|delta| booked + receipt on disk.
    r2 = compare(impl_a, impl_b, sizes=(16, 512), mode="BIT", repeats=3,
                 warmup_iters=2, ramp_window_s=0.25,
                 receipt_dir=str(base / "bitkill"), task_id="parity-bit-kill")
    receipts["bit_kill"] = r2.get("receipt_path", "")
    checks["divergent_impl_kill_booked"] = (
        r2["verdict"] == "KILL"
        and all(row["parity_verdict"] == "KILL" and row["max_abs_diff"] > 0.0
                for row in r2["sizes"])
        and Path(receipts["bit_kill"]).exists())

    # 2b. TOL mode with a frozen tolerance: B passes a loose gate, tolerance
    # recorded; TOL without tolerance raises (frozen-before-run contract).
    r_tol = compare(impl_a, impl_b, sizes=(16,), mode="TOL", tolerance=1.0,
                    repeats=2, warmup_iters=1, ramp_window_s=0.05,
                    task_id="parity-tol")
    checks["tol_mode_frozen_tolerance"] = (
        r_tol["verdict"] == "PASS" and r_tol["tolerance_frozen_before_run"] == 1.0)
    tol_raises = False
    try:
        compare(impl_a, impl_b, sizes=(16,), mode="TOL")
    except ParityHarnessError:
        tol_raises = True
    checks["tol_requires_frozen_tolerance"] = tol_raises

    # 3. Synthetic 13x ramp source: factor booked; INCONCLUSIVE before
    # clear, PASS after warmup.
    steps, sizes16 = 10, float(16 * 16 * 10)
    burst = _noop_burst(steps)
    clk = _FakeClock(steps=steps, fast_ns=1000, factor=13.0, slow_bursts=1)
    gate = RampGate(warmup_iters=2, ramp_window_s=0.0001, clock=clk)
    pre = gate.diagnostic_probe(burst, sizes16)
    early = gate.timed_repeats(burst, sizes16, repeats=3)
    checks["timing_inconclusive_before_ramp_clear"] = (
        early["timing_verdict"] == "INCONCLUSIVE" and "ramp" in early["reason"])
    gate.clear(burst, sizes16)
    late = gate.timed_repeats(burst, sizes16, repeats=3)
    checks["ramp_factor_booked_13x"] = (
        gate.ramp_factor is not None and 12.0 <= gate.ramp_factor <= 14.0
        and pre["cells_per_s"] < late["cells_per_s_best"])
    checks["timing_pass_after_warmup"] = late["timing_verdict"] == "PASS"

    # 4. std==0 across repeats -> INCONCLUSIVE (degenerate pin).
    clk0 = _FakeClock(steps=steps, fast_ns=1000, factor=13.0, slow_bursts=1,
                      jitter=False)
    gate0 = RampGate(warmup_iters=1, ramp_window_s=0.0001, clock=clk0)
    gate0.diagnostic_probe(burst, sizes16)
    gate0.clear(burst, sizes16)
    deg = gate0.timed_repeats(burst, sizes16, repeats=3)
    checks["std_zero_degenerate_inconclusive"] = (
        deg["timing_verdict"] == "INCONCLUSIVE" and "degenerate" in deg["reason"])

    # 5. Misaligned grid -> exception (fail loud).
    misaligned = False
    try:
        compare(impl_a, lambda size, steps=10, seed=2718: np.zeros((size, size + 1),
                 dtype=np.float32), sizes=(16,), repeats=2, warmup_iters=1,
                 ramp_window_s=0.05, task_id="parity-misalign")
    except ParityHarnessError:
        misaligned = True
    checks["misaligned_grid_raises"] = misaligned

    verdict = "PASS" if all(checks.values()) else "FAIL"
    return {"verdict": verdict, "checks": checks, "receipts": receipts,
            "sizes_tested": list(sizes)}


def main() -> int:
    try:
        result = selftest()
    except BaseException:
        result = {"verdict": "FAIL", "error": traceback.format_exc(limit=5)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
