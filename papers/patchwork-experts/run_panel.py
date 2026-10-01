"""Expert review panel for paper-v0 (patchwork-experts). Three roles, three models."""
import json
import os
import time
import urllib.request

BASE = os.path.expanduser("~/projects/quilt-gpu-lab/papers/patchwork-experts")
OUT = os.path.join(BASE, "reviews")
os.makedirs(OUT, exist_ok=True)
paper = open(os.path.join(BASE, "paper-v0.md")).read()

DI = "https://api.deepinfra.com/v1/openai/chat/completions"
DS = "https://api.deepseek.com/chat/completions"
REVIEWERS = [
    ("hermes_adversarial", DI, "NousResearch/Hermes-3-Llama-3.1-405B",
     os.path.expanduser("~/.config/deepinfra/token"),
     "adversarial methods reviewer. Attack every claim: find overclaims, unsupported leaps, "
     "missing controls, places the microcosm result would NOT generalize, and any claim stated "
     "more strongly than the receipts allow."),
    ("deepseek_stats", DS, "deepseek-chat",
     os.path.expanduser("~/.config/deepseek/token"),
     "statistics and methods reviewer. Check: numbers consistency across sections, CI and variance "
     "usage, baseline fairness (same representation/split everywhere?), branch-ruling honesty "
     "(do the frozen branches match the conclusions?), multiple-comparison and post-hoc-selection "
     "risks, and whether the blind-control correction is handled correctly."),
    ("seed_novelty", DI, "ByteDance/Seed-2.0-mini",
     os.path.expanduser("~/.config/deepinfra/token"),
     "fresh-reader reviewer. Would a first-time reader follow it? State the paper's contribution "
     "in one sentence as YOU understand it, then flag every place the draft loses the thread, "
     "buries the lede, or uses jargon before defining it. Rate novelty 1-10 with one line why."),
]


def review(name, url, model, keyfile, role):
    key = open(keyfile).read().strip()
    prompt = (
        f"You are an expert peer reviewer of a preprint draft. Your assigned role: {role}\n"
        "Return exactly these sections:\n"
        "VERDICT: accept | minor revision | major revision\n"
        "TOP CRITIQUES: the 5 most important, each tied to a specific section\n"
        "CONSISTENCY: any factual or internal-consistency problems detectable from the text alone\n"
        "ONE CHANGE: the single change that would most improve the paper\n"
        "Be specific and blunt. Do not praise. Do not summarize the paper back at me.\n\n"
        f"DRAFT:\n{paper}"
    )
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read().decode())
    dt = round(time.time() - t0, 1)
    text = data["choices"][0]["message"]["content"]
    out = os.path.join(OUT, f"review_{name}.md")
    with open(out, "w") as f:
        f.write(f"# Review — {name} ({model})\n\nlatency: {dt}s\n\n{text}\n")
    print(f"{name}: {dt}s -> {out} ({len(text)} chars)", flush=True)


if __name__ == "__main__":
    for spec in REVIEWERS:
        try:
            review(*spec)
        except Exception as e:
            print(f"{spec[0]}: FAILED {type(e).__name__}: {e}", flush=True)
            with open(os.path.join(OUT, f"review_{spec[0]}.md"), "w") as f:
                f.write(f"# Review — {spec[0]} FAILED\n\n{type(e).__name__}: {e}\n")
