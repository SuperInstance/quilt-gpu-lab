#!/usr/bin/env python3
"""path1_schedule_census.py — PATH-1 knob history-dependence census (SCOUT-101 spawn).

Two-arm schedule census: RAMP (full THRESH-2 ladder in order, endpoint captured at
the final rung, all inside ONE fresh interpreter) vs DIRECT (endpoint only). If the
endpoint payload depends on the schedule, the knob is PATH-DEPENDENT (G3) and the
booked THRESH-2 single-step grades are schedule-conditional.

Gates frozen in proposals/runs/PATH-1-knob-history-dependence-prereg-2026-10-11.md.
CPU-only; determ1 arm graded SOFT (torch run-to-run class) with DIRECT-vs-DIRECT control.
--out with refuse-overwrite (exit 3) per the RC-1 rule. Never echoes secrets.
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
PREREG = "proposals/runs/PATH-1-knob-history-dependence-prereg-2026-10-11.md"

LADDERS = {
    "determ1 eps": ["1e-1", "1e-2", "1e-3", "1e-4", "1e-5"],
    "eproc sigma": ["0.1", "0.25", "0.5", "0.75", "1.0"],
    "degrade_gate tolerance": ["0.0", "0.25", "0.5", "0.75", "1.0"],
    "verdict_gate minimum": ["0.80", "0.85", "0.875", "0.90", "0.95"],
}
ENDPOINT = {"determ1 eps": "1e-3", "eproc sigma": "0.5",
            "degrade_gate tolerance": "0.5", "verdict_gate minimum": "0.875"}


def norm(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---- knob payload emitters (in-process; called per setting inside one arm) ----

def payload_determ1(setting: str, tag: str) -> dict:
    out = REPO / f"results/determ1_lattice_snap/B-{tag}.json"
    p = subprocess.run([PY, "experiments/determ1_lattice_snap.py", "B", setting, tag],
                       cwd=REPO, capture_output=True, text=True, timeout=300)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"determ1 rc={p.returncode} {p.stderr[-300:]}")
    rec = json.loads(out.read_text())
    rec.pop("wall_s", None)
    return rec


def payload_eproc(setting: str, tag: str) -> dict:
    import math
    sys.path.insert(0, str(REPO))
    from tools.eproc import eprocess
    d = [0.3 * math.sin(i * 0.7) + (i % 5) * 0.05 for i in range(64)]  # pinned THRESH-2 series
    r = eprocess(d, float(setting))
    return {"E": [float(x) for x in r["E"]]}


def payload_degrade(setting: str, tag: str) -> dict:
    sweep = json.dumps([
        {"param": 70, "benefit": 12.25},
        {"param": 60, "benefit": 10.1},
        {"param": 52, "benefit": 6.3},
        {"param": 45, "benefit": 4.0},
        {"param": 40, "benefit": 4.5},
    ])
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"dg_{tag}.json"
        p = subprocess.run([PY, "tools/degrade_gate.py", "--sweep", sweep,
                            "--tolerance", setting, "--out", str(out)],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        if p.returncode not in (0, 1) or not out.exists():
            raise RuntimeError(f"degrade rc={p.returncode} {p.stderr[-300:]}")
        return json.loads(out.read_text())


def payload_verdict(setting: str, tag: str) -> dict:
    sys.path.insert(0, str(REPO))
    from tools.verdict_gate import finalize, Gate, StatMeta
    v = finalize(gates=[Gate("x", value=0.91, minimum=float(setting))],
                 stats={"x": StatMeta(std=0.03, n=32)},
                 completeness=True, status_source="own")
    return {"verdict": v.verdict}


PAYLOADS = {"determ1 eps": payload_determ1, "eproc sigma": payload_eproc,
            "degrade_gate tolerance": payload_degrade, "verdict_gate minimum": payload_verdict}


def run_arm(knob: str, arm: str) -> dict:
    """Driver: execute the arm's schedule INSIDE this fresh interpreter; emit endpoint digest."""
    ladder = LADDERS[knob]
    seq = ladder if arm == "RAMP" else [ENDPOINT[knob]]
    digs = {}
    for i, s in enumerate(seq):
        tag = f"path1_{arm}_{i}_{s}"
        digs[s] = norm(PAYLOADS[knob](s, tag))
    return {"knob": knob, "arm": arm, "schedule": seq,
            "endpoint": ENDPOINT[knob], "endpoint_digest": digs[ENDPOINT[knob]],
            "rung_digests": digs}


# ---- G2 anchors: THRESH-2 grade classes reproduce (cite fd25a5c) ----

def g2_anchors() -> dict:
    a = {}
    d = run_arm("eproc sigma", "DIRECT")
    sys.path.insert(0, str(REPO))
    from tools.eproc import eprocess
    try:
        eprocess([0.1], 0.0)
        a["eproc_sigma0_refuses"] = False
    except ValueError:
        a["eproc_sigma0_refuses"] = True
    rungs = len(set(d["rung_digests"].values()))
    a["eproc_grade_continues"] = rungs == 5
    v = run_arm("verdict_gate minimum", "DIRECT")
    a["verdict_coarse"] = (len(set(v["rung_digests"].values())) == 2
                           and v["rung_digests"]["0.80"] == norm({"verdict": "PASS"})
                           and v["rung_digests"]["0.95"] == norm({"verdict": "FAIL"}))
    dg = run_arm("degrade_gate tolerance", "DIRECT")
    a["degrade_coarse"] = (len(set(dg["rung_digests"].values())) == 2
                           and dg["rung_digests"]["0.0"] != dg["rung_digests"]["1.0"])
    a["ok"] = all([a["eproc_sigma0_refuses"], a["eproc_grade_continues"],
                   a["verdict_coarse"], a["degrade_coarse"]])
    return a


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["RAMP", "DIRECT"])  # driver mode (fresh interpreter)
    ap.add_argument("--knob")
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.arm and args.knob:
        print(json.dumps(run_arm(args.knob, args.arm)))
        return

    rows, reds = [], []
    for knob in LADDERS:
        arms = {}
        for arm in ("RAMP", "DIRECT"):
            p = subprocess.run([PY, __file__, "--arm", arm, "--knob", knob],
                               cwd=REPO, capture_output=True, text=True, timeout=600)
            if p.returncode != 0:
                rows.append({"knob": knob, "ok": False, "why": f"{arm} rc={p.returncode} {p.stderr[-300:]}"})
                reds.append(f"RUN:{knob}:{arm}")
                break
            arms[arm] = json.loads(p.stdout.strip().splitlines()[-1])
        if len(arms) < 2:
            continue
        same = arms["RAMP"]["endpoint_digest"] == arms["DIRECT"]["endpoint_digest"]
        row = {"knob": knob, "ok": True, "path_independent": same,
               "endpoint": arms["RAMP"]["endpoint"],
               "digest_ramp": arms["RAMP"]["endpoint_digest"],
               "digest_direct": arms["DIRECT"]["endpoint_digest"]}
        if not same:
            if knob == "determ1 eps":
                # SOFT disambiguation: DIRECT-vs-DIRECT control (nondeterminism vs history)
                c = [subprocess.run([PY, __file__, "--arm", "DIRECT", "--knob", knob],
                                    cwd=REPO, capture_output=True, text=True, timeout=600) for _ in range(2)]
                ok = all(x.returncode == 0 for x in c)
                dd = [json.loads(x.stdout.strip().splitlines()[-1])["endpoint_digest"] for x in c] if ok else None
                row["control_direct_vs_direct"] = dd
                row["grade"] = ("PATH-DEPENDENT-SOFT" if (dd and len(set(dd)) > 1) else "TBD-CONTROL")
                if not (dd and len(set(dd)) > 1):
                    reds.append(f"PATH:{knob}")
            else:
                row["grade"] = "PATH-DEPENDENT"
                reds.append(f"PATH:{knob}")
        else:
            row["grade"] = "PATH-INDEPENDENT"
        rows.append(row)

    anchors = g2_anchors()
    if not anchors["ok"]:
        reds.append("ANCHOR:G2")
    census = {"tool": "path1_schedule_census", "prereg": PREREG, "rows": rows,
              "g2_anchors": anchors, "n_knobs": len(rows),
              "reds": reds, "verdict": "GREEN" if not reds else "RED"}
    census["census_digest"] = norm({k: v for k, v in census.items()})
    text = json.dumps(census, indent=2, sort_keys=True)
    if args.out:
        op = Path(args.out)
        if op.exists() and not args.force:
            print(json.dumps({"verdict": "REFUSED-OVERWRITE", "why": f"{op} exists; --force"}))
            sys.exit(3)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(text + "\n")
    print(text)
    sys.exit(0 if census["verdict"] == "GREEN" else 1)


if __name__ == "__main__":
    main()
