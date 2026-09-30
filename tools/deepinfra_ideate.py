#!/usr/bin/env python3
"""DeepInfra multi-model ideation round (grabbable tool).

Rotates a prompt across the cheap/cached DeepInfra roster, one model per lane, and appends
each response to a JSONL. Doctrine: wide ideation across many models, then a synthesis pass —
rotate across lanes, never mid-thread (cache economics).

Usage:
    python tools/deepinfra_ideate.py --prompt-file p.txt --out /tmp/round.jsonl
    python tools/deepinfra_ideate.py --prompt "..." --models m1,m2 --max-tokens 700
Token: read at use-time from ~/.config/deepinfra/token (never echoed).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.deepinfra.com/v1/openai/chat/completions"
TOKEN = Path.home() / ".config" / "deepinfra" / "token"

DEFAULT_ROSTER = [
    "XiaomiMiMo/MiMo-V2.6-Flash",
    "nvidia/NVIDIA-Nemotron-3.5-Lightning",
    "Qwen/Qwen3.8-Flash",
    "ibm-granite/granite-4.2-3b",
    "inclusionAI/Ling-3.0-flash",
]


def ask(model, prompt, max_tokens, system=None, temperature=0.9, timeout=180):
    body = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else [])
        + [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN.read_text().strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"model": model, "error": f"HTTP {e.code}", "detail": e.read().decode()[:300]}
    except Exception as e:  # noqa: BLE001 - report, never crash the round
        return {"model": model, "error": type(e).__name__, "detail": str(e)[:300]}
    choice = data["choices"][0]
    msg = choice.get("message", {})
    rec = {
        "model": model,
        "latency_s": round(time.time() - t0, 2),
        "text": msg.get("content") or "",
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage", {}),
    }
    rc = msg.get("reasoning_content") or msg.get("reasoning")
    if rc:
        rec["reasoning"] = rc
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--models", help="comma-separated; default = cheap/cached roster")
    ap.add_argument("--out", default="/home/eileen/scratch/ideation/round.jsonl")
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--system", default=None)
    args = ap.parse_args()

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text()
    if not prompt:
        print(__doc__)
        sys.exit(2)

    models = args.models.split(",") if args.models else DEFAULT_ROSTER
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as f:
        for m in models:
            r = ask(m, prompt, args.max_tokens, system=args.system)
            f.write(json.dumps(r) + "\n")
            f.flush()
            status = r.get("error") or (
                f"{len(r.get('text',''))} chars in {r.get('latency_s')}s"
                + (f" (+{len(r.get('reasoning',''))} reasoning chars)" if r.get("reasoning") else "")
            )
            print(f"[{m}] {status}", flush=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
