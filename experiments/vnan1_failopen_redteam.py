"""VNaN-1 — fail-open red-team of numeric/enum verdict surfaces (pre-reg: proposals/runs/VNaN-1-failopen-redteam.md).

Injects NaN/inf/string/None/empty into every enumerated field of
verdict_gate.finalize / eproc.witness / prereg_seal and records each outcome as
REFUSE (loud), LATTICE (non-PASS verdict — also safe), ALLOWED (documented
allowlist), or RED (silent accept / PASS-equivalent that honest input wouldn't yield).

Exit 0 iff no RED.
"""
import io
import math
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import eproc as EP  # noqa: E402
from tools import verdict_gate as VG  # noqa: E402

NAN = float("nan")
INF = float("inf")
NINF = float("-inf")

INJECTIONS_NUM = [NAN, INF, NINF, "NaN", "nan", None, ""]
INJECTIONS_ENUM = ["", "Own", "own ", None]

HONEST_EPS = [0.02, 0.005, 0.01, 0.03, 0.0, 0.01, -0.01, 0.02, 0.01, 0.04, 0.0, 0.02]

results = []  # (surface, field, injection, outcome, detail)


ALLOWLIST = {
    ("verdict_gate", "maximum", "None"): "optional upper bound by design; PARAM-1a fails only when BOTH bounds are None",
    ("verdict_gate", "std", "None"): "docstring pin: std=None means variance UNKNOWN, treated as unknown not degenerate",
    ("verdict_gate", "saturated", "None"): "optional saturation attestation by design (absence is not a false claim)",
}


def record(surface, field, inj, outcome, detail=""):
    if outcome == "RED" and (surface, field, repr(inj)) in ALLOWLIST:
        outcome, detail = "ALLOWED", ALLOWLIST[(surface, field, repr(inj))]
    results.append((surface, field, repr(inj), outcome, detail))


def attempt(fn, surface, field, inj):
    """Run one injection; only classify an unexpected crash as REFUSE here.
    (go() records its own outcome for non-raising paths — no double record.)"""
    try:
        fn()
    except (ValueError, TypeError, KeyError, AssertionError) as e:
        record(surface, field, inj, "REFUSE", f"{type(e).__name__}: {e}")
        return
    except Exception as e:  # noqa: BLE001
        record(surface, field, inj, "REFUSE", f"{type(e).__name__}: {e}")


# ---------------- Surface 1: verdict_gate ----------------

def vg_outcome(gate_kwargs, stats_kwargs, completeness, status_source):
    g = VG.Gate(**gate_kwargs)
    m = VG.StatMeta(**stats_kwargs)
    v = VG.finalize(gates=[g], stats={"g": m}, completeness=completeness,
                    status_source=status_source)
    return v.verdict


def redteam_verdict_gate():
    # G1 inventory: value, minimum, maximum, std, n, saturated, completeness, status_source
    for field in ("value", "minimum", "maximum"):
        for inj in INJECTIONS_NUM:
            def go(inj=inj, field=field):
                kw = dict(name="g", value=0.9, minimum=0.8, maximum=None)
                kw[field] = inj
                skw = dict(std=0.03, n=8)
                out = vg_outcome(kw, skw, True, "own")
                # gate is evaluated at call: capture verdict rather than raising
                record("verdict_gate", field, inj,
                       "LATTICE" if out != "PASS" else "RED", f"verdict={out}")
            attempt(lambda: go(), "verdict_gate", field, inj)
    for field in ("std", "n", "saturated"):
        for inj in INJECTIONS_NUM:
            def go(inj=inj, field=field):
                gkw = dict(name="g", value=0.9, minimum=0.8)
                skw = dict(std=0.03, n=8)
                skw[field] = inj
                out = vg_outcome(gkw, skw, True, "own")
                record("verdict_gate", field, inj,
                       "LATTICE" if out != "PASS" else "RED", f"verdict={out}")
            attempt(lambda: go(), "verdict_gate", field, inj)
    for field in ("completeness", "status_source"):
        for inj in INJECTIONS_ENUM:
            def go(inj=inj, field=field):
                kw = dict(name="g", value=0.9, minimum=0.8)
                skw = dict(std=0.03, n=8)
                comp, ss = (inj, "own") if field == "completeness" else (True, inj)
                out = vg_outcome(kw, skw, comp, ss)
                record("verdict_gate", field, inj,
                       "LATTICE" if out != "PASS" else "RED", f"verdict={out}")
            attempt(lambda: go(), "verdict_gate", field, inj)


# ---------------- Surface 2: eproc ----------------

def redteam_eproc():
    for field in ("series", "sigma", "delta", "claim"):
        for inj in (INJECTIONS_NUM if field != "claim" else INJECTIONS_ENUM):
            def go(inj=inj, field=field):
                series, sigma, delta, claim = list(HONEST_EPS), 0.02, 0.05, "DECREASES"
                if field == "series":
                    series = [inj] * len(series)
                elif field == "sigma":
                    sigma = inj
                elif field == "delta":
                    delta = inj
                else:
                    claim = inj
                out = EP.witness(series, claim=claim, sigma=sigma, delta=delta)
                record("eproc", field, inj,
                       "LATTICE" if out["verdict"] != "WITNESSED" else "RED",
                       f"verdict={out['verdict']}")
            attempt(lambda: go(), "eproc", field, inj)


# ---------------- Surface 3: prereg_seal (env secret) ----------------

def redteam_prereg_seal():
    import subprocess
    import tempfile
    probe = Path(tempfile.mkdtemp()) / "probe.txt"
    probe.write_text("vnan1 probe\n")
    env_cases = [("", "empty"), ("   ", "whitespace")]
    for secret, label in env_cases:
        r = subprocess.run(
            [sys.executable, "tools/prereg_seal.py", "seal", str(probe)],
            capture_output=True, text=True, timeout=30,
            env={"PATH": "/usr/bin:/bin", "PREREG_SEAL_SECRET": secret},
        )
        if r.returncode != 0 and "REFUSE" in (r.stderr + r.stdout):
            record("prereg_seal", "PREREG_SEAL_SECRET", label, "REFUSE", r.stderr.strip())
        else:
            record("prereg_seal", "PREREG_SEAL_SECRET", label, "RED", r.stdout.strip())


def report_and_gate():
    print(f"{'surface':12s} {'field':22s} {'injection':10s} {'outcome':8s} detail")
    red = 0
    for s, f, i, o, d in results:
        print(f"{s:12s} {f:22s} {i:10s} {o:8s} {d}")
        if o == "RED":
            red += 1
    print(f"\nTOTAL={len(results)} RED={red} REFUSE={sum(1 for r in results if r[3]=='REFUSE')} "
          f"LATTICE={sum(1 for r in results if r[3]=='LATTICE')} ALLOWED={sum(1 for r in results if r[3]=='ALLOWED')}")
    # G3 explicit unit pin: NaN construction must now REFUSE loudly (the a2a lesson, fixed)
    try:
        VG.Gate("g", value=NAN, minimum=0.8)
        print("G3-UNIT RED: Gate(value=nan) constructed without refusal")
        red += 1
    except ValueError as e:
        print(f"G3-UNIT OK: Gate(value=nan) refuses loudly ({e})")
    return red


if __name__ == "__main__":
    redteam_verdict_gate()
    redteam_eproc()
    redteam_prereg_seal()
    red = report_and_gate()
    sys.exit(1 if red else 0)
