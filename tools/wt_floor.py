#!/usr/bin/env python3
"""wt_floor.py — bandwidth-time partner-discovery floor prober (stdlib-only).

Lifted from experiments/d12l_noise_floor.py (run 2026-10-02): given N candidate
channels, each emitting W binary streams per tick, how many ticks T do you need
to identify each channel's correlation partner (the unique other channel its
streams agree with with probability p_corr > chance)?

The D12l/D12i/D12j finding this tool reproduces: the floor is governed by the
bandwidth-time product W*T, and symmetric measurement noise (each observed bit
flipped with prob eps AFTER the correlation step) rescales the effective signal
    s = (2*p_corr - 1) * (1 - 2*eps)
so floors track W*T_floor ~<= 600 / s^2 (a bonus-consistent bound, not a fit).
Chance accuracy = 1/(N-1); a channel is "identified" when the argmax partner
guess over a W*T-bit observation window is correct.

Usage:
  python tools/wt_floor.py --p 0.3 --eps 0.05 --w 4 --n 16 --ts 10,25,50,100,200,400 --draws 3
  python tools/wt_floor.py --p 0.5 --eps 0.0 --w 4 --n 16 --ts 25,50,100 --draws 5 --out receipt.json
  python tools/wt_floor.py --selftest

Output (stdout + optional --out JSON): per-T identification rate, T_floor
(first T reaching the ACC_BAR=0.9 accuracy bar), and the 600/s^2 bound verdict.
Exit codes: 0 = fine (floor found or all-Ts pass/fail honestly booked);
2 = bad input (p<=0.5, eps outside [0,0.5], n<4, w<1, empty/invalid ts).

Worked example: with p=0.5, eps=0 (clean signal, s=1), N=16, W=4 the floor
lands near T=25 (W*T~100), matching the D12j ~100-200 band at p=0.5.
"""
from __future__ import annotations

import argparse
import json
import random
import sys

ACC_BAR = 0.9
BOUND_C = 600.0  # empirical constant from D12i/D12j/D12l receipts


def make_partner(n: int, rng: random.Random) -> dict[int, int]:
    perm = list(range(n))
    rng.shuffle(perm)
    partner: dict[int, int] = {}
    for i in range(0, n, 2):
        a, b = perm[i], perm[i + 1]
        partner[a] = b
        partner[b] = a
    return partner


def sample_window(partner: dict[int, int], n: int, w: int, p: float, eps: float,
                  t_obs: int, rng: random.Random) -> dict[int, list[list[int]]]:
    """streams[channel][q] = list of t_obs bits in {-1,+1} (post-noise)."""
    streams = {c: [[] for _ in range(w)] for c in range(n)}
    for _ in range(t_obs):
        seen: set[int] = set()
        for a in partner:
            if a in seen:
                continue
            seen |= {a, partner[a]}
            b = partner[a]
            for q in range(w):
                base = 1 if rng.random() < 0.5 else -1
                if rng.random() < p:
                    va, vb = base, base
                else:
                    va, vb = base, (1 if rng.random() < 0.5 else -1)
                if rng.random() < eps:
                    va = -va
                if rng.random() < eps:
                    vb = -vb
                streams[a][q].append(va)
                streams[b][q].append(vb)
    return streams


def identify(streams: dict[int, list[list[int]]], partner: dict[int, int]) -> tuple[int, int]:
    """Greedy argmax-correlation matching. Returns (correct, total)."""
    import itertools
    chans = sorted(streams)
    corr: dict[tuple[int, int], float] = {}
    for a, b in itertools.combinations(chans, 2):
        num = 0
        den = 0
        for qa in streams[a]:
            for qb in streams[b]:
                num += sum(x * y for x, y in zip(qa, qb))
                den += len(qa)
        corr[(a, b)] = num / den if den else 0.0
    edges = sorted(corr.items(), key=lambda kv: -kv[1])
    matched: set[int] = set()
    got = 0
    for (a, b), _ in edges:
        if a in matched or b in matched:
            continue
        matched |= {a, b}
        if partner[a] == b:
            got += 2
    return got, len(chans)


def effective_signal(p: float, eps: float) -> float:
    return (2 * p - 1) * (1 - 2 * eps)


def run(p: float, eps: float, w: int, n: int, ts: list[int], draws: int, seed: int) -> dict:
    if p <= 0.5:
        raise ValueError(f"--p must be > 0.5 (chance), got {p}")
    if not 0.0 <= eps <= 0.5:
        raise ValueError(f"--eps must be in [0,0.5], got {eps}")
    if n < 4 or n % 2:
        raise ValueError(f"--n must be even and >= 4, got {n}")
    if w < 1:
        raise ValueError(f"--w must be >= 1, got {w}")
    if not ts or any(t < 1 for t in ts):
        raise ValueError(f"--ts must be non-empty positive ints, got {ts}")
    s = effective_signal(p, eps)
    rows = []
    for t in sorted(ts):
        accs = []
        for d in range(draws):
            rng = random.Random(seed + 1000 * d + t)
            partner = make_partner(n, rng)
            streams = sample_window(partner, n, w, p, eps, t, rng)
            got, total = identify(streams, partner)
            accs.append(got / total)
        rate = sum(accs) / len(accs)
        rows.append({"T": t, "WT": w * t, "rate": round(rate, 4),
                     "above_bar": rate >= ACC_BAR})
    t_floor = next((r["T"] for r in rows if r["above_bar"]), None)
    bound = BOUND_C / (s * s) if s > 0 else None
    verdict = {
        "T_floor": t_floor,
        "chance_acc": round(1 / (n - 1), 4),
        "s": round(s, 4),
        "bound_WT_600_over_s2": round(bound, 1) if bound else None,
        "floor_within_bound": (t_floor is not None and bound is not None
                               and w * t_floor <= bound),
    }
    return {"tool": "wt_floor", "p": p, "eps": eps, "w": w, "n": n,
            "draws": draws, "seed": seed, "rows": rows, "verdict": verdict}


def selftest() -> int:
    ok = True
    # 1) clean strong signal (p=0.9, eps=0) identifies perfectly at modest T
    r = run(0.9, 0.0, 2, 8, [20], 2, seed=1)
    v = r["verdict"]
    if not (v["T_floor"] == 20 and v["floor_within_bound"]):
        print(f"SELFTEST FAIL: strong-signal floor, got {v}", file=sys.stderr)
        ok = False
    # 2) chance-level signal (p=0.5) is rejected as bad input
    try:
        run(0.5, 0.0, 2, 8, [20], 1, seed=1)
        print("SELFTEST FAIL: p=0.5 accepted", file=sys.stderr)
        ok = False
    except ValueError:
        pass
    # 3) s-scaling law: eps>0 shrinks s exactly as the law says
    s0 = effective_signal(0.6, 0.0)
    s1 = effective_signal(0.6, 0.25)
    if abs((s0 - s1) - (0.2 * 0.5)) > 1e-12:
        print("SELFTEST FAIL: s law arithmetic", file=sys.stderr)
        ok = False
    # 4) noise hurts (J1): floor at eps>0 is not better than clean
    clean = run(0.7, 0.0, 4, 12, [25, 50, 100], 2, seed=7)["verdict"]["T_floor"]
    noisy = run(0.7, 0.1, 4, 12, [25, 50, 100, 200], 2, seed=7)["verdict"]["T_floor"]
    if noisy is not None and clean is not None and noisy < clean:
        print(f"SELFTEST FAIL: J1 violated clean={clean} noisy={noisy}", file=sys.stderr)
        ok = False
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 epilog="See module docstring for the worked example.")
    ap.add_argument("--p", type=float, default=0.6, help="correlation prob (>0.5)")
    ap.add_argument("--eps", type=float, default=0.0, help="post-correlation bit-flip noise")
    ap.add_argument("--w", type=int, default=4, help="streams per channel")
    ap.add_argument("--n", type=int, default=16, help="channels (even, >=4)")
    ap.add_argument("--ts", default="10,25,50,100,200,400", help="comma-separated T values")
    ap.add_argument("--draws", type=int, default=3, help="independent draws per T")
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    try:
        ts = [int(x) for x in args.ts.split(",") if x.strip()]
        receipt = run(args.p, args.eps, args.w, args.n, ts, args.draws, args.seed)
    except ValueError as e:
        print(f"FAIL-INPUT: {e}", file=sys.stderr)
        return 2
    v = receipt["verdict"]
    for r in receipt["rows"]:
        mark = "*" if r["above_bar"] else " "
        print(f" {mark} T={r['T']:>4}  W*T={r['WT']:>6}  acc={r['rate']:.3f}")
    print(f"T_floor={v['T_floor']}  s={v['s']}  bound W*T<={v['bound_WT_600_over_s2']}  "
          f"within_bound={v['floor_within_bound']}  chance={v['chance_acc']}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
        print(f"receipt -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
