# AL-1 — proj_lattice digest dialect hardening (pre-registration; FROZEN before fire)

Spawned by SCOUT-58 (self-catch: tools/proj_lattice.py:62 fnv1a64 iterates ord(ch) — code-unit
dialect family) and AMENDED by SCOUT-64 (canons 3da3db2: eisenstein-embed `%64` OR-fold collision
class — FNV low-6-bits is a multiplication mod 64, alphabet +8 stride a≡q..j≡z; rule: never take
hash % 2^k as a bit index / never OR-fold into fixed width).

## Scope (frozen)
- tools/proj_lattice.py ONLY. px2_patchwork's terrain_digest_fnv1a64 is PINNED by cited receipts
  (0x75f652bc1d8464b8 in px2 gardener session headers) and a different module — DO NOT TOUCH.
- Change: fnv1a64 hashes UTF-8 bytes (`text.encode('utf-8')`) instead of ord(ch) code points;
  genome_digest gains an ASCII fail-loud gate on the canonical parts (fleet genomes are ASCII;
  non-ASCII must be explicit, not silently dialect-dependent).

## Gates (pre-registered, words)
- **G1 (blast-radius zero)**: zero BOOKED verdicts cite proj_lattice digests (VX-1 taint query +
  grep of results/ for proj_lattice digest values before and after change; verdict sets IDENTICAL).
- **G2 (ASCII invariance)**: all ASCII digests byte-identical pre/post fix — pinned pre-fix values:
  d("")=cbf29ce484222325, d("abcdefgh")=25da8c1836a8d66d, d("qrstuvwx")=a5beb10ce3cb36ad,
  d("cat")=f5e307190ce4a327, d("sat")=822d97195cd5ebf7, plus DEMO_FABRIC genome_digest before/after.
- **G3 (dialect + non-ASCII determinism)**: fnv1a64("é") equals the UTF-8-byte FNV-1a64 reference
  computed independently in the test; non-ASCII inputs deterministic cross-call; ASCII gate raises
  on a non-ASCII genome part (RED observed first: gate absent → then added → PASS).
- **G4 (SCOUT-64 collision-class pin)**: test asserts the eisenstein fold-class pairs DIFFER under
  our full-width digest — ("abcdefgh","qrstuvwx"), ("cat","sat") — and a source-level census gate:
  no `& 0x3f` / `% 64` / `% 0x40` fold of the hash anywhere in tools/ (grep-in-test).

## Cost
CPU only, ~15 min. No GPU. No booked result may change (G1); if G1 finds a citing booking, STOP
before firing and re-scope.
