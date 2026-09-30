#!/usr/bin/env node
// fleet_board.mjs — project real work lanes onto a quilt-canvas as fabric cells.
//
// GRABBABLE: the fabric module comes from a quilt-canvas-tui clone.
//   git clone https://github.com/SuperInstance/quilt-canvas-tui
//   export CANVAS_FABRIC=$PWD/quilt-canvas-tui/bridge/fabric.mjs
//   export QUILT_SOCK=/home/eileen/tmp/quilt-fleet.sock
//   node fleet_board.mjs &                                  # this controller
//   QUILT_SOCK=$QUILT_SOCK node quilt-canvas-tui/bridge/canvas.mjs   # the canvas
//   # in the canvas pane: 'g' = glyph mode (dials -> tone ramp), 'G' = sculpt (links -> edges)
//
// LANES: defaults below are Lucineer's 2026-09-29 fire-wide lanes (real receipts).
// To project YOUR lanes, point LANES_FILE at JSON:
//   {"cells":[{"addr":"A1","dials":[4688,9844],"kind":"what-it-is"}],"links":[["A1","B1"]]}
//
// LAW: the grid IS the address space (A1..H6) — semantics ride in `kind`, dials are
// uint32 (real receipt fractions x10000). The controller is the authority; the canvas
// renders the genome and cannot flatter you.
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const FABRIC_PATH = process.env.CANVAS_FABRIC;
if (!FABRIC_PATH) {
  process.stderr.write(
    "[fleet-board] FATAL: set CANVAS_FABRIC to the quilt-canvas-tui fabric module,\n" +
    "  e.g. CANVAS_FABRIC=$HOME/scratch/quilt-canvas-tui/bridge/fabric.mjs\n");
  process.exit(2);
}
let Fabric;
try {
  ({ Fabric } = await import(pathToFileURL(FABRIC_PATH).href));
} catch (e) {
  process.stderr.write(`[fleet-board] FATAL: cannot import fabric from ${FABRIC_PATH}: ${e.message}\n`);
  process.exit(2);
}

const SOCK = process.env.QUILT_SOCK || "/home/eileen/tmp/quilt-fleet.sock";

// Default lanes: Lucineer's fire-wide window, 2026-09-29 (receipts, not aspirations).
const DEFAULT_LANES = {
  cells: [
    { addr: "A1", dials: [4688, 9844], kind: "mortar1-invalid-harness" },
    { addr: "B1", dials: [10000, 2812, 2344, 9688], kind: "mortar2-ORDER-CARRIES-LEANING" },
    { addr: "C1", dials: [200, 5550], kind: "bridge-green-bug-booked" },
    { addr: "D1", dials: [400, 8766], kind: "lever-v0.4.0" },
    { addr: "E1", dials: [3, 2, 0], kind: "turbquant-running" },
    { addr: "F1", dials: [0], kind: "c5-BLOCKED-no-videos" },
    { addr: "G1", dials: [44, 23, 5, 14], kind: "herd-14-unique" },
    { addr: "H1", dials: [14, 8920], kind: "si-api-14-tools" },
    { addr: "A2", dials: [2, 5], kind: "ideation-2-rounds" },
  ],
  links: [
    ["A1", "B1"],  // mortar1 -> mortar2 lineage
    ["A2", "B1"],  // ideation seeded mortar2
    ["B1", "H1"],  // receipt booked to ledger
    ["C1", "D1"],  // bridge -> lever
    ["C1", "H1"],  // bridge -> si-api
    ["E1", "H1"],  // turbquant -> ledger embeddings
    ["G1", "H1"],  // herd -> bookings
  ],
};

function loadLanes() {
  const f = process.env.LANES_FILE;
  if (!f) return DEFAULT_LANES;
  try {
    const raw = JSON.parse(fs.readFileSync(f, "utf8"));
    if (!Array.isArray(raw.cells)) throw new Error("cells[] missing");
    return { cells: raw.cells, links: Array.isArray(raw.links) ? raw.links : [] };
  } catch (e) {
    process.stderr.write(`[fleet-board] FATAL: LANES_FILE ${f}: ${e.message}\n`);
    process.exit(2);
  }
}

const lanes = loadLanes();
const f = new Fabric();
for (const c of lanes.cells) f.bind(c.addr, c.dials, c.kind);
for (const [a, b] of lanes.links) f.link(a, b);
f.doTick();

function summaryUpdate() {
  const links = [];
  for (const c of f.cells.values())
    for (const n of c.neighbors)
      if (c.addr < n) links.push([c.addr, n]);
  return {
    type: "update", tick: f.tick,
    cells: [...f.cells.values()].map((c) => ({ addr: c.addr, dials: [...c.dials], kind: c.kind })),
    links,
    gdigest: f.graphDigest(), journal: f.receipts.length,
  };
}

const server = net.createServer((conn) => {
  let buf = "";
  conn.on("data", (d) => {
    buf += d.toString("utf8");
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const ln = buf.slice(0, i); buf = buf.slice(i + 1);
      if (!ln.trim()) continue;
      let msg;
      try { msg = JSON.parse(ln); } catch { continue; }
      if (msg.type === "ready") {
        conn.write(JSON.stringify({ type: "update", ...summaryUpdate(), hello: true }) + "\n");
      } else if (msg.type === "opcode") {
        const { op, cell, args } = msg;
        const r = op === "FORGET" ? f.forget(cell) : f.op(op, cell, args || {}).result;
        process.stderr.write(`[fleet-board] ${op} ${cell} -> ${JSON.stringify(r).slice(0, 90)}\n`);
        conn.write(JSON.stringify({ type: "update", ...summaryUpdate() }) + "\n");
      }
    }
  });
  conn.on("close", () => {}); conn.on("error", () => {});
});

fs.mkdirSync(path.dirname(SOCK), { recursive: true });
try { fs.unlinkSync(SOCK); } catch {}
server.listen(SOCK, () => {
  process.stderr.write(
    `[fleet-board] ${f.cells.size} cells, ${f.receipts.length} receipts, gdigest=${f.graphDigest()} on ${SOCK}\n`);
});
