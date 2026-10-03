#!/usr/bin/env python3
"""FACE-DIALS V1: local two-model cascade.
S-A moondream PERCEIVES (natural-language description, no JSON scaffold)
S-B qwen2.5:3b QUANTIZES (text -> strict JSON dials)
v0 lesson: 1.8B VLM echoes bare JSON templates with zeros -> never scaffold
the output format into the perceiver's prompt. Cascade: describe, then rate.
"""
import base64, json, sys, urllib.request, pathlib

OLLAMA = "http://127.0.0.1:11434/api/generate"
PNG_DIR = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
FACES = sys.argv[1:] or ["casey", "lucineer", "jev", "wesley", "zeroclaw"]
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

def gen(model, prompt, images=None, num_predict=140, tries=3):
    import time
    body = {"model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "num_predict": num_predict}}
    if images: body["images"] = images
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["response"]
        except urllib.error.HTTPError as e:
            last = e; time.sleep(3 * (t + 1))
    raise last

def extract_json(txt):
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i: return None
    try:
        d = json.loads(txt[i:j+1])
        return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError:
        return None

def main():
    out = {"cascade": "moondream->qwen2.5:3b", "temp": 0, "trials": 3, "faces": {}}
    # PHASED to respect 6GB VRAM: all moondream (perceive) first, then all qwen (quantize).
    # Both models resident simultaneously 500s on this box.
    descs = []
    for face in FACES:
        b64 = base64.b64encode((PNG_DIR / f"{face}.png").read_bytes()).decode()
        for _ in range(3):
            descs.append((face, gen("moondream", PERCEIVE, images=[b64]).strip()))
        print(f"perceived {face}")
    reads_by_face = {f: [] for f in FACES}
    for face, desc in descs:
        d = extract_json(gen("qwen2.5:3b-instruct-q4_K_M", QUANTIZE.replace("{desc}", desc)))
        reads_by_face[face].append({"dials": d, "desc": desc[:260]})
    for face in FACES:
        reads = reads_by_face[face]
        oks = [r["dials"] for r in reads if r["ok" if False else "dials"] is not None]
        if not oks:
            print(f"FACE {face}: 0/3 quantized"); out["faces"][face] = reads; continue
        spread = {k: max(d[k] for d in oks) - min(d[k] for d in oks) for k in DIALS}
        median = {k: sorted(d[k] for d in oks)[len(oks)//2] for k in DIALS}
        stable = {k: spread[k] == 0 for k in DIALS}
        out["faces"][face] = {"reads": reads, "spread": spread, "median_dials": median,
                              "stable": stable, "reading": reads[0]["desc"][:120]}
        print(f"FACE {face}: quantized {len(oks)}/3 | stable {sum(stable.values())}/5 | median {median}")
        print(f"   desc: {reads[0]['desc'][:150]}")
    meds = {f: v["median_dials"] for f, v in out["faces"].items() if "median_dials" in v}
    if len(meds) >= 2:
        seps = {k: len({m[k] for m in meds.values()}) for k in DIALS}
        print(f"SEPARATION distinct-per-dial across {len(meds)} faces: {seps}")
        out["separation_distinct_values"] = seps
    pathlib.Path(__file__).parent.joinpath("facedials-v1.json").write_text(json.dumps(out, indent=1))
    print("receipt: facedials-v1.json")

if __name__ == "__main__":
    main()
