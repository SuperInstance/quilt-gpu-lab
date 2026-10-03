# VSB-1 — vendor-stripped blob-bytes census tool (pre-registered 2026-10-03 ~15:2x UTC)

Spawned by SCOUT-31 (canons "size-is-a-lie": repo `size` field broken fleet-wide).
Reference method: quilt-research-canons `research/scout/SCOUT-2026-09-30T1955Z.md` — git
tree blob bytes, with vendored trees excluded: `node_modules|target|vendor|dist|build|
.next|out|_build|__pycache__|.wrangler|coverage`.

## Deliverable
`tools/vendor_strip_census.py` — for a git repo (default: this one):
- Raw census: `git ls-tree -r -l HEAD` → per-path blob sizes; ranking + totals.
- Stripped census: same tree, vendor dirs excluded from ranking and counts.
- Output JSON to `results/vsb1/vendor_strip_census.json` (byte rankings, totals,
  vendored share).

## Pre-registered gates (frozen before fire)
- G1 (two-method agreement): blob bytes computed via `git ls-tree -r -l` MUST equal
  bytes computed independently via `git cat-file --batch-check` on `ls-tree -r
  --name-only`, per file and in total (exact integer equality — both come from the
  same object store; any delta = a real bug, fail loud).
- G2 (strip delta honesty): report vendored byte share; tool must NOT silently apply
  stripping to the raw total — both numbers always emitted.
- G3 (no-tree refuse): empty tree or non-repo path → exit 2 with message.
- G4 (test): pytest pinning (a) two-method equality on a tiny synthetic tree via
  tmp git repo, (b) vendor dir exclusion, (c) empty-repo refusal.

## Verdict rule
PASS iff G1-G4 hold on this repo; the census itself is descriptive (no fitness claim).
