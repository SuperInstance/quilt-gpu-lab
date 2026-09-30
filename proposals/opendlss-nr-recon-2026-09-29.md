# OpenDLSS-NR Deep Recon — 2026-09-29

Repo: /home/eileen/scratch/external/OpenDLSS-NR (READ-ONLY recon)
Goal: techniques for running neural nets on GPUs in novel ways; feed new-tool proposals for the SuperInstance fleet (RTX 4050, WSL2).

## 1. ARCHITECTURE

Not ONNX, not ncnn, no external inference engine. It is a **hand-written Vulkan-compute inference stack**, two complete routes producing identical bytes (docs/execution.md:54):

- **GLSL route** (`shaders/`, 16 kernels): FP8 GEMMs via `VK_KHR_cooperative_matrix` (`mma.sync m16n8k32` 16x16x32 cooperative-matrix chains), fused 32-channel transformer block per workgroup, fused QKV+window attention (execution.md:56-66).
- **PTX route** (`scripts/ptx/`, ~3.3k lines of Python generators emitting PTX text): `mma.sync.aligned.m16n8k32...f16.e4m3.e4m3.f16`, cp.async 3-stage rings, warp specialization (copy warp issues all cp.async via named barriers — gemm2_e4m3.py:24-28), split-K, streamed global attention. PTX text becomes a `VkCudaModuleNV` via **`VK_NV_cuda_kernel_launch`** — CUDA kernels launched inside a Vulkan command buffer, driver JITs (execution.md:26-27, README.md:77).

**Model format:** custom directory — `manifest.json` with 11 stage files of packed E4M3 bytes (sha256-verified on load, nr_model.cpp:85-86) + 153 tensor records `(stage, stageOffset, byteLength)` (weights.md:11-13). Weights are stored **as MMA fragments, not matrices** — the host re-lays the fragment permutation into plain tiles (`packedWeightIndex`, weights.md:51-64, nr_model.cpp:17-33). 141 MiB, 71 blocks. **Weights are NOT in the repo and nothing here extracts them** — "You supply the weights" (README.md:11,106); you must reverse-engineer NVIDIA's binaries yourself (legal firewall, README.md:163-167).

**The network:** U-net of shifted-window Swin transformers + global ViT at the bottleneck; 71 blocks, 6 pooling levels. Dataflow: 16 f32 input lanes/pixel — 3 Gaussian noise lanes (Box-Muller from padded-coordinate hash), display proxy (not HDR — tone-mapped sRGB, centred), reprojected previous output, style/tone/structure/skin scalars (network.md:10-21) → output 4 f32: RGB residual + temporal-blend logit (network.md:7-8). Resolution-preserving re-renderer, not an upscaler. Block = FFN (grouped-expert MLP) + window attention with learned per-channel skip scales; skip is **seeded into the MMA C operand**, not added in epilogue (network.md:102-104).

**Numerics as spec:** E4M3 publications at every kernel boundary, f16 inside; NaN→+0, −0 sign preserved; the FP8 tensor-core dot product is reverse-engineered as fixed-point F13 arithmetic and reimplemented exactly (numerics.md:9-48) — including a CPU reference (`src/reference.cpp`) and a **WebGPU port with no tensor cores/FP8** that is still byte-exact (ports/browser-webgpu/, E4M3 decoded arithmetically from u32 words, pow2 built by writing the exponent field).

## 2. BIT-EXACTNESS

"Bit-exact" = every intermediate at all **75 block boundaries matches NVIDIA's captures byte-for-byte**, not just the final image (README.md:5-6). Verification machinery:

- `dlss5vk parity` — runs the graph against a fixture dir of recorded native captures (E4M3 boundary refs, f32 head, composed output); verdicts: **bit-exact** / equal-up-to-sign-of-zero / within-one-code (8-bit capture only) / mismatch (main.cpp:78,563). Fixtures are strict-manifested: every comparable boundary must have a reference or a declared reason (README.md:105-125).
- `dlss5vk verify` — **kernel-by-kernel bisect**: captures intra-block GPU tensors, feeds each check the GPU's own inputs so a mismatch names exactly one kernel (verify.cpp:1-4).
- Every tuning switch (PTX↔GLSL fallbacks, chaining off, split-K off...) must itself pass parity — the gate keeps the non-default route from rotting (execution.md:68-70).
- WebGPU port has its own JS/WGSL oracle + numerics.bin CPU-reference gate (browser-webgpu README).

Core lesson: a network's identity is a *sequence of roundings*, not a real-valued function; parity harness + per-kernel bisect is the transferable pattern.

## 3. TOOLING

| Tool | What | Reusable? |
|---|---|---|
| `scripts/ptx/*.py` | Python PTX emitters (Ptx helper class, shared swin.py fragment layout lib) | ⭐⭐⭐ the crown jewels — CUDA-kernel codegen without CUDA toolchain |
| `dlss5vk bench/profile` | per-dispatch GPU timing, 241-dispatch breakdown (README.md:56-58) | ⭐⭐ pattern for any Vulkan-compute profiler |
| `dlss5vk parity/verify` | golden-fixture bit-exact gate + kernel bisect | ⭐⭐⭐ steal wholesale |
| `src/reference.cpp` | CPU bit-accurate model of tensor-core FP8 math | ⭐⭐⭐ oracle generator |
| `scripts/fetch_tools.ps1` | portable pinned toolchain (glslang, volk, headers, CMake, Ninja) — no SDK install | ⭐⭐ |
| barrier-free chaining lib | device-counter producer/consumer sync (`red.release.gpu.global.add` / `ld.acquire.gpu`, forward-DAG check, 1s watchdog) — execution.md:117-159 | ⭐⭐⭐ kills dispatch-barrier overhead |
| WebGPU port + check.mjs | same exactness gate in browser, headless Chrome harness | ⭐⭐ |
| Filament patch/demo | per-object motion vectors + `queueVulkanCommand` interop hook (frame.md:34-37) | ⭐ reference only |

## 4. NOVEL TOOLS FOR US

1. **vkgolden** — deterministic Vulkan-compute inference micro-framework: golden-fixture parity harness + CPU oracle + per-kernel bisect (ports of verify.cpp/reference.cpp pattern). Our JEPA/tile models get bit-exact regression gates across driver changes. Value: high. Effort: low — 4050 Ada supports coop-matrix.
2. **ptx-weave** — the Python-PTX-emitter technique generalized: emit specialized fused kernels (cp.async rings, warp-spec, counter chaining) for our small models, launched via `VK_NV_cuda_kernel_launch` or plain CUDA. Dead code elimination per-shape = no tensor framework. Value: high for cell-mesh/tile kernels. Effort: medium.
3. **igpu-tinynet** — WebGPU-port trick on our iGPU/edge lane: exact FP8/f16 emulation with u32-decoded E4M3 and exponent-field pow2, so one numeric spec runs on anything (browser, iGPU, WSL) byte-identically. Value: medium-high (fleet heterogeneity). Effort: low-medium.
4. **nr-prefilter-tile** — neural prefilter for our tile pipeline: 16-lane feature packing (noise lanes + proxy + conditioning scalars) → tiny 32-channel Swin block, resolution-preserving, applied per tile before codec quantization. Value: high if it survives compression tests. Effort: medium-high (need training, we only get inference techniques here).
5. **chainbar-off** — standalone device-counter chaining (forward-DAG validated, watchdog) as a lib for any Vulkan compute graph with many small dispatches (our 241-dispatch-style pipelines). Value: medium. Effort: low.

Ranking for 4050+WSL2: 1 > 5 > 2 > 3 > 4.

## 5. WSL REALITY CHECK

**Core host is Windows-bound; the ideas are not.** Hard constraints: requires Windows + Ada + `VK_NV_cooperative_matrix2`, `VK_EXT_shader_float8`, `VK_NV_cuda_kernel_launch` (README.md:88-89) — `cuda_kernel_launch` is Windows-NVIDIA-driver-only in practice; all build/run scripts are PowerShell. However: it is **pure compute** — no swapchain, no vsync, no present; `vk::Context` is "one device, one compute queue, storage buffers only, no images, no render passes" (execution.md:5-6). So on WSL2: the GLSL cooperative-matrix route should run under Vulkan-on-WSL *if* the WSL NVIDIA ICD exposes coop-matrix (it exposes the host's; needs a probe — `vulkaninfo | grep cooperative`), but the PTX fast route needs `VK_NV_cuda_kernel_launch`, which the WSL driver likely does not surface. The demo (Filament/present) is display-bound. The WebGPU port runs anywhere (headless Chrome works in WSL). Verdict: **portability constraint is driver extension surface, not display** — a WSL-native rebuild would use the GLSL route or swap `cuda_kernel_launch` for plain CUDA interop.

WORDS: 1037
