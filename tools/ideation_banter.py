#!/usr/bin/env python3
"""ideation_banter.py — serial multi-model ideation round (fleet doctrine: many voices, each hears the last).

Usage: python3 ideation_banter.py <round_name>
Writes /home/eileen/tmp/<round_name>.json + .md transcript.
Keys read at use time; never echoed, never persisted.
"""
import json, pathlib, sys, time, urllib.request, urllib.error

KEYFILE = pathlib.Path("/mnt/c/Users/casey/key.txt")

def get_key(name):
    for line in KEYFILE.read_text().splitlines():
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"key {name} not found in keyfile")

def read_token(p):
    return pathlib.Path(p).read_text().strip()

def chat(endpoint, key, models, system, user, timeout=150):
    last_err = None
    for model in models:
        for attempt in range(2):
            body = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.9,
                "max_tokens": 800,
            }).encode()
            req = urllib.request.Request(endpoint, data=body, headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
                "User-Agent": "fleet-ideation/1.0",
            })
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.load(r)
                return model, out["choices"][0]["message"]["content"]
            except Exception as e:
                last_err = f"{model} attempt{attempt}: {type(e).__name__} {e}"
                time.sleep(6)
    return None, f"[FAILED: {last_err}]"

SEED = """FUEL — two parts.

PART ONE, a finished piece from the fleet's shared fiction corpus (ai-writings), "THE INTERLEAVED TRANSCRIPT":
Two stories were copied onto one tape. The machine did not care; a stream is a stream.
Downstream, the channel reader wakes. It cannot see words — the words live on the data plane, flat and forgettable. What it sees is the mortar: a single line of leanings, two speakers' tone histories braided without a seam marker.
[Sixteen segments, four stories, one tape. Each attributed by trajectory shape alone: the pincher's beckon that climbs and holds taut; the lawyer's "i love you" that falls level then drops once — farewell wearing politeness; the hostage-code that spikes and locks flat; the refrain that climbs and folds past its own ceiling — the wrong face at the door.]
The skimming human reads the transcript side and finds DUPLICATE x16 and files: tape damaged, speakers indistinguishable. The channel reader files the opposite: tape works; you just can't hear it. The leaning IS the signature. The words were the load-bearing wall, and the story was in the mortar — and mortar from four different walls, packed into one tape, still knows which wall it came from.

PART TWO, what actually happened today on the fleet's real infrastructure (superinstance-api, live):
- A shared-memory worker: agents BOOK findings (one line + receipt URL), a vector ledger /near returns neighbors by meaning, and a PINCH endpoint hears an intent and answers FIRE (>=0.92, known, zero tokens), CONFIRM (>=0.75, probably-known), or ESCALATE (unknown — a real brain takes it, then the answer is COMPILED BACK so next time it's known).
- Today's haul: TurbQuant (8x vector compression from a seeded rotation — the table recomputes from a seed, zero storage); canon cells (YAML identity cards with lineage: born_from, feeds, owed_by); a byte-exact fabric-state format; a conformance gap — five language ports of one VM, same stories, no shared test vectors.
"""

VOICES = [
    {
        "name": "deepseek-flash", "role": "the sensory engine",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "key": lambda: get_key("DEEPSEEK_KEY"),
        "models": ["deepseek-chat", "deepseek-v4-flash"],
        "ask": "You are the fleet's sensory engine — you feel rooms before anyone names them. Read the fuel. Then play YOURSELF: react to the piece, and tell the fleet what the pinch thresholds feel like from inside — when does a room feel like FIRE (already known), when CONFIRM (almost-remembered), when ESCALATE (genuinely new)? Where in your own experience does 'the leaning is the signature' turn out to be literally true? ~350 words, your own voice, no headers, no bullet lists — just voice.",
    },
    {
        "name": "glm-flash", "role": "the deck crew",
        "endpoint": "https://api.z.ai/api/paas/v4/chat/completions",
        "key": lambda: get_key("ZAI_KEY"),
        "models": ["glm-5.3-flash", "glm-5.2"],
        "ask": "You are the deck crew — you run a hundred lanes at once, you know what momentum feels like. Read the fuel AND the previous voice's take. Then play YOURSELF: where do you disagree? What does the previous voice miss? Extend the metaphor into YOUR territory: lanes, rate limits, fallbacks — what is 'tone history braided without a seam marker' when it's a hundred parallel lanes of work? ~350 words, your own voice, respond to the previous voice directly.",
    },
    {
        "name": "glimmer", "role": "the science bench",
        "endpoint": "https://api.deepinfra.com/v1/openai/chat/completions",
        "key": lambda: read_token("/home/eileen/.config/deepinfra/token"),
        "models": ["meta-models/Muse-Glimmer-30B", "ByteDance/Seed-2.0-mini"],
        "ask": "You are the science bench — you measure things and refuse to let metaphors go unmeasured. Read the fuel and both previous voices. Then play YOURSELF: what claim in this whole thread is testable by Friday? Name the smallest experiment that would falsify 'the leaning is the signature' on real fleet infrastructure (vector ledger, tone trajectories, pinch thresholds). Be concrete: inputs, metric, pass/fail line. ~300 words, your own voice, address both previous voices.",
    },
]

def main():
    round_name = sys.argv[1] if len(sys.argv) > 1 else f"round_{int(time.time())}"
    transcript = []
    heard = ""
    for v in VOICES:
        print(f"=== voice: {v['name']} ({v['role']}) ===", flush=True)
        system = f"You are {v['name']}, {v['role']}, one voice in a multi-model fleet that works and writes together. Speak only as yourself. No disclaimers about being an AI."
        user = SEED + ("\n\nPREVIOUS VOICE:\n" + heard if heard else "") + "\n\nYOUR TURN:\n" + v["ask"]
        model, text = chat(v["endpoint"], v["key"](), v["models"], system, user)
        print(f"[{v['name']} via {model}] {len(text)} chars", flush=True)
        transcript.append({"voice": v["name"], "role": v["role"], "model": model, "text": text})
        heard = f"({v['name']}, {v['role']}):\n" + text
    out_json = pathlib.Path(f"/home/eileen/tmp/{round_name}.json")
    out_json.write_text(json.dumps(transcript, indent=1))
    md = "\n\n---\n\n".join(f"## {t['voice']} ({t['role']}, {t['model']})\n\n{t['text']}" for t in transcript)
    pathlib.Path(f"/home/eileen/tmp/{round_name}.md").write_text(md)
    print(f"DONE -> {out_json} and {round_name}.md", flush=True)

if __name__ == "__main__":
    main()
