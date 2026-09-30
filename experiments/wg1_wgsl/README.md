# wg1_wgsl — WGSL workgroup-memory lab (first rung of `wgsl-lab`)

Single-binary Rust/wgpu harness. Build: `cargo build --release`. Run: `./target/release/wg1_wgsl <n> <iters>`.

Kernels: `shared_tick` (cooperative tile + halo), `direct_tick` (global neighbours), `casey_pass` (1:1 shared roundtrip),
`pure_copy` (registers only). Every kernel is verified against a CPU golden (ring TICK / elementwise) and prints
adapter + limits + us/dispatch + Mnodes/s, so receipts are self-contained.

Backend note: this WSL2 host has no NVIDIA Vulkan ICD -> runs on llvmpipe (CPU). Treat timings as semantic evidence,
not GPU hierarchy evidence. See `../../proposals/wgsl-workgroup-notes-2026-09-29.md`.
