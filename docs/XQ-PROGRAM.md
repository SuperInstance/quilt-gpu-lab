# XQ — External Cognition Program (think WITH the quilt, THROUGH an NN)

Casey's steering (2026-10-01 08:07): keep experimenting with quilts and local models,
evolving algorithms, refining how to think EXTERNALLY with a quilt through an NN we
design and work with. This file is the program charter. Everything below runs local
(4050 / Ollama). No frontier models.

## Thesis (falsifiable)
Cognition = NN × substrate. The quilt is not a store — its PHYSICS does part of the
thinking: flow-diffusion averages evidence across cells for free (exactly the
integration the D-line pays T timesteps for), and thresholds turn smooth fields into
events. An NN that learns WHAT to externalize (write head) and reads back the
CONSOLIDATED state should integrate evidence with fewer internal parameters and lower
T-floors than the same NN alone. If consolidation-by-substrate never beats
passive-external-memory at matched reads/writes, the thesis dies honestly.

## Why now — everything we own collides here
- **D12i/D12j law**: T_floor ~ C(N,p)/W — the integration cost we're trying to beat.
- **S6b** (queued): memory tokens = the INTERNAL scratchpad control. XQ0 moves the
  scratchpad OUTSIDE and gives it physics. S6b's NOMEM arm is XQ0's NN-alone twin —
  same seeds, same code path, cross-check built in.
- **CM1 r5/r6**: judge-state quality degrades with size; chunking (externalizing
  state) is the same question one tier up, at LLM scale.
- **SuperInstance API**: tiles/rooms/gist tiers = the production cousin. Whatever XQ
  learns about what-to-write and when-to-consolidate feeds the reflex/demotion design.

## Evolution protocol (the "evolving algorithms" half)
Generations, not one-shots. Each generation: (1) freeze 2–4 arm variants on ONE axis,
(2) pre-register gates BEFORE fire, (3) run, book every verdict including negatives,
(4) the winning arm's config seeds the next generation's baseline. Axes queue:
G0 write-policy=learned-annotation (this one) → G1 read policy (every-step vs final)
→ G2 quilt operating points (leak/res/scale sweep, INFORMED by INSTRUMENT-01 +
RUNTIME10 precision curves) → G3 event-triggered writes (entropy/spl as the NN's
interrupt line) → G4 frozen local reader (qwen2.5:0.5b + learned read/write adapters
— thinking with a LOCAL MODEL through the quilt). Ledger: proposals/runs/XQ-GENERATIONS.md.

## Non-goals
No gradient-bloated mega runs (≤3 GPU-hr/arm), no frontier API spend, no gate
loosening ever, every generation booked whether it wins or dies.
