"""eproc.py — Python port of SuperInstance/quilt-ewitness eproc.mjs (anytime-valid
e-process witnesses). Ported VERBATIM in semantics for the QO6 kill-evidence gate.

Vendored lineage (pinned in delta-shape PR #1 src/esign.mjs):
  repo   : SuperInstance/quilt-ewitness
  commit : 61b9e0403f2254691570cdf877bbbf81624df1f1
  sha256 : aad90ac5aedb4d8e19b189808b47b22fc7258044af2c25c8f7fc90efec19e63a

Honesty contract inherited: sigma is REQUIRED and pre-registered; the tool refuses
to run without it rather than silently peeking. Ville: P(sup_t E_t >= 1/delta) <= delta
under H0. Retraction: fired-then-decayed evidence is retracted — a process that cannot
retract is a p-value in disguise.

Lineage note: this is a semantic port of the vendored .mjs bytes (converted to numpy),
not byte consumption; parity is enforced by the V1 port-parity pins in
experiments/qo6_kill_evidence.py.
"""
import math

import numpy as np

VENDOR_REPO = "SuperInstance/quilt-ewitness"
VENDOR_COMMIT = "61b9e0403f2254691570cdf877bbbf81624df1f1"
VENDOR_SHA256 = "aad90ac5aedb4d8e19b189808b47b22fc7258044af2c25c8f7fc90efec19e63a"

MU_GRID = [0.01, 0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6]  # in units of sigma


def increments(y):
    y = np.asarray(y, dtype=float)
    return y[1:] - y[:-1]


def eprocess(d, sigma, sign=-1, mu_grid=MU_GRID):
    """Running mixture e-process over increments; sign=-1 for DECREASES, +1 for INCREASES."""
    if not (sigma > 0 and math.isfinite(sigma)):
        raise ValueError("sigma must be a positive finite number (pre-registered)")
    d = np.asarray(d, dtype=float)
    mu = sign * np.asarray(mu_grid, dtype=float) * sigma  # (K,)
    # log f_mu(d) - log f_0(d) = -((d-mu)^2 - d^2) / (2 sigma^2), broadcast (T,K)
    lr = -(((d[:, None] - mu[None, :]) ** 2 - d[:, None] ** 2) / (2.0 * sigma * sigma))
    log_acc = math.log(1.0 / len(mu_grid)) + np.cumsum(lr, axis=0)  # (T,K)
    m = log_acc.max(axis=1)
    log_e = m + np.log(np.exp(log_acc - m[:, None]).sum(axis=1))
    return {"logE": log_e, "E": np.exp(log_e)}


def witness(series, claim="DECREASES", sigma=None, delta=0.05):
    """Witness a claim on a series. sigma REQUIRED (pre-registered noise scale)."""
    if claim not in ("DECREASES", "INCREASES"):
        raise ValueError(f"unknown claim {claim}")
    series = list(series)
    if len(series) < 10:
        raise ValueError("series too short (<10) — refuse to witness")
    if not all(math.isfinite(v) for v in series):
        raise ValueError("non-finite value in series — refuse")
    if sigma is None:
        raise ValueError("sigma is REQUIRED and pre-registered — no silent default")
    if not (0 < delta < 1 and math.isfinite(delta)):
        raise ValueError(f"delta must be a finite number in (0,1) (got {delta!r}) — no silent mis-set (PARAM-1 hardening)")
    sign = -1 if claim == "DECREASES" else 1
    E = eprocess(increments(series), sigma, sign)["E"]
    bar = 1.0 / delta
    stop_t = -1
    for t, e in enumerate(E):
        if e >= bar:
            stop_t = t + 1
            break
    return {
        "claim": claim, "sigma": sigma, "delta": delta, "bar": bar,
        "E_final": float(E[-1]), "E_max": float(E.max()), "stop_t": stop_t,
        "retracted": stop_t > 0 and E[-1] < bar,
        "verdict": "WITNESSED" if stop_t > 0 else "NOT_WITNESSED",
    }


def kill_gate(series, sigma, delta=0.05):
    """QO6 consumer: retractable kill-evidence for one stream's P(cross) trajectory.
    Returns KILL_CANDIDATE / KEEP / INSUFFICIENT plus the witness record."""
    try:
        w = witness(series, claim="DECREASES", sigma=sigma, delta=delta)
    except ValueError as e:
        raise
    if w["verdict"] == "WITNESSED" and not w["retracted"]:
        decision = "KILL_CANDIDATE"
    elif w["retracted"]:
        decision = "KEEP"  # late evidence arrived — kill retracted
    else:
        decision = "INSUFFICIENT"
    return {"decision": decision, **w}
