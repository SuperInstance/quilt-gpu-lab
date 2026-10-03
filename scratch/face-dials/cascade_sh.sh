#!/bin/bash
# FACE-DIALS V1 via curl (urllib 500s on this ollama rc; curl never does)
# usage: cascade_sh.sh TRIALS FACE [FACE...]
set -u
TRIALS=$1; shift
PNG=/home/eileen/projects/dicebear-quilt/quilt/play-2026-10-02/png
OUT=/home/eileen/projects/quilt-gpu-lab/scratch/face-dials
PERCEIVE="Describe this avatar face in 3 short sentences: its mood, how friendly it seems, how busy the design is, whether it looks like a machine or a living creature, and how colorful it is."
QT='You rate avatar faces from a description. Reply with ONLY strict JSON, integers 0-10: {"mood":<0 gloomy..10 joyful>,"warmth":<0 cold..10 friendly>,"complexity":<0 minimal..10 busy>,"machine_vs_organic":<0 machine..10 organic>,"colorfulness":<0 monochrome..10 vivid>} Description: DESC'
: > "$OUT/cascade_raw.jsonl"
for trial in $(seq 1 "$TRIALS"); do
  for face in "$@"; do
    b64=$(base64 -w0 "$PNG/$face.png")
    desc=$(curl -s --max-time 120 http://127.0.0.1:11434/api/generate \
      -d "{\"model\":\"moondream\",\"prompt\":\"$PERCEIVE\",\"images\":[\"$b64\"],\"stream\":false,\"options\":{\"temperature\":0,\"num_predict\":140}}" \
      | python3 -c "import json,sys;print(json.load(sys.stdin)['response'].strip())")
    qt=${QT/DESC/"$desc"}
    quant=$(curl -s --max-time 120 http://127.0.0.1:11434/api/generate \
      -d "{\"model\":\"qwen2.5:3b-instruct-q4_K_M\",\"prompt\":\"$qt\",\"stream\":false,\"options\":{\"temperature\":0,\"num_predict\":140}}" \
      | python3 -c "import json,sys;print(json.load(sys.stdin)['response'].strip())")
    python3 -c "
import json,sys
face,trial,desc,quant=sys.argv[1:5]
i,j=quant.find('{'),quant.rfind('}')
try: d=json.loads(quant[i:j+1])
except Exception: d=None
print(json.dumps({'face':face,'trial':int(trial),'dials':d,'desc':desc[:220]}))
" "$face" "$trial" "$quant-placeholder" "$desc" >> /dev/null 2>&1 # placeholder guard
    python3 - "$face" "$trial" "$desc" "$quant" >> "$OUT/cascade_raw.jsonl" <<'PYEOF'
import json, sys
face, trial, desc, quant = sys.argv[1:5]
i, j = quant.find('{'), quant.rfind('}')
try:
    d = json.loads(quant[i:j+1])
except Exception:
    d = None
print(json.dumps({"face": face, "trial": int(trial), "dials": d, "desc": desc[:220]}))
PYEOF
    echo "$face t$trial -> $(echo "$quant" | head -c 80)"
  done
done
echo "=== ANALYSIS ==="
python3 - <<'PYEOF'
import json, collections
rows = [json.loads(l) for l in open("/home/eileen/projects/quilt-gpu-lab/scratch/face-dials/cascade_raw.jsonl")]
DIALS = ["mood","warmth","complexity","machine_vs_organic","colorfulness"]
by = collections.defaultdict(list)
for r in rows:
    if r["dials"]: by[r["face"]].append(r["dials"])
meds = {}
for f, ds in by.items():
    med = {k: sorted(d[k] for d in ds)[len(ds)//2] for k in DIALS if all(k in d for d in ds)}
    spread = {k: max(d[k] for d in ds) - min(d[k] for d in ds) for k in med}
    meds[f] = med
    print(f"{f}: median {med} spread {spread}")
if len(meds) >= 2:
    seps = {k: len({m[k] for m in meds.values()}) for k in DIALS if all(k in m for m in meds.values())}
    print(f"SEPARATION: {seps}")
json.dump(meds, open("/home/eileen/projects/quilt-gpu-lab/scratch/face-dials/facedials-v1.json","w"), indent=1)
PYEOF
