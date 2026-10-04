#!/usr/bin/env bash
# Wave 1: raw-fetch fixed candidate paths for every SuperInstance repo.
# Usage: fetch_wave1.sh <fetchlist.tsv>   (lines: repo<TAB>branch<TAB>path)
# Saves hits under _raw/<repo>/<path-with-__-for-slashes>, prints status per line.
set -u
LIST="$1"
OUTROOT="$(cd "$(dirname "$0")" && pwd)/_raw"
fetch_one() {
  local repo="$1" branch="$2" path="$3"
  local out="$OUTROOT/$repo/$(echo "$path" | tr '/' '__')"
  mkdir -p "$OUTROOT/$repo"
  local code
  code=$(curl -sL --max-filesize 262144 --max-time 20 -o "$out" -w '%{http_code}' \
    "https://raw.githubusercontent.com/SuperInstance/$repo/$branch/$path" 2>/dev/null) || code="ERR"
  if [ "$code" = "200" ] && [ -s "$out" ]; then
    # sanity: skip files that look binary (null byte in first 2KB)
    if od -An -tx1 -N2048 "$out" 2>/dev/null | grep -qw 00; then rm -f "$out"; echo "BIN $repo $path"; return; fi
    echo "OK $repo $path"
  else
    rm -f "$out"; echo "MISS $repo $path $code"
  fi
}
export -f fetch_one
export OUTROOT
# emit jobs
awk -F'\t' '{print $1"\t"$2"\t"$3}' "$LIST" | \
xargs -d '\n' -P 12 -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r r b p <<< "{}"; fetch_one "$r" "$b" "$p"'
