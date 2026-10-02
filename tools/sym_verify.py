#!/usr/bin/env python3
"""
sym-verify — standalone executable answer verifier for generated math answers.

Pattern lifted PROVEN from experiments/rest_em_loop.py (ReST-EM/QLoRA smoke,
2026-10-01: verifier 8/8 accept + 12/12 reject on the smoke run). No LLM judge
anywhere: regex 'Answer:' extraction, strict integer equality for arithmetic,
sympy simplify + frozen rational-probe property test for symbolic equality.

Why grabbable: any generate-then-check loop (ReST-EM, self-play, dataset
distillation) needs the same judge — copy this one file, no harness.

Usage:
    python tools/sym_verify.py --kind arith --target 132 --text 'Answer: 132'
    python tools/sym_verify.py --kind symb --target '4*x - 3' --text 'Answer: -3 + 4*x'
    echo 'Answer: 4x - 3' | python tools/sym_verify.py --kind symb --target '4*x - 3' --stdin
    python tools/sym_verify.py --selftest      # negative-control battery, must be 100%

Output: one JSON receipt {ok, reason, answer, kind}. Exit 0 if ok, 1 if judged
REJECT, 2 on FAIL-INPUT (bad args / selftest failure). sympy is optional; only
--kind symb needs it (fails loud rc=2 without it).

Docstring worked example (live-tested):
    >>> # arith accept:  {"ok": true,  "reason": "exact"}
    >>> # arith reject:  {"ok": false, "reason": "wrong_value"}   (off-by-one)
    >>> # symb accept:   {"ok": true,  "reason": "exact_simplify"} or "numeric_property"
    >>> # symb reject:   {"ok": false, "reason": "numeric_mismatch"|"parse_error"|"unsafe"|...}
"""
from __future__ import annotations

import argparse
import json
import re
import sys

try:
    import sympy
    from sympy import Rational, Symbol, simplify
    from sympy.parsing.sympy_parser import (
        implicit_multiplication_application,
        convert_xor,
        parse_expr,
        standard_transformations,
    )
    HAVE_SYMPY = True
except Exception:  # pragma: no cover
    HAVE_SYMPY = False

X = Symbol("x")  # single shared symbol; never real=True (assumption mismatch = invisible bug)
LOCAL_DICT = {"x": X}
TRANSFORMS = standard_transformations + (convert_xor, implicit_multiplication_application)
PROBE_POINTS = [Rational(-7, 3), Rational(-1, 2), Rational(1, 5), Rational(2), Rational(13, 4)]
UNSAFE_SUBSTRINGS = ["__", "lambda", ";", "import", "eval", "exec", "open(", "input("]
ANSWER_RE = re.compile(r"(?is)answer\s*[:\-]\s*([^\n]+)")


def extract_answer(text: str):
    """Return the last 'Answer: ...' payload, or None."""
    if not text:
        return None
    matches = ANSWER_RE.findall(text)
    if not matches:
        return None
    return matches[-1].strip().rstrip(".").strip()


def check_arith(ans_str: str, target: int):
    s = ans_str.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+", s):
        return False, "not_int"
    return int(s) == target, "exact" if int(s) == target else "wrong_value"


def check_symbolic(ans_str: str, target_expr):
    if not HAVE_SYMPY:
        raise RuntimeError("sympy required for --kind symb")
    s = ans_str.strip()
    if any(b in s for b in UNSAFE_SUBSTRINGS):
        return False, "unsafe"
    try:
        expr = parse_expr(s, local_dict=LOCAL_DICT, transformations=TRANSFORMS, evaluate=True)
    except Exception:
        return False, "parse_error"
    try:
        if not (getattr(expr, "free_symbols", set()) <= {X}):
            return False, "bad_symbols"
    except Exception:
        return False, "bad_symbols"
    try:
        if simplify(expr - target_expr) == 0:
            return True, "exact_simplify"
    except Exception:
        pass
    # Property test: numeric substitution at frozen rational points.
    try:
        for pt in PROBE_POINTS:
            d = abs(complex((expr - target_expr).subs({X: pt}).evalf()))
            if not (d == d) or d > 1e-9:  # NaN or mismatch
                return False, "numeric_mismatch"
        return True, "numeric_property"
    except Exception:
        return False, "numeric_error"


def check(text: str, kind: str, target):
    """Full judge: extract then check. Returns (ok, reason, answer). No LLM anywhere."""
    ans = extract_answer(text)
    if ans is None:
        return False, "no_answer_tag", None
    if kind == "arith":
        ok, reason = check_arith(ans, int(target))
    else:
        ok, reason = check_symbolic(ans, sympy.sympify(target, locals={"x": X}))
    return ok, reason, ans


def self_test() -> dict:
    """Negative-control battery. Must be 100% or callers should abort the run."""
    sym = lambda s: sympy.sympify(s, locals={"x": X})
    accept_cases = [
        ("arith", 132, "47 + 85 = 132\nAnswer: 132"),
        ("arith", 132, "I think it is 132.\nAnswer: 132"),
        ("arith", 136, "Answer: 136"),
        ("symb", "4*x - 3", "Combining: 4*x - 3\nAnswer: 4*x - 3"),
        ("symb", "4*x - 3", "Answer: -3 + 4*x"),
        ("symb", "4*x - 3", "Answer: 4x - 3"),          # implicit-multiplication leniency (intended)
        ("symb", "2*x**2 + 5*x", "Answer: 2*x**2 + 5*x"),
        ("symb", "2*x**2 + 5*x", "Answer: 5*x + 2*x^2"),  # convert_xor leniency (intended)
    ]
    reject_cases = [
        ("arith", 132, "Answer: 131"),        # off by one
        ("arith", 132, "Answer: 133"),        # off by one
        ("arith", 132, "Answer: 132.0"),      # strict integer format
        ("arith", 132, "the answer is 132"),  # no Answer tag
        ("arith", 132, ""),                   # empty
        ("arith", 136, "Answer: 135"),
        ("symb", "4*x - 3", "Answer: 5*x - 3"),       # wrong coefficient
        ("symb", "4*x - 3", "Answer: 4*y - 3"),       # wrong variable
        ("symb", "4*x - 3", "Answer: 4*x - 3 + 1"),   # wrong constant
        ("symb", "4*x - 3", "Answer: banana"),        # garbage
        ("symb", "2*x**2 + 5*x", "Answer: 2*x**2 + 5"),  # dropped term
        ("symb", "2*x**2 + 5*x", "Answer: x**3"),
    ]
    a_fail = [(t, check(t, k, tgt)) for (k, tgt, t) in accept_cases if not check(t, k, tgt)[0]]
    r_fail = [(t, check(t, k, tgt)) for (k, tgt, t) in reject_cases if check(t, k, tgt)[0]]
    return {
        "n_accept_cases": len(accept_cases), "n_reject_cases": len(reject_cases),
        "accept_failures": a_fail, "reject_failures": r_fail,
        "passed": (not a_fail) and (not r_fail),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Executable answer verifier (no LLM judge).")
    ap.add_argument("--kind", choices=["arith", "symb"], help="arith: strict int; symb: sympy equivalence")
    ap.add_argument("--target", help="expected int (arith) or expression in x (symb)")
    ap.add_argument("--text", help="model output containing an 'Answer: ...' line")
    ap.add_argument("--stdin", action="store_true", help="read model output from stdin instead of --text")
    ap.add_argument("--selftest", action="store_true", help="run negative-control battery and exit")
    args = ap.parse_args()

    if args.selftest:
        r = self_test()
        print(json.dumps(r, indent=2, default=str))
        return 0 if r["passed"] else 2

    if not args.kind or args.target is None:
        print("FAIL-INPUT: --kind and --target required (or --selftest)", file=sys.stderr)
        return 2
    text = args.text
    if args.stdin:
        text = sys.stdin.read()
    if text is None:
        print("FAIL-INPUT: provide --text or --stdin", file=sys.stderr)
        return 2
    if args.kind == "symb" and not HAVE_SYMPY:
        print("FAIL-INPUT: sympy not installed; --kind symb unavailable", file=sys.stderr)
        return 2

    ok, reason, ans = check(text, args.kind, args.target)
    print(json.dumps({"ok": ok, "reason": reason, "answer": ans, "kind": args.kind}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
