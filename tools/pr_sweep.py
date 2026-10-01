#!/usr/bin/env python3
"""pr_sweep — org-wide open-PR triage for the SuperInstance fleet.

READ-ONLY: inventories open PRs across all org repos, pulls CI status, and
emits a triage report with suggested actions. It NEVER merges, closes,
comments, or approves — triage reports; Lucineer-with-hands acts afterward
(per docs/PR-TRIAGE-QUEUE.md: read the diff, extract a learning, then resolve).

Usage:
  pr_sweep.py [--org SuperInstance] [--out FILE] [--repo-limit 300]

Requires: gh CLI authenticated. Subprocess list-form ONLY (fleet red line:
no shell=True). Light sleeps between repos; gh owns auth/rate limits.

Triage rules (mechanical, reported — not acted on):
  PENDING         any check still running/queued         -> wait, do not merge
  FAST-FAIL       failed checks, total failed runtime <90s -> suspect workflow/
                  config break; diff .github/workflows vs last green commit,
                  fix forward in ONE commit. (15-50s failures = parse/secret/
                  action-version break, not the bumped code.)
  CONFLICTS       mergeable == CONFLICTING, checks green   -> rebase plan
  MERGE-CANDIDATE all checks green, no conflicts           -> still requires the
                  diff read + learning line before merge (queue doc rules)
  OTHER           mixed/partial states                     -> look at the logs
Dependabot rows get a batch hint: patch/minor green -> batch-merge; majors
get a breaking-change scan first.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

FAILED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
OK_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED", "SUCCESSFUL"}
ACTIVE_STATES = {"PENDING", "IN_PROGRESS", "QUEUED", "REQUESTED", "WAITING"}


def gh_json(args, default=None):
    """Run gh with list-form args; return (parsed, error_or_None)."""
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if r.returncode != 0:
        return default, r.stderr.strip()[:300]
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as e:
        return default, f"json decode: {e}"


def check_runtime_s(entry):
    """Best-effort runtime seconds for a CheckRun-style rollup entry."""
    try:
        from datetime import datetime as dt
        s = entry.get("startedAt")
        c = entry.get("completedAt")
        if not s or not c:
            return None
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        return (dt.strptime(c, fmt) - dt.strptime(s, fmt)).total_seconds()
    except Exception:
        return None


def classify(rollup):
    """Return (bucket, note) from a statusCheckRollup list."""
    if not rollup:
        return "OTHER", "no checks configured — manual look required"
    states, conclusions, failed_rt = [], [], 0.0
    for e in rollup:
        st = e.get("status")
        if st in ACTIVE_STATES:
            return "PENDING", f"check '{e.get('name', '?')}' still {st}"
        cc = e.get("conclusion") or e.get("state") or "UNKNOWN"
        conclusions.append(cc)
        if cc in FAILED_CONCLUSIONS:
            rt = check_runtime_s(e)
            failed_rt += rt if rt is not None else 0.0
    if any(c in FAILED_CONCLUSIONS for c in conclusions):
        if failed_rt and failed_rt < 90:
            return "FAST-FAIL", f"failed checks total {failed_rt:.0f}s — config-break suspect"
        return "OTHER", f"failed checks (runtime {failed_rt:.0f}s or unknown) — read logs"
    if all(c in OK_CONCLUSIONS for c in conclusions):
        return "GREEN", "all checks concluded OK"
    return "OTHER", f"mixed conclusions: {sorted(set(conclusions))}"


def failed_runs_hint(repo, branch):
    runs, _ = gh_json(["run", "list", "--repo", repo, "--branch", branch,
                       "--status", "failure", "--limit", "3",
                       "--json", "databaseId,workflowName"])
    if not runs:
        return ""
    hints = ", ".join(f"'{r.get('workflowName')}' run {r.get('databaseId')}"
                      for r in runs[:3])
    example = runs[0].get("databaseId")
    return f" failed runs on branch: {hints}. Diagnose: gh run view {example} --repo {repo} --log-failed"


def main():
    ap = argparse.ArgumentParser(description="org-wide open-PR triage (read-only)")
    ap.add_argument("--org", default="SuperInstance")
    ap.add_argument("--out", default=None, help="also write markdown report here")
    ap.add_argument("--repo-limit", type=int, default=300)
    args = ap.parse_args()

    repos, err = gh_json(["repo", "list", args.org, "--json", "name",
                          "-L", str(args.repo_limit)])
    if repos is None:
        print(f"FAIL: cannot list repos for org {args.org}: {err}", file=sys.stderr)
        sys.exit(1)
    names = [r["name"] for r in repos]

    rows = {k: [] for k in ("FAST-FAIL", "PENDING", "CONFLICTS", "GREEN",
                            "OTHER", "REPO-ERROR")}
    for name in names:
        repo = f"{args.org}/{name}"
        time.sleep(0.2)
        prs, err = gh_json(["pr", "list", "--repo", repo, "--state", "open",
                            "--json", "number,title,author,headRefName,"
                                      "baseRefName,mergeable,updatedAt,url",
                            "--limit", "50"])
        if prs is None:
            rows["REPO-ERROR"].append(f"- {repo}: gh error: {err}")
            continue
        for pr in prs:
            who = (pr.get("author") or {}).get("login", "?")
            head = pr.get("headRefName", "?")
            view, verr = gh_json(["pr", "view", str(pr["number"]), "--repo", repo,
                                  "--json", "statusCheckRollup"])
            rollup = (view or {}).get("statusCheckRollup") if not verr else None
            if rollup is None:
                bucket, note = "OTHER", f"rollup unavailable: {verr}"
            else:
                bucket, note = classify(rollup)
            label = f"{repo}#{pr['number']} — {pr['title']} ({who}, `{head}`→{pr.get('baseRefName')})"
            if bucket == "FAST-FAIL":
                note += failed_runs_hint(repo, head)
            if who == "dependabot[bot]":
                note += " [dependabot: patch/minor green => batch-merge; majors need breaking-change scan]"
            if pr.get("mergeable") == "CONFLICTING" and bucket == "GREEN":
                bucket = "CONFLICTS"
                note = "mergeable CONFLICTING — rebase plan needed"
            rows[bucket].append(f"- {label} — {note}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    order = ["FAST-FAIL", "PENDING", "CONFLICTS", "GREEN", "OTHER", "REPO-ERROR"]
    lines = [f"# pr_sweep report — {args.org} — {now}", ""]
    total = 0
    for k in order:
        body = rows[k]
        total += len(body)
        lines.append(f"## {k} ({len(body)})")
        if body:
            lines.append("```")
            lines.extend(body)
            lines.append("```")
        else:
            lines.append("(none)")
        lines.append("")
    lines.append(f"Total open PRs: {total}. GREEN rows are MERGE-CANDIDATES — "
                 "diff read + learning line required first (docs/PR-TRIAGE-QUEUE.md).")
    report = "\n".join(lines)
    print(report)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(report + "\n")


if __name__ == "__main__":
    main()
