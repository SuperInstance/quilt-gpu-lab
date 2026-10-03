# SOMRG-PILOT-V0 — SOM-learned RG blocking vs geometric majority blocking (ternary Ising)

**Origin:** vessel-lane journal proposal (16:5x AKDT, uncommitted): "SOM-learned blocking
reproduces geometric majority-blocking fixed points without being told the Hamiltonian's
symmetries." This pilot is the first falsifiable atom, CPU-only, numpy-only.

**Hypothesis H10:** per-site fluctuation signatures carry enough structure that a SOM's
winner-map partition of SITES approximates geometric 2×2 majority blocking — i.e., learned
blocks carve the lattice like RG blocks, without ever seeing the geometry.

## Frozen design (before any run; rng seeded 42)

- Model: ternary Ising, s ∈ {−1,0,+1}, H = −Σ_<ij> s_i s_j (pair ferromagnetic, J=1),
  24×24 periodic, checkerboard-vectorized metropolis. Seed 42.
- Temps: T ∈ {0.5, 0.8, 1.0, 1.2, 1.5, 2.0}. Per T: 3000 equilibration sweeps, then
  200 sample configs spaced 50 sweeps.
- **Geometric blocking:** 2×2 non-overlapping; coarse state = sign(sum of 4 trits), 0 if sum==0.
- **SOM learned blocking:** per-T SOM, 12×12=144 nodes, inputs = per-site features
  [mean(s), std(s), P(s=0)] z-scored across that T's 200 configs; sequential online updates,
  200 epochs, lr 0.5→exp decay, gaussian neighborhood σ 6→decay; site's block = its BMU.
- **Primary metric — PAIR-AGREE:** fraction of site pairs co-blocked (same block) in blocking A
  AND blocking B; compare partition of SOM vs partition of geometric blocking (576 sites,
  331k pairs, vectorized).
- **Control:** 5 random partitions per T with the SAME block-size histogram as the SOM's
  (permuted site labels), mean PAIR-AGREE vs geometric.
- **Secondary (informational):** FIELD-AGREE via majority-position node→geo-block mapping;
  spatial contiguity of SOM blocks; |m| per T.

## Gates (frozen)

- **PASS:** PAIR-AGREE delta (SOM − shuffled control) ≥ **+0.20** at T=0.5 **AND** ≥ **+0.10**
  at T=0.8 → learned blocking carries geometric signal → v1 design justified.
- **KILL:** delta ≤ 0 at every T ∈ {0.5, 1.0} → "SOM site-partition carries no geometric
  signal on pair coupling alone" → v0 dead, journal the corpse.
- Otherwise: grey — report, redesign v1 before any further run.

## Bounds & receipts

- CPU-only, ≤ 10 min wall, numpy only, single seed (42; controls seeded 1000+idx).
- Receipts: `results/somrg_pilot_v0.json` + stdout table; i2i booking; RESULTS.md annotation
  after reading. rc: 0 PASS / 1 KILL / 2 fail-loud. No re-rolls regardless of outcome.
