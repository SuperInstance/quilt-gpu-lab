#!/usr/bin/env python3
"""path1c_horizon.py — PATH-1c horizon probe over the two FIXED-POINT-AT-FINE knobs.

Per PATH-1c prereg (committed before fire, SCOUT-107 spawn / rc q37): widen the gate-input
observation window (V0 single / V1 n2x / V2 n4x) and re-ask whether fine targets stay
byte-identical. Same emitters as PATH-1b, verbatim. G1 anchors to PATH-1b digests + RAMP
rung counts; G2 horizon-limited; G3 quantization CONFIRMED; G4 determinism rerun.
CPU-only. --out refuse-overwrite (exit 3). VEXIT-1: `VERDICT:` + exit contract
(0 GREEN / 1 RED / 3 refusal).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "experiments"))
PREREG = "proposals/runs/PATH-1c-horizon-probe-prereg-2026-10-11.md"
PATH1B_PREREG = "proposals/runs/PATH-1b-steerability-prereg-2026-10-11.md"

TARGETS = {
    "degrade_gate tolerance": ["0.5", "0.625", "0.75"],
    "verdict_gate minimum": ["0.875", "0.895", "0.90"],
}
ANCHOR_DISTINCT = {"degrade_gate tolerance": 2, "verdict_gate minimum": 2}
PATH1B_LADDERS = {
    "degrade_gate tolerance": ["0.0", "0.25", "0.5", "0.75", "1.0"],
    "verdict_gate minimum": ["0.80", "0.85", "0.875", "0.90", "0.95"],
}
VARIANTS = {"V0": 1, "V1": 2, "V2": 4}
TARGETS_KEYS = list(TARGETS.keys())


def norm(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---- payload emitters: PATH-1b's, verbatim, with a window multiplier ----

def payload_degrade(setting: str, tag: str, win: int) -> dict:
    import subprocess, tempfile
    base = [
        {"param": 70, "benefit": 12.25},
        {"param": 60, "benefit": 10.1},
        {"param": 52, "benefit": 6.3},
        {"param": 45, "benefit": 4.0},
        {"param": 40, "benefit": 4.5},
    ]
    sweep = json.dumps(base * win)  # same marginal evidence, win x window
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"dg_{tag}.json"
        p = subprocess.run([sys.executable, "tools/degrade_gate.py", "--sweep", sweep,
                            "--tolerance", setting, "--out", str(out)],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        if p.returncode not in (0, 1) or not out.exists():
            raise RuntimeError(f"degrade rc={p.returncode} {p.stderr[-300:]}")
        return json.loads(out.read_text())


def payload_verdict(setting: str, tag: str, win: int) -> dict:
    from tools.verdict_gate import finalize, Gate, StatMeta
    v = finalize(gates=[Gate("x", value=0.91, minimum=float(setting))],
                 stats={"x": StatMeta(std=0.03, n=32 * win)},
                 completeness=True, status_source="own")
    return {"verdict": v.verdict}


PAYLOADS = {"degrade_gate tolerance": payload_degrade, "verdict_gate minimum": payload_verdict}


def g1_anchor() -> dict:
    a = {}
    for knob, ladder in PATH1B_LADDERS.items():
        digs = {s: norm(PAYLOADS[knob](s, f"path1c_anchor_{knob}_{s}", 1)) for s in ladder}
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
    if not anchors["ok"]:
        census = {"tool": "path1c_horizon", "prereg": PREREG, "g1_anchors": anchors,
                  "verdict": "RED", "why": "G1 anchor void; premise gone"}
        print(json.dumps(census, indent=2, sort_keys=True))
        print(f"VERDICT: {census['verdict']}")
        sys.exit(1)

    rowmap, horizon_hits, reds = {}, [], []
    for knob, targets in TARGETS.items():
        per_variant, vok = {}, True
        for vname, win in VARIANTS.items():
            digs = {}
            for s in targets:
                try:
                    digs[s] = norm(PAYLOADS[knob](s, f"path1c_{vname}_{knob}_{s}", win))
                except Exception as e:  # fail-loud, no retry loop
                    rowmap[knob] = {"knob": knob, "ok": False, "why": f"{vname}/{s}: {e}"}
                    reds.append(f"RUN:{knob}:{vname}:{s}")
                    vok = False
                    break
            if not vok:
                break
            per_variant[vname] = {"digests": digs, "n_distinct": len(set(digs.values()))}
            if len(set(digs.values())) >= 2:
                horizon_hits.append(f"{knob}:{vname}")
        if not vok:
            continue
        ident_all = all(per_variant[v]["n_distinct"] == 1 for v in VARIANTS)
        rowmap[knob] = {"knob": knob, "ok": True, "targets": targets,
                        "variants": per_variant, "identical_all_variants": ident_all}
    rows = list(rowmap.values())
    if len(rows) < len(TARGETS):
        census = {"tool": "path1c_horizon", "prereg": PREREG, "g1_anchors": anchors,
                  "rows": rows, "reds": reds, "verdict": "RED",
                  "why": "runner failure (fail-loud)"}
    else:
        # G4 determinism: rerun V0 digests, must be byte-identical
        rerun_ok = True
        for knob, targets in TARGETS.items():
            for s in targets:
                if norm(PAYLOADS[knob](s, f"path1c_rerun_{knob}_{s}", 1)) != \
                        rowmap[knob]["variants"]["V0"]["digests"][s]:
                    rerun_ok = False
                    reds.append(f"NONDET:{knob}:{s}")
        g2_fired = bool(horizon_hits)
        verdict_word = ("G3:QUANTIZATION-CONFIRMED" if not g2_fired else
                        f"G2:HORIZON-LIMITED {horizon_hits}")
        census = {"tool": "path1c_horizon", "prereg": PREREG, "path1b_prereg": PATH1B_PREREG,
                  "g1_anchors": anchors, "rows": rows, "g2_horizon_hits": horizon_hits,
                  "g4_rerun_deterministic": rerun_ok, "reds": reds,
                  "outcome": verdict_word,
                  "verdict": "GREEN" if (rerun_ok and not reds) else "RED"}
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
