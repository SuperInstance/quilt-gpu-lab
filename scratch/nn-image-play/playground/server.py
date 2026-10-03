#!/usr/bin/env python3
"""QUILT IMAGE PORTAL — chat-driven image cascade with live system graph,
growing gallery, and generation timelapse (GIF exportable).

Runs under the GPU venv:
  /home/eileen/venvs/elephant-gpu/bin/python server.py
Stdlib http.server only (NO flask). Port 8790, bind 0.0.0.0.

Panels served by index.html:
  CHAT       vibe-coding: POST /api/chat enqueues a job; worker runs the
             full cascade; receipts stream back via GET /api/job
  NETWORK    GET /api/graph — live system states + event log
  GALLERY    GET /api/gallery — accepted set (wave receipts + portal accepts)
  TIMELAPSE  GET /api/timelapse (frames) / GET /api/timelapse.gif (build+save)

Cascade per job (stage machine, GPU_LOCK phases per 6GB law):
  parse -> seed -> edges? -> generate(timelapse frames) -> identity(CLIP,DINOv2)
        -> perceive -> jev -> verdict -> gallery
6GB law: one heavy model resident; ollama calls use keep_alive=0 (RAM law).
Fails loud as JSON {"error":...}; a bad request never kills the server.
Legacy v1 studio preserved: /legacy -> index_v1.html.
"""
import base64
import collections
import io
import json
import pathlib
import queue
import shutil
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).parent
INDEX = HERE / "index.html"
LEGACY = HERE / "index_v1.html"
GEN = HERE / "gen"; GEN.mkdir(exist_ok=True)
TL_DIR = GEN / "timelapses"; TL_DIR.mkdir(exist_ok=True)
ACCEPTED = GEN / "accepted"; ACCEPTED.mkdir(exist_ok=True)
PORTAL_LOG = GEN / "portal_gallery.jsonl"

SCRATCH = pathlib.Path("/home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play")
FLEET_DIR = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
CN_DIR = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/controlnet/lllyasviel_scribble"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
OLLAMA = "http://127.0.0.1:11434/api/generate"
KEYFILE = "/mnt/c/Users/casey/key.txt"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
CLIP_ID = "openai/clip-vit-base-patch32"
DINO_ID = "facebook/dinov2-base"
RENDER_MJS = HERE / "render_dicebear.mjs"

HOST, PORT = "0.0.0.0", 8790
DIALS = ["mood", "warmth", "complexity", "machine_vs_organic", "colorfulness"]
FLEET = ("lucineer", "casey", "jev", "mmx")

GPU_LOCK = threading.Lock()
JOBS = {}                 # id -> job dict
JOBQ = queue.Queue()
TL = {}                   # job_id -> {"frames":[paths], "meta":{...}}
LAST_JOB = {"id": None}
SYS = {name: {"state": "idle", "detail": "", "ms": None}
       for name in ("ChatParse", "DiceSeed", "Perception", "ScribbleEdges",
                    "Generator", "IdentityBoard", "JEVGate", "Gallery", "Timelapse")}
EVENTS = collections.deque(maxlen=60)
SRC_DIALS = {}            # (init_key) -> {"desc","dials"} cache
DIAL_LOCK = threading.Lock()


def log(*a):
    print(*a, flush=True)


def ev(msg):
    EVENTS.append({"t": round(time.time(), 3), "msg": msg})
    log("[ev]", msg)


# ---------------------------------------------------------------- helpers
def strip_b64(s):
    if not isinstance(s, str) or not s:
        raise ValueError("missing base64 image payload")
    if s.startswith("data:"):
        s = s.split(",", 1)[1]
    return s.strip()


def b64_to_bytes(s):
    return base64.b64decode(strip_b64(s))


def ollama(model, prompt, images=None, opts=None, keep_alive=0):
    base = {"temperature": 0, "num_predict": 140,
            "repeat_penalty": 1.15, "repeat_last_n": 32}
    if opts:
        base.update(opts)
    body = {"model": model, "prompt": prompt, "stream": False, "options": base}
    if images:
        body["images"] = images
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    last_err = None
    for temp in (None, 0.3, 0.5):
        if temp is not None:
            body["options"]["temperature"] = temp
        req = urllib.request.Request(
            OLLAMA, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read())["response"]
        except urllib.error.HTTPError as e:
            errbody = e.read().decode()[:300]
            last_err = f"ollama HTTP {e.code}: {errbody}"
            if "repeat limit" in errbody:
                continue
            raise RuntimeError(last_err)
    raise RuntimeError(last_err or "ollama: no response")


QUANTIZE = (
    "You rate avatar faces from a description. Reply with ONLY strict JSON, "
    "integers 0-10:\n"
    '{"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,'
    '"complexity":<0 minimal..10 busy>,'
    '"machine_vs_organic":<0 machine..10 organic>,'
    '"colorfulness":<0 monochrome..10 vivid>}\n'
    "Description: {desc}"
)


def extract_dials(txt):
    if not txt:
        return None
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(txt[i:j + 1])
    except json.JSONDecodeError:
        return None
    return d if all(k in d for k in DIALS) else None


def perceive_png_bytes(png_bytes):
    """moondream perceive -> qwen quantize. No heavy GPU model held."""
    b64 = base64.b64encode(png_bytes).decode()
    desc = ollama("moondream", "Describe this avatar face.", images=[b64],
                  opts={"temperature": 0}, keep_alive=0).strip()
    if not desc:
        raise RuntimeError("moondream returned empty description")
    dials = extract_dials(ollama("qwen2.5:3b-instruct-q4_K_M",
                                 QUANTIZE.replace("{desc}", desc),
                                 opts={"temperature": 0}, keep_alive=0))
    if dials is None:
        raise RuntimeError("qwen did not return valid dial JSON")
    return {"desc": desc, "dials": dials}


def typesafe_key():
    for line in open(KEYFILE):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("TYPESAFE_AI_KEY not found in key.txt")


JEV_Q = {
    "robot": ("Does this description clearly indicate a machine-like robot "
              "character rather than a human?",
              "Answer true only if the description unambiguously refers to a "
              "robot/machine figure."),
    "human": ("Does this description clearly indicate a human character "
              "rather than a machine or robot?",
              "Answer true only if the description unambiguously refers to a "
              "human figure."),
    "abstract": ("Does this description clearly indicate a distinct "
                 "non-human character figure (robot, judge, or abstract "
                 "entity)?",
                 "Answer true only if the description unambiguously refers "
                 "to a distinct character figure."),
}


def jev_noul(desc, kind="robot"):
    q, ins = JEV_Q.get(kind, JEV_Q["robot"])
    req_body = {"model": "jev-latest", "state": desc,
                "questions": {"char": {"type": "noul", "question": q,
                                       "instructions": ins}}}
    req = urllib.request.Request(
        TYPESAFE_URL, data=json.dumps(req_body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {typesafe_key()}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    noul = None
    for path in (("answers", "char", "noul"), ("results", "char", "noul"),
                 ("answers", "robot", "noul"), ("results", "robot", "noul")):
        cur, ok = resp, True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, (int, float)):
            noul = cur
            break
    return {"noul": noul, "raw": resp}


def render_dicebear(style, seed, size=512):
    """Server-side dicebear render via node (resvg). Returns PNG bytes."""
    out = HERE / f"_seed_{uuid.uuid4().hex[:8]}.png"
    proc = subprocess.run(
        ["node", str(RENDER_MJS), style, seed, str(size), str(out)],
        capture_output=True, text=True, timeout=60)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"dicebear render failed: {proc.stderr[-300:]}")
    data = out.read_bytes()
    out.unlink()
    return data


def edge_map(png_bytes, size=512):
    """v4b-verified scribble extraction."""
    from PIL import Image, ImageFilter, ImageOps
    img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((size, size))
    e = ImageOps.invert(img.filter(ImageFilter.FIND_EDGES))
    return ImageOps.autocontrast(e).filter(ImageFilter.GaussianBlur(0.6))


def auto_prompt(dials, vibe=""):
    if not dials:
        base = "portrait of a character, clean vector shapes"
    else:
        p = ["portrait of"]
        m = dials.get("machine_vs_organic", 5)
        if m >= 7:
            p.append("a machine-like robot")
        elif m <= 3:
            p.append("a friendly human")
        else:
            p.append("a cyborg character")
        mo = dials.get("mood", 5)
        p.append("joyful" if mo >= 7 else ("stoic" if mo <= 3 else "calm"))
        cx = dials.get("complexity", 5)
        p.append("highly detailed" if cx >= 7 else "minimal, clean vector shapes")
        co = dials.get("colorfulness", 5)
        p.append("vivid colors" if co >= 7 else "muted tones")
        base = ", ".join(p)
    if vibe:
        base = f"{base}, {vibe}"
    return base


PARSE_PROMPT = (
    "You translate an image request into strict JSON for an avatar pipeline. "
    "Reply with ONLY JSON, no prose:\n"
    '{"subject":"lucineer|casey|jev|mmx|custom","style":"<dicebear style, e.g. '
    'bottts|adventurer|personas|pixel-art|fun-emoji, empty if subject known>",'
    '"seed":"<seed string for custom, else empty>","kind":"robot|human|abstract",'
    '"vibe":"<comma-separated style descriptors from the message>",'
    '"strength":<0.30-0.80>,"cn":<true|false>,"cn_scale":<0.30-0.90>}\n'
    "Defaults: subject lucineer, kind robot, cn true, cn_scale 0.6, strength "
    "0.55. Known fleet faces ignore style/seed. 'keep the shape/structure' -> "
    "cn true; 'loose/free/painterly/drifting' -> cn false. Bigger changes -> "
    "higher strength.\nMessage: {msg}"
)


def parse_intent(message, history):
    ctx = ""
    if history:
        last = history[-1]
        ctx = f"\nPrevious request context: {json.dumps(last)[:400]}"
    txt = ollama("qwen2.5:3b-instruct-q4_K_M",
                 PARSE_PROMPT.replace("{msg}", message).replace(
                     "{last_spec}", ctx),
                 opts={"temperature": 0, "num_predict": 200}, keep_alive=0)
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i:
        raise RuntimeError(f"parser returned no JSON: {txt[:120]}")
    spec = json.loads(txt[i:j + 1])
    spec["subject"] = spec.get("subject", "lucineer")
    spec["kind"] = spec.get("kind", "robot")
    spec["style"] = spec.get("style") or "bottts"
    spec["seed"] = spec.get("seed") or spec["subject"]
    spec["vibe"] = spec.get("vibe") or ""
    spec["strength"] = max(0.3, min(0.8, float(spec.get("strength", 0.55))))
    spec["cn"] = bool(spec.get("cn", True))
    spec["cn_scale"] = max(0.3, min(0.9, float(spec.get("cn_scale", 0.6))))
    return spec


# ---------------------------------------------------------------- stages
class Stage:
    def __init__(self, system):
        self.system = system

    def __enter__(self):
        SYS[self.system].update(state="busy", detail="", ms=None)
        self.t0 = time.time()
        return self

    def __exit__(self, et, ev_, tb):
        ms = round((time.time() - self.t0) * 1000)
        SYS[self.system]["ms"] = ms
        if et is None:
            SYS[self.system]["state"] = "done"
        else:
            SYS[self.system]["state"] = "error"
            SYS[self.system]["detail"] = str(ev_)[:160]
        self.ms = ms
        return False


def set_detail(system, detail):
    SYS[system]["detail"] = str(detail)[:160]


def run_job(job):
    """Full cascade. Appends to job['stages']; composes job['reply']."""
    import torch
    from PIL import Image

    jid = job["id"]
    spec = job["spec"]
    st = job["stages"]

    def mark(name, state, ms=None, detail=""):
        st.append({"name": name, "state": state, "ms": ms, "detail": detail})

    try:
        # ---- 1. seed ------------------------------------------------
        t0 = time.time()
        with Stage("DiceSeed"):
            if spec["subject"] in FLEET:
                init_bytes = (FLEET_DIR / f"{spec['subject']}.png").read_bytes()
                init_key = spec["subject"]
                seed_note = f"fleet face {spec['subject']}"
            else:
                init_bytes = render_dicebear(spec["style"], spec["seed"])
                init_key = f"{spec['style']}:{spec['seed']}"
                seed_note = f"dicebear {spec['style']} seed={spec['seed']}"
        mark("seed", "done", round((time.time() - t0) * 1000), seed_note)
        job["seed_note"] = seed_note

        # ---- 2. source perception (cached) --------------------------
        t0 = time.time()
        with Stage("Perception"):
            with DIAL_LOCK:
                cached = SRC_DIALS.get(init_key)
            if cached is None:
                cached = perceive_png_bytes(init_bytes)
                with DIAL_LOCK:
                    SRC_DIALS[init_key] = cached
        mark("source_dials", "done", round((time.time() - t0) * 1000),
             json.dumps(cached["dials"]))
        src_dials = cached["dials"]
        prompt = auto_prompt(src_dials, spec["vibe"])
        job["prompt"] = prompt

        # ---- 3. edges (optional CN) ---------------------------------
        emap = None
        if spec["cn"]:
            t0 = time.time()
            with Stage("ScribbleEdges"):
                emap = edge_map(init_bytes)
            mark("edges", "done", round((time.time() - t0) * 1000), "PIL scribble")

        # ---- 4. generate + timelapse --------------------------------
        t0 = time.time()
        frames = []
        with Stage("Generator"):
            from diffusers import (StableDiffusionControlNetImg2ImgPipeline,
                                   StableDiffusionImg2ImgPipeline,
                                   ControlNetModel)
            from diffusers.schedulers.scheduling_lcm import LCMScheduler

            init = Image.open(io.BytesIO(init_bytes)).convert("RGB").resize((512, 512))
            frames.append(init)

            def capture(pipe, i, t, kw):
                lat = kw["latents"]
                with torch.no_grad():
                    z = lat / pipe.vae.config.scaling_factor
                    img = pipe.vae.decode(z).sample
                frames.append(pipe.image_processor.postprocess(
                    img, output_type="pil")[0])
                return {}

            gen_kwargs = dict(prompt=prompt, image=init, strength=spec["strength"],
                              guidance_scale=1.5, num_inference_steps=6,
                              callback_on_step_end=capture,
                              callback_on_step_end_tensor_inputs=["latents"])
            load_s = None
            if emap is not None:
                t0g = time.time()
                cn = ControlNetModel.from_pretrained(
                    CN_DIR, torch_dtype=torch.float16, variant="fp16")
                pipe = StableDiffusionControlNetImg2ImgPipeline.from_single_file(
                    CKPT, controlnet=cn, torch_dtype=torch.float16,
                    safety_checker=None)
                pipe.load_lora_weights(LCM)
                pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
                pipe.to("cuda"); pipe.enable_attention_slicing()
                load_s = round(time.time() - t0g, 1)
                gen_kwargs.update(control_image=emap,
                                  controlnet_conditioning_scale=spec["cn_scale"])
            else:
                t0g = time.time()
                pipe = StableDiffusionImg2ImgPipeline.from_single_file(
                    CKPT, torch_dtype=torch.float16, safety_checker=None)
                pipe.load_lora_weights(LCM)
                pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
                pipe.to("cuda"); pipe.enable_attention_slicing()
                load_s = round(time.time() - t0g, 1)

            g = torch.Generator("cuda").manual_seed(job["seed"])
            t1 = time.time()
            out = pipe(**gen_kwargs, generator=g).images[0]
            gen_s = round(time.time() - t1, 1)
            frames.append(out)
            outdir = GEN / "tl" / jid
            outdir.mkdir(parents=True, exist_ok=True)
            fpaths = []
            for i, f in enumerate(frames):
                p = outdir / f"frame_{i:02d}.png"
                f.save(p)
                fpaths.append(str(p))
            outpath = outdir / "final.png"
            out.save(outpath)
            del pipe
            if emap is not None:
                del cn
            torch.cuda.empty_cache()
        mark("generate", "done", round((time.time() - t0) * 1000),
             f"gen {gen_s}s load {load_s}s frames {len(fpaths)}")
        TL[jid] = {"frames": fpaths,
                   "meta": {"prompt": prompt, "strength": spec["strength"],
                            "cn": spec["cn"], "cn_scale": spec["cn_scale"],
                            "seed": job["seed"], "gen_s": gen_s, "load_s": load_s}}
        LAST_JOB["id"] = jid
        with Stage("Timelapse"):
            set_detail("Timelapse", f"{len(fpaths)} frames")
        ev(f"timelapse ready: {jid} ({len(fpaths)} frames)")

        # ---- 5. identity (CLIP then DINOv2, phased) -----------------
        t0 = time.time()
        with Stage("IdentityBoard"):
            from transformers import CLIPModel, CLIPProcessor, AutoModel, AutoImageProcessor
            clip = CLIPModel.from_pretrained(CLIP_ID, local_files_only=True).to("cuda").eval()
            cproc = CLIPProcessor.from_pretrained(CLIP_ID, local_files_only=True)

            @torch.no_grad()
            def cembed(im):
                inp = cproc(images=im, return_tensors="pt").to("cuda")
                f = clip.get_image_features(**inp)
                f = f.pooler_output if hasattr(f, "pooler_output") else f
                return torch.nn.functional.normalize(f, dim=-1)[0]
            clip_cos = round(torch.nn.functional.cosine_similarity(
                cembed(init), cembed(out), dim=0).item(), 4)
            del clip, cproc
            torch.cuda.empty_cache()
            dino = AutoModel.from_pretrained(DINO_ID, local_files_only=True).to("cuda").eval()
            dproc = AutoImageProcessor.from_pretrained(DINO_ID, local_files_only=True)

            @torch.no_grad()
            def dembed(im):
                inp = dproc(images=im, return_tensors="pt").to("cuda")
                h = dino(**inp).last_hidden_state[:, 0]
                return torch.nn.functional.normalize(h, dim=-1)[0]
            dino_cos = round(torch.nn.functional.cosine_similarity(
                dembed(init), dembed(out), dim=0).item(), 4)
            del dino, dproc
            torch.cuda.empty_cache()
        mark("identity", "done", round((time.time() - t0) * 1000),
             f"clip {clip_cos} dino {dino_cos}")

        # ---- 6. output perception -----------------------------------
        t0 = time.time()
        buf = io.BytesIO(); out.save(buf, format="PNG")
        with Stage("Perception"):
            out_perc = perceive_png_bytes(buf.getvalue())
        mark("out_dials", "done", round((time.time() - t0) * 1000),
             json.dumps(out_perc["dials"]))
        delta = {k: int(out_perc["dials"][k]) - int(src_dials[k]) for k in DIALS}

        # ---- 7. JEV --------------------------------------------------
        t0 = time.time()
        with Stage("JEVGate"):
            jr = jev_noul(out_perc["desc"], spec["kind"])
        noul = jr["noul"]
        mark("jev", "done", round((time.time() - t0) * 1000), f"noul {noul}")

        # ---- 8. verdict + gallery ------------------------------------
        accepted = (clip_cos >= 0.80) and (noul is not None and noul >= 0.60)
        with Stage("Gallery"):
            rec = {"ts": round(time.time(), 3), "job": jid, "accepted": accepted,
                   "subject": spec["subject"], "style": spec.get("style"),
                   "seed_str": spec["seed"], "seed": job["seed"], "kind": spec["kind"],
                   "message": job["message"], "prompt": prompt,
                   "strength": spec["strength"], "cn": spec["cn"],
                   "cn_scale": spec["cn_scale"], "clip": clip_cos,
                   "dino": dino_cos, "noul": noul,
                   "dials_src": src_dials, "dials_out": out_perc["dials"],
                   "delta": delta, "path": str(outpath)}
            if accepted:
                dest = ACCEPTED / f"{jid}.png"
                shutil.copyfile(outpath, dest)
                rec["accepted_path"] = str(dest)
            with open(PORTAL_LOG, "a") as f:
                f.write(json.dumps(rec) + "\n")
        ev(f"job {jid} verdict: {'ACCEPTED' if accepted else 'REJECTED'} "
           f"clip {clip_cos} dino {dino_cos} noul {noul}")

        job.update({"result": rec, "accepted": accepted,
                    "image_path": str(outpath),
                    "reply": compose_reply(job, spec, seed_note, prompt,
                                           gen_s, load_s, clip_cos, dino_cos,
                                           noul, delta, accepted)})
    except Exception as e:
        traceback.print_exc()
        job["error"] = f"{type(e).__name__}: {e}"
        job["reply"] = f"💥 job failed: {job['error']}"
        mark("error", "error", None, job["error"][:160])


def compose_reply(job, spec, seed_note, prompt, gen_s, load_s,
                  clip_cos, dino_cos, noul, delta, accepted):
    lines = []
    vibe = f' vibe="{spec["vibe"]}"' if spec["vibe"] else ""
    lines.append(f"⚙ parsed → {seed_note}, kind={spec['kind']}, "
                 f"cn={'%s @ %.2f' % ('scribble', spec['cn_scale']) if spec['cn'] else 'off'}, "
                 f"strength={spec['strength']:.2f}{vibe}")
    lines.append(f"🎨 generated · prompt: {prompt} · {gen_s}s gen, {load_s}s load")
    top = sorted(delta.items(), key=lambda kv: -abs(kv[1]))[:2]
    dtxt = ", ".join(f"{k} {v:+d}" for k, v in top)
    lines.append(f"👁 dial drift (out − source): {dtxt or 'flat'}")
    ok_id = clip_cos >= 0.80
    lines.append(f"🧭 identity: CLIP {clip_cos:.3f} {'✓' if ok_id else '✗'} · "
                 f"DINO {dino_cos:.3f} (morph-watch)")
    ok_j = noul is not None and noul >= 0.60
    lines.append(f"⚖ JEV noul {noul if noul is None else round(noul, 3)} "
                 f"{'✓' if ok_j else '✗'} ({spec['kind']} question)")
    if accepted:
        lines.append("✅ ACCEPTED → added to the growing gallery. "
                     "Timelapse frames ready — hit SAVE GIF in the timelapse panel.")
    else:
        why = []
        if not ok_id:
            why.append("identity below the 0.80 floor")
        if not ok_j:
            why.append("JEV noul below 0.60")
        lines.append(f"❌ REJECTED — {', '.join(why)}. Try: more structure "
                     "(cn on), lower strength, or a different seed.")
    return "\n".join(lines)


def worker():
    while True:
        job = JOBQ.get()
        try:
            job["state"] = "running"
            ev(f"job {job['id']} started: {job['message'][:60]}")
            # ---- parse ----
            t0 = time.time()
            with Stage("ChatParse"):
                try:
                    spec = parse_intent(job["message"], job["history"])
                except Exception as pe:
                    log("[parse fallback]", pe)
                    spec = {"subject": "lucineer", "style": "bottts",
                            "seed": "lucineer", "kind": "robot", "vibe": "",
                            "strength": 0.55, "cn": True, "cn_scale": 0.6}
            job["spec"] = spec
            job["stages"].append({"name": "parse", "state": "done",
                                  "ms": round((time.time() - t0) * 1000),
                                  "detail": json.dumps(spec)[:160]})
            run_job(job)
        except Exception as e:
            traceback.print_exc()
            job["error"] = f"{type(e).__name__}: {e}"
            job["reply"] = f"💥 job failed: {job['error']}"
        finally:
            job["state"] = "done" if not job.get("error") else "error"
            ev(f"job {job['id']} {job['state']}")


# ---------------------------------------------------------------- gallery
def _find_receipt(name):
    p = SCRATCH / name
    if p.exists():
        return p
    hits = sorted(SCRATCH.rglob(name))
    return hits[-1] if hits else None


def gallery_items():
    items = []
    if PORTAL_LOG.exists():
        for line in PORTAL_LOG.read_text().splitlines():
            try:
                r = json.loads(line)
                if r.get("accepted"):
                    items.append({"src": "portal", "name": r["job"],
                                  "path": r.get("accepted_path") or r["path"],
                                  "clip": r.get("clip"), "dino": r.get("dino"),
                                  "noul": r.get("noul"), "subject": r.get("subject"),
                                  "prompt": r.get("prompt"), "ts": r.get("ts")})
            except json.JSONDecodeError:
                continue
    for rname, label in (("v4_receipt.json", "v4"), ("v3_receipt.json", "v3")):
        p = _find_receipt(rname)
        if not p:
            continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        for c in d.get("candidates", []) or d.get("accepted", []) or []:
            if not isinstance(c, dict):
                continue
            if c.get("accepted") or c.get("corrected_pass") or c.get("identity_pass"):
                items.append({"src": label, "name": c.get("name", "?"),
                              "path": c.get("path"), "clip": c.get("identity"),
                              "noul": (c.get("jev") or {}).get("noul"),
                              "subject": c.get("subject"), "prompt": c.get("prompt"),
                              "ts": None})
    items.sort(key=lambda x: x.get("ts") or 0, reverse=True)
    return items


def bias_sheet():
    v2 = _find_receipt("gate_v2_receipt.json")
    v0 = _find_receipt("gate_receipt.json")
    if v2 is None and v0 is None:
        return {"error": "no receipts yet"}
    out = {"bias_base": None, "bias_push": None,
           "prompt_steering_effect_machine": None}
    if v2 is not None:
        d = json.loads(v2.read_text())
        out["bias_base"] = d.get("bias_base")
        out["bias_push"] = d.get("bias_push")
        out["prompt_steering_effect_machine"] = d.get("prompt_steering_effect_machine")
        out["target_dials"] = d.get("target_dials")
        out["source_v2"] = str(v2)
    if v0 is not None:
        d = json.loads(v0.read_text())
        if out["bias_base"] is None:
            out["bias_base"] = d.get("bias")
        out["source_v0"] = str(v0)
    return out


def graph_state():
    jid = LAST_JOB["id"]
    cur = JOBS.get(jid) if jid else None
    stage_now = None
    if cur and cur["state"] == "running":
        busy = [n for n, s in SYS.items() if s["state"] == "busy"]
        stage_now = busy[0] if busy else None
    edges = [
        ["ChatParse", "DiceSeed"], ["DiceSeed", "Perception"],
        ["DiceSeed", "ScribbleEdges"], ["ScribbleEdges", "Generator"],
        ["Perception", "Generator"], ["Generator", "IdentityBoard"],
        ["Generator", "Perception"], ["Perception", "JEVGate"],
        ["IdentityBoard", "JEVGate"], ["JEVGate", "Gallery"],
        ["Generator", "Timelapse"], ["JEVGate", "ChatParse"],
    ]
    return {"systems": SYS, "edges": edges, "events": list(EVENTS)[-14:],
            "stage_now": stage_now,
            "job": ({"id": cur["id"], "state": cur["state"],
                     "message": cur["message"][:80]} if cur else None)}


def timelapse_frames(thumb=320):
    jid = LAST_JOB["id"]
    if not jid or jid not in TL:
        return {"error": "no timelapse yet"}
    from PIL import Image
    frames = []
    for p in TL[jid]["frames"]:
        im = Image.open(p).convert("RGB").resize((thumb, thumb))
        buf = io.BytesIO(); im.save(buf, format="PNG")
        frames.append(base64.b64encode(buf.getvalue()).decode())
    return {"job": jid, "meta": TL[jid]["meta"], "frames": frames}


def timelapse_gif():
    jid = LAST_JOB["id"]
    if not jid or jid not in TL:
        raise RuntimeError("no timelapse yet")
    from PIL import Image
    frames = [Image.open(p).convert("RGB").resize((256, 256))
              for p in TL[jid]["frames"]]
    dest = TL_DIR / f"tl_{jid}.gif"
    frames[0].save(dest, format="GIF", save_all=True,
                   append_images=frames[1:], duration=550, loop=0)
    ev(f"gif saved: {dest.name} ({frames[0] and len(frames)} frames)")
    return dest.read_bytes(), dest.name


# ---------------------------------------------------------------- http
ALLOWED_ROOTS = (SCRATCH.resolve(), GEN.resolve())


class Handler(BaseHTTPRequestHandler):
    server_version = "QuiltPortal/2.0"

    def log_message(self, fmt, *a):
        log("[http]", self.address_string(), fmt % a)

    def _send(self, code, payload, ctype="application/json", headers=None):
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload).encode()
        elif isinstance(payload, str):
            data = payload.encode()
        else:
            data = payload
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        return json.loads(raw or b"{}")

    def do_GET(self):
        try:
            path, _, qs = self.path.partition("?")
            if path in ("/", "/index.html"):
                if not INDEX.exists():
                    self._send(500, {"error": "index.html missing"})
                else:
                    self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            elif path == "/legacy":
                self._send(200, LEGACY.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/health":
                self._send(200, {"ok": True, "jobs": len(JOBS),
                                 "last_job": LAST_JOB["id"]})
            elif path == "/api/graph":
                self._send(200, graph_state())
            elif path == "/api/gallery":
                self._send(200, {"items": gallery_items()})
            elif path == "/api/timelapse":
                self._send(200, timelapse_frames())
            elif path == "/api/timelapse.gif":
                data, name = timelapse_gif()
                self._send(200, data, "image/gif",
                           {"Content-Disposition": f'attachment; filename="{name}"'})
            elif path == "/api/img":
                from urllib.parse import parse_qs, unquote
                p = unquote(parse_qs(qs).get("p", [""])[0])
                real = pathlib.Path(p).resolve()
                if not any(str(real).startswith(str(r)) for r in ALLOWED_ROOTS):
                    self._send(403, {"error": "path outside allowed roots"})
                    return
                if not real.exists():
                    self._send(404, {"error": "not found"})
                    return
                self._send(200, real.read_bytes(), "image/png")
            elif path == "/api/bias":
                self._send(200, bias_sheet())
            elif path.startswith("/api/job"):
                from urllib.parse import parse_qs
                jid = parse_qs(qs).get("id", [""])[0]
                job = JOBS.get(jid)
                if not job:
                    self._send(404, {"error": "no such job"})
                else:
                    self._send(200, {k: job.get(k) for k in
                                     ("id", "state", "stages", "spec", "reply",
                                      "error", "accepted", "image_path",
                                      "message", "seed")})
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        try:
            body = self._read_json()
        except Exception as e:
            self._send(400, {"error": f"bad json: {type(e).__name__}: {e}"})
            return
        try:
            path = self.path.split("?", 1)[0]
            if path == "/api/chat":
                msg = (body.get("message") or "").strip()
                if not msg:
                    self._send(400, {"error": "empty message"})
                    return
                jid = uuid.uuid4().hex[:10]
                job = {"id": jid, "message": msg,
                       "history": (body.get("history") or [])[-6:],
                       "seed": int(body.get("seed", int(time.time()) % 10000)),
                       "state": "queued", "stages": [], "spec": None,
                       "reply": None, "error": None}
                JOBS[jid] = job
                JOBQ.put(job)
                self._send(200, {"job_id": jid})
            elif path == "/api/measure":
                self._send(200, self.measure(body))
            elif path == "/api/generate":
                self._send(200, self.generate(body))
            elif path == "/api/jev":
                desc = (body.get("desc") or "").strip()
                if not desc:
                    self._send(400, {"error": "missing desc"})
                    return
                self._send(200, jev_noul(desc, body.get("kind", "robot")))
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    # legacy v1 endpoints kept for the /legacy studio --------------------
    def measure(self, body):
        b64 = strip_b64(body.get("png_b64"))
        raw = base64.b64decode(b64)
        return perceive_png_bytes(raw)

    def generate(self, body):
        import torch
        from diffusers import StableDiffusionImg2ImgPipeline
        from diffusers.schedulers.scheduling_lcm import LCMScheduler
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor

        init_bytes = b64_to_bytes(body.get("png_b64"))
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("missing prompt")
        try:
            strength = float(body.get("strength", 0.55))
        except (TypeError, ValueError):
            strength = 0.55
        strength = max(0.3, min(0.8, strength))
        try:
            seed = int(body.get("seed", 1))
        except (TypeError, ValueError):
            seed = 1
        init = Image.open(io.BytesIO(init_bytes)).convert("RGB").resize((512, 512))
        with GPU_LOCK:
            t0 = time.time()
            pipe = StableDiffusionImg2ImgPipeline.from_single_file(
                CKPT, torch_dtype=torch.float16, safety_checker=None)
            pipe.load_lora_weights(LCM)
            pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
            pipe.to("cuda"); pipe.enable_attention_slicing()
            load_s = round(time.time() - t0, 1)
            g = torch.Generator("cuda").manual_seed(seed)
            t1 = time.time()
            out = pipe(prompt=prompt, image=init, strength=strength,
                       guidance_scale=1.3, num_inference_steps=6,
                       generator=g).images[0]
            gen_s = round(time.time() - t1, 1)
            outpath = GEN / f"gen_{int(time.time())}_s{seed}_st{strength}.png"
            out.save(outpath)
            del pipe
            torch.cuda.empty_cache()
            clip = CLIPModel.from_pretrained(CLIP_ID, local_files_only=True).to("cuda").eval()
            cproc = CLIPProcessor.from_pretrained(CLIP_ID, local_files_only=True)

            @torch.no_grad()
            def embed(im):
                inp = cproc(images=im, return_tensors="pt").to("cuda")
                f = clip.get_image_features(**inp)
                f = f.pooler_output if hasattr(f, "pooler_output") else f
                return torch.nn.functional.normalize(f, dim=-1)[0]
            cosine = round(torch.nn.functional.cosine_similarity(
                embed(init), embed(out), dim=0).item(), 4)
            del clip, cproc
            torch.cuda.empty_cache()
        buf = io.BytesIO(); out.save(buf, format="PNG")
        return {"image_b64": base64.b64encode(buf.getvalue()).decode(),
                "identity_cosine": cosine, "gen_s": gen_s,
                "load_s": load_s, "strength": strength, "seed": seed,
                "saved": str(outpath)}


def main():
    threading.Thread(target=worker, daemon=True).start()
    log(f"portal: http://{HOST}:{PORT}/   (gen -> {GEN})")
    log(f"scratch: {SCRATCH}   fleet: {FLEET_DIR}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
