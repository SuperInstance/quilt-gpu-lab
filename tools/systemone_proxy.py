#!/usr/bin/env python3
"""System One API proxy — every teacher call becomes a sealed training episode.

Doctrine (2026-09-30, wide-scope): the API is the teacher; the ledger of its calls is the
seed corpus for distillation. Wrap ALL /v1/systemone calls through this module so every
judgment the teacher ever grades is HMAC-booked locally (state, questions, answers,
probabilities, model) — the distillery's P-1: a corpus that grows by using the teacher.

- Token read at use-time from ~/.config/typesafe/token (never echoed, never logged).
- Ledger: ~/.config/systemone/call-ledger.jsonl (append-only; one HMAC-sealed line/call).
- Fail loud on HTTP errors (no retry loops — throttle doctrine).
- Import-safe (no side effects on import); CLI passthrough for one-shot calls.

Usage:
    from tools.systemone_proxy import ask
    result = ask(state="...", questions={"flow": {...}})          # dict in, dict out
    python3 tools/systemone_proxy.py --state "..." --questions questions.json
"""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.typesafe.ai/v1/systemone"
TOKEN_PATH = Path.home() / ".config" / "typesafe" / "token"
LEDGER_DIR = Path.home() / ".config" / "systemone"
LEDGER_PATH = LEDGER_DIR / "call-ledger.jsonl"
# HMAC key: derived from the token itself (never stored separately; rotates with the token).


def _token() -> str:
    tok = TOKEN_PATH.read_text().strip()
    if not tok:
        raise RuntimeError(f"empty token at {TOKEN_PATH}")
    return tok


def _seal(record: dict) -> dict:
    key = _token().encode()
    body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["hmac"] = hmac.new(key, body, hashlib.sha256).hexdigest()
    return record


def ask(state, questions, model="jev-latest", book=True, timeout=60):
    """POST one judgment call. Returns parsed response dict. Books a sealed episode."""
    payload = {"model": model, "state": state, "questions": questions}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        raise RuntimeError(f"systemone HTTP {e.code}: {detail}") from None

    if book:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        episode = {
            "ts": round(time.time(), 3),
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "model": result.get("model", model),
            "state": state,
            "questions": questions,
            "answers": result.get("answers", {}),
            "usage": result.get("usage", {}),
        }
        with open(LEDGER_PATH, "a") as f:
            f.write(json.dumps(_seal(episode), separators=(",", ":")) + "\n")
    return result


def ledger_stats():
    """Corpus vitals: episodes, question-type counts, mean latency."""
    if not LEDGER_PATH.exists():
        return {"episodes": 0}
    n, types, lat = 0, {}, []
    for line in LEDGER_PATH.read_text().splitlines():
        if not line.strip():
            continue
        ep = json.loads(line)
        n += 1
        lat.append(ep.get("latency_ms", 0))
        for ans in ep.get("answers", {}).values():
            t = ans.get("type", "?")
            types[t] = types.get(t, 0) + 1
    return {"episodes": n, "question_types": types,
            "mean_latency_ms": round(sum(lat) / len(lat), 1) if lat else 0}


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--stats":
        print(json.dumps(ledger_stats(), indent=2))
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "--state":
        state = sys.argv[2]
        qpath = sys.argv[sys.argv.index("--questions") + 1] if "--questions" in sys.argv else None
        questions = json.loads(Path(qpath).read_text()) if qpath else {}
        print(json.dumps(ask(state, questions), indent=2))
        sys.exit(0)
    print(__doc__)
