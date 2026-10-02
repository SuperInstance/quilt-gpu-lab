#!/usr/bin/env python3
"""deepinfra_call.py — minimal OpenAI-compatible DeepInfra chat caller.

House law: list-form subprocess only (no shell), token read from
~/.config/deepinfra/token at runtime and never echoed, retry once on
429/5xx with backoff, fail loud (non-zero exit + stderr) on error.

Usage:
  tools/deepinfra_call.py --model ibm-granite/granite-4.2-30b \
      --prompt-file brief.txt --max-tokens 2000 [--temperature 0] \
      [--system "..."] [--out reply.txt]

Exit codes: 0 ok, 2 usage, 3 api error, 4 token missing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.deepinfra.com/v1/openai/chat/completions"
TOKEN_PATH = Path.home() / ".config" / "deepinfra" / "token"
RETRY_STATUS = {429, 500, 502, 503, 504}


def read_token() -> str:
    try:
        tok = TOKEN_PATH.read_text().strip()
    except OSError as e:
        print(f"FATAL: cannot read token at {TOKEN_PATH}: {e}", file=sys.stderr)
        sys.exit(4)
    if not tok:
        print(f"FATAL: empty token at {TOKEN_PATH}", file=sys.stderr)
        sys.exit(4)
    return tok


def call(model: str, messages: list, max_tokens: int, temperature: float,
         timeout: float) -> dict:
    token = read_token()
    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        API, data=body,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method="POST")
    last_err = None
    for attempt in (1, 2):  # retry once on 429/5xx
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}"
            if e.code in RETRY_STATUS and attempt == 1:
                wait = 3.0
                print(f"retry: {last_err} (sleep {wait}s)", file=sys.stderr)
                time.sleep(wait)
                continue
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt == 1:
                time.sleep(3.0)
                continue
            break
    print(f"FATAL api error: {last_err}", file=sys.stderr)
    sys.exit(3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--system", default=None)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.prompt and a.prompt_file:
        print("usage: give --prompt or --prompt-file, not both", file=sys.stderr)
        sys.exit(2)
    if a.prompt_file:
        prompt = Path(a.prompt_file).read_text()
    elif a.prompt:
        prompt = a.prompt
    else:
        print("usage: need --prompt or --prompt-file", file=sys.stderr)
        sys.exit(2)

    messages = []
    if a.system:
        messages.append({"role": "system", "content": a.system})
    messages.append({"role": "user", "content": prompt})

    resp = call(a.model, messages, a.max_tokens, a.temperature, a.timeout)
    try:
        choice = resp["choices"][0]
        content = choice["message"]["content"]
        reasoning = choice["message"].get("reasoning_content")
        finish = choice.get("finish_reason")
    except (KeyError, IndexError) as e:
        print(f"FATAL malformed response: {resp}", file=sys.stderr)
        sys.exit(3)

    usage = resp.get("usage", {})
    meta = {"model": resp.get("model", a.model), "finish_reason": finish,
            "content_chars": len(content or ""),
            "reasoning_chars": len(reasoning or ""),
            "usage": usage}
    print(json.dumps(meta), file=sys.stderr)

    if content is None or content == "":
        print("WARN: empty content (finish_reason=%s, usage=%s)"
              % (finish, usage), file=sys.stderr)

    if a.out:
        Path(a.out).write_text(content or "")
        if reasoning:
            Path(a.out + ".reasoning.txt").write_text(reasoning)
    else:
        sys.stdout.write(content or "")


if __name__ == "__main__":
    main()
