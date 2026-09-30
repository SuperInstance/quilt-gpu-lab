#!/usr/bin/env bash
# codespace_lane.sh — fire an ephemeral Codespace lane, run a job, PUT IT AWAY.
#
# Usage:  ./codespace_lane.sh <owner/repo> "<command>"
#   e.g.  ./codespace_lane.sh SuperInstance/quilt-canvas "uname -a && nproc && df -h /"
#
# Why this exists: see docs/codespace-lanes.md. The economics decide the design —
# storage is billed while a codespace EXISTS (not while it runs), and the default
# machine's 32 GB is larger than the whole free 15 GB-month allowance. So the
# delete is not cleanup, it is the point. The EXIT trap deletes on every path,
# including failure and Ctrl-C.
#
# Token: reads GH_TOKEN from $GITHUB_TOKEN_FILE (default ~/.config/fleet/github-token,
# created from the fleet key file; 600). Needs the `codespace` scope.
set -euo pipefail

REPO="${1:?usage: codespace_lane.sh <owner/repo> \"<command>\"}"
shift
CMD="${*:?usage: codespace_lane.sh <owner/repo> \"<command>\"}"

TOKEN_FILE="${GITHUB_TOKEN_FILE:-$HOME/.config/fleet/github-token}"
[ -r "$TOKEN_FILE" ] || { echo "[lane] FATAL: no token file at $TOKEN_FILE" >&2; exit 2; }
# NOTE: `read < file` returns non-zero at EOF when the file has no trailing
# newline, and under `set -e` that is a SILENT death (bit us 2026-09-29: empty
# log, no process, no error). Hence the `|| true` plus an explicit guard.
read -r GH_TOKEN < "$TOKEN_FILE" || true
[ -n "${GH_TOKEN:-}" ] || { echo "[lane] FATAL: token file $TOKEN_FILE is empty" >&2; exit 2; }
export GH_TOKEN

MACHINE="${MACHINE:-basicLinux32gb}"
IDLE="${IDLE_TIMEOUT:-5m}"          # task machine stops itself quickly
RETENTION="${RETENTION_PERIOD:-1h}" # ...and expires for real if we die mid-job
DISPLAY="lane-$(date +%Y%m%d-%H%M%S)"
NAME=""

DELETED=0
cleanup() {
  local rc=$?
  if [ -n "$NAME" ] && [ "$DELETED" = "0" ]; then
    DELETED=1
    echo "[lane] putting it away: gh codespace delete -c $NAME --force"
    if gh codespace delete -c "$NAME" --force >/dev/null 2>&1; then
      echo "[lane] deleted — storage quota released"
    else
      echo "[lane] WARN: delete failed — SWEEP REQUIRED: gh codespace delete -c $NAME --force" >&2
    fi
  fi
  exit $rc
}
trap cleanup EXIT INT TERM

echo "[lane] repo=$REPO machine=$MACHINE idle=$IDLE retention=$RETENTION display=$DISPLAY"
gh codespace create -R "$REPO" -m "$MACHINE" --idle-timeout "$IDLE" \
   --retention-period "$RETENTION" --display-name "$DISPLAY" >/dev/null 2>&1 || {
     echo "[lane] FATAL: create failed" >&2; exit 3; }

# resolve the generated name from our display name (the API names codespaces itself)
NAME="$(gh codespace list --json name,displayName \
        -q "[.[] | select(.displayName==\"$DISPLAY\")] | last | .name")"
[ -n "$NAME" ] && [ "$NAME" != "null" ] || { echo "[lane] FATAL: could not resolve name" >&2; exit 4; }
echo "[lane] name=$NAME"

# wait for Available (cold start is minutes; a prebuild would make this the pinch)
state=""
for _ in $(seq 1 40); do
  # jq-free state check: gh's -q output was empty for us, leaving the wait loop
  # spinning until an outer timeout killed the run (2026-09-29).
  state="$(gh codespace list --json name,state 2>/dev/null | python3 -c 'import json,sys; n=sys.argv[1]; print(next((c["state"] for c in json.load(sys.stdin) if c["name"]==n), ""))' "$NAME" 2>/dev/null || true)"
  [ "$state" = "Available" ] && break
  sleep 10
done
echo "[lane] state=$state"
[ "$state" = "Available" ] || { echo "[lane] FATAL: never became Available" >&2; exit 5; }

echo "[lane] exec: $CMD"
set +e
gh codespace ssh -c "$NAME" -- bash -lc "$CMD" 2>&1 | tail -25
rc=${PIPESTATUS[0]}
set -e
echo "[lane] job rc=$rc"
exit $rc
