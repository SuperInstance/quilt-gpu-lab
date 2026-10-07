"""AL-1 test pin: proj_lattice fnv1a64 UTF-8-byte dialect + SCOUT-64 collision-class census.

Pre-reg: proposals/runs/AL-1-proj-lattice-digest-dialect.md (frozen before fire).
"""
import importlib.util
import pathlib
import re
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = importlib.util.spec_from_file_location("proj_lattice_al1", TOOLS / "proj_lattice.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pl = _load()

# Pre-fix pinned values (captured 2026-10-07 pre-reg, /tmp/al1_prefix.json committed in booking)
PINNED = {
    "": "cbf29ce484222325",
    "abcdefgh": "25da8c1836a8d66d",
    "qrstuvwx": "a5beb10ce3cb36ad",
    "cat": "f5e307190ce4a327",
    "sat": "822d97195cd5ebf7",
}


def ref_fnv_utf8(text):
    """Independent UTF-8-byte FNV-1a64 reference (written from the spec, not the tool)."""
    h = 0xCBF29CE484222325
    for b in text.encode("utf-8"):
        h = ((h ^ b) * 0x100000001B3) % (1 << 64)
    return "%016x" % h


@pytest.mark.parametrize("text,digest", sorted(PINNED.items()))
def test_g2_ascii_invariance(text, digest):
    assert pl.fnv1a64(text) == digest


def test_g2_demo_genome_unchanged():
    assert pl.genome_digest(pl.DEMO_FABRIC) == "f01271c5aa10079f"


def test_g3_nonascii_utf8_dialect():
    assert pl.fnv1a64("é") == ref_fnv_utf8("é")
    assert pl.fnv1a64("naïve—γ") == ref_fnv_utf8("naïve—γ")
    assert pl.fnv1a64("naïve—γ") == pl.fnv1a64("naïve—γ")  # deterministic


def test_g3_ascii_gate_raises():
    bad = {"cells": [{"addr": "A", "dials": [1], "kind": "kïnd"}], "links": []}
    with pytest.raises(ValueError, match="non-ASCII genome part"):
        pl.genome_digest(bad)


def test_g4_scout64_collision_classes_differ():
    # eisenstein-embed fold makes these EQUAL (+8 stride / bucket collision);
    # our full-width digest must keep them distinct.
    assert pl.fnv1a64("abcdefgh") != pl.fnv1a64("qrstuvwx")
    assert pl.fnv1a64("cat") != pl.fnv1a64("sat")
    # alphabet stride pairs: a/b..i/j neighbors never share full digest
    letters = "abcdefghijklmnopqrstuvwxyz"
    ds = {c: pl.fnv1a64(c) for c in letters}
    assert len(set(ds.values())) == 26


def test_g4_no_mod2k_fold_in_tools():
    pat = re.compile(r"(fnv1a64\([^)]*\)\s*%\s*(?:0x40|64))|(&\s*0x3f\b.{0,40}fnv)", re.I)
    hits = []
    for f in TOOLS.glob("*.py"):
        src = f.read_text()
        for i, line in enumerate(src.splitlines(), 1):
            if pat.search(line):
                hits.append("%s:%d: %s" % (f.name, i, line.strip()))
    assert not hits, "mod-2^k fold of fnv digest found (SCOUT-64 rule): %r" % hits
