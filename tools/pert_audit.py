#!/usr/bin/env python3
"""pert-audit — generic corruption-sensitivity (leakage) audit for any text scorer.

Pattern lifted PROVEN from ST1-AUDIT (booked 2026-10-07, commit 0988f17:
verdict_flip & tau_off mechanically LEAKY at AUC 1.0 while honest-path scorers
stayed weak — "is a checker driven by content or by operation artifacts?" is a
MEASUREMENT, made by scoring clean vs corrupted inputs and ranking separation).

Given N pairs {clean, corrupt} (corrupt may be null => skipped with an honest
count) and ANY scorer command (list-form subprocess: JSON object on stdin,
{"score": <number>} on stdout), this tool:
  1. scores every clean and corrupt text through the scorer,
  2. computes paired AUC P(score(corrupt) > score(clean)) with ties = 0.5,
  3. guards degeneracy (all scores identical => the audit cannot speak),
  4. books a verdict:   LEAKY   if AUC >= --hi (default 0.95)
                        CLEAN   if AUC <= --lo (default 0.60)
                        MIXED   otherwise (needs eyes — booked honestly)
  5. writes one fail-loud JSON receipt. rc 0 = CLEAN, 1 = LEAKY / MIXED /
     DEGENERATE, 2 = fail-loud input (bad JSON, missing score key, scorer
     nonzero, non-finite score, n_valid == 0).

Stdlib-only. The scorer command is never run through a shell; secrets are the
caller's business and are never touched by this file.

Worked example (selftest scorers, no external deps):
  python tools/pert_audit.py --example
  # verdict-artifact detector on flipped verdicts -> LEAKY rc=1
  # honest consistency scorer on the same pairs    -> MIXED rc=1 (never fake CLEAN)

CLI:
  python tools/pert_audit.py --pairs pairs.json --scorer CMD --scorer-args a,b \
      [--hi 0.95 --lo 0.60 --out r.json]
  python tools/pert_audit.py --selftest
pairs.json: [{"clean": "...", "corrupt": "..."}, ...]
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg, code=2):
    print(f"pert-audit: FAIL({code}): {msg}", file=sys.stderr)
    sys.exit(code)


def score_one(cmd, args_, text, timeout=60):
    """Run the scorer on one text; return float score. Fail-loud on anything odd."""
    payload = json.dumps({"text": text})
    try:
        proc = subprocess.run(
            [cmd] + list(args_),
            input=payload, capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        fail(f"scorer launch failed: {e}")
    if proc.returncode != 0:
        fail(f"scorer exited {proc.returncode}: {proc.stderr.strip()[:300]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        fail(f"scorer stdout is not JSON: {proc.stdout.strip()[:200]}")
    if not isinstance(out, dict) or "score" not in out:
        fail("scorer JSON lacks a 'score' key")
    s = out["score"]
    if not isinstance(s, (int, float)) or isinstance(s, bool) or not math.isfinite(s):
        fail(f"scorer score not a finite number: {s!r}")
    return float(s)


def auc_paired(clean_scores, corrupt_scores):
    """P(corrupt > clean) + 0.5 P(equal), paired — ties count half."""
    win = 0.0
    for c, k in zip(clean_scores, corrupt_scores):
        if k > c:
            win += 1.0
        elif k == c:
            win += 0.5
    return win / len(clean_scores)


def run_audit(pairs, cmd, args_, hi, lo):
    clean_s, corrupt_s = [], []
    skipped = 0
    for i, p in enumerate(pairs):
        if not isinstance(p, dict) or "clean" not in p:
            fail(f"pair {i} lacks 'clean'")
        corrupt = p.get("corrupt")
        if corrupt is None:
            skipped += 1
            continue
        clean_s.append(score_one(cmd, args_, p["clean"]))
        corrupt_s.append(score_one(cmd, args_, corrupt))
    n = len(clean_s)
    if n == 0:
        fail("no valid pairs (all null-corrupt or empty input)")
    a = auc_paired(clean_s, corrupt_s)
    degenerate = len(set(clean_s + corrupt_s)) == 1
    if degenerate:
        verdict = "DEGENERATE"   # audit cannot speak; booked honestly, rc=1
        rc = 1
    elif a >= hi:
        verdict, rc = "LEAKY", 1
    elif a <= lo:
        verdict, rc = "CLEAN", 0
    else:
        verdict, rc = "MIXED", 1
    return {
        "n_pairs": len(pairs), "n_valid": n, "n_skipped_null_corrupt": skipped,
        "auc": a, "degenerate": degenerate, "hi": hi, "lo": lo,
        "verdict": verdict, "rc": rc,
        "scorer": [cmd] + list(args_),
    }


# ------------------------------------------------------------------ selftest

def _ex(rng):
    verdict = rng.choice(["KEEP", "KILL"])
    wins = rng.randint(3, 9)
    npairs = rng.randint(10, 14)
    tau = round(rng.uniform(0.42, 0.58), 2)
    return {"wins": wins, "n_pairs": npairs, "tau": tau, "verdict": verdict}, verdict


def _render(ex, rng):
    if rng.random() < 0.5:
        return json.dumps(ex, sort_keys=True)
    return (f"verdict: {ex['verdict']}\nmri: {ex.get('mri', 0.0):+.3f}\n"
            f"wins: {ex['wins']} of {ex['n_pairs']} pairs\n"
            f"tau: {ex['tau']:.2f} (grid 0.40-0.60)")


def _corrupt(ex, rng):
    o = json.loads(json.dumps(ex))
    op = rng.choice(["verdict_flip", "tau_off"])
    if op == "verdict_flip":
        o["verdict"] = "KILL" if o["verdict"] == "KEEP" else "KEEP"
    else:
        o["tau"] = rng.choice([0.30, 0.65, 0.99])
    return o, op


ARTIFACT_SCORER = (
    "import json,sys,re\n"
    "t=json.load(sys.stdin)['text']\n"
    "mv=re.search(r'verdict\\\"?:\\s*\\\"?(\\w+)', t)\n"
    "mm=re.search(r'mri\\\"?:\\s*\\\"?([+-]?[\\d.]+)', t)\n"
    "if not (mv and mm):\n"
    "    print(json.dumps({'score': 0.0}))\n"
    "else:\n"
    "    honest = 'KEEP' if float(mm.group(1)) > 0 else 'KILL'\n"
    "    print(json.dumps({'score': 0.0 if mv.group(1) == honest else 1.0}))\n"
)

HONEST_SCORER = (
    "import json,sys,re\n"
    "t=json.load(sys.stdin)['text']\n"
    "m=re.search(r'wins\\\"?:\\s*\\\"?(\\d+)\\s+of\\s+(\\d+)', t)\n"
    "ok = (not m) or (int(m.group(1)) <= int(m.group(2)))\n"
    "mj=re.search(r'verdict\\\"?:\\s*\\\"?(\\w+)', t)\n"
    "s = 1.0 if (ok and mj and mj.group(1) in ('KEEP','KILL')) else 0.0\n"
    "print(json.dumps({'score': s}))\n"
)


def selftest():
    """FAIL-FIRST battery: artifact-driven scorer must book LEAKY, an honest
    scorer MIXED-not-fake-CLEAN, and the fail-loud paths must fire."""
    import random
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)

        # pin1 positive control: an artifact detector that derives the honest
        # verdict from mri (ST1-AUDIT's mechanical_flag in spirit) —
        # flip-corrupt pairs disagree, clean ones don't; this MUST trip LEAKY
        # or the audit is blind.
        scorer_a = tdp / "scorer_artifact.py"
        scorer_a.write_text(ARTIFACT_SCORER)
        flip_pairs = []
        rng2 = random.Random(2718)
        for _ in range(80):
            ex, _ = _ex(rng2)
            ex["mri"] = round(rng2.uniform(0.05, 0.4), 3)   # KEEP-honest numbers
            ex["verdict"] = "KEEP"                          # clean = honest book
            o = json.loads(json.dumps(ex))
            o["verdict"] = "KILL"                           # corrupt = flipped
            flip_pairs.append({"clean": _render(ex, rng2),
                               "corrupt": _render(o, rng2)})
        r = run_audit(flip_pairs, sys.executable, [str(scorer_a)], 0.95, 0.60)
        assert r["verdict"] == "LEAKY" and r["auc"] >= 0.95, f"pin1 blind audit: {r}"

        # pin2: honest consistency checker (wins<=n_pairs, verdict well-formed);
        # tau_off corruption doesn't touch those => scores equal => AUC 0.5 =>
        # MIXED (needs eyes) — an honest book, not a fake CLEAN.
        scorer_b = tdp / "scorer_honest.py"
        scorer_b.write_text(HONEST_SCORER)
        mixed_pairs = []
        rng3 = random.Random(1618)
        for _ in range(80):
            ex, _ = _ex(rng3)
            o = json.loads(json.dumps(ex))
            o["tau"] = rng3.choice([0.30, 0.99])   # off-band but structurally fine
            mixed_pairs.append({"clean": _render(ex, rng3),
                                "corrupt": _render(o, rng3)})
        r2 = run_audit(mixed_pairs, sys.executable, [str(scorer_b)], 0.95, 0.60)
        # An honest scorer that cannot see the corruption scores both sides
        # identically => all-1.0 => DEGENERATE (the audit cannot speak). The
        # honest book. It must NEVER book CLEAN.
        assert r2["verdict"] in ("MIXED", "DEGENERATE") and r2["auc"] <= 0.6, f"pin2: {r2}"

        # pin3 fail-loud: scorer exits nonzero
        bad = tdp / "bad.py"
        bad.write_text("import sys; sys.exit(3)\n")
        try:
            run_audit(mixed_pairs[:2], sys.executable, [str(bad)], 0.95, 0.60)
            raise AssertionError("pin3: nonzero-exit scorer not caught")
        except SystemExit as e:
            assert e.code == 2, f"pin3 rc: {e.code}"

        # pin4 fail-loud: missing score key
        nos = tdp / "noscore.py"
        nos.write_text("import json,sys; print(json.dumps({'x':1}))\n")
        try:
            run_audit(mixed_pairs[:2], sys.executable, [str(nos)], 0.95, 0.60)
            raise AssertionError("pin4: missing score not caught")
        except SystemExit as e:
            assert e.code == 2, f"pin4 rc: {e.code}"

        # pin5 fail-loud: all-null corrupt => no valid pairs
        try:
            run_audit([{"clean": "a", "corrupt": None}], sys.executable,
                      [str(scorer_b)], 0.95, 0.60)
            raise AssertionError("pin5: empty valid set not caught")
        except SystemExit as e:
            assert e.code == 2, f"pin5 rc: {e.code}"

    print(json.dumps({"selftest": "PASS", "pins": 5,
                      "sha256": hashlib.sha256(
                          Path(__file__).read_bytes()).hexdigest()[:16]}))
    return 0


def example():
    """Two live audits with embedded scorers (ST1-AUDIT miniature):
    verdict-flip corruption vs an artifact detector (LEAKY expected) and the
    same corruption vs an honest consistency scorer (equal scores -> MIXED,
    honestly booked)."""
    import random
    rng = random.Random(2718)
    flip_pairs = []
    for _ in range(60):
        ex, _ = _ex(rng)
        ex["mri"] = round(rng.uniform(0.05, 0.4), 3)
        ex["verdict"] = "KEEP"
        o = json.loads(json.dumps(ex))
        o["verdict"] = "KILL"
        flip_pairs.append({"clean": _render(ex, rng), "corrupt": _render(o, rng)})
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        artifact = tdp / "artifact.py"
        artifact.write_text(ARTIFACT_SCORER)
        r1 = run_audit(flip_pairs, sys.executable, [str(artifact)], 0.95, 0.60)
        honest = tdp / "honest.py"
        honest.write_text(HONEST_SCORER)
        r2 = run_audit(flip_pairs, sys.executable, [str(honest)], 0.95, 0.60)
    print(json.dumps({"artifact_detector_on_flips": r1["verdict"],
                      "auc_artifact": r1["auc"],
                      "honest_scorer_on_flips": r2["verdict"],
                      "auc_honest": r2["auc"],
                      "lesson": "artifact detectors book LEAKY; honest content "
                                "scorers that cannot see the corruption book "
                                "MIXED/DEGENERATE — never a fake CLEAN"}, indent=1))
    return 1 if r1["verdict"] == "LEAKY" else 0


def main():
    ap = argparse.ArgumentParser(
        description="corruption-sensitivity (leakage) audit for text scorers")
    ap.add_argument("--pairs", help="JSON file of {clean, corrupt} pairs")
    ap.add_argument("--pairs-json", help="inline JSON pairs")
    ap.add_argument("--scorer", help="scorer command (list-form, no shell)")
    ap.add_argument("--scorer-args", default="",
                    help="comma-separated scorer args")
    ap.add_argument("--hi", type=float, default=0.95, help="LEAKY bar")
    ap.add_argument("--lo", type=float, default=0.60, help="CLEAN bar")
    ap.add_argument("--out", help="receipt path")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.example:
        sys.exit(example())
    if not (a.pairs or a.pairs_json) or not a.scorer:
        fail("--pairs/--pairs-json and --scorer required (or --selftest/--example)")
    if a.lo >= a.hi:
        fail(f"lo ({a.lo}) must be < hi ({a.hi})")
    src = Path(a.pairs).read_text() if a.pairs else a.pairs_json
    try:
        pairs = json.loads(src)
    except json.JSONDecodeError as e:
        fail(f"pairs JSON: {e}")
    if not isinstance(pairs, list) or not pairs:
        fail("pairs must be a non-empty JSON array")
    args_ = [x for x in a.scorer_args.split(",") if x] if a.scorer_args else []
    r = run_audit(pairs, a.scorer, args_, a.hi, a.lo)
    if a.out:
        dest = Path(a.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
    sys.exit(r["rc"])


if __name__ == "__main__":
    main()
