#!/usr/bin/env python3
"""receipt_manifest.py — seal the lab's ledgers into a chained receipt.

Dogfood of the fleet's receipt doctrine (pong-quilt R37+; canonical source
SuperInstance/AI-Writings algebra.md — the five-opcode quilt WAL; canonical
producer SuperInstance/git-agent quilt_emit, git-agent#1): a result the
ledger cannot re-derive is a claim, not a receipt. The manifest binds:

  - RESULTS.md        (the verdict ledger — the lab's memory)
  - QUEUE.md          (the worklist — what was claimed)
  - experiments/*.py  (the code that produced every verdict)

to their sha256 digests at a moment in time. tests/test_receipts.py
recomputes and compares; any drift trips the pin by name.

REGENERATION IS THE DECLARED RE-EMBED: after any honest ledger change
(new result, new experiment, queue check-off), rerun this tool and
commit the manifest WITH the change:

    python tools/receipt_manifest.py

Never edit receipts/manifest.json by hand — the pin exists so that a
digest no one re-ran the tool for is red, not silently stale.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
EXPERIMENTS = LAB / "experiments"
TOOLS = LAB / "tools"
MANIFEST = LAB / "receipts" / "manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    exp_digests = {
        p.name: sha256(p)
        for p in sorted(EXPERIMENTS.glob("*.py"))
    }
    # RECEIPT-HASH (2026-09-30, spawned by PR-SWEEP #4 off delta-shape #1's
    # hash-pinned vendoring): tools and trained weights are part of the
    # receipt — any drift in qcell_sim.py or qcell_oracle.pt must be
    # detectable against past bookings. Hash IS the identity.
    tool_digests = {}
    for p in sorted(TOOLS.iterdir()):
        if p.is_file() and p.suffix in {".py", ".pt", ".sh", ".mjs", ".js"} or p.name == "README.md":
            tool_digests[p.name] = sha256(p)
    return {
        "schema": "quilt-gpu-lab/receipt-manifest@v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": "regenerate via tools/receipt_manifest.py; never edit by hand",
        "ledgers": {
            "RESULTS.md": sha256(LAB / "RESULTS.md"),
            "QUEUE.md": sha256(LAB / "QUEUE.md"),
        },
        "experiments": exp_digests,
        "tools": tool_digests,
    }


def main() -> None:
    manifest = build()
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"sealed: RESULTS.md {manifest['ledgers']['RESULTS.md'][:12]}… "
          f"QUEUE.md {manifest['ledgers']['QUEUE.md'][:12]}… "
          f"{len(manifest['experiments'])} experiment file(s), "
          f"{len(manifest['tools'])} tool/weight file(s)")


if __name__ == "__main__":
    main()
