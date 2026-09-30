# Encod Misc: bech32-encode / geohash-encoder / dodecet-encoder — Synergy Proposal

Date: 2026-09-29 · Author: subagent `encod-misc` · Repo root: `/home/eileen/scratch/encod/`
All three inspected READ-ONLY (no writes/commits). Commands run in copies under `/tmp` where a
build was required.

---

## 1. bech32-encode

**Purpose:** BIP-173 / BIP-350 Bech32 and Bech32m encoder — human-readable base32 with a 30-bit
BCH checksum, used for SegWit addresses & Lightning invoices.

**Format/algorithm (all in one file, `src/main.rs`, 162 lines):**
- 32-char charset `qpzry9x8gf2tvdw0s3jn54khce6mua7l` (`main.rs:4`).
- Polymod BCH generator constants `{0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3}` (`main.rs:16`); `bech32_polymod` (`main.rs:9-21`); HRP expand hi/lo nibbles (`main.rs:24-34`).
- `BECH32_CONST = 1`, `BECH32M_CONST = 0x2BC830A3` (`main.rs:5-6`); 6-symbol checksum (`main.rs:37-47`).
- `bech32_encode(hrp, data, encoding)` writes `hrp + '1' + data + checksum` (`main.rs:71-86`) — data must ALREADY be 5-bit groups.
- `convertbits(data, 8, 5, pad)` (`main.rs:89-113`); `encode_segwit_address` = witver + convertbits 8→5 (`main.rs:116-125`).

**Deps/language:** Rust 2021, **zero dependencies** (`Cargo.toml`). It is a *binary* crate
(`src/main.rs` only, no `lib.rs`), so its "library" functions are unreachable from other crates.

**Maturity: FAILS at runtime.** `cargo build` succeeds (1 dead-code warning). `cargo test` →
`running 0 tests` (no test module at all). Running the binary **panics**:
`thread 'main' panicked at src/main.rs:95:12: attempt to shift right with overflow` — line 95 is
`if value >> frombits != 0` in `convertbits`, where `value: u8` is shifted by `frombits = 8`.
Debug builds panic; release builds mask the shift (`>> 0`) and then `.unwrap()` on `None` panics
instead. Net: **the 8→5 bit conversion — i.e. the entire SegWit address path — never works.**
The one path that does work is `bech32_encode` fed hand-converted 5-bit data: it printed
`bc1qw508d6qejxtdg4y5…`, matching the BIP-173 test vector, so the polymod/checksum is correct.

**License:** `MIT OR Apache-2.0` (Cargo.toml; no LICENSE file in repo).

**Verdict:** checksum core is correct and worth lifting; everything above it is broken and untested.

---

## 2. geohash-encoder

**Purpose:** Geohash (Niemeyer 2008) encode/decode of (lat, lon) into base-32 Z-order-curve
strings, plus 8-neighbour ring query.

**Format/algorithm (`src/lib.rs`, 102 lines):**
- Alphabet `0123456789bcdefghjkmnpqrstuvwxyz` (`lib.rs:3`), `char_to_val` (`lib.rs:5-14`).
- `encode` (`lib.rs:16-51`): binary-bisection of lat/lon ranges, 5 bits → 1 char, lon at even bit index.
- `decode` (`lib.rs:53-74`): reverses, returns cell centre.
- `neighbors` (`lib.rs:76-88`): decode → offset by estimated cell size → re-encode 8 directions.

**Deps/language:** Rust 2021, **zero dependencies**; proper lib crate with 1 unit test.

**Maturity: BROKEN — `cargo test` FAILS** (0 passed, 1 failed):
`assertion left == right failed: left "u3nq", right "u4pr"` at `lib.rs:97` on the canonical
Wikipedia input `(57.64911, 10.40744)`. Empirical probe (compiled `lib.rs` unmodified into `/tmp`):

| input | crate `encode` | its own `decode` of that | error |
|---|---|---|---|
| (57.64911, 10.40744) p=12 | `u3nqgfgmqwrd` | (51.873, 66.660) | 5.78°, 56.25° |
| (51.5074, −0.1278) p=9 | `gpxqk4pk2` | (−50.744, 20.267) | 102°, 20° |
| (0, 0) p=7 | `s000000` | (0.0007, 45.0007) | lon +45° |
| (40.7128, −74.006) p=8 | `dfwmzw7y` | (20.78, −1.38) | 20°, 73° |

So **encode and decode are not inverses** — the bit-interleave is wrong; `decode` is also off
canonical (`decode("u4pruydqqvj") = (58.53, 54.40)`, should be ≈(57.65, 10.41)).
Two further verified defects:
- `char_to_val('z')` returns **32** (`'z'−'a'+7`, `lib.rs:11`) but `z` is index 31 of the alphabet →
  `decode("zzzz") = (−89.91, −179.82)` (min corner) instead of the max corner. Latent
  out-of-range/duplicate-mapping bug.
- `neighbors` cell-size math uses `4f64.powi(precision*5/2)` (= 2^(p·5), the *square* of the true
  denominator, `lib.rs:79-80`) → offsets ≈0 → returns duplicates: `neighbors("u4pr") =
  ["v3jf"×5, "v3jc"×3]`, not 8 distinct cells.

**License:** `MIT OR Apache-2.0` (Cargo.toml; no LICENSE file).

**Verdict:** algorithm sketch only; every observable output is wrong. Nothing here is safe to
reuse except the alphabet.

---

## 3. dodecet-encoder
_(pending)_

## 4. Harmony — ranked GPU-testable synergy experiments
_(pending)_

## 5. CPU-only, do not burn GPU
_(pending)_
