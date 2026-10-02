#!/usr/bin/env python3
"""port_harness — dual-implementation equivalence harness (standalone block).

Harvested from the proven B1-DISTILL engine-port control (RESULTS.md B1-DISTILL
entry, 2026-10-01). The distillation itself KILLed its 1e-3 gate; what survived
and is harvested here is the VERIFICATION MACHINERY that proved the JS engine
port behaviorally equivalent to the torch model BEFORE any gate ran
(js_vs_torch_port_max_abs_diff = [7.15e-07, 6.28e-07] <= 7.2e-07).

Booked defect that became this block's central law (B1-DISTILL controls.json,
defect_1): the FIRST port control ran MIXED-SIDE rows — row i from JS paired
against row j from torch — and measured 0.162 agreement, a phantom bug / false
FAIL. Fixed to PER-SIDE rows: each implementation computes BOTH sides of the
same symmetric comparison and rows are compared side-by-side. Lesson encoded
here: a port harness must align inputs per-side, per-row, with the pairing
explicit, or it measures shuffle noise.

Environment: python 3.14 + numpy (reference side), node v22 (port side),
stdlib otherwise. NO torch, NO GPU. The subprocess is spawned list-form;
shell=True is never used anywhere in this block.

House contracts baked in: seed 2718 default · single JSON verdict on the final
stdout line · fail loud · list-form subprocess only · std==0 across repeats ->
INCONCLUSIVE (multi-seed gate stats) · no secrets are read, printed, or copied.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
JS_PORT = HERE / "port_ref.js"          # carried port artifact
DEFAULT_SEED = 2718                     # house seed
DEFAULT_TOL = 1e-6                      # the 7.2e-07 receipt class

# ── pong derived law constants (shipped quilt-arcade games/pong ai.track,
#    reproduced verbatim in experiments/b1_pong_law_engine.mjs TRACK_SWITCH) ──
LAW = {"speed_left": 0.85, "speed_right": 0.70, "dead": 1.5, "clamp": (6.0, 54.0)}
FIELD_H = 60.0


# ── (1) paired-case generator ────────────────────────────────────────────────
@dataclass(frozen=True)
class PairedCaseSpec:
    """Input ranges and the side set for a symmetric paired comparison.

    Each generated row carries the SHARED state plus BOTH sides, so both
    implementations must compute every (row, side) pair themselves. The pairing
    is explicit in the row; nothing is aligned by list order downstream.
    """

    input_ranges: dict          # name -> (lo, hi) uniform float range
    sides: tuple = ("left", "right")


@dataclass(frozen=True)
class PairedCase:
    row_id: int
    state: dict                 # shared inputs, identical for every side
    sides: tuple                # the sides this row must be evaluated on


def generate_paired_cases(spec: PairedCaseSpec, n: int, seed: int = DEFAULT_SEED):
    """Seeded per-side paired rows: row i carries the shared state AND both
    sides of the symmetric comparison (the B1 mixed-side defect fix)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        state = {k: float(rng.uniform(lo, hi)) for k, (lo, hi) in spec.input_ranges.items()}
        rows.append(PairedCase(row_id=i, state=state, sides=spec.sides))
    return rows


# ── (2) runner protocol ──────────────────────────────────────────────────────
# A runner takes the SAME paired rows and returns {(row_id, side): output} for
# the rows it was given — keyed, never positionally aligned.
class Runner:
    name = "runner"

    def run(self, cases) -> dict:  # -> {(row_id, side): float}
        raise NotImplementedError

    def metadata(self) -> dict:
        return {"runner": self.name}


def pong_law_numpy(p, b, side, dead: float = LAW["dead"]):
    """Reference law, vectorised, float64 end to end (precision contract:
    no float32 anywhere; see port_ref.js header)."""
    p = np.asarray(p, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    speed = np.where(np.asarray(side) == "left", LAW["speed_left"], LAW["speed_right"])
    d = np.abs(b - p)
    step = np.sign(b - p) * np.minimum(speed, d - dead)
    y = p + np.where(d > dead, step, 0.0)
    lo, hi = LAW["clamp"]
    return np.clip(y, lo, hi)


class NumpyPongRunner(Runner):
    """REFERENCE side: numpy implementation of the pong derived law."""

    name = "numpy_reference"

    def run(self, cases) -> dict:
        out = {}
        for c in cases:
            for s in c.sides:
                out[(c.row_id, s)] = float(pong_law_numpy(c.state["p"], c.state["b"], s))
        return out

    def metadata(self) -> dict:
        return {"runner": self.name, "impl": "numpy float64",
                "numpy": np.__version__, "python": platform.python_version()}


class JsPongPortRunner(Runner):
    """PORT side: the JS port in a persistent node child (list-form spawn,
    JSON-lines protocol, shell=True never used). The same rows go down the
    same pipe; the child computes every (row, side) pair and results come back
    keyed by (row_id, side)."""

    name = "js_port"

    def __init__(self, js_path=JS_PORT, bug=None, node="node", timeout_s=30.0):
        self.js_path = Path(js_path)
        if not self.js_path.exists():
            raise FileNotFoundError(f"FAIL LOUD: port artifact missing: {self.js_path}")
        self._bug = bug
        env = dict(os.environ)
        if bug:
            env["PORT_HARNESS_BUG"] = bug
        self.proc = subprocess.Popen(
            [node, str(self.js_path)], cwd=str(self.js_path.parent),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
        )
        self.timeout_s = timeout_s

    def _roundtrip(self, msg) -> dict:
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        except (BrokenPipeError, OSError) as e:
            raise RuntimeError(f"FAIL LOUD: port child died: "
                               f"{self.proc.stderr.read()[-2000:]}") from e
        if not line:
            raise RuntimeError("FAIL LOUD: port child produced no output: "
                               + self.proc.stderr.read()[-2000:])
        r = json.loads(line)
        if not r.get("ok"):
            raise RuntimeError(f"FAIL LOUD: port error on {msg.get('cmd')}: {r.get('error')}")
        return r

    def run(self, cases) -> dict:
        payload = [{"row_id": c.row_id, "p": c.state["p"], "b": c.state["b"], "side": s}
                   for c in cases for s in c.sides]
        r = self._roundtrip({"cmd": "eval", "cases": payload})
        out = {}
        for item in r["results"]:
            out[(int(item["row_id"]), item["side"])] = float(item["y"])
        return out

    def close(self):
        try:
            self._roundtrip({"cmd": "quit"})
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def metadata(self) -> dict:
        digest = hashlib.sha256(self.js_path.read_bytes()).hexdigest()
        try:
            node_v = subprocess.run(["node", "--version"], capture_output=True,
                                    text=True, timeout=10).stdout.strip()
        except Exception:
            node_v = "unknown"
        return {"runner": self.name, "impl": "javascript float64 (node child)",
                "artifact": self.js_path.name, "artifact_sha256": digest,
                "node": node_v, "bug_injected": bool(self._bug)}


# ── (3) comparator: align by (row_id, side), NEVER by list order alone ──────
@dataclass
class ComparatorReport:
    n_rows: int
    n_points: int
    max_abs_diff: float
    mean_abs_diff: float
    exact_match_rate: float
    first_divergent: dict | None = field(default=None)   # {row_id, side, reference, port, abs_diff}

    def to_dict(self):
        return {"n_rows": self.n_rows, "n_points": self.n_points,
                "max_abs_diff": self.max_abs_diff, "mean_abs_diff": self.mean_abs_diff,
                "exact_match_rate": self.exact_match_rate,
                "first_divergent": self.first_divergent}


def compare(reference: dict, port: dict, tol_hint: float | None = None) -> ComparatorReport:
    """Align the two output maps by (row_id, side) key. Missing or extra keys
    on either side are a fail-loud protocol breach, not a silent reshuffle."""
    rk, pk = set(reference), set(port)
    if rk != pk:
        missing, extra = sorted(rk - pk), sorted(pk - rk)
        raise RuntimeError(f"FAIL LOUD: runner output keys do not align by (row_id, side); "
                           f"missing_in_port={missing[:4]} extra_in_port={extra[:4]} "
                           f"— this is exactly the B1 mixed-side defect class")
    keys = sorted(rk)  # explicit (row_id, side) ordering; insertion order ignored
    diffs = np.array([abs(reference[k] - port[k]) for k in keys], dtype=np.float64)
    first = None
    for k, d in zip(keys, diffs):
        if d > 0.0:
            first = {"row_id": k[0], "side": k[1],
                     "reference": reference[k], "port": port[k], "abs_diff": float(d)}
            break
    return ComparatorReport(
        n_rows=len({k[0] for k in keys}), n_points=len(keys),
        max_abs_diff=float(diffs.max()) if len(diffs) else 0.0,
        mean_abs_diff=float(diffs.mean()) if len(diffs) else 0.0,
        exact_match_rate=float((diffs == 0.0).mean()) if len(diffs) else 1.0,
        first_divergent=first,
    )


# ── (4) frozen-tolerance gate ────────────────────────────────────────────────
class FrozenToleranceGate:
    """PASS iff max_abs_diff <= tol. The bar is FIXED at construction, before
    any output is seen; a missing tol fails loud rather than defaulting
    silently mid-run."""

    def __init__(self, tol: float | None = DEFAULT_TOL):
        if tol is None:
            raise ValueError("FAIL LOUD: gate tolerance must be fixed before the run")
        self.tol = float(tol)

    def adjudicate(self, report: ComparatorReport) -> str:
        return "PASS" if report.max_abs_diff <= self.tol else "KILL"

    def multi_seed_stats(self, per_seed_max_abs_diff: list[float]) -> dict:
        """House law: std==0 across repeats -> INCONCLUSIVE, never PASS. Applies
        to the port's per-seed gate stats when a port is verified over multiple
        input-generation seeds."""
        vals = np.asarray(per_seed_max_abs_diff, dtype=np.float64)
        std = float(vals.std()) if len(vals) else 0.0
        mean = float(vals.mean()) if len(vals) else 0.0
        if len(vals) < 2 or std == 0.0:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "PASS" if mean <= self.tol else "KILL"
        return {"per_seed_max_abs_diff": [float(v) for v in vals], "mean": mean,
                "std": std, "tol": self.tol, "verdict": verdict}


# ── (5) honest booking ───────────────────────────────────────────────────────
def run_metadata(reference: Runner, port: Runner, spec, seed: int, n: int,
                 tol: float) -> dict:
    """Runner versions/digests are cheap (one sha256, one --version): book them."""
    return {"seed": seed, "n_rows": n, "tol": tol,
            "spec": {"input_ranges": spec.input_ranges, "sides": list(spec.sides)},
            "reference": reference.metadata(), "port": port.metadata()}


# ── self-test ────────────────────────────────────────────────────────────────
def self_test() -> int:
    spec = PairedCaseSpec(input_ranges={"p": LAW["clamp"], "b": (0.0, FIELD_H)})
    gate = FrozenToleranceGate(DEFAULT_TOL)  # frozen before any comparison
    booking = {"block": "port_harness", "precision_contract": "both sides float64",
               "receipt_class": "js_vs_torch_port_max_abs_diff [7.15e-07, 6.28e-07] "
                                "<= 7.2e-07 (RESULTS.md B1-DISTILL entry, 2026-10-01)",
               "defect_lesson": "align per-side, per-row, pairing explicit "
                                "(mixed-side first attempt measured 0.162, a false FAIL)"}

    # (a) reference vs correct port over ~2000 seeded paired rows
    N = 2000
    cases = generate_paired_cases(spec, N, seed=DEFAULT_SEED)
    ref = NumpyPongRunner()
    ref_out = ref.run(cases)
    with JsPongPortRunner() as good:
        good_out = good.run(cases)
        booking["run"] = run_metadata(ref, good, spec, DEFAULT_SEED, N, gate.tol)
    report = compare(ref_out, good_out)
    verdict_a = gate.adjudicate(report)

    # lesson encoded as a check: shuffling the port's dict insertion order must
    # not change the report — alignment is by (row_id, side), not list order
    import random
    shuffled = dict(random.Random(DEFAULT_SEED).sample(
        sorted(good_out.items(), key=lambda kv: kv[0]), len(good_out)))
    report_shuffled = compare(ref_out, shuffled)
    order_invariant = (report_shuffled.max_abs_diff == report.max_abs_diff
                       and report_shuffled.first_divergent == report.first_divergent)

    # multi-seed stats (house law demo): per-seed input seeds -> per-seed diffs;
    # an exact float64 port gives std==0 -> INCONCLUSIVE, booked honestly
    per_seed = []
    for s in (DEFAULT_SEED, DEFAULT_SEED + 1, DEFAULT_SEED + 2):
        cs = generate_paired_cases(spec, 400, seed=s)
        with JsPongPortRunner() as pr:
            per_seed.append(compare(ref.run(cs), pr.run(cs)).max_abs_diff)
    multi = gate.multi_seed_stats(per_seed)

    # (b) reference vs deliberately-bugged port (deadzone halved): the HARNESS
    # is the unit under test — it must detect the bug, name the first divergent
    # (row, side) with values, and the gate must return KILL for that port.
    with JsPongPortRunner(bug="deadzone_halved") as buggy:
        buggy_out = buggy.run(cases)
    report_bug = compare(ref_out, buggy_out)
    verdict_b = gate.adjudicate(report_bug)
    harness_detected_buggy_port = bool(
        verdict_b == "KILL" and report_bug.first_divergent is not None
        and report_bug.max_abs_diff > gate.tol)

    checks = {"correct_port_gate": verdict_a,
              "correct_port_max_abs_diff": report.max_abs_diff,
              "buggy_port_gate": verdict_b,
              "buggy_port_max_abs_diff": report_bug.max_abs_diff,
              "buggy_port_first_divergent": report_bug.first_divergent,
              "harness_detected_buggy_port": harness_detected_buggy_port,
              "comparator_order_invariant": order_invariant,
              "multi_seed_gate_stats": multi}
    booking["checks"] = checks
    print("HARNESS " + json.dumps(booking, sort_keys=True), flush=True)

    # The single printed verdict adjudicates the HARNESS (a)+(b)+(invariants),
    # not the buggy port — the buggy port's KILL is the expected, asserted
    # outcome proving detection works.
    ok = (verdict_a == "PASS"
          and harness_detected_buggy_port
          and order_invariant
          and multi["verdict"] == "INCONCLUSIVE")
    final = "PASS" if ok else "FAIL"
    print(json.dumps({"verdict": final}), flush=True)   # exactly one top-level field
    return 0 if final == "PASS" else 1


if __name__ == "__main__":
    sys.exit(self_test())
