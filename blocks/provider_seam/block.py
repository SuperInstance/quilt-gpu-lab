#!/usr/bin/env python3
"""provider_seam — Provider interface + envelope assembly over envelope_guard.

Harvested from the proven XP-C seam (experiments/xp_c_providers.py +
experiments/xp_c_envelope.py; RESULTS.md XP-C entry, 2026-10-01;
results/xp_c/). The seam is the composition point: a dispatch goes in, a
provider is called, the envelope {cell_id, z_in_digest, z_out, provider,
seed} is assembled, and the SIBLING envelope_guard block validates it. Raw
string in, guard-validated envelope out — that import IS the composition.

Provider receipt (XP-C, 2026-10-01): STUB arm 30/30 well-formed and 3/3
byte-identical replays (ground truth); CLOUD arm (glm-5.3-flash, z.ai coding
endpoint) 30/30; LOCAL arm (qwen2.5:3b, ollama) KILLed — determinism FAIL +
well-formed 0.9333, failing by KEY OMISSION (provider/seed dropped) which the
guard refused as output.key_set. NO network provider is implemented in this
block (secrets + scope): the plug-in point is the Provider ABC, documented in
BLOCK.md COMPOSITION.

House contracts baked in: seed 2718 default · single JSON verdict on the final
stdout line · fail loud (ProviderError / guard Refusal; never silently degrade
to a stub) · no subprocess in this block · no secrets are read, printed, or
copied.
"""
from __future__ import annotations

import json
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCKS_ROOT = HERE.parent
ENVELOPE_GUARD_DIR = BLOCKS_ROOT / "envelope_guard"

# ── the composition: import the sibling block by its directory (sys.path
#    insertion), exactly as specified. If it cannot be imported, fail loud. ──
if str(ENVELOPE_GUARD_DIR) not in sys.path:
    sys.path.insert(0, str(ENVELOPE_GUARD_DIR))
try:
    import block as envelope_guard  # noqa: E402  — blocks/envelope_guard/block.py
except ImportError as exc:
    raise RuntimeError(f"FAIL LOUD: sibling block not importable from "
                       f"{ENVELOPE_GUARD_DIR}: {exc}") from None

Guard = envelope_guard.Guard
Dispatch = envelope_guard.Dispatch
Cell = envelope_guard.Cell
Refusal = envelope_guard.Refusal
fnv1a64 = envelope_guard.fnv1a64
SEED_DEFAULT = envelope_guard.SEED_DEFAULT
ENVELOPE_KEYS = envelope_guard.ENVELOPE_KEYS


class ProviderError(RuntimeError):
    """Loud provider failure — never silently degrade to a stub."""


# ── Provider interface (the frozen seam; any arm plugs in here) ──────────────
class Provider(ABC):
    """A model seat. provide() returns the RAW text the provider produced.

    emits_envelope=False (default): the raw text is the ANSWER (z_out); the
    seam assembles the binding fields from the dispatch and the guard
    validates. emits_envelope=True: the raw text IS the provider's own
    envelope-shaped JSON (the real-LLM arm path in XP-C: the prompt asks the
    model to emit the whole envelope) — the guard validates the provider's
    bytes directly, including every binding field it may have fumbled.
    """

    name: str = "provider"
    emits_envelope: bool = False

    @abstractmethod
    def provide(self, prompt: str, seed: int, temperature: float) -> str:
        ...  # -> raw provider output (str); anything else is a contract breach


class StubProvider(Provider):
    """Ground truth: a pure deterministic function of (prompt, seed).

    z_out is digest-derived; the XP-C stub arm scored 30/30 well-formed and
    3/3 byte-identical replays at seed 2718 / temperature 0 (results/xp_c/).
    The blueprint seed cross-check is the proven fail-loud behavior from
    xp_c_providers.py: the prompt must carry the same seed as the call.
    """

    name = "stub"
    emits_envelope = False

    def provide(self, prompt: str, seed: int, temperature: float) -> str:
        m = re.search(r"^seed = (.*)$", prompt, re.M)
        if not m:
            raise ProviderError("stub: blueprint field missing: seed")
        if int(m.group(1).strip()) != seed:
            raise ProviderError("stub: blueprint seed != call seed")
        return "stub:" + f"{fnv1a64(f'{prompt}|{seed}'):016x}"


class ReplayProvider(Provider):
    """Canned raw envelope responses keyed by prompt — for tests and for
    offline reproduction of real-arm failure modes (XP-C's local seat failed
    by omission: it dropped keys, the guard refused). A prompt with no canned
    response is a loud error — never degrade to something else."""

    name = "replay"
    emits_envelope = True

    def __init__(self, canned: dict[str, str]):
        self.canned = dict(canned)

    def provide(self, prompt: str, seed: int, temperature: float) -> str:
        if prompt not in self.canned:
            raise ProviderError("replay: no canned response for this prompt")
        return self.canned[prompt]


# ── the seam ─────────────────────────────────────────────────────────────────
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


class EnvelopeSeam:
    """dispatch -> input-schema check -> provider call -> envelope assembly ->
    guard validation. Returns the validated envelope dict; raises Refusal
    (guard) or ProviderError (wiring/provider contract) — never None, never a
    silent default."""

    def __init__(self, provider: Provider, guard: Guard | None = None,
                 temperature: float = 0.0, prompt_template: str = PROMPT_TEMPLATE):
        if not isinstance(provider, Provider):
            raise TypeError(f"FAIL LOUD: provider must be a Provider, got {type(provider).__name__}")
        self.provider = provider
        self.guard = guard if guard is not None else Guard()
        self.temperature = float(temperature)
        self.prompt_template = prompt_template

    def build_prompt(self, dispatch: Dispatch) -> str:
        return self.prompt_template.format(
            cell_id=dispatch.cell_id, digest=self.guard.digest(dispatch.z_in),
            provider=self.provider.name, seed=dispatch.seed, question=dispatch.z_in)

    def run(self, dispatch: Dispatch) -> dict:
        if not isinstance(dispatch, Dispatch):
            raise TypeError(f"FAIL LOUD: dispatch must be Dispatch, got {type(dispatch).__name__}")
        if dispatch.provider != self.provider.name:
            raise ProviderError(f"seam: dispatch.provider {dispatch.provider!r} != "
                                f"provider.name {self.provider.name!r} — refusing to mis-bind")
        self.guard.validate_input(Cell(dispatch.cell_id, dispatch.z_in))
        prompt = self.build_prompt(dispatch)
        raw = self.provider.provide(prompt, seed=dispatch.seed,
                                    temperature=self.temperature)
        if not isinstance(raw, str):
            raise ProviderError(f"provider returned {type(raw).__name__}, contract is str")
        if self.provider.emits_envelope:
            # real-LLM arm path: the provider's own bytes go to the guard,
            # binding fields included — a fumbled key is a refusal, not a patch
            return self.guard.validate_output(raw, dispatch)
        # answer path: the seam assembles the envelope around the raw answer;
        # the guard still validates everything, including the assembled digest
        env = {"cell_id": dispatch.cell_id,
               "z_in_digest": self.guard.digest(dispatch.z_in),
               "z_out": raw, "provider": self.provider.name,
               "seed": dispatch.seed}
        return self.guard.validate_output(json.dumps(env, ensure_ascii=False), dispatch)


# ── self-test ────────────────────────────────────────────────────────────────
def _dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)


def self_test() -> int:
    guard = Guard()
    stub = StubProvider()
    seam = EnvelopeSeam(stub, guard=guard)
    fails: list[str] = []

    # composition is real: the sibling block on disk is what we imported
    if not str(envelope_guard.__file__).replace("\\", "/").endswith(
            "blocks/envelope_guard/block.py"):
        fails.append(f"sibling import resolved to {envelope_guard.__file__}")

    dispatches = [Dispatch(f"cell_a{i + 1:02d}", q, stub.name, SEED_DEFAULT)
                  for i, q in enumerate(QUESTIONS)]
    if len(dispatches) != 30:
        fails.append(f"question bank must be 30, got {len(dispatches)}")

    # (1) stub arm through the seam: the XP-C 30/30-style loop, real guard
    accepted = 0
    envs = []
    for d in dispatches:
        try:
            envs.append(seam.run(d))
            accepted += 1
        except (Refusal, ProviderError) as exc:
            fails.append(f"stub dispatch {d.cell_id} refused: {exc}")
    keys_ok = all(set(e) == set(ENVELOPE_KEYS) for e in envs)
    zout_ok = all(e["z_out"].startswith("stub:") for e in envs)
    if accepted != 30 or not keys_ok or not zout_ok:
        fails.append(f"stub loop: accepted={accepted}/30 keys_ok={keys_ok} zout_ok={zout_ok}")

    # (2) determinism: 3 replays byte-identical (the XP-C stub receipt was
    #     3/3 byte-identical at seed 2718 / temperature 0)
    replay_raws = [[stub.provide(seam.build_prompt(d), seed=d.seed, temperature=0.0)
                    for d in dispatches] for _ in range(3)]
    byte_identical = all(r == replay_raws[0] for r in replay_raws[1:])
    if not byte_identical:
        fails.append("stub replays are not byte-identical")

    # (3) tampered raw output gets refused: empty z_out -> output.empty_z_out
    class _EmptyProvider(Provider):
        name = "stub"
        def provide(self, prompt, seed, temperature):
            return ""

    try:
        EnvelopeSeam(_EmptyProvider(), guard=guard).run(dispatches[0])
        fails.append("tampered empty z_out was accepted")
    except Refusal as r:
        if r.code != "output.empty_z_out":
            fails.append(f"tampered empty z_out: expected output.empty_z_out, got {r.code}")

    # provider returning non-str is a contract breach -> ProviderError, loud
    class _BytesProvider(Provider):
        name = "stub"
        def provide(self, prompt, seed, temperature):
            return b"not a str"

    try:
        EnvelopeSeam(_BytesProvider(), guard=guard).run(dispatches[0])
        fails.append("non-str provider output accepted")
    except ProviderError:
        pass
    except Refusal as r:
        fails.append(f"non-str provider output: ProviderError expected, got Refusal {r.code}")

    # (4) replay provider: valid canned envelope passes
    d0 = dispatches[0]
    good_replay_env = {"cell_id": d0.cell_id, "z_in_digest": guard.digest(d0.z_in),
                       "z_out": "a replayed answer", "provider": "replay",
                       "seed": d0.seed}
    replay_dispatch = Dispatch(d0.cell_id, d0.z_in, "replay", d0.seed)
    replay = ReplayProvider({})  # canned key must be THIS seam's prompt (provider name inside)
    replay_seam = EnvelopeSeam(replay, guard=guard)
    replay.canned[replay_seam.build_prompt(replay_dispatch)] = _dump(good_replay_env)
    try:
        env = replay_seam.run(replay_dispatch)
        if env["z_out"] != "a replayed answer":
            fails.append("replay valid envelope: wrong z_out")
    except (Refusal, ProviderError) as exc:
        fails.append(f"replay valid envelope refused: {exc}")

    # (5) XP-C failure-by-omission: the provider drops a key (the local seat's
    #     exact flake mode, cell_a08/cell_a13) -> output.key_set through the seam
    for dropped in ("seed", "provider"):
        env_missing = {k: v for k, v in good_replay_env.items() if k != dropped}
        rp = ReplayProvider({replay_seam.build_prompt(replay_dispatch): _dump(env_missing)})
        try:
            EnvelopeSeam(rp, guard=guard).run(replay_dispatch)
            fails.append(f"replay omission of {dropped}: accepted")
        except Refusal as r:
            if r.code != "output.key_set":
                fails.append(f"replay omission of {dropped}: expected output.key_set, got {r.code}")

    # (6) a provider that fakes the binding digest -> output.digest_mismatch
    env_fake = {**good_replay_env, "z_in_digest": "0123456789abcdef"}
    rp_fake = ReplayProvider({replay_seam.build_prompt(replay_dispatch): _dump(env_fake)})
    try:
        EnvelopeSeam(rp_fake, guard=guard).run(replay_dispatch)
        fails.append("replay fake digest accepted")
    except Refusal as r:
        if r.code != "output.digest_mismatch":
            fails.append(f"replay fake digest: expected output.digest_mismatch, got {r.code}")

    # (7) replay with no canned response -> ProviderError, never a degrade
    try:
        replay_seam.run(dispatches[1])
        fails.append("replay unknown prompt accepted")
    except ProviderError:
        pass
    except Refusal as r:
        fails.append(f"replay unknown prompt: ProviderError expected, got Refusal {r.code}")

    # (8) dispatch/provider name mismatch -> ProviderError before any call
    try:
        seam.run(Dispatch(d0.cell_id, d0.z_in, "cloud", d0.seed))
        fails.append("provider name mismatch accepted")
    except ProviderError:
        pass

    booking = {"block": "provider_seam",
               "receipt": "RESULTS.md XP-C entry (2026-10-01), results/xp_c/ "
                          "— stub 30/30 + 3/3 byte-identical; cloud 30/30; "
                          "local KILL 0.9333 failing by omission (output.key_set)",
               "stub_loop": f"{accepted}/30",
               "stub_replays_byte_identical": byte_identical,
               "omission_mode": "dropped seed/provider -> output.key_set (reproduced)",
               "binding_tamper": "fake z_in_digest -> output.digest_mismatch (reproduced)",
               "composition": f"envelope_guard @ {envelope_guard.__file__}"}
    print("SEAM " + json.dumps(booking, sort_keys=True), flush=True)

    final = "PASS" if not fails else "FAIL"
    for f in fails:
        print(f"SELFTEST-FAIL {f}", file=sys.stderr, flush=True)
    print(json.dumps({"verdict": final}), flush=True)  # exactly one top-level field
    return 0 if final == "PASS" else 1


if __name__ == "__main__":
    sys.exit(self_test())
