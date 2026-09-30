# DLSS 5 MANAGER — Deep Recon (2026-09-29)

Target: /home/eileen/scratch/external/DLSS-5-MANAGER — .NET 8 / Avalonia / F# app (33 .fs files) + native C++ ScreenNative layer (screen_worker.cpp = 7,128 lines) + bundled Python "Screen" runtime. Read-only recon for the quilt-gpu-lab fleet (RTX 4050 / WSL2).

## 1. End-to-End: What the App Actually Does

It is a **per-game neural-upscaler runtime swapper + a desktop-wide GPU inference engine**. Two halves:

**(a) Game manager/installer.** `GameScanner` inventories every installed game: Steam via registry HKCU\Software\Valve\Steam + `libraryfolders.vdf` + `appmanifest_*.acf` parsing (GameScanner.fs:373–429), Epic via `%ProgramData%\Epic\...\Manifests\*.item` JSON (fs:455–523), GOG via registry `SOFTWARE\WOW6432Node\GOG.com\Games` (fs:526–583), plus a raw fixed-drive walk for repacks/standalones (fs:585+). Per game it resolves the *real* executable with a scoring engine (version-resource FileDescription vs title ×50,000, engine layout bonuses like `/binaries/win64/`, Unity `<Name>_Data` detection, crack-folder penalties — GameAnalyzer.fs:254–330), and detects upscaler DLLs by filename: `nvngx_dlss*`→DLSS, `ffx_fsr*`→FSR, `libxess`, `optiscaler`, `nvngx.ini` (GameScanner.fs:334–352). `findDlssFolders`/`findStreamlineFolders` then locate `nvngx_dlss.dll/nvngx_dlssg.dll/nvngx_dlssd.dll` and the 8 `sl.*.dll` Streamline runtimes, reading each DLL's `FileVersionInfo` (GameAnalyzer.fs:36–48, 377–383, 449–457). Results are persisted in `analysis_cache_v2.json` so installs never re-walk trees (AnalysisStore.fs:7–11, 40–46).

`ModInstaller` then swaps/upgrades runtime DLLs **per game, reversibly**: every overwritten file is backed up and recorded in a manifest (`dlss5-install.json` in AppData + a sidecar beside the game exe — ModInstaller.fs:13–19, 212–260). Version discipline: Streamline is only refreshed if the game ships ≥ 2.4 (`minimumStreamlineVersion`, ModInstaller.fs:24, 1877–1895); DLLs are replaced only when the bundled build is newer ("Updating %s %s -> %s…", fs:2307–2311). Install routes (InstallMode, fs:78–99): **OptiScaler** proxy-DLL hijack on slots `dxgi/winmm/version/dbghelp/d3d12/wininet/winhttp.dll` or `OptiScaler.asi` (fs:579–580); **ReShade + RenoDX** add-ons for DX12/DX11/DX9-via-dgVoodoo/Vulkan; emulator route; AMD RDNA4 route. Payloads in `mod files/`: `renodx-dlss.addon64` / `renodx-dlss5.addon64` (Multipass) / `renodx-mfgunlock.addon64` (multi-frame-gen unlock), `nvngx.dll.addon64` (neural upstream), and the 165 MB `nvngx_dlssnr.dll` ray-reconstruction model (fs:354–383, 540, deployed at fs:2565). **GPU-targeted payload selection**: an RTX 40/50 machine (regex `RTX\s*(40|50)\d{2}`, SystemSpecs.fs:123–127) installs a different OptiScaler build folder than other cards (ModInstaller.fs:549–574). `AntiCheat.fs:5–11` warns (never blocks) when target folders contain EAC/BattlEye/etc.

**(b) Screen / LIVE FLOW.** A bundled Python `controller.py` (ScreenViewModel.fs:785–799) drives C++ workers that capture a window/monitor (Windows Graphics Capture, screen_worker.cpp:17–21) and run **NGX "feature 18" (DLSS ray reconstruction) over the whole desktop** — sharpness, edge smoothing, optical-flow frame interpolation (`NS_SHARPNESS/NS_EDGE_SMOOTH/NS_FLOW_MFG`, screen_worker.cpp:1940–1967), HDR scRGB/PQ colorspace handling (fs:1906–1936), motion via NVIDIA Optical Flow SDK (`motion_backend=nvofa`, ScreenViewModel.fs:764–769), custom HLSL compute kernels refining the flow field block-by-block (flow_shader.h:5–29), and Spout2 shared-texture output for other apps (spout_bridge.cpp).

Support: `CloudAssets` pulls optional payload bundles from a public R2 bucket with HEAD size checks and staged-atomic download into `mod files` (CloudAssets.fs:19, 114, 150–178); `SystemSpecs` reads GPU/driver from registry display-class GUID subkeys (never WMI), ordering dGPU before iGPU (SystemSpecs.fs:14–15, 49–95); `CommunityApi` reports/querys a shared `/v1/games` results DB (CommunityApi.fs:324–360).

### The two hard reverse-engineering wins (ScreenNative)
1. **nvapi architecture spoof** — `nvngx_dlssnr.dll` refuses feature 18 on pre-Blackwell GPUs, yet its fatbins contain Turing/Ampere/Ada/Blackwell kernels: "the refusal is policy, not missing code." The worker hooks `NvAPI_GPU_GetArchInfo` **in its own process memory** (prologue-saved patch, no trampoline), caching real answers first and lying only for the primary card: Ada→Blackwell 0x1B0 (screen_worker.cpp:219–343).
2. **Caller-identity gate bypass** — the same DLL rejects callers whose module path lacks the substring "nvngx.dll" (measured with a 4-run probe, ngx_forwarder.cpp:1–24). The worker is simply *named* `nvngx.dll`; a forwarder DLL is the escape hatch.
3. **32-bit bridge** — 32-bit games can't load x64 NGX, so a sidecar "host" process opens a 1×1 hidden D3D12 window ("from the add-on's point of view it IS a D3D12 game") and evaluates DLAA on frames shipped via **cross-process shared D3D11 textures + shared fences**, pipe carrying only fixed-size structs — "everything heavy stays on the GPU" (screen_worker.cpp:1–11; feed_ipc.h:3–9).

## 2. GPU-Harnessing Inventory (mechanisms in code)

1. Per-game proxy-DLL hijack of the DXGI/D3D load chain (OptiScaler slots, ModInstaller.fs:579).
2. ReShade add-on injection: RenoDX DLSS-overrides, MFG unlock, neural upstream (fs:354–383).
3. Model-file swap with version gating: newer-only DLSS/Streamline upgrades, min-version floors (fs:24, 2307).
4. Direct NGX SDK driving of feature 18 with color/depth/MV inputs (screen_worker.cpp:1497–1511).
5. In-memory capability spoof of nvapi arch query (fs:219–343) + module-name gate bypass (ngx_forwarder.cpp).
6. Full-desktop capture→GPU inference→present pipeline incl. HDR tone mapping (screen_worker.cpp:1906+).
7. GPU optical-flow (NVOFA) + custom HLSL flow-refinement kernels for frame interpolation (flow_shader.h).
8. Cross-process zero-copy GPU IPC: shared textures, NT handles, D3D12 fences (feed_ipc.h:3–9).
9. GPU-variant payload selection (RTX 40 build vs neural build; ModInstaller.fs:549–574).
10. Driver/GPU registry interrogation replacing WMI (SystemSpecs.fs:14–15); community telemetry of route outcomes (CommunityApi.fs).

## 3. Transferable: Top 5 for a Linux/WSL RTX-4050 ML Fleet

1. **Capability-gate skepticism + cached interrogation layer.** The arch-spoof lesson: vendor libraries encode *policy* gates, not capability truths — verify with evidence (fatbin sm_ coverage). Rebuild: an NVML/`cuDeviceGetAttribute` probe service that answers (arch, driver, CUDA, VRAM, fatbin coverage) once per boot, cached like SystemSpecs' registry read (fs:108) — cheap, no subprocess spam; WSL2's driver is the Windows driver, so registry/NVML parity matters across the boundary.
2. **Reversible per-target artifact swapping with manifests + sidecars.** ModInstaller's manifest model (InstalledFile{Target,Backup,WasExisting} + mode/api/arch tags, fs:36–73; AppData copy + sidecar beside the target, fs:212–260) is exactly the hygiene a fleet needs for pinning per-project CUDA/torch/cuDNN/model versions: backup-before-swap, upgrade-only-if-newer, uninstall = restore. Steal the schema.
3. **Sidecar GPU-host pattern with zero-copy IPC.** Decouple "who produces frames" from "who owns the GPU context": a stable host process that looks like a legit graphics/compute app, producers ship buffers via shared memory + fences, control over a tiny pipe protocol (feed_ipc.h). Maps directly to CUDA IPC / Vulkan external memory on WSL2 for fleet agents feeding one 4050 inference host.
4. **Scan-once, score, cache analysis.** The inventory pipeline (multi-store discovery → heuristic scoring with version-resource signals → targeted filename walks, depth-capped → JSON cache, GameAnalyzer.fs:399–423, AnalysisStore.fs) is a template for a fleet-wide "what models/runtimes/venvs are installed where" index without heavy calls.
5. **R2-backed atomic asset distribution + hardware-targeted variants.** CloudAssets' HEAD-then-staged-download-rename (fs:114, 150–178) plus RTX40-vs-neural payload folders = artifact variants selected by GPU probe. Rebuild: R2 bucket of torch wheels/checkpoints per GPU class, staged-atomic installs, community-style result telemetry (which model+driver combo worked) fed back to a `/v1/games`-like results DB.

## Receipts Index
Key files: GameScanner.fs:334–352, 373–453 · GameAnalyzer.fs:36–48, 254–330, 377–457, 510–620 · ModInstaller.fs:13–19, 24, 36–99, 354–383, 549–616, 1877–1895, 2307–2311, 2565 · AnalysisStore.fs:7–46 · SystemSpecs.fs:14–15, 49–95, 123–127 · CloudAssets.fs:19, 114, 150–178 · CommunityApi.fs:324–360 · AntiCheat.fs:5–11 · ScreenViewModel.fs:764–799 · screen_worker.cpp:1–11, 219–343, 1497–1511, 1906–1967 · ngx_forwarder.cpp:1–24 · feed_ipc.h:3–9 · flow_shader.h:5–29 · spout_bridge.cpp:1–25 · verify_output.cpp:1–25.

WORDS: 1044
