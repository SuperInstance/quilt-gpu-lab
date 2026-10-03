## SOMRG-PILOT-V0 — KILLED (2026-10-02 16:5x, CPU, seed 42, pre-registered gate)

Verdict per frozen gates: KILL (d05=+0.000 need>=+0.20; d05<=0 and d10<=0).
Rows: T=0.5..2.0 -> SOM pair-agree == shuffled control EXACTLY at every T (delta +0.000 x6).
Finding: not 'weak signal' but BLIND BY CONSTRUCTION. Ordered phase (|m|=1.0): all sites
saturate to +/-1 -> identical per-site scalar features -> SOM cannot distinguish sites ->
near-all-singleton partition (3 nontrivial blocks at T=0.5) -> pair-agreement degenerates to
a function of the block-size histogram, identical to any same-histogram shuffle. Disordered
phase (T=2.0): 130 nontrivial blocks but no spatial coherence to find.
Lesson for v1: scalar per-site features [mean,std,P0] carry no spatial information; inputs
must be local PATCHES (site+neighbors) or spatially-seeded SOM. The pair-agree metric also
needs a degeneracy guard (warn when >50% singletons).
Artifacts: scratch/somrg/pilot_v0.py, results/somrg_pilot_v0.json, prereg proposals/runs/SOMRG-PILOT-V0.md.
One way it doesn't work: eliminated. The chord hunt continues.
