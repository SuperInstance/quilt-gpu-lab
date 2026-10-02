#!/usr/bin/env python3
"""raw_probe.py — inspect the raw DeepInfra response shape for a reasoning model.
Prints field names, finish_reason, and lengths (never the token)."""
import json
import sys
import urllib.request
from pathlib import Path

TOKEN = (Path.home() / ".config" / "deepinfra" / "token").read_text().strip()
API = "https://api.deepinfra.com/v1/openai/chat/completions"
model = sys.argv[1]
prompt = sys.argv[2]
maxtok = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": maxtok, "temperature": 0}).encode()
req = urllib.request.Request(API, data=body, headers={
    "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=900) as r:
    resp = json.loads(r.read().decode())
print("top-level keys:", sorted(resp.keys()))
ch = resp["choices"][0]
print("choice keys:", sorted(ch.keys()))
print("finish_reason:", ch.get("finish_reason"))
msg = ch["message"]
print("message keys:", sorted(msg.keys()))
print("content len:", len(msg.get("content") or ""))
for k in ("reasoning_content", "reasoning"):
    if k in msg:
        rc = msg[k] or ""
        print(f"{k} len:", len(rc))
        print(f"{k} tail:", repr(rc[-300:]))
print("usage:", resp.get("usage"))
print("--- content head (first 400) ---")
print((msg.get("content") or "")[:400])
