# Lattice projections — the "latt" family as raw material for our rendering layer

**Asked by Casey, 2026-09-29 18:33** ("think about different repos too and how they
can create novel effects in our projections"). Grounded in a live org search + clones
of the five readable ones — not speculation.

## What "our projections" means

The projection layer is where a fabric's **genome** (cells: address, dials, kind,
links) is *rendered* — chiaroscuro `g` glyph mode (dials → tone ramp), `G` sculpt mode
(links → edges), the canvas grid (A1..H6), the rack-flip (ActiveLog front /
ActiveLedger back), plato rooms. Two laws hold it up:

1. the grid **is** the address space (semantics live in `kind`, not in coordinates);
2. a projection renders the genome and **cannot flatter you** (genome ≠ evidence).

Everything below is judged by whether it makes a *new* rendering possible while
keeping those two laws.

## The inventory (12 repos matching "latt" in SuperInstance, live 2026-09-29)

| Repo | What it actually is (verified) |
|---|---|
| `slackwater-lattice` | Python 0.1.0, 52 tests: exact integer geometry on the **A₂ Eisenstein hexagonal lattice** — arithmetic, build placement + collision, **A\* on the hex neighbor graph** |
| `hex-lattice-explorer` | single-file HTML canvas: A₂ grid + **Pythagorean48 direction overlay** + hover inspection. "the spatial math layer of the ternary construct" |
| `penrose-lattice` | pure Rust: Penrose tilings by **substitution** (Fibonacci matrix, eigenvalues φ, −1/φ), Penrose graph, spectral analysis, zero deps |
| `ternary-lattice` | Rust: lattice crypto over **ℤ₃ = {−1,0,+1}** — LWE sampling, 2 bits/coefficient (16× smaller than FP32), **no multiplication** (sign flip / zero check), constant-time |
| `ternary-lattice-gc` | Rust 6.9 MB: lattice-based **garbage collection for GPU object graphs** with ternary liveness |
| `lattice-hamiltonian` | Rust: **Ising/Potts, transfer matrices, phase transitions, Metropolis MC** |
| `lattice-crypto-rs` | Rust 9.1 MB: **LWE / Ring-LWE, Gaussian sampling, LLL** |
| `crystal-lattice` | Rust 4.9 MB: crystal lattice simulation — "part of the fleet ecosystem for distributed cognitive agent orchestration" |
| `lattice-climate` | Python: discrete spacetime grids with **spectral conservation** |
| `base60-lattice` | TypeScript: the **base-60 navigational lattice** — bisection × trisection of 360°; "one ring lit (the moment being retrieved)" |
| `lattice-crypto` | 10 KB stub |
| `recovered-copy-20260824-base60-lattice` | empty carcass (0 KB) from the 08-24 recovery |

## Novel effects, ranked by (novelty × cheapness × law-consistency)

**1. Hex projection — the isotropic render (slackwater-lattice + hex-lattice-explorer).**
Our square grid has asymmetric adjacency: an orthogonal link and a diagonal link are
different distances, which is exactly the aliasing surface where the canvas render
already showed ±1 dial drift and where "the grid IS the address space" strains. On an
A₂ lattice every neighbour is **equidistant and there is no privileged axis** — links
get one length, and Eisenstein integer coordinates mean the projection is **exact**
(no float drift). *New effect:* replace coordinates without touching the genome; add
**route rendering** (A\* through the fabric) so an escalation path — pinch → escalate →
compile-back — can be *drawn*, which we have never been able to do.

**2. Penrose zoom — the scale-coherent render (penrose-lattice).**
Today zoom just scales pixels. Under a Penrose substitution, zoom is an **inflation
step**: depth n+1 is derived from depth n by a fixed matrix whose eigenvalue is φ. So
a fabric rendered at scale k maps *deterministically* onto scale k+1 — no resampling
artifacts, and the thick/thin ratio itself converges to φ as a measurable receipt.
*New effect:* semantic zoom (a cell's neighbourhood at one scale is structurally the
same object at another), which is what the "gist / hint / full" tile tiers in
superinstance-api are trying to do with text.

**3. Ternary channel — the direction + decay render (ternary-lattice, ternary-lattice-gc).**
Our dials are uint32: big, unsigned, and *direction-blind*. We have been bitten twice
by implicit positive direction (the C3 logistic and C4 centroid sign bugs). A ℤ₃
projection channel renders each cell as **{−1, 0, +1}**: sign is visible by
construction, and `forget()` becomes a **three-state decay** (live → limbo →
reclaimable) instead of a silent disappearance. Bonus lever: 2 bits/coefficient is
**16× smaller than FP32** for *shipping* a projection between agents, and ℤ₃ math
needs no multiplication and has no data-dependent branching — a side-channel-free
render path for fabrics that carry secrets.

**4. Thermodynamic projection (lattice-hamiltonian).**
Dials → spins, links → couplings, then render magnetization / energy / the order
parameter. *New effect:* a fleet **temperature** and a visible **phase transition** —
the moment lanes go from disordered to ordered. This is the most falsifiable of the
set: Ising/Potts with Metropolis + transfer matrices on a 9-cell fabric is a
sub-second CPU job, and the claim ("a critical coupling exists and is reproducible
across runs") is exactly the kind of thing the lab exists to kill or keep.

**5. Base-60 clock — the temporal render (base60-lattice).**
Their own image says it: rings marking hours and days, one ring lit — *the moment
being retrieved*. Our ledger is already time-indexed (`ts`, `/since`). A base-60
nested clock renders the fleet's history as a **clock face** rather than a list:
bisection and trisection interlace, so 6×60=360 is geometric, not arbitrary. *New
effect:* the tapestry doctrine ("trails are first-class content") gets a shape.

**6. Attested projection (lattice-crypto-rs, ternary-lattice).**
LLL reduces a projection basis to its **most orthogonal** form — a canonical basis
two agents compute identically from the same genome. LWE signatures let a projection
carry **attestation**: "this rendering came from genome X", verifiable without
revealing the genome. That upgrades genome ≠ evidence from *journal testifies* to
*the rendering itself proves its provenance*.

**7. Defect map (crystal-lattice).**
Crystals are unit cell + defects; the projection shows **vacancies and interstitials**
= missing lanes, broken links, cells with no receipts. Tonight already produced
examples (C5 blocked, lanes that died without a receipt). *New effect:* a structural
health render that shows gaps spatially instead of as a list of failures.

**8. Conservation receipt (lattice-climate).**
Render the same fabric N times and assert **spectral conservation** — a lossless-render
invariant. This generalises our "checkpoint embeddings after extraction" habit into a
property of the projection pipeline itself.

## The law that makes it falsifiable

**Round-trip law: a projection may change the rendering, never the genome.**

Any projection we build must re-encode back to the *same* fabric digest. A rendering
that changes the digest is a **mutation**, and the harness must fail loud. This gives
the projection layer a gate as sharp as the inference gates:

```
genome → project(P) → re-encode → digest' == digest   (else FATAL: mutation, not projection)
```

Combined with the round-trip, effects 1–4 admit a single cheap experiment: take the
live `fleet_board` fabric (9 cells, 7 links, real receipts) and render it square /
hex / Penrose / ternary, asserting (a) identical digest after re-encode, (b) the hex
projection removes the ±1 dial-drift artifact, (c) Penrose zoom is depth-stable.

## Build order

1. `tools/proj_lattice.py` (or `.mjs`): fabric JSON → N projections + the round-trip
   assertion. Starts with **hex** (slackwater-lattice for geometry; we already have a
   canvas to render into) and **ternary** (pure arithmetic, no deps).
2. **Penrose** depth/zoom, then **Ising** criticality (the falsifiable one).
3. Wire the winner into the live canvas as a projection mode (`h` hex, `t` ternary),
   alongside the existing `g`/`G` chiaroscuro modes.

## Unknowns / to verify by recon

- `ternary-lattice-gc` and `crystal-lattice` internals unread (6.9 MB / 4.9 MB) — the
  liveness and defect vocabularies above are inferred from their READMEs.
- `lattice-climate`'s "spectral conservation" — needs a definition before we can
  assert it as a receipt.
- Whether `slackwater-lattice` is on PyPI at 0.1.0 (README badge suggests yes) — if so
  it is a **pip install**, not a port.
- LLL/LWE (9 MB Rust) is the heaviest lift and the only one with real cryptographic
  stakes; treat as a research lane, not a projection feature, until the others land.
