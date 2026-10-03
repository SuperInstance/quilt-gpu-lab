# PLAYGROUND-NOTES — Quilt GPU Lab Image Cascade Playground

Browser face over tonight's local cascade: **dicebear → measure (moondream→qwen) → generate (SD+LCM) → CLIP identity → JEV gate**.

Location: `/home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play/playground/`

## Files
- `server.py` — stdlib `http.server` (ThreadingHTTPServer, NO flask). Port **8790**, bind `0.0.0.0`.
- `index.html` — single-file dark-themed vanilla-JS UI, no build step.
- `gen/` — every `/api/generate` take is written here as `gen_<epoch>_s<seed>_st<strength>.png`.

## How to run
```bash
/home/eileen/venvs/elephant-gpu/bin/python \
  /home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play/playground/server.py
# then browse http://<host>:8790/
```
Needs: ollama up on `127.0.0.1:11434` (moondream + qwen2.5:3b-instruct-q4_K_M), CUDA
(torch 2.14+cu126 in the elephant-gpu venv), and the sd1.5 checkpoint/LoRA on `/mnt/c`.

## Endpoints (all JSON; errors are `{"error": "..."}` with HTTP 500; bad JSON body → 400)
| Method | Path | Body → Return |
|---|---|---|
| GET | `/` | `index.html` |
| GET | `/api/health` | `{ok:true}` |
| POST | `/api/measure` | `{png_b64}` → `{desc, dials:{mood,warmth,complexity,machine_vs_organic,colorfulness}}` |
| POST | `/api/generate` | `{png_b64, prompt, strength(0.3–0.8), seed}` → `{image_b64, identity_cosine, gen_s, load_s, strength, seed, saved}` |
| POST | `/api/jev` | `{desc}` → `{noul, raw}` |
| GET | `/api/bias` | `{bias_base, bias_push, prompt_steering_effect_machine, target_dials, arms, source_v2, source_v0}` or `{error:"no receipts yet"}` |

Copy shapes reused from tonight's verified code: `identity_loop.py`, `gate_loop.py`,
`gate_v2.py`, `face_dials_v3.py`.

### /api/measure (Phase C)
moondream `"Describe this avatar face."` (temp 0, `repeat_penalty 1.15`, `repeat_last_n 32`,
`keep_alive=0`) → on ollama HTTP 500 whose **body** contains `repeat limit`, retry with
temperature bumped 0.3 / 0.5 (the lesson: READ THE ERROR BODY). Then
`qwen2.5:3b-instruct-q4_K_M` quantizes the description to 0–10 dials (`keep_alive=0`).

### /api/generate (SD img2img + identity)
`StableDiffusionImg2ImgPipeline.from_single_file(dreamshaper_8.safetensors)` +
`load_lora_weights(lcm.safetensors)` + `LCMScheduler`, **6 steps, guidance 1.3**,
strength clamped 0.3–0.8. Identity = `openai/clip-vit-base-patch32` cosine
(`local_files_only`, `.pooler_output`) between the input face and the output.

### /api/jev
`POST https://api.typesafe.ai/v1/systemone` `{model:"jev-latest", state:desc, questions:{robot:{type:"noul", ...}}}`,
`Authorization: Bearer <TYPESAFE_AI_KEY>` parsed **at use-time** from
`/mnt/c/Users/casey/key.txt` (line starting `TYPESAFE_AI_KEY=`). noul read from
`answers.robot.noul` or `results.robot.noul`.

## VRAM phasing (6GB law — ONE heavy model resident at a time)
A single process-wide `threading.Lock` serializes every heavy phase. Inside each request:
- `/api/measure` never touches SD; ollama models use `keep_alive=0`.
- `/api/generate` loads SD → generates → `del pipe; torch.cuda.empty_cache()` → **only then**
  loads CLIP → embeds → `del clip, proc; torch.cuda.empty_cache()`.
So CLIP is never resident while SD loads, and SD never overlaps CLIP. Heavy torch imports are
lazy (inside the function), so `import server` stays stdlib-only and `py_compile` is model-free.

## Frontend notes
- dicebear **v11 rc API is `new Avatar(new Style(definition), {seed, size:512}).toString()`**
  — `createAvatar` does NOT exist in rc.2. Definition JSONs come from
  `cdn.jsdelivr.net/npm/@dicebear/styles@11.0.0-rc.3/dist/<style>.min.json` (verified 6 styles:
  bottts, adventurer, personas, pixel-art, identicon, fun-emoji). This is the only working
  style CDN path tonight (JSON-only package).
- SVG→PNG: `Blob` → object URL → `Image` → canvas 512 (white background) → `toDataURL`.
- "Generate take" auto-builds the prompt from measured dials (machine_vs_organic ≥7 →
  `machine-like robot`, ≤3 → `friendly human`, mood ≥7 → `joyful`, etc.).
- Graceful degradation: dicebear import/API failures print inline; page still renders dicebear-only.
- Every API call appends a row (endpoint, latency ms, verdict) to the receipt log.

## Known limits
- Generation is **slow**: SD load ~15 s + 6-step LCM gen on the 4050; the button stays disabled
  and says "generating… (SD load ~15s)".
- `/api/bias` reads `gate_v2_receipt.json` (from `gate_loop/v2/`) and `gate_receipt.json`
  (from `gate_loop/`); returns `{error:"no receipts yet"}` if both are gone.
- No auth, no upload size cap, single-process lock means one GPU job at a time — LAN playground only.
- Identity cosine is CLIP-vit-b32 pooled cosine, not a face-recognition metric (same caveat as
  `identity_loop.py`); treat as a soft similarity, not proof.

## Self-test performed
- `py_compile server.py` (venv + system) → OK.
- Inline module JS extracted → `node --check` → OK.
- CDN reachability: esm.sh core + all 6 jsdelivr style JSONs → 200.
- `bias_sheet()` dry-run (no server started): bias_base/-push machine = −5.62/−6.88,
  steering effect −1.26; `extract_dials` + `typesafe_key` (108 chars) OK.
- Server was **not** started and nothing was committed (parent serves/tests).
