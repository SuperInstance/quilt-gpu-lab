#!/usr/bin/env python3
"""FACE-DIALS V0: can a tiny local VLM (moondream) MEASURE dicebear faces?
Three questions, one script:
  Q1 STABILITY  — same face+prompt at temp0 x3: how identical are the dials?
  Q2 SEPARATION — do different faces get different dials (instrument not noise)?
  Q3 CLAIMS     — do measured dials match the style's authored claim?
Usage: face_dials_v0.py [png ...]  (default: 5 crew faces)
"""
import base64, json, sys, urllib.request, pathlib, collections

OLLAMA = "http://127.0.0.1:11434/api/generate"
PNG_DIR = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
FACES = sys.argv[1:] or ["casey", "lucineer", "jev", "wesley", "zeroclaw"]
DIALS = ["mood", "warmth", "complexity", "machine_vs_organic", "colorfulness"]
PROMPT = (
    "Look at this avatar face. Rate it on 5 dials, each an integer 0-10:\n"
    "mood (0 gloomy .. 10 joyful), warmth (0 cold .. 10 friendly), "
    "complexity (0 minimal .. 10 busy), machine_vs_organic (0 machine .. 10 organic), "
    "colorfulness (0 monochrome .. 10 vivid).\n"
    'Reply with ONLY strict JSON: {"mood":n,"warmth":n,"complexity":n,'
    '"machine_vs_organic":n,"colorfulness":n,"reading":"<six words max>"}'
)
STYLE_CLAIMS = {  # authored claims from dicebear style docs — Q3 referee
    "casey": "friendly human adventurer, casual", "lucineer": "friendly robot, techy",
    "jev": "robot judge, stern", "wesley": "young human, eager",
    "zeroclaw": "retro pixel creature, playful",
}

def ask(png_path: pathlib.Path) -> str:
    b64 = base64.b64encode(png_path.read_bytes()).decode()
    body = json.dumps({"model": "moondream", "prompt": PROMPT, "images": [b64],
                       "stream": False, "options": {"temperature": 0, "num_predict": 120}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["response"]

def parse(txt: str):
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(txt[i:j + 1])
        return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError:
        return None

def main():
    out = {"model": "moondream", "temp": 0, "trials": 3, "faces": {}}
    for face in FACES:
        png = PNG_DIR / f"{face}.png"
        if not png.exists():
            print(f"SKIP {face} (no png)"); continue
        reads = []
        for t in range(3):
            raw = ask(png); d = parse(raw)
            reads.append({"ok": d is not None, "dials": d, "raw": raw[:300]})
        oks = [r["dials"] for r in reads if r["ok"]]
        if not oks:
            print(f"FACE {face}: 0/3 parseable"); out["faces"][face] = reads; continue
        stability = {k: len({d[k] for d in oks}) == 1 for k in DIALS}  # all-3-identical?
        spread = {k: max(d[k] for d in oks) - min(d[k] for d in oks) for k in DIALS}
        median = {k: sorted(d[k] for d in oks)[len(oks) // 2] for k in DIALS}
        out["faces"][face] = {"reads": reads, "stability_all3identical": stability,
                              "spread": spread, "median_dials": median,
                              "reading": oks[0].get("reading", "")}
        print(f"FACE {face}: parse {len(oks)}/3 | stable {sum(stability.values())}/5 dials | "
              f"spread {spread} | median {median}")
    # Q2 cross-face separation on medians
    meds = {f: v["median_dials"] for f, v in out["faces"].items() if "median_dials" in v}
    if len(meds) >= 2:
        seps = {k: len({m[k] for m in meds.values()}) for k in DIALS}
        print(f"SEPARATION distinct-values-per-dial across {len(meds)} faces: {seps}")
        out["separation_distinct_values"] = seps
    pathlib.Path(__file__).parent.joinpath("facedials-v0.json").write_text(json.dumps(out, indent=1))
    print(f"receipt: {__file__.rsplit('/',1)[0]}/facedials-v0.json")

if __name__ == "__main__":
    main()
