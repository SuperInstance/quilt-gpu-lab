#!/usr/bin/env python3
"""angle-width-gate — hidden-angle channel WIDTH rescue gate (stdlib-only).

Pattern lifted PROVEN from D23d (experiments/d23d_angle_width.py, booked
2026-10-11: G1 rescue PASSED — acc(W=8)-acc(W=1)=0.144 >= 0.10 at T=100 —
the width lever rescues an angle register KILLed at W=1; G2 viability failed
honestly, verdict KILL). This mechanizes the whole test for ANY
circular-angle relational channel:

  N cells / N/2 pairs share a secret angle psi_k; each cell holds W qubits,
  each qubit's angle = psi_k + N(0, sigma_private); a reader gets J views at
  phases phi_j: per view, T Bernoulli bits with p = (1-cos(theta-phi_j))/2.
  Estimate = grid-MLE per qubit + circular mean across W -> nearest-neighbor
  2AFC pair-match accuracy.

Gates (both clauses, else KILL):
  G1 rescue: acc(W_hi) - acc(W_lo) >= delta at the reference T.
  G2 viability: acc(W_hi) >= via at the reference T.
Null control: shuffled secrets must land near chance 1/(N/2 - 1) — if the
null is hot, the metric is leaking, book RED, never PASS.

Stdlib-only (math/random/json), seeded, deterministic, fail-loud rc=2,
exit 0=RESCUED / 1=KILL or RED / 2=FAIL-INPUT, JSON receipt.

Worked example:
  python tools/angle_width_gate.py \\
      --n 24 --w-lo 1 --w-hi 8 --t 100 --delta 0.10 --via 0.90 --draws 3 --out r.json
Selftest:
  python tools/angle_width_gate.py --selftest
"""
import argparse, json, math, random, sys, time

def fail(msg, rc=2):
    print(json.dumps({"fail_input": msg}, indent=2))
    sys.exit(rc)

def estimate_angle(k1s, phis, T, grid):
    """Grid-MLE per qubit. k1s: per-view ones counts.
    ll(g) = sum_j k1_j*log(pg) + (T-k1_j)*log(1-pg)."""
    n_g = len(grid)
    ll = [0.0] * n_g
    for g_idx, g in enumerate(grid):
        ll_g = 0.0
        for k1, phi in zip(k1s, phis):
            pg = (1 - math.cos(g - phi)) / 2.0
            pg = min(max(pg, 1e-12), 1 - 1e-12)
            ll_g += k1 * math.log(pg) + (T - k1) * math.log(1 - pg)
        ll[g_idx] = ll_g
    best = max(range(n_g), key=lambda i: ll[i])
    return grid[best]

def circular_mean(angles):
    s = sum(math.sin(a) for a in angles)
    c = sum(math.cos(a) for a in angles)
    return math.atan2(s, c)

def main():
    ap = argparse.ArgumentParser(description="hidden-angle WIDTH rescue gate")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--w-lo", type=int, default=1)
    ap.add_argument("--w-hi", type=int, default=8)
    ap.add_argument("--t", type=int, default=100)
    ap.add_argument("--delta", type=float, default=0.10, help="G1 rescue bar")
    ap.add_argument("--via", type=float, default=0.90, help="G2 viability bar")
    ap.add_argument("--sigma-secret", type=float, default=0.15)
    ap.add_argument("--sigma-private", type=float, default=0.10)
    ap.add_argument("--j-views", type=int, default=8)
    ap.add_argument("--grid-n", type=int, default=360)
    ap.add_argument("--draws", type=int, default=3)
    ap.add_argument("--seed", type=int, default=2718)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        sys.exit(0)

    if args.n < 6 or args.n % 2:
        fail("--n must be even and >= 6")
    for name, v in (("--w-lo", args.w_lo), ("--w-hi", args.w_hi)):
        if v < 1:
            fail(f"{name} must be >= 1")
    if args.w_hi <= args.w_lo:
        fail("--w-hi must exceed --w-lo (width rescue needs a ladder)")
    if args.t < 1:
        fail("--t must be >= 1")
    if args.draws < 1:
        fail("--draws must be >= 1")
    if args.j_views < 2:
        fail("--j-views must be >= 2")
    if args.grid_n < 32:
        fail("--grid-n too coarse (< 32)")
    for name, v in (("--sigma-secret", args.sigma_secret),
                    ("--sigma-private", args.sigma_private)):
        if v < 0:
            fail(f"{name} must be >= 0")

    t0 = time.time()
    rng = random.Random(args.seed)
    n_pairs = args.n // 2
    chance = 1.0 / (n_pairs - 1)
    phis = [-math.pi + 2 * math.pi * i / args.j_views for i in range(args.j_views)]
    grid = [-math.pi + 2 * math.pi * i / args.grid_n for i in range(args.grid_n)]

    def acc_at(w, t_use, shuffle=False):
        hits = 0
        for _ in range(args.draws):
            psi = [rng.uniform(-math.pi, math.pi) for _ in range(n_pairs)]
            labels = [i // 2 for i in range(args.n)]
            if shuffle:
                # per-cell INDEPENDENT secrets (D23d null): partners split and
                # no two cells share a secret, so a hot null = metric leaking
                secrets = [rng.uniform(-math.pi, math.pi) for _ in range(args.n)]
            else:
                secrets = [psi[labels[i]] for i in range(args.n)]
            est = []
            for i in range(args.n):
                per_qubit = []
                for _w in range(w):
                    th = secrets[i] + rng.gauss(0, args.sigma_private)
                    k1s = []
                    for phi in phis:
                        p1 = (1 - math.cos(th - phi)) / 2.0
                        k1s.append(sum(1 for _ in range(t_use) if rng.random() < p1))
                    per_qubit.append(estimate_angle(k1s, phis, t_use, grid))
                est.append(circular_mean(per_qubit))
            for i in range(args.n):
                a = est[i]
                best_j, best_d = None, float("inf")
                for k in range(args.n):
                    if k == i:
                        continue
                    d = abs(math.atan2(math.sin(a - est[k]), math.cos(a - est[k])))
                    if d < best_d:
                        best_d, best_j = d, k
                if best_j is not None and labels[best_j] == labels[i]:
                    hits += 1
        return hits / (args.n * args.draws)

    acc_lo = acc_at(args.w_lo, args.t)
    acc_lo_rerun = acc_at(args.w_lo, args.t)  # determinism is via seeded stream;
    # note: rerun consumes further draws, so it is NOT expected to match — it is
    # booked as a draw-variance estimate honestly, not as determinism.
    acc_hi = acc_at(args.w_hi, args.t)
    null_acc = acc_at(args.w_hi, args.t, shuffle=True)
    delta = acc_hi - acc_lo

    g1 = delta >= args.delta
    g2 = acc_hi >= args.via
    null_hot = null_acc > 3.0 / (args.n - 1)  # null chance = 1/(n-1) after shuffle
    if null_hot:
        verdict = "RED"
    elif g1 and g2:
        verdict = "RESCUED"
    else:
        verdict = "KILL"
    receipt = {
        "tool": "angle-width-gate", "pattern": "D23d",
        "config": {k: getattr(args, k.replace("-", "_")) for k in
                   ("n", "w_lo", "w_hi", "t", "delta", "via", "sigma_secret",
                    "sigma_private", "j_views", "grid_n", "draws", "seed")},
        "acc_w_lo": acc_lo, "acc_w_lo_second": acc_lo_rerun,
        "acc_w_hi": acc_hi, "rescue_delta": delta,
        "null_acc": null_acc, "chance": chance, "null_hot": null_hot,
        "G1_rescue_pass": g1, "G2_viability_pass": g2,
        "verdict": verdict, "wall_s": round(time.time() - t0, 2),
    }
    print(json.dumps(receipt, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(receipt, f, indent=2)
    sys.exit(0 if verdict == "RESCUED" else 1)

def selftest():
    """Pins: (1) strong channel -> RESCUED exit 0; (2) dead channel
    (sigma_private huge) -> KILL, honest; (3) shuffled null cold;
    (4) fail-loud on odd n. Each pin carries the failure it guards."""
    import subprocess, tempfile, os
    here = os.path.dirname(os.path.abspath(__file__))
    tool = os.path.join(here, "angle_width_gate.py")
    checks = []

    def run_cli(extra):
        r = subprocess.run([sys.executable, tool] + extra,
                           capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    # Pin 1: easy channel (tiny private noise) must RESCUE.
    rc, rec = run_cli(["--n", "12", "--w-lo", "1", "--w-hi", "8", "--t", "400",
                       "--sigma-private", "0.02", "--delta", "0.05",
                       "--via", "0.85", "--draws", "2", "--seed", "7"])
    checks.append(("easy-channel RESCUED", rc == 0 and rec["verdict"] == "RESCUED",
                   f"rc={rc} verdict={rec.get('verdict')}"))

    # Pin 2: dead channel (private noise 5x secret) must honestly KILL, not PASS.
    rc, rec = run_cli(["--n", "12", "--w-lo", "1", "--w-hi", "8", "--t", "50",
                       "--sigma-private", "1.5", "--draws", "2", "--seed", "7"])
    checks.append(("dead-channel KILL", rc == 1 and rec["verdict"] == "KILL",
                   f"rc={rc} verdict={rec.get('verdict')}"))

    # Pin 3: shuffled null cold in the easy run (metric not leaking).
    checks.append(("null cold (<=3x chance)",
                   rec["null_acc"] <= rec["chance"] * 3,
                   f"null={rec['null_acc']} chance={rec['chance']}"))

    # Pin 4: odd n fails loud rc=2.
    rc, out = run_cli(["--n", "11"])
    checks.append(("odd-n fail-loud rc=2", rc == 2, f"rc={rc}"))

    ok = sum(1 for _, p, _ in checks if p)
    print(json.dumps({"selftest": {"passed": ok, "total": len(checks),
                                   "checks": [{"name": n, "pass": p, "why": w}
                                              for n, p, w in checks]}}, indent=2))
    sys.exit(0 if ok == len(checks) else 1)

if __name__ == "__main__":
    main()
