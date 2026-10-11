#!/usr/bin/env python3
"""vexit_check — VERDICT-line vs exit-code convention witness (VEXIT-1 pattern).

Pattern lifted PROVEN from VEXIT-1 (commits 10b3f0b/a5adb43, 2026-10-11): the
fleet adopted the convention that a tool prints its final `VERDICT: GREEN` /
`VERDICT: RED` line AND exits 0/nonzero consistently — because exit_gate_witness
(SCOUT-74) found 9/28 experiments exiting 0 under verdict-INVERTING mutation,
and trace_id (SCOUT-103/q35) found claims diverging from the actual event stream.
"verdict and exit code agree" is a MEASUREMENT over the run, not an assertion.

Run a command (list-form subprocess, never a shell), capture stdout + exit code,
extract the LAST `VERDICT:` line, and gate the convention:

  rc 0  CONSISTENT  — last VERDICT agrees with the exit code
  rc 1  MURMUR      — convention violated (named: GREEN-with-nonzero or
                      RED-with-zero = the murmur class), OR no VERDICT line
                      (silent exit), OR no verdict expected but one printed
  rc 2  FAIL-INPUT  — command not runnable, nonzero run exit without a parsed
                      verdict is MURMUR (named), but spawn failures / bad args
                      fail loud

Verdict vocabulary (extensible via --green/--red):
  GREEN words:  GREEN, PASS, KEEP, CLEAN, OK, ANCHORED, IDENTICAL, SAME,
                WITNESSED, STABLE, CONSISTENT, FLAT, GRACEFUL, PINNED, QUIET,
                CALIBRATED, INTACT, ADEQUATE, HIT, RESOLVED
  RED words:    RED, FAIL, KILL, DRIFT, DIVERGED, DEAD, MURMUR, PHANTOM,
                SYSTEMATIC, SCALING, BRITTLE, EXPIRES, EXO-FIRED, UNPINNED,
                TAMPERED, INADEQUATE, LEAKY, CONTAMINATED, VOID, MISSING,
                FINDINGS, DEGENERATE, NO-HIT, INDETERMINATE
Anything else books MURMUR (unknown verdict word — the vocabulary is the gate).

Worked example:
    python tools/vexit_check.py --cmd python3 --args=-c,print("VERDICT: GREEN")
    python tools/vexit_check.py --selftest

Selftest battery: green-consistent, red-consistent (nonzero exit), the two
murmur classes (GREEN+exit1, RED+exit0), silent-nonzero (no VERDICT line),
unknown verdict word, and spawn-failure fail-loud. Selftest pins are written
against a reference classifier so a bug in the classifier cannot hide behind
its own pin (reference implementation is 6 lines, kept intentionally dumb).

Stdlib-only. List-form subprocess only. Read-only on the target.
"""

import json
import subprocess
import sys
from pathlib import Path

GREEN_WORDS = {
    "GREEN", "PASS", "KEEP", "CLEAN", "OK", "ANCHORED", "IDENTICAL", "SAME",
    "WITNESSED", "STABLE", "CONSISTENT", "FLAT", "GRACEFUL", "PINNED", "QUIET",
    "CALIBRATED", "INTACT", "ADEQUATE", "HIT", "RESOLVED",
}
RED_WORDS = {
    "RED", "FAIL", "KILL", "DRIFT", "DIVERGED", "DEAD", "MURMUR", "PHANTOM",
    "SYSTEMATIC", "SCALING", "BRITTLE", "EXPIRES", "EXO-FIRED", "UNPINNED",
    "TAMPERED", "INADEQUATE", "LEAKY", "CONTAMINATED", "VOID", "MISSING",
    "FINDINGS", "DEGENERATE", "NO-HIT", "INDETERMINATE",
}

VERDICT_PREFIX = "VERDICT:"


def last_verdict_line(stdout: str):
    """Return the payload of the last VERDICT: line, or None."""
    found = None
    for line in stdout.splitlines():
        s = line.strip()
        if s.upper().startswith(VERDICT_PREFIX):
            found = s[len(VERDICT_PREFIX):].strip()
    return found


def classify(verdict_word, exit_code, green=None, red=None):
    """Reference-dumb classifier: (rc, family, why).

    rc 0 = CONSISTENT, 1 = MURMUR, 2 = FAIL-INPUT.
    """
    green = GREEN_WORDS if green is None else green
    red = RED_WORDS if red is None else red
    w = (verdict_word or "").strip().upper()
    if not w:
        return 2, "FAIL-INPUT", "no verdict word to classify"
    if w in green:
        if exit_code == 0:
            return 0, "CONSISTENT", f"{w} with exit 0"
        return 1, "MURMUR", f"GREEN verdict {w} but exited {exit_code} (murmur: success verdict, failing exit)"
    if w in red:
        if exit_code != 0:
            return 0, "CONSISTENT", f"{w} with exit {exit_code}"
        return 1, "MURMUR", f"RED verdict {w} but exited 0 (the SCOUT-74 murmur class: FAIL prints, exits clean)"
    return 1, "MURMUR", f"unknown verdict word {verdict_word!r} — vocabulary is the gate"


def run_check(cmd, args, timeout=120, green=None, red=None):
    """Run cmd+args (list-form, no shell), gate the convention. Returns receipt dict."""
    if not cmd:
        return {"rc": 2, "family": "FAIL-INPUT", "why": "empty --cmd"}
    full = [cmd] + list(args or [])
    try:
        proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {"rc": 2, "family": "FAIL-INPUT", "why": f"command not found: {cmd}"}
    except PermissionError:
        return {"rc": 2, "family": "FAIL-INPUT", "why": f"command not executable: {cmd}"}
    except subprocess.TimeoutExpired:
        return {"rc": 2, "family": "FAIL-INPUT", "why": f"timeout {timeout}s: {cmd}"}
    payload = last_verdict_line(proc.stdout)
    if payload is None:
        return {
            "rc": 1, "family": "MURMUR",
            "why": f"no {VERDICT_PREFIX} line on stdout (silent exit {proc.returncode}) — silent exit books MURMUR, never silent-clean",
            "cmd": full, "exit_code": proc.returncode,
            "stderr_tail": proc.stderr[-500:],
        }
    word = payload.split()[0] if payload.split() else ""
    rc, family, why = classify(word, proc.returncode, green=green, red=red)
    return {
        "rc": rc, "family": family, "why": why, "cmd": full,
        "exit_code": proc.returncode, "verdict_word": word,
        "verdict_line": payload[:200],
    }


# ---------------------------------------------------------------- selftest

def _ref_classify(word, exit_code):
    """Intentionally-dumb reference for the selftest (written twice = pin)."""
    g = word in {"GREEN", "PASS"}
    r = word in {"RED", "FAIL"}
    if not (g or r):
        return 1
    return 0 if ((g and exit_code == 0) or (r and exit_code != 0)) else 1


def selftest():
    fails = []
    import hashlib
    cases = [
        # (args-for-python -c, expected rc, expected family)
        ('print("VERDICT: GREEN")', 0, "CONSISTENT"),
        ('print("stuff"); print("VERDICT: PASS")', 0, "CONSISTENT"),
        ('print("VERDICT: RED"); raise SystemExit(1)', 0, "CONSISTENT"),
        ('print("VERDICT: FAIL"); raise SystemExit(3)', 0, "CONSISTENT"),
        # murmur class 1: success verdict, failing exit
        ('print("VERDICT: GREEN"); raise SystemExit(1)', 1, "MURMUR"),
        # murmur class 2 (SCOUT-74): FAIL verdict, exit 0
        ('print("VERDICT: FAIL")', 1, "MURMUR"),
        # silent exit: no VERDICT line at all
        ('raise SystemExit(1)', 1, "MURMUR"),
        ('print("hello")', 1, "MURMUR"),
        # unknown verdict word
        ('print("VERDICT: MAYBE")', 1, "MURMUR"),
    ]
    for code, exp_rc, exp_family in cases:
        r = run_check(sys.executable, ["-c", code])
        if r["rc"] != exp_rc or r["family"] != exp_family:
            fails.append(f"pin {code[:40]!r}: got rc={r['rc']}/{r['family']} want {exp_rc}/{exp_family} ({r['why']})")
        # cross-check the two murmur/consistent verdict cases against the
        # dumb reference so the classifier cannot drift from its own pin
        if "verdict_word" in r:
            word = r["verdict_word"]
            if word in {"GREEN", "PASS", "RED", "FAIL"}:
                want = _ref_classify(word, r["exit_code"])
                got = 0 if r["family"] == "CONSISTENT" else 1
                if got != want:
                    fails.append(f"classifier/reference drift on {word}@exit{r['exit_code']}: {got} vs {want}")
    # fail-loud pins
    r = run_check("definitely-not-a-real-binary-xyz", [])
    if r["rc"] != 2 or r["family"] != "FAIL-INPUT":
        fails.append(f"spawn-failure should fail loud, got {r}")
    r = run_check("", [])
    if r["rc"] != 2 or r["family"] != "FAIL-INPUT":
        fails.append(f"empty cmd should fail loud, got {r}")
    return fails


def main(argv):
    if "--selftest" in argv:
        fails = selftest()
        print(f"vexit selftest: {9 + 2} pins, {len(fails)} failures")
        for f in fails:
            print("FAIL:", f)
        if fails:
            print("VERDICT: RED")
            return 1
        print("VERDICT: GREEN")
        return 0

    cmd, args, out_path, timeout = None, [], None, 120
    i = 0
    while i < len(argv):
        a = argv[i]
        if "=" in a and a.startswith("--") and a.split("=", 1)[0] in {"--cmd", "--args", "--out", "--timeout"}:
            argv = argv[:i] + [a.split("=", 1)[0], a.split("=", 1)[1]] + argv[i + 1:]
            a = argv[i]
        if a == "--cmd":
            cmd = argv[i + 1]; i += 2
        elif a == "--args":
            args = [x for x in argv[i + 1].split(",") if x != ""]; i += 2
        elif a == "--out":
            out_path = argv[i + 1]; i += 2
        elif a == "--timeout":
            timeout = int(argv[i + 1]); i += 2
        else:
            print(f"unknown arg {a!r} (see --help via module docstring)", file=sys.stderr)
            return 2
    if cmd is None:
        print(__doc__)
        print("usage: python tools/vexit_check.py --cmd CMD [--args=a,b] [--out r.json] | --selftest")
        return 2

    receipt = run_check(cmd, args, timeout=timeout)
    receipt["tool"] = "vexit_check"
    receipt["convention"] = "VEXIT-1: last VERDICT: line on stdout must agree with exit code"
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(receipt, indent=2) + "\n")
        tmp.replace(p)
        receipt["receipt"] = str(p)
    print(json.dumps({k: receipt[k] for k in ("rc", "family", "why") if k in receipt}))
    if "receipt" in receipt:
        print(f"receipt: {receipt['receipt']}")
    print(f"VERDICT: {'GREEN' if receipt['rc'] == 0 else 'RED'}")
    return receipt["rc"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
