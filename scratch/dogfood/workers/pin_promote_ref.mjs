// pin_promote_ref.mjs — reference regression pin (lane-authored control).
// Proves the /promote precedence bug and the fix, independent of MiMo's pin.
// Usage: node pin_promote_ref.mjs [buggy|fixed]
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const mode = process.argv[2] === "buggy" ? "buggy" : "fixed";
const target = resolve(
  new URL(".", import.meta.url).pathname,
  mode === "buggy" ? "edge-lab-buggy/src/worker.js" : "edge-lab-fixed/src/worker.js",
);

function makeEnv() {
  const run = {
    run_id: "run_30_42_1000_abcd1234", colo: "SIN",
    chain_tail: "21c225f9e7320974", ticks: 1000, rule: 30, seed: 42,
  };
  const puts = [];
  return {
    RECEIPTS: { async get(key, type) { return key === "run:" + run.run_id ? (type === "json" ? run : JSON.stringify(run)) : null; } },
    SAVES: { async put(key, val) { puts.push([key, val]); return {}; } },
    DB: { prepare() { return { bind() { return { async run() { return {}; }, async first() { return {}; }, async all() { return { results: [] }; } }; } }; } },
    _puts: puts,
  };
}

const mod = await import(pathToFileURL(target).href);
const worker = mod.default;
const env = makeEnv();
const req = new Request("https://x/promote", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ run_id: "run_30_42_1000_abcd1234" }), // quality_score ABSENT
});
const res = await worker.fetch(req, env, {});
const body = await res.json();
const finite = Number.isFinite(body.quality_score) && body.quality_score === 0.5;

console.log(JSON.stringify({ mode, status: res.status, quality_score: body.quality_score, saved: body.saved }, null, 1));
if (mode === "fixed") {
  console.log(finite ? "PIN-PASS (finite 0.5)" : "PIN-FAIL");
  process.exit(finite ? 0 : 1);
} else {
  const reproduced = body.quality_score === null;
  console.log(reproduced ? "BUG-REPRODUCED (quality_score null)" : "BUG-NOT-REPRODUCED");
  process.exit(reproduced ? 0 : 1);
}
