#!/usr/bin/env python3
"""QG1d-SUCCESSOR — readout-function census over the exp022 anchor pairs (analysis-only).

Pre-registration: proposals/runs/QG1d-SUCCESSOR-readout-census.md (committed+pushed BEFORE fire).
Reuses qg1c machinery (embed/perm/swap conventions). New axis: readout f(p000,p111), frozen R0-R3,
crossed with wire conventions C0 and C3. Gates G1-G3 per prereg. No post-hoc candidates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "experiments"))
import qg1c_swap_convention as Q  # noqa: E402  (main-guarded census machinery)

OUT = LAB / "results" / "qg1d_successor"
OUT.mkdir(parents=True, exist_ok=True)
TOL = Q.TOL

READOUTS = {
    "R0_min":    lambda a, b: torch.minimum(a, b),
    "R1_p000":   lambda a, b: a,
    "R2_p111":   lambda a, b: b,
    "R3_mean":   lambda a, b: (a + b) / 2,
}
WIRES = {"C0": "C0_current", "C3": "C3_both_reversed"}


def probs_for(cfg_name: str):
    cfg = Q.CANDIDATES[cfg_name]
    gu = Q.make_genome_unitary(
        Q.make_embed1(cfg["reverse_embed"]), Q.make_perm(cfg["reverse_perm"]),
        cfg["swap_single"], cfg["reverse_order"])
    streams, uniq = Q.load_pairs()
    keys = list(uniq.keys())
    M = torch.stack([gu(uniq[k]) for k in keys]).to(Q.DEV)
    e0 = torch.zeros(len(keys), 8, 1, dtype=torch.complex128, device=Q.DEV)
    e0[:, 0, 0] = 1
    s = torch.bmm(M, e0).squeeze(-1)
    p000 = (s[:, 0].abs() ** 2).cpu()
    p111 = (s[:, 7].abs() ** 2).cpu()
    PB = {keys[i]: (float(p000[i]), float(p111[i])) for i in range(len(keys))}
    return streams, uniq, PB


def anchor_cell(streams, uniq, PB, f):
    rows, ok, tot = [], 0, 0
    for kk in streams:
        for gi, c in streams[kk]:
            a, b = PB[Q.R.key(c["genome"])]
            e = float(f(torch.tensor(a), torch.tensor(b)))
            for obs in ("train_p", "verify_p"):
                rec = c[obs]
                tot += 1
                good = abs(e - rec) <= TOL
                ok += int(good)
                rows.append({"stream": kk, "gen": gi, "observable": obs,
                             "recorded": rec, "exact": e, "fail": not good,
                             "genome_key": Q.R.key(c["genome"])})
    return {"anchor": ok / tot, "ok": ok, "total": tot, "rows": rows}


def sigma_bound(rows, PB):
    """G3: binomial 4-sigma test on remaining failures (n=512 shots)."""
    out, outside = [], 0
    fails = [r for r in rows if r["fail"]]
    for r in fails:
        p = r["exact"]
        sig = (max(p * (1 - p), 1e-12) / 512) ** 0.5
        inb = abs(p - r["recorded"]) <= 4 * sig
        outside += int(not inb)
        out.append({k: r[k] for k in ("stream", "gen", "observable", "recorded", "exact")} | {"outside_4sigma": not inb})
    return {"n_failing": len(fails), "outside_4sigma": outside, "rows": out}


def main() -> None:
    results = {}
    cells = {}
    for wname, cfg_name in WIRES.items():
        streams, uniq, PB = probs_for(cfg_name)
        for rname, f in READOUTS.items():
            cell = anchor_cell(streams, uniq, PB, f)
            cells[(wname, rname)] = cell
            results[f"{wname}x{rname}"] = {"anchor": cell["anchor"], "ok": cell["ok"], "total": cell["total"]}
            print(f"{wname}x{rname}  anchor {cell['anchor']:.4f} ({cell['ok']}/{cell['total']})")

    # G1
    g1 = [k for k, c in cells.items() if c["ok"] == c["total"]]
    # G2: readout fixes all 28 C0-fails while keeping C0 anchors
    base = cells[("C0", "R0_min")]
    fails0 = [r for r in base["rows"] if r["fail"]]
    fail_keys = {(r["stream"], r["gen"], r["observable"]) for r in fails0}
    g2 = None
    for rname, f in READOUTS.items():
        c = cells[("C0", rname)]
        fixed = all(not x["fail"] for x in c["rows"] if (x["stream"], x["gen"], x["observable"]) in fail_keys)
        kept = all(not x["fail"] for x in c["rows"] if (x["stream"], x["gen"], x["observable"]) not in fail_keys)
        if fixed and kept:
            g2 = f"R0-residual fixed by {rname} (anchors kept)"
            break
    # G3 on best cell (max anchor, C0xR0 tie-break first)
    best = max(cells.items(), key=lambda kv: (kv[1]["ok"], kv[0] == ("C0", "R0_min")))
    g3 = sigma_bound(best[1]["rows"], None)

    verdict = "NAMED:" + "+".join(g1[0]) if g1 else (f"READOUT ({g2})" if g2 else "NONE")
    out = {"cells": results, "G1_named_cells": [f"{a}x{b}" for a, b in g1],
           "G2": g2, "G3": g3, "verdict": verdict,
           "tol": TOL, "frozen_set": "R0-R3 x {C0,C3}"}
    (OUT / "results.json").write_text(json.dumps(out, indent=1))
    print("VERDICT:", verdict)
    print("G2:", g2)
    print("G3:", json.dumps({k: v for k, v in g3.items() if k != "rows"}))


if __name__ == "__main__":
    main()
