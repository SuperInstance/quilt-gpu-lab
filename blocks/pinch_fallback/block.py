"""pinch_fallback — graded-confidence pinch to a deterministic known-answer path.

Harvested from the CM1 relay rounds (experiments/cm1_relay.py r1,
cm1_relay_r2/r3.py) and the RING-CX-2 threshold-degeneracy law
(experiments/ring_cx2.py); receipts of record: RESULTS.md CM1 r1/r2/r3
(2026-09-29) and RING-CX-2 (2026-10-01).

THE MECHANISM (CM1 r1/r3, verbatim wiring):
    a PRIMARY path proposes an answer; a GRADER returns graded noul scores
    (floats in [0,1], one per named question) for the draft; if
    min(score) < pinch threshold the draft is DOUBTED -> exactly one retry
    whose prompt carries the gate complaint ("Gate scores domain=%.2f
    urgency=%.2f (threshold %.2f). Re-derive carefully..."); if the retry
    still doubts, the item is PINCHED to a DETERMINISTIC known-answer path
    (the CM1 keyword router) and the pinch is booked honestly as a
    first-class flow state. A pinch is never silently absorbed.

Booked receipts this block encodes:
    CM1 r1 — broken 0.5b GEN: arm A ungated 0/12 (all PARSE_FAIL); gated
        relay 10/12 with 11/12 PINCHED_FALLBACK — "the pinch path
        (deterministic keyword router) carried accuracy — the pincher
        doctrine PROVEN under generative-cell failure". S12 wrong via the
        pre-registered negation blind spot ("no AIS contacts"
        substring-matches the router motion term).
    CM1 r2 — format-first: a draft that cannot even PARSE never reaches the
        semantic gates; with a broken cell 12/12 FORMAT_PINCHED and ALL
        correctness came from the fallback; the pinch sweep was degenerate
        (threshold never engaged) and was booked honestly as such.
    CM1 r3 — competent GEN: TIE_NOISE at pinch 0.3/0.5/0.7; the net never
        let a wrong answer through; at p0.7 gates doubted 12/12 CORRECT
        drafts ({11 RETRY, 1 PINCHED}) and accuracy STILL held 12/12.
    RING-CX-2 — the frost law for thresholds: a threshold so conservative
        that NOTHING engages (0 alerts) cannot adjudicate the safety net:
        std==0 / zero engagements => INCONCLUSIVE, never PASS. The fix is
        the house tau doctrine: pick the threshold as the TRAIN quantile at
        the desired doubt prevalence (pinch_threshold_for_rate).

Standalone: stdlib + numpy only (numpy used only by the tau helper), no
repo-internal imports, no network, no subprocess. CPU-only, deterministic:
seed 2718 default everywhere. Fail loud: every failure mode raises a
PinchError subclass, never a silent default.

House contracts: the self-test's final stdout line is exactly one JSON
object with exactly one top-level "verdict" field (PASS/KILL/INCONCLUSIVE);
exit 0 iff PASS.
"""
from __future__ import annotations

import json
import random
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

SEED = 2718

# Flow states — first-class, exactly the CM1 census vocabulary.
DRAFT_PASS = "DRAFT_PASS"          # min(noul) >= threshold on the first draft
RETRY_PASS = "RETRY_PASS"          # doubted once, retry cleared the bar
PINCHED_FALLBACK = "PINCHED_FALLBACK"  # retry still doubted -> known-answer path
FORMAT_PINCHED = "FORMAT_PINCHED"  # primary cannot even format (r2 format-first)
FLOWS = (DRAFT_PASS, RETRY_PASS, PINCHED_FALLBACK, FORMAT_PINCHED)


class PinchError(Exception):
    """Booked exception base — fail loud, never silent."""


class PrimaryFormatError(PinchError):
    """The PRIMARY declares its own draft unformattable (format-first, r2):
    the draft never reaches the semantic grader; pinch straight to fallback."""


class BadScoresError(PinchError):
    """The grader returned something that is not {name: float in [0,1]}."""


def validate_scores(scores: Any) -> Dict[str, float]:
    """Strict grader-output contract: non-empty dict, every value a finite
    float in [0,1]. Anything else fails loud (BadScoresError)."""
    if not isinstance(scores, dict) or not scores:
        raise BadScoresError(f"grader must return a non-empty dict, got {scores!r}")
    out: Dict[str, float] = {}
    for k, v in scores.items():
        if not isinstance(k, str) or not k:
            raise BadScoresError(f"grader question name must be non-empty str, got {k!r}")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise BadScoresError(f"grader score for {k!r} must be numeric, got {v!r}")
        fv = float(v)
        if not (0.0 <= fv <= 1.0):
            raise BadScoresError(f"noul score for {k!r} outside [0,1]: {fv}")
        out[k] = fv
    return out


class PinchFallback:
    """One pinch policy over injected primary / grader / fallback callables.

    Parameters
    ----------
    primary : callable(item, feedback=None) -> draft
        The generative path. May raise PrimaryFormatError to declare an
        unformattable draft (the r2 format-first route: straight to
        fallback, no semantic grading). `feedback` is the gate complaint
        string on the retry call.
    grader : callable(item, draft) -> {name: noul in [0,1]}
        The judgment layer. Returns GRADED scores, not verdicts.
    fallback : callable(item) -> answer
        The DETERMINISTIC known-answer path (e.g. keyword_router below).
        Must be side-effect-free and reproducible; it is the load-bearing
        safety net, so it must not call any model.
    threshold : float in [0,1]
        Pinch threshold tau: the item is doubted iff min(noul) < tau.
    retries : int (0 or 1)
        CM1 wiring: exactly one complaint-carrying retry before the pinch.
    """

    def __init__(self, *, primary: Callable, grader: Callable, fallback: Callable,
                 threshold: float = 0.5, retries: int = 1, seed: int = SEED):
        if not callable(primary) or not callable(grader) or not callable(fallback):
            raise PinchError("primary, grader and fallback must all be callable")
        if not (0.0 <= float(threshold) <= 1.0):
            raise PinchError(f"threshold must be in [0,1], got {threshold}")
        if int(retries) not in (0, 1):
            raise PinchError(f"retries must be 0 or 1 (CM1 wiring), got {retries}")
        self.primary = primary
        self.grader = grader
        self.fallback = fallback
        self.threshold = float(threshold)
        self.retries = int(retries)
        self.seed = int(seed)

    # -- internals ---------------------------------------------------------
    def _complaint(self, scores: Dict[str, float]) -> str:
        """The r3 retry prompt verbatim shape: scores + threshold named."""
        parts = " ".join(f"{k}={v:.2f}" for k, v in sorted(scores.items()))
        return (f"Gate scores {parts} (threshold {self.threshold:.2f}). "
                f"Re-derive carefully step by step, then answer again.")

    def _doubted(self, scores: Dict[str, float]) -> bool:
        return min(scores.values()) < self.threshold

    # -- the mechanism ------------------------------------------------------
    def run(self, item: Any) -> Dict[str, Any]:
        """Route ONE item through draft -> (doubt? retry ->) pinch/fallback.

        Returns the per-item receipt: flow state, final answer, every score
        dict the grader produced, primary/grader call counts, pinched flag.
        Never raises on doubt (that is the mechanism); raises PinchError
        only on contract violations (bad grader output, bad config).
        """
        t0 = time.time()
        receipt: Dict[str, Any] = {
            "item": item, "answer": None, "flow": None,
            "scores": [], "primary_calls": 0, "grader_calls": 0,
            "retries": 0, "pinched": False, "threshold": self.threshold,
        }
        try:
            draft = self.primary(item)
        except PrimaryFormatError as exc:
            # r2 format-first: an unformattable draft never reaches the
            # semantic gates; pinch straight to the deterministic path.
            receipt.update(primary_calls=1, answer=self.fallback(item),
                           flow=FORMAT_PINCHED, pinched=True,
                           format_error=str(exc))
            receipt["wall_s"] = round(time.time() - t0, 6)
            return receipt
        receipt["primary_calls"] = 1
        scores = validate_scores(self.grader(item, draft))
        receipt["grader_calls"] = 1
        receipt["scores"].append(scores)

        if not self._doubted(scores):
            receipt.update(answer=draft, flow=DRAFT_PASS)
        elif self.retries == 0:
            receipt.update(answer=self.fallback(item), flow=PINCHED_FALLBACK,
                           pinched=True)
        else:
            draft2 = self.primary(item, feedback=self._complaint(scores))
            receipt["primary_calls"] += 1
            scores2 = validate_scores(self.grader(item, draft2))
            receipt["grader_calls"] += 1
            receipt["scores"].append(scores2)
            receipt["retries"] = 1
            if self._doubted(scores2):
                receipt.update(answer=self.fallback(item), flow=PINCHED_FALLBACK,
                               pinched=True)
            else:
                receipt.update(answer=draft2, flow=RETRY_PASS)
        receipt["wall_s"] = round(time.time() - t0, 6)
        return receipt

    def run_corpus(self, items: Sequence[Any],
                   truth: Optional[Dict[Any, Any]] = None) -> Dict[str, Any]:
        """Run every item; aggregate the flow census exactly like the CM1
        rounds (paths dict + counts). If `truth` maps item -> correct answer,
        accuracy is computed per flow and overall. Zero-engagement corpora
        are NOT proof the net works — the sweep-level frost law (below) is
        the caller's responsibility to apply."""
        receipts = [self.run(it) for it in items]
        counts = {f: 0 for f in FLOWS}
        for r in receipts:
            counts[r["flow"]] += 1
        out: Dict[str, Any] = {
            "threshold": self.threshold, "retries": self.retries, "seed": self.seed,
            "n": len(receipts), "counts": counts, "receipts": receipts,
            "engagements": counts[RETRY_PASS] + counts[PINCHED_FALLBACK]
                           + counts[FORMAT_PINCHED],
        }
        if truth is not None:
            def ok(r: Dict[str, Any]) -> bool:
                return r["answer"] == truth.get(r["item"])
            out["accuracy"] = sum(ok(r) for r in receipts) / len(receipts)
            out["accuracy_by_flow"] = {
                f: (sum(ok(r) for r in receipts if r["flow"] == f) / counts[f])
                for f in FLOWS if counts[f] > 0}
        return out


def sweep(pinch_factory: Callable[[float], PinchFallback], items: Sequence[Any],
          thresholds: Sequence[float],
          truth: Optional[Dict[Any, Any]] = None) -> Dict[str, Any]:
    """The r3 pinch sweep with the RING-CX-2 frost law applied per level:
    a threshold with ZERO engagements (nothing doubted, nothing pinched)
    exercises no safety net, so its verdict is INCONCLUSIVE — never PASS.
    `pinch_factory(threshold)` builds a fresh PinchFallback per level (the
    CM1 rounds froze everything but the pinch level)."""
    levels: Dict[str, Any] = {}
    for tau in thresholds:
        res = pinch_factory(float(tau)).run_corpus(items, truth=truth)
        engaged = res["engagements"] > 0
        if not engaged:
            res["verdict"] = "INCONCLUSIVE"
            res["verdict_reason"] = ("zero engagements at this threshold — the "
                                     "safety net is unexercised (RING-CX-2 "
                                     "frost law: std==0/0-alert degeneracy)")
        else:
            res["verdict"] = "MEASURED"
        levels[f"p{tau:.2f}"] = res
    return {"thresholds": list(thresholds), "levels": levels,
            "frost_law": "zero engagements => INCONCLUSIVE, never PASS"}


def pinch_threshold_for_rate(train_min_scores: Sequence[float], rate: float) -> float:
    """The house tau doctrine (RING-CX-2 / COMP1 prevalence matching): choose
    the pinch threshold as the `rate`-quantile of TRAIN min-noul scores, so
    the expected pinch rate on train material equals `rate`. Fixes the
    degenerate-threshold calibration of dead graders (a threshold nothing
    ever crosses books no evidence about the net)."""
    if not 0.0 <= rate <= 1.0:
        raise PinchError(f"rate must be in [0,1], got {rate}")
    arr = np.asarray(list(train_min_scores), dtype=float)
    if arr.size == 0:
        raise PinchError("train_min_scores is empty")
    return float(np.quantile(arr, rate))


# ---------------------------------------------------------------------------
# The canonical deterministic known-answer path: the CM1 keyword router,
# verbatim (experiments/cm1_relay.py) — rule, term lists, stimuli, router.
# Its booked blind spot (S12 negation: "no AIS contacts" substring-matches
# the motion term) is part of the receipt and is asserted by the self-test.
# ---------------------------------------------------------------------------
RULE = """Rule: domain = engine if the report mentions engine terms (temp rising/falling, oil, fuel, rpm); else navigation if it mentions motion terms (blob moving, course drift, AIS contact); else deck.
urgency = high if any hazard term (rising, falling, dropping, leak, fire) or two+ domains are implicated; else mid if any motion term; else low."""

STIMULI = [
    ("S1", "Camera frame: three blobs, one moving left at 0.4 units per second. Engine readings steady. Deck clear.", "BOOK:navigation:mid"),
    ("S2", "Engine temp rising 2C per minute. Oil pressure dropping. No camera motion detected.", "BOOK:engine:high"),
    ("S3", "All sensors nominal. Bilge dry. Radio quiet. No motion on any camera.", "BOOK:deck:low"),
    ("S4", "AIS contact closing from starboard, course drift detected. Engine nominal.", "BOOK:navigation:mid"),
    ("S5", "Fuel flow steady at cruise rate. No motion. Bilge dry.", "BOOK:engine:low"),
    ("S6", "Smoke alarm triggered in the engine room, possible fire. Temp rising.", "BOOK:engine:high"),
    ("S7", "Bilge water rising. Engine nominal, no motion on cameras.", "BOOK:deck:high"),
    ("S8", "Course drift 5 degrees starboard over last minute. AIS clear.", "BOOK:navigation:mid"),
    ("S9", "Galley water leak reported. Engine nominal, no motion.", "BOOK:deck:high"),
    ("S10", "RPM steady at 1800. Oil pressure normal. No contacts.", "BOOK:engine:low"),
    ("S11", "Blob moving fast toward vessel bow on camera two. Engine nominal.", "BOOK:navigation:mid"),
    ("S12", "Radio check complete, all quiet. Bilge dry. No AIS contacts, no motion.", "BOOK:deck:low"),
]

ENGINE_TERMS = ["temp rising", "temp falling", "oil", "fuel", "rpm"]
MOTION_TERMS = ["moving", "course drift", "ais contact"]
HAZARD_TERMS = ["rising", "falling", "dropping", "leak", "fire"]


def keyword_router(report: str) -> str:
    """The deterministic known-answer path (CM1 r1, verbatim). Substring
    term matching over the rule's vocabulary; no model in the loop."""
    low = report.lower()
    eng = any(t in low for t in ENGINE_TERMS)
    mot = any(t in low for t in MOTION_TERMS)
    haz = any(t in low for t in HAZARD_TERMS)
    domain = "engine" if eng else ("navigation" if mot else "deck")
    urgency = "high" if (haz or (eng and mot)) else ("mid" if mot else "low")
    return "BOOK:%s:%s" % (domain, urgency)


TRUTH = {sid: truth for sid, _report, truth in STIMULI}
REPORTS = {sid: report for sid, report, _truth in STIMULI}
S12_BLIND_SPOT = ("S12", "BOOK:navigation:mid",
                  "'no AIS contacts' substring-matches the router motion term "
                  "'ais contact' (pre-registered negation blind spot, CM1 r1)")


# ---------------------------------------------------------------------------
# Self-test: scripted primaries/graders re-run the booked CM1 textures.
# ---------------------------------------------------------------------------
def self_test() -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    items = [sid for sid, _r, _t in STIMULI]

    # (0) the fallback path itself: 11/12 with the S12 blind spot, verbatim.
    fb_correct = {sid: keyword_router(REPORTS[sid]) == TRUTH[sid] for sid in items}
    checks["fallback_11_of_12_with_S12_blind_spot"] = (
        sum(fb_correct.values()) == 11 and fb_correct["S12"] is False)
    checks["fallback_deterministic"] = (
        keyword_router(REPORTS["S12"]) == keyword_router(REPORTS["S12"])
        == S12_BLIND_SPOT[1])

    # (1) CM1 r1/r2 texture — BROKEN primary: garbage drafts, low graded
    #     scores -> everything pinches; the deterministic path carries it.
    rng = random.Random(SEED)

    def broken_primary(item, feedback=None):
        return "asduoi zxcv %d" % rng.randrange(10 ** 6)  # never matches truth

    def broken_grader(item, draft):
        # gate scores 0.04-0.45: the r1 broken-cell regime (below every
        # pinch level in the sweep, including after the retry).
        return {"domain_ok": rng.uniform(0.04, 0.45),
                "urgency_ok": rng.uniform(0.04, 0.45)}

    broken_sweep = sweep(
        lambda tau: PinchFallback(primary=broken_primary, grader=broken_grader,
                                  fallback=lambda it: keyword_router(REPORTS[it]),
                                  threshold=tau),
        items, (0.3, 0.5, 0.7), truth=TRUTH)
    lv = broken_sweep["levels"]
    checks["r1_broken_all_levels_measured"] = all(
        v["verdict"] == "MEASURED" for v in lv.values())
    checks["r1_broken_all_pinched"] = all(
        v["counts"][PINCHED_FALLBACK] == 12 for v in lv.values())
    checks["r1_broken_fallback_carries_accuracy"] = all(
        v["accuracy"] == 11 / 12 for v in lv.values())
    checks["r1_broken_armA_would_be_zero"] = (
        sum(broken_primary(s) == TRUTH[s] for s in items) == 0)

    # (2) CM1 r2 texture — FORMAT_PINCHED: primary declares unformattable.
    def fmt_broken_primary(item, feedback=None):
        raise PrimaryFormatError("no BOOK:<domain>:<urgency> line in draft")

    def never_grader(item, draft):  # pragma: no cover - must never be called
        raise PinchError("grader must not see an unformattable draft")

    r2 = PinchFallback(primary=fmt_broken_primary, grader=never_grader,
                       fallback=lambda it: keyword_router(REPORTS[it]),
                       threshold=0.5).run_corpus(items, truth=TRUTH)
    checks["r2_format_pinched_12_of_12"] = r2["counts"][FORMAT_PINCHED] == 12
    checks["r2_all_correctness_from_fallback"] = (
        r2["accuracy"] == 11 / 12
        and all(r["grader_calls"] == 0 for r in r2["receipts"]))

    # (3) CM1 r3 texture — COMPETENT primary, doubting grader at p0.7:
    #     12/12 doubted, 11 RETRY_PASS + 1 PINCHED_FALLBACK, accuracy holds.
    rng3 = random.Random(SEED)
    doubter_state: Dict[str, int] = {}

    def competent_primary(item, feedback=None):
        return TRUTH[item] if feedback is None else TRUTH[item]

    def doubting_grader(item, draft):
        doubter_state[item] = doubter_state.get(item, 0) + 1
        first_call = doubter_state[item] == 1
        if first_call:
            # r3 p0.7: gates doubted 12/12 CORRECT drafts (scores < 0.7)
            return {"domain_ok": rng3.uniform(0.55, 0.69),
                    "urgency_ok": rng3.uniform(0.55, 0.69)}
        # retry: 11 items recover; S5 stays doubted -> the 1 PINCHED item
        if item == "S5":
            return {"domain_ok": rng3.uniform(0.55, 0.69),
                    "urgency_ok": rng3.uniform(0.55, 0.69)}
        return {"domain_ok": rng3.uniform(0.75, 0.95),
                "urgency_ok": rng3.uniform(0.75, 0.95)}

    r3 = PinchFallback(primary=competent_primary, grader=doubting_grader,
                       fallback=lambda it: keyword_router(REPORTS[it]),
                       threshold=0.7).run_corpus(items, truth=TRUTH)
    checks["r3_p07_texture_11_RETRY_1_PINCHED"] = (
        r3["counts"][RETRY_PASS] == 11 and r3["counts"][PINCHED_FALLBACK] == 1
        and r3["counts"][DRAFT_PASS] == 0)
    checks["r3_p07_accuracy_holds_12_of_12"] = r3["accuracy"] == 1.0
    checks["r3_pinched_item_fallback_correct"] = (
        [r for r in r3["receipts"] if r["flow"] == PINCHED_FALLBACK][0]["answer"]
        == TRUTH["S5"])

    # (3b) competent primary at p0.5: nothing doubted -> all DRAFT_PASS.
    rng3b = random.Random(SEED)

    def calm_grader(item, draft):
        return {"domain_ok": rng3b.uniform(0.75, 0.95),
                "urgency_ok": rng3b.uniform(0.75, 0.95)}

    r3b = PinchFallback(primary=competent_primary, grader=calm_grader,
                        fallback=lambda it: keyword_router(REPORTS[it]),
                        threshold=0.5).run_corpus(items, truth=TRUTH)
    checks["r3_p05_all_draft_pass"] = (
        r3b["counts"][DRAFT_PASS] == 12 and r3b["accuracy"] == 1.0)

    # (4) RING-CX-2 frost law — a threshold nothing engages is INCONCLUSIVE;
    #     a live threshold (0.8, above calm scores' floor) is MEASURED.
    frost_sweep = sweep(
        lambda tau: PinchFallback(primary=competent_primary, grader=calm_grader,
                                  fallback=lambda it: keyword_router(REPORTS[it]),
                                  threshold=tau),
        items, (0.2, 0.8), truth=TRUTH)
    checks["frost_law_dead_threshold_inconclusive"] = (
        frost_sweep["levels"]["p0.20"]["verdict"] == "INCONCLUSIVE"
        and frost_sweep["levels"]["p0.20"]["engagements"] == 0)
    checks["frost_law_live_threshold_measured"] = (
        frost_sweep["levels"]["p0.80"]["verdict"] == "MEASURED"
        and frost_sweep["levels"]["p0.80"]["engagements"] > 0)

    # (5) tau doctrine — prevalence-matched threshold from TRAIN min-scores.
    train_mins = [0.11, 0.23, 0.37, 0.41, 0.55, 0.62, 0.78, 0.81, 0.93, 0.97]
    tau = pinch_threshold_for_rate(train_mins, 0.3)
    induced = sum(m < tau for m in train_mins) / len(train_mins)
    checks["tau_doctrine_train_rate_matches"] = abs(induced - 0.3) <= 1.0 / len(train_mins)

    # (6) fail-loud contracts.
    loud = False
    try:
        PinchFallback(primary=competent_primary, grader=calm_grader,
                      fallback=lambda it: keyword_router(REPORTS[it]),
                      threshold=1.5)
    except PinchError:
        loud = True
    checks["bad_threshold_fails_loud"] = loud
    loud = False
    try:
        validate_scores({"q": 1.5})
    except BadScoresError:
        loud = True
    checks["bad_scores_fail_loud"] = loud

    # (7) determinism: the whole seeded sweep reproduces bit-for-bit.
    def run_broken_sweep():
        rng_d = random.Random(SEED)

        def bp(item, feedback=None):
            return "asduoi zxcv %d" % rng_d.randrange(10 ** 6)

        def bg(item, draft):
            return {"domain_ok": rng_d.uniform(0.04, 0.45),
                    "urgency_ok": rng_d.uniform(0.04, 0.45)}

        return sweep(lambda tau: PinchFallback(primary=bp, grader=bg,
                                               fallback=lambda it: keyword_router(REPORTS[it]),
                                               threshold=tau),
                     items, (0.3, 0.5, 0.7), truth=TRUTH)

    a_, b_ = run_broken_sweep(), run_broken_sweep()

    def behavior(sw):  # wall_s is timing, not behavior — strip before compare
        return [[(r["item"], r["flow"], r["answer"], r["scores"])
                 for r in lv["receipts"]] for lv in sw["levels"].values()]

    checks["seeded_determinism"] = behavior(a_) == behavior(b_)

    # frost law on the SELF-TEST headline: the broken-cell sweep must have
    # engaged at every level (else its rescue claim is unexercised).
    headline_engaged = all(v["engagements"] > 0 for v in lv.values())
    verdict = "PASS" if all(checks.values()) else "KILL"
    reason = ("all booked textures reproduced (r1 rescue, r2 format pinch, "
              "r3 net-never-hurts, frost law, tau doctrine)")
    if not headline_engaged:
        verdict = "INCONCLUSIVE"
        reason = "headline sweep had zero engagements — rescue claim unexercised"

    return {
        "verdict": verdict,
        "reason": reason,
        "checks": checks,
        "seed": SEED,
        "fallback_baseline": {"correct": sum(fb_correct.values()), "n": 12,
                              "blind_spot": {"sid": S12_BLIND_SPOT[0],
                                             "router_says": S12_BLIND_SPOT[1],
                                             "cause": S12_BLIND_SPOT[2]}},
        "r1_broken_sweep": {k: {"counts": v["counts"], "accuracy": v["accuracy"],
                                "verdict": v["verdict"]}
                            for k, v in lv.items()},
        "r3_p07": {"counts": r3["counts"], "accuracy": r3["accuracy"]},
        "provenance": "RESULTS.md CM1 r1/r2/r3 (2026-09-29) + RING-CX-2 (2026-10-01)",
    }


def main() -> int:
    try:
        summary = self_test()
    except PinchError as exc:
        summary = {"verdict": "KILL",
                   "reason": f"booked exception {type(exc).__name__}: {exc}"}
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
