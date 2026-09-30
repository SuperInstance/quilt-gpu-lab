# GPU-IDEATION — the arc so far + ranked proposals (2026-09-29 17:05 AKDT, Casey's ask)

Status: DRAFT for team ideation (banter round 2 running). Gates freeze BEFORE any run fires.

## The arc, one line each

- **C1** Cosmos3-Edge 4B boots KEEP on 6GB (17.5 tok/s NF4).
- **C2** skip-tower recipe PROVEN: tower+projector bf16 + LM NF4 → coherent 4B-class VLM incl. bbox-JSON grounding (~53 tok/s, 2.35 GiB peak). Quantized vision was the poison.
- **C3** domain structure survives the encoder (AUC 1.0; synth/real = the easy half).
- **C4** video identity perfectly decodable (LOOCV 1.0); temporal structure strongly present.
- **IE1-3** cells are DEDICATED (0.987/0.984 specialist trunks beat joint & sequential-shared). Routing happens BETWEEN cells.
- **CM1 r1-4** format-first gates + pinch-to-fallback rescue broken cells near-free, never hurt competent ones; r4 honest band-miss (+0.119 < 0.15 gate).

Doctrine forming: **perception is per-cell (GPU), knowledge is shared (Cloudflare), the pinch decides who answers.**

## Org pushes noticed (live scout 17:05)

quilt-jepa (JEPA world model in anisotropic cell mesh — closest neighbor), micrograd-quilt (tiny autograd), Syzygy (fused single-pass sensor exec), substrate-llm-client (JEV-gated multi-provider client — CM1-adjacent), knowledge-vault-rs (SQLite+BGE-Micro vector DB), exoj (naturality 2.2e-16), pong-quilt, jev-quilt, quilt-tools, AI-Writings, quilt-research-canons, PersonalLog, quilt-c, quilt-jev-toolkit.

## Proposals (ranked, pending team ideation + Casey)

1. **C5 paired-action probe** — does the skip-tower VLM encode ACTION (same actor/different action vs different actor/same action)? Identity was 1.0; action is the harder half. The perception half of the boat brain. [pre-reg to freeze: design from C4 code; gate TBD]
2. **MORTAR TEST** — attribute tone-streams by trajectory shape alone; falsifies "the leaning is the signature" (INTERLEAVED) on real data. CPU-light companion. If it holds: attribution-without-words for the ledger. [seeded by banter round 1]
3. **TURBQUANT MEASURED** — run seeded-rotation 4-bit compression on real bge-m3 1024-d ledger embeddings; measure recall loss; turn README assertion into receipt; if ~0.5% holds → 8x storage cut for tile/pinch vectors. [evening quickie]
4. **MICROGRAD REPLICATION** — IE3 dedicated-vs-shared re-run on real task data atop micrograd-quilt (someone else's engine, doctrine-hardening). Cross-pollination with quilt-jepa.

## Banter round 1 seed (deepseek, sensory)

"FIRE is the click of recognition before the sentence finishes... CONFIRM is the word at the tip of the tongue... ESCALATE is a floor that isn't there — you step where the room should have ground and your foot keeps going... Build the test vectors. The mortar has a shape."
