import json, subprocess
rec = json.load(open("/home/eileen/projects/quilt-gpu-lab/scratch/nn-image-play/gate_loop/v2/gate_v2_receipt.json"))
pairs = [(c["desc"], c["dials"]) for c in rec["candidates"] if c.get("dials") and c.get("desc")][:6]
LT = ('Classify this avatar description. Reply with ONLY strict JSON using exactly one word per value: '
      '{"mood":"gloomy" or "joyful","warmth":"cold" or "friendly","complexity":"minimal" or "busy",'
      '"machine_vs_organic":"machine" or "organic","colorfulness":"monochrome" or "vivid"} '
      'Description: {desc}')
def ask(p):
    r = subprocess.run(["ollama","run","lfm2.5:230m",p], capture_output=True, text=True, timeout=120)
    return r.stdout.strip()
def parse(t):
    i,j = t.find("{"), t.rfind("}")
    if i<0 or j<=i: return None
    try: return json.loads(t[i:j+1])
    except json.JSONDecodeError: return None
POLES = {"mood":("gloomy","joyful"),"warmth":("cold","friendly"),"complexity":("minimal","busy"),
         "machine_vs_organic":("machine","organic"),"colorfulness":("monochrome","vivid")}
ok=tot=agree=axes=0
for desc, ref in pairs:
    d = parse(ask(LT.replace("{desc}", desc[:300]))); tot += 1
    if d and isinstance(d, dict):
        keys_ok = all(k in d for k in POLES)
        if keys_ok:
            ok += 1
            for k,(lo,hi) in POLES.items():
                v = str(d[k]).strip().lower().strip('"')
                pred = 0 if v==lo else (10 if v==hi else None)
                if pred is not None:
                    axes += 1
                    if (ref[k] >= 5) == (pred == 10): agree += 1
print(f"valid-label-JSON: {ok}/{tot} | pole agreement: {agree}/{axes}")
