#!/usr/bin/env python3
"""test_receipts.py — the lab's first verification pins.

Dogfood of the fleet's FAIL-first doctrine: every pin here must be
demonstrably RED on the state it guards against, before it can go green.
Run: python -m unittest discover -s tests -v   (or: python tests/test_receipts.py)

Pins:
  1. queue/results consistency — every checked QUEUE item has at least
     one RESULTS entry and vice versa (the cron loop can drift: a
     check-off without a run, an append that missed the box).
  2. every RESULTS entry names an experiment file that exists — a
     verdict whose code left the repo is a claim no one can re-run.
  3. receipts/manifest.json matches the working tree — digests are
     re-derived, never trusted. Regenerate via tools/receipt_manifest.py.
  4. doctrine citation drift — the README's Doctrine provenance block
     names the canonical source (SuperInstance/AI-Writings, algebra.md).
     A doctrine no one names is a doctrine no one can trace.
  5. edge drift — the provenance names the canonical WAL producer
     (SuperInstance/git-agent, quilt_emit): the referral edge
     aw-quint-opcode -> gl-ledgers must be named where the doctrine is
     claimed, or the weight law cannot mint it.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "tools"))
import receipt_manifest  # noqa: E402

QUEUE = LAB / "QUEUE.md"
RESULTS = LAB / "RESULTS.md"
MANIFEST = LAB / "receipts" / "manifest.json"

# Experiments legitimately run from outside this repo. Any entry here is
# a DECLARED external — the pin still requires a RESULTS note naming it.
DECLARED_EXTERNALS: frozenset[str] = frozenset({"E5"})  # subsumed by D7, never run standalone

CHECKED_RE = re.compile(r"^- \[x\] ([ED][0-9]+[a-z]?)\s", re.M)
UNCHECKED_RE = re.compile(r"^- \[ \] ([ED][0-9]+[a-z]?)\s", re.M)
RESULTS_H_RE = re.compile(r"^## ([ED][0-9]+[a-z]?)\b", re.M)


def queue_ids(text: str) -> tuple[set[str], set[str]]:
    return set(CHECKED_RE.findall(text)), set(UNCHECKED_RE.findall(text))


def results_ids(text: str) -> list[str]:
    return RESULTS_H_RE.findall(text)


class QueueResultsConsistency(unittest.TestCase):
    def test_checked_items_have_results(self):
        checked, _ = queue_ids(QUEUE.read_text())
        have = set(results_ids(RESULTS.read_text()))
        missing = checked - have
        self.assertEqual(missing, set(),
                         f"QUEUE items checked but no RESULTS entry: {sorted(missing)}")

    def test_results_have_checked_queue_items(self):
        checked, _ = queue_ids(QUEUE.read_text())
        for rid in results_ids(RESULTS.read_text()):
            self.assertIn(rid, checked,
                          f"RESULTS entry {rid} has no checked QUEUE item — "
                          "the run was never claimed")


class ExperimentFilesExist(unittest.TestCase):
    def test_every_result_entry_has_a_file(self):
        for rid in set(results_ids(RESULTS.read_text())):
            if rid in DECLARED_EXTERNALS:
                continue
            prefix = rid[0].lower()          # 'E' -> 'e', 'D' -> 'd'
            slug = rid[1:].lower()           # 'E2b' -> '2b'
            pat = f"{prefix}{slug}_*.py"
            hits = list((LAB / "experiments").glob(pat))
            self.assertTrue(hits,
                            f"RESULTS entry {rid} has no experiments/{pat} — "
                            "a verdict whose code left the repo cannot be re-run")


class ReceiptManifestMatches(unittest.TestCase):
    def test_manifest_matches_working_tree(self):
        self.assertTrue(MANIFEST.exists(),
                        "receipts/manifest.json missing — regenerate via "
                        "python tools/receipt_manifest.py and commit it WITH your change")
        on_disk = json.loads(MANIFEST.read_text())
        live = receipt_manifest.build()
        for ledger, digest in live["ledgers"].items():
            self.assertEqual(on_disk["ledgers"].get(ledger), digest,
                             f"{ledger} drifted from the sealed digest — regenerate "
                             "the manifest (tools/receipt_manifest.py), never edit it by hand")
        self.assertEqual(on_disk.get("experiments"), live["experiments"],
                         "experiment digests drifted — regenerate the manifest")
        self.assertEqual(on_disk.get("tools"), live["tools"],
                         "tool/weight digests drifted — regenerate the manifest "
                         "(tools/receipt_manifest.py) and commit it WITH your change")


class RC5PushCheck(unittest.TestCase):
    """RC-5 (2026-10-02, MicroMoth #32 auto-push class): the push-time layer
    of the seal pin — an un-resealed landing goes red at push time, not
    red-on-next-clone. FAIL-first: check() did not exist before this feature;
    the tamper arm below is red against any module lacking the drift diff."""

    def test_clean_tree_checks_clean(self):
        drift = receipt_manifest.check()
        self.assertEqual(drift, [],
                         f"sealed manifest drifted from tree: {drift}")

    def test_tampered_digest_is_named(self):
        import copy
        sealed = json.loads(MANIFEST.read_text())
        sealed["ledgers"]["RESULTS.md"] = "0" * 64
        original = MANIFEST.read_bytes()  # restore the live file, NOT the git
        # index: a fresh seal not yet committed is legitimate state (RC-5 fix,
        # the index-restore clobbered the seal made moments earlier)
        MANIFEST.write_text(json.dumps(sealed, indent=2) + "\n")
        try:
            drift = receipt_manifest.check()
        finally:
            MANIFEST.write_bytes(original)
        self.assertTrue(any("RESULTS.md" in ln and "DRIFT" in ln for ln in drift),
                        f"tampered RESULTS.md digest not named: {drift}")


class DoctrineProvenance(unittest.TestCase):
    def test_readme_names_canonical_source(self):
        text = (LAB / "README.md").read_text()
        self.assertIn("SuperInstance/AI-Writings", text,
                      "README Doctrine provenance must name the canonical source "
                      "(SuperInstance/AI-Writings, algebra.md) — a doctrine no one "
                      "names is a doctrine no one can trace")
        self.assertIn("algebra.md", text)

    def test_edge_named_in_provenance(self):
        text = (LAB / "README.md").read_text()
        self.assertIn("aw-quint-opcode", text,
                      "README Doctrine provenance must name the referral edge "
                      "aw-quint-opcode -> gl-ledgers and the canonical producer "
                      "(SuperInstance/git-agent, quilt_emit), or the weight law "
                      "cannot mint the edge")
        self.assertIn("quilt_emit", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
