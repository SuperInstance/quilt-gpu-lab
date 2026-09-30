# WGSL workgroup memory & thread cooperation — play -> science -> tooling (2026-09-29)

Trigger: Casey's "highly optimized, production-grade" WGSL template using `var<workgroup>` + `workgroupBarrier()`.
Verdict: correct skeleton, but the stated *reasons* are wrong and the pattern as written wastes the feature.

## 1. PLAY — harness built (`experiments/wg1_wgsl/`, single Rust binary, wgpu 24)
Four kernels, all GOLDEN PASS against a CPU reference (ring TICK, `out = 3*self - left - right`):
| kernel | what it tests |
|---|---|
| `casey_pass` | the template as sent: 1:1 slot mapping + barrier (shared memory roundtrip, ZERO reuse) |
| `pure_copy` | same math, registers only (the floor) |
| `direct_tick` | neighbours fetched straight from global memory |
| `shared_tick` | cooperative tile load + **halo**: interior neighbours from workgroup memory, only 2 edge threads touch global |
Gotchas paid for: wgpu24 has no `util` feature and `Instance::new(&desc)`; auto bind-group layout is per-entry-point (shared_tick doesn't use the uniform -> 2 bindings vs 3); WGSL uniform struct with `vec3` pads to 32B; and the first golden failure (exactly 2048 = 2 per 64-block) was the classic **halo** bug — a tile without halo reads its own edge as its neighbour.

## 2. SCIENCE — first pass (n=65536 / 262144, 50/20 dispatches)
Backend: **llvmpipe (CPU Vulkan)** — see §4. us/dispatch @262144: pure_copy 659 | direct_tick 837 | casey_pass 888 | shared_tick 1091.
- `casey_pass` vs `pure_copy`: **+26% for zero benefit** (store + barrier + reload that returns the thread's own value). The template's shared memory is decorative.
- `shared_tick` (halo, real cross-thread reads) is **slower** than `direct_tick` here. Reason is structural, not a bug: this stencil reads each element ~3x with only 2 of those reads coming from the tile, and it pays a barrier. **Reuse factor is the variable that matters, not "using shared memory."**
- These numbers are CPU-parallelism-bound; they validate correctness/semantics and say nothing about GPU memory hierarchy.
- Adapter limits reported: wg_storage=16384B, wg_x=256, invocations=256 (spec minimums).

## 3. THINKING — technical specs for tooling
**Where workgroup memory actually wins (reuse>1, or cross-invocation data sharing):** GEMM tiles (k-deep reuse), tall-halo stencils, reductions/prefix-sums (barrier log-tree), workgroup-atomic histograms, padding-aware transposes, and cooperative-matrix/tensor-core paths (cf. OpenDLSS-NR's `VK_KHR_cooperative_matrix` + PTX routes).
**Corrections to the template's claims:** 64 != warp size (NVIDIA/Apple SIMD = 32, AMD = 32/64); bank conflicts are a property of *access stride*, not workgroup size — 1:1 stride-1 access is conflict-free at any size; `workgroupBarrier()` is correct but here synchronises nothing (no thread reads another's slot) and must sit in uniform control flow; named 16B padding is a *layout/binding* concern, not a perf one.
**Fleet rhyme:** workgroup storage is private to the block, barrier = the tick boundary, global/ledger = cross-block routing. "Cells are dedicated; routing happens BETWEEN cells" (IE3) is the same architecture one level down.
**Tool spec — `wgsl-lab` (first rung built tonight):** adapter/limits probe (workgroup storage, invocations, subgroup + cooperative-matrix + timestamp support), pattern library (1:1, halo-stencil, reduction, GEMM tile, transpose), CPU-golden verification with JSON receipts, **explicit backend labelling so no one mistakes lavapipe for the 4050.**
**Next experiments:** WG2 reuse-factor sweep (find the crossover where shared flips from loss to win); WG3 barrier-logtree reduction vs global atomics; WG4 hardware path hunt.

## 4. BLOCKER for the WGSL-on-GPU lane (needs a decision)
This WSL2 host exposes **no NVIDIA Vulkan ICD**: `/etc/vulkan/icd.d` has no nvidia entry, and `/usr/lib/wsl/lib` ships no `libnvidia-vulkan-producer.so` (23 libs: cuda, ml, ngx, opticalflow, encode, gpucomp, **libdxcore.so**) — so every Vulkan/WebGPU compute path here lands on llvmpipe. Paths to real silicon: (a) Windows-side Chrome/Edge WebGPU benchmark, (b) mesa **dozen** (D3D12->Vulkan) on top of the present `libdxcore.so`, (c) keep WGSL as a correctness lab and do perf science on the CUDA lane (proven tonight: futhark exp1/exp5 run on the 4050, bit-identical to the CPU backend).
