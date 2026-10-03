"""The fleet canary, and the alphabet canary that should have existed all along.

Adapted verbatim from SuperInstance/fleet-kit fleetlint/templates (MIT). The byte canary
is applied to a FIXTURE STRING; the alphabet canary is applied to the NAMES of our canon
(the qcell gate vocabulary in tools/qcell_sim.py: h, x, rx, rz, cx, crx, swap).
One line of input, and a gate rename fails the same day (canons SCOUT-2235Z / MERGER class).
"""
M = (1 << 64) - 1
CANARY_HEX = "café Δ 日本語"          # fixture string
FLEET_CANARY = 0x24A555471370B18D     # byte canary — compare as INTEGER, never text
#   Canon (fleet-kit e06f00a, 2026-10-02): canonical TEXT is 16 hex digits, no leading
#   zero. The same integer written 0x024A55... is L9(d) non-canonical — a grep for the
#   canon cannot match it ("a check that cannot fail is worse than no check").
ACCENTED_TRAP = 0xFEE91CF40962B966    # unaccented twin; never a canary
CANON_GATES = ["crx", "cx", "h", "rx", "rz", "swap", "x"]  # tools/qcell_sim.py gate set
ALPHABET_CANARY = 0xCA289D4829D9A834  # FNV-1a64 over sorted canon gates joined by '|'


def fnv1a64(s: str) -> int:
    h = 14695981039346656037
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 1099511628211) & M
    return h


def alphabet_canary(opcodes, sep="|") -> int:
    """Proves the NAMES of the canon are unchanged."""
    return fnv1a64(sep.join(sorted(opcodes)))


def _is_canonical_pin_text(s: str) -> bool:
    """L9(d): canonical pin TEXT is '0x' + 16 hex digits, no leading zero."""
    return (isinstance(s, str) and s.startswith("0x") and len(s) == 18
            and s[2] in "123456789abcdef"
            and all(c in "0123456789abcdef" for c in s[2:]))


def control_ladder() -> dict:
    """CAN-1 control ladder (crab-traps template, SCOUT-30). Runs entirely IN-MEMORY —
    writes nothing, dirties no tree (pre-reg gate G2). Returns {rung: (expect_red, observed_red)}.
    Ladder PASS iff every expect_red rung observed_red and the positive rung is green."""
    rungs = {}

    def check(name, expect_red, ok):
        rungs[name] = (expect_red, bool(ok))

    # POS: canonical fixture + canonical pin => green (digest agrees, pin text canonical).
    pos_ok = fnv1a64(CANARY_HEX) == FLEET_CANARY and _is_canonical_pin_text(hex(FLEET_CANARY))
    check("POS", False, not pos_ok)  # second element is uniformly FIRED(=red)

    # T1 tamper-expectation: flip one hex digit of the expected pin => detector MISMATCH.
    t1_pin = FLEET_CANARY ^ 0x1
    check("T1-tamper-expectation", True, fnv1a64(CANARY_HEX) != t1_pin)

    # T2 wrong-pin-tip: non-canonical text (leading-zero form) must fail the canonical-text check.
    check("T2-wrong-pin-tip", True, not _is_canonical_pin_text("0x024a555471370b18d"))

    # T3 tamper-input-bytes: unaccented twin of the fixture must diverge from the pin.
    tampered = CANARY_HEX.replace("café", "cafe")
    check("T3-tamper-input-bytes", True, tampered != CANARY_HEX and fnv1a64(tampered) != FLEET_CANARY)

    # T4 tamper-canon-ops: rename one gate => alphabet pin moves.
    renamed = [*CANON_GATES[:1], "cxr", *CANON_GATES[2:]]
    check("T4-tamper-canon-ops", True, alphabet_canary(renamed) != ALPHABET_CANARY
          and alphabet_canary(CANON_GATES) == ALPHABET_CANARY)

    return rungs


def ladder_verdict(rungs: dict) -> tuple:
    """(ok, reason). Fail-closed: every expect_red rung must be red; POS must be green."""
    for name, (expect_red, observed_red) in rungs.items():
        if expect_red and not observed_red:
            return False, f"{name} did not fire (control cannot fail — worse than no check)"
        if not expect_red and observed_red:
            return False, f"{name} fired on the canonical state"
    return True, f"all {len(rungs)} rungs correct"
