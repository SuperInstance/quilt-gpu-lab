#!/usr/bin/env python3
"""path1b_steerability.py — PATH-1b steerability gate for CONTINUOUS upgrades (SCOUT-106 spawn).

Per PATH-1b prereg (committed before fire): for the three deterministic PATH-INDEPENDENT knobs,
fire payload emitters at two adjacent ladder rungs + one midpoint FINER than the ladder.
- At least one fine pair distinct  => STEERABLE at finest resolution; PATH-1 CONTINUOUS upgrade stands.
- ALL targets byte-identical       => FIXED-POINT-AT-FINE (rc q36 shape) => RED row; annotate
  owning receipt; BLOCK unconditional upgrade.
determ1 eps excluded (SOFT nondeterminism class, spawn scope <=3 knobs).

Gates G1-G4 frozen in proposals/runs/PATH-1b-steerability-prereg-2026-10-11.md.
CPU-only. --out refuse-overwrite (exit 3) per RC-1 rule. VEXIT-1: final `VERDICT:` line +
exit-code contract (0 GREEN / 1 RED / 3 refusal).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "experiments"))
PREREG = "proposals/runs/PATH-1b-steerability-prereg-2026-10-11.md"
PATH1_PREREG = "proposals/runs/PATH-1-knob-history-dependence-prereg-2026-10-11.md"

TARGETS = {
    "eproc sigma": ["0.5", "0.55", "0.75"],
    "degrade_gate tolerance": ["0.5", "0.625", "0.75"],
    "verdict_gate minimum": ["0.875", "0.895", "0.90"],
}
# PATH-1 booked grade shapes (G1 anchor: count-of-distinct RAMP rung digests)
ANCHOR_DISTINCT = {"eproc sigma": 5, "degrade_gate tolerance": 2, "verdict_gate minimum": 2}


def norm(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---- payload emitters: PATH-1's, verbatim (pinned inputs) ----

def payload_eproc(setting: str, tag: str) -> dict:
    import math
    from tools.eproc import eprocess
    d = [0.3 * math.sin(i * 0.7) + (i % 5) * 0.05 for i in range(64)]
    r = eprocess(d, float(setting))
    return {"E": [float(x) for x in r["E"]]}


def payload_degrade(setting: str, tag: str) -> dict:
    import subprocess, tempfile
    sweep = json.dumps([
        {"param": 70, "benefit": 12.25},
        {"param": 60, "benefit": 10.1},
        {"param": 52, "benefit": 6.3},
        {"param": 45, "benefit": 4.0},
        {"param": 40, "benefit": 4.5},
    ])
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"dg_{tag}.json"
        p = subprocess.run([sys.executable, "tools/degrade_gate.py", "--sweep", sweep,
                            "--tolerance", setting, "--out", str(out)],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        if p.returncode not in (0, 1) or not out.exists():
            raise RuntimeError(f"degrade rc={p.returncode} {p.stderr[-300:]}")
        return json.loads(out.read_text())


def payload_verdict(setting: str, tag: str) -> dict:
    from tools.verdict_gate import finalize, Gate, StatMeta
    v = finalize(gates=[Gate("x", value=0.91, minimum=float(setting))],
                 stats={"x": StatMeta(std=0.03, n=32)},
                 completeness=True, status_source="own")
    return {"verdict": v.verdict}


PAYLOADS = {"eproc sigma": payload_eproc, "degrade_gate tolerance": payload_degrade,
            "verdict_gate minimum": payload_verdict}

PATH1_LADDERS = {
    "eproc sigma": ["0.1", "0.25", "0.5", "0.75", "1.0"],
    "degrade_gate tolerance": ["0.0", "0.25", "0.5", "0.75", "1.0"],
    "verdict_gate minimum": ["0.80", "0.85", "0.875", "0.90", "0.95"],
}


def g1_anchor() -> dict:
    """Fresh RAMP rung digests over the PATH-1 ladders; anchor = count-of-distinct."""
    a = {}
    for knob, ladder in PATH1_LADDERS.items():
        digs = {s: norm(PAYLOADS[knob](s, f"path1b_anchor_{knob}_{s}")) for s in ladder}
        a[knob] = {"distinct": len(set(digs.values())), "expected": ANCHOR_DISTINCT[knob],
                   "ok": len(set(digs.values())) == ANCHOR_DISTINCT[knob]}
    a["ok"] = all(v.get("ok") for v in a.values() if isinstance(v, dict))
    return a


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    anchors = g1_anchor()
    rows, reds = [], []
    for knob, targets in TARGETS.items():
        digs, ok = {}, True
        for s in targets:
            try:
                digs[s] = norm(PAYLOADS[knob](s, f"path1b_{knob}_{s}"))
            except Exception as e:  # fail-loud, no retry loop
                rows.append({"knob": knob, "ok": False, "why": f"{s}: {e}"})
                reds.append(f"RUN:{knob}:{s}")
                ok = False
                break
        if not ok:
            continue
        pairs = [(targets[0], targets[1]), (targets[1], targets[2]), (targets[0], targets[2])]
        fine_distinct = [f"{a}!={b}" for a, b in pairs if digs[a] != digs[b]]
        fixed_point = len(set(digs.values())) == 1
        row = {"knob": knob, "ok": True, "targets": targets, "digests": digs,
               "n_distinct": len(set(digs.values())),
               "fixed_point_at_fine": fixed_point,
               "fine_distinct_pairs": fine_distinct,
               "grade": "FIXED-POINT-AT-FINE" if fixed_point else "STEERABLE"}
        if fixed_point:
            reds.append(f"FIXED-POINT:{knob}")
        rows.append(row)

    g2_ok = all(r.get("ok") for r in rows)
    census = {"tool": "path1b_steerability", "prereg": PREREG, "path1_prereg": PATH1_PREREG,
              "rows": rows, "g1_anchors": anchors, "g2_liveness": g2_ok,
              "n_knobs": len(TARGETS), "reds": reds,
              "verdict": "GREEN" if (not reds and anchors["ok"] and g2_ok) else "RED"}
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
    print(f"VERDICT: {census['verdict']}")
    sys.exit(0 if census["verdict"] == "GREEN" else 1)


if __name__ == "__main__":
    main()
