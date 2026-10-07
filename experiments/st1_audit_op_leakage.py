#!/usr/bin/env python3
"""ST1-AUDIT — op-by-op mechanical leakage audit on the ST1 synthetic lane.

Pre-reg: proposals/runs/ST1-AUDIT-op-leakage.md (frozen before fire).
Reuses the committed ST1v2 generator verbatim (import, not copy) so the audit
is anchored to the booked corpus definition. Mechanical discriminators see the
RENDERED TEXT only. --out supported (RC-1 doctrine): verification never writes
into results/.
"""
import argparse, json, random, re, sys, hashlib
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "experiments"))
from st1_quilt_cell_v0 import make_example, corrupt_example, render, SYN_OPS  # noqa: E402

SEED = 2718
N_PER_SIDE = 600

RE_VERDICT = re.compile(r"verdict:\s*(\w+)|\"verdict\":\s*\"(\w+)\"")
RE_MRI = re.compile(r"mean_rel_improvement:\s*([+-]?\d+\.\d+)|\"mean_rel_improvement\":\s*(-?\d+\.?\d*)")
RE_WINS = re.compile(r"wins:\s*(\d+)|\"wins\":\s*(\d+)")
RE_NPAIRS = re.compile(r"of\s+(\d+)\s+pairs|\"n_pairs\":\s*(\d+)")
RE_TAU = re.compile(r"tau:\s*(\d+\.\d+)|\"tau\":\s*(\d+\.?\d*)")
RE_SEEDS = re.compile(r"seeds:|\"seeds\"")

def _g(rx, text, cast=float):
    m = rx.search(text)
    if not m:
        return None
    for grp in m.groups():
        if grp is not None:
            return cast(grp)
    return None

def mechanical_flag(op: str, text: str) -> float:
    from st1_quilt_cell_v0 import honest_verdict
    verdict = _g(RE_VERDICT, text, str)
    mri = _g(RE_MRI, text)
    wins = _g(RE_WINS, text, int)
    npairs = _g(RE_NPAIRS, text, int)
    tau = _g(RE_TAU, text)
    has_seeds = RE_SEEDS.search(text) is not None
    if op in ("sign_flip", "verdict_flip"):
        if None in (verdict, mri, wins, npairs):
            return 0.0
        return 0.0 if honest_verdict(wins, npairs, mri) == verdict else 1.0
    if op in ("wins_over", "denom_swap"):
        if wins is None or npairs is None:
            return 0.0
        return 1.0 if wins > npairs else 0.0
    if op == "tau_off":
        if tau is None:
            return 0.0
        return 0.0 if 0.40 <= tau <= 0.60 else 1.0
    if op == "seed_drop":
        return 0.0 if has_seeds else 1.0
    raise ValueError(f"unknown op {op}")

def auc(scores, labels):
    """Rank AUC with ties (Mann-Whitney)."""
    pos = sorted(s for s, l in zip(scores, labels) if l == 1)
    neg = sorted(s for s, l in zip(scores, labels) if l == 0)
    if not pos or not neg:
        return None
    import bisect
    win = 0.0
    for p in pos:
        lo = bisect.bisect_left(neg, p)
        hi = bisect.bisect_right(neg, p)
        win += lo + 0.5 * (hi - lo)
    return win / (len(pos) * len(neg))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(LAB / "results" / "st1_audit" / "results.json"))
    args = ap.parse_args()
    rng = random.Random(SEED)
    out = {"seed": SEED, "n_per_side": N_PER_SIDE, "ops": {}, "runner_sha256":
           hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    for op in SYN_OPS:
        scores, labels = [], []
        render_kinds = set()
        for label in (0, 1):
            for _ in range(N_PER_SIDE):
                ex = make_example(rng)
                if label:
                    ex = corrupt_example(ex, rng, op)
                # 50/50 render styles as in the booked corpus
                text = render(ex, rng.choice(["template", "json"]))
                render_kinds.add("t" if "receipt " in text else "j")
                scores.append(mechanical_flag(op, text))
                labels.append(label)
        a = auc(scores, labels)
        # DEGENERATE guard: score has zero variance overall (discriminator fires
        # always or never) — cannot speak, per the fleet murmuration law.
        degenerate = len(set(scores)) == 1
        entry = {"auc": a, "degenerate": bool(degenerate),
                 "leaky": (a is not None and a >= 0.95 and not degenerate),
                 "render_kinds": sorted(render_kinds)}
        out["ops"][op] = entry
    leaky = sorted(k for k, v in out["ops"].items() if v["leaky"])
    degen = sorted(k for k, v in out["ops"].items() if v["degenerate"])
    out["leaky_ops"] = leaky
    out["degenerate_ops"] = degen
    out["verdict"] = "KEEP-AUDIT" if leaky else "CLEAN"
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
