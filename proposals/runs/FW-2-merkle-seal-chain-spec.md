# FW-2 — Merkle seal-chain spec amendment for receipt-manifest (RC-4)

Spawned: SCOUT-42 (fleet-witness RFC 6962 Merkle checkpoints, 5th converging witness on the
seal-chain class). Raised: SCOUT-92 (fleet-witness *executed forgery* — reseal of tampered
content verified clean against a mutable working tree). Status: SPEC (docs-only landing;
implementation is a follow-on prereg, this document is the frozen words it must satisfy).

Source read (read-only, 2026-10-10): SuperInstance/fleet-witness @ 2eabe6a —
`src/tree.js` (RFC 6962 MTH: 0x00-leaf / 0x01-node domain separation, split by
largest power of two < n), `src/checkpoint.js` (C2SP-shaped note `origin\nsize\nbase64(root)`,
strict byte-canonical tail parse, Ed25519 sig seam over exact body bytes, sig excluded from
anchored digest), `docs/WITNESSING.md` (L1–L4 layer table; L4 TSA rejected; no wire-compat
claim until byte-tested per RFC 9162 lesson).

## Gap being closed (what our sealer still cannot detect)

Current `tools/receipt_manifest.py` binds sealed paths to sha256 digests at seal time, with
the SEAL-1 tracked-drift refusal and the GIT-ANCHOR-1 (eb188d1) committed-blob verify arm.
Remaining holes, both in the RC-4 class:

1. **Wholesale re-seal**: an attacker with write access may rewrite RESULTS.md history,
   regenerate the manifest (sealing is not a secret operation), and commit — every digest
   is internally consistent, GIT-ANCHOR-1 vs the NEW HEAD passes, and no artifact compares
   the new seal to any prior seal.
2. **Suffix truncation**: removing recent ledger rows (the "results never existed" attack)
   changes only the tail of RESULTS.md; nothing in our verify path asks "how many rows did
   the previous seal see?" fleet-witness's L0 fnv1a-64 chain is tamper-LOUD but their own
   study shows clean suffix truncation verifies clean at L0 — fixed at L1 by binding
   **size + root**.

## Adopted design (v2 manifest, `schema: quilt-gpu-lab/receipt-manifest@v2`)

1. **Leaf set** = the same sealed rows the v1 manifest digests: one leaf per (path, digest)
   row, leaf payload = canonical string `path + "\0" + hex-digest + "\n"`, sorted by path
   (deterministic order; no tie-break ambiguity — PARAM-1a lesson).
2. **Merkle root** over the leaf set, RFC 6962 algorithms with 0x00/0x01 domain separation,
   ported to Python stdlib (hashlib only). Vectors: pin against fleet-witness `tree.js`
   outputs on a fixed 7-leaf corpus (odd-count + power-of-two + singleton + empty cases).
   **Empty set root = SHA-256("") per RFC 6962** (fail-loud on the vacuous-seal corner).
3. **Checkpoint note** (our format, no wire-compat claim): `origin\nsize\nbase64(root)\n`
   with `origin = quilt-gpu-lab/receipt-manifest/v2`. Strict byte-canonical parse (junk
   after body throws). Size = leaf count (defeats truncation).
4. **Chain field**: manifest v2 carries `seal_chain: { prev_digest: <sha256 of the previous
   committed manifest.json blob>, size, root, note }`. `prev_digest` is read from
   `git show HEAD:receipts/manifest.json` at seal time (fail-loud if absent on first v2
   seal — the genesis admission is recorded explicitly as `prev_digest: null` exactly once).
   Verifier rule: the chain must connect HEAD~1's committed manifest to HEAD's; a break is
   named RED. This is our L2 anchor — git history IS the witness channel (we already
   operate it); no Ed25519 seam in v2 (fleet signing key is Casey territory; seam stays a
   documented v3 option, matching fleet-witness's own sig-seam deferral).
5. **Tool invariants preserved**: dirty tracked-sealed-paths refusal (SEAL-1), tracked-only
   scope, regeneration-is-the-declared-re-embed, never-edit-by-hand. tests/test_receipts.py
   gains: vector pins (item 2), truncation catch (drop a leaf → root AND size mismatch →
   RED), chain-break catch (mutate prev_digest → RED), re-seal-of-tampered-history control
   (GIT-ANCHOR-1 stays the committed-blob arm of this test).

## Pre-registered gates (implementation follow-on, frozen now)

- **G1 vectors**: Python MTH reproduces fleet-witness `tree.js` roots on the pinned corpus,
  byte-equal, including empty and singleton.
- **G2 chain**: genesis seal (explicit null) → next seal carries HEAD-manifest digest;
  tampering prev_digest in a copy → verifier RED names the field.
- **G3 truncation**: removing k≥1 leaf rows → both size and root mismatch, RED names size
  first; re-seal of the truncated set with a stale prev_digest → chain-break RED.
- **G4 non-regression**: v1 behaviors intact — tracked-drift refusal exits 2, clean seal
  exits 0, GIT-ANCHOR-1 ANCHORED on the sealed HEAD, existing test suite green. Cost: CPU
  minutes only; no GPU.
- **STOP rule**: if G1 vectors cannot be made byte-equal (algorithmic divergence), stop and
  book the divergence — do not fork the RFC 6962 spec to make tests pass.

## Non-goals (this amendment)

- No Ed25519 signing (Casey-key territory; v3 documented option).
- No witness quorum (fleet-witness L3; our single-repo git history is the single trust
  domain we actually operate).
- No TSA/external timestamp (fleet-witness L4 rejection adopted: append-only proof, not
  trusted time).
