// demo-compile.mjs — ONE concrete adjustment→cell compilation, live, on a toy domain.
//
// Toy domain: a corner-store COUPON counter. A soft joint reads the coupon moment and
// answers the redemption line. A specific input ("SAVE10") is manually fixed TWICE
// across two runs (the operator keeps correcting the joint). On the second identical
// fix the compiler must emit a permanent LOOKUP cell, after which the same input is
// served by a fast table hit with ZERO model calls.
//
// This is the "repeated manual fixes compile into permanent cells" claim, exercised
// end to end with the REAL decompose()/runJoint()/compileAdjustments() from
// quilt-softjoints and the LOCAL ollama model as the joint backend.
import fs from 'node:fs';
import { decompose, runJoint, compileAdjustments, freezingTest } from '/tmp/scout/quilt-softjoints/src/index.js';
import { makeOllamaChatBackend, resetCalls, callCount, SMALL } from './lib/ollama.mjs';

const out = [];
const log = (s) => { console.log(s); out.push(s); };

// ---- the toy domain ----------------------------------------------------------
const spec = {
  id: 'corner-store-coupons',
  domain: 'coupon-redemption',
  behaviors: [
    {
      id: 'coupon.joint', kind: 'judgment', inputs: [],
      vector: { dim: 2, labels: ['confidence', 'urgency'] },
      backend: { type: 'deepinfra-chat', model: SMALL },
      fallback: { type: 'default', note: null },
      notes: 'Read the coupon moment and answer with the redemption line for the customer.',
    },
    {
      id: 'coupon.table', kind: 'deterministic', inputs: ['code'],
      map: {}, default: 'Unknown coupon — please ask the counter.',
    },
  ],
};

const { sheet, receipts: decompReceipts } = decompose(spec);
log('# Adjustment → cell compilation, live (local ollama, CPU-only)');
log('');
log(`domain: ${spec.id}  cells: ${sheet.cells.map((c) => `${c.id}:${c.kind}`).join(', ')}`);
log(`decomposition rules: ${decompReceipts.map((r) => `${r.behavior}→${r.rule.split('→')[1]?.trim()}`).join(' | ')}`);

const jointBackend = makeOllamaChatBackend({ vector: { labels: ['confidence', 'urgency'] } }, { model: SMALL });

// ---- phase 1+2: two live runs, two manual fixes ------------------------------
// Two DIFFERENT phrasings of the SAME coupon input (the input the operator keys the
// fix on is "SAVE10"). Two runs so the cache cannot collapse them into one call.
const runs = [
  { run_id: 'coupon-live-1', at_seq: 2, message: 'I have coupon SAVE10 — what does it give me?' },
  { run_id: 'coupon-live-2', at_seq: 3, message: 'applying my SAVE10 code at the till, what do I get?' },
];
const FIX = { input: 'SAVE10', after: 'SAVE10 = 10% off produce', hypothesis: 'SAVE10 always means 10 percent off produce every single time' };

const adjustments = [];
log('');
log('## Phase 1/2 — live joint calls, then a manual fix (twice)');
for (const run of runs) {
  resetCalls();
  const res = await runJoint(sheet, 'coupon.joint', { state: { message: run.message } }, {
    backend: jointBackend, prompt: 'give the coupon redemption line', cache: false,
  });
  const before = res.answer;
  log(`  [${run.run_id}] message: "${run.message}"`);
  log(`  [${run.run_id}] model answered (${callCount()} model call): ${JSON.stringify(before)}`);
  log(`  [${run.run_id}] operator FIX: ${JSON.stringify(before)} → ${JSON.stringify(FIX.after)}`);
  adjustments.push({
    kind: 'adjustment', seq: adjustments.length + 1, run_id: run.run_id, at_seq: run.at_seq,
    target: { cell_id: 'coupon.joint', input: FIX.input, sheet: spec.id },
    before, after: FIX.after,
    why: { trigger: `coupon ${FIX.input} answered inconsistently`, hypothesis: FIX.hypothesis, evidence: [`${run.run_id}@${run.at_seq}`] },
    generalizes: true,
  });
}
fs.writeFileSync(new URL('./logs/adjustments-demo.jsonl', import.meta.url), adjustments.map((a) => JSON.stringify(a)).join('\n') + '\n');

// ---- phase 3: compile --------------------------------------------------------
log('');
log('## Phase 3 — compileAdjustments(sheet, adjustments, {threshold:2})');
const { sheet: compiled, receipts, compiledCells } = compileAdjustments(sheet, adjustments, { threshold: 2 });
for (const r of receipts) log(`  compile-receipt: cluster="${r.cluster}" consumed=${r.adjustments_consumed} new_cell=${r.new_cell.id} (${r.new_cell.kind})`);
for (const c of compiledCells) log(`  compiled cell: ${JSON.stringify(c)}`);

// ---- phase 4: the fast lookup ------------------------------------------------
log('');
log('## Phase 4 — the same input now serves from the compiled lookup');
const compiledCell = compiled.cells.find((c) => c.id === compiledCells[0]?.id);
function resolve(sheetObj, input, backend) {
  const compiled = sheetObj.cells.filter((c) => c.compiled_from).find((c) => c.kind === 'lookup' && Object.prototype.hasOwnProperty.call(c.table, input));
  if (compiled) return Promise.resolve({ answer: compiled.table[input], source: 'compiled-lookup', calls: 0 });
  return runJoint(sheetObj, 'coupon.joint', { state: { message: `coupon ${input}` } }, { backend, prompt: 'give the coupon redemption line' }).then((r) => ({ answer: r.answer, source: r.source, calls: callCount() }));
}
resetCalls();
const after = await resolve(compiled, 'SAVE10', makeOllamaChatBackend({ vector: { labels: ['confidence', 'urgency'] } }, { model: SMALL }));
log(`  resolve("SAVE10") → ${JSON.stringify(after.answer)}  source=${after.source}  model_calls=${after.calls}`);
log(`  table of compiled cell: ${JSON.stringify(compiledCell.table)}`);

// idempotency: recompiling the ALREADY-compiled sheet must not grow it (the
// compiler regenerates its candidate list every call, so the honest measure is the
// change in the sheet's actual cell count, not compiledCells.length).
const again = compileAdjustments(compiled, adjustments, { threshold: 2 });
const grewBy = again.sheet.cells.length - compiled.cells.length;
log(`  idempotent recompile: sheet cells ${compiled.cells.length} → ${again.sheet.cells.length} (grew by ${grewBy}; expected 0 — new cells appended, nothing removed or duplicated)`);
const demoIdem = { grew_by: grewBy, cells_before: compiled.cells.length, cells_after: again.sheet.cells.length };

// ---- phase 5: the freezing test (softjoint → lookup, the other direction) ----
log('');
log('## Phase 5 — freezingTest (the promotion instrument), real refunder data');
const { refunderPreVector } = await import('/tmp/scout/quilt-storefront/src/vector.js');
const refundMessages = [
  'I would like to return these socks please — they are unused and I have the receipt.',
  'the milk I bought yesterday spoiled early and I am upset about it',
  'the toaster I bought here broke on day one and honestly I am furious — but I know it is not your fault, and I would appreciate whatever you can do.',
  'you know me, I am in here every week — this bread is stale, I would like to return it',
  'hi, it is my first time in your shop — the eggs I just bought were cracked, I want a refund',
];
const observed = refundMessages.map((m, i) => ({ vector: refunderPreVector(m), output: i < 3 ? 'full refund' : 'store credit' }));
const realProposals = freezingTest(observed, { threshold: 3 });
log(`  real refunder observations: ${observed.length}; freeze-proposals: ${realProposals.length} (repo reports 0 — honest non-result)`);
const synthetic = Array.from({ length: 3 }, () => ({ vector: { distress: 0.9, goodwill: 0.2, 'repeat-customer': 0.1 }, output: 'full refund' }));
const synthProposals = freezingTest(synthetic, { threshold: 3 });
log(`  synthetic unanimous region (n=3, same output): freeze-proposals: ${synthProposals.length} → ${synthProposals[0]?.output ?? 'none'}`);

const demoReport = {
  at_utc: new Date().toISOString(),
  domain: spec.id,
  adjustments,
  compiled_cells: compiledCells,
  compile_receipts: receipts,
  fast_lookup_after: after,
  idempotent_recompile: demoIdem,
  freezing_test: { real_proposals: realProposals.length, synthetic_proposals: synthProposals.length },
};
fs.writeFileSync(new URL('./demo-report.json', import.meta.url), JSON.stringify(demoReport, null, 2) + '\n');
fs.writeFileSync(new URL('./logs/demo-run.log', import.meta.url), out.join('\n') + '\n');
