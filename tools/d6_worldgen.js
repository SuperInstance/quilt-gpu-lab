// D6 worldgen driver — batch-export raw cargo-line-tycoon procgen worlds as JSONL.
//
// Usage: node d6_worldgen.js <seed_start> <count> <ticks>
// Emits one JSON object per line on stdout, one per seed:
//   { seed, ticks, ports: [...], chokepoints: [...], panama_ticks, fact_landed }
// Each port: { id, lat, lng, pencil, decoy, trust, proven, commodity, price, base, demand }
//
// The procgen entrypoint is the real GameEngine constructor
// (cargo-line-tycoon game/src/engine.js): seeded pencil ports + markets +
// reveal schedule, then `ticks` ticks of the deterministic world tick loop
// (panama/chokepoint events, price drift, ambient reveals) with no player
// actions — the world "breathes" on its own. Replay-deterministic per the
// engine's own contract: same seed -> same exported world, every time.
"use strict";
const TYCOON = "/home/eileen/projects/cargo-line-tycoon";
const { GameEngine } = require(TYCOON + "/game/src/engine.js");

const [, , seedStartArg, countArg, ticksArg] = process.argv;
const seedStart = parseInt(seedStartArg, 10);
const count = parseInt(countArg, 10);
const ticks = parseInt(ticksArg, 10);
if (!Number.isFinite(seedStart) || !Number.isFinite(count) || !Number.isFinite(ticks)) {
  console.error("usage: node d6_worldgen.js <seed_start> <count> <ticks>");
  process.exit(2);
}

const CP_ORDER = ["panama", "suez", "malacca", "gibraltar", "bab_el_mandeb"];

for (let s = seedStart; s < seedStart + count; s++) {
  const e = new GameEngine({ seed: s });
  for (let t = 0; t < ticks; t++) e.tick();

  const ports = [];
  for (const pid of e._allPortIds()) {
    const cell = e.world.entities.get("port:" + pid);
    const m = e.world.entities.get("market:" + pid);
    if (!cell || !m) continue;
    const pc = cell.state;
    const pp = e.pencilPorts[pid] || null;
    ports.push({
      id: pid,
      lat: pc.lat,
      lng: pc.lng,
      pencil: !!pp,
      decoy: pp ? !!pp.isDecoy : false,
      trust: pp ? pp.trust : 1.0,
      proven: pp ? !!pp.proven : true,
      commodity: pc.commodity || (m.state.commodity ?? null),
      price: m.state.price,
      base: m.state.basePrice,
      demand: m.state.demand,
    });
  }

  const chokepoints = CP_ORDER.map((id) => {
    const cp = e.chokepoints[id];
    if (!cp) return null;
    const v = cp.current && cp.current.value;
    return v === "disrupted" ? 2 : v === "congested" ? 1 : 0;
  });

  const out = {
    seed: s,
    ticks,
    ports,
    chokepoints,
    panama_ticks: e.panama.disrupted ? e.panama.ticksRemaining : 0,
    fact_landed: e.world.witness_log.filter((x) => x.type === "fact_landed").length,
  };
  process.stdout.write(JSON.stringify(out) + "\n");
}
