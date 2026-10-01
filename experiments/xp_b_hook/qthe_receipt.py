#!/usr/bin/env python3
"""qthe_receipt.py — canonical cell-state serialization + receipt digests.

XP-B lane. Seed 2718. Pure digests, NO keys.

Canonical state for a commit = compact sorted-key JSON of the sorted (by path)
staged cell states, plus corpus_seed and prev_receipt (chain link).

Digests:
  sha256   -> 64 lower hex  (the gate's pinned scheme)
  fnv1a64  -> 16 lower hex  (audit arm; M4 measures its adequacy)
"""
from __future__ import annotations

import hashlib
import json
import re

CORPUS_SEED = 2718
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1

RECEIPT_PREFIX = "qthe-receipt@1"
# exact, strict format
RECEIPT_RE = re.compile(
    r"^qthe-receipt@1 seed=(?P<seed>\d+) "
    r"sha256=(?P<sha>[0-9a-f]{64}) "
    r"fnv64=(?P<fnv>[0-9a-f]{16}) "
    r"prev=(?P<prev>GENESIS|[0-9a-f]{64})$"
)


def fnv1a64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h = ((h ^ b) * FNV_PRIME) & MASK64
    return h


def fnv1a64_hex(data: bytes) -> str:
    return format(fnv1a64(data), "016x")


def body_digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def cell_entry(cell: dict) -> dict:
    """Canonical per-cell projection (drops everything not bound by the receipt)."""
    dials = [int(d) for d in cell["dials"]]
    if len(dials) != 16:
        raise ValueError("cell %r: expected 16 dials, got %d" % (cell.get("id"), len(dials)))
    return {
        "cell_id": cell["id"],
        "kind": cell["kind"],
        "dials": dials,
        "seed": int(cell["seed"]),
        "body_sha256": body_digest(cell["body"]),
    }


def canonical_state_bytes(cells: dict, prev_receipt: str) -> bytes:
    """cells: {path: cell-dict}. Deterministic bytes over sorted paths."""
    entries = [cell_entry(cells[p]) for p in sorted(cells)]
    obj = {
        "corpus_seed": CORPUS_SEED,
        "cells": entries,
        "prev_receipt": prev_receipt or "GENESIS",
    }
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digests(cells: dict, prev_receipt: str) -> dict:
    raw = canonical_state_bytes(cells, prev_receipt)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "fnv64": fnv1a64_hex(raw),
        "canonical": raw,
    }


def receipt_line(sha256: str, fnv64: str, prev_receipt: str) -> str:
    return "%s seed=%d sha256=%s fnv64=%s prev=%s" % (
        RECEIPT_PREFIX, CORPUS_SEED, sha256, fnv64, prev_receipt or "GENESIS")


def parse_receipt(text: str) -> dict:
    """Return {'sha256','fnv64','prev','seed'} or raise ValueError (fail loud)."""
    line = None
    for ln in (text or "").splitlines():
        if ln.strip().startswith(RECEIPT_PREFIX):
            line = ln.strip()
            break
    if line is None:
        raise ValueError("no qthe-receipt@1 line in commit message")
    m = RECEIPT_RE.match(line)
    if not m:
        raise ValueError("receipt line malformed (truncated/format): %r" % line)
    seeded = int(m.group("seed"))
    if seeded != CORPUS_SEED:
        raise ValueError("receipt seed %d != corpus seed %d" % (seeded, CORPUS_SEED))
    return {
        "sha256": m.group("sha"),
        "fnv64": m.group("fnv"),
        "prev": m.group("prev"),
        "seed": seeded,
        "line": line,
    }
