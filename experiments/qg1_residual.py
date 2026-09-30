#!/usr/bin/env python3
"""QG1-residual — localize the 28/1920 anchor misses (analysis-only arbitration).

Pre-registration: proposals/runs/QG1-residual.md (frozen and committed BEFORE this
file was written). Decides CLOSE (the 28 misses are the 512-shot noise tail; the
original 99%-within-2sigma bar was internally inconsistent) vs NAME (a gate-convention
subpopulation the census readout gets wrong).

Machinery (gate2/embed1/perm/genome_unitary/key) is copied verbatim from
experiments/qg1_exact_census.py — that module is script-style (no main guard;
QO3 lesson), so importing it would re-run the census. Copy declared here.
Corpus: /home/eileen/projects/micromoth-quilt/receipts/exp022-desert-break/
exp022.telemetry.{k3..k7}.jsonl — read-only.

Two-sided exact tests, no scipy: binomial pmf via lgamma; Fisher 2x2 two-sided via
the "all tables no more probable than observed" rule; BH step-up at q=0.01.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import torch

LAB = Path(__file__).resolve().parent.parent
CORPUS = Path("/home/eileen/projects/micromoth-quilt/receipts/exp022-desert-break")
OUT = LAB / "results" / "qg1_residual"
DEV = "cuda" if torch.cuda.is_available() else "cpu"
N_SHOTS = 512
FAIL_TOL = 0.044          # same threshold as the census
REBAND_Z = 2.5758         # two-sided 99% normal quantile
BH_Q = 0.01
FISHER_ALPHA = 0.001
FLAGS = ["h", "x", "rx", "rz", "crx", "cx", "swap"]


# ---------- verbatim from experiments/qg1_exact_census.py ----------
def gate2(g):
    n = g[0]
    if n == "h":  return torch.tensor([[1,1],[1,-1]], dtype=torch.complex128)/math.sqrt(2)
    if n == "x":  return torch.tensor([[0,1],[1,0]], dtype=torch.complex128)
    if n == "rx":
        t = float(g[1])/2
        return torch.tensor([[complex(math.cos(t),0),complex(0,-math.sin(t))],[complex(0,-math.sin(t)),complex(math.cos(t),0)]], dtype=torch.complex128)
    if n == "rz":
        t = float(g[1])/2
        return torch.tensor([[complex(math.cos(t),-math.sin(t)),0],[0,complex(math.cos(t),math.sin(t))]], dtype=torch.complex128)
    raise ValueError(f"unknown 1q gate {n}")


def kron(a, b): return torch.kron(a, b)


def embed1(u, q):
    ops = [torch.eye(2, dtype=torch.complex128) for _ in range(3)]
    ops[q] = u
    M = ops[0]
    for o in ops[1:]:
        M = kron(M, o)
    return M


def perm(pairs):  # permutation matrix from index map old->new
    P = torch.zeros(8, 8, dtype=torch.complex128)
    for st in range(8):
        nx = st
        for (a, b) in pairs:
            if st == a: nx = b
            elif st == b: nx = a
        P[nx, st] = 1
    return P


def genome_unitary(genome):
    M = torch.eye(8, dtype=torch.complex128)
    for g in genome:
        n = g[0]
        if n in ("h", "x", "rx", "rz"): M = embed1(gate2(g), int(g[-1])) @ M
        elif n == "crx":
            th, c, t = float(g[1]), int(g[2]), int(g[3])
            U = embed1(gate2(["rx", g[1], t]), t)
            P0, P1 = torch.zeros(8, 8, dtype=torch.complex128), torch.zeros(8, 8, dtype=torch.complex128)
            for st in range(8):
                if (st >> (2 - c)) & 1: P1[st, st] = 1
                else: P0[st, st] = 1
            M = (P0 + P1 @ U) @ M
        elif n == "cx": M = perm([(int(g[1]), int(g[2]))]) @ M
        elif n == "swap": M = perm([(int(g[1]), int(g[2])), (int(g[2]), int(g[1]))]) @ M
        else: raise ValueError(f"unknown gate {n}")
    return M


def key(g): return str([(t[0],) + tuple(round(float(x), 6) if isinstance(x, (int, float)) else x for x in t[1:]) for t in g])


# ---------- exact-test helpers (no scipy) ----------
def lchoose(n, k): return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def binom_pmf(k, n, p):
    if p <= 0.0: return 1.0 if k == 0 else 0.0
    if p >= 1.0: return 1.0 if k == n else 0.0
    return math.exp(lchoose(n, k) + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_two_sided(k, n, p):
    """Exact two-sided: sum of all outcomes at most as probable as the observed."""
    if p <= 0.0: return 1.0 if k == 0 else 0.0
    if p >= 1.0: return 1.0 if k == n else 0.0
    obs = binom_pmf(k, n, p)
    tol = obs * (1 + 1e-9)
    return min(1.0, sum(binom_pmf(j, n, p) for j in range(n + 1) if binom_pmf(j, n, p) <= tol))


def fisher_two_sided(a, b, c, d):
    """2x2 table [[a,b],[c,d]]; two-sided via sum of hypergeometric tables with
    probability <= observed, conditional on both margins."""
    row1, col1, N = a + b, a + c, a + b + c + d
    lo, hi = max(0, row1 + col1 - N), min(row1, col1)
    def pr(x): return math.exp(lchoose(col1, x) + lchoose(N - col1, row1 - x) - lchoose(N, row1))
    obs = pr(a); tol = obs * (1 + 1e-9)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= tol))


def bh_rejections(ps, q):
    """BH step-up: largest i (1-indexed, ascending ps) with ps[i-1] <= i*q/m."""
    m = len(ps)
    sp = sorted(ps)
    k = 0
    for i in range(1, m + 1):
        if sp[i - 1] <= i * q / m:
            k = i
    return k


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    # ---- corpus (identical loading to the census) ----
    streams = {}
    for kk in ["k3", "k4", "k5", "k6", "k7"]:
        lines = [json.loads(l) for l in open(CORPUS / f"exp022.telemetry.{kk}.jsonl")]
        streams[kk] = [(gi, c) for gi, line in enumerate(lines) for c in line["census"]["cloud"]]

    uniq = {}
    for kk in streams:
        for gi, c in streams[kk]:
            uniq.setdefault(key(c["genome"]), c["genome"])
    genomes = list(uniq.values())
    keys = list(uniq.keys())
    KIDX = {kk: i for i, kk in enumerate(keys)}

    # ---- exact balances, batched on GPU (same as census) ----
    M = torch.stack([genome_unitary(g) for g in genomes]).to(DEV)
    e0 = torch.zeros(len(genomes), 8, 1, dtype=torch.complex128, device=DEV); e0[:, 0, 0] = 1
    s = torch.bmm(M, e0).squeeze(-1)
    p_bal = torch.minimum(s[:, 0].abs() ** 2, s[:, 7].abs() ** 2).cpu()
    PB = {keys[i]: float(p_bal[i]) for i in range(len(keys))}

    # ---- per-pair arbitration quantities ----
    pairs = []          # one row per (stream, gen, observable)
    for kk in ["k3", "k4", "k5", "k6", "k7"]:
        for gi, c in streams[kk]:
            for obs_name in ("train_p", "verify_p"):
                rec = c[obs_name]
                p0 = min(max(PB[key(c["genome"])], 0.0), 1.0)
                kshots = int(round(rec * N_SHOTS))
                dev = rec - p0
                pairs.append({
                    "stream": kk, "gen": gi, "observable": obs_name,
                    "recorded": rec, "exact": p0, "k": kshots,
                    "dev": dev, "fail": abs(dev) > FAIL_TOL,
                    "pval": binom_two_sided(kshots, N_SHOTS, p0),
                    "in_reband": abs(dev) <= REBAND_Z * math.sqrt(max(p0 * (1 - p0), 1e-12) / N_SHOTS),
                    "genome_key": key(c["genome"]),
                })
    assert len(pairs) == 1920, f"expected 1920 pairs, got {len(pairs)}"
    fails = [r for r in pairs if r["fail"]]

    # ---- G-LOCALIZE census table ----
    def flags_of(genome):
        names = [g[0] for g in genome]
        return {f: (f in names) for f in FLAGS}

    def angles_of(genome):
        out = []
        for g in genome:
            if g[0] in ("rx", "rz"):
                out.append([g[0], round(float(g[1]), 6), int(g[-1])])
            elif g[0] == "crx":
                out.append(["crx", round(float(g[1]), 6), int(g[2]), int(g[3])])
        return out

    table = [{
        "stream": r["stream"], "gen": r["gen"], "observable": r["observable"],
        "recorded": round(r["recorded"], 6), "exact": round(r["exact"], 6),
        "dev": round(r["dev"], 6), "k_of_512": r["k"],
        "gate_multiset": sorted(g[0] for g in uniq[r["genome_key"]]),
        "flags": flags_of(uniq[r["genome_key"]]),
        "angles": angles_of(uniq[r["genome_key"]]),
        "pair_pval": r["pval"],
    } for r in fails]
    signed_mean_dev = sum(r["dev"] for r in fails) / len(fails) if fails else 0.0

    # ---- ENRICHMENT: Fisher per flag over all 1920 pairs ----
    enrichment = {}
    for f in FLAGS:
        present = [r for r in pairs if flags_of(uniq[r["genome_key"]])[f]]
        if len(present) == 0 or len(present) == len(pairs):
            enrichment[f] = {"n_present": len(present), "fisher_p": "n/a"}
            continue
        a = sum(1 for r in present if r["fail"])
        b = len(fails) - a
        c = len(present) - a
        d = len(pairs) - len(fails) - c
        p = fisher_two_sided(a, b, c, d)
        enrichment[f] = {"n_present": len(present), "failing_with_flag": a,
                         "failing_rate_with": a / len(present),
                         "failing_rate_without": b / (len(pairs) - len(present)),
                         "fisher_p": p, "enriches": p < FISHER_ALPHA}

    # ---- CALIBRATION + RE-BAND ----
    bh = bh_rejections([r["pval"] for r in pairs], BH_Q)
    reband_frac = sum(1 for r in pairs if r["in_reband"]) / len(pairs)

    gates = {
        "G_CLOSE": (bh == 0
                    and all(not (isinstance(v["fisher_p"], float) and v["enriches"]) for v in enrichment.values())
                    and reband_frac >= 0.99),
    }
    strongest = min((v for v in enrichment.values() if isinstance(v["fisher_p"], float)),
                    key=lambda v: v["fisher_p"], default=None)
    verdict = "CLOSE" if gates["G_CLOSE"] else "NAME"
    res = {
        "n_pairs": len(pairs), "n_failing": len(fails), "fail_rate": len(fails) / len(pairs),
        "signed_mean_dev_failing": signed_mean_dev,
        "bh_rejections_q0.01": bh,
        "reband99_fraction": reband_frac,
        "enrichment": enrichment,
        "strongest_flag": strongest,
        "gates": gates, "verdict": verdict,
        "fire_time_pins": {
            "runner_sha256": sha256(Path(__file__)),
            "prereg_sha256": sha256(LAB / "proposals/runs/QG1-residual.md"),
            "telemetry_sha256": {f"exp022.telemetry.{kk}.jsonl": sha256(CORPUS / f"exp022.telemetry.{kk}.jsonl")
                                 for kk in ["k3", "k4", "k5", "k6", "k7"]},
            "device": DEV,
        },
        "failing_table": table,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(OUT / "results.json", "w"), indent=1, default=str)
    print(f"pairs {len(pairs)} | failing {len(fails)} ({len(fails)/len(pairs):.4f}) | signed mean dev {signed_mean_dev:+.5f}")
    print(f"BH rejections @q=0.01: {bh} | re-band-99% fraction: {reband_frac:.4f}")
    for f, v in enrichment.items():
        print(f"  flag {f:4s}: n={v['n_present']:5d} fisher_p={v['fisher_p']}")
    print("VERDICT:", verdict, "| gates:", gates)


if __name__ == "__main__":
    main()
