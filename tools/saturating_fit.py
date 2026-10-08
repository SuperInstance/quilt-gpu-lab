#!/usr/bin/env python3
"""saturating-fit — saturating one-variable fit + held-out prediction gate.

Pattern lifted PROVEN from D12aa (booked 2026-10-07): D12z linearly
extrapolated k_eff(p) to p=0.7 and got 1.614 — the true parameter saturates
(~0.65-0.86). This tool mechanizes the alternative: fit k(x) = k0 + A*exp(-x/tau)
to anchor points via a tau grid-scan with closed-form 2-parameter least squares
for (k0, A) per tau (pure Python normal equations, no numpy), predict the
held-out x with NO refit, and gate:

  G1  anchor residual (absolute RMS, the D12aa convention) <= --resid-bar (default 0.10)
  G2  sanity: tau within [tau-lo, tau-hi] bounds (a tau pinned at the grid
      edge means the exponential is degenerate on these anchors — booked
      honestly, never silent), and k(x) must be finite
  G3  optional: if --actual is given, |k_pred/actual - 1| <= --band
      (default 0.5, the D12v band)

Exit 0 = PASS, 1 = FAIL (a gate tripped, booked), 2 = fail-loud input.
One JSON receipt either way. Stdlib-only, deterministic.

Worked example (docstring = contract):
    anchors = [(0.3, 0.657), (0.4, 0.8963), (0.45, 0.7765)]
    r = fit_saturating(anchors)          # -> k0, A, tau, resid
    k = predict(r, 0.7)                  # held-out, no refit

CLI:
    python tools/saturating_fit.py --anchors '[[0.3,0.657],[0.4,0.8963],[0.45,0.7765]]' \\
        --predict 0.7 [--actual 0.836 --resid-bar 0.1 --out r.json] | --selftest
"""
import argparse
import json
import math
import sys
import time

TAU_GRID = [0.01 * (1.0 ** (i / 20000.0)) * (10.0 ** (i / 20000.0)) for i in
            range(20001)]  # geomspace 0.01..10.0 without numpy


def _lsq2(rows, ys):
    """Closed-form least squares for 2 params: minimize |M p - y|^2.
    rows = list of [m1, m2]; normal equations 2x2, pure Python."""
    s11 = sum(r[0] * r[0] for r in rows)
    s12 = sum(r[0] * r[1] for r in rows)
    s22 = sum(r[1] * r[1] for r in rows)
    t1 = sum(r[0] * y for r, y in zip(rows, ys))
    t2 = sum(r[1] * y for r, y in zip(rows, ys))
    det = s11 * s22 - s12 * s12
    if abs(det) < 1e-300:
        raise ValueError("degenerate design matrix (collinear basis)")
    return ((t1 * s22 - t2 * s12) / det, (s11 * t2 - s12 * t1) / det)


def fit_saturating(anchors, tau_lo=0.01, tau_hi=10.0, n_tau=20001):
    """Fit k(x) = k0 + A*exp(-x/tau) to anchors [(x, k)] via tau grid scan.
    Returns dict with k0, A, tau, anchor_resid (relative RMS)."""
    if len(anchors) < 3:
        raise ValueError("need >= 3 anchors for 3-parameter saturating fit")
    xs = [float(a[0]) for a in anchors]
    ys = [float(a[1]) for a in anchors]
    if any(not math.isfinite(v) for v in xs + ys):
        raise ValueError("non-finite anchor value")
    if len(set(xs)) != len(xs):
        raise ValueError("duplicate anchor x values")
    best = None
    for i in range(n_tau):
        tau = tau_lo * (tau_hi / tau_lo) ** (i / (n_tau - 1))
        rows = [[1.0, math.exp(-x / tau)] for x in xs]
        k0, A = _lsq2(rows, ys)
        resid_abs = math.sqrt(sum((k0 + A * math.exp(-x / tau) - y) ** 2
                                   for x, y in zip(xs, ys)))
        resid_rel = resid_abs / math.sqrt(sum(y * y for y in ys))
        if best is None or resid_abs < best[0]:
            best = (resid_abs, resid_rel, k0, A, tau)
    return {"k0": best[2], "A": best[3], "tau": best[4],
            "anchor_resid": best[0], "anchor_resid_rel": best[1]}


def predict(fit, x):
    """Held-out prediction k(x) from a fit — no refit, by construction."""
    return fit["k0"] + fit["A"] * math.exp(-float(x) / fit["tau"])


def linear_extrap(anchors, x):
    """Control: ordinary least-squares LINEAR fit through the anchors,
    evaluated at x — the D12z failure mode, reported for contrast."""
    xs = [float(a[0]) for a in anchors]
    ys = [float(a[1]) for a in anchors]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((v - mx) ** 2 for v in xs)
    sxy = sum((v - mx) * (w - my) for v, w in zip(xs, ys))
    if sxx == 0:
        raise ValueError("zero x variance — linear control undefined")
    b = sxy / sxx
    return my + b * (x - mx)


def run_gate(anchors, x_test, actual=None, resid_bar=0.10,
             tau_lo=0.01, tau_hi=10.0, band=0.5, tau_edge_tol=1e-9):
    fit = fit_saturating(anchors, tau_lo=tau_lo, tau_hi=tau_hi)
    k_pred = predict(fit, x_test)
    lin = linear_extrap(anchors, x_test)
    checks = {}
    checks["g1_resid"] = fit["anchor_resid"] <= resid_bar
    tau_pinned_lo = abs(fit["tau"] - tau_lo) <= tau_edge_tol
    tau_pinned_hi = abs(fit["tau"] - tau_hi) <= tau_edge_tol
    checks["g2_tau_interior"] = not (tau_pinned_lo or tau_pinned_hi)
    checks["g2_finite"] = math.isfinite(k_pred)
    if actual is not None:
        checks["g3_band"] = abs(k_pred / float(actual) - 1.0) <= band
    verdict = "PASS" if all(checks.values()) else "FAIL"
    return {"tool": "saturating-fit", "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "anchors": [list(map(float, a)) for a in anchors],
            "x_test": float(x_test), "actual": actual,
            "fit": fit, "k_pred": k_pred, "linear_control": lin,
            "checks": checks, "verdict": verdict}


def selftest():
    checks = []
    # Pin 1: D12aa reproduction — fit numbers from the committed receipt
    # results/d12aa_saturating_kfit_p07.json (resid there is ABSOLUTE RMS).
    anchors = [(0.3, 0.657), (0.4, 0.8963), (0.45, 0.7765)]
    fit = fit_saturating(anchors)
    checks.append(("d12aa_k0", abs(fit["k0"] - 0.8364027491) < 1e-6,
                   f'k0={fit["k0"]:.6f} want 0.836403'))
    checks.append(("d12aa_resid", abs(fit["anchor_resid"] - 0.08471711285) < 1e-6,
                   f'resid={fit["anchor_resid"]:.6f} want 0.084717'))
    k07 = predict(fit, 0.7)
    checks.append(("d12aa_k07", abs(k07 - 0.8364027491) < 1e-6,
                   f"k(0.7)={k07:.6f} (tau pinned low => saturates at k0)"))
    # Pin 2: tau at the grid-LOW edge — the D12aa reality (tau=0.01). The
    # exponential term is degenerate on these anchors; run_gate must book
    # that honestly (g2_tau_interior False) rather than a silent PASS.
    r1 = run_gate(anchors, 0.7, actual=0.836, band=0.5)
    checks.append(("d12aa_tau_edge_honest",
                   r1["verdict"] == "FAIL" and r1["checks"]["g2_tau_interior"] is False
                   and r1["checks"]["g1_resid"] is True and r1["checks"]["g3_band"] is True,
                   f"verdict={r1['verdict']} checks={r1['checks']}"))
    # Pin 3: the D12z contrast — the linear control climbs ABOVE the
    # saturating prediction, which is exactly the failure mode this tool
    # exists to catch.
    checks.append(("linear_contrast",
                   linear_extrap(anchors, 0.7) > k07,
                   f'lin={linear_extrap(anchors, 0.7):.3f} > sat={k07:.3f}'))
    # Pin 4: interior-tau saturant passes all gates; rising prediction must
    # exceed the anchor ceiling.
    anchors2 = [(0.1, 1.1), (0.3, 1.9), (0.5, 2.4)]
    r2 = run_gate(anchors2, 0.8)
    checks.append(("growing_pass",
                   r2["verdict"] == "PASS" and predict(r2["fit"], 0.8) > 2.4,
                   f"verdict={r2['verdict']}, k(0.8)={predict(r2['fit'], 0.8):.3f}"))
    # Pin 5: --actual band gate trips on a wrong held-out truth (interior tau,
    # so the FAIL is attributable to g3 alone).
    r3 = run_gate(anchors2, 0.8, actual=9.0, band=0.5)
    checks.append(("band_fail",
                   r3["verdict"] == "FAIL" and r3["checks"]["g3_band"] is False
                   and r3["checks"]["g1_resid"] is True,
                   f"verdict={r3['verdict']} checks={r3['checks']}"))
    # Pin 4: fail-loud inputs.
    for name, fn in [
        ("two_anchors", lambda: fit_saturating([(0.1, 1.0), (0.2, 2.0)])),
        ("dup_x", lambda: fit_saturating([(0.1, 1.0), (0.1, 2.0), (0.3, 3.0)])),
        ("nan", lambda: fit_saturating([(0.1, float("nan")), (0.2, 2.0), (0.3, 3.0)])),
    ]:
        try:
            fn()
            checks.append((name, False, "no exception raised"))
        except ValueError:
            checks.append((name, True, "refused rc=2-class input"))
    ok = [c for c in checks if c[1]]
    print(json.dumps({"selftest": f"{len(ok)}/{len(checks)}",
                      "failures": [c[0] for c in checks if not c[1]]}, indent=2))
    return 0 if len(ok) == len(checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 epilog="See module docstring for the contract.")
    ap.add_argument("--anchors", help="JSON list of [x, k] anchor pairs")
    ap.add_argument("--anchors-file", help="or a JSON file of the same")
    ap.add_argument("--predict", type=float, help="held-out x to predict (no refit)")
    ap.add_argument("--actual", type=float, help="optional held-out truth for the G3 band gate")
    ap.add_argument("--resid-bar", type=float, default=0.10)
    ap.add_argument("--band", type=float, default=0.5)
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        if a.anchors_file:
            with open(a.anchors_file) as f:
                anchors = [tuple(p) for p in json.load(f)]
        elif a.anchors:
            anchors = [tuple(p) for p in json.loads(a.anchors)]
        else:
            ap.error("--anchors or --anchors-file required (or --selftest)")
        if a.predict is None:
            ap.error("--predict x required")
        r = run_gate(anchors, a.predict, actual=a.actual,
                     resid_bar=a.resid_bar, band=a.band)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(json.dumps({"tool": "saturating-fit", "error": str(e),
                          "verdict": "FAIL-INPUT"}), file=sys.stderr)
        return 2
    line = json.dumps({k: r[k] for k in ("verdict", "k_pred", "linear_control",
                                         "fit", "checks")}, default=str)
    print(line)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(r, f, indent=2)
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
