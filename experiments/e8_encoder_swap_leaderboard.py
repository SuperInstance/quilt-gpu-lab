"""E8 — encoder-swap leaderboard: aggregate the lab's per-encoder readings
into ONE honest table.

Pure aggregation from RESULTS.md (the ledger is the source of truth): parse
each experiment's ```json block by experiment id (E1, E3, E7 — and E9 when
it lands), extract per-encoder readings under their published names, and
refuse to invent numbers: a reading an experiment never took stays "not
taken"/"not run" in the table. The latest non-ABORTED result per id wins.

Columns per encoder: separation gap (heldout, with its metric name),
drift-gate behavior, surprise reading, axis-correlation, verdict, date.
Output: results/leaderboard.json + a human-readable markdown table appended
to RESULTS.md. No model downloads, no GPU, no RNG — SEED is recorded only
to honor the lab convention.

Caveat (carried into the output, not buried): gaps are within-metric only —
E1 is a margin delta on learned 6-dim obs, E3 is vMF d_mu on hand-crafted
dials, E7/E9 are cosine within-minus-cross on frozen JEPA embeddings. The
board tracks per-encoder readings against the SAME cell contract; it does
NOT rank raw gap numbers across rows. Cross-encoder correlation (the
surprise protocol in MODELS.md) needs persisted embeddings — future work.
Re-run E8 after E9 lands to refresh the board.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
RESULTS_MD = LAB / "RESULTS.md"
LEADERBOARD = LAB / "results" / "leaderboard.json"

SEED = 2718  # lab convention; this script performs no sampling
ORDER = ["E1", "E3", "E7", "E9"]
ENCODERS = {
    "E1": "our contrastive RoomEncoder (~150k, learned L0)",
    "E3": "elephant vMF pipeline (hand-crafted dials)",
    "E7": "V-JEPA 2 ViT-L (frozen, video JEPA)",
    "E9": "I-JEPA ViT-B (frozen, still-image JEPA)",
}
SECTION_RE = re.compile(r"^## (E\d+[b]?)\b", re.M)
JSON_RE = re.compile(r"```json\n(.*?)\n```", re.S)
RAN_RE = re.compile(r"ran:\s*(\d{4}-\d{2}-\d{2})")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
VERDICT_RE = re.compile(r"^\s*-\s*verdict:\s*\*{0,2}([A-Z]+)", re.M)
GAP_METRIC = {
    "E1": "margin delta trained-minus-untrained (heldout)",
    "E7": "cosine within-minus-cross (heldout)",
    "E9": "cosine within-minus-cross (heldout)",
}


def parse_ledger(text: str) -> dict:
    """{eid: {date, result, aborted}} — last non-aborted ```json block per id."""
    heads = list(SECTION_RE.finditer(text))
    out: dict = {}
    for i, m in enumerate(heads):
        eid = m.group(1)
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        sec = text[m.start():end]
        blocks = JSON_RE.findall(sec)
        if not blocks:
            continue  # non-JSON section (e.g. E8's own markdown table)
        try:
            res = json.loads(blocks[0])
        except json.JSONDecodeError:
            continue  # torn/foreign block — skip, never fabricate
        pre = sec.split("```", 1)[0]
        if res.get("verdict") is None:  # early entries keep verdict in the bullet
            vm = VERDICT_RE.search(pre)
            if vm:
                res = {**res, "verdict": vm.group(1)}
        d = RAN_RE.search(pre) or DATE_RE.search(pre)
        rec = {"date": d.group(1) if d else None, "result": res}
        if str(res.get("verdict", "")).upper().startswith("ABORT"):
            out.setdefault(eid, {**rec, "aborted": True})
            continue
        out[eid] = {**rec, "aborted": False}
    return out


def row_for(eid: str, res: dict) -> dict:
    r = {"encoder": ENCODERS[eid], "experiment": eid}

    # separation gap (heldout): published field name per experiment shape
    gap = res.get("heldout_gap")
    metric = GAP_METRIC.get(eid)
    if gap is None and isinstance(res.get("checks"), dict):
        seps = [v.get("d_mu") for k, v in res["checks"].items()
                if k.startswith("separation") and v.get("d_mu") is not None]
        if seps:
            gap, metric = seps[0], "vmf d_mu (heldout fits)"
    r["heldout_gap"], r["gap_metric"] = gap, metric

    # drift gate: E3's checks ARE the gate; everyone else never ran it
    checks = res.get("checks")
    if isinstance(checks, dict) and checks:
        stab = [v for k, v in checks.items() if k.startswith("stability")]
        sep = [v for k, v in checks.items() if k.startswith("separation")]
        stab_ok = all(not v.get("real") for v in stab) and bool(stab)
        sep_ok = all(v.get("real") for v in sep) and bool(sep)
        if stab_ok and sep_ok:
            r["drift_gate"] = (f"pass (stability {len(stab)}/{len(stab)} not-real, "
                               f"separation {len(sep)}/{len(sep)} real)")
        else:
            r["drift_gate"] = "fail (see experiment JSON)"
    else:
        r["drift_gate"] = "not run"

    # surprise: only published readings; never derived after the fact
    if res.get("kl_sym_heldout") is not None:
        r["surprise"], r["surprise_metric"] = res["kl_sym_heldout"], "KL sym (heldout vMF fits)"
    else:
        r["surprise"], r["surprise_metric"] = None, "not taken"

    if res.get("tex_vs_motion_axis_corr") is not None:
        r["axis_corr"] = res["tex_vs_motion_axis_corr"]
        r["axis_corr_metric"] = "tex-vs-motion axis corr (smpte-still vs testsrc-testsrc2)"
    else:
        r["axis_corr"], r["axis_corr_metric"] = None, "not taken"

    r["verdict"] = res.get("verdict")
    return r


def fmt_gap(row: dict) -> str:
    if row["heldout_gap"] is None:
        return "n/a"
    return f"{row['heldout_gap']:+.4f} ({row['gap_metric']})"


def main() -> dict:
    ledger = parse_ledger(RESULTS_MD.read_text())
    rows, pending, aborted = [], [], []
    for eid in ORDER:
        rec = ledger.get(eid)
        if rec is None or rec.get("aborted"):
            if rec is not None:
                aborted.append(eid)
            pending.append(eid)
            continue
        row = row_for(eid, rec["result"])
        row["date"] = rec["date"]
        rows.append(row)
    pend_rows = [{"encoder": ENCODERS[e], "experiment": e,
                  "status": "pending (no non-aborted result in RESULTS.md yet)"}
                 for e in pending]

    scored = [r for r in rows if r["heldout_gap"] is not None]
    verdict = "KEEP" if (len(rows) >= 3 and len(scored) >= 2) else "INCONCLUSIVE"
    caveat = ("gaps are within-metric only (E1 margin on learned obs; E3 vMF d_mu on "
              "hand-crafted dials; E7/E9 cosine on frozen JEPA embeddings) — the board "
              "compares encoders against the SAME cell contract, not raw gap numbers "
              "across rows. Cross-encoder correlation (MODELS.md surprise protocol) "
              "needs persisted embeddings — future work.")

    board = {
        "experiment": "E8 encoder-swap leaderboard",
        "seed": SEED,
        "generated": datetime.date.today().isoformat(),
        "source": "RESULTS.md",
        "rows": rows,
        "pending": pend_rows,
        "aborted_latest_only": aborted,
        "caveat": caveat,
        "verdict": verdict,
    }
    LEADERBOARD.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD.write_text(json.dumps(board, indent=2) + "\n")

    # human-readable table appended to the ledger (E8's own runner entry follows)
    lines = ["",
             f"## E8 — encoder-swap leaderboard (generated {board['generated']})", "",
             "| encoder | exp | separation gap (heldout) | drift gate | surprise | axis corr | verdict | date |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['encoder']} | {r['experiment']} | {fmt_gap(r)} | {r['drift_gate']} "
            f"| {r['surprise'] if r['surprise'] is not None else 'not taken'} "
            f"| {r['axis_corr'] if r['axis_corr'] is not None else 'not taken'} "
            f"| {r['verdict']} | {r['date']} |")
    for p in pend_rows:
        lines.append(f"| {p['encoder']} | {p['experiment']} | {p['status']} | | | | | |")
    lines += [f"- caveat: {caveat}",
              f"- full machine-readable board: results/leaderboard.json", ""]
    with RESULTS_MD.open("a") as f:
        f.write("\n".join(lines))

    print(json.dumps(board, indent=2))
    return board


if __name__ == "__main__":
    main()
