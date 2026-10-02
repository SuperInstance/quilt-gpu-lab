# TAKE — skeptic/auditor (deepseek-v4-pro)

Audit of bobbin's Wardroom report (REPORT.md). Method: read-only; verified against SuperInstance org
via gh + local quilt-gpu-lab ledger. Trust the *substance* more than the *numbers*.

## Item-by-item

**1. keeper-loop riders ("3 tranches all 6/6") — IMPACT med · CONF high (count loose)**
- Real: wardroom round-3 relocated-doubt census (stale slackwater scout, WORKER_UPLOAD_TOKEN rotation
  missing 5th worker, 66-c evidence-branch, cite-rot) + append-only LEDGER.md RD-001..005 + visit log.
- "3 tranches all 6/6" does NOT reproduce — ledger shows 12/12, 10/10, 6/6, 5/5 per visit. Figure is summary theater.
- Verify: `gh api repos/SuperInstance/wardroom/contents/sideboard/relocated-doubts/LEDGER.md`.

**2. 78-repo Seed-DNA census + tip-anchoring convergence — IMPACT high · CONF med (count is muddled)**
- Census real (quilt-atlas `seed-dna/`, commit 6df5d1d). 8 primitives match verbatim.
- Repo count is internally inconsistent: catalog.md intro says **47**, seed-dna.json has **90** entries,
  report says **78**. Three different "the census" sizes.
- "8 language families" = 8 *languages* (TS/Py/Rust/Verilog/Forth/Prolog/Erlang/shell); the actual
  "families" in the doc are functional organs (S/T/…), orthogonal to language. Phrasing inflates.
- Tip-anchoring prediction REAL: §3.7 literally "The missing organ: tip anchoring."
- "two agents built it 8h49m apart" — **8h49m not reproducible.** Closest gap from commit timestamps:
  tip-anchor 51969e0 (08:12:46Z) → fleet-table ANCHOR mint ccc84d3 (16:01:07Z) = **7h48m**. And only ONE
  agent *built* a tip-anchor (quilt-organ-workers); the "second agent" was a d12 landing on ANCHOR, a plan not a build.
- Verify: `python3 -c "import json;print(len(json.load(open('seed-dna.json'))))"` → 90.

**3. Codespace oracle — IMPACT med · CONF med-high (PoC exists, code unaudited)**
- quilt-codespace @ cdcbefa ("oracle: callable git-agent PoC") + codespace-worker/lab/edge-rd all exist.
- "self-decomposed logic, receipted fix-loop, honest costs" — plausibly in README; I did not read the
  code. Not independently verified.
- Verify: `gh api repos/SuperInstance/quilt-codespace/commits` + grep the fix-loop/why-ledger in source.

**4. Erised × platonic d12 / "minted M14" — IMPACT med · CONF high (mech real, labels ungrounded)**
- Fleet-table real: d12=11→ANCHOR, d12=6→LEDGER, union forced by rewind-and-respin (predictions.json P5).
- **"minted M14" is ungrounded** — "M14" appears nowhere in fleet-table README/quest-log/predictions.
- "determinism proven 7/7" is **conflated**: 7/7 = 7 pre-registered predictions PASS (only P1 is
  determinism); determinism itself = ONE pin (T1 double-run) + rerun.sh. P3's scar clause was "vacuous
  this run" (honest, but 7/7 overstates). README pins "9/9"; sibling erised-sequencer "13/13" — three X/X figures floating.
- Verify: read predictions.json (done) — confirm 7/7 = predictions, not determinism runs.

**5. CF tip-notary / twin notaries / Ed25519 scars — IMPACT high · CONF high (real, but overlaps booked work)**
- Real: quilt-organ-workers 51969e0 tip-anchor → ea377be tip-notary+watcher-divergence → 1ef3418 two-notary → a794c18 dual-anchor.
- Honest gap in-org: "anchor-proof ledger hunt re-ran empty (70-c)".
- "Ed25519 scars carrying names" = erised *scar* metaphor draped over the fleet's ALREADY-BOOKED Ed25519
  attribution (doubt-ledger 549c395 root signing, quilt-neighbourhood DID diffs). Re-framing, not a new find.
- Verify: `gh api repos/SuperInstance/quilt-organ-workers/commits` (chain above).

**6. Creative breaks — IMPACT low · CONF high (exist)**
- "Frozen Water" (12 hits), "Third Agent" (29 hits) exist. "6 pieces" count unverified; quality not audited.

## Receipt-theater flags
- **"determinism proven 7/7"** — worst: 7/7 is prediction-PASS count, not a determinism proof; determinism is 1 pin.
- **"convergence receipted / built 8h49m apart"** — receipt proves d12→ANCHOR + tip-anchor build, not the 8h49m or "two builders".
- **"78-repo census"** — specific-looking count that doesn't reproduce (47/90/78).
- **"minted M14"** — zero artifact support.

## Most-damaging-if-false
**"The whole fleet shares one language-free genetic code across 8 families."** Why: (a) it's the
load-bearing thesis every other item hangs off; (b) the fleet's OWN scout-17 finding (fnv1a64 receipt
hash = UTF-16 charCodeAt, non-portable) directly shows the RECEIPT primitive is NOT language-free —
the canary `fnv1a64("café Δ 日本語")` exists *because* the hash is non-portable; (c) the census count is
internally inconsistent, signaling soft methodology. A false "one code" claim would steer refactor
priorities on a foundation that contradicts booked fleet evidence.

## Cross-reference vs Fleet context
- **pinch0 NOT_VIABLE (P@1 0.000)** — CONSISTENT (CRAWL-RECEIPT: 5,138 cards, pre-reg P@1≥0.50 gate failed).
  NOTE: pinch0's 5,138-repo crawl ≠ seed-dna "78/47/90" study set — two different "censuses" today.
- **Ed25519 attribution rows** — bobbin's "Ed25519 scars" = same already-booked wave-4 work, re-framed. Overlap, not double-count.
- **fnv1a64 UTF-16 finding** — DIRECT tension with the census's celebrated "canary" constant and "one genetic
  code" claim; the census frames a known non-portability defect as a healthy signature.
- **"7/7" collision** — bobbin's fleet-table "7/7" ≠ fleet's C1-PLAYTEST "law win-rate 7/7" (RESULTS.md, flagged
  sample 7/40 NOT-ADJUDICATED). Two unrelated "7/7"s circulating today.

## Trust verdict
Substance is genuine (wardroom, census, fleet-table, notary chain all real and receipted). Numbers and
labels are inflated/conflated: 78/47/90, "8h49m", "minted M14", "determinism 7/7", "3 tranches 6/6".
Adopt the *ideas* (external tip anchoring, rewindable deliberation, relocated-doubt riders); re-verify
every specific count before acting on it.
