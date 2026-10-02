"""XP-C provider arms: STUB (ground truth) / LOCAL (ollama on the 4050) / CLOUD (z.ai).

Stdlib only. No external deps. House style: seed 2718, fail loud.

Provider interface (frozen for XP-C):

    class Provider:
        name: str
        def generate(self, prompt: str, seed: int, temperature: float,
                     max_tokens: int) -> str: ...

`generate` returns the RAW text the provider produced (the harness/Guard
decides whether it is a well-formed envelope).

Secrets law: the z.ai key is read at use-time from the keyfile line
starting `ZAI_KEY`, travels to its own service ONLY (HTTP Authorization
header, passed to curl through a 0600 config file so it never enters
argv), and is never printed/echoed/logged or written to any artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time

KEYFILE = "/mnt/c/Users/casey/key.txt"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
# The pay-as-you-go paas endpoint answers 429 code 1113 (Insufficient balance);
# this key is the account's CODING-plan key, so the coding base URL is used
# (same endpoint shape as experiments/g1c_verdict_routing.py — fleet-proven).
ZAI_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"

# Candidate z.ai model ids, tried in order (probe decides; no auth improvisation).
ZAI_MODEL_CANDIDATES = ("glm-5.3-flash", "glm-4.6", "glm-4.5-flash")


class ProviderError(RuntimeError):
    """Loud provider failure — never silently degrade to a stub."""


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# curl plumbing (list-form argv only; never shell=True)
# --------------------------------------------------------------------------
def _curl_post(url: str, body: dict, *, headers=None, extra_args=None,
               timeout_s: float = 180.0, cfg_header: str | None = None) -> tuple[int, str]:
    """POST json body with curl. Returns (http_code, response_body).

    cfg_header: a full header line ("Authorization: Bearer ...") that is
    passed via a 0600 curl config file (-K) so it never appears in argv.
    """
    import shutil
    curl = shutil.which("curl") or "/usr/bin/curl"
    args = [curl, "-sS", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "--max-time", str(int(timeout_s))]
    for h in (headers or []):
        args += ["-H", h]
    cfg_path = None
    if cfg_header:
        fd, cfg_path = tempfile.mkstemp(prefix="xpc_curl_", suffix=".cfg")
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write('header = "%s"\n' % cfg_header.replace("\\", "\\\\").replace('"', '\\"'))
        args += ["-K", cfg_path]
    args += ["--data-binary", "@-", "-w", "\n__HTTP__%{http_code}"]
    if extra_args:
        args += list(extra_args)
    try:
        p = subprocess.run(args, input=json.dumps(body), capture_output=True,
                           text=True, timeout=timeout_s + 30)
    finally:
        if cfg_path and os.path.exists(cfg_path):
            os.unlink(cfg_path)
    out = p.stdout or ""
    code = 0
    m = re.search(r"__HTTP__(\d{3})\s*$", out)
    if m:
        code = int(m.group(1))
        out = out[:m.start()].rstrip("\n")
    if p.returncode != 0 and code == 0:
        raise ProviderError(f"curl exit {p.returncode}: {(p.stderr or '').strip()[:300]}")
    return code, out


def _read_key(name: str) -> str:
    """Read a secret line at use-time. Never prints or persists the value."""
    try:
        with open(KEYFILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith(name):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if not v:
                        raise ProviderError(f"{name} present but empty")
                    return v
    except FileNotFoundError as e:
        raise ProviderError(f"keyfile missing: {e}") from None
    raise ProviderError(f"{name} not found in keyfile")


# --------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------
class StubProvider:
    """Ground truth: a pure deterministic function of (prompt, seed).

    It reads the blueprint lines the harness embedded in the prompt and
    emits a perfect envelope. z_out is deterministic in (prompt, seed).
    """
    name = "stub"

    def generate(self, prompt: str, seed: int, temperature: float,
                 max_tokens: int) -> str:
        def field(k: str) -> str:
            m = re.search(rf"^{k} = (.*)$", prompt, re.M)
            if not m:
                raise ProviderError(f"stub: blueprint field missing: {k}")
            return m.group(1).strip()
        cell_id = field("cell_id")
        digest = field("z_in_digest")
        provider = field("provider")
        seed_s = int(field("seed"))
        if seed_s != seed:
            raise ProviderError("stub: blueprint seed != call seed")
        z_out = "stub:" + hashlib.sha256(
            f"{prompt}|{seed}".encode("utf-8")).hexdigest()[:20]
        return json.dumps({
            "cell_id": cell_id, "z_in_digest": digest, "z_out": z_out,
            "provider": provider, "seed": seed_s,
        }, ensure_ascii=False)


class LocalOllamaProvider:
    """Local GPU seat: ollama chat API over 127.0.0.1:11434 (curl list-form)."""
    name = "local"

    def __init__(self, model: str = "qwen2.5:3b-instruct-q4_K_M",
                 url: str = OLLAMA_URL, timeout_s: float = 240.0):
        self.model = model
        self.url = url
        self.timeout_s = timeout_s

    def generate(self, prompt: str, seed: int, temperature: float,
                 max_tokens: int) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"seed": int(seed), "temperature": float(temperature),
                        "num_predict": int(max_tokens), "top_p": 1.0},
        }
        code, out = _curl_post(self.url, body, timeout_s=self.timeout_s)
        if code != 200:
            raise ProviderError(f"ollama http {code}: {out[:300]}")
        try:
            data = json.loads(out)
        except Exception:
            raise ProviderError(f"ollama non-json response: {out[:300]}")
        if "error" in data:
            raise ProviderError(f"ollama error: {str(data['error'])[:300]}")
        return data.get("message", {}).get("content", "")


class CloudZaiProvider:
    """Cloud arm: z.ai GLM chat completions (OpenAI-compatible shape)."""
    name = "cloud"

    def __init__(self, model: str | None = None, url: str = ZAI_URL,
                 timeout_s: float = 180.0):
        self.model = model  # if None, first candidate that works is latched
        self.url = url
        self.timeout_s = timeout_s
        self.probed_model: str | None = None

    def _call(self, model: str, prompt: str, seed: int, temperature: float,
              max_tokens: int) -> tuple[int, str]:
        key = _read_key("ZAI_KEY")  # at use-time only
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "seed": int(seed),
            "max_tokens": int(max_tokens),
            "stream": False,
        }
        # key rides in a 0600 curl config header, never argv/URL/logs
        last = (0, "")
        for attempt in range(4):
            code, out = _curl_post(self.url, body, timeout_s=self.timeout_s,
                                   cfg_header=f"Authorization: Bearer {key}")
            last = (code, out)
            if code == 200 or code in (400, 401, 403):
                return code, out
            time.sleep(2.0 * (attempt + 1))  # 429 / 5xx / transport: backoff
        return last

    def probe(self) -> str:
        """One minimal test call to latch the model id. Raises ProviderError."""
        prompt = "Reply with exactly the word: ok"
        last = None
        for cand in ([self.model] if self.model else list(ZAI_MODEL_CANDIDATES)):
            code, out = self._call(cand, prompt, 2718, 0.0, 8)
            if code == 200:
                self.probed_model = cand
                self.model = cand
                return cand
            last = f"{cand} -> http {code}: {out[:200]}"
            # auth failures must not be improvised around: bail immediately
            if code in (401, 403):
                raise ProviderError(f"cloud auth failure (not improvising): {last}")
        raise ProviderError(f"cloud probe failed for all candidates: {last}")

    def generate(self, prompt: str, seed: int, temperature: float,
                 max_tokens: int) -> str:
        if not self.model:
            self.probe()
        code, out = self._call(self.model, prompt, seed, temperature, max_tokens)
        if code != 200:
            raise ProviderError(f"cloud http {code}: {out[:300]}")
        try:
            data = json.loads(out)
        except Exception:
            raise ProviderError(f"cloud non-json response: {out[:300]}")
        if "error" in data:
            raise ProviderError(f"cloud error: {str(data['error'])[:300]}")
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            raise ProviderError(f"cloud unexpected shape: {out[:300]}")


def get_provider(arm: str, **kw):
    if arm == "stub":
        return StubProvider()
    if arm == "local":
        return LocalOllamaProvider(**kw)
    if arm == "cloud":
        return CloudZaiProvider(**kw)
    raise ProviderError(f"unknown arm: {arm}")
