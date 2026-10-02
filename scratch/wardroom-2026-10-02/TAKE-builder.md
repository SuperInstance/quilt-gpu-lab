# TAKE-builder — Wardroom digest, builder/engineer alignment

glm-5.3-flash · 2026-10-02 · READ-ONLY on repos; write-scope = this file.
Lens: smallest falsifiable slice, this week, our box (flaky WSL2 GPU — nothing below
needs local GPU; the only embeddings pass runs CF-side where the pinch0 index lives).

## The six areas — slice / cost / deps / rank

1. **Keeper-loop riders (stale-scout, token rotation)** — rank 2
   Slice: heartbeat rider that (a) flags scouts whose last receiptd `by-lane` entry is
   >N h old, (b) preflights token expiry before a lane launches; fail-loud to stderr.
   Cost: 1 lane × 1–2 h, CPU. Deps: receiptd live (✓). Kill: 48 h dry-run flags zero
   stale scouts AND rotation already automated → dead.

2. **Seed-DNA census (78 repos, 9-token vocabulary)** — rank 4
   Slice: run the vocabulary pass over OUR repos (rg, CPU) → per-repo DNA matrix receipt.
   Cost: 1 lane × 2–3 h. Deps: repo list; pinch0 index for the semantic pass (free, CF).
   Kill: our match rate <~half the vocabulary → "one genetic code" doesn't transfer.

3. **Codespace oracle (self-decomposed fix-loop, two-git-agents)** — rank 5
   Slice: consume, don't build — run ONE oracle job on bobbin's existing quilt-codespace
   PoC against a real small bug in our repos; receipt the loop locally.
   Cost: 1 lane × 1 h (it exists). Deps: codespace access. Kill: honest-costs receipt
   shows per-run cost > value for single-box loops → pattern-only adoption.

4. **Erised rewindable dice (forced tie-break, determinism 7/7)** — rank 3
   Slice: stdlib `dice.py` — seeded PRNG with save/restore state; every roll receipts
   {seed, state-hash, outcome} into receiptd (verb=roll). One integration: scout
   dispatch tie-breaks.
   Cost: 0.5 lane × 1 h, CPU. Deps: receiptd (✓). Kill: no ≥1 real decision/week where
   a forced roll beats dithering → shelf the module.

5. **Cloudflare in the loops (tip-notary, divergence watcher, twin notaries)** — rank 1
   Slice: tip-notary — read receiptd tip, anchor it in CF KV, readback-check, receipt the
   notarization. Watcher = re-run `verify` + compare tip vs KV; divergence → receipt + rc≠0.
   Cost: 1 lane × 2 h, CPU. Deps: receiptd (✓ 12/12), CF free tier + wrangler (✓).
   Kill: see below.

6. **Creative breaks** — rank 6. Zero build. Adopt only as a heartbeat rider line
   (rotate a prompt), not infra.

## Top pick: tip-notary on receiptd (highest leverage-per-hour)

Hardens the thing we shipped *today*; ~2 h; no GPU; external anchor makes tampering
visible even to an attacker who can rewrite the whole file.

- Script: `scratch/receiptd/tipnotary.py` (stdlib only: socket to daemon or
  `subprocess.run([...])` CLI list-form; `urllib.request` → CF KV API).
- Input: `receiptd.py tail 1` → {seq, h}; env `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `KV_NS`.
- Steps: `verify` (rc≠0 → abort loud) → KV PUT `si/tip` =
  `{"h":…,"seq":N,"notarized_at":iso}` → GET readback, byte-compare → append receipt
  {verb:"notarize", claim:"kv=si/tip", v:+1} → stdout `TIPNOTARY OK seq=N h=… kv=match`.
- Receipt/output: the KV pair + the chain row + one stdout line. Fail-loud: any step
  fails → rc≠0, stderr says which.
- KILL: 20 consecutive runs over an idle chain — any readback≠write, any tip change
  without a new receipt, or >2 h to a stable tip read → slice dies as specified.
  (If it instead *fires* on a real divergence like the fnv1a64 UTF-16 class — that's
  not death, that's the canary earning its seed corn; fix the spec, re-run.)

Twin-notary note: local `verify` vs a CF Worker re-verifier makes the fnv1a64 UTF-16
finding a live cross-check instead of a dormant scout note — byte-exact hash spec
required on both sides. Slice 2, only after slice 1 holds.

## Do NOT adopt (DALI pattern: ignore the build, steal the idea)

- **Two-git-agents standing infra** — wrong box (codespace-resident; our loops are
  single-box + subagents) and a maintenance burden; bobbin's own "honest costs" receipt
  is the warning label. Steal the self-decomposition prompt skeleton only.
- **A Seed-DNA *service*** — a one-shot census answers the question; a service is
  maintenance for a settled question. Steal the 9-token vocabulary as a grep checklist.
- **Any census/embedding work on local GPU** — pointless; the index already lives
  CF-side. Also dodges the N2 ReST-EM retry window (armed 00:30) entirely.

## Reuse map (no new infrastructure)

- receiptd ← tip-notary, divergence watcher, dice-roll rows, keeper-rider freshness
  queries. `verify` re-derives from disk — that IS the watcher's engine.
- pinch0's 5,138-card bge-m3 index (CF Workers AI, free tier) ← Seed-DNA semantic pass
  and any "which repos already do X" lookup. Zero local GPU, zero new store.
- fnv1a64 canary ← becomes the twin-notary's first real test case.

Order of execution: tip-notary (2 h) → keeper riders (2 h) → dice (1 h) → census (2–3 h)
→ one oracle consumption run. All CPU; one lane at a time; nothing touches the GPU box.
