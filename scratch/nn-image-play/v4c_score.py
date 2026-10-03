#!/usr/bin/env python3
"""V4 E2/E3/E4 scoring — perception (anchor-relative targets), claims, JEV, montage."""
import base64, json, time, urllib.request, pathlib
import torch
from transformers import CLIPModel, CLIPProcessor
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
PNG = pathlib.Path("/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png")
OLLAMA = "http://127.0.0.1:11434/api/generate"
SUBJECTS = ("lucineer", "casey", "jev", "mmx")
DIALS = ["mood", "warmth", "complexity", "machine_vs_organic", "colorfulness"]
JEV_Q = {
    "lucineer": {"question": "Does this description clearly indicate a machine-like robot character rather than a human?",
                 "instructions": "Answer true only if the description unambiguously refers to a robot/machine figure."},
    "casey": {"question": "Does this description clearly indicate a human adventurer character rather than a robot?",
              "instructions": "Answer true only if the description unambiguously refers to a human figure."},
    "jev": {"question": "Does this description clearly indicate a machine-like or abstract computational figure rather than a human?",
            "instructions": "Answer true only if the description unambiguously refers to a machine/abstract figure."},
    "mmx": {"question": "Does this description clearly indicate a colorful playful cartoon figure?",
            "instructions": "Answer true only if the description unambiguously refers to a colorful cartoon-style figure."},
}
def log(*a): print(*a, flush=True)

def edge_bin(p, t=100, size=512):
    img = Image.open(p).convert("L").resize((size, size))
    e = ImageOps.invert(img.filter(ImageFilter.FIND_EDGES))
    return e.point(lambda v: 255 if v > t else 0)

def drift(gen, src):
    a, b = edge_bin(gen).tobytes(), edge_bin(src).tobytes()
    changed = sum(1 for x, y in zip(a, b) if x != y)
    src_n = sum(1 for v in b if v)
    return round(changed / max(1, src_n), 4)

data = json.loads((HERE / "v4_cands.json").read_text())
cands = data["candidates"]
t0 = time.time()

def ollama(model, prompt, images=None, keep_alive=None):
    body = {"model": model, "prompt": prompt, "stream": False, "options":
            {"temperature": 0, "num_predict": 140, "repeat_penalty": 1.15, "repeat_last_n": 32}}
    if images: body["images"] = images
    if keep_alive is not None: body["keep_alive"] = keep_alive
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    for temp in (0, 0.4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())["response"]
        except urllib.error.HTTPError as e:
            if "repeat limit" in e.read().decode()[:200]:
                body["options"]["temperature"] = temp + 0.3; continue
            raise
    return None
def extract_dials(txt):
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j <= i: return None
    try:
        d = json.loads(txt[i:j+1]); return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError: return None
QT = ('You rate avatar faces from a description. Reply with ONLY strict JSON, integers 0-10: '
      '{"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,"complexity":<0 minimal..10 busy>,'
      '"machine_vs_organic":<0 machine..10 organic>,"colorfulness":<0 monochrome..10 vivid>} '
      'Description: {desc}')

# anchor-relative targets: measure the sources themselves
targets = {}
for s in SUBJECTS:
    b64 = base64.b64encode(open(PNG / f"{s}.png", "rb").read()).decode()
    desc = ollama("moondream", "Describe this avatar face.", images=[b64])
    d = extract_dials(ollama("qwen2.5:3b-instruct-q4_K_M", QT.replace("{desc}", (desc or "")[:200]), keep_alive=0)) if desc else None
    targets[s] = d
    log(f"anchor {s}: {d}")
anchors = {"targets_measured": targets, "source_descs": {}}

clip = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to("cuda").eval()
cproc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
@torch.no_grad()
def embed(p):
    inp = cproc(images=Image.open(p).convert("RGB"), return_tensors="pt").to("cuda")
    f = clip.get_image_features(**inp)
    f = f.pooler_output if hasattr(f, "pooler_output") else f
    return torch.nn.functional.normalize(f, dim=-1)[0]
for a in cands:
    src = PNG / f"{a['init_subject']}.png"
    e0 = embed(str(src))
    a["identity"] = round(torch.nn.functional.cosine_similarity(e0, embed(a["path"]), dim=0).item(), 4)
    a["structure_drift"] = drift(a["path"], str(src))
del clip; torch.cuda.empty_cache()
log(f"identity+drift {round(time.time()-t0,1)}s")

for a in cands:
    b64 = base64.b64encode(open(a["path"], "rb").read()).decode()
    desc = ollama("moondream", "Describe this avatar face.", images=[b64])
    a["desc"] = (desc or "")[:200]
    d = extract_dials(ollama("qwen2.5:3b-instruct-q4_K_M", QT.replace("{desc}", a["desc"]), keep_alive=0)) if desc else None
    a["dials"] = d
log(f"C: {len(cands)} perceived {round(time.time()-t0,1)}s")

# bias per (subject, arm) vs anchor targets
for a in cands:
    td = targets.get(a["subject"])
    if a.get("dials") and td:
        a["anchor_L1"] = round(sum(abs(a["dials"][k] - td[k]) for k in DIALS), 2)
for subj in SUBJECTS:
    arms = sorted({a["arm"] for a in cands if a["subject"] == subj})
    for arm in arms:
        arm_c = [a for a in cands if a["subject"] == subj and a["arm"] == arm and a.get("dials")]
        if not arm_c or not targets.get(subj): continue
        td = targets[subj]
        bias = {k: round(sum(a["dials"][k] - td[k] for a in arm_c) / len(arm_c), 2) for k in DIALS}
        for a in arm_c:
            a["corrected_L1"] = round(sum(abs((a["dials"][k] - td[k]) - bias[k]) for k in DIALS), 2)
            a["corrected_pass"] = a["corrected_L1"] <= 5.0
        anchors[f"bias_{subj}_{arm}"] = bias

def m(a, key): return sum(x[key] for x in a) / len(a)
def sel(subj=None, arm=None):
    return [a for a in cands if (subj is None or a["subject"] == subj) and (arm is None or a["arm"] == arm)]

claims = {}
# E2a drift discrimination
e2a = {}
for subj in SUBJECTS:
    cn_arms = [a for a in sel(subj) if a["arm"].startswith("cn")]
    bs = sel(subj, "base")
    if cn_arms and bs:
        e2a[subj] = {"cn_drift": round(m(cn_arms, "structure_drift"), 4), "base_drift": round(m(bs, "structure_drift"), 4),
                     "pass": m(cn_arms, "structure_drift") < m(bs, "structure_drift")}
claims["E2a"] = {"claim": "cn drift < base per subject", "detail": e2a, "pass": all(v["pass"] for v in e2a.values())}
# E2b machine bias pooled cn (lucineer)
lb = [anchors.get(f"bias_lucineer_{a}") for a in ("cn045", "cn06") if anchors.get(f"bias_lucineer_{a}")]
if lb:
    cn_l = sel("lucineer", "cn045") + sel("lucineer", "cn06")
    pooled = round(sum(a["dials"]["machine_vs_organic"] - targets["lucineer"]["machine_vs_organic"] for a in cn_l) / len(cn_l), 2) if cn_l else None
    claims["E2b"] = {"claim": "|machine bias| <= 5.0 pooled cn lucineer", "pooled_bias": pooled, "pass": pooled is not None and abs(pooled) <= 5.0}
# E3 cross identity must fail
x = sel(arm="xcn06")
claims["E3"] = {"claim": "cross-identity mean identity < 0.80 (gate must refuse morphs)",
                "mean_identity": round(m(x, "identity"), 4) if x else None,
                "identities": {a["name"]: a["identity"] for a in x},
                "pass": bool(x) and m(x, "identity") < 0.80}
# E4 style under structure
e4 = {}
for style in ("water", "neon"):
    cn_a = sel("lucineer", f"{style}_cn06"); bs = sel("lucineer", f"{style}_base")
    if cn_a and bs:
        e4[style] = {"cn_ident": round(m(cn_a, "identity"), 4), "base_ident": round(m(bs, "identity"), 4),
                     "pass_floor": m(cn_a, "identity") >= 0.78, "pass_paired": m(cn_a, "identity") > m(bs, "identity")}
claims["E4"] = {"claim": "cn >= 0.78 AND cn > base per style", "detail": e4,
                "pass": bool(e4) and all(v["pass_floor"] and v["pass_paired"] for v in e4.values())}

survivors = [a for a in cands if a["arm"] != "xcn06" and a.get("corrected_pass") and a["identity"] >= 0.80]
gate_weak = [a for a in sel(arm="xcn06") if a["identity"] >= 0.80]
def typesafe_key():
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith("TYPESAFE_AI_KEY="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("no key")
def jev(a):
    q = JEV_Q[a["subject"]]
    body = {"model": "jev-latest", "state": a["desc"], "questions": {"match": {"type": "noul", **q}}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {typesafe_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r_:
            a["jev"] = json.loads(r_.read()).get("answers", {}).get("match", {})
        log(f"D {a['name']}: noul {a['jev'].get('noul')}")
    except Exception as e:
        a["jev_error"] = str(e)[:120]
for a in survivors + gate_weak:
    jev(a)
accepted = [a["name"] for a in survivors if a.get("jev", {}).get("noul", 0) >= 0.6]

# montage of accepted
if accepted:
    acc = [a for a in cands if a["name"] in accepted][:8]
    cell = 200; W = cell * len(acc); H = cell + 30
    board = Image.new("RGB", (W, H), (18, 18, 24))
    d = ImageDraw.Draw(board)
    for i, a in enumerate(acc):
        im = Image.open(a["path"]).resize((cell - 8, cell - 8))
        board.paste(im, (i * cell + 4, 4))
        d.text((i * cell + 6, cell + 4), a["name"].replace("lucineer_", "luc_")[:26], fill=(200, 200, 210))
    board.save(HERE / "gate_loop" / "v4_montage.png")

e1 = json.loads((HERE / "v4_e1.json").read_text()) if (HERE / "v4_e1.json").exists() else {}
receipt = {"experiment": "image-wave-v4", "prereg": json.loads((HERE / "v4_wave_prereg.json").read_text()),
           "gen_s": data["gen_s"], "total_s": round(time.time() - t0, 1), "anchors": anchors,
           "n_candidates": len(cands), "claims": claims, "E1": {k: e1.get(k) for k in ("spearman", "flip_rate", "claim_E1a_pass", "claim_E1b_pass", "n", "dino_ok")},
           "accepted": accepted, "survivors": [a["name"] for a in survivors], "gate_weak_xarms": [a["name"] for a in gate_weak],
           "candidates": cands}
(HERE / "v4_receipt.json").write_text(json.dumps(receipt, indent=1))
log("CLAIMS " + json.dumps({k: v.get("pass") for k, v in claims.items()}))
if e1: log(f"E1 spearman {e1.get('spearman')} flips {e1.get('flip_rate')} pass {e1.get('claim_E1a_pass')}/{e1.get('claim_E1b_pass')}")
log(f"ACCEPTED {len(accepted)}: {accepted}")
log(f"GATE-WEAK XARMS: {receipt['gate_weak_xarms']}")
