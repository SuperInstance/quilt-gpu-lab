"""PX0 round 1 — outside-the-box ideation on the patchwork-experts gardener system.

Three DeepInfra lanes, parallel, same brief, distinct angles. No pre-reg needed (this is
design ideation, not measurement) but the output must contain at least one FALSIFIABLE
proposal per lane — doctrine: every ideation lane ends in something the 4050 can test.

Models (Casey's pick, 2026-09-30 16:04): Hermes-3-405B (adversarial epistemics),
Seed-2.0-mini (fast novel cells), tencent Hy3/Hy4-preview (wildcard). Key read at
~/.config/deepinfra/token — never echoed, never logged.
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

TOKEN = open(os.path.expanduser("~/.config/deepinfra/token")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

BRIEF = """You are advising an autonomous GPU agent (RTX 4050 6GB, WSL) in a multi-agent
fleet. It is building "patchwork-experts": a spreadsheet-like canvas where TINY models
(0.3B-4B, run locally) act as judgment/filter cells; a large "gardener" model (GLM-5.3
class, via API) rearranges, wires, and builds new cells, ALWAYS leaving its chain-of-thought
as a receipt per move. Built cells are cataloged for reuse. Related proven results on the
bench: a depth-3 decision tree already beats a linear model 2.4x on tic-tac-toe optimal
play (shallow composition is cheap and powerful); discrete judges are coarse structural
instruments (good at region boundaries, bad at picking individual cells); format-first
gates catch broken generators at zero judgment cost; pinch-to-known-answer fallback works
under total generator failure.

Answer these three, concretely:
1. Design the FIRST falsifiable experiment for the patchwork-experts system. State the
   prediction, the metric, and what result would kill the idea.
2. Name the most likely way this system fails SILENTLY (a failure the receipts would not
   reveal), and the cheapest control that would expose it.
3. Propose ONE cell type nobody would think to build.

Be specific and terse. No preamble."""

ANGLES = [
    (
        "seed_mini",
        "ByteDance/Seed-2.0-mini",
        "Angle: fast ideation. Swing wide on question 3 — novel cell types, weird "
        "representations, cells made of code or files or sensors, not just NN weights.",
        0.9,
    ),
    (
        "hermes_405b",
        "NousResearch/Hermes-3-Llama-3.1-405B",
        "Angle: adversarial epistemics reviewer. Focus on question 2 — how do the "
        "gardener's receipts lie? Where does the patchwork rot: cell decay, threshold "
        "drift, gardeners grading their own homework, cells tuned to past traffic "
        "serving new traffic?",
        0.7,
    ),
    (
        "h3_wildcard",
        "tencent/Hy3-preview",
        "Angle: wildcard. No constraints on your thinking. If the spreadsheet-canvas "
        "metaphor is wrong, say what the right metaphor is.",
        0.8,
    ),
]

# Fallbacks if a model id 404s (roster drift).
FALLBACK = {
    "h3_wildcard": ["tencent/Hy4-preview", "tencent/Hunyuan-13B-Instruct"],
    "hermes_405b": ["NousResearch/Hermes-3-Llama-3.1-70B-Turbo"],
    "seed_mini": ["ByteDance/Seed-2.0-pro"],
}


def call(name, model, angle, temp):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": angle},
            {"role": "user", "content": BRIEF},
        ],
        "max_tokens": 900,
        "temperature": temp,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            out = json.loads(r.read())
        return {
            "lane": name,
            "model": model,
            "ok": True,
            "secs": round(time.time() - t0, 1),
            "text": out["choices"][0]["message"]["content"],
            "usage": out.get("usage", {}),
        }
    except urllib.error.HTTPError as e:
        return {"lane": name, "model": model, "ok": False, "error": f"HTTP {e.code}: {e.read()[:200]}"}
    except Exception as e:
        return {"lane": name, "model": model, "ok": False, "error": repr(e)}


def main():
    results = []
    with ThreadPoolExecutor(3) as ex:
        futs = [ex.submit(call, *a) for a in ANGLES]
        for f in futs:
            results.append(f.result())

    # One fallback retry per failed lane (different model id, same angle).
    for i, r in enumerate(results):
        if not r["ok"] and r["lane"] in FALLBACK:
            fb = FALLBACK[r["lane"]][0]
            print(f"lane {r['lane']} failed on {r['model']} ({r['error'][:80]}), retrying with {fb}", flush=True)
            results[i] = call(r["lane"], fb, ANGLES[i][2], ANGLES[i][3])

    outdir = os.path.expanduser("~/projects/quilt-gpu-lab/results/px0_ideation")
    os.makedirs(outdir, exist_ok=True)
    lines = [
        "# PX0 round 1 — patchwork-experts gardener: three-lane ideation",
        f"# fired 2026-09-30 ~16:0x AKDT; lanes: " + ", ".join(a[0] for a in ANGLES),
        "",
    ]
    for r in results:
        lines.append(f"## {r['lane']} — {r['model']}  (ok={r['ok']}" + (f", {r.get('secs')}s)" if r['ok'] else f", ERROR: {r.get('error','')[:300]})"))
        if r["ok"]:
            lines.append(r["text"])
        lines.append("")
    out = os.path.join(outdir, "round1.md")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    print("wrote", out)
    for r in results:
        print(f"[{r['lane']}] ok={r['ok']} model={r['model']}")


if __name__ == "__main__":
    main()
