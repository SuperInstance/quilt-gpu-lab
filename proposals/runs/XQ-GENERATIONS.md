# XQ Evolution Ledger — one generation per row; the winner seeds the next baseline

| Gen | Axis (one question) | Arms | Verdict | Receipt | Status |
|-----|---------------------|------|---------|---------|--------|
| G0 | External state + consolidation: does F>0 flow beat F=0 passive and no-quilt at matched reads/writes? | NOMEM / MATCH / PASSIVE / QFLOW | pending | results/xq0_substrate_consolidation.json | staged (pre-reg XQ0) |

## Seeding rules
- The winning arm's config becomes the next generation's baseline (same seeds family).
- A DEAD/negative verdict closes the axis honestly and promotes the next queued axis.
- Every generation pre-registers gates BEFORE fire; every verdict (win or die) is
  booked in RESULTS.md like every other receipt.

## Axis queue (from docs/XQ-PROGRAM.md)
- **G1** — read policy: every-step read (current) vs final-only read. Does the NN need
  to watch the substrate think, or only see the end state?
- **G2** — quilt operating points: leak k, res, inject scale sweep. INFORMED by
  INSTRUMENT-01 (box law) and RUNTIME10 (precision curves) — run those first.
- **G3** — event-triggered writes: entropy/spl fields as the NN's interrupt line
  (the substrate asks to be written, not just written to).
- **G4** — frozen local reader: qwen2.5:0.5b + learned read/write adapters —
  thinking with a LOCAL MODEL through the quilt (Casey's "quilts and local models").
