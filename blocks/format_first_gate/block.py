#!/usr/bin/env python3
"""format_first_gate — judge-answer gating layer (FORMAT-FIRST / RETRY-ONCE /
PINCH-TO-FALLBACK), harvested from the CM1 relay rounds.

Provenance:
- experiments/cm1_relay_r4.py (CM1 r4, 2026-09-29): rule-blind gates fabricated
  doubt ({3 DRAFT_PASS, 6 RETRY_PASS, 3 PINCHED_FALLBACK}, judge wall 6.9s/18
  calls) while the rule-rich ONE-CALL batched gate went {12 DRAFT_PASS} in 0.28s
  with 25x less wall and 4.5x fewer tokens. This block is the parse/flow layer of
  that batched gate, minus any network.
- experiments/cm1_relay_r5.py (CM1 r5, 2026-09-30): same recipe under a judge
  swap + roster; confirmed the receipt shape transfers (flow census + token
  ledger + batch walls).
- tools/typesafe_batch.py: the retry-once / fail-loud / flat-latency batched
  judge call this gate sits in front of.

Core ideas, standalone and stdlib-only:
1. FORMAT-FIRST — the judge returns ONE batched response carrying named answers
   for the frozen question list. Parse strictly BEFORE any trust is placed in
   content: every named question present exactly once, typed/coercible values,
   no extras, no prose tolerance.
2. RETRY-ONCE — a format failure (or a transport error) triggers exactly one
   structured re-ask, pinched to the complaint. Never an infinite loop.
3. PINCH-TO-FALLBACK — on persistent format failure, fall back to a
   deterministic local fallback answer per unanswered question and BOOK the
   pinch honestly in the flow receipt. PINCHED_FALLBACK is a first-class state,
   not a silent degradation. (CM1 doctrine: the deterministic router is the
   load-bearing safety net — CURL-1 r1, CM1 r1, CM1 r5.)
4. Flow-state receipt — per-question flow in {DRAFT_PASS, RETRY_PASS,
   PINCHED_FALLBACK} + aggregate counts + wall_s + token counts (when the judge
   reports usage) + retries + pinched + judge_calls.
5. Fail loud — judge transport failure after retry-once, or unparseable-after-
   retry with no fallback configured, raises GateError carrying the receipt.
   Never a silent pass.

House contracts baked in: DEFAULT_SEED = 2718; single JSON verdict on the final
stdout line of the self-test; list-form subprocess only / never shell=True for
any real transport (this block ships NO transport and touches NO secrets — the
judge is injected; tokens are never printed or copied); std==0 across repeats
=> INCONCLUSIVE downstream (see tools/verdict_gate.py), so this block is
deterministic given its judge.

Self-test: python3 blocks/format_first_gate/block.py  ->  final stdout line is
exactly one JSON object {"verdict": "PASS"}; exit 0 iff PASS. CPU-only, <10s.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple, Union

DRAFT_PASS = "DRAFT_PASS"
RETRY_PASS = "RETRY_PASS"
PINCHED_FALLBACK = "PINCHED_FALLBACK"
FLOWS = (DRAFT_PASS, RETRY_PASS, PINCHED_FALLBACK)

DEFAULT_SEED = 2718
MAX_ATTEMPTS = 2  # retry-once: the initial call plus exactly one re-ask

KNOWN_TYPES = ("noul", "bool", "int", "float", "str")


class FormatComplaint(ValueError):
    """The judge answered, but the response failed strict format parsing."""


class GateError(RuntimeError):
    """Fail-loud refusal. Carries the flow receipt built up to the failure."""

    def __init__(self, message: str, receipt: "GateReceipt"):
        super().__init__(message)
        self.receipt = receipt


class JudgeResponse:
    """Normalized judge payload (what a transport hands back).

    answers: {qname: value-or-{type: value}} — the proven wire shape from
    tools/typesafe_batch.py is {qname: {"noul": 0.77}}; bare values are also
    accepted and coerced by the strict parser.
    """

    def __init__(self, answers: Dict[str, Any],
                 input_tokens: Optional[int] = None,
                 output_tokens: Optional[int] = None,
                 wall_s: Optional[float] = None):
        self.answers = answers
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.wall_s = wall_s


class JudgeClient(Protocol):
    """Injected transport contract. No network, no secrets in this block.

    A typesafe-style transport (tools/typesafe_batch.py) plugs in via a thin
    adapter: its state+questions payload maps verbatim; `feedback` (the pinched
    complaint on the re-ask) is folded into the transport's feedback channel.
    Any real subprocess transport must use list-form argv, never shell=True,
    and must never print or copy API tokens.
    """

    def batch(self, state: Any, questions: Dict[str, Dict[str, Any]],
              feedback: Optional[str] = None) -> Any:
        ...


def _unwrap_typed(name: str, raw: Any, qtype: str) -> Any:
    """Accept the proven {'noul': 0.77} wrapper; anything else must be bare."""
    if isinstance(raw, dict):
        if len(raw) == 1 and qtype in raw:
            return raw[qtype]
        raise FormatComplaint("%s: answer wrapper %r does not match type %r"
                              % (name, sorted(raw), qtype))
    return raw


def _coerce(name: str, raw: Any, qtype: str) -> Any:
    raw = _unwrap_typed(name, raw, qtype)
    if qtype == "noul":
        if isinstance(raw, bool):
            raise FormatComplaint("%s: bool is not a noul" % name)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise FormatComplaint("%s: %r is not a noul" % (name, raw))
        if not math.isfinite(v) or not 0.0 <= v <= 1.0:
            raise FormatComplaint("%s: noul %r out of [0,1]" % (name, raw))
        return v
    if qtype == "float":
        if isinstance(raw, bool):
            raise FormatComplaint("%s: bool is not a float" % name)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise FormatComplaint("%s: %r is not a float" % (name, raw))
        if not math.isfinite(v):
            raise FormatComplaint("%s: float %r not finite" % (name, raw))
        return v
    if qtype == "int":
        if isinstance(raw, bool):
            raise FormatComplaint("%s: bool is not an int" % name)
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            if raw.is_integer():
                return int(raw)
            raise FormatComplaint("%s: %r is not an int" % (name, raw))
        if isinstance(raw, str) and raw.strip().lstrip("+-").isdigit():
            return int(raw.strip())
        raise FormatComplaint("%s: %r is not an int" % (name, raw))
    if qtype == "bool":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
            return raw.strip().lower() == "true"
        raise FormatComplaint("%s: %r is not a bool" % (name, raw))
    if qtype == "str":
        if isinstance(raw, str) and raw.strip():
            return raw
        raise FormatComplaint("%s: %r is not a non-empty str" % (name, raw))
    raise FormatComplaint("%s: unknown question type %r" % (name, qtype))


def _normalize(raw: Any) -> JudgeResponse:
    """Accept JudgeResponse | proven-wire dict | JSON string. Else complaint."""
    if isinstance(raw, JudgeResponse):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as e:
            raise FormatComplaint("response is not strict JSON: %r" % e)
    if isinstance(raw, dict):
        answers = raw.get("answers")
        if not isinstance(answers, dict):
            raise FormatComplaint("response has no answers object")
        usage = raw.get("usage") or {}
        try:
            tin = usage.get("input_tokens")
            tout = usage.get("output_tokens")
            wall = raw.get("_wall_s")
            return JudgeResponse(answers,
                                 int(tin) if tin is not None else None,
                                 int(tout) if tout is not None else None,
                                 float(wall) if wall is not None else None)
        except (TypeError, ValueError) as e:
            raise FormatComplaint("response usage/wall malformed: %r" % e)
    raise FormatComplaint("response of type %s is not a judge payload"
                          % type(raw).__name__)


class GateReceipt:
    """Flow-state receipt. answers == {} and error != None on fail-loud paths."""

    def __init__(self, answers: Dict[str, Any], flow: Dict[str, str],
                 retries: int, pinched: bool, judge_calls: int,
                 wall_s: float, tokens_in: Optional[int],
                 tokens_out: Optional[int], error: Optional[str]):
        self.answers = answers
        self.flow = flow
        self.counts = {s: sum(1 for f in flow.values() if f == s) for s in FLOWS}
        self.retries = retries
        self.pinched = pinched
        self.judge_calls = judge_calls
        self.wall_s = wall_s
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {"answers": self.answers, "flow": self.flow, "counts": self.counts,
                "retries": self.retries, "pinched": self.pinched,
                "judge_calls": self.judge_calls, "wall_s": self.wall_s,
                "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "error": self.error}


class Gate:
    """Format-first gate over a batched judge.

    questions: list[str] (auto-wrapped as 'noul' questions keyed by the string)
    or a dict {name: {type, question, instructions}} in the proven
    typesafe_batch shape. The list is FROZEN at construction; names unique.
    fallback: deterministic Callable[[qname], value] for unanswered questions
    after a persistent format failure. None -> fail loud instead.
    judge: any JudgeClient (object with .batch or plain callable accepting
    (state, questions, feedback=None)); may raise on transport failure.
    seed: house default 2718; the gate itself is deterministic, the seed is
    reserved for downstream stochastic extensions and is recorded here.
    """

    def __init__(self, questions: Union[Sequence[str], Dict[str, Dict[str, Any]]],
                 fallback: Optional[Callable[[str], Any]] = None,
                 judge: Optional[Any] = None,
                 seed: int = DEFAULT_SEED):
        if isinstance(questions, dict):
            specs = dict(questions)
        else:
            specs = {q: {"type": "noul", "question": str(q)} for q in questions}
        if not specs:
            raise ValueError("questions must be non-empty")
        names = list(specs)
        if len(set(names)) != len(names):
            raise ValueError("question names must be unique")
        for name, spec in specs.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("question names must be non-empty strings")
            if not isinstance(spec, dict) or spec.get("type") not in KNOWN_TYPES:
                raise ValueError("question %s needs a spec with type in %s"
                                 % (name, KNOWN_TYPES))
        self._specs = specs
        self._names = names
        self._fallback = fallback
        self._judge = judge
        self.seed = seed

    @property
    def questions(self) -> List[str]:
        return list(self._names)

    def _call_judge(self, state: Any, feedback: Optional[str]) -> Any:
        if self._judge is None:
            raise ValueError("no judge injected")
        if hasattr(self._judge, "batch"):
            return self._judge.batch(state, self._specs, feedback=feedback)
        return self._judge(state, self._specs, feedback=feedback)

    def _strict_parse(self, resp: JudgeResponse) -> Dict[str, Any]:
        """Format-first: the whole batch is trusted only if EVERY named question
        is present exactly once, coerces to its declared type, with no extras."""
        answers = resp.answers
        missing = [q for q in self._names if q not in answers]
        extra = [k for k in answers if k not in self._specs]
        bad: List[str] = []
        out: Dict[str, Any] = {}
        for name in self._names:
            if name in missing:
                continue
            try:
                out[name] = _coerce(name, answers[name], self._specs[name]["type"])
            except FormatComplaint as e:
                bad.append(str(e))
        if missing or extra or bad:
            parts = []
            if missing:
                parts.append("missing %d: %s" % (len(missing), missing[:3]))
            if extra:
                parts.append("extra %d: %s" % (len(extra), extra[:3]))
            if bad:
                parts.append("mistyped %d: %s" % (len(bad), bad[:3]))
            raise FormatComplaint("; ".join(parts))
        return out

    def run(self, state: Any) -> GateReceipt:
        """Gate one state through the batched judge. Exactly ONE judge call for
        N questions on the happy path; retry-once otherwise; never more."""
        t0 = time.perf_counter()
        calls = 0
        tin = tout = 0
        have_tokens = False
        parsed: Optional[Dict[str, Any]] = None
        last_kind: Optional[str] = None
        last_err = ""
        feedback: Optional[str] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                raw = self._call_judge(state, feedback)
            except Exception as e:
                calls += 1
                last_kind = "transport"
                last_err = "judge attempt %d raised %r" % (attempt, e)
                feedback = ("TRANSPORT_COMPLAINT: " + last_err +
                            "; re-ask the identical batch once, unchanged.")
                continue
            calls += 1
            try:
                resp = _normalize(raw)
                if resp.input_tokens is not None:
                    tin += resp.input_tokens
                    have_tokens = True
                if resp.output_tokens is not None:
                    tout += resp.output_tokens
                    have_tokens = True
                parsed = self._strict_parse(resp)
                break
            except FormatComplaint as e:
                last_kind = "format"
                last_err = str(e)
                feedback = ("FORMAT_COMPLAINT: batch rejected (" + last_err +
                            "). Re-emit ALL %d answers as one strict JSON object, "
                            "keyed exactly by the question names, each value "
                            "coercible to its declared type. No prose, no extras."
                            % len(self._names))
        wall = round(time.perf_counter() - t0, 6)

        if parsed is not None:
            state_flow = DRAFT_PASS if calls == 1 else RETRY_PASS
            return GateReceipt(parsed, {q: state_flow for q in self._names},
                               retries=calls - 1, pinched=False, judge_calls=calls,
                               wall_s=wall,
                               tokens_in=tin if have_tokens else None,
                               tokens_out=tout if have_tokens else None,
                               error=None)

        receipt = GateReceipt({}, {}, retries=calls - 1, pinched=False,
                              judge_calls=calls, wall_s=wall,
                              tokens_in=tin if have_tokens else None,
                              tokens_out=tout if have_tokens else None,
                              error="%s failure after retry-once: %s"
                                    % (last_kind, last_err))
        if last_kind == "transport":
            # The judge itself is unreachable/broken: nothing to trust, and a
            # deterministic local answer cannot paper over a dead transport.
            raise GateError("judge transport failed after retry-once: %r"
                            % last_err, receipt=receipt)
        if self._fallback is None:
            raise GateError("format failure after retry-once and no fallback "
                            "configured: %s" % last_err, receipt=receipt)
        pinched_answers: Dict[str, Any] = {}
        for name in self._names:
            try:
                pinched_answers[name] = _coerce(
                    name, self._fallback(name), self._specs[name]["type"])
            except FormatComplaint as e:
                raise GateError("fallback for %s failed coercion: %s"
                                % (name, e), receipt=receipt)
        return GateReceipt(pinched_answers,
                           {q: PINCHED_FALLBACK for q in self._names},
                           retries=calls - 1, pinched=True, judge_calls=calls,
                           wall_s=wall,
                           tokens_in=tin if have_tokens else None,
                           tokens_out=tout if have_tokens else None,
                           error=receipt.error)


def mean_agreement(gold: Dict[str, Any], answers: Dict[str, Any],
                   tol: float = 1e-9) -> Optional[float]:
    """Calibration scorer ported from CM1: mean agreement with gold labels,
    over the questions present in both dicts. 1.0/0.0 per item. None if the
    overlap is empty (booked honestly, never guessed)."""
    shared = [q for q in gold if q in answers]
    if not shared:
        return None
    total = 0.0
    for q in shared:
        g, a = gold[q], answers[q]
        if isinstance(g, bool) or isinstance(a, bool):
            agree = isinstance(g, bool) and isinstance(a, bool) and g == a
        elif isinstance(g, (int, float)) and isinstance(a, (int, float)):
            agree = math.isfinite(float(g)) and math.isfinite(float(a)) and \
                math.isclose(float(g), float(a), rel_tol=0.0, abs_tol=tol)
        else:
            agree = type(g) is type(a) and g == a
        total += 1.0 if agree else 0.0
    return total / len(shared)


calibration = mean_agreement  # CM1 name for the same scorer


# --------------------------------------------------------------------------
# Self-test: scripted fake judges, CPU-only, <10s.
# --------------------------------------------------------------------------

def _wellformed(state: Any, questions: Dict[str, Dict[str, Any]],
                feedback: Optional[str] = None) -> Dict[str, Any]:
    return {"answers": {q: {"noul": 0.75} for q in questions},
            "usage": {"input_tokens": 130, "output_tokens": 41},
            "_wall_s": 0.28}


class _ScriptedJudge:
    """Pops scripted turns; each turn is a payload dict or an exception."""

    def __init__(self, turns: List[Any]):
        self.turns = list(turns)
        self.calls = 0
        self.feedback: List[Optional[str]] = []

    def batch(self, state: Any, questions: Dict[str, Dict[str, Any]],
              feedback: Optional[str] = None) -> Any:
        self.calls += 1
        self.feedback.append(feedback)
        if not self.turns:
            raise AssertionError("scripted judge exhausted after %d calls" % self.calls)
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        if callable(turn):
            return turn(state, questions, feedback=feedback)
        return turn


def _selftest() -> Tuple[bool, List[str]]:
    checks: List[Tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    # The r4 arm-B question roster: 24 named questions for 12 stimuli.
    q24 = ["S%d_%s_ok" % (i, side)
           for i in range(1, 13) for side in ("domain", "urgency")]

    # (a) always well-formed -> all DRAFT_PASS, zero retries, ONE call for N.
    j_a = _ScriptedJudge([_wellformed] * 4)
    g_a = Gate(q24, fallback=lambda q: 0.5, judge=j_a)
    r_a = g_a.run({"rule_canon": "canon", "reports": []})
    check("a.draft_pass", all(f == DRAFT_PASS for f in r_a.flow.values())
          and r_a.counts[DRAFT_PASS] == 24, str(r_a.counts))
    check("a.zero_retries", r_a.retries == 0 and not r_a.pinched)
    check("a.one_call_for_n", j_a.calls == 1 and r_a.judge_calls == 1,
          "calls=%d for %d questions" % (j_a.calls, len(q24)))
    check("a.tokens", r_a.tokens_in == 130 and r_a.tokens_out == 41)
    check("a.typed", all(isinstance(v, float) and 0.0 <= v <= 1.0
                         for v in r_a.answers.values()))
    check("a.seed_default", g_a.seed == 2718)
    r_a2 = g_a.run({"rule_canon": "canon", "reports": []})
    check("a.deterministic",
          r_a.answers == r_a2.answers and r_a.flow == r_a2.flow
          and r_a.counts == r_a2.counts and r_a.pinched == r_a2.pinched)

    # (b) malformed once, then well-formed -> RETRY_PASS, exactly one re-ask,
    #     re-ask pinched to the format complaint.
    def _malformed(state, questions, feedback=None):
        answers = {q: {"noul": 0.75} for q in questions}
        answers.pop("S3_domain_ok")                      # missing
        answers["S4_urgency_ok"] = {"noul": 1.4}         # out of range
        answers["prose"] = "I think the answer is..."    # extra
        return {"answers": answers,
                "usage": {"input_tokens": 100, "output_tokens": 30}}
    j_b = _ScriptedJudge([_malformed, _wellformed])
    g_b = Gate(q24, judge=j_b)
    r_b = g_b.run("state-b")
    check("b.retry_pass", all(f == RETRY_PASS for f in r_b.flow.values())
          and r_b.counts[RETRY_PASS] == 24, str(r_b.counts))
    check("b.exactly_one_reask", j_b.calls == 2 and r_b.retries == 1,
          "calls=%d retries=%d" % (j_b.calls, r_b.retries))
    fb1 = j_b.feedback[0]
    fb2 = j_b.feedback[1] or ""
    check("b.first_call_clean", fb1 is None)
    check("b.pinched_reask", "FORMAT_COMPLAINT" in fb2
          and "S3_domain_ok" in fb2 and "prose" in fb2, fb2[:80])
    check("b.tokens_accumulated", r_b.tokens_in == 230 and r_b.tokens_out == 71)

    # (c) persistently garbage -> PINCHED_FALLBACK with honest booking; and
    #     no-fallback configuration raises loud.
    j_c = _ScriptedJudge(["garbage, not json"] * 3)
    g_c = Gate(q24, fallback=lambda q: 0.5, judge=j_c)
    r_c = g_c.run("state-c")
    check("c.pinched_fallback",
          all(f == PINCHED_FALLBACK for f in r_c.flow.values())
          and r_c.counts[PINCHED_FALLBACK] == 24 and r_c.pinched,
          str(r_c.counts))
    check("c.fallback_answers", all(v == 0.5 for v in r_c.answers.values()))
    check("c.honest_booking", r_c.retries == 1 and r_c.error is not None
          and "format" in r_c.error and r_c.judge_calls == 2)
    g_c2 = Gate(q24, judge=_ScriptedJudge(["garbage, not json"] * 3))
    try:
        g_c2.run("state-c")
        check("c.no_fallback_loud", False, "no exception raised")
    except GateError as e:
        check("c.no_fallback_loud", True)
        check("c.error_carries_receipt", e.receipt.judge_calls == 2
              and e.receipt.answers == {} and e.receipt.error is not None)

    # (d) transport error -> loud refusal, even with a fallback configured;
    #     and transport-then-wellformed lands RETRY_PASS (retry-once).
    g_d = Gate(q24, fallback=lambda q: 0.5,
               judge=_ScriptedJudge([ConnectionError("judge down"),
                                     ConnectionError("judge down")]))
    try:
        g_d.run("state-d")
        check("d.transport_loud", False, "no exception raised")
    except GateError as e:
        check("d.transport_loud", True)
        check("d.transport_receipt", e.receipt.judge_calls == 2
              and e.receipt.retries == 1
              and "transport" in (e.receipt.error or ""))
    j_d2 = _ScriptedJudge([ConnectionError("blip"), _wellformed])
    r_d2 = Gate(q24, judge=j_d2).run("state-d2")
    check("d.transport_then_ok", all(f == RETRY_PASS for f in r_d2.flow.values())
          and r_d2.retries == 1)

    # (e) calibration scorer on a tiny gold set.
    gold = {"q1": True, "q2": False, "q3": "BOOK:engine:high",
            "q4": 0.75, "q5": 7}
    ans = {"q1": True, "q2": True, "q3": "BOOK:engine:high",
           "q4": 0.75, "q5": 7}
    check("e.calibration", mean_agreement(gold, ans) == 0.8,
          str(mean_agreement(gold, ans)))
    check("e.empty_overlap_none",
          mean_agreement({"z": 1}, {"q1": True}) is None)
    check("e.bool_not_int", mean_agreement({"b": True}, {"b": 1}) == 0.0)
    check("e.coerced_float_ok", mean_agreement({"n": 0.5},
                                               {"n": 0.5}) == 1.0)

    # Flow-state universe is exactly the three proven states.
    universe_ok = all(f in FLOWS for f in r_a.flow.values()) and \
        all(f in FLOWS for f in r_b.flow.values()) and \
        all(f in FLOWS for f in r_c.flow.values())
    check("flow_universe", universe_ok)

    ok_all = all(ok for _, ok, _ in checks)
    for name, ok, detail in checks:
        print("check %-24s %s %s" % (name + ":", "ok" if ok else "FAIL", detail))
    return ok_all, ["%s:%s" % (n, "ok" if ok else "FAIL") for n, ok, _ in checks]


def main() -> int:
    ok_all, _ = _selftest()
    verdict = "PASS" if ok_all else "FAIL"
    # Final stdout line: exactly one JSON object with exactly one top-level
    # "verdict" field. Exit 0 iff PASS.
    print(json.dumps({"verdict": verdict}))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
