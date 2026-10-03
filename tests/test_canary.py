import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from canary import (CANARY_HEX, FLEET_CANARY, ACCENTED_TRAP, ALPHABET_CANARY,
                    CANON_GATES, fnv1a64, alphabet_canary)


def test_byte_canary():
    assert fnv1a64(CANARY_HEX) == FLEET_CANARY
    # Compare the INTEGER, never the text. The fleet writes the canary as
    # 0x024a555471370b18d -- SEVENTEEN hex digits; a u64 prints sixteen. Padded and
    # stripped forms are different STRINGS for the same number (fleetlint L9 trap).
    assert fnv1a64(CANARY_HEX) == 0x024A555471370B18D


def test_unaccented_twin_is_not_the_canary():
    assert fnv1a64("cafe Δ 日本語") == ACCENTED_TRAP
    assert fnv1a64("cafe Δ 日本語") != FLEET_CANARY


def test_alphabet_canary():
    assert alphabet_canary(CANON_GATES) == ALPHABET_CANARY


def test_NEGATIVE_CONTROL_renaming_a_gate_moves_the_pin():
    """Break it on purpose and watch the pin move (fleet-kit negative-control doctrine)."""
    renamed = [*CANON_GATES[:1], "cxr", *CANON_GATES[2:]]
    assert renamed != CANON_GATES
    assert alphabet_canary(renamed) != ALPHABET_CANARY
    assert alphabet_canary(CANON_GATES) == ALPHABET_CANARY
