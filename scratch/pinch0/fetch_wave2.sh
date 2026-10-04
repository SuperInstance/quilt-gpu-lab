#!/usr/bin/env bash
# Wave 2 (gentle resume): fetch remaining repos after CDN 429 backoff.
# Usage: fetch_wave2.sh <fetchlist.tsv>   (lines: repo<TAB>branch<TAB>path)
set -u
LIST="$1"
OUTROOT="$(cd "$(dirname "$0")" && pwd)/_raw"
fetch_one() {
  local repo="$1" branch="$2" path="$3"
  # skip repos we already have something for
  if compgen -G "$OUTROOT/$repo/*" > /dev/null; then echo "SKIP $repo"; return; fi
  local out="$OUTROOT/$repo/$(echo "$path" | tr '/' '__')"
  mkdir -p "$OUTROOT/$repo"
  local code
  code=$(curl -sL --max-filesize 262144 --max-time 20 -o "$out" -w '%{http_code}' \
    "https://raw.githubusercontent.com/SuperInstance/$repo/$branch/$path" 2>/dev/null) || code="ERR"
  if [ "$code" = "429" ]; then sleep 30;
    code=$(curl -sL --max-filesize 262144 --max-time 20 -o "$out" -w '%{http_code}' \
      "https://raw.githubusercontent.com/SuperInstance/$repo/$branch/$path" 2>/dev/null) || code="ERR"
  fi
  if [ "$code" = "200" ] && [ -s "$out" ]; then
    if od -An -tx1 -N2048 "$out" 2>/dev/null | grep -qw 00; then rm -f "$out"; echo "BIN $repo $path"; return; fi
    echo "OK $repo $path"
  else
    rm -f "$out"; echo "MISS $repo $path $code"
  fi
  sleep 0.6
}
export -f fetch_one
export OUTROOT
awk -F'\t' '{print $1"\t"$2"\t"$3}' "$LIST" | \
xargs -d '\n' -P 4 -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r r b p <<< "{}"; fetch_one "$r" "$b" "$p"'
