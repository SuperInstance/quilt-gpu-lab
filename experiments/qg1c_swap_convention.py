#!/usr/bin/env python3
"""QG1c — swap/wire-order convention: corrected census (analysis-only, frozen candidate set).

Pre-registration: proposals/runs/QG1c-swap-convention.md (frozen + committed BEFORE fire).
Builds on QG1-residual (BOOKED: NAME; swap Fisher 7.0e-19 owns the 28 miss).

Machinery is imported from experiments/qg1_residual.py (main-guarded => safe to import;
that module carries the BOOKING machinery: pi-unit gate2 + census embed1/perm XOR-map).
Candidates are parameterized variants of {embed1 index map, perm index map, swap pair
expansion, gate application order} — frozen set C0..C5, no post-hoc expansion.

Corpus: /home/eileen/projects/micromoth-quilt/receipts/exp022-desert-break/ (read-only).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import torch

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "experiments"))
import qg1_residual as R  # noqa: E402  (main-guarded; booking machinery = pi-units)

OUT = LAB / "results" / "qg1c_swap_convention"
DEV = "cuda" if torch.cuda.is_available() else "cpu"
TOL = 0.044
FLAGS = R.FLAGS


def kron(a, b): return torch.kron(a, b)


def make_embed1(reverse: bool):
    def embed1(u, q):
        qq = (2 - q) if reverse else q
        I = torch.eye(2, dtype=torch.complex128)
        return (kron(kron(u, I), I) if qq == 0
                else (kron(kron(I, u), I) if qq == 1 else kron(kron(I, I), u)))
    return embed1


def make_perm(reverse: bool):
    def perm(pairs):
        P = torch.zeros(8, 8, dtype=torch.complex128)
        for s in range(8):
            b = [(s >> (2 - q)) & 1 for q in range(3)]
            for c, t in pairs:
                c2 = (2 - c) if reverse else c
                t2 = (2 - t) if reverse else t
                b[t2] ^= b[c2]
            P[(b[0] << 2) | (b[1] << 1) | b[2], s] = 1
        return P
    return perm


def make_genome_unitary(embed1, perm, swap_single: bool, reverse_order: bool):
    def genome_unitary(genome):
        gates = []
        for g in genome:
            n = g[0]
            if n in ("h", "x", "rx", "rz"):
                gates.append(embed1(R.gate2(g), int(g[-1])))
            elif n == "crx":
                th, c, t = float(g[1]), int(g[2]), int(g[3])
                c2 = int(g[2]); t2 = int(g[3])
                # apply the embed1 index map to the crx qubits too
                U = embed1(R.gate2(["rx", g[1], t2]), t2)
                P0 = torch.zeros(8, 8, dtype=torch.complex128)
                P1 = torch.zeros(8, 8, dtype=torch.complex128)
                for st in range(8):
                    bit = (st >> (2 - c2)) & 1
                    (P1 if bit else P0)[st, st] = 1
                gates.append(P0 + P1 @ U)
            elif n == "cx":
                gates.append(perm([(int(g[1]), int(g[2]))]))
            elif n == "swap":
                a, b = int(g[1]), int(g[2])
                gates.append(perm([(a, b)]) if swap_single else perm([(a, b), (b, a)]))
            else:
                raise ValueError(f"unknown gate {n}")
        if reverse_order:
            gates = list(reversed(gates))
        M = torch.eye(8, dtype=torch.complex128)
        for U in gates:
            M = U @ M
        return M
    return genome_unitary


CANDIDATES = {
    "C0_current":           dict(reverse_embed=False, reverse_perm=False, swap_single=False, reverse_order=False),
    "C1_embed_reversed":    dict(reverse_embed=True,  reverse_perm=False, swap_single=False, reverse_order=False),
    "C2_perm_reversed":     dict(reverse_embed=False, reverse_perm=True,  swap_single=False, reverse_order=False),
    "C3_both_reversed":     dict(reverse_embed=True,  reverse_perm=True,  swap_single=False, reverse_order=False),
    "C4_order_reversed":    dict(reverse_embed=False, reverse_perm=False, swap_single=False, reverse_order=True),
    "C5_swap_as_cnot":      dict(reverse_embed=False, reverse_perm=False, swap_single=True,  reverse_order=False),
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_pairs():
    streams = {}
    for kk in ["k3", "k4", "k5", "k6", "k7"]:
        lines = [json.loads(l) for l in open(R.CORPUS / f"exp022.telemetry.{kk}.jsonl")]
        streams[kk] = [(gi, c) for gi, line in enumerate(lines) for c in line["census"]["cloud"]]
    uniq = {}
    for kk in streams:
        for gi, c in streams[kk]:
            uniq.setdefault(R.key(c["genome"]), c["genome"])
    return streams, uniq


def anchor_for(streams, uniq, genome_unitary):
    keys = list(uniq.keys())
    M = torch.stack([genome_unitary(uniq[k]) for k in keys]).to(DEV)
    e0 = torch.zeros(len(keys), 8, 1, dtype=torch.complex128, device=DEV); e0[:, 0, 0] = 1
    s = torch.bmm(M, e0).squeeze(-1)
    p_bal = torch.minimum(s[:, 0].abs() ** 2, s[:, 7].abs() ** 2).cpu()
    PB = {keys[i]: float(p_bal[i]) for i in range(len(keys))}

    rows = []
    ok = tot = 0
    for kk in streams:
        for gi, c in streams[kk]:
            e = PB[R.key(c["genome"])]
            for obs in ("train_p", "verify_p"):
                rec = c[obs]; tot += 1
                good = abs(e - rec) <= TOL
                ok += int(good)
                rows.append({"stream": kk, "gen": gi, "observable": obs,
                             "recorded": rec, "exact": e, "fail": not good,
                             "genome_key": R.key(c["genome"])})
    return {"anchor": ok / tot, "ok": ok, "total": tot, "rows": rows}


def enrich(rows, uniq):
    fails = [r for r in rows if r["fail"]]
    out = {}
    for f in FLAGS:
        def has(r): return f in [g[0] for g in uniq[r["genome_key"]]]
        present = [r for r in rows if has(r)]
        if len(present) == 0 or len(present) == len(rows):
            out[f] = {"n_present": len(present), "fisher_p": "n/a"}; continue
        a = sum(1 for r in present if r["fail"]); b = len(fails) - a
        c = len(present) - a; d = len(rows) - len(fails) - c
        out[f] = {"n_present": len(present), "failing_with_flag": a,
                  "fisher_p": R.fisher_two_sided(a, b, c, d),
                  "enriches": R.fisher_two_sided(a, b, c, d) < 0.001}
    return {"n_failing": len(fails), "enrichment": out}


def main() -> None:
    streams, uniq = load_pairs()
    results = {}
    for name, cfg in CANDIDATES.items():
        e1 = make_embed1(cfg["reverse_embed"])
        pm = make_perm(cfg["reverse_perm"])
        gu = make_genome_unitary(e1, pm, cfg["swap_single"], cfg["reverse_order"])
        a = anchor_for(streams, uniq, gu)
        en = enrich(a["rows"], uniq)
        results[name] = {"anchor": a["anchor"], "n_failing": en["n_failing"],
                         "enrichment": en["enrichment"], "rows": a["rows"]}
        print(f"{name:20s} anchor {a['anchor']:.4f} ({a['ok']}/{a['total']}) failing {en['n_failing']}")

    base = results["C0_current"]
    fails0 = [r for r in base["rows"] if r["fail"]]
    def has(r, f): return f in [g[0] for g in uniq[r["genome_key"]]]
    decomp = {
        "n_failing_C0": len(fails0),
        "swap_and_x": sum(1 for r in fails0 if has(r, "swap") and has(r, "x")),
        "swap_only": sum(1 for r in fails0 if has(r, "swap") and not has(r, "x")),
        "x_only": sum(1 for r in fails0 if not has(r, "swap") and has(r, "x")),
        "neither": sum(1 for r in fails0 if not has(r, "swap") and not has(r, "x")),
    }

    best = max(results.items(), key=lambda kv: kv[1]["anchor"])
    best_name, best_res = best
    best_clean = all(not (isinstance(v["fisher_p"], float) and v.get("enriches"))
                     for v in best_res["enrichment"].values())
    if best_res["anchor"] >= 0.99 and best_clean and best_name != "C0_current":
        verdict = "FIXED"
    elif (best_res["anchor"] - base["anchor"]) >= 0.02:
        verdict = "PARTIAL"
    else:
        verdict = "NONE"

    res = {
        "candidates": {k: {"anchor": v["anchor"], "n_failing": v["n_failing"],
                           "enrichment": v["enrichment"]} for k, v in results.items()},
        "best_candidate": best_name, "best_anchor": best_res["anchor"],
        "swap_vs_x_decomposition_C0": decomp,
        "gates": {"G_FIX": verdict == "FIXED", "G_PARTIAL": verdict == "PARTIAL",
                  "G_NONE": verdict == "NONE"},
        "verdict": verdict,
        "fire_time_pins": {
            "runner_sha256": sha256(Path(__file__)),
            "prereg_sha256": sha256(LAB / "proposals/runs/QG1c-swap-convention.md"),
            "telemetry_sha256": {f"exp022.telemetry.{kk}.jsonl":
                                 sha256(R.CORPUS / f"exp022.telemetry.{kk}.jsonl")
                                 for kk in ["k3", "k4", "k5", "k6", "k7"]},
            "device": DEV,
        },
        "failing_table_C0": [{"stream": r["stream"], "gen": r["gen"], "observable": r["observable"],
                              "recorded": round(r["recorded"], 6), "exact": round(r["exact"], 6),
                              "gates": sorted(g[0] for g in uniq[r["genome_key"]])} for r in fails0],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(OUT / "results.json", "w"), indent=1, default=str)
    print("swap-vs-x decomposition (C0 28):", decomp)
    print("VERDICT:", verdict, "| best:", best_name, f"{best_res['anchor']:.4f}")


if __name__ == "__main__":
    main()
