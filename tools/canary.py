"""The fleet canary, and the alphabet canary that should have existed all along.

Adapted verbatim from SuperInstance/fleet-kit fleetlint/templates (MIT). The byte canary
is applied to a FIXTURE STRING; the alphabet canary is applied to the NAMES of our canon
(the qcell gate vocabulary in tools/qcell_sim.py: h, x, rx, rz, cx, crx, swap).
One line of input, and a gate rename fails the same day (canons SCOUT-2235Z / MERGER class).
"""
M = (1 << 64) - 1
CANARY_HEX = "café Δ 日本語"          # fixture string
FLEET_CANARY = 0x024A555471370B18D    # byte canary — compare as INTEGER, never text
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
