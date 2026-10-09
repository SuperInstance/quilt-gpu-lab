"""verdict_gate — the TRUNC-B + DEGENERATE pin (fleet doctrine, 3+ independent witnesses).

Converts raw gate statistics into a verdict, refusing the two silent-corruption
classes the fleet keeps hitting:

1. DEGENERATE (murmuration std==0 law; our F1 G1, QO5 g0 AUC=0.500, W5a saturation):
   a gate statistic with zero variance (or a degenerate denominator) can never
   yield PASS. std==0 => DEGENERATE, never PASS.

2. TRUNC-B (canons judge_gate truncation blind spot; our 09:1x tmpfs tail
   incident: `pipeline | tail` reported SUCCESS with no file written):
   verdicts extracted from produced output must carry a completeness/termination
   attestation. Truncated-but-plausible => INCONCLUSIVE, never PASS.

3. DEGENERATE-widening (CONVERGENCE.md shape 3): a check whose reported status is
   not the check's own (exit-code-of-last-command class) — handled by requiring
   the caller to attest the status source explicitly; status="inherited" is VOID.

PARAM-1a: a gate with a value but NO bound (minimum is None AND maximum is None) is a
vacuous gate — it can never fail, so it converts absence of a real check into a PASS.
finalize() fail-closes such a gate: verdict FAIL with the vacuous-gate reason (after the
VOID/DEGENERATE precedence checks, so it never masks a stronger refusal).

Verdict lattice (never escalates to PASS silently):
    VOID        caller did not attest completeness/status source / missing stats
    DEGENERATE  any gated statistic has zero variance (or n < min_n)
    INCONCLUSIVE completeness False or truncated evidence
    FAIL        all gates evaluated, at least one gate fails
    PASS        all gates evaluated and pass, evidence complete, non-degenerate

Usage:
    from tools.verdict_gate import finalize, Gate
    v = finalize(
        gates=[Gate("auc", value=0.91, minimum=0.80)],
        stats={"auc": {"std": 0.03, "n": 32}},
        completeness=True,       # produced output verified complete/terminated
        status_source="own",     # "own" | "inherited" | "unknown"
    )
    assert v.verdict in {"PASS","FAIL","INCONCLUSIVE","DEGENERATE","VOID"}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Gate:
    """One pre-registered gate: `name` must be >= minimum (or <= maximum)."""
    name: str
    value: Optional[float]
    minimum: Optional[float] = None
    maximum: Optional[float] = None

    def evaluates(self) -> bool:
        return self.value is not None

    def passes(self) -> bool:
        if not self.evaluates():
            return False
        if self.minimum is not None and self.value < self.minimum:
            return False
        if self.maximum is not None and self.value > self.maximum:
            return False
        return True


@dataclass
class StatMeta:
    """Per-statistic metadata enabling the DEGENERATE pin."""
    std: Optional[float] = None      # None = variance unknown => treated as unknown, not degenerate
    n: int = 1
    saturated: Optional[bool] = None  # explicit saturation attestation (W5a class)


@dataclass
class Verdict:
    verdict: str
    reasons: List[str] = field(default_factory=list)
    gate_results: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": self.verdict, "reasons": self.reasons,
                "gate_results": self.gate_results}


MIN_N = 2  # variance of a single observation is undefined


def finalize(
    gates: List[Gate],
    stats: Dict[str, StatMeta],
    completeness: Optional[bool],
    status_source: str,
    min_n: int = MIN_N,
) -> Verdict:
    """The pin. Order of precedence: VOID > DEGENERATE > INCONCLUSIVE > FAIL > PASS."""
    reasons: List[str] = []

    # (3) status-source pin: never let an inherited status stand as the verdict.
    if status_source != "own":
        reasons.append(f"status_source={status_source!r}: reported status is not this check's own")
        return Verdict("VOID", reasons)

    # (2) TRUNC-B: completeness must be attested True, not merely absent.
    if completeness is not True:
        reasons.append(f"completeness={completeness!r}: truncated/attestation-missing => INCONCLUSIVE, never PASS")
        return Verdict("VOID" if completeness is None else "INCONCLUSIVE", reasons)

    # (1) DEGENERATE: zero-variance (or sub-min_n) statistics cannot PASS.
    for g in gates:
        m = stats.get(g.name)
        if m is not None and g.evaluates():
            if m.std is not None and m.std == 0.0:
                reasons.append(f"gate {g.name}: std==0 (degenerate statistic) => DEGENERATE, never PASS")
                return Verdict("DEGENERATE", reasons)
            if m.saturated:
                reasons.append(f"gate {g.name}: saturated attestation (W5a class) => DEGENERATE, never PASS")
                return Verdict("DEGENERATE", reasons)
            if m.n < min_n:
                reasons.append(f"gate {g.name}: n={m.n} < {min_n} (variance undefined) => DEGENERATE")
                return Verdict("DEGENERATE", reasons)

    unevaluated = [g.name for g in gates if not g.evaluates()]
    if unevaluated:
        reasons.append(f"gates missing values: {unevaluated} => INCONCLUSIVE")
        return Verdict("INCONCLUSIVE", reasons)

    # PARAM-1a: evaluated-but-boundless gates are vacuous => fail closed.
    boundless = [g.name for g in gates if g.evaluates() and g.minimum is None and g.maximum is None]
    if boundless:
        reasons.append(f"gates with no bound (vacuous gate, never fails): {boundless} => FAIL")
        return Verdict("FAIL", reasons, {g.name: False for g in gates})

    gate_results = {g.name: g.passes() for g in gates}
    if all(gate_results.values()):
        return Verdict("PASS", ["all gates pass, evidence complete, statistics non-degenerate"], gate_results)
    failed = [n for n, ok in gate_results.items() if not ok]
    return Verdict("FAIL", [f"gates failed: {failed}"], gate_results)
