# FWIT-1 — fleet-witness sig-seam as upgrade path for our sha-only receipt-manifest seal
Date: 2026-10-09 04:4x AKDT (day-conductor slice, B-slot; scout rotation satisfied by SCOUT-84 03:45)
Type: READ-ONLY design note. **No seal format change without Casey sign-off.** No tree changes.

## Sources (all MERGED on SuperInstance/fleet-witness, read via gh, read-only)
- #5 checkpoint: Ed25519 signer seam filled (v0.1) — `sign(size, root, privPem)` over exact
  note-body bytes; `sig:<base64>` line appended; **sig line never enters the anchored digest**
  (anchors bind body only); unsigned notes verify `{ok:false, reason:'unsigned'}` = honest
  degradation, not error. 26/26 pins, FAIL-first (runner dies at require on pristine main).
- #3 channel (b): sibling-seal digest embedding — a sibling ledger binds to an anchored
  checkpoint with ONE ordinary WAL row; verifier re-derives the digest from the *presented
  note*, never trusting the row's digest field. Catches truncation-after-embedding and
  forged notes. 28/28 pins.
- #4/#7 L3 witness quorum (designed-not-built per study R7): C2SP tlog-witness v1.0.0 shape —
  consistency proof before cosign, persist-before-cosign, k-of-n with strict-majority bound
  t ≥ ⌈(n+m+1)/2⌉; n=3 across 3 trust domains, k=2; client-held policy, unrecognized-key
  fail-closed. Honest semantics: without monitors, split-view resistance = fail-closed
  freezing, not convergence.
- #8 truncate-demo: live-narrated attack artifact (L0 silent-truncation hole → checkpoint
  catches; rollback + same-size in-place forgery variants caught). "A demo that can't fail
  is marketing, not evidence" — exits 0 only if every attack caught.

## Assessment vs our receipt-manifest seal (tools/receipt_manifest.py, sha256 content seals)
1. **What a signed seal would buy us:** collapses standing EP-1 class #6 ("historical seal
   digest" — a digest alone cannot prove WHO sealed or that the sealer was honest) into a
   verifiable signature. Also closes the agent-that-reseals adversary class our own slices
   keep demonstrating (SIG-1 note, SCOUT-9; reseal-forgery instances: quilt-jepa ×2, jev-receipts,
   canons 1017Z — RC-4 raised 3×).
2. **Direct transplant is NOT drop-in:** their design anchors an append-only WAL/checkpoint
   chain; our manifest is a whole-tree content seal re-issued on every ledger change. The
   mapping that fits us: keep the sha256 manifest as the "note body", add an Ed25519
   `sig` line over the manifest digest, key held OUTSIDE the agent process (their fleet-PEM
   pattern, ~/.config/fleet-witness; matches quilt-canvas-tui identity-plane v1 finding from
   SCOUT-9: key must be outside the agent process or the signature proves nothing).
3. **Sequencing per their build gate doctrine:** L2 (bind-only) first — a manifest row that
   embeds the prior seal's digest = cheap chain seals (RC-4 spec amendment already pinned
   "chain seals" from SCOUT-28); signature seam second; L3 quorum only if/when ≥2 external
   hosts run always-on (their gate; ours would be Casey's fleet decision).
4. **Their honesty rules we should adopt verbatim:** (a) unsigned/unsigned-verify is honest
   degradation, never an error; (b) "no witnessing claim until a real external cosig exists
   on disk" (Nous v5.67 rule); (c) sig bytes never enter the sealed digest — signature is a
   wrapper, not a content change (preserves byte-stability of existing seals).
5. **Convergence witness:** canons dcb327f / doubt-ledger Ed25519 root signing / jev
   checkpoint signatures (RC-4 prior-art fold, SCOUT-19) — this is now a 4th independent
   fleet implementation pointing the same direction. Fleet consensus is real; RC-4's
   "chain seals + re-derive don't re-execute verify mode" spec amendment stands, signature
   seam is the natural next increment behind it.

## Gates (pre-registered, words)
- G1: read-only — zero bytes changed in the repo by this item (verifiable: git status shows
  only this note + RESULTS.md booking).
- G2: every claim above cites a merged PR or an already-booked repo finding; no speculation
  presented as fact.
- G3: no key material read, echoed, or moved (keys never echoed; fleet PEM path noted, not opened).

## Verdict
PASS as design note. Recommendation to Casey (day item, gated): adopt increment 2.5 —
Ed25519 sig line over manifest digest, key outside agent process — as the RC-4 follow-on
after chain seals. Not scheduled; no code written.
