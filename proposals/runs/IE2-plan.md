# IE2 — Blob-only reader: sensor gap or reader dilution?

**Pre-registered 2026-09-29 09:0X AKDT, before any IE2 code.** Status: fired.

## Why

IE1 (KEEP, 6e40608) read direction from pooled Reichardt fam codes — but the
KEEP was grating-borne: blobs-only r2 = 0.061 / 0.044 / 0.015 at densities
8/16/32 while gratings read 0.702–0.836. IE1's mixed-trained ridge is
dominated by grating feature variance; blobs are a small perturbation of that
fit. Two candidate explanations:

- **H-reader (reader dilution):** the sensor carries blob direction fine; the
  mixed training distribution just never taught the reader to see it.
- **H-sensor (architecture boundary):** wide-field pooled correlators cannot
  carry small-field direction at all (a σ=2–3 blob activates a handful of the
  pooled pairs; the mean over all interior cells buries it) — matching fly
  biology, where small-field objects are read in the lobula, NOT the LPTC
  wide-field path this rung models.

## Design (frozen)

Exact reuse of the IE1 harness (import ie1_reichardt: same blob_scene,
fam_codes, ridge, seeds protocol). **One delta: the reader trains on
BLOB-ONLY sequences and is tested on blob-only sequences.**

- Config unchanged from IE1: σ ∈ {2,3}, speeds {0.25, 0.5}, 4 cardinals,
  densities 8/16/32, τ = 2 frames, warmup 12 / kept 48, 4 train + 4 test seqs
  per cfg, ridge α = 0.01, seed base 20260928.

## Gate (frozen)

**KEEP** iff blob-only r2(direction) ≥ 0.5 at ≥ 2 of 3 densities (τ=2).
- KEEP → H-reader: IE1's gap was training-distribution dilution; the
  lobula-plate rung DOES carry small-field direction.
- KILL → H-sensor: small-field motion is past the wide-field pooling rung's
  operating envelope — an architecture boundary, booked as such.

## Diagnostics (descriptive, no gates)

- Blob-only τ sweep {1, 4} at density 16 (is the blob read τ-sensitive?).
- Amplitude dilution per density: mean |pooled R code| for a blob vs a
  grating sequence at matched speed — quantifies how small the small-field
  signal is under wide-field pooling.

## Artifacts

`experiments/ie2_blob_reader.py` · `results/ie2_blob_reader.json` ·
`ie2_run.log` · this plan. CPU-only (numpy, system python3), no GPU lock.
