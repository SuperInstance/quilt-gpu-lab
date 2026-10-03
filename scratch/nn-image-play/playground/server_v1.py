#!/usr/bin/env python3
"""PLAYGROUND SERVER — browser face over tonight's local image-cascade.
Runs under the GPU venv:
  /home/eileen/venvs/elephant-gpu/bin/python server.py
Stdlib http.server only (NO flask). Port 8790, bind 0.0.0.0.

Endpoints (JSON):
  GET  /                -> index.html
  POST /api/measure     {png_b64} -> Phase C cascade (moondream -> qwen2.5:3b) {desc,dials}
  POST /api/generate    {png_b64,prompt,strength,seed} -> SD img2img + CLIP cosine
  POST /api/jev         {desc} -> typesafe noul {noul}
  GET  /api/bias        -> {bias_base,bias_push,prompt_steering_effect_machine}

Heavy torch models are loaded LAZILY per phase and unloaded (del + empty_cache)
before the next phase loads: ONE heavy model resident at a time (6GB VRAM law).
/api/measure never holds SD; /api/generate frees SD before CLIP loads.
Every endpoint fails loud as JSON {"error":...} 500; a bad request never kills
the server thread.

Code shapes copied from tonight's verified runs:
  scratch/nn-image-play/identity_loop.py, gate_loop.py, gate_v2.py
  scratch/face-dials/face_dials_v3.py
"""
import base64
import io
import json
import pathlib
import threading
import time
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).parent
INDEX = HERE / "index.html"
GEN = HERE / "gen"
GEN.mkdir(exist_ok=True)

# --- tonight's verified resource paths -------------------------------------
SCRATCH = pathlib.Path("/home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play")
CKPT = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/checkpoints/dreamshaper_8.safetensors"
LCM = "/mnt/c/ProgramData/ASUS/AICreator/sd1.5/lora/lcm.safetensors"
OLLAMA = "http://127.0.0.1:11434/api/generate"
KEYFILE = "/mnt/c/Users/casey/key.txt"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
CLIP_ID = "openai/clip-vit-base-patch32"

HOST, PORT = "0.0.0.0", 8790
DIALS = ["mood", "warmth", "complexity", "machine_vs_organic", "colorfulness"]

# One heavy GPU phase at a time (6GB VRAM law). Serializes SD / CLIP / ollama-vision.
GPU_LOCK = threading.Lock()


# --- helpers ---------------------------------------------------------------
def log(*a):
    print(*a, flush=True)


def strip_b64(s):
    """Accept raw base64 or a data: URL; return raw base64 string."""
    if not isinstance(s, str) or not s:
        raise ValueError("missing base64 image payload")
    if s.startswith("data:"):
        s = s.split(",", 1)[1]
    return s.strip()


def b64_to_bytes(s):
    return base64.b64decode(strip_b64(s))


# --- ollama cascade (verified shape from face_dials_v3 / gate_loop) --------
def ollama(model, prompt, images=None, opts=None, keep_alive=None):
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
    # temp 0 first; on the ollama 'repeat limit' abort, bump temp and retry.
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
            errbody = e.read().decode()[:300]   # THE LESSON: READ THE ERROR BODY
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


def measure(body):
    """Phase C: moondream perceives -> qwen2.5:3b quantizes. No SD resident."""
    b64 = strip_b64(body.get("png_b64"))
    with GPU_LOCK:
        # moondream: perceive (unload when done so nothing lingers into SD phase)
        desc = ollama("moondream", "Describe this avatar face.", images=[b64],
                      opts={"temperature": 0}, keep_alive=0)
        desc = (desc or "").strip()
        if not desc:
            raise RuntimeError("moondream returned empty description")
        # qwen: quantize (keep_alive=0 so the model frees after the call)
        dials = extract_dials(ollama(
            "qwen2.5:3b-instruct-q4_K_M", QUANTIZE.replace("{desc}", desc),
            opts={"temperature": 0}, keep_alive=0))
        if dials is None:
            raise RuntimeError("qwen did not return valid dial JSON")
    return {"desc": desc, "dials": dials}


def generate(body):
    """SD img2img (DreamShaper8 + LCM LoRA, 6 steps, guidance 1.3) then
    CLIP identity cosine vs the input face. SD is freed before CLIP loads."""
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
        # ---- Phase A: SD + LCM img2img (the only heavy model resident) ----
        t0 = time.time()
        pipe = StableDiffusionImg2ImgPipeline.from_single_file(
            CKPT, torch_dtype=torch.float16, safety_checker=None)
        pipe.load_lora_weights(LCM)
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        pipe.to("cuda")
        pipe.enable_attention_slicing()
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
        torch.cuda.empty_cache()          # free SD before CLIP loads

        # ---- Phase B: CLIP identity cosine (input face vs output) ----
        clip = CLIPModel.from_pretrained(
            CLIP_ID, local_files_only=True).to("cuda").eval()
        proc = CLIPProcessor.from_pretrained(CLIP_ID, local_files_only=True)

        @torch.no_grad()
        def embed(im):
            inp = proc(images=im, return_tensors="pt").to("cuda")
            f = clip.get_image_features(**inp)
            f = f.pooler_output if hasattr(f, "pooler_output") else f
            return torch.nn.functional.normalize(f, dim=-1)[0]

        cosine = round(torch.nn.functional.cosine_similarity(
            embed(init), embed(out), dim=0).item(), 4)
        del clip, proc
        torch.cuda.empty_cache()

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return {"image_b64": base64.b64encode(buf.getvalue()).decode(),
            "identity_cosine": cosine, "gen_s": gen_s,
            "load_s": load_s, "strength": strength, "seed": seed,
            "saved": str(outpath)}


def typesafe_key():
    for line in open(KEYFILE):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("TYPESAFE_AI_KEY not found in key.txt")


def jev(body):
    desc = (body.get("desc") or "").strip()
    if not desc:
        raise ValueError("missing desc")
    req_body = {
        "model": "jev-latest",
        "state": desc,
        "questions": {"robot": {
            "type": "noul",
            "question": ("Does this description clearly indicate a machine-like "
                         "robot character rather than a human?"),
            "instructions": ("Answer true only if the description unambiguously "
                             "refers to a robot/machine figure.")}},
    }
    req = urllib.request.Request(
        TYPESAFE_URL, data=json.dumps(req_body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {typesafe_key()}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())

    # noul may arrive under answers.robot or results.robot (both seen tonight)
    noul = None
    for path in (("answers", "robot", "noul"), ("results", "robot", "noul")):
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


def _find_receipt(name):
    p = SCRATCH / name
    if p.exists():
        return p
    hits = sorted(SCRATCH.rglob(name))
    return hits[-1] if hits else None


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
        out["arms"] = d.get("arms")
        out["source_v2"] = str(v2)
    if v0 is not None:
        d = json.loads(v0.read_text())
        if out["bias_base"] is None:
            out["bias_base"] = d.get("bias")   # v1 receipt key
        out["source_v0"] = str(v0)
    return out


# --- HTTP ------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "QuiltPlayground/1.0"

    def log_message(self, fmt, *a):
        log("[http]", self.address_string(), fmt % a)

    def _send(self, code, payload, ctype="application/json"):
        data = (json.dumps(payload).encode()
                if ctype.startswith("application/json") else payload)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
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
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                if not INDEX.exists():
                    self._send(500, {"error": "index.html missing"})
                    return
                self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/bias":
                self._send(200, bias_sheet())
            elif path == "/api/health":
                self._send(200, {"ok": True})
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
            if path == "/api/measure":
                self._send(200, measure(body))
            elif path == "/api/generate":
                self._send(200, generate(body))
            elif path == "/api/jev":
                self._send(200, jev(body))
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})


def main():
    log(f"playground: http://{HOST}:{PORT}/   (gen -> {GEN})")
    log(f"scratch: {SCRATCH}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
