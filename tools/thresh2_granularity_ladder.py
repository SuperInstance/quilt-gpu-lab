#!/usr/bin/env python3
"""thresh2_granularity_ladder.py — THRESH-2 census (SCOUT-99 spawn, q33/q34).

Extends THRESH-1's 2-setting divergence probe to a 5-rung granularity ladder per
censused knob. Grades each knob CONTINUOUS / LADDERED / COARSE / MONOLITHIC by
counting DISTINCT payload rungs; flags MONOLITHIC as RED (q32 vacuous-knob class).
Endpoint anchors must reproduce THRESH-1's booked behavior (G2). Non-monotone
ordinal rungs are recorded as HAZARD-shape (q34), not dead.

Gates frozen in proposals/runs/THRESH-2-granularity-ladder-census-prereg-2026-10-11.md.
CPU-only, deterministic (SOFT on the determ1 torch lane). Never echoes secrets.
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
RC_OK, RC_RED = 0, 1

PREREG = "proposals/runs/THRESH-2-granularity-ladder-census-prereg-2026-10-11.md"


def digest_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(obj) -> str:
    return digest_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def grade(digs: dict[str, str]) -> dict:
    rungs = sorted(set(digs.values()))
    n = len(digs)
    nr = len(rungs)
    if nr == n:
        g = "CONTINUOUS"
    elif nr == 1:
        g = "MONOLITHIC"
    elif nr == 2:
        g = "COARSE"
    else:
        g = "LADDERED"
    return {"n_settings": n, "n_rungs": nr, "grade": g}


# K1: determ1 eps ladder (subprocess, scratch tags, payload digest minus wall_s)
def k1_determ1() -> dict:
    ladders = ["1e-1", "1e-2", "1e-3", "1e-4", "1e-5"]
    digs = {}
    for eps in ladders:
        tag = f"thresh2_eps{eps}"
        rc, so = run([PY, "experiments/determ1_lattice_snap.py", "B", eps, tag])
        out = REPO / f"results/determ1_lattice_snap/B-{tag}.json"
        if rc != 0 or not out.exists():
            return {"knob": "determ1 eps", "ok": False, "why": f"rc={rc} {so[-400:]}"}
        rec = json.loads(out.read_text())
        rec.pop("wall_s", None)
        digs[eps] = norm(rec)
    row = {"knob": "determ1 eps", "ok": True, "settings": digs, **grade(digs)}
    row["anchors_ok"] = digs["1e-2"] != digs["1e-4"]  # THRESH-1 G2 anchor
    return row


# K2: eproc sigma ladder (in-process, pinned series)
def k2_eproc() -> dict:
    import math
    sys.path.insert(0, str(REPO))
    from tools.eproc import eprocess
    d = [0.3 * math.sin(i * 0.7) + (i % 5) * 0.05 for i in range(64)]  # pinned
    ladders = ["0.1", "0.25", "0.5", "0.75", "1.0"]  # AMENDMENT 1: 0.0 is out-of-domain
    digs, epaths = {}, {}
    for s in ladders:
        r = eprocess(d, float(s))
        e = [float(x) for x in r["E"]]
        digs[s] = norm(e)
        epaths[s] = "".join("1" if x >= 1.0 else "0" for x in e)
    # refusal finding (PARAM-1 G3 corroboration): out-of-domain sigma must fail LOUD
    refusal_ok = False
    try:
        eprocess(d, 0.0)
    except ValueError:
        refusal_ok = True
    row = {"knob": "eproc sigma", "ok": True, "settings": digs, **grade(digs),
           "sigma0_refuses": refusal_ok}
    row["anchors_ok"] = digs["0.5"] != digs["0.75"]  # THRESH-1 G2 anchor
    # ordinal monotonicity of the E-path under sigma (q34 hazard shape check)
    row["ordinal_sequence"] = {s: epaths[s] for s in ladders}
    row["monotone_rungs"] = len(set(epaths.values())) == len(ladders)
    return row


# K3: degrade_gate tolerance ladder (subprocess, pinned sweep)
def k3_degrade() -> dict:
    sweep = json.dumps([
        {"param": 70, "benefit": 12.25},
        {"param": 60, "benefit": 10.1},
        {"param": 52, "benefit": 6.3},
        {"param": 45, "benefit": 4.0},
        {"param": 40, "benefit": 4.5},
    ])
    ladders = ["0.0", "0.25", "0.5", "0.75", "1.0"]
    digs, verdicts = {}, {}
    with tempfile.TemporaryDirectory() as td:
        for tol in ladders:
            out = Path(td) / f"dg_{tol}.json"
            rc, so = run([PY, "tools/degrade_gate.py", "--sweep", sweep,
                          "--tolerance", tol, "--out", str(out)])
            if rc not in (0, 1) or not out.exists():
                return {"knob": "degrade_gate tolerance", "ok": False,
                        "why": f"rc={rc} {so[-400:]}"}
            verdicts[tol] = json.loads(out.read_text()).get("verdict")
            digs[tol] = digest_bytes(out.read_bytes())
    row = {"knob": "degrade_gate tolerance", "ok": True, "settings": digs,
           "verdicts": verdicts, **grade(digs)}
    row["anchors_ok"] = (verdicts["0.0"] == "REGIME-BRITTLE"
                         and verdicts["1.0"] == "GRACEFUL"
                         and digs["0.0"] != digs["1.0"])
    return row


# K4: verdict_gate minimum ladder (in-process, pinned)
def k4_verdict() -> dict:
    from tools.verdict_gate import finalize, Gate, StatMeta
    ladders = ["0.80", "0.85", "0.875", "0.90", "0.95"]
    digs, verdicts = {}, {}
    for mn in ladders:
        v = finalize(gates=[Gate("x", value=0.91, minimum=float(mn))],
                     stats={"x": StatMeta(std=0.03, n=32)},
                     completeness=True, status_source="own")
        verdicts[mn] = v.verdict
        digs[mn] = v.verdict
    row = {"knob": "verdict_gate minimum", "ok": True, "settings": digs,
           "verdicts": verdicts, **grade(digs)}
    row["anchors_ok"] = verdicts["0.80"] == "PASS" and verdicts["0.95"] == "FAIL"
    seq = [verdicts[m] for m in ladders]
    row["ordinal_sequence"] = seq
    row["monotone_rungs"] = seq == sorted(seq, key=lambda v: (v == "PASS")) or \
        seq == sorted(seq, key=lambda v: (v == "PASS"), reverse=True)
    return row


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else None
    if out_path and out_path.exists() and not args.force:
        print(json.dumps({"verdict": "REFUSED-OVERWRITE",
                          "why": f"{out_path} exists; --force to override"}))
        sys.exit(3)

    rows = []
    for fn in (k1_determ1, k2_eproc, k3_degrade, k4_verdict):
        try:
            rows.append(fn())
        except Exception as e:
            rows.append({"knob": fn.__name__, "ok": False, "why": f"EXC {e!r}"})

    anchors_fail = [r["knob"] for r in rows if r.get("ok") and not r.get("anchors_ok")]
    refusal_fail = [r["knob"] for r in rows
                    if "sigma0_refuses" in r and not r["sigma0_refuses"]]
    reds = ([r["knob"] for r in rows if (not r["ok"]) or (r.get("grade") == "MONOLITHIC")]
            + [f"ANCHOR:{k}" for k in anchors_fail]
            + [f"REFUSAL:{k}" for k in refusal_fail])
    census = {
        "tool": "thresh2_granularity_ladder",
        "prereg": PREREG,
        "rows": rows,
        "n_knobs": len(rows),
        "n_runnable": sum(1 for r in rows if r["ok"]),
        "reds": reds,
        "verdict": "GREEN" if not reds else "RED",
    }
    census["census_digest"] = norm({k: v for k, v in census.items()})
    text = json.dumps(census, indent=2, sort_keys=True)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n")
    print(text)
    sys.exit(RC_OK if census["verdict"] == "GREEN" else RC_RED)


if __name__ == "__main__":
    main()
