#!/usr/bin/env python3
"""FACE-DIALS V2 — the cascade, done right.
v0: VLM echoed JSON template (scaffold lesson). v1 infra: 500s were ollama
repeat-abort bodies we never read (READ THE ERROR BODY). v2: repeat_penalty
breaks greedy loops; retry w/ temp bump; proper desc plumbing; keep_alive=0
on quantizer. Cascade: moondream PERCEIVES -> qwen2.5:3b QUANTIZES.
"""
import base64, json, time, urllib.request, urllib.error, pathlib

OLLAMA = "http://127.0.0.1:11434/api/generate"
PNG_DIR = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
HERE = pathlib.Path(__file__).parent
FACES = ["casey", "lucineer", "jev", "wesley", "zeroclaw"]
TRIALS = 3
DIALS = ["mood", "warmth", "complexity", "machine_vs_organic", "colorfulness"]
PERCEIVE = ("Describe this avatar face in 3 short sentences: its mood, how friendly "
            "it seems, how busy the design is, whether it looks like a machine or a "
            "living creature, and how colorful it is.")
QUANTIZE = (
    "You rate avatar faces from a description. Reply with ONLY strict JSON, integers 0-10:\n"
    '{"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,'
    '"complexity":<0 minimal..10 busy>,"machine_vs_organic":<0 machine..10 organic>,'
    '"colorfulness":<0 monochrome..10 vivid>}\n'
    "Description: {desc}"
)

def gen(model, prompt, images=None, opts=None):
    body = {"model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "num_predict": 140,
                        "repeat_penalty": 1.15, "repeat_last_n": 32}}
    if opts: body["options"].update(opts)
    if images: body["images"] = images
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())["response"]
    except urllib.error.HTTPError as e:
        errbody = e.read().decode()[:200]   # THE LESSON: read the body
        if "repeat limit" in errbody:
            return None                      # caller retries w/ temp bump
        raise RuntimeError(f"ollama {e.code}: {errbody}")

def perceive(png_b64):
    for temp in (0, 0.3, 0.5):
        r = gen("moondream", PERCEIVE, images=[png_b64], opts={"temperature": temp})
        if r and r.strip(): return r.strip(), temp
    return None, -1

def quantize(desc):
    r = gen("qwen2.5:3b-instruct-q4_K_M", QUANTIZE.replace("{desc}", desc),
            opts={"temperature": 0})
    if not r: return None
    i, j = r.find("{"), r.rfind("}")
    if i < 0 or j <= i: return None
    try:
        d = json.loads(r[i:j+1])
        return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError:
        return None

def main():
    out = {"cascade": "moondream->qwen2.5:3b", "repeat_penalty": 1.15, "trials": TRIALS, "faces": {}}
    # PHASE A: all perception (one model resident)
    descs = []
    for face in FACES:
        b64 = base64.b64encode((PNG_DIR / f"{face}.png").read_bytes()).decode()
        for t in range(TRIALS):
            desc, temp = perceive(b64)
            descs.append((face, desc, temp))
            print(f"A {face} t{t}: temp_used={temp} desc={'' if not desc else desc[:70]}")
            time.sleep(0.5)
    # PHASE B: all quantization (other model resident, keep_alive=0)
    by_face = {f: [] for f in FACES}
    for face, desc, temp in descs:
        d = quantize(desc) if desc else None
        by_face[face].append({"dials": d, "desc": desc})
        time.sleep(0.3)
    for face in FACES:
        oks = [r["dials"] for r in by_face[face] if r["dials"]]
        if not oks:
            print(f"FACE {face}: 0 quantized"); continue
        spread = {k: max(d[k] for d in oks) - min(d[k] for d in oks) for k in DIALS}
        median = {k: sorted(d[k] for d in oks)[len(oks)//2] for k in DIALS}
        out["faces"][face] = {"reads": by_face[face], "spread": spread,
                              "median_dials": median, "desc": by_face[face][0]["desc"]}
        print(f"FACE {face}: q{len(oks)}/{TRIALS} spread {spread} median {median}")
    meds = {f: v["median_dials"] for f, v in out["faces"].items() if "median_dials" in v}
    if len(meds) >= 2:
        seps = {k: len({m[k] for m in meds.values()}) for k in DIALS}
        out["separation_distinct_values"] = seps
        print(f"SEPARATION across {len(meds)} faces: {seps}")
    (HERE / "facedials-v2.json").write_text(json.dumps(out, indent=1))
    print("receipt: facedials-v2.json")

if __name__ == "__main__":
    main()
