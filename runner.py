#!/usr/bin/env python3
"""runner.py — claims the first unchecked experiment from QUEUE.md and runs it
under the GPU guard. Appends an honest entry to RESULTS.md, checks the box
with date + verdict.

Cron-friendly: no TTY, exits 0 even when a guard breach aborts (the breach
is recorded in RESULTS.md — failures are data, not errors).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
from guard import Guard  # noqa: E402

QUEUE = LAB / "QUEUE.md"
RESULTS = LAB / "RESULTS.md"
VENV_PY = Path.home() / "venvs/elephant-gpu/bin/python"

ITEM_RE = re.compile(r"^- \[ \] (E\d+)\s+(.+)$")
EXP_MOD = {
    "E1": "experiments.e1_real_glyph_contrast",
    "E2": "experiments.e2_flow_beat_vs_pool",
}


def claim() -> tuple[str, str] | None:
    for line in QUEUE.read_text().splitlines():
        m = ITEM_RE.match(line)
        if m:
            return m.group(1), m.group(2)
    return None


def check_off(eid: str, verdict: str) -> None:
    text = QUEUE.read_text()
    today = datetime.date.today().isoformat()
    pat = re.compile(rf"^- \[ \] {eid} (.+)$", re.M)
    text = pat.sub(
        rf"- [x] {eid} \1 — {today} {verdict}", text, count=1)
    QUEUE.write_text(text)


def run(eid: str) -> dict:
    guard = Guard(timeout_s=1800)
    if not guard.preflight():
        return {"experiment": eid, "verdict": "ABORTED", "reason": guard.breach,
                "guard": guard.summary()}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(LAB)
    code, out, err = guard.run(
        [str(VENV_PY), "-m", EXP_MOD[eid]], cwd=str(LAB), env=env)
    result = {"experiment": eid, "guard": guard.summary()}
    if code != 0:
        result.update(verdict="ABORTED", reason=f"exit {code}",
                      stderr=err[-2000:])
        return result
    # experiment prints a single JSON object at the end
    try:
        j = json.loads(out[out.rindex("{\n"):])
        result.update(j)
        result["guard_summary"] = result.pop("guard")
    except Exception:
        result.update(verdict="INCONCLUSIVE", reason="no parseable result",
                      stdout_tail=out[-1500:])
    return result


def main() -> int:
    claimed = claim()
    if not claimed:
        print("QUEUE: nothing unchecked. The chip rests (add experiments).")
        return 0
    eid, title = claimed
    print(f"claiming {eid}: {title}")
    res = run(eid)
    verdict = res.get("verdict", "ABORTED")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    RESULTS.open("a").write(
        f"\n## {eid} — {title}\n- ran: {ts}\n- verdict: {verdict}\n"
        f"- result: ```json\n{json.dumps(res, indent=2)}\n```\n")
    check_off(eid, verdict)
    print(f"{eid} -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
