#!/usr/bin/env bash
# Tier A deep-dive: per-repo root listing, workflows, recent commit subjects.
# Usage: deepdive.sh <tierfile> <with_commits:0|1>
set -u
TIER="$1"; WC="$2"
APIROOT="$(cd "$(dirname "$0")" && pwd)/_api"
mkdir -p "$APIROOT"
one() {
  local r="$1" wc="$2" out="$APIROOT/$1"
  [ -s "$out.root.json" ] || gh api "repos/SuperInstance/$r/contents" -q '[.[] | {n:.name,t:.type,s:.size}]' > "$out.root.json" 2>"$out.err" || echo "ROOTFAIL $r" 
  [ -s "$out.wf.json" ] || gh api "repos/SuperInstance/$r/contents/.github/workflows" -q '[.[] | select(.type=="file") | .name]' > "$out.wf.json" 2>>"$out.err" || echo "[]" > "$out.wf.json"
  if [ "$wc" = "1" ] && [ ! -s "$out.commits.json" ]; then
    gh api "repos/SuperInstance/$r/commits?per_page=10" -q '[.[] | {sha:.sha[0:7], msg:(.commit.message | split("\n")[0])}]' > "$out.commits.json" 2>>"$out.err" || echo "[]" > "$out.commits.json"
  fi
}
export -f one; export APIROOT
cat "$TIER" | xargs -d '\n' -P 3 -I{} bash -c 'one "$1" "$2"' _ {} "$WC"
echo "DEEPDIVE_DONE $TIER"
