# MODELS — candidate encoders for quilt cells (the swap-and-hunt roster)

The question is not "which model is best" but "which model, living inside a
quilt cell, produces an effect we didn't anticipate." Every candidate below
gets the same cell contract: clip frames in → per-window room embedding out
→ same drift-gate / quilt-cell-log wire shape. Swap encoders, keep the
organ machinery identical, compare.

| # | model | params | fits 4050 (6GB)? | source | status |
|---|-------|--------|------------------|--------|--------|
| 1 | elephant hand-crafted dials (vmf) | 0 | CPU, 3ms/batch | local | ✓ base line (E3 KEEP) |
| 2 | our contrastive RoomEncoder | ~150k | seconds | local (E1) | ✓ trained baseline |
| 3 | V-JEPA 2 ViT-L (video world model) | ~300M | yes, inference fp16 | HF `facebook/vjepa2-vitl-fpc16-256-ssv2` | E7 |
| 4 | I-JEPA ViT-B (image JEPA) | ~86M | yes | github.com/facebookresearch/ijepa | E9 |
| 5 | LLM-JEPA (language JEPA, if weights open) | tbd | tbd | scouting | watch |
| 6 | int8 quantized (2) | /4 | yes | local | E5 |

## The breakthrough-hunt protocol
Same frames (4 lavfi clips, 6s each), same split, three readings per
encoder: (a) room separation gap, (b) drift-gate behavior at boundaries,
(c) the surprise metric — anything an encoder reads that the others don't
(dims where cross-encoder correlation < 0.5). A "no clean win" is still a
KEEP if the surprise metric fires: novel effects are the point.

## Notes from the scout (2026-09-27)
- V-JEPA 2.1 distills exist (artykbayevk/vjepa21) but HF transformers 5.17
  has native `VJEPA2Model` — prefer the native path, no third-party converter.
- I-JEPA official repo needs manual checkpoint handling; E9 will use the
  ViT-B/16 INTR checkpoint if mirrored on HF, else torch.hub fallback.
- "openJEV": no public JEV-like repo found yet (JEV is our internal
  quilt-paradigm). Closest public analogues = JEPA family. The hunt
  continues; adding candidates here as found.
