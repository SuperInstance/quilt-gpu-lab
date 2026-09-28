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

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
from guard import Guard  # noqa: E402

QUEUE = LAB / "QUEUE.md"
RESULTS = LAB / "RESULTS.md"
VENV_PY = Path.home() / "venvs/elephant-gpu/bin/python"

ITEM_RE = re.compile(r"^- \[ \] (E\d+)\s+(.+)$")
EXP_MOD = {
    "E1": "experiments.e1_real_glyph_contrast",
    "E2": "experiments.e2_flow_beat_vs_pool",
    "E2b": "experiments.e2b_flow_beat_revision",
    "E3": "experiments.e3_cast_heldout",
    "E4": "experiments.e4_next_room_transformer",
    "E4b": None,  # revision of E4, dataset redesign — script pending
    "E5": None,   # int8 probe — script pending
    "E6": None,   # harness self-test — script pending
    "E7": "experiments.e7_vjepa2_in_cells",
    "E8": "experiments.e8_encoder_swap_leaderboard",
    "E9": "experiments.e9_ijepa_stills",
    "E10": "experiments.e10_invariance_race",
    "E11": "experiments.e11_debounce_kill",
    "D1": "experiments.d1_look_again_scale",
    "D2": "experiments.d2_ternary_kernel",
    "D3": "experiments.d3_statevector_ceiling",
    "D4": "experiments.d4_canon_lora",
    "D5": "experiments.d5_probe_foundry",
    "D6": "experiments.d6_fun_scorer",
    "D7": "experiments.d7_quant_drift",
    "D10": "experiments.d10_cell_kernel",
    "D12": "experiments.d12_substrate_falsification",
    "D14": "experiments.d14_qthe_timbre_proof",
}


def claim() -> tuple[str, str] | None:
    for line in QUEUE.read_text().splitlines():
        m = ITEM_RE.match(line)
        if m:
            eid = m.group(1)
            if EXP_MOD.get(eid) is None:
                print(f"[runner] {eid} has no script yet — skipping")
                continue
            return eid, m.group(2)
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
        # Robust extraction: find the LAST top-level JSON object. rindex("{\n")
        # breaks on nested dicts (indent=2); use raw_decode scanning backward.
        decoder = json.JSONDecoder()
        obj = None
        idx = out.rfind('{')
        while idx >= 0 and obj is None:
            try:
                obj, _ = decoder.raw_decode(out, idx)
            except json.JSONDecodeError:
                idx = out.rfind('{', 0, idx)
        if obj is None:
            raise ValueError("no JSON object found in stdout")
        result.update(obj)
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
