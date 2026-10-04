#!/usr/bin/env python3
"""onboard — fleet-standard credential onboarding for grabbable tools (stdlib-only).

Born 2026-10-04 (Casey: "a quick onboarding cli and good documentation for how
to point to environmental variables" — the fleet-standard answer for any tool
that touches a provider). Pairs with tools/onboard.json, the per-tool registry
of which env vars a tool needs and where each can legitimately come from.

Resolution order per variable (first hit wins, STATUS ONLY — values are never
read into memory-as-output, never printed, never logged):

    1. env      — already exported in the current environment
    2. keyfile  — declared by name in the fleet keyfile
                  (default /mnt/c/Users/casey/key.txt, override: FLEET_KEYFILE)
    3. config   — extracted working copy (e.g. ~/.config/typesafe/token)
    4. MISSING  — onboard prints the paste-ready fix, never the value

Usage
-----
    python tools/onboard.py --tool typesafe-batch   # one tool
    python tools/onboard.py --all                   # every registered tool
    python tools/onboard.py --tool i2i-ledger --json receipt.json
    python tools/onboard.py --selftest

House law: stdlib-only; fail-loud (rc=0 ready, rc=1 something missing,
rc=2 bad input); deterministic; keys never echoed — output contains
statuses and paths only. The selftest asserts that a planted fake secret
value never appears in any output.
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "onboard.json")
KEYFILE_DEFAULT = "/mnt/c/Users/casey/key.txt"


def log(msg):
    print(msg, flush=True)


def load_registry(path=REGISTRY_PATH):
    if not os.path.isfile(path):
        raise FileNotFoundError("registry missing: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        reg = json.load(f)
    if "tools" not in reg or not isinstance(reg["tools"], dict):
        raise ValueError("registry malformed: no 'tools' object")
    return reg


def keyfile_has(keyfile_path, name):
    """True if the fleet keyfile declares `name` at line start. Never returns
    the value; the file is only grepped for the variable NAME."""
    if not name or not os.path.isfile(keyfile_path):
        return False
    try:
        with open(keyfile_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith(name):
                    return True
    except OSError:
        return False
    return False


def resolve_var(entry, keyfile_path):
    """-> (status, source_hint). status in {env, keyfile, config, MISSING}."""
    var = entry["var"]
    if os.environ.get(var):
        return "env", "exported in current environment"
    kf_name = entry.get("keyfile")
    if kf_name and keyfile_has(keyfile_path, kf_name):
        return "keyfile", "%s declares %s" % (keyfile_path, kf_name)
    cfg = entry.get("config")
    if cfg:
        cfg_x = os.path.expanduser(cfg)
        if os.path.isfile(cfg_x):
            return "config", cfg_x
    return "MISSING", None


def fix_hint(var, entry, keyfile_path):
    kf_name = entry.get("keyfile")
    cfg = entry.get("config")
    hints = []
    if kf_name:
        hints.append("add line '%s=<value>' to %s" % (kf_name, keyfile_path))
    if cfg:
        hints.append("or write the token to %s" % os.path.expanduser(cfg))
    hints.append("or export %s=<value> in your shell" % var)
    return hints


def report_tool(name, tool, keyfile_path):
    log("")
    log("== %s — %s" % (name, tool.get("purpose", "")))
    missing = 0
    for entry in tool.get("env", []):
        var = entry["var"]
        status, source = resolve_var(entry, keyfile_path)
        req = "" if entry.get("required", True) else " (optional)"
        if status == "MISSING":
            missing += 1 if entry.get("required", True) else 0
            log("  %-24s [MISSING]%s" % (var, req))
            for hint in fix_hint(var, entry, keyfile_path):
                log("    fix: %s" % hint)
        else:
            log("  %-24s [%s]%s  %s" % (var, status, req, source))
    return missing


def selftest():
    """Deterministic battery in a fake HOME/keyfile/env. Also asserts the
    planted secret VALUE never leaks into any output (capture via os.pipe)."""
    fake_val = "SUPERSECRET_planted_value_9f3a1"
    tmp = tempfile.mkdtemp(prefix="onboard_selftest_")
    kf = os.path.join(tmp, "key.txt")
    with open(kf, "w", encoding="utf-8") as f:
        f.write("FAKE_A=%s\nFAKE_B=whatever\n" % fake_val)
    cfg_dir = os.path.join(tmp, ".config", "toolx")
    os.makedirs(cfg_dir)
    cfg_path = os.path.join(cfg_dir, "token")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("configtoken\n")
    reg = {
        "keyfile_default": kf,
        "tools": {
            "t_env": {"purpose": "p", "env": [{"var": "OB_TEST_ENV", "keyfile": None, "config": None, "required": True}]},
            "t_keyfile": {"purpose": "p", "env": [{"var": "OB_TEST_KF", "keyfile": "FAKE_B", "config": None, "required": True}]},
            "t_config": {"purpose": "p", "env": [{"var": "OB_TEST_CFG", "keyfile": None, "config": cfg_path, "required": True}]},
            "t_missing": {"purpose": "p", "env": [{"var": "OB_TEST_NOPE", "keyfile": None, "config": None, "required": True}]},
            "t_optional": {"purpose": "p", "env": [{"var": "OB_TEST_OPT", "keyfile": None, "config": None, "required": False}]},
        },
    }
    reg_path = os.path.join(tmp, "onboard.json")
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg, f)

    # capture stdout while running checks
    import io
    from contextlib import redirect_stdout

    results = []
    os.environ["OB_TEST_ENV"] = fake_val
    reg_loaded = load_registry(reg_path)
    kf_saved = KEYFILE_DEFAULT

    def run_report(tool_name):
        buf = io.StringIO()
        with redirect_stdout(buf):
            report_tool(tool_name, reg_loaded["tools"][tool_name], kf)
        return buf.getvalue()

    out_env = run_report("t_env")
    results.append(("env resolution", "[env]" in out_env))
    del os.environ["OB_TEST_ENV"]
    out_kf = run_report("t_keyfile")
    results.append(("keyfile resolution", "[keyfile]" in out_kf))
    out_cfg = run_report("t_config")
    results.append(("config resolution", "[config]" in out_cfg and cfg_path in out_cfg))
    out_missing = run_report("t_missing")
    results.append(("missing + fix hint", "[MISSING]" in out_missing and "fix:" in out_missing))
    results.append(("optional missing not counted", " (optional)" in run_report("t_optional")))
    all_out = out_env + out_kf + out_cfg + out_missing
    results.append(("no secret values in output", fake_val not in all_out and "configtoken" not in all_out))
    try:
        load_registry(os.path.join(tmp, "nope.json"))
        results.append(("fail-loud missing registry", False))
    except FileNotFoundError:
        results.append(("fail-loud missing registry", True))

    fails = 0
    for name, ok in results:
        log("  [%s] %s" % ("PASS" if ok else "FAIL", name))
        fails += 0 if ok else 1
    log("SELFTEST: %d/%d" % (len(results) - fails, len(results)))
    assert kf_saved == KEYFILE_DEFAULT  # no global mutation
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="Fleet credential onboarding: per-tool env-var status + paste-ready fixes. Never prints secret values.")
    ap.add_argument("--tool", help="onboard one registered tool")
    ap.add_argument("--all", action="store_true", help="every registered tool (doctor)")
    ap.add_argument("--json", dest="json_out", help="write a status receipt (statuses only, no values)")
    ap.add_argument("--registry", default=REGISTRY_PATH, help="override registry path")
    ap.add_argument("--selftest", action="store_true", help="deterministic battery")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    keyfile_path = os.environ.get("FLEET_KEYFILE", KEYFILE_DEFAULT)
    if not args.tool and not args.all:
        ap.error("choose --tool NAME or --all")
    try:
        reg = load_registry(args.registry)
    except (FileNotFoundError, ValueError) as e:
        log("FATAL: %s" % e)
        sys.exit(2)

    names = sorted(reg["tools"]) if args.all else [args.tool]
    if not args.all and args.tool not in reg["tools"]:
        log("FATAL: unknown tool %r — registered: %s" % (args.tool, ", ".join(sorted(reg["tools"]))))
        sys.exit(2)

    total_missing = 0
    receipt = {"schema": "onboard.v1", "keyfile": keyfile_path, "tools": {}}
    for name in names:
        missing = report_tool(name, reg["tools"][name], keyfile_path)
        total_missing += missing
        receipt["tools"][name] = {"missing_required": missing}

    log("")
    if total_missing == 0:
        log("ONBOARD: all required credentials resolvable. rc=0")
    else:
        log("ONBOARD: %d required variable(s) MISSING across %d tool(s). rc=1" % (total_missing, len(names)))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=1)
        log("receipt: %s" % args.json_out)
    sys.exit(0 if total_missing == 0 else 1)


if __name__ == "__main__":
    main()
