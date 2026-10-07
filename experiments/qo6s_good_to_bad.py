"""QO6s — good→bad retention asymmetry on the frozen QO6 kill gate
(prereg: proposals/runs/QO6s-good-to-bad-retention-asymmetry.md, commit BEFORE fire).

SCOUT-55/q11: full-prefix cumsum (QO6h) means a good→bad flip leaves E dominated by
the confirming prefix. Gates G1/G2 controls, G3 primary (kill within flip+15).
Deterministic CPU. Verdict RED is bookable and does NOT void QO6/QO6h/QO6t.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import eproc as eproc_mod  # noqa: E402

kill_gate = eproc_mod.kill_gate

LATENCY_BUDGET = 15  # pre-registered in the prereg; do not tune post hoc


def lcg(seed):
    s = seed & 0xFFFFFFFF
    while True:
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        yield s


def hopeless_tail(n, gen):
    # V3-style decay, verbatim arithmetic from qo6_kill_evidence.py hope stream
    out = []
    for _ in range(n):
        out.append(max(0.0, out[-1] if out else 0.60) - 0.06 + ((next(gen) % 5) - 2) * 0.01)
    return out


def good_then_bad(prefix_len, seed):
    g = lcg(seed)
    prefix = [0.20 + (0.60 - 0.20) * (i + 1) / prefix_len for i in range(prefix_len)]
    tail = hopeless_tail(40, g)
    return prefix + tail, prefix_len


def bloom_control():
    # verbatim V2 from qo6h_evidence_horizon.py
    return [0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05,
            0.19, 0.33, 0.47, 0.61, 0.72, 0.80, 0.86]


def hopeless_control():
    g = lcg(99)
    s = [0.60]
    for _ in range(13):
        s.append(max(0.0, s[-1] - 0.06 + ((next(g) % 5) - 2) * 0.01))
    return s


SIGMA, DELTA = 0.03, 0.05
gb1, f1 = good_then_bad(30, 21)
gb2, f2 = good_then_bad(60, 22)
gb3, f3 = good_then_bad(15, 23)
STREAMS = {
    "GB1_flip30": (gb1, f1),
    "GB2_flip60": (gb2, f2),
    "GB3_flip15": (gb3, f3),
}
CONTROLS = {
    "CTRL_KILL_V3": hopeless_control(),
    "CTRL_KEEP_V2": bloom_control(),
}

R = {"gates": {}, "streams": {}, "ALL_PASS": False}

for name, series in CONTROLS.items():
    kg = kill_gate(series, sigma=SIGMA, delta=DELTA)
    R["streams"][name] = {"decision": kg["decision"], "stop_t": kg.get("stop_t")}
R["gates"]["G1_ctrl_kill"] = R["streams"]["CTRL_KILL_V3"]["decision"] == "KILL_CANDIDATE"
R["gates"]["G2_ctrl_keep"] = R["streams"]["CTRL_KEEP_V2"]["decision"] == "KEEP"

g3 = True
for name, (series, flip) in STREAMS.items():
    kg = kill_gate(series, sigma=SIGMA, delta=DELTA)
    stop_t = kg.get("stop_t")
    ok = (kg["decision"] == "KILL_CANDIDATE") and (stop_t is not None) and (stop_t <= flip + LATENCY_BUDGET)
    g3 = g3 and ok
    R["streams"][name] = {"decision": kg["decision"], "stop_t": stop_t, "flip_t": flip,
                          "within_budget": bool(ok), "E_final": kg.get("E_final")}
R["gates"]["G3_primary_within_flip_plus_15"] = g3
R["ALL_PASS"] = all(R["gates"].values())
R["VERDICT"] = "PASS" if R["ALL_PASS"] else "RED (retention-asymmetry limit named)"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=None, help="scratch output dir (RC-1: never results/)")
args = ap.parse_args()
text = json.dumps(R, indent=2)
if args.out:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(text)
print(text)
print(f"QO6s VERDICT: {R['VERDICT']}")
