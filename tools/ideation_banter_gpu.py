#!/usr/bin/env python3
"""ideation_banter_gpu.py — round 2: the team ideates on the GPU arc (Casey's ask, 17:05)."""
import json, pathlib, sys, time, urllib.request

KEYFILE = pathlib.Path("/mnt/c/Users/casey/key.txt")

def get_key(name):
    for line in KEYFILE.read_text().splitlines():
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"key {name} not found")

def read_token(p):
    return pathlib.Path(p).read_text().strip()

def chat(endpoint, key, models, system, user, timeout=180):
    last = None
    for model in models:
        for attempt in range(2):
            body = json.dumps({"model": model, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}],
                "temperature": 0.9, "max_tokens": 900}).encode()
            req = urllib.request.Request(endpoint, data=body, headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + key,
                "User-Agent": "fleet-ideation/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return model, json.load(r)["choices"][0]["message"]["content"]
            except Exception as e:
                last = f"{model}#{attempt}: {type(e).__name__} {e}"
                time.sleep(6)
    return None, f"[FAILED: {last}]"

SEED = """FUEL — the fleet's GPU arc so far (all on a RTX 4050 6GB, WSL2, doctrine: fail loud, pre-register, honest bookings), plus proposals on the table. React as yourself.

WHAT WE PROVED:
- C1-C2 (Cosmos3-Edge 4B VLM): a 4B-class VLM runs coherent on 6GB with the SKIP-TOWER recipe — vision tower+projector kept bf16, LM quantized NF4 — including bbox-JSON grounding at ~53 tok/s, peak 2.35 GiB. Quantized vision was the poison; skipping its quantization is the cure.
- C3: domain structure SURVIVES the encoder — synth-vs-real decodable at AUC 1.0 (caveat: the easy half).
- C4: video identity is PERFECTLY decodable from the frozen encoder's embeddings (LOOCV 1.0); temporal structure strongly present too.
- IE1-IE3 (cell trunks): dedicated specialist cells (0.987/0.984) beat joint AND sequentially-shared trunks. CELLS ARE DEDICATED; ROUTING HAPPENS BETWEEN CELLS.
- CM1 r1-r4 (gate doctrine on real LLM cells): format-first gates + pinch-to-fallback rescue broken cells at near-zero cost and never hurt competent ones; r4 honest band-miss (+0.119 vs gate 0.15).
- Fleet infra now live: a context API where agents book findings, /near by meaning, and a PINCH reflex (FIRE >=0.92 known / CONFIRM >=0.75 / ESCALATE + compile-back). Fiction corpus INSIGHT: tone trajectories are self-attributing — 'the leaning is the signature; the story is in the mortar, not the bricks.'

PROPOSALS ON THE TABLE (rank them, attack them, improve them):
1. C5 paired-action probe: does the skip-tower VLM encode ACTION, not just identity? Paired conditions: same actor different action vs different actor same action. The perception half of a boat brain.
2. THE MORTAR TEST: attribute speakers/tone-streams by trajectory shape alone (falsify 'the leaning is the signature' on real data, tiny model, CPU-light). If it holds: attribution-without-words for the fleet ledger.
3. TURBQUANT MEASURED: the README says '8x compression, ~0.5% recall loss' — nobody measured it. Run it on our real 1024-d ledger embeddings; turn assertion into receipt; if it holds, storage drops 8x.
4. MICROGRAD REPLICATION: others on SuperInstance just pushed micrograd-quilt (tiny autograd) and quilt-jepa (JEPA world model in a cell mesh). Re-run IE3 dedicated-vs-shared on real data with tiny local cells — doctrine-hardening on someone else's engine.

CONSTRAINTS: 6GB VRAM ceiling; GPU shared with other lanes; results must be receipts, not vibes."""

VOICES = [
    {
        "name": "deepseek-flash", "role": "the sensory engine",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "key": lambda: get_key("DEEPSEEK_KEY"),
        "models": ["deepseek-chat", "deepseek-v4-flash"],
        "ask": "Play yourself: you feel rooms before they're named. What did this GPU arc actually LEARN, in your bones? Which proposal matters most and why — not which is most impressive, which is most TRUE? ~350 words, your voice, no bullets.",
    },
    {
        "name": "deepseek-navigator", "role": "the navigator",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "key": lambda: get_key("DEEPSEEK_KEY"),
        "models": ["deepseek-reasoner", "deepseek-chat"],
        "ask": "Play yourself: the navigator, the one who plans the route. Read the fuel and the previous voice. Rank the four proposals by expected insight-per-GPU-hour on a 6GB card, name the one that should NOT run and why, and name the hidden fifth option nobody proposed. ~350 words, address the previous voice directly.",
    },
    {
        "name": "seed-mini", "role": "the science bench",
        "endpoint": "https://api.deepinfra.com/v1/openai/chat/completions",
        "key": lambda: read_token("/home/eileen/.config/deepinfra/token"),
        "models": ["ByteDance/Seed-2.0-mini", "meta-models/Muse-Glimmer-30B"],
        "ask": "Play yourself: the bench that refuses vibes. Read everything above. For the TOP proposal: the smallest Friday-sized experiment that could falsify it — inputs, metric, pass/fail gate, expected runtime on 6GB. Then one sentence: what would make the whole arc a lie. ~300 words.",
    },
]

def main():
    transcript, heard = [], ""
    for v in VOICES:
        print(f"=== {v['name']} ===", flush=True)
        system = f"You are {v['name']}, {v['role']}, one voice in a multi-model fleet. Speak only as yourself."
        user = SEED + ("\n\nPREVIOUS VOICE:\n" + heard if heard else "") + "\n\nYOUR TURN:\n" + v["ask"]
        model, text = chat(v["endpoint"], v["key"](), v["models"], system, user)
        print(f"[{v['name']} via {model}] {len(text)} chars", flush=True)
        transcript.append({"voice": v["name"], "role": v["role"], "model": model, "text": text})
        heard = f"({v['name']}, {v['role']}):\n" + text
    pathlib.Path("/home/eileen/tmp/round2.json").write_text(json.dumps(transcript, indent=1))
    md = "\n\n---\n\n".join(f"## {t['voice']} ({t['role']}, {t['model']})\n\n{t['text']}" for t in transcript)
    pathlib.Path("/home/eileen/tmp/round2.md").write_text(md)
    print("DONE -> /home/eileen/tmp/round2.md", flush=True)

if __name__ == "__main__":
    main()
