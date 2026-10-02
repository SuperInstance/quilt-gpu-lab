#!/usr/bin/env node
// PROBE-BATTERY #7 — INDEPENDENT node re-derivation of the quilt-gpu-lab ledger
// row-hash scheme (tidepool #11 doctrine: "deliberately independent code ... so a
// shared bug cannot blind both sides" — zero imports from the lab's python tools).
//
// The subject scheme (reverse-engineered from the booked artifacts, NOT imported):
//   sha256( json.dumps(row_without_sha256_key, sort_keys=True) )   [python stdlib]
//
// Two canonicalizers are implemented independently here:
//   naive  — what a JS builder writes naturally: recursively key-sorted JSON.stringify
//            (compact separators, JS string escaping). Tests whether the scheme's
//            canonical form is language-neutral. Expected: it is NOT.
//   mirror — a re-derivation of the actual scheme: key-sorted, python-json separator
//            convention (", " / ": "), C0/\u2028\u2029 escaping (ensure_ascii analog),
//            sha256 over the UTF-8 bytes. Written from the OBSERVED byte format of the
//            stored rows, not by running python's json module.
//
// Modes (argv[2]): "verify"    — recompute row digests from stdin JSONL (rows parsed,
//                                 sha256 key dropped, canonicalized, hashed) and emit
//                                 JSON: [{stored, naive, mirror}, ...]
//                  "perturb"   — stdin JSONL; reverse key insertion order of each row,
//                                 emit the mirror-canon digest of each perturbed row
//                  "transplant"— stdin: one JSON row; emit its digest (for the
//                                 unkeyed-path demonstration)
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

function pyEscape(s) {
  // python json.dumps ensure_ascii=True analog: ", \, control chars, and the
  // 2028/2029 line separators escaped; non-ASCII -> \uXXXX (rows here are ASCII)
  let out = '"';
  for (const ch of s) {
    const cp = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (cp === 0x0a) out += "\\n";
    else if (cp === 0x0d) out += "\\r";
    else if (cp === 0x09) out += "\\t";
    else if (cp === 0x08) out += "\\b";
    else if (cp === 0x0c) out += "\\f";
    else if (cp < 0x20 || cp === 0x7f) out += "\\u" + cp.toString(16).padStart(4, "0");
    else if (cp === 0x2028 || cp === 0x2029) out += "\\u" + cp.toString(16);
    else if (cp > 0x7e) out += "\\u" + cp.toString(16).padStart(4, "0");
    else out += ch;
  }
  return out + '"';
}

function canonMirror(v) {
  if (v === null) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return String(v); // python renders 3 as "3"
    return String(v); // divergence risk (python repr vs JS) — noted in the probe report
  }
  if (typeof v === "string") return pyEscape(v);
  if (Array.isArray(v)) {
    return "[" + v.map(canonMirror).join(", ") + "]";
  }
  const keys = Object.keys(v).sort();
  return "{" + keys.map((k) => pyEscape(k) + ": " + canonMirror(v[k])).join(", ") + "}";
}

function canonNaive(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(canonNaive).join(",") + "]";
  const keys = Object.keys(v).sort();
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonNaive(v[k])).join(",") + "}";
}

const sha256 = (s) => createHash("sha256").update(Buffer.from(s, "utf8")).digest("hex");

const mode = process.argv[2] ?? "verify";
const lines = readFileSync(0, "utf8").split("\n").filter((l) => l.trim());
const out = [];
for (const line of lines) {
  const row = JSON.parse(line);
  const { sha256: stored, ...rest } = row;
  if (mode === "perturb") {
    const rev = {};
    for (const k of Object.keys(rest).reverse()) rev[k] = rest[k]; // reversed insertion order
    out.push({ mirror_perturbed: sha256(canonMirror(rev)), mirror_plain: sha256(canonMirror(rest)) });
  } else if (mode === "transplant") {
    out.push({ transplanted_row_digest: sha256(canonMirror(rest)), stored });
  } else {
    out.push({ stored, naive: sha256(canonNaive(rest)), mirror: sha256(canonMirror(rest)) });
  }
}
console.log(JSON.stringify(out));
