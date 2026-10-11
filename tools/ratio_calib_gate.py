#!/usr/bin/env python3
"""ratio-calib-gate — one-parameter ratio calibration with heldout invariance.

Pattern lifted PROVEN from D12al/D12am (booked 2026-10-10): when a nuisance
parameter inflates a measured quantity, ABSOLUTE models are unreliable but
RATIOS cancel grid quantization and baseline offset — so fit ONE parameter c
by bisection on the blow-up RATIO at a calibration point, then (G1) re-hit the
fit point, (G2) predict the HELD-OUT point with the SAME c (no refit), and
(G3) check invariance: the c implied by the held-out measurement / c_fit must
sit in band. If implied-c drifts with the sweep variable, the functional FORM
(e.g. rho^2 vs rho^4) is wrong — booked honestly, never a silent PASS.

Model: user supplies --expr, an expression in variables c and rho giving the
MODELED blow-up ratio (e.g. "1 + 25*rho*rho" style with c as the parameter:
"1 + c*rho**2"). Measured pairs: rho:ratio. Stdlib-only, deterministic,
fail-loud rc=2. Exit 0=CALIBRATED / 1=MISFIT, one JSON receipt.

Example (replays D12al W=8 data: rho=0.2 -> 2.00x, rho=0.4 -> 6.40x):
  python tools/ratio_calib_gate.py \
    --expr "1 + c*rho**2" --cal 0.2:2.0 --heldout 0.4:6.4 \
    [--band 0.5,2.0 --inv-band 0.5,2.0 --out r.json]
  -> c_fit=25.0, heldout model 5.0 vs measured 6.4 (ratio 1.28),
     implied-c ratio 1.35 -> CALIBRATED rc=0.

Selftest: python tools/ratio_calib_gate.py --selftest
"""
import argparse
import json
import math
import sys

def fail(msg, rc=2):
    print(json.dumps({"verdict": "FAIL-INPUT", "error": msg}, indent=2))
    sys.exit(rc)

def eval_ratio(expr, c, rho):
    try:
        val = float(eval(expr, {"__builtins__": {}},
                         {"c": c, "rho": rho, "x": rho,
                          "sqrt": math.sqrt, "exp": math.exp, "log": math.log}))
    except Exception as e:
        fail(f"expr {expr!r} failed at c={c}, rho={rho}: {e}")
    if not math.isfinite(val) or val <= 0:
        fail(f"expr returned non-finite/non-positive {val} at c={c}, rho={rho}")
    return val

def parse_pairs(spec, name):
    out = []
    for tok in spec:
        try:
            r, v = tok.split(":")
            r, v = float(r), float(v)
        except ValueError:
            fail(f"--{name} entry {tok!r} not rho:ratio")
        if r < 0 or v <= 0 or not math.isfinite(v):
            fail(f"--{name} entry {tok!r} out of domain")
        out.append((r, v))
    return out

def fit_c(expr, rho, target, lo=1e-9, hi=1e9, iters=200):
    """Bisect c so model(rho, c) == target. Monotone-in-c assumed (checked)."""
    if target <= 0 or not math.isfinite(target):
        fail(f"target {target} at rho={rho} out of domain (must be positive, finite)")
    f_lo, f_hi = eval_ratio(expr, lo, rho), eval_ratio(expr, hi, rho)
    if not (f_lo <= target <= f_hi):
        return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if eval_ratio(expr, mid, rho) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

def in_band(x, band):
    return band[0] <= x <= band[1]

def run(expr, cal, held, band, inv_band):
    if not cal:
        fail("need at least one --cal pair")
    # fit c on the FIRST calibration point (single-parameter doctrine)
    rho0, tgt0 = cal[0]
    c_fit = fit_c(expr, rho0, tgt0)
    if c_fit is None:
        return {"verdict": "MISFIT", "why": f"no c brackets target {tgt0} at rho={rho0}",
                "c_fit": None, "g1": None, "heldout": []}, 1
    g1 = {f"rho={r}": {"measured": t, "model": eval_ratio(expr, c_fit, r),
                       "ratio": t / eval_ratio(expr, c_fit, r),
                       "pass": in_band(t / eval_ratio(expr, c_fit, r), band)}
          for r, t in cal}
    held_rows = []
    g2_all, g3_all = True, True
    for r, t in held:
        model = eval_ratio(expr, c_fit, r)
        g2 = in_band(t / model, band)
        c_impl = fit_c(expr, r, t)
        g3 = c_impl is not None and in_band(c_impl / c_fit, inv_band)
        g2_all &= g2
        g3_all &= g3
        held_rows.append({"rho": r, "measured": t, "model": model,
                          "ratio": t / model, "g2_pass": g2,
                          "c_implied": c_impl,
                          "c_implied_over_fit": (c_impl / c_fit) if c_impl else None,
                          "g3_pass": g3})
    ok = all(v["pass"] for v in g1.values()) and g2_all and g3_all
    verdict = "CALIBRATED" if ok else "MISFIT"
    receipt = {"verdict": verdict, "expr": expr, "c_fit": c_fit,
               "band": list(band), "inv_band": list(inv_band),
               "g1_fit": g1, "heldout": held_rows,
               "why": ("all clauses pass" if ok else
                       "clause failure: " + json.dumps({"g1": {k: v["pass"] for k, v in g1.items()},
                                                        "g2_all": g2_all, "g3_all": g3_all}))}
    return receipt, (0 if ok else 1)

def selftest():
    checks = []
    # 1. exact rho^2 law: fit reproduces, heldout + invariance pass
    r, rc = run("1 + c*rho**2", [(0.2, 2.0)], [(0.4, 4.0)], (0.5, 2.0), (0.5, 2.0))
    checks.append(("law-consistent CALIBRATED", r["verdict"] == "CALIBRATED" and rc == 0
                   and abs(r["c_fit"] - 25.0) / 25.0 < 1e-6))
    # 2. rho^4 truth vs rho^2 model: heldout ratio blows past band -> MISFIT rc=1
    #    (rho=0.4 measured blowup 6.4 like D12al; model predicts 5.0 -> passes band,
    #     so push to rho=0.6 where divergence is unmissable: law says 10, model says 10/9? no:
    #     true form 1+40*rho**4 -> 0.6: 6.18; rho^2 fit c=25 -> 1+9=10... use steeper case)
    r2, rc2 = run("1 + c*rho**2", [(0.2, 2.0)], [(0.6, 20.0)], (0.5, 2.0), (0.5, 2.0))
    c_impl = r2["heldout"][0]["c_implied_over_fit"]
    checks.append(("form-break MISFIT via G3", r2["verdict"] == "MISFIT" and rc2 == 1
                   and c_impl is not None and c_impl > 2.0))
    # 3. G1 trip on a SECOND calibration point (the fit point is hit by construction)
    r3, rc3 = run("1 + c*rho**2", [(0.2, 2.0), (0.4, 12.0)], [], (0.5, 2.0), (0.5, 2.0))
    checks.append(("G1 fit miss MISFIT", r3["verdict"] == "MISFIT" and rc3 == 1
                   and r3["g1_fit"]["rho=0.4"]["pass"] is False))
    # 4. unbracketable target fails loud honestly (MISFIT, not crash)
    r4, rc4 = run("1 + c*rho**2", [(0.2, 1e12)], [], (0.5, 2.0), (0.5, 2.0))
    checks.append(("unbracketable honest MISFIT", r4["verdict"] == "MISFIT" and rc4 == 1
                   and r4["c_fit"] is None))
    # 5. fail-loud inputs
    bads = (lambda: run("1 + c*rho**2", [], [], (0.5, 2.0), (0.5, 2.0)),
            lambda: run("1 + c*explode", [(0.2, 2.0)], [], (0.5, 2.0), (0.5, 2.0)),
            lambda: run("1 + c*rho**2", [(0.2, 0.0)], [], (0.5, 2.0), (0.5, 2.0)))
    loud_ok = True
    for bad in bads:
        try:
            bad()
            loud_ok = False
            break
        except SystemExit as e:
            if e.code != 2:
                loud_ok = False
                break
    checks.append(("fail-loud rc=2 x3", loud_ok))
    ok = all(c for _, c in checks)
    print(json.dumps({"selftest": "OK" if ok else "FAIL",
                      "checks": [f"{n}: {'ok' if c else 'FAIL'}" for n, c in checks]}, indent=2))
    sys.exit(0 if ok else 1)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expr", help="model blow-up ratio expression in c and rho")
    ap.add_argument("--cal", nargs="*", default=[], help="rho:ratio calibration pairs (first is fit point)")
    ap.add_argument("--heldout", nargs="*", default=[], help="rho:ratio held-out pairs")
    ap.add_argument("--band", default="0.5,2.0", help="measured/model band (G1,G2)")
    ap.add_argument("--inv-band", default="0.5,2.0", help="c_implied/c_fit band (G3)")
    ap.add_argument("--out", help="write JSON receipt here")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if not a.expr:
        fail("--expr required")
    cal = parse_pairs(a.cal, "cal")
    held = parse_pairs(a.heldout, "heldout")
    try:
        band = tuple(float(x) for x in a.band.split(","))
        inv_band = tuple(float(x) for x in a.inv_band.split(","))
    except ValueError:
        fail("--band/--inv-band must be lo,hi floats")
    if len(band) != 2 or len(inv_band) != 2 or not (0 < band[0] < band[1]) or not (0 < inv_band[0] < inv_band[1]):
        fail("bands must be lo,hi with 0 < lo < hi")
    receipt, rc = run(a.expr, cal, held, band, inv_band)
    receipt["ts_utc"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    text = json.dumps(receipt, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    print(text)
    sys.exit(rc)

if __name__ == "__main__":
    main()
