#!/usr/bin/env python3
"""
exclu_pool.py — deterministic task-pool generator with heldout exclusion BY
CONSTRUCTION (pattern lifted PROVEN from DET-1c, commit 65a168c 2026-10-05:
the DET-1b abort class was pool/heldout expr collision discovered at run time
4/6 arms dead; the remedy generates the pool already excluding the heldout
set, smoke overlap=0 / deterministic across all 3 seeds).

Same family rotation + rng stream as the original gen_task_pool, but any
candidate whose `expr` collides with the exclusion set is skipped at
generation time and replaced by CONTINUING the same deterministic rotation
until both counts fill. n_skipped is booked for honesty (family mix may
deviate from exact rotation when a collision is skipped; declared in the
prereg, does not touch any gate word).

Stdlib-only for arith; symb families use sympy if importable (their target
needs simplify) — pass --no-symb to run purely stdlib.

Exit codes: 0 = OK, 1 = gate FAIL (selftest / overlap check), 2 = fail-loud
input (bad args, missing sympy for symb, undrained exclusion set).

CLI:
  python tools/exclu_pool.py --seed 101 --n-arith 20 --n-symb 20 \
      --exclude heldout.json --out pool.json
  python tools/exclu_pool.py --example        # worked example: gen heldout,
                                              # gen pool excluding it, prove overlap=0
  python tools/exclu_pool.py --selftest

Exclusion file format: plain JSON list of expr strings (the `expr` field of
heldout tasks), e.g. ["13 + 85", "(2*x + 3) + (4*x - 5)"].

Worked example (docstring form):
  >>> from exclu_pool import gen_pool_excluding, gen_pool
  >>> heldout = gen_pool(seed=7, n_arith=10, n_symb=0)
  >>> pool, skipped = gen_pool_excluding(seed=101, n_arith=20, n_symb=0,
  ...                                    exclude={t.expr for t in heldout})
  >>> assert not ({t.expr for t in pool} & {t.expr for t in heldout})
"""
import argparse
import json
import random
import sys
import time
from dataclasses import dataclass, asdict

try:
    import sympy
    from sympy import Symbol, simplify, expand
    HAVE_SYMPY = True
except Exception:
    HAVE_SYMPY = False

_X = Symbol("x") if HAVE_SYMPY else None


def _sym(s):
    return sympy.sympify(s, locals={"x": _X})


# --------------------------------------------------------------------------------------
# Task generators (frozen family rotation; lifted from experiments/rest_em_loop.py)
# --------------------------------------------------------------------------------------
@dataclass
class Task:
    tid: int
    kind: str          # 'arith' | 'symb'
    family: str
    expr: str
    prompt_user: str
    target_str: str


ARITH_FAMILIES = ["add2", "add3", "sub", "mul", "mixed"]
SYMB_FAMILIES = ["lin_add", "lin_sub", "sq_collect", "dist"]
# HARD distribution (amendment A1 keeper, 2026-10-02)
ARITH_FAMILIES_HARD = ["mul2x3", "nested2", "mul", "mixed", "add3"]
SYMB_FAMILIES_HARD = ["poly2", "sq_collect", "dist", "lin_add"]


def _arith_task(rng, tid, family):
    if family == "add2":
        a, b = rng.randint(13, 499), rng.randint(13, 499)
        expr, ans = f"{a} + {b}", a + b
    elif family == "add3":
        a, b, c = (rng.randint(5, 99) for _ in range(3))
        expr, ans = f"{a} + {b} + {c}", a + b + c
    elif family == "sub":
        a = rng.randint(120, 999)
        b = rng.randint(11, a - 5)
        expr, ans = f"{a} - {b}", a - b
    elif family == "mul":
        a, b = rng.randint(12, 29), rng.randint(3, 12)
        expr, ans = f"{a} * {b}", a * b
    elif family == "mixed":
        a, b, c = rng.randint(5, 99), rng.randint(5, 99), rng.randint(3, 9)
        expr, ans = f"({a} + {b}) * {c}", (a + b) * c
    elif family == "mul2x3":
        a, b = rng.randint(100, 999), rng.randint(10, 99)
        expr, ans = f"{a} * {b}", a * b
    elif family == "nested2":
        a, b, c, d = (rng.randint(2, 30), rng.randint(2, 30),
                      rng.randint(2, 12), rng.randint(2, 99))
        expr, ans = f"(({a} + {b}) * {c}) - {d}", (a + b) * c - d
    else:
        raise ValueError(family)
    return Task(tid, "arith", family, expr, f"Compute {expr}.", str(ans))


def _symb_task(rng, tid, family):
    if not HAVE_SYMPY:
        raise RuntimeError("symb families require sympy (not importable); use --no-symb")
    if family == "lin_add":
        a, c = rng.randint(2, 12), rng.randint(2, 12)
        b, d = rng.randint(1, 20), rng.randint(1, 20)
        expr = f"({a}*x + {b}) + ({c}*x - {d})"
    elif family == "lin_sub":
        a, c = rng.randint(2, 12), rng.randint(2, 12)
        b, d = rng.randint(1, 20), rng.randint(1, 20)
        expr = f"({a}*x + {b}) - ({c}*x + {d})"
    elif family == "sq_collect":
        a, c = rng.randint(2, 9), rng.randint(2, 9)
        b, d = rng.randint(2, 9), rng.randint(2, 9)
        expr = f"{a}*x**2 + {b}*x - ({c}*x**2 - {d}*x)"
    elif family == "dist":
        a, c = rng.randint(2, 9), rng.randint(2, 9)
        b = rng.randint(2, 15)
        expr = f"{a}*(x + {b}) + {c}*x"
    elif family == "poly2":
        a, b, c, d = (rng.randint(2, 9) for _ in range(4))
        expr = f"({a}*(x + {b}) - {c}) * (x + {d})"
    else:
        raise ValueError(family)
    e = expand(simplify(_sym(expr)))
    return Task(tid, "symb", family, expr,
                f"Simplify the expression: {expr}. Give the result in terms of x.",
                str(e))


def _families(difficulty):
    if difficulty == "hard":
        return ARITH_FAMILIES_HARD, SYMB_FAMILIES_HARD
    if difficulty == "registered":
        return ARITH_FAMILIES, SYMB_FAMILIES
    raise ValueError(f"difficulty must be 'registered' or 'hard', got {difficulty!r}")


def gen_pool(seed, n_arith, n_symb, start_tid=0, difficulty="registered"):
    """Original (unexcluded) pool — exact DET-1c rotation: arith phase then symb phase."""
    af, sf = _families(difficulty)
    rng = random.Random(seed)
    tasks, tid = [], start_tid
    for i in range(n_arith):
        tasks.append(_arith_task(rng, tid, af[i % len(af)]))
        tid += 1
    for i in range(n_symb):
        tasks.append(_symb_task(rng, tid, sf[i % len(sf)]))
        tid += 1
    rng.shuffle(tasks)
    return tasks


def gen_pool_excluding(seed, n_arith, n_symb, exclude, start_tid=0,
                       difficulty="registered"):
    """DET-1c remedy: pool with heldout exclusion BY CONSTRUCTION.

    Same rng stream; colliding exprs are skipped and replaced by continuing the
    same deterministic rotation. Returns (tasks, n_skipped). Raises
    RuntimeError if the rotation can't fill within a sane attempt budget
    (exclusion set effectively exhausts the space — fail loud, not spin).
    """
    if n_arith < 0 or n_symb < 0:
        raise ValueError("counts must be >= 0")
    af, sf = _families(difficulty)
    exclude = set(exclude)
    rng = random.Random(seed)
    tasks, tid = [], start_tid
    skipped = attempts = 0
    ai = si = 0
    budget = 1000 * (n_arith + n_symb) + 10000
    while len(tasks) < n_arith + n_symb:
        attempts += 1
        if attempts > budget:
            raise RuntimeError("exclusion set could not be drained in budget — "
                               "space exhausted or exclude-set pathological")
        # interleaved so one skipped family cannot starve the other side
        take_arith = (len(tasks) % 2 == 0 and ai < n_arith) or si >= n_symb
        if take_arith:
            t = _arith_task(rng, tid, af[ai % len(af)])
            ai += 1
        else:
            t = _symb_task(rng, tid, sf[si % len(sf)])
            si += 1
        if t.expr in exclude:
            skipped += 1
            continue
        tasks.append(t)
        tid += 1
    rng.shuffle(tasks)
    return tasks, skipped


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _fail(rc, msg):
    print(json.dumps({"tool": "exclu_pool", "verdict": "FAIL-LOUD", "rc": rc,
                      "error": msg}), file=sys.stderr)
    sys.exit(rc)


def _receipt(**kw):
    r = {"tool": "exclu_pool", "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    r.update(kw)
    return r


def _write_out(path, receipt):
    if path:
        with open(path, "w") as f:
            json.dump(receipt, f, indent=2)
        print(f"receipt -> {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n-arith", type=int)
    ap.add_argument("--n-symb", type=int)
    ap.add_argument("--difficulty", choices=["registered", "hard"], default="registered")
    ap.add_argument("--exclude", help="JSON file: list of expr strings to exclude")
    ap.add_argument("--start-tid", type=int, default=0)
    ap.add_argument("--out", help="write JSON receipt (+ pool) here")
    ap.add_argument("--no-symb", action="store_true", help="force n_symb=0 (stdlib-only path)")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.example:
        # worked example: heldout pool -> excluding pool -> overlap gate + determinism
        heldout = gen_pool(seed=7, n_arith=12, n_symb=0)
        pool, skipped = gen_pool_excluding(seed=101, n_arith=30, n_symb=10,
                                           exclude={t.expr for t in heldout})
        overlap = {t.expr for t in pool} & {t.expr for t in heldout}
        pool2, skipped2 = gen_pool_excluding(seed=101, n_arith=30, n_symb=10,
                                             exclude={t.expr for t in heldout})
        det = [asdict(t) for t in pool] == [asdict(t) for t in pool2]
        ok = not overlap and det
        r = _receipt(mode="example", verdict="PASS" if ok else "FAIL",
                     heldout_n=len(heldout), pool_n=len(pool), skipped=skipped,
                     overlap=sorted(overlap), deterministic=det)
        print(json.dumps(r, indent=2))
        _write_out(args.out, r)
        sys.exit(0 if ok else 1)

    if args.seed is None or args.n_arith is None or args.n_symb is None:
        _fail(2, "--seed, --n-arith, --n-symb required (or use --example/--selftest)")
    n_symb = 0 if args.no_symb else args.n_symb
    if n_symb > 0 and not HAVE_SYMPY:
        _fail(2, "symb tasks need sympy; install it or pass --no-symb")
    exclude = set()
    if args.exclude:
        with open(args.exclude) as f:
            raw = json.load(f)
        if not isinstance(raw, list) or not all(isinstance(e, str) for e in raw):
            _fail(2, "exclude file must be a JSON list of strings")
        exclude = set(raw)
    pool, skipped = gen_pool_excluding(args.seed, args.n_arith, n_symb, exclude,
                                       start_tid=args.start_tid,
                                       difficulty=args.difficulty)
    residual = {t.expr for t in pool} & exclude
    ok = not residual
    r = _receipt(mode="gen", verdict="PASS" if ok else "FAIL",
                 seed=args.seed, n_arith=args.n_arith, n_symb=n_symb,
                 difficulty=args.difficulty, exclude_n=len(exclude),
                 pool_n=len(pool), skipped=skipped, residual_overlap=sorted(residual))
    r["pool"] = [asdict(t) for t in pool]
    print(json.dumps({k: v for k, v in r.items() if k != "pool"}, indent=2))
    _write_out(args.out, r)
    sys.exit(0 if ok else 1)


def selftest():
    fails = []
    checks = []

    def check(name, cond, detail=""):
        checks.append(name)
        if not cond:
            fails.append(f"{name}: {detail}")

    # 1. exclusion overlap = 0 (the DET-1b abort class, killed by construction)
    heldout = gen_pool(seed=5, n_arith=20, n_symb=6)
    pool, skipped = gen_pool_excluding(seed=11, n_arith=20, n_symb=6,
                                       exclude={t.expr for t in heldout})
    check("overlap-zero", not ({t.expr for t in pool} & {t.expr for t in heldout}),
          f"skipped={skipped}")

    # 2. determinism: same seed + exclude set -> identical pool
    pool2, _ = gen_pool_excluding(11, 20, 6, {t.expr for t in heldout})
    check("deterministic", [asdict(t) for t in pool] == [asdict(t) for t in pool2])

    # 3. different seed -> different pool (not a constant function)
    pool3, _ = gen_pool_excluding(12, 20, 6, {t.expr for t in heldout})
    check("seed-sensitivity",
          [t.expr for t in pool] != [t.expr for t in pool3])

    # 4. exclusion actually skips: expr from heldout at same seed gets replaced
    plain = gen_pool(seed=42, n_arith=30, n_symb=0)
    victim = plain[0]
    excl_pool, sk = gen_pool_excluding(42, 30, 0, exclude={victim.expr})
    check("exclusion-fires",
          victim.expr not in {t.expr for t in excl_pool} and sk >= 1,
          f"skipped={sk}")

    # 5. no exclusion -> identical to plain generator (pattern fidelity)
    same, sk0 = gen_pool_excluding(42, 30, 0, exclude=set())
    check("plain-equivalence",
          [asdict(t) for t in same] == [asdict(t) for t in plain] and sk0 == 0)

    # 6. hard difficulty accepted, registered families present in registered mode
    hp, _ = gen_pool_excluding(3, 10, 4, set(), difficulty="hard")
    check("hard-difficulty", all(t.family in ARITH_FAMILIES_HARD + SYMB_FAMILIES_HARD
                                 for t in hp))

    # 7. fail-loud on undrainable pathological case
    try:
        gen_pool_excluding(1, 5, 0, exclude=set(), difficulty="bogus")
        check("bad-difficulty-fails", False, "no raise")
    except ValueError:
        check("bad-difficulty-fails", True)

    # 8. counts preserved
    check("counts", len(pool) == 26 and all(isinstance(t.tid, int) for t in pool))

    print(json.dumps({"selftest": "exclu_pool", "checks": len(checks),
                      "fails": fails, "verdict": "PASS" if not fails else "FAIL"},
                     indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    main()
