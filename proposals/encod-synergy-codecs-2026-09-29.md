# Encod Synergy Codecs — 2026-09-29

Read-only analysis of `/home/eileen/scratch/encod/delta-encode` and `fleet-midi-encode` (no writes to either repo; one throwaway probe crate in /tmp). All claims below were read in code or executed; anything else is marked UNVERIFIED.

## Repo 1 — delta-encode

**Purpose:** pure-Rust delta/prediction encoding library, 5 modules (`src/lib.rs:1-5`).

**Deps + language:** Rust, edition 2021 (`Cargo.toml`). **Zero dependencies** — `Cargo.lock` contains only the crate itself. License **MIT** (`Cargo.toml` `license="MIT"`; `LICENSE` "MIT License, Copyright (c) 2025 SuperInstance").

**Wire format / schemes:**
- Fixed delta (`src/delta.rs:3-84`): output[0] = base value, output[i] = v[i]−v[i−1]. `encode_u64/decode_u64` round-trip through `as i64` casts (`delta.rs:8,22`), `encode_i64/decode_i64`, and `encode_bytes→Vec<i16>` / `decode_bytes` (each byte a value, `delta.rs:59-84`).
- Varint delta (`src/vdelta.rs:7-112`): LEB128 continue-bit varint (`vdelta.rs:75-87`, `0x80` high-bit). First value = zigzag(v0) varint; then zigzag(v[i]−v[i−1]) varints (`vdelta.rs:19-23`). Decoder **requires an explicit `count`** (`vdelta.rs:30`) — the stream is **not self-delimiting**; errors: `"Unexpected end of varint data"` (`vdelta.rs:97`), `"Varint too large"` at shift≥64 (`vdelta.rs:106-108`).
- XOR delta (`src/xor.rs:3-120`): `XorDelta{xor_len: u8, xor_value: u64}`; `encode_f64` → `(first_bits: u64, Vec<XorDelta>)` with `xor_len = 64 − leading_zeros` (`xor.rs:24`). Gorilla-style `EfficientXorDelta{leading_zeros, meaningful_bits, xor_value = xor >> trailing_zeros}` (`xor.rs:87-91`). `encode_u64/decode_u64` prefix-XOR (`xor.rs:98-120`).
- Zigzag (`src/zigzag.rs:3-40`): standard `(n<<1)^(n>>63)` for i16/i32/i64 + slices.
- Prediction (`src/predict.rs:3-110`): `Predictor = fn(&[i64])->i64`; residuals = v[i]−predictor(prefix) (`predict.rs:16-17`); predictors `predict_last` (`:41`), `predict_linear` (2·last−prev, `:51`), `predict_average` (`:59`), `predict_double_exponential` (`:63`); `mse` (`:85`), `compare_predictors` → 3 (name, MSE) pairs (`:94`).

**Maturity:** `cargo test` **passes: 33 passed / 0 failed** (executed). `cargo clippy -- -D warnings` **clean** (executed); CI (` .github/workflows/ci.yml`) runs check+test+clippy. **1 commit**, clean tree. `src/main.rs` is a hello-world stub (`main.rs:1-3`); no README example test.

**README claims vs code (verified failures):**
1. README's usage block does **not compile** — `delta::encode` / `delta::decode(&deltas, values[0])` do not exist; the real names are `encode_u64`/`decode_u64` with a **1-arg** decode. Reproduced: `error[E0425]: cannot find function 'encode' in module 'delta'` and `'decode'`.
2. **Latent panic (real bug):** `encode_f64_efficient` panics at `xor.rs:90` (`xor >> trailing_zeros`) with *"attempt to shift right with overflow"* whenever consecutive f64 values are **bit-identical** (then `trailing_zeros == 64`, `xor.rs:76-79`). Reproduced with a probe: `vec![3.14f64; 5]`. It is latent because `test_f64_identical` (`xor.rs:150-154`) exercises the non-efficient path only.
3. Overflow behaviour of `encode_u64/decode_u64` for u64 values > i64::MAX is **UNVERIFIED** (no test covers it; casts at `delta.rs:8,22` are potentially lossy/wrapping).

## Repo 2 — fleet-midi-encode

**Purpose (README):** "Compressed MIDI encoding for fleet transport" — a ternary→music mapping.

**Language + deps:** Python 3, JavaScript, Go. **No build system, no manifest, no tests, no CI.** License **MIT** (same text). **1 commit**, clean tree.

**"Wire format": none exists.** There is no MIDI serialization and no compression. `lib/engine.py:1-7` is the whole encoder: start at `base` (default 60); `+1 → +4`, `-1 → −4`, `0 → hold`; it returns a Python list of note numbers. Grep for `midi|MThd|compress|varint|zlib` across all source files returns **zero matches** — no header bytes, no delta-time, no entropy coding. So the scheme is a ±4-semitone delta walk over ternary symbols; the "compressed MIDI" framing is unsubstantiated by the code.

**README claims vs reality (verified):**
- "verified across 6 languages: Python, JavaScript, Go, Rust, C, and C++" — **only 3 exist**. `find` shows just `lib/engine.py`, `lib/process.js`, `lib/go/process.go`; **Rust, C, C++ are absent**. The 6-language verification claim is **UNVERIFIED and contradicted** by the tree.
- "`python3 lib/engine.py` … output never changes" — running it produces **no output at all** (the module defines `process()` but has no `print`/`__main__`). Verified: empty stdout.
- The documented vector is otherwise correct: `process([1,0,-1,1,0,-1,1,1])` with base 60 = `[60,64,64,60,64,64,60,64,68]`. `lib/process.js:2` reproduces it (executed, matches README exactly).
- `lib/go/process.go` reads consistently with Python/JS but `go` is **not installed** here → execution **UNVERIFIED**.

## Harmony — Ranked GPU-testable synergy experiments

All gates are frozen before the run; a failed gate kills the branch, no post-hoc tuning. Baseline corpus: real tape WAL opcode rows (`BIND/LINK/EFFECT/VIEW/TICK`) and cowboy fleet rows (`qm_bind/qm_link/qm_effect/qm_view/qm_tick`) — UNVERIFIED until the parent supplies the tap; assume ≥50k rows or abort.

**H1 (strongest) — Opcode-stream delta codec.** *Hypothesis:* WAL/fleet opcode streams are temporally redundant (repeated opcodes, slowly drifting tile ids), so `zigzag+varint` deltas of `(opcode, tile_id, tick)` triplets cut bytes/opcode by ≥60% vs raw and a learned residual beats `predict_last`. *Harness:* tokenize taps → i64 triplets; measure bytes via `vdelta::encode_varint_deltas` vs raw; train 2-layer 128-d GRU on residuals, targets = next-opcode/tile-delta; metrics: bits/opcode, residual MSE, exact round-trip %. *Gates:* (a) varint stream must decode byte-exactly for 100% of 50k rows; (b) learned predictor beats `predict_last` MSE by ≥20%; (c) GPU ≤4 min. *4050 6GB:* ~2–4 min (tiny model, streamed, <1GB VRAM).

**H2 — Retrieval-trained predictor replaces hand predictors.** *Hypothesis:* the TC2 96-d retrieval-trained bottleneck (top-1 0.8782) transfers to residual prediction of tile/opcode sequences, beating best-of-`{last, linear, average}` from `predict.rs:94`. *Harness:* `predict::compare_predictors` as the frozen CPU baseline; train the 96-d encoder on the same retrieval objective, then a 1-layer head predicting next-value; metric = MSE ratio + top-1 retrieval retention. *Gates:* ≥15% MSE win over best hand predictor AND zero retrieval regression; else drop the learned head. *4050:* ~3–5 min.

**H3 — Tile boundary-integrity guard (plato-tile + MCP ingest).** *Hypothesis:* the verified failure mode — a multi-byte codepoint split at a 384-byte tile field boundary makes `decode_binary` return `None` and loses the whole tile (id64+question128+answer128+domain32+tags20+conf4+ghost4+use4) — is detectable from tile bytes alone, so a tiny classifier can flag corrupt tiles at superinstance-api ingest. *Harness:* synthesize corrupt/clean tiles (fuzz UTF-8 splits at exact field offsets; note the doc comment's wrong `tags(24)`), featurize with XOR-delta of the 64-byte sha256-hex id; train 3-layer MLP, metric AUC on held-out corrupt set. *Gates:* AUC ≥0.95 → ship MCP ingest guard; <0.90 → abandon (fall back to strict re-decode). *4050:* ~2–3 min.

**H4 — Gorilla XOR-delta for f64 payloads (confidence/embeddings/qm_view telemetry).** *Hypothesis:* after fixing the `xor.rs:90` shift bug (reuse previous leading/trailing-zero window on `xor==0`), `encode_f64_efficient` compresses f64 telemetry ≥35% vs raw with bit-exact round-trip. *Harness:* 1M floats incl. NaN, ±0, ±inf, subnormals; compare plain vs efficient vs zstd; metric bytes/float + bit-exactness. *Gates:* 0 panics, 100% bit-exact, ≥35% reduction on the smooth subset; mostly CPU-bound (GPU only if vectorized on the 4050). *4050:* <30s (or CPU-only).

**H5 — i2i-ledger Vectorize payload slimming.** *Hypothesis:* delta/XOR-encoding normalized embedding vectors before Vectorize upsert cuts stored bytes ≥35% with top-1 retrieval unchanged (cosine preserved). *Harness:* sample ledger vectors; encode with prefix-XOR (`xor.rs:98`) + optional varint quantization; metric = bytes stored + recalled@10 vs raw baseline. *Gates:* top-1 delta ≤0.002 and bytes ≤65% of baseline; else keep raw. *4050:* ~1–2 min.

## CPU-only, do not burn GPU

- **Ternary transport conformance:** write the missing Rust/C/C++ ports for the MIDI mapping and byte-diff all implementations over 10k random ternary strings (incl. UTF-8 boundary cases). The 6-language claim needs code before it needs a GPU.
- **Fix + test the two verified defects:** README example (E0425) and the `xor.rs:90` shift-overflow panic; add a regression test using bit-identical f64 runs.
- **Size benchmarks / CI:** run `cargo test`+`cargo clippy -D warnings` (already green), plus varint-vs-zstd byte counts on captured taps — pure CPU.
- **Governance:** license audit (both MIT), commit-count/README drift notes, and tap availability check before any H1–H5 GPU run.
