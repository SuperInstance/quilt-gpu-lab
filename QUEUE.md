# QUEUE — the chip's standing worklist. Runner claims the first unchecked item.

- [x] E1 real-glyph-contrast (2026-09-27 KEEP) — real ffmpeg frames through elephant's contrastive encoder, heldout separation vs untrained baseline
- [x] E2 flow-beat-vs-pool (2026-09-27 INCONCLUSIVE) — 40x20 flow+beat L0 tokens vs mean-pool floor on real frames (pyramid-contract test)
- [x] E3 cast-heldout control (2026-09-27 KEEP) — elephant's full vmf pipeline on real frames with cast-heldout split (does separation survive unseen content?)
- [x] E4 next-room transformer (2026-09-27 INCONCLUSIVE — dataset too thin, E4b revision needed) — <2M-param model predicting next-room from room-history over glyph-cell logs (JEV-temporal probe, 10 min budget)
- [x] E7 vjepa2-in-cells (retry after pillow+torchvision install) — V-JEPA 2 ViT-L (Meta, downloaded) embeddings through the same cell contract; judged on separation, drift-gate, and surprise vs local heads — 2026-09-27 ABORTED — 2026-09-27 KEEP
- [ ] E5 quantization probe — int8 vs fp16 embedding drift: does room-sense survive quantization for portable deployment?
- [ ] E6 harness self-test — guard breach paths, torn-queue resilience, results append integrity
- [x] E2b flow-beat-revision (2026-09-27 KILL — hand-crafted L0 dead, learned L0 next) — per-clip temporal-delta correlation only + within-texture clip pair (two moving sources); E2's cross-clip pairing conflated static-content distance with the temperature axis
- [ ] E4b next-room-revision — 60s clips (~240 cells), interleaved walk, blocked split, constant+markov-1 baselines reported alongside

- [x] E8 encoder-swap leaderboard — aggregate E1/E3/E7 (+E9) readings into one table: separation gap, drift-gate, surprise dims per encoder. The scoreboard for the swap-and-hunt protocol. — 2026-09-27 INCONCLUSIVE
- [ ] E9 ijepa stills — I-JEPA ViT-B (facebookresearch/ijepa) on still frames through the same cell contract; does a still-image world model read rooms differently than video V-JEPA 2?
- [ ] E10 invariance race — ternary gate vs a stateless sign-tracker (persistence/dead-reckoning) on the SAME frames; does the gate beat a lookup table, or is it a fancy debounce circuit? The ground-truth pole.
- [ ] E11 debounce kill — pre-registered adversarial test: run the gate on held-out sign-patterns and see if it loses to a 2-bit dead-reckoning baseline; a loss here kills the 'ternary = learning substrate' thesis honestly.
- [x] D1 look-again-scale (reach-bound fold sweep) — jev-quilt G21 Law-7 effect at scale — 2026-09-27 KEEP
- [x] D2 qthe ternary matmul kernel — parity + speedup vs fp16 (prices C1) — 2026-09-27 KEEP
- [x] D3 statevector ceiling — GPU executor for micromoth — 2026-09-27 KEEP
- [x] D6 fun scorer + seed bank — cargo-line-tycoon — 2026-09-27 KEEP
- [x] D7 quant-drift probe — fp16/int8/NF4 reader portability — 2026-09-27 KEEP
