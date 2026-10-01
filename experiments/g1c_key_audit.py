#!/usr/bin/env python3
"""G1c key audit + rescore.

The G1c routing table depends on the blind key. While scoring, two classes
(contra, count) showed arms collapsing to a single verdict. This script
RECOMPUTES the ground truth of every battery claim directly from its prompt
text (pure logic / arithmetic / enumeration) and compares it with the shipped
key, then rescores all three arms (local seat, JEV, GLM) against both keys.

Read-only w.r.t. the battery and the shipped key; writes results/g1c/key_audit.json.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATTERY = Path("/home/eileen/projects/fleet-seeds/docs/g1/battery-96.json")
KEY = ROOT / "results" / "g1" / "battery-96-key.json"
LOCAL = ROOT / "results" / "g1" / "run1" / "score.json"
OUT = ROOT / "results" / "g1c"


def truth_arith(t):
    m = re.search(r"Claim: (\d+) ([+\-x]) (\d+) = (-?\d+)\.", t)
    a, op, c, r = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
    v = {"+": a + c, "-": a - c, "x": a * c}[op]
    return "SUPPORTED" if v == r else "REFUTED"


def truth_seq(t):
    m = re.search(r"the next term of the sequence \[([\d, ]+)\] is (\d+)", t)
    xs = [int(v) for v in m.group(1).split(",")]
    claim = int(m.group(2))
    d = xs[1] - xs[0]
    ok = all(xs[i + 1] - xs[i] == d for i in range(len(xs) - 1)) and xs[-1] + d == claim
    return "SUPPORTED" if ok else "REFUTED"


def truth_date(t):
    m = re.search(r"Claim: (\d+) days after (\d{4}-\d{2}-\d{2}) is (\d{4}-\d{2}-\d{2})\.", t)
    n = int(m.group(1))
    d0 = datetime.date.fromisoformat(m.group(2))
    claim = datetime.date.fromisoformat(m.group(3))
    return "SUPPORTED" if d0 + datetime.timedelta(days=n) == claim else "REFUTED"


def truth_xref(t):
    assigns = {}
    for mm in re.finditer(r"^\s*(\w+) → department (D\d+) \(([^,]+), ([^)]+)\)$", t, re.M):
        assigns[mm.group(1)] = (mm.group(2), mm.group(3), mm.group(4))
    cm = re.search(r"Claim: (\w+) works in department (D\d+) \(([^)]+)\), "
                   r"stationed in ([^,.]+), per the assignments list", t)
    who, dept, unit, city = cm.group(1), cm.group(2), cm.group(3), cm.group(4)
    a = assigns.get(who)
    return "SUPPORTED" if a == (dept, unit, city) else "REFUTED"


def truth_contra(t):
    A = re.search(r"Statement A: The locker contains exactly these items: (.*?)\.\n", t).group(1)
    alist = [s.strip() for s in A.split(",")]
    Bm = re.search(r"Statement B: (.*?)\.\n", t).group(1)
    m = re.match(r"The (.*?) is NOT on the locker list$", Bm)
    if not m:
        return None  # unrecognised B form -> cannot recompute
    item = m.group(1).strip()
    # A is an asserted enumeration; B is consistent with A iff B is true under A.
    return "SUPPORTED" if item not in alist else "REFUTED"


def truth_count(t):
    items = [s.strip() for s in re.search(r"Manifest states: (.*?)\.\n", t).group(1).split(";")]
    cm = re.search(r"Claim: the manifest lists '(.*?)' exactly (\d+) times", t)
    item, n = cm.group(1), int(cm.group(2))
    return "SUPPORTED" if items.count(item) == n else "REFUTED"


TRUTH = {"arith": truth_arith, "seq": truth_seq, "date": truth_date,
         "xref": truth_xref, "contra": truth_contra, "count": truth_count}
CLASS_RE = re.compile(r"g1b-(\w+)-\d+")


def main():
    prompts = json.load(open(BATTERY))["prompts"]
    key = json.load(open(KEY))["key"]
    local = {r["id"]: r["got"] for r in json.load(open(LOCAL))["rows"]}
    jev = json.load(open(OUT / "arm_jev_raw.json"))
    glm = json.load(open(OUT / "arm_glm_raw.json"))

    rows = []
    for p in prompts:
        pid = p["id"]
        cls = CLASS_RE.match(pid).group(1)
        shipped = key[pid]["expected"]
        rec = TRUTH[cls](p["text"])
        rows.append({
            "id": pid, "class": cls,
            "shipped": shipped, "recomputed": rec,
            "key_consistent": (rec is not None and rec == shipped),
            "truth_text": key[pid]["truth"],
            "local": local.get(pid),
            "jev": jev[pid].get("verdict"),
            "glm": glm[pid].get("verdict"),
        })

    classes = ["arith", "seq", "date", "xref", "contra", "count"]
    aud = {c: {"n": sum(1 for r in rows if r["class"] == c),
               "key_mismatches": sum(1 for r in rows if r["class"] == c and not r["key_consistent"])}
           for c in classes}

    def score(ref):
        out = {}
        for c in classes:
            sub = [r for r in rows if r["class"] == c]
            for arm in ("local", "jev", "glm"):
                k = sum(1 for r in sub if r[arm] == r[ref])
                out.setdefault(arm, {})[c] = round(k / len(sub), 4)
        for arm in ("local", "jev", "glm"):
            k = sum(1 for r in rows if r[arm] == r[ref])
            out[arm]["OVERALL"] = round(k / len(rows), 4)
            sound = [r for r in rows if r["class"] in ("arith", "seq", "date", "xref")]
            ks = sum(1 for r in sound if r[arm] == r[ref])
            out[arm]["SOUND4"] = round(ks / len(sound), 4)
        return out

    report = {
        "schema": "g1c-key-audit/v1",
        "note": ("Ground truth recomputed from prompt text. A claim is "
                 "'key_consistent' iff the shipped key label equals the "
                 "recomputed truth."),
        "audit": aud,
        "scores_vs_shipped_key": score("shipped"),
        "scores_vs_recomputed_truth": score("recomputed"),
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT / "key_audit.json", "w"), indent=2)

    print("class    n  key-mismatches")
    for c in classes:
        print(f"{c:8s} {aud[c]['n']:2d} {aud[c]['key_mismatches']:2d}")
    print(f"\ntotal key mismatches: {sum(v['key_mismatches'] for v in aud.values())}/96")
    print("\naccuracy vs SHIPPED key:")
    for arm in ("local", "jev", "glm"):
        print(f"  {arm:6s} {json.dumps(report['scores_vs_shipped_key'][arm])}")
    print("\naccuracy vs RECOMPUTED truth:")
    for arm in ("local", "jev", "glm"):
        print(f"  {arm:6s} {json.dumps(report['scores_vs_recomputed_truth'][arm])}")


if __name__ == "__main__":
    main()
