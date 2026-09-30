# TC1 — The 384-byte tile: does a learned codec beat the deterministic one at an identical byte budget?

Pre-registered 2026-09-29 (fired immediately after commit+push). Source: SuperInstance/plato-tile-encoder
(384-byte binary codec, read at /home/eileen/scratch/encod/plato-tile-encoder) × the canon's "6D codec gap"
(menu vs pyramid) × our own corpus (quilt-gpu-lab + canon research + workspace memory).

## Question
The crate spends 384 bytes on TEXT fields: id(64) + question(128) + answer(128) + domain(32) + tags(20) +
confidence(4) + ghost(4) + use_count(4). Two sibling budgets at exactly 384 bytes are available and untested:
a full-dimension int8 embedding (384 dims x 1 byte) and a learned 96-d float32 bottleneck (96 x 4 = 384).
Which codec preserves tile MEANING best at the same budget?

## Design (frozen)
- Corpus: real tiles mined from our own markdown (RESULTS.md, proposals/, canon research/, workspace memory/).
  id = sha256 hex of question+answer (64 chars = exactly the crate's 64-byte id field), question = section
  heading, answer = first paragraph, domain = source, tags = <=3 words from the heading.
  Unicode-heavy documents are deliberately included (our docs carry --, ->, checkmarks, micro-dollar signs).
- Embedder: thenlper/gte-small (384-d), CUDA.
- Arms (each EXACTLY 384 bytes):
  A) DETERMINISTIC — faithful Python reimplementation of the crate's layout + truncation semantics
     (byte-truncate at field size; decode fails on invalid UTF-8, as read_str does), validated
     byte-for-byte against the real Rust crate on shared fixtures.
  B) INT8_FULL — symmetric int8 quantization of the 384-d embedding (no training).
  C) LEARNED_BOTTLENECK — 384->96->384 autoencoder (linear), Adam, trained on the corpus, 96 float32.
- Metrics: cosine(original meaning, decoded meaning); retrieval top-1/top-5 (query = question embedding,
  index = decoded tile representation); deterministic-arm decode-failure rate; bytes used per arm.

## Frozen gates
- G1 DETERMINISTIC_DECODE_LOSS: arm A fails to decode >= 5% of the real corpus (a bug-class finding).
- G2 ADAPTIVE_WINS: best of (B, C) has cosine >= A + 0.10 AND retrieval top-1 >= A + 0.05.
- G3 DETERMINISTIC_WINS: A has cosine >= best of (B, C) + 0.10.
- Otherwise TIE. Report all arms regardless; no re-rolls. Any harness bug -> diagnose, discard, re-fire.

## Predicted (recorded before firing, for honesty)
A will lose meaning because answers >128 bytes are silently truncated, and will fail outright on unicode
truncation (read_str returns None). B loses less (no truncation, quantized noise only). C should be closest
to B or better on cosine but may trail on retrieval. Guess: G2 fires; the tile text fields are not enough.
