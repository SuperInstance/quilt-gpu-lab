"""PX0 round 1 addendum — H3 wildcard lane re-fire.

Round 1 notes: tencent/Hy3-preview 404s; correct DeepInfra id is `tencent/Hy3`
(verified against the /v1/openai/models list, 187 models). Hy4-preview exists but was
429 engine_overloaded. Firing Hy3 now; Hy4 kept as fallback.
"""
import json, os, urllib.request, urllib.error
from px0_ideation_round1 import ANGLES, call

angle, model, temp = None, None, None
for name, m, a, t in ANGLES:
    if name == "h3_wildcard":
        model, angle, temp = m, a, t
        break

# angle is the system prompt; strip the old model name from ANGLES entry mismatch.
for name, m, a, t in ANGLES:
    if name == "h3_wildcard":
        angle = a

r = call("h3_wildcard", "tencent/Hy3", angle, temp)
if not r["ok"]:
    print("Hy3 failed:", r.get("error", "")[:200])
    r = call("h3_wildcard", "tencent/Hy4-preview", angle, temp)

out = os.path.expanduser("~/projects/quilt-gpu-lab/results/px0_ideation/round1.md")
with open(out, "a") as f:
    f.write(f"\n## h3_wildcard — {r['model']}  (ok={r['ok']}, addendum re-fire"
            + (f", {r.get('secs')}s)" if r["ok"] else f", ERROR: {r.get('error','')[:300]})") + "\n")
    if r["ok"]:
        f.write(r["text"] + "\n")
print("appended", out, "| ok =", r["ok"], "| model =", r["model"])
if r["ok"]:
    print(r["text"][:400])
