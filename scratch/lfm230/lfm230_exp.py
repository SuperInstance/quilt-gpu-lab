import json, subprocess, pathlib
# reference pairs: moondream desc -> qwen-3b dials, from tonight's gate loops
rec = json.load(open("/home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play/gate_loop/v2/gate_v2_receipt.json"))
pairs = [(c["desc"], c["dials"]) for c in rec["candidates"] if c.get("dials") and c.get("desc")][:6]
DIALS = ["mood","warmth","complexity","machine_vs_organic","colorfulness"]
QT = ('You rate avatar faces from a description. Reply with ONLY strict JSON, integers 0-10: '
      '{"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,"complexity":<0 minimal..10 busy>,'
      '"machine_vs_organic":<0 machine..10 organic>,"colorfulness":<0 monochrome..10 vivid>} '
      'Description: {desc}')
def ask(model, prompt):
    r = subprocess.run(["ollama","run",model,prompt], capture_output=True, text=True, timeout=120)
    return r.stdout.strip()
def parse(t):
    i,j = t.find("{"), t.rfind("}")
    if i<0 or j<=i: return None
    try:
        d = json.loads(t[i:j+1]); return d if all(k in d for k in DIALS) else None
    except json.JSONDecodeError: return None
ok = tot = 0; l1s = []; raw_first = []
for desc, ref in pairs:
    out = ask("lfm2.5:230m", QT.replace("{desc}", desc[:300])); tot += 1
    d = parse(out)
    if len(raw_first) < 2: raw_first.append(out[:150])
    if d:
        ok += 1
        l1 = sum(abs(int(d[k])-ref[k]) for k in DIALS)
        l1s.append(l1)
print(f"valid-JSON: {ok}/{tot}")
if l1s: print(f"per-face L1 vs qwen-3b: {l1s} mean {sum(l1s)/len(l1s):.1f}")
print("raw sample 0:", json.dumps(raw_first[0])[:200])
print("raw sample 1:", json.dumps(raw_first[1])[:200])
