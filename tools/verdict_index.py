"""verdict_index — VX-1: taint query over the FW-1-censused bookings (verdict->instrument).

The quilt-matrix guard-registry lesson (XM-1): wholesale-void must be a LOOKUP, not
archaeology. This tool compiles the FW-1 field-write census (tranches 1-3, 9 bookings)
into receipts/verdict_index.json and answers taint queries:

    python tools/verdict_index.py taint "positional name->oid map"   # -> ["VSB-1"]
    python tools/verdict_index.py taint "E trajectory"               # -> ["QO6"]
    python tools/verdict_index.py selftest                           # G1-G4 gates

Frozen gates (proposals/runs/VX-1-verdict-index.md, committed BEFORE this tool fired):
  G1 COMPLETENESS: exactly the 9 FW-1 bookings present; statuses match booked FW-1 verdicts
     (8 GREEN + W5b2 GREEN-with-caveat; zero RED).
  G2 ROUND-TRIP: taint(booking's own verdict-feeding write site) includes that booking.
  G3 NEGATIVE CONTROL: taint("vx1_negative_control_field") == [] and mutation control
     (removing a coverage entry from a COPY) flips G2 RED.
  G4 COST: CPU-only, <5 s, no GPU, no network.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "receipts" / "verdict_index.json"

EXPECTED_BOOKINGS = {
    "QO10", "QO6", "QC-JEV", "D12i", "W5b2", "QG7", "CI-1", "VSB-1", "QG7b",
}


def load_index(path: Path = INDEX_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def taint(query: str, index: dict) -> list[str]:
    """Bookings whose verdict_reads, write_sites, or coverage mention `query`."""
    q = query.lower()
    hits = []
    for b in index["bookings"]:
        haystack = " | ".join(
            b.get("verdict_reads", []) + b.get("write_sites", []) + b.get("coverage", [])
        ).lower()
        if q in haystack:
            hits.append(b["booking"])
    return sorted(hits)


def gate1(index: dict) -> tuple[bool, list[str]]:
    reasons = []
    names = {b["booking"] for b in index["bookings"]}
    if names != EXPECTED_BOOKINGS:
        reasons.append(f"booking set mismatch: extra={sorted(names - EXPECTED_BOOKINGS)} missing={sorted(EXPECTED_BOOKINGS - names)}")
    red = [b["booking"] for b in index["bookings"] if "RED" in b.get("fw1_status", "").upper()
           and "GREEN" not in b.get("fw1_status", "").upper()]
    if red:
        reasons.append(f"RED statuses present (FW-1 booked none): {red}")
    caveats = [b["booking"] for b in index["bookings"] if "caveat" in b.get("fw1_status", "")]
    if caveats != ["W5b2"]:
        reasons.append(f"caveat set mismatch (expected [W5b2]): {caveats}")
    return not reasons, reasons


def gate2(index: dict) -> tuple[bool, list[str]]:
    reasons = []
    probes = {
        "QO10": "G1 anchors",
        "QO6": "E trajectory",
        "QC-JEV": "d_ptrue",
        "D12i": "T_floor",
        "W5b2": "mean_rel",
        "QG7": "gen-1 oracle AUC",
        "CI-1": "control_ladder() rungs",
        "VSB-1": "positional name->oid map",
        "QG7b": "pairwise Spearman matrix",
    }
    for booking, probe in probes.items():
        hits = taint(probe, index)
        if booking not in hits:
            reasons.append(f"round-trip miss: taint({probe!r}) = {hits}, missing {booking}")
    return not reasons, reasons


def gate3(index: dict) -> tuple[bool, list[str]]:
    reasons = []
    if taint("vx1_negative_control_field", index) != []:
        reasons.append("negative control returned non-empty set")
    # mutation control: drop one coverage entry from a copy; round-trip must flip RED
    mutated = json.loads(json.dumps(index))
    for b in mutated["bookings"]:
        if b["booking"] == "VSB-1":
            b["write_sites"] = [s for s in b["write_sites"] if "name->oid" not in s]
    ok2, _ = gate2(mutated)
    if ok2:
        reasons.append("mutation control NOT caught: index with removed write site still passes G2")
    return not reasons, reasons


def selftest() -> int:
    t0 = time.time()
    index = load_index()
    results = {}
    for name, fn in (("G1", gate1), ("G2", gate2), ("G3", gate3)):
        results[name] = fn(index)
    ok = all(r[0] for r in results.values())
    for name, (passed, reasons) in results.items():
        print(f"{name} {'PASS' if passed else 'FAIL'}" + (f": {reasons}" if reasons else ""))
    elapsed = time.time() - t0
    if elapsed > 5.0:
        print(f"G4 FAIL: selftest took {elapsed:.2f}s (> 5s)")
        ok = False
    else:
        print(f"G4 PASS ({elapsed:.3f}s, CPU-only, no network)")
    print("selftest:", "OK" if ok else "FAIL")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "selftest":
        return selftest()
    if len(argv) >= 3 and argv[1] == "taint":
        hits = taint(argv[2], load_index())
        print(json.dumps(hits, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
