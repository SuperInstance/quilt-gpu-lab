#!/usr/bin/env python3
"""thresh1_trace_divergence.py — THRESH-1 census (q32 vacuous-knob class).

For each parameterized instrument in the live stack, execute two adjacent
parameter settings on a PINNED input and check that the trace/output differs.
A knob with no witnessable divergence = RED (q32 shape: parameter decoration).

Gates frozen in proposals/runs/THRESH-1-trace-divergence-census-prereg-2026-10-10.md
(G1 runnability, G2 divergence, G3 vacuous=>RED, G4 determinism).

CPU-only, stdlib+numpy (eproc), deterministic. Never echoes secrets.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
RC_OK, RC_RED, RC_INPUT, RC_EXISTS = 0, 1, 2, 3


def digest_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(obj) -> str:
    """Canonical digest of a JSON-serializable object (sorted keys)."""
    return digest_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------- K1: determ1 eps (subprocess, scratch outputs) ----------------
def k1_determ1() -> dict:
    digs = {}
    for eps, tag in (("1e-2", "thresh1_eps1e-2"), ("1e-4", "thresh1_eps1e-4")):
        rc, so = run([PY, "experiments/determ1_lattice_snap.py", "B", eps, tag])
        out = REPO / f"results/determ1_lattice_snap/B-{tag}.json"
        if rc != 0 or not out.exists():
            return {"knob": "determ1 eps", "ok": False, "why": f"rc={rc} {so[-400:]}"}
            # strip wall-clock field before digest (wall_s is nondeterministic
            # bookkeeping, not trace); compare the physics payload only.
            rec = json.loads(out.read_text())
            rec.pop("wall_s", None)
            digs[eps] = norm(rec)
    return {"knob": "determ1 eps", "ok": True,
            "settings": digs, "diverges": digs["1e-2"] != digs["1e-4"]}


# ---------------- K2: eproc sigma (in-process, pinned series) ----------------
def k2_eproc() -> dict:
    sys.path.insert(0, str(REPO))
    import math
    from tools.eproc import eprocess
    d = [0.3 * math.sin(i * 0.7) + (i % 5) * 0.05 for i in range(64)]  # pinned
    digs = {}
    for sigma in (0.5, 0.75):
        r = eprocess(d, sigma)
        digs[str(sigma)] = norm([float(x) for x in r["E"]])
    return {"knob": "eproc sigma", "ok": True, "settings": digs,
            "diverges": digs["0.5"] != digs["0.75"]}


# ---------------- K3: degrade_gate tolerance (subprocess, pinned sweep) ----------------
def k3_degrade() -> dict:
    sweep = json.dumps([
        {"param": 70, "benefit": 12.25},
        {"param": 60, "benefit": 10.1},
        {"param": 52, "benefit": 6.3},
        {"param": 45, "benefit": 4.0},
        {"param": 40, "benefit": 4.5},  # small positive delta: tolerance-witnessing step
    ])
    digs, verdicts = {}, {}
    with tempfile.TemporaryDirectory() as td:
        for tol in ("0.0", "1.0"):
            out = Path(td) / f"dg_{tol}.json"
            rc, so = run([PY, "tools/degrade_gate.py", "--sweep", sweep,
                          "--tolerance", tol, "--out", str(out)])
            if rc not in (0, 1) or not out.exists():
                return {"knob": "degrade_gate tolerance", "ok": False,
                        "why": f"rc={rc} {so[-400:]}"}
            r = json.loads(out.read_text())
            verdicts[tol] = r.get("verdict")
            digs[tol] = digest_bytes(out.read_bytes())
    return {"knob": "degrade_gate tolerance", "ok": True, "settings": digs,
            "verdicts": verdicts, "diverges": digs["0.0"] != digs["1.0"]}


# ---------------- K4: verdict_gate bounds (in-process, pinned) ----------------
def k4_verdict() -> dict:
    from tools.verdict_gate import finalize, Gate, StatMeta
    digs = {}
    for mn in (0.80, 0.95):
        v = finalize(gates=[Gate("x", value=0.91, minimum=mn)],
                     stats={"x": StatMeta(std=0.03, n=32)},
                     completeness=True, status_source="own")
        digs[str(mn)] = v.verdict
    return {"knob": "verdict_gate minimum", "ok": True, "settings": digs,
            "diverges": digs["0.8"] != digs["0.95"]}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write census JSON here")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else None
    if out_path and out_path.exists() and not args.force:
        print(json.dumps({"verdict": "REFUSED-OVERWRITE",
                          "why": f"{out_path} exists; --force to override"}))
        sys.exit(RC_EXISTS)

    rows = []
    for fn in (k1_determ1, k2_eproc, k3_degrade, k4_verdict):
        try:
            rows.append(fn())
        except Exception as e:  # fail-loud per-row, census continues
            rows.append({"knob": fn.__name__, "ok": False, "why": f"EXC {e!r}"})

    runnable = [r for r in rows if r["ok"]]
    reds = [r["knob"] for r in rows if (not r["ok"]) or (not r.get("diverges"))]
    census = {
        "tool": "thresh1_trace_divergence",
        "prereg": "proposals/runs/THRESH-1-trace-divergence-census-prereg-2026-10-10.md",
        "rows": rows,
        "n_knobs": len(rows),
        "n_runnable": len(runnable),
        "n_witnessed": sum(1 for r in runnable if r["diverges"]),
        "reds": reds,
        "verdict": "GREEN" if not reds else "RED",
    }
    # G4: in-process determinism — rebuild the census payload digest excluding
    # nothing (all rows are deterministic); self-consistency is the re-run.
    census["census_digest"] = norm({k: v for k, v in census.items()})
    text = json.dumps(census, indent=2, sort_keys=True)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n")
    print(text)
    sys.exit(RC_OK if census["verdict"] == "GREEN" else RC_RED)


if __name__ == "__main__":
    main()
