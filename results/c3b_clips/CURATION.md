# C3b real-footage curation (handoff H1)

**Date:** 2026-10-04 · **Lane:** H1 → C3b · **Status:** complete

## Why

C3's "real" domain was built from only the 2 Cosmos-snapshot example mp4s
(`experiments/c3_make_data.py` → `REAL_SOURCES`). Two sources cannot support a
"real vs synth" domain claim — any latent statistic measured on 2 cameras with
2 scene types is a statistic of those 2 files. This lane curates ~20 diverse,
properly licensed, real-footage clips and determinizes each to the exact C3
clip geometry so the GPU lane can extract Cosmos-3-Edge latents (C3b) on a
real domain that actually spans real-world footage.

## Determinization (byte-exact law of `c3_make_data.py`)

Read from the script, not guessed. Every clip:

- `ffmpeg -ss <t0> -i <src> -frames:v 16 -vf "fps=10,scale=256:256:force_original_aspect_ratio=increase:flags=bilinear,crop=256:256" -pix_fmt rgb24 -f rawvideo <out>.rgb`
- 16 frames × 256×256 × rgb24 = **3,145,728 bytes** exactly; size-checked, fail-loud.
- Input-side `-ss` (accurate seek is ffmpeg's default) — same as the script.
- **t0 law:** `frame_starts(pool)[0]` = 0.000 s (the script's own pick for
  1-clip-per-source). Black-fade guard: if the clip decodes with mean RGB
  < 8/255, fall back to the pool midpoint — frame-aligned, no RNG, recorded
  per clip in the manifest (`t0_rule`).
- sha256 hashed in 1 MiB chunks; **injectivity asserted** across all clips
  (no two clips byte-identical — the 2026-09-29 audit rule).

Driver: `experiments/c3b_make_clips.py` (`--check` re-hashes disk vs manifest).

## Sources & provenance (non-negotiable)

21 sources: **5 NASA** (public domain, NASA media usage guidelines) +
**16 Wikimedia Commons** (CC BY / CC BY-SA / PD / CC0 — per-clip in
`sources.json` and `MANIFEST.json`, with author credits).

Pexels/Pixabay were the requested first stops; both reject unauthenticated
programmatic fetches (HTTP 403 / API-key walls), so the build leans on the two
archives that serve permissive media with no auth. Wikimedia rate-limited the
initial burst (429, retry-after 600 s); remaining files were fetched politely
after the penalty window — nothing was scraped around any limiter.

## Diversity spread (scene × camera × motion)

| Axis | Coverage |
|---|---|
| Scenes | urban night crowd (Times Sq), urban demolition timelapse, ocean waves (Iceland), waterfall (Kenya), river-mouth aerial (Carmel), blue fire landscape (Ijen), wind turbine, road-milling machine, high-speed train, songbird nest (macro-ish static), pedestrian crossing, snowfall (Sweden), drone-over-forest (BLM), weaver-ant extreme macro, indoor pan-frying, wheat harvest (USDA), rocket launch, hurricane satellite loop, solar timelapse (SDO), astronaut pool training, rover cleanroom |
| Cameras | satellite (GPM), space telescope (SDO), pad telephoto, facility CCTV-ish static, consumer handheld, tripod static, drone, timelapse rigs, macro closeups |
| Motion | static-cam scene motion (waves, snow, fire, frying), fast linear (launch, HSR train), rotating (turbine), timelapse (viaduct, SDO, storm), aerial drift (drone, Carmel), people/vehicle flows (crossing, milling crew, cleanroom) |
| Indoor/outdoor | ~5 indoor (cleanroom, pool, frying, Times Sq signage, partially milling) vs 16 outdoor |
| Licenses | 8 PD (NASA/USDA/BLM/Commons-PD), 12 CC BY/BY-SA (3.0–4.0), 1 CC0 family among candidates; exact per clip in manifest |

## Artifacts

- `results/c3b_clips/sources.json` — provenance per source (URL, license, credit) — **tracked**
- `results/c3b_clips/MANIFEST.json` — per-clip sha256, geometry, t0, argv, license mirror — **tracked**
- `results/c3b_clips/clips/*.rgb` — 21 determinized clips — local only (gitignored)
- `results/c3b_clips/sources/*` — original downloads — local only (gitignored)
- `results/c3b_clips/c3b_clips_2026-10-04.tar.gz` — pick-up tarball for the GPU lane — local only

## Honesty notes

- NASA entries use the `~mobile.mp4` transcodes (480–720p), not `~orig`
  (74 MB–1 GB each); at 256×256 downstream this costs nothing and keeps the
  tarball sane.
- Commons metadata durations are trusted at curation time but every clip is
  re-probed locally by the driver before determinization.
- 12 of 21 sources are CC-BY* — attribution requirements are satisfied by the
  per-clip artist credit in `sources.json`/`MANIFEST.json` (kept alongside any
  redistribution).
