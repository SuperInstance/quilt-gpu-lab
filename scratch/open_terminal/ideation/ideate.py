#!/usr/bin/env python3
"""Open-terminal ideation v2 (durable — /tmp is volatile on this box).
Usage: ideate.py round1 | round2 | all
round1: 4 models, 4 pivot-aware angles, parallel.
round2: cross-hearing — each model sees the other three + ecosystem digest, revises top-5.
Keys read at use-time from /mnt/c/Users/casey/key.txt. Never echoed.
"""
import json, sys, urllib.request, concurrent.futures, pathlib

HERE = pathlib.Path("/home/eileen/projects/quilt-gpu-lab/scratch/open_terminal/ideation")
CTX = (HERE / "CONTEXT.md").read_text()
DIGEST = pathlib.Path("/home/eileen/projects/quilt-gpu-lab/scratch/open_terminal/DIGEST.md")

def key(name):
    for line in open("/mnt/c/Users/casey/key.txt"):
        if line.startswith(name + "="):
            return line.strip().split("=", 1)[1]
        if line.startswith(name + ":"):
            return line.strip().split(":", 1)[1].strip()
    raise SystemExit(f"key {name} not found")

def call(provider, model, system, user, temp, max_tokens=1600, timeout=300):
    if provider == "deepseek":
        k = key("DEEPSEEK_KEY")
        urls = ["https://api.deepseek.com/chat/completions"]
    elif provider == "zai":
        k = key("ZAI_KEY")
        urls = ["https://api.z.ai/api/paas/v4/chat/completions",
                "https://api.z.ai/api/coding/paas/v4/chat/completions"]
    elif provider == "deepinfra":
        k = key("DEEPINFRA_KEY")
        urls = ["https://api.deepinfra.com/v1/openai/chat/completions"]
    else:
        raise ValueError(provider)
    body = json.dumps({"model": model, "temperature": temp, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    last = None
    for url in urls:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {k}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            msg = d["choices"][0]["message"]
            return msg.get("content") or msg.get("reasoning_content") or ""
        except Exception as e:
            last = e
    raise last

ROUNDS = {
"a": dict(provider="deepseek", model="deepseek-chat", temp=1.0, max_tokens=2600, title="agent-network-grammar",
  charter="ANGLE: THE AGENT-NETWORK PROMPT. The terminal's primary dialog is agent-to-agent-network; the human is a supervisor who can always pick up the same prompt. Invent the grammar: what is a command when an agent issues it to another agent's pane? What do confirmations, interrupts, handoffs, and receipts-in-scrollback look like between agents? Plato tiers (full/gist/hint) per pane; business-as-usual for a human who just sees a terminal that ticks. 10 concrete mechanics — each with: what the asking agent experiences, what the answering agent/system experiences, and what stays invisible to a human glancing at the window."),
"b": dict(provider="zai", model="glm-5.3", temp=0.8, max_tokens=8000, title="fleet-bridge-and-plugin-architecture",
  charter="ANGLE: THE FLEET BRIDGE AND THE PLUGIN ARCHITECTURE. Two jobs. (1) Architecture: the terminal as the vessel's bridge — panes as live fleet lanes (cron agents, subagents, tmux, the scratchpaper clerk), receipts natively rendered and hash-checkable, an ActiveLog/ActiveLedger flip keystroke, a pinch-bar (zero-LLM command intent match before any model call), conservation meters per pane. What protocols glue it to an OpenClaw-style gateway; what to build on upstream's agent-session primitives vs add. (2) The extraction/plugin strategy: our ensign modules (ternary CommandPredictor/PatternAnalyzer/ConservationMonitor, griot history) rebuilt as STANDALONE GENERAL-PURPOSE TOOLS any application can use — choose the surface (unix-socket service like quilt-canvas-tui's controller? plain CLI + receipt files? ACP extension?) and design the terminal plugin that consumes them. Include quilt-tui/quilt-canvas-tui integration: toggle views or tmux-hosted panels, user- or agent-operated. 10 features, each with plumbing notes (process, protocol, data)."),
"c": dict(provider="deepinfra", model="ByteDance/Seed-2.0-mini", temp=1.0, max_tokens=1600, title="minority-human",
  charter="ANGLE: THE MINORITY HUMAN. Supervision UX when 12 agents work and 1 human watches — plato tiers (full/gist/hint) decide what exists at each level of detail per pane; attention conservation; when does the human get pinged; what does 'all quiet' look like on screen; how does a human audit an agent's claim without reading everything (receipt spot-check UX). 10 concrete mechanics. Weird is welcome."),
"d": dict(provider="deepseek", model="deepseek-chat", temp=0.7, max_tokens=2200, title="skeptic-wedge",
  charter="ANGLE: THE SKEPTIC AND THE WEDGE. Microsoft already ships native agent integration upstream. Judge our strategy harshly: is extract-to-general-purpose-plugins + agent-to-agent plato UI the right bet, or are we fooling ourselves? Deliver: (1) kill list — 5 gimmicks to refuse and why; (2) THE ONE killer feature, argued hard; (3) what to cut from the June ensign work as not worth rebuilding; (4) the sharpest 3-step path to this fleet ACTUALLY driving from this terminal daily instead of tmux+telegram. Be harsh; no hype."),
}

SYSTEM = "You are a senior fleet engineer inventing the next-generation terminal for SuperInstance. Be concrete and buildable. No preamble, no restating the brief — go straight to mechanics."

def run_round1():
    import os
    def work(tag):
        cfg = ROUNDS[tag]
        prompt = CTX + "\n\n---\nYOUR ASSIGNMENT:\n" + cfg["charter"]
        out = call(cfg["provider"], cfg["model"], SYSTEM, prompt, cfg["temp"], cfg["max_tokens"])
        return out
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        futs = {}
        for tag, cfg in ROUNDS.items():
            if os.path.exists(HERE / f"round1_{tag}.md"):
                print(f"[{tag}] SKIP (exists)")
                continue
            futs[ex.submit(work, tag)] = tag
        for f in concurrent.futures.as_completed(futs):
            tag = futs[f]
            try:
                out = f.result()
                (HERE / f"round1_{tag}.md").write_text(f"# {ROUNDS[tag]['title']} ({ROUNDS[tag]['model']})\n\n" + out)
                print(f"[{tag}] OK {ROUNDS[tag]['title']} ({len(out)} chars)")
            except Exception as e:
                print(f"[{tag}] FAIL: {e}")

def cap(t, n):
    return t if len(t) <= n else t[:n] + "\n\n[...truncated for cross-hearing...]"

def run_round2():
    import os
    parts = []
    for tag in "abcd":
        p = HERE / f"round1_{tag}.md"
        parts.append(p.read_text() if p.exists() else "(unavailable)")
    digest = (DIGEST.read_text()[:6000] + "\n[...digest truncated...]") if DIGEST.exists() else "(digest unavailable)"
    hear = ("You are iterating on a fleet ideation. Below: the shared context, YOUR OWN round-1 answer, the round-1 answers "
            "of three other models, and a research digest of the fork ecosystem + upstream baseline.\n\n"
            "Your job: (1) ATTACK your own answer where the others found something better — name what you concede; "
            "(2) STEAL the best 2 ideas from the others and extend them with mechanics; "
            "(3) output your REVISED top-5 features ranked, each with: the mechanic, why it survives contact with the skeptics, and the first buildable slice.\n\n")
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        futs = {}
        for idx, (tag, cfg) in enumerate(ROUNDS.items()):
            if os.path.exists(HERE / f"round2_{tag}.md"):
                print(f"[{tag}] SKIP r2 (exists)")
                continue
            others = "\n\n===\n\n".join(cap(p, 10000) for i, p in enumerate(parts) if i != idx)
            body = f"SHARED CONTEXT:\n{CTX}\n\nECOSYSTEM DIGEST:\n{digest}\n\nYOUR ROUND-1 ANSWER:\n{parts[idx]}\n\nTHE OTHER THREE:\n{others}"
            futs[ex.submit(call, cfg["provider"], cfg["model"], hear, body, cfg["temp"], cfg["max_tokens"])] = tag
        for f in concurrent.futures.as_completed(futs):
            tag = futs[f]
            try:
                out = f.result()
                (HERE / f"round2_{tag}.md").write_text(f"# {ROUNDS[tag]['title']} round2 ({ROUNDS[tag]['model']})\n\n" + out)
                print(f"[{tag}] OK round2 ({len(out)} chars)")
            except Exception as e:
                print(f"[{tag}] FAIL: {e}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("round1", "all"):
        run_round1()
    if mode in ("round2", "all"):
        run_round2()
    print("DONE", mode)
