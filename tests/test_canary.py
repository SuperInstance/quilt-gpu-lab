import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from canary import (CANARY_HEX, FLEET_CANARY, ACCENTED_TRAP, ALPHABET_CANARY,
                    CANON_GATES, fnv1a64, alphabet_canary, control_ladder, ladder_verdict)


def test_byte_canary():
    assert fnv1a64(CANARY_HEX) == FLEET_CANARY
    # Compare the INTEGER, never the text. Canon (fleet-kit e06f00a, 2026-10-02):
    # the canonical TEXT form is 16 hex digits, no leading zero; the same integer
    # written 0x024a55... (17 digits) is the L9(d) non-canonical string a canon grep
    # cannot match. Pin BOTH: value agreement and canonical text form.
    assert fnv1a64(CANARY_HEX) == 0x24A555471370B18D


def test_canary_TEXT_is_canonical_L9d():
    """L9(d): a non-canonical canary string means a grep for the canon cannot match.
    Our constant's text must be exactly 16 hex digits, uppercase, no leading zero."""
    s = hex(FLEET_CANARY)
    assert s == "0x24a555471370b18d"
    assert len(s) == 18  # 0x + 16 digits
    assert FLEET_CANARY.to_bytes(8, "big")[0] == 0x24


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


def test_CAN1_ladder_all_rungs():
    """CAN-1 G1: T1-T4 RED, POS GREEN, in one run."""
    rungs = control_ladder()
    assert set(rungs) == {"POS", "T1-tamper-expectation", "T2-wrong-pin-tip",
                          "T3-tamper-input-bytes", "T4-tamper-canon-ops"}
    ok, reason = ladder_verdict(rungs)
    assert ok, reason


def test_CAN1_ladder_mutation_sanity():
    """CAN-1 G3: the ladder itself is verified — sabotage a rung's detector and the
    verdict must flip fail-closed (crab-traps: 1 hex flip => EXIT=1 doctrine)."""
    rungs = control_ladder()
    name = "T3-tamper-input-bytes"
    expect_red, _ = rungs[name]
    rungs[name] = (expect_red, False)  # simulate a detector blind to the tamper
    ok, reason = ladder_verdict(rungs)
    assert not ok and name in reason
