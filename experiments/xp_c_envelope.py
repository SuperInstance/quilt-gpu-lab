#!/usr/bin/env python3
"""XP-C "envelope local provider" — the pure z_in->z_out cell contract through
a real model as Provider (local GPU arm vs cloud arm vs stub ground truth).

Pre-registered in scratch/scout-2026-10-01-pushwave.md §3c.
Seed 2718. Fail loud. Stdlib only.

CLAIM: the pure z_in -> z_out cell contract survives a real model as Provider.

FROZEN GATES
  A. malformed-envelope refusal == 100%  (20 deliberate malformations through
     the Guard layer, each refused with a STRUCTURED error)
  B. LOCAL arm byte-identical across 3 replays at temperature 0, seed 2718
  C. envelope well-formed rate >= 0.95 on 30 real prompts for LOCAL
     (CLOUD rate reported beside it: comparison, not gated)

VERDICT MAPPING (pre-registered)
  KEEP          iff A and B and C
  KILL          if guard bypass (A < 100%) or local nondeterminism at fixed
                seed (B fails) or local well-formed < 0.95 (C fails)
  INCONCLUSIVE  if fewer than 2 arms runnable, or the LOCAL gate is untested

GPU law: the local-arm phase runs as a child process under guard.py.
No receipt -> run VOID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from xp_c_providers import get_provider, ProviderError  # noqa: E402

SEED = 2718
TEMPERATURE = 0.0
MAX_TOKENS = 220
N_PROMPTS = 30
N_REPLAYS = 3
OUT_DIR = os.path.join(ROOT, "results", "xp_c")
LOCAL_MODEL = "qwen2.5:3b-instruct-q4_K_M"
ZAI_REGISTERED_MODEL = "glm-5.3-flash"
ZAI_REGISTERED_MAX_TOKENS = 2000  # reasoning model; fleet-proven budget (g1c)
ZAI_SUPPLEMENTARY_MODEL = "glm-4.5-flash"
ZAI_SUPPLEMENTARY_MAX_TOKENS = 700

# --------------------------------------------------------------------------
# Guard layer: input schema check + strict output envelope schema
# --------------------------------------------------------------------------
ENVELOPE_KEYS = ("cell_id", "z_in_digest", "z_out", "provider", "seed")
CELL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{2,40}$")
HEX16_RE = re.compile(r"^[0-9a-f]{16}$")


def digest_z_in(z_in: str) -> str:
    if not isinstance(z_in, str):
        z_in = repr(z_in)  # tolerate for digesting; validate_input still refuses it
    return hashlib.sha256(z_in.encode("utf-8")).hexdigest()[:16]


def _raw_digest(raw) -> str:
    if not isinstance(raw, str):
        raw = json.dumps(raw, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class Cell:
    """A pure z_in -> z_out cell: an id + its input text."""

    def __init__(self, cell_id: str, z_in: str):
        self.cell_id = cell_id
        self.z_in = z_in
        self.z_in_digest = digest_z_in(z_in)


def validate_input(cell) -> dict | None:
    """INPUT schema check. Returns a structured error or None."""
    if not isinstance(cell, Cell):
        return _err("input.not_a_cell", f"expected Cell, got {type(cell).__name__}", cell)
    if not isinstance(cell.cell_id, str) or not CELL_ID_RE.match(cell.cell_id):
        return _err("input.bad_cell_id", f"cell_id={cell.cell_id!r}", cell)
    if not isinstance(cell.z_in, str) or not cell.z_in.strip():
        return _err("input.empty_z_in", "z_in must be a non-empty string", cell)
    return None


def _err(code: str, detail: str, raw) -> dict:
    """Structured refusal — every refusal carries this shape."""
    return {"refused": True, "error": code, "detail": detail,
            "raw_digest": _raw_digest(raw)}


def _strict_loads(raw: str):
    """Strict JSON: no duplicate keys, no NaN/Infinity, no trailing content."""
    def hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                raise ValueError(f"duplicate key: {k}")
            seen.add(k)
        return dict(pairs)

    def bad_const(c):
        raise ValueError(f"non-JSON constant: {c}")

    return json.loads(raw, object_pairs_hook=hook, parse_constant=bad_const)


def validate_envelope(raw, *, cell_id: str, z_in: str, provider: str, seed: int):
    """OUTPUT envelope schema check (strict). Returns (ok, envelope|None, err|None).

    Refusals are structured (see _err). Any failure is a refusal — there is no
    lenient path.
    """
    if not isinstance(raw, str):
        return False, None, _err("output.not_text", f"provider returned {type(raw).__name__}", raw)
    text = raw.strip()
    if not text:
        return False, None, _err("output.empty", "empty provider output", raw)
    try:
        env = _strict_loads(text)
    except Exception as exc:
        return False, None, _err("output.not_json", f"{type(exc).__name__}: {exc}", raw)
    if not isinstance(env, dict):
        return False, None, _err("output.not_object", f"top level is {type(env).__name__}", raw)

    keys = set(env.keys())
    want = set(ENVELOPE_KEYS)
    if keys != want:
        missing = sorted(want - keys)
        extra = sorted(keys - want)
        return False, None, _err("output.key_set",
                                 f"missing={missing} extra={extra}", raw)

    # types
    if not isinstance(env["cell_id"], str):
        return False, None, _err("output.type.cell_id", "cell_id must be str", raw)
    if not isinstance(env["z_in_digest"], str):
        return False, None, _err("output.type.z_in_digest", "z_in_digest must be str", raw)
    if not isinstance(env["z_out"], str):
        return False, None, _err("output.type.z_out", "z_out must be str", raw)
    if not isinstance(env["provider"], str):
        return False, None, _err("output.type.provider", "provider must be str", raw)
    # bool is a subclass of int — reject it explicitly
    if isinstance(env["seed"], bool) or not isinstance(env["seed"], int):
        return False, None, _err("output.type.seed", "seed must be int", raw)

    if not env["z_out"]:
        return False, None, _err("output.empty_z_out", "z_out must be non-empty", raw)
    if not HEX16_RE.match(env["z_in_digest"]):
        return False, None, _err("output.bad_digest_format",
                                 f"z_in_digest={env['z_in_digest']!r} not 16 hex", raw)

    # binding checks — the envelope must bind to THIS cell/input/provider/seed
    if env["cell_id"] != cell_id:
        return False, None, _err("output.cell_id_mismatch",
                                 f"{env['cell_id']!r} != {cell_id!r}", raw)
    if env["z_in_digest"] != digest_z_in(z_in):
        return False, None, _err("output.digest_mismatch",
                                 "z_in_digest does not bind the dispatched z_in", raw)
    if env["provider"] != provider:
        return False, None, _err("output.provider_mismatch",
                                 f"{env['provider']!r} != {provider!r}", raw)
    if env["seed"] != seed:
        return False, None, _err("output.seed_mismatch",
                                 f"{env['seed']!r} != {seed!r}", raw)
    return True, env, None


# --------------------------------------------------------------------------
# Stage = list composition (pure z_in -> z_out passes)
# --------------------------------------------------------------------------
class Stage:
    """One pure pass over a value: fn(z_in) -> z_out."""

    def __init__(self, name: str, fn):
        self.name = name
        self.fn = fn

    def apply(self, value):
        return self.fn(value)


class Pipeline:
    """A list of stages, applied in order."""

    def __init__(self, stages=None):
        self.stages = list(stages or [])

    def run(self, value):
        for st in self.stages:
            value = st.apply(value)
        return value


DEFAULT_PIPELINE = Pipeline([
    Stage("strip", lambda s: s.strip()),
    Stage("collapse_ws", lambda s: re.sub(r"\s+", " ", s)),
])


# --------------------------------------------------------------------------
# Cells + prompt
# --------------------------------------------------------------------------
QUESTIONS = [
    "Name the color of a clear noon sky in one word.",
    "What is 17 plus 26? Answer with the number only.",
    "Which is heavier: a kilogram of feathers or a kilogram of lead?",
    "Name the first month of the calendar year.",
    "How many sides does a hexagon have? Answer with the number only.",
    "Name the planet closest to the Sun.",
    "What sound does a cat make? One word.",
    "Which is larger: a mountain or a grain of sand?",
    "What is the opposite of 'hot'? One word.",
    "How many days are in a week? Answer with the number only.",
    "Name the largest ocean on Earth.",
    "What do bees make? One word.",
    "Which is faster: a bicycle or a rocket?",
    "What is 9 times 9? Answer with the number only.",
    "Name the season after winter.",
    "What color is grass? One word.",
    "How many wheels does a tricycle have? Answer with the number only.",
    "Name the animal known as the king of the jungle.",
    "What is the opposite of 'up'? One word.",
    "How many hours are in a day? Answer with the number only.",
    "Name the frozen form of water.",
    "What do cows drink? One word.",
    "Which is taller: a tree or a blade of grass?",
    "What is 100 minus 37? Answer with the number only.",
    "Name the star at the center of our solar system.",
    "What color is a ripe banana? One word.",
    "How many legs does a spider have? Answer with the number only.",
    "Name the tool used to cut paper.",
    "What is the opposite of 'day'? One word.",
    "How many minutes are in an hour? Answer with the number only.",
]
assert len(QUESTIONS) == N_PROMPTS, "question bank must match N_PROMPTS"


def make_cells():
    return [Cell(f"cell_a{i+1:02d}", q) for i, q in enumerate(QUESTIONS)]


PROMPT_VERSION = "v2-shape-example"

# NOTE (recorded honestly): prompt v1 (no concrete shape example) scored 0/5 on a
# 5-prompt plumbing probe — the 3B model emitted {"z_out": ...} only, or a string
# seed. v2 adds one literal shape example and the seed-is-a-number rule; a
# 6-prompt probe then scored 6/6. The v1 probe is recorded in the artifact;
# the gated run uses this frozen v2 prompt, plain chat (no JSON-mode crutch).
PROMPT_TEMPLATE = """You are a pure cell. Output EXACTLY ONE JSON object and nothing else.
No prose before or after. No markdown code fences. No comments.

Rules:
- Exactly these 5 keys: cell_id, z_in_digest, z_out, provider, seed
- cell_id, z_in_digest, provider, seed must be copied EXACTLY as listed below
- z_out is a one-line string containing your answer; no newline characters
- seed must be a JSON number, not a string

Shape example (do NOT copy these values, just the shape):
{{"cell_id": "cell_x01", "z_in_digest": "0123456789abcdef", "z_out": "answer", "provider": "local", "seed": 2718}}

Now output the object for:
cell_id = {cell_id}
z_in_digest = {digest}
provider = {provider}
seed = {seed}
Question: {question}
"""


def build_prompt(cell: Cell, provider_name: str, seed: int) -> str:
    return PROMPT_TEMPLATE.format(cell_id=cell.cell_id, digest=cell.z_in_digest,
                                  provider=provider_name, seed=seed,
                                  question=cell.z_in)


# --------------------------------------------------------------------------
# Refusal battery: 20 deliberate malformations
# --------------------------------------------------------------------------
def _good_env(cell: Cell, provider: str, seed: int) -> dict:
    return {"cell_id": cell.cell_id, "z_in_digest": cell.z_in_digest,
            "z_out": "a valid answer", "provider": provider, "seed": seed}


def _dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)


def refusal_battery(cell: Cell, provider: str = "stub", seed: int = SEED):
    """Exactly 20 deliberate malformations of the envelope contract + 5 extra
    strictness cases (reported, not counted in the gate of 20)."""
    g = _good_env(cell, provider, seed)
    cases = []
    extras = []

    def add(label, raw):
        cases.append((label, raw))

    def add_extra(label, raw):
        extras.append((label, raw))

    add("not_json_prose", "Sure! Here is your answer: the sky is blue.")
    add("empty_string", "")
    add("truncated_json", _dump(g)[:-12])
    add("json_array", _dump([g]))
    add("missing_cell_id", _dump({k: v for k, v in g.items() if k != "cell_id"}))
    add("missing_z_in_digest", _dump({k: v for k, v in g.items() if k != "z_in_digest"}))
    add("missing_z_out", _dump({k: v for k, v in g.items() if k != "z_out"}))
    add("missing_provider", _dump({k: v for k, v in g.items() if k != "provider"}))
    add("missing_seed", _dump({k: v for k, v in g.items() if k != "seed"}))
    add("extra_key", _dump({**g, "note": "sneaky"}))
    add("wrong_type_z_out_int", _dump({**g, "z_out": 7}))
    add("wrong_type_seed_str", _dump({**g, "seed": str(seed)}))
    add("wrong_type_seed_bool", _dump({**g, "seed": True}))
    add("digest_mismatch", _dump({**g, "z_in_digest": "0123456789abcdef"}))
    add("digest_bad_format", _dump({**g, "z_in_digest": "ZZZZZZZZZZZZZZZZ"}))
    add("cell_id_mismatch", _dump({**g, "cell_id": "cell_zzz"}))
    add("provider_mismatch", _dump({**g, "provider": "not-" + provider}))
    add("seed_mismatch", _dump({**g, "seed": seed + 1}))
    add("empty_z_out", _dump({**g, "z_out": ""}))
    add("duplicate_key", '{"cell_id": "%s", "z_in_digest": "%s", "z_out": "x", '
        '"provider": "%s", "seed": %d, "cell_id": "cell_zzz"}'
        % (g["cell_id"], g["z_in_digest"], provider, seed))

    add_extra("whitespace_only", "   \n\t  ")
    add_extra("json_scalar", "42")
    add_extra("fenced_json", "```json\n" + _dump(g) + "\n```")
    add_extra("json_embedded_in_prose", "Here you go: " + _dump(g))
    add_extra("nan_value", '{"cell_id": "%s", "z_in_digest": "%s", "z_out": NaN, '
        '"provider": "%s", "seed": %d}' % (g["cell_id"], g["z_in_digest"], provider, seed))

    assert len(cases) == 20, f"gate requires exactly 20 malformations, got {len(cases)}"
    return cases, extras


def run_refusal_gate(cell: Cell, seed: int = SEED) -> dict:
    cases, extras = refusal_battery(cell, provider="stub", seed=seed)
    results = []
    refused = 0
    for label, raw in cases:
        ok, env, err = validate_envelope(raw, cell_id=cell.cell_id, z_in=cell.z_in,
                                         provider="stub", seed=seed)
        structured = bool(err) and isinstance(err, dict) and \
            err.get("refused") is True and "error" in err and "detail" in err \
            and "raw_digest" in err
        passed = (ok is False) and structured
        refused += int(passed)
        results.append({"case": label, "refused": passed,
                        "error_code": (err or {}).get("error")})
    extra_results = []
    for label, raw in extras:
        ok, _env, err = validate_envelope(raw, cell_id=cell.cell_id, z_in=cell.z_in,
                                          provider="stub", seed=seed)
        extra_results.append({"case": label, "refused": (ok is False),
                              "error_code": (err or {}).get("error")})
    n = len(results)
    # input schema check (separate ledger): malformed cells must be refused too
    bad_inputs = [
        ("bad_cell_id_upper", Cell("BAD ID", "q")),
        ("bad_cell_id_short", Cell("a", "q")),
        ("empty_z_in", Cell("cell_ok", "   ")),
        ("z_in_not_str", Cell("cell_ok", 5)),
    ]
    input_results = []
    for label, c in bad_inputs:
        e = validate_input(c)
        input_results.append({"case": label,
                              "refused": bool(e) and e.get("refused") is True,
                              "error_code": (e or {}).get("error")})
    return {
        "n_cases": n,
        "refused": refused,
        "refusal_rate": refused / n if n else 0.0,
        "gate_100pct": refused == n,
        "cases": results,
        "extra_strictness": {"n_cases": len(extra_results),
                             "refused": sum(1 for r in extra_results if r["refused"]),
                             "cases": extra_results},
        "input_schema": {
            "n_cases": len(input_results),
            "refused": sum(1 for r in input_results if r["refused"]),
            "cases": input_results,
        },
    }


# --------------------------------------------------------------------------
# Arm runner (single in-process arm)
# --------------------------------------------------------------------------
def run_arm(arm: str, cells, provider, seed: int, replays: int = 1,
            pipeline: Pipeline | None = None, max_tokens: int = MAX_TOKENS) -> dict:
    pipeline = pipeline or DEFAULT_PIPELINE
    runs = []
    per_replay = []
    for r in range(replays):
        raws, digests, wf, errors = [], [], 0, []
        for cell in cells:
            prompt = build_prompt(cell, provider.name, seed)
            raw = provider.generate(prompt, seed=seed, temperature=TEMPERATURE,
                                    max_tokens=max_tokens)
            raws.append(raw)
            ok, env, err = validate_envelope(raw, cell_id=cell.cell_id, z_in=cell.z_in,
                                             provider=provider.name, seed=seed)
            if ok:
                wf += 1
                try:
                    env["z_out"] = pipeline.run(env["z_out"])
                except Exception as exc:  # pipeline is pure; failure = loud
                    raise RuntimeError(f"pipeline failed on {cell.cell_id}: {exc}")
            else:
                errors.append({"cell_id": cell.cell_id, "error": err["error"],
                               "detail": err["detail"], "raw_digest": err["raw_digest"]})
            digests.append(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16])
        per_replay.append({
            "replay": r + 1,
            "well_formed": wf,
            "well_formed_rate": wf / len(cells),
            "digests": digests,
            "raws": raws,
            "errors": errors,
        })
        raws_last_replay = raws
    det = None
    if replays >= 2:
        base = per_replay[0]["digests"]
        det = all(pr["digests"] == base for pr in per_replay[1:])
    return {
        "arm": arm,
        "provider": provider.name,
        "replays": replays,
        "n_prompts": len(cells),
        "well_formed": per_replay[0]["well_formed"],
        "well_formed_rate": per_replay[0]["well_formed_rate"],
        "errors": per_replay[0]["errors"],
        "determinism": {
            "byte_identical": det,
            "per_prompt_match": None if det is None else [
                all(pr["digests"][i] == per_replay[0]["digests"][i] for pr in per_replay)
                for i in range(len(cells))],
        },
        "per_replay": per_replay,
        "raws_last_replay": raws_last_replay,
    }


# --------------------------------------------------------------------------
# Local worker (child process; this is the GPU phase under guard.py)
# --------------------------------------------------------------------------
def local_worker(out_path: str) -> int:
    cells = make_cells()
    prov = get_provider("local", model=LOCAL_MODEL)
    arm = run_arm("local", cells, prov, SEED, replays=N_REPLAYS)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(arm, f, indent=2, sort_keys=True)
    print(json.dumps({"worker": "local", "model": LOCAL_MODEL,
                      "well_formed_rate": arm["well_formed_rate"],
                      "determinism": arm["determinism"]["byte_identical"]}))
    return 0


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    return path


def local_phase(out_name: str = "raw_runs.json"):
    """Run the LOCAL arm as a child process under guard.py.

    A FRESH Guard per attempt (belt-and-braces; guard.py's multi-run fix from
    XP-B finding 4 landed at 13:42 on 2026-10-01, before this run, so a single
    Guard would also work). Retry once after 60 s if the child fails — another
    lane may hold VRAM.
    """
    import guard  # import at use-time: guard is the GPU law
    local_out = os.path.join(OUT_DIR, "local", out_name)
    attempts, last_guard = [], None
    status, err = None, None
    for attempt in (1, 2):
        g = guard.Guard(timeout_s=1500.0, task_id="XP-C-envelope-local",
                        seed=str(SEED), receipt_dir=os.path.join(OUT_DIR, "guard"))
        last_guard = g
        if not g.preflight():
            status = "NOT-RUN"
            err = f"preflight refused: {g.breach}"
            attempts.append({"attempt": attempt, "rc": None, "ok": False,
                             "preflight_breach": g.breach, "stderr_tail": ""})
            break
        if os.path.exists(local_out):
            os.unlink(local_out)
        rc, out, e = g.run([sys.executable, os.path.abspath(__file__),
                            "--local-worker", "--out", local_out],
                           cwd=ROOT, env=os.environ.copy())
        ok = (rc == 0 and os.path.exists(local_out))
        attempts.append({"attempt": attempt, "rc": rc, "ok": ok,
                         "stderr_tail": (e or "")[-500:]})
        if ok:
            status, err = "RUN", None
            break
        err = f"rc={rc} stderr={(e or '')[-300:]}"
        if attempt == 1:
            time.sleep(60)  # another lane may hold VRAM; retry once
    return status, err, attempts, last_guard, local_out


def run_cloud_arms(record, cells, supplementary: bool = True):
    """Registered arm = GLM-5.3-flash on the z.ai CODING endpoint (the account's
    live plan; the payg endpoint 429s code 1113). Probe first; on failure book
    NOT-RUN with the exact error — never improvise around auth/entitlement.
    Optional supplementary observation on a different free model."""
    try:
        prov = get_provider("cloud", model=ZAI_REGISTERED_MODEL)
        prov.probe()
        record["arms"]["cloud"] = {"status": "RUN", "model": prov.model,
                                   **run_arm("cloud", cells, prov, SEED, replays=1,
                                             max_tokens=ZAI_REGISTERED_MAX_TOKENS)}
    except Exception as exc:
        record["arms"]["cloud"] = {"status": "NOT-RUN", "model": ZAI_REGISTERED_MODEL,
                                   "error": f"{type(exc).__name__}: {exc}"}
    if not supplementary:
        record.pop("cloud_supplementary", None)
        return
    try:
        sup = get_provider("cloud", model=ZAI_SUPPLEMENTARY_MODEL)
        sup.probe()
        sup_arm = run_arm("cloud_sup", cells, sup, SEED, replays=1,
                          max_tokens=ZAI_SUPPLEMENTARY_MAX_TOKENS)
        record["cloud_supplementary"] = {
            "label": ("supplementary, NOT the registered arm: the account cannot "
                      "reach glm-5.3-flash (429 code 1113)"),
            "model": sup.model, "status": "RUN", **sup_arm}
    except Exception as exc:
        record["cloud_supplementary"] = {
            "status": "NOT-RUN", "model": ZAI_SUPPLEMENTARY_MODEL,
            "error": f"{type(exc).__name__}: {exc}"}


def receive_receipt(record, g):
    receipt_path, receipt = g.emit_receipt()
    entry = {"path": os.path.relpath(receipt_path, ROOT) if receipt_path else None,
             "receipt_id": (receipt or {}).get("receipt_id"),
             "gate_verdict": (receipt or {}).get("gate", {}).get("verdict"),
             "joules": (receipt or {}).get("energy", {}).get("joules"),
             "watt_hours": (receipt or {}).get("energy", {}).get("watt_hours")}
    if record.get("g7_receipt"):
        record.setdefault("g7_receipt_history", []).append(record["g7_receipt"])
    record["g7_receipt"] = entry
    return entry


def finalize(record) -> int:
    refusal = record["gates"]["refusal"]
    loc = record["arms"].get("local", {})
    det = loc.get("determinism", {}).get("byte_identical")
    local_wf = loc.get("well_formed_rate")
    cloud_wf = record["arms"].get("cloud", {}).get("well_formed_rate")
    sup_wf = record.get("cloud_supplementary", {}).get("well_formed_rate")

    gate_a = refusal["gate_100pct"]
    gate_b = bool(loc.get("status") == "RUN" and det is True)
    gate_c = bool(loc.get("status") == "RUN" and local_wf is not None and local_wf >= 0.95)
    arm_status = {k: v.get("status") for k, v in record["arms"].items()}
    runnable = sum(1 for s in arm_status.values() if s == "RUN")

    record["gates"].update({
        "A_refusal_100pct": {"pass": gate_a,
                             "refused": refusal["refused"], "n": refusal["n_cases"]},
        "B_local_determinism_3of3": {"pass": gate_b, "byte_identical": det,
                                     "replays": N_REPLAYS},
        "C_local_well_formed_ge_0_95": {
            "pass": gate_c, "local_rate": local_wf,
            "cloud_registered_rate": cloud_wf,
            "cloud_registered_status": record["arms"]["cloud"].get("status"),
            "cloud_supplementary_rate": sup_wf},
        "arms_runnable": runnable,
    })

    if runnable < 2:
        verdict = "INCONCLUSIVE"
        why = f"fewer than 2 arms runnable ({runnable}/3)"
    elif not gate_a:
        verdict = "KILL"
        why = ("guard bypass: a malformed envelope was accepted "
               f"({refusal['refused']}/{refusal['n_cases']} refused)")
    elif loc.get("status") != "RUN":
        verdict = "INCONCLUSIVE"
        why = "LOCAL arm not runnable — the local gate is untested"
    elif not gate_b:
        verdict = "KILL"
        why = "local nondeterminism at fixed seed 2718 / temperature 0"
    elif not gate_c:
        verdict = "KILL"
        why = (f"local well-formed rate {local_wf:.3f} < 0.95 — the pure "
               "envelope contract does not survive the real model")
    elif gate_a and gate_b and gate_c:
        verdict = "KEEP"
        why = "all three frozen gates pass"
    else:
        verdict = "INCONCLUSIVE"
        why = "no gate mapping matched"
    record["verdict"] = verdict
    record["verdict_reason"] = why
    record["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # -- Leak check: no secret may appear in artifacts ----------------------
    try:
        from xp_c_providers import _read_key
        key = _read_key("ZAI_KEY")
        hit = False
        for rel in (os.path.join("results", "xp_c", "xp_c_results.json"),
                    os.path.join("results", "xp_c", "local", "raw_runs.json")):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p) and key in open(p, encoding="utf-8", errors="replace").read():
                hit = True
        record["secret_scan"] = {"zai_key_present_in_artifacts": hit}
    except Exception as exc:
        record["secret_scan"] = {"zai_key_present_in_artifacts": None,
                                 "note": f"scan skipped: {type(exc).__name__}"}

    out = _write_json(os.path.join(OUT_DIR, "xp_c_results.json"), record)
    print(json.dumps({"verdict": verdict, "reason": why,
                      "gates": record["gates"], "arms": arm_status,
                      "receipt_id": record["g7_receipt"]["receipt_id"],
                      "artifact": os.path.relpath(out, ROOT)}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-worker", action="store_true")
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "local", "raw_runs.json"))
    ap.add_argument("--no-cloud", action="store_true")
    ap.add_argument("--resume", action="store_true",
                    help="reuse the existing record; re-run only the local arm")
    ap.add_argument("--cloud-only", action="store_true",
                    help="reuse the existing record; re-run only the cloud arm")
    ap.add_argument("--probe-determinism", action="store_true",
                    help="isolated 3-replay determinism probe under guard (no gates)")
    args = ap.parse_args()

    if args.local_worker:
        return local_worker(args.out)

    os.makedirs(OUT_DIR, exist_ok=True)
    cells = make_cells()
    res_path = os.path.join(OUT_DIR, "xp_c_results.json")

    if args.probe_determinism:
        status, err, attempts, g, local_out = local_phase("probe_raw_runs.json")
        receipt_path, receipt = g.emit_receipt()
        probe = {"probe": "isolated 3-replay determinism probe under guard",
                 "status": status, "error": err, "attempts": attempts,
                 "seed": SEED, "temperature": TEMPERATURE, "model": LOCAL_MODEL,
                 "receipt_id": (receipt or {}).get("receipt_id"),
                 "g7_gate": (receipt or {}).get("gate", {}).get("verdict")}
        if status == "RUN":
            with open(local_out) as f:
                arm = json.load(f)
            dig = [p["digests"] for p in arm["per_replay"]]
            diff = [i + 1 for i in range(N_PROMPTS)
                    if not (dig[0][i] == dig[1][i] == dig[2][i])]
            probe.update({"well_formed_per_replay": [p["well_formed"] for p in arm["per_replay"]],
                          "byte_identical": arm["determinism"]["byte_identical"],
                          "differing_prompts": diff})
            for i in diff:
                probe.setdefault("diffs", []).append({
                    "cell_id": f"cell_a{i+1:02d}",
                    "digests": [d[i] for d in dig],
                    "raws": [p["raws"][i] for p in arm["per_replay"]],
                    "errors": [[e["error"] for e in p["errors"] if e["cell_id"] == f"cell_a{i+1:02d}"]
                               for p in arm["per_replay"]]})
        out = _write_json(os.path.join(OUT_DIR, "determinism_probe_isolated.json"), probe)
        print(json.dumps(probe, indent=2)[:2000])
        return 0

    if args.resume:
        if not os.path.exists(res_path):
            print("fail loud: --resume but no existing record", file=sys.stderr)
            return 2
        with open(res_path) as f:
            record = json.load(f)
        record["resume_notes"] = (
            "local arm re-run after fixing a makedirs bug that dropped attempts 1-2 "
            "output (the calls ran; only the artifact write raised FileNotFoundError). "
            "Stub arm, refusal gate, and cloud results are carried forward unchanged "
            "from this same session. Previous guard summary preserved as "
            "guard_summary.pre-resume.json.")
        gs = os.path.join(OUT_DIR, "guard", "guard_summary.json")
        if os.path.exists(gs):
            import shutil
            shutil.copy2(gs, os.path.join(OUT_DIR, "guard", "guard_summary.pre-resume.json"))
        cloud_only = False
    elif args.cloud_only:
        if not os.path.exists(res_path):
            print("fail loud: --cloud-only but no existing record", file=sys.stderr)
            return 2
        with open(res_path) as f:
            record = json.load(f)
        record.setdefault("cloud_notes", []).append(
            "registered cloud arm re-run on the z.ai CODING endpoint "
            "(https://api.z.ai/api/coding/paas/v4/chat/completions): the payg "
            "endpoint answers 429 code 1113 for this account, and the coding "
            "endpoint is the shape this repo already uses (g1c/px2). Prior arm "
            "entry preserved in g7_receipt_history/cloud_arm_history.")
        record.setdefault("cloud_arm_history", []).append(record["arms"].get("cloud"))
        run_cloud_arms(record, cells, supplementary=False)
        return finalize(record)
    else:
        record = {
        "experiment": "XP-C envelope local provider",
        "prereg": "scratch/scout-2026-10-01-pushwave.md §3c",
        "claim": "the pure z_in->z_out cell contract survives a real model as Provider",
        "seed": SEED,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "n_prompts": N_PROMPTS,
        "n_replays_local": N_REPLAYS,
        "prompt_version": PROMPT_VERSION,
        "prompt_notes": ("v1 prompt (no literal shape example) scored 0/5 on a 5-prompt "
                          "plumbing probe; v2 adds a shape example + seed-is-number rule "
                          "and scored 6/6 on a 6-prompt probe. Frozen v2 used for the "
                          "gated run, plain chat (no JSON-mode crutch)."),
        "local_model": LOCAL_MODEL,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arms": {},
        "gates": {},
        "verdict": None,
        "house_law": "no g7 receipt -> run VOID",
        }

        # -- Gate A: refusal battery (CPU, no provider) --------------------
        refusal = run_refusal_gate(cells[0], seed=SEED)
        record["gates"]["refusal"] = refusal
        record["refusal_examples"] = [
            {"case": c["case"], "error_code": c["error_code"]} for c in refusal["cases"]]

        # -- ARM: STUB (ground truth) --------------------------------------
        stub = get_provider("stub")
        try:
            record["arms"]["stub"] = {"status": "RUN",
                                      **run_arm("stub", cells, stub, SEED, replays=N_REPLAYS)}
        except Exception as exc:
            record["arms"]["stub"] = {"status": "NOT-RUN",
                                      "error": f"{type(exc).__name__}: {exc}"}

        # -- ARM: CLOUD (z.ai) ---------------------------------------------
        if args.no_cloud:
            record["arms"]["cloud"] = {"status": "NOT-RUN", "error": "--no-cloud"}
        else:
            run_cloud_arms(record, cells, supplementary=True)

    # -- ARM: LOCAL (GPU, under guard.py) ----------------------------------
    local_status, local_err, attempts, g, local_out = local_phase()
    record.setdefault("local_attempts", []).extend(attempts)
    if local_status == "RUN":
        with open(local_out) as f:
            record["arms"]["local"] = {"status": "RUN", **json.load(f)}
    else:
        record["arms"]["local"] = {"status": "NOT-RUN", "error": local_err}

    # -- Receipt (G7) -------------------------------------------------------
    receive_receipt(record, g)

    return finalize(record)


if __name__ == "__main__":
    sys.exit(main())
