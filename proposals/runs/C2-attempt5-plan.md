# C2 attempt-5 — skip-tower isolation (vision tower + projector in bf16, LM in NF4)

Pre-registered 2026-09-29, frozen before firing. Parent: Lucineer.

## Question

attempt-4 localized the C2 poison to vision-token injection under NF4
(text-only coherent on the same loader; image+thinking garbles into digit
cycles; image+no-thinking emits "..." + EOS). WHERE does the quant damage
live — in the quantized vision tower/projector, or in the LM's handling of
vision tokens?

## Delta from attempt-4 (frozen)

- Loader: `BitsAndBytesConfig(..., llm_int8_skip_modules=["visual", "projector"])`
  (attribute names verified in transformers modeling_cosmos3_edge.py:
  `self.visual = Cosmos3EdgeVisionModel...`, `self.projector`).
- Everything else identical: repo example prompt verbatim, greedy,
  MAX_NEW=96, guard preflight, NF4 for the rest of the model.
- Cells: Q = image+thinking (the question cell), B2 = image+no-thinking,
  A2 = text+thinking (control — must stay coherent or the run is INVALID).
- Receipt must record `model.visual` param dtype (expect torch.bfloat16) —
  if the skip list silently failed to keep it bf16, verdict is INVALID_HARNESS.

## Gate (frozen)

- KEEP if Q produces >= 24 new tokens of scene-relevant text (references
  the task's objects/steps, no digit-cycle loop) AND A2 control stays coherent.
- If Q still garbles with visual+projector in bf16: the damage is in the LM's
  vision-token pathway — books as KILL for the skip-recipe, KEEP for the
  localization science, hands off to H2 (full-bf16 box).
- INVALID_HARNESS if visual is not bf16 at runtime or A2 control garbles.

## Books to

- The "skip the tower" recipe for every small-GPU box (grabbable tool).
- H2 handoff (full-bf16 check) if the LM pathway is implicated.
