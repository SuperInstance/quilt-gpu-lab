#!/usr/bin/env python3
"""envelope_guard — strict validation core for the z_in -> z_out cell envelope.

Harvested from the proven XP-C Guard layer (experiments/xp_c_envelope.py;
RESULTS.md XP-C entry, 2026-10-01; results/xp_c/). In the XP-C run this layer
refused 20/20 deliberate envelope malformations (each with a structured error
code), 5/5 extra strictness cases, and 4/4 malformed input cells — the
strongest part of the build. What it validates: the provider's raw output must
be exactly one strict JSON object with exactly the 5 envelope keys, and it must
BIND to the dispatch (cell_id, provider, seed, and a z_in_digest of the
DISPATCHED z_in). Binding is what makes an envelope a receipt rather than
decoration.

Digest: FNV-1a-64, hand-rolled below (digest_algo="fnv1a64"), rendered as 16
lowercase hex chars — the same 16-hex digest shape XP-C used (XP-C used
sha256[:16]; the hex16 contract is identical, see BLOCK.md).

Fail loud: malformed anything -> structured Refusal (code + detail +
raw_digest). validate_output never lets a parse exception escape and never has
a lenient accept path.

House contracts baked in: seed 2718 default · single JSON verdict on the final
stdout line · fail loud (structured refusals, booked codes) · no subprocess in
this block · no secrets are read, printed, or copied.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent

SEED_DEFAULT = 2718  # house seed

ENVELOPE_KEYS = ("cell_id", "z_in_digest", "z_out", "provider", "seed")
CELL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{2,40}$")
HEX16_RE = re.compile(r"^[0-9a-f]{16}$")

# Stable refusal codes (the contract; do not renumber/reword):
#   input.not_a_cell, input.bad_cell_id, input.empty_z_in
#   output.not_text, output.empty, output.not_json, output.not_object,
#   output.key_set, output.type.cell_id, output.type.z_in_digest,
#   output.type.z_out, output.type.provider, output.type.seed,
#   output.empty_z_out, output.bad_digest_format, output.digest_mismatch,
#   output.cell_id_mismatch, output.provider_mismatch, output.seed_mismatch

FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x100000001B3
FNV1A64_MASK = 0xFFFFFFFFFFFFFFFF


def fnv1a64(data) -> int:
    """FNV-1a-64 over bytes (str is encoded utf-8). Hand-rolled, stdlib only."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = FNV1A64_OFFSET
    for b in data:
        h = ((h ^ b) * FNV1A64_PRIME) & FNV1A64_MASK
    return h


def digest_text(text: str) -> str:
    """The z_in digest: 16 lowercase hex chars of FNV-1a-64."""
    if not isinstance(text, str):
        raise TypeError(f"FAIL LOUD: digest_text expects str, got {type(text).__name__}")
    return f"{fnv1a64(text):016x}"


class Refusal(Exception):
    """Structured refusal — the ONLY failure mode of the Guard.

    Carries the XP-C refusal shape: refused/error/detail/raw_digest.
    """

    def __init__(self, code: str, detail: str, raw=None):
        self.code = code
        self.detail = detail
        self.raw_digest = _raw_digest(raw)
        super().__init__(f"{code}: {detail} (raw_digest={self.raw_digest})")

    def as_dict(self) -> dict:
        return {"refused": True, "error": self.code, "detail": self.detail,
                "raw_digest": self.raw_digest}


def _raw_digest(raw) -> str:
    if not isinstance(raw, str):
        try:
            raw = json.dumps(raw, sort_keys=True, default=str)
        except Exception:
            raw = repr(raw)
    return digest_text(raw)


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


@dataclass(frozen=True)
class Dispatch:
    """What was dispatched to the provider: cell + input + provider + seed.
    The envelope must bind to ALL of these (the receipt checks)."""
    cell_id: str
    z_in: str
    provider: str
    seed: int = SEED_DEFAULT


class Cell:
    """A pure z_in -> z_out cell: an id + its input text (input-schema side)."""

    def __init__(self, cell_id: str, z_in: str):
        self.cell_id = cell_id
        self.z_in = z_in

    @property
    def z_in_digest(self) -> str:
        return digest_text(self.z_in)


class Guard:
    """Strict envelope guard. digest_algo is fixed at construction (fail loud
    on anything but the shipped 'fnv1a64'); there is no lenient mode."""

    def __init__(self, digest_algo: str = "fnv1a64"):
        if digest_algo != "fnv1a64":
            raise ValueError(f"FAIL LOUD: unsupported digest_algo {digest_algo!r} "
                             "(this block ships 'fnv1a64' only)")
        self.digest_algo = digest_algo

    def digest(self, text: str) -> str:
        return digest_text(text)

    digest_z_in = digest

    def validate_input(self, cell) -> None:
        """INPUT schema check. Raises Refusal; returns None on accept."""
        if not isinstance(cell, Cell):
            raise Refusal("input.not_a_cell",
                          f"expected Cell, got {type(cell).__name__}", cell)
        if not isinstance(cell.cell_id, str) or not CELL_ID_RE.match(cell.cell_id):
            raise Refusal("input.bad_cell_id", f"cell_id={cell.cell_id!r}", cell)
        if not isinstance(cell.z_in, str) or not cell.z_in.strip():
            raise Refusal("input.empty_z_in", "z_in must be a non-empty string", cell)

    def validate_output(self, raw: str, dispatch: Dispatch) -> dict:
        """OUTPUT envelope schema check + binding vs the dispatch.

        Returns the parsed envelope (exactly the 5 keys) on accept.
        Raises Refusal — with a stable code — on ANY malformation. There is no
        lenient path and no exception escape from parsing.
        """
        if not isinstance(dispatch, Dispatch):
            raise TypeError(f"FAIL LOUD: dispatch must be Dispatch, got {type(dispatch).__name__}")
        if not isinstance(raw, str):
            raise Refusal("output.not_text", f"provider returned {type(raw).__name__}", raw)
        text = raw.strip()
        if not text:
            raise Refusal("output.empty", "empty provider output", raw)
        try:
            env = _strict_loads(text)
        except Exception as exc:
            raise Refusal("output.not_json", f"{type(exc).__name__}: {exc}", raw) from None
        if not isinstance(env, dict):
            raise Refusal("output.not_object", f"top level is {type(env).__name__}", raw)

        keys = set(env.keys())
        want = set(ENVELOPE_KEYS)
        if keys != want:
            raise Refusal("output.key_set",
                          f"missing={sorted(want - keys)} extra={sorted(keys - want)}", raw)

        if not isinstance(env["cell_id"], str):
            raise Refusal("output.type.cell_id", "cell_id must be str", raw)
        if not isinstance(env["z_in_digest"], str):
            raise Refusal("output.type.z_in_digest", "z_in_digest must be str", raw)
        if not isinstance(env["z_out"], str):
            raise Refusal("output.type.z_out", "z_out must be str", raw)
        if not isinstance(env["provider"], str):
            raise Refusal("output.type.provider", "provider must be str", raw)
        # bool is a subclass of int — reject it explicitly
        if isinstance(env["seed"], bool) or not isinstance(env["seed"], int):
            raise Refusal("output.type.seed", "seed must be int", raw)

        if not env["z_out"]:
            raise Refusal("output.empty_z_out", "z_out must be non-empty", raw)
        if not HEX16_RE.match(env["z_in_digest"]):
            raise Refusal("output.bad_digest_format",
                          f"z_in_digest={env['z_in_digest']!r} not 16 hex", raw)

        # binding checks — the envelope must bind to THIS cell/input/provider/seed
        if env["cell_id"] != dispatch.cell_id:
            raise Refusal("output.cell_id_mismatch",
                          f"{env['cell_id']!r} != {dispatch.cell_id!r}", raw)
        if env["z_in_digest"] != self.digest(dispatch.z_in):
            raise Refusal("output.digest_mismatch",
                          "z_in_digest does not bind the dispatched z_in", raw)
        if env["provider"] != dispatch.provider:
            raise Refusal("output.provider_mismatch",
                          f"{env['provider']!r} != {dispatch.provider!r}", raw)
        if env["seed"] != dispatch.seed:
            raise Refusal("output.seed_mismatch",
                          f"{env['seed']!r} != {dispatch.seed!r}", raw)
        return env


# ── self-test ────────────────────────────────────────────────────────────────
def _dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)


def _outcome(guard: Guard, raw, dispatch: Dispatch):
    """(accepted, code_or_None, refusal_or_envelope) — never raises."""
    try:
        env = guard.validate_output(raw, dispatch)
    except Refusal as r:
        return False, r.code, r
    return True, None, env


def self_test() -> int:
    guard = Guard()
    d = Dispatch("cell_a01", "Name the color of a clear noon sky in one word.",
                 "stub", SEED_DEFAULT)
    g = {"cell_id": d.cell_id, "z_in_digest": guard.digest(d.z_in),
         "z_out": "a valid answer", "provider": d.provider, "seed": d.seed}
    fails: list[str] = []

    def expect_refusal(label: str, raw, code: str) -> int:
        """Returns 1 iff refused with exactly `code` and the structured shape."""
        accepted, got, refusal = _outcome(guard, raw, d)
        structured = (not accepted and isinstance(refusal, Refusal)
                      and set(refusal.as_dict()) == {"refused", "error", "detail", "raw_digest"}
                      and refusal.as_dict()["refused"] is True)
        if accepted or got != code or not structured:
            fails.append(f"{label}: expected refusal {code}, got accept={accepted} code={got}")
            return 0
        return 1

    def expect_accept(label: str, raw):
        accepted, got, env = _outcome(guard, raw, d)
        if not accepted or env.get("z_out") != "a valid answer":
            fails.append(f"{label}: expected accept, got code={got}")

    # ── digest known-answer vectors (FNV-1a-64 reference values) ──
    if fnv1a64(b"") != 0xCBF29CE484222325:
        fails.append("fnv KAT empty")
    if fnv1a64(b"a") != 0xAF63DC4C8601EC8C:
        fails.append("fnv KAT a")
    if fnv1a64(b"foobar") != 0x85944171F73967E8:
        fails.append("fnv KAT foobar")
    if digest_text("") != "cbf29ce484222325" or not HEX16_RE.match(guard.digest(d.z_in)):
        fails.append("digest_text hex16 shape")

    # unknown digest algo must fail loud at construction
    try:
        Guard("sha256")
        fails.append("Guard('sha256') should raise")
    except ValueError:
        pass

    # ── the XP-C gate-A battery: EXACTLY 20 deliberate malformations,
    #    ported label-for-label from xp_c_envelope.py:refusal_battery ──
    xp20 = [
        ("not_json_prose", "Sure! Here is your answer: the sky is blue.", "output.not_json"),
        ("empty_string", "", "output.empty"),
        ("truncated_json", _dump(g)[:-12], "output.not_json"),
        ("json_array", _dump([g]), "output.not_object"),
        ("missing_cell_id", _dump({k: v for k, v in g.items() if k != "cell_id"}), "output.key_set"),
        ("missing_z_in_digest", _dump({k: v for k, v in g.items() if k != "z_in_digest"}), "output.key_set"),
        ("missing_z_out", _dump({k: v for k, v in g.items() if k != "z_out"}), "output.key_set"),
        ("missing_provider", _dump({k: v for k, v in g.items() if k != "provider"}), "output.key_set"),
        ("missing_seed", _dump({k: v for k, v in g.items() if k != "seed"}), "output.key_set"),
        ("extra_key", _dump({**g, "note": "sneaky"}), "output.key_set"),
        ("wrong_type_z_out_int", _dump({**g, "z_out": 7}), "output.type.z_out"),
        ("wrong_type_seed_str", _dump({**g, "seed": str(d.seed)}), "output.type.seed"),
        ("wrong_type_seed_bool", _dump({**g, "seed": True}), "output.type.seed"),
        ("digest_mismatch", _dump({**g, "z_in_digest": "0123456789abcdef"}), "output.digest_mismatch"),
        ("digest_bad_format", _dump({**g, "z_in_digest": "ZZZZZZZZZZZZZZZZ"}), "output.bad_digest_format"),
        ("cell_id_mismatch", _dump({**g, "cell_id": "cell_zzz"}), "output.cell_id_mismatch"),
        ("provider_mismatch", _dump({**g, "provider": "not-stub"}), "output.provider_mismatch"),
        ("seed_mismatch", _dump({**g, "seed": d.seed + 1}), "output.seed_mismatch"),
        ("empty_z_out", _dump({**g, "z_out": ""}), "output.empty_z_out"),
        ("duplicate_key", '{"cell_id": "%s", "z_in_digest": "%s", "z_out": "x", '
         '"provider": "stub", "seed": %d, "cell_id": "cell_zzz"}'
         % (g["cell_id"], g["z_in_digest"], d.seed), "output.not_json"),
    ]
    # block-only output codes, exercised by their own triggers (the XP-C
    # battery never triggered these four — they are the block's additions)
    block_extra = [
        ("not_text", 7, "output.not_text"),
        ("wrong_type_cell_id", _dump({**g, "cell_id": 7}), "output.type.cell_id"),
        ("wrong_type_z_in_digest", _dump({**g, "z_in_digest": 123}), "output.type.z_in_digest"),
        ("wrong_type_provider", _dump({**g, "provider": ["stub"]}), "output.type.provider"),
    ]
    assert len(xp20) == 20, "gate A requires exactly 20 malformations"
    xp20_refused = sum(expect_refusal(label, raw, code) for label, raw, code in xp20)
    extra_codes_refused = sum(expect_refusal(label, raw, code)
                              for label, raw, code in block_extra)

    # ── 5 extra strictness cases (reported beside the gate in XP-C) ──
    extras = [
        ("whitespace_only", "   \n\t  ", "output.empty"),
        ("json_scalar", "42", "output.not_object"),
        ("fenced_json", "```json\n" + _dump(g) + "\n```", "output.not_json"),
        ("json_embedded_in_prose", "Here you go: " + _dump(g), "output.not_json"),
        ("nan_value", '{"cell_id": "%s", "z_in_digest": "%s", "z_out": NaN, '
         '"provider": "stub", "seed": %d}' % (g["cell_id"], g["z_in_digest"], d.seed),
         "output.not_json"),
    ]
    extras_refused = sum(expect_refusal(label, raw, code) for label, raw, code in extras)

    # ── input schema: 4 malformed cells (plus the not-a-cell case) ──
    input_cases = [
        ("bad_cell_id_upper", Cell("BAD ID", "q"), "input.bad_cell_id"),
        ("bad_cell_id_short", Cell("a", "q"), "input.bad_cell_id"),
        ("empty_z_in", Cell("cell_ok", "   "), "input.empty_z_in"),
        ("z_in_not_str", Cell("cell_ok", 5), "input.empty_z_in"),
        ("not_a_cell", {"cell_id": "cell_a01", "z_in": "q"}, "input.not_a_cell"),
    ]
    input_refused = 0
    for label, cell, code in input_cases:
        try:
            guard.validate_input(cell)
            fails.append(f"{label}: expected input refusal {code}, got accept")
        except Refusal as r:
            input_refused += 1
            if r.code != code:
                fails.append(f"{label}: expected {code}, got {r.code}")

    # ── accept path + binding sanity (good envelope must pass; a re-bound
    #    envelope against a WRONG dispatch must fail on each binding axis) ──
    expect_accept("valid_envelope", _dump(g))
    for label, dd, code in [
        ("bind_wrong_digest", Dispatch(d.cell_id, d.z_in + "x", d.provider, d.seed), "output.digest_mismatch"),
        ("bind_wrong_cell_id", Dispatch("cell_zzz", d.z_in, d.provider, d.seed), "output.cell_id_mismatch"),
        ("bind_wrong_provider", Dispatch(d.cell_id, d.z_in, "cloud", d.seed), "output.provider_mismatch"),
        ("bind_wrong_seed", Dispatch(d.cell_id, d.z_in, d.provider, d.seed + 1), "output.seed_mismatch"),
    ]:
        accepted, got, _ = _outcome(guard, _dump(g), dd)
        if accepted or got != code:
            fails.append(f"{label}: expected {code}, got accept={accepted} code={got}")

    # ── never-escape fuzz: nothing malformed may produce a non-Refusal ──
    for nasty in (b"{}", None, ["x"], {"a": 1}, 3.14, object()):
        try:
            guard.validate_output(nasty, d)
            fails.append(f"fuzz {type(nasty).__name__}: accepted")
        except Refusal:
            pass
        except Exception as exc:  # a non-Refusal escape IS the failure mode
            fails.append(f"fuzz {type(nasty).__name__}: escaped as {type(exc).__name__}")

    booking = {"block": "envelope_guard",
               "receipt": "RESULTS.md XP-C entry (2026-10-01), results/xp_c/ "
                          "— gate A 20/20 + 5/5 strictness + 4/4 input",
               "gate_A_xp20": f"{xp20_refused}/20",
               "block_extra_codes": f"{extra_codes_refused}/{len(block_extra)}",
               "extra_strictness": f"{extras_refused}/{len(extras)}",
               "input_schema": f"{input_refused}/{len(input_cases)}",
               "digest": "fnv1a64/hex16 (KATs verified)",
               "codes_exercised": sorted({c for _, _, c in xp20 + block_extra + extras + input_cases})}
    print("GUARD " + json.dumps(booking, sort_keys=True), flush=True)

    final = "PASS" if not fails else "FAIL"
    for f in fails:
        print(f"SELFTEST-FAIL {f}", file=sys.stderr, flush=True)
    print(json.dumps({"verdict": final}), flush=True)  # exactly one top-level field
    return 0 if final == "PASS" else 1


if __name__ == "__main__":
    sys.exit(self_test())
