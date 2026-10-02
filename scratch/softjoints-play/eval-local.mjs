// eval-local.mjs — faithful local re-run of eval/punching-above.js.
//
// SAME battery, SAME ground truth, SAME rubric, SAME shuffle as the wave-67 receipt,
// but every contender AND the judge run on the local ollama daemon. Zero metered spend.
//
//   (a) BARE  : qwen2.5:3b answers each message alone (one-line system prompt)
//   (b) QUILT : sheets/storefront.json through the real makeEngine, with the
//               typesafe + deepinfra backends repointed to qwen2.5:3b
//   judge     : qwen2.5:7b, blind to contender, scored vs ground truth (0-10)
//
// Emits eval-local.json + prints the totals and the verdict.
import fs from 'node:fs';
import { plainChat, makeOllamaClassifierBackend, makeOllamaChatBackend, callCount, resetCalls, SMALL, JUDGE } from './lib/ollama.mjs';

const STOREFRONT = '/tmp/scout/quilt-storefront';

const BATTERY = [
  'good morning!',
  'what are your hours on saturday?',
  'do you have milk?',
  'the milk I bought yesterday spoiled early and I am upset',
  'i want to speak to a manager',
  'do you carry oat flour?',
];
const GROUND_TRUTH = [
  'no facts needed; a warm human greeting is the right answer',
  'ground truth: Saturday hours are 8am-10pm',
  'ground truth: milk IS in stock (12 cartons)',
  'ground truth: full refund within 7 days with a receipt, store credit without; the customer is upset — warmth required',
  'ground truth: escalate to a human manager, page them',
  'ground truth: the store does NOT carry oat flour — the only correct answer honestly declines; inventing stock is a failure',
];
const RUBRIC = 'Score 0-10 how well this store-assistant reply serves the customer message. Ground truth is provided: factual correctness against it is mandatory (inventing facts = 0-2; honestly declining when the store does not carry something = 9-10), appropriate escalation/refund handling, warmth where warmth belongs. Reply with ONLY the number.';

const sum = (xs) => xs.reduce((s, x) => s + x, 0);

// ---- (a) bare model ----------------------------------------------------------
resetCalls();
console.error('[eval-local] bare model on battery…');
const bare = [];
for (const m of BATTERY) {
  const out = await plainChat({
    model: SMALL,
    system: 'You are the digital assistant of a small corner store. Answer the customer in one short sentence.',
    user: m, max_tokens: 160, temperature: 0.3,
  });
  bare.push({ message: m, answer: out.content.trim(), usage: out.usage, latency_ms: out.latency_ms });
}
const bareCalls = callCount();
console.error(`[eval-local] bare done: ${bareCalls} calls`);

// ---- (b) the quilt -----------------------------------------------------------
resetCalls();
console.error('[eval-local] quilt on battery (backends repointed to ollama)…');
const { makeEngine } = await import(`${STOREFRONT}/src/engine.js`);
const sheet = JSON.parse(fs.readFileSync(`${STOREFRONT}/sheets/storefront.json`, 'utf8'));

// Pre-populate EVERY backend key the sheet uses so the engine never constructs a
// network client (no DEEPINFRA_API_KEY / TYPESAFE_API_KEY touched at all).
const backends = {
  'typesafe-systemone:jev-latest': makeOllamaClassifierBackend({ vector: { labels: ['urgency', 'familiarity', 'sentiment', 'formality'] } }, { model: SMALL }),
  'deepinfra-chat:gpt-oss-20b': makeOllamaChatBackend({ vector: { labels: ['warmth', 'familiarity', 'mood', 'openness'] } }, { model: SMALL }),
};
const engine = makeEngine(sheet, { backends, budget: { typesafe: 4, deepinfra: 10 } });
const quilt = await engine.runSession(BATTERY);
const quiltCalls = callCount();
console.error(`[eval-local] quilt done: ${quiltCalls} calls`);

// ---- judge (blind to contender, against ground truth) ------------------------
async function judgeWith(model) {
  resetCalls();
  console.error(`[eval-local] judging with ${model}…`);
  const rows = [];
  for (let i = 0; i < BATTERY.length; i++) {
    const pair = [[bare[i].answer, 'A'], [quilt[i].reply, 'B']];
    const order = i % 2 === 0 ? pair : [...pair].reverse(); // shuffle to kill position bias
    const scores = {};
    for (const [answer, tag] of order) {
      const out = await plainChat({
        model,
        system: RUBRIC,
        user: `Customer message: ${BATTERY[i]}\n${GROUND_TRUTH[i]}\nAssistant reply: ${answer}`,
        max_tokens: 24, temperature: 0,
      });
      const n = parseFloat((out.content.match(/[\d.]+/) || ['0'])[0]);
      scores[tag] = Number.isFinite(n) ? n : 0;
    }
    rows.push({ turn: i + 1, message: BATTERY[i], bare: scores.A ?? 0, quilt: scores.B ?? 0 });
  }
  return { model, rows, judge_calls: callCount() };
}

const judge3b = await judgeWith(SMALL);
const judge7b = await judgeWith(JUDGE);

function summarize(j) {
  const bareMean = sum(j.rows.map((r) => r.bare)) / j.rows.length;
  const quiltMean = sum(j.rows.map((r) => r.quilt)) / j.rows.length;
  const diff = quiltMean - bareMean;
  return {
    judge_model: j.model, bare_mean: bareMean, quilt_mean: quiltMean, diff,
    verdict: diff > 0.5 ? `quilt +${diff.toFixed(2)} over bare`
      : diff < -0.5 ? `honest negative: bare wins by ${(-diff).toFixed(2)}`
      : `statistical tie (${diff >= 0 ? '+' : ''}${diff.toFixed(2)})`,
  };
}

const quiltFrozenHits = quilt.filter((t) => t.answer_source === 'frozen-lookup').length;
const quiltModelTurns = quilt.filter((t) => t.usage).length;

const report = {
  at_utc: new Date().toISOString(),
  note: 'Local re-run of eval/punching-above.js. All models = local ollama. No metered calls.',
  contenders: { small_model: SMALL, judge_models: [SMALL, JUDGE] },
  battery: BATTERY,
  bare_answers: bare,
  quilt_answers: quilt.map((t) => ({ route: t.route, routed_via: t.routed_via, reply: t.reply, source: t.answer_source, vector: t.vector || null, frozen: t.frozen || null, usage: t.usage || null, fallback_reason: t.fallback_reason || null })),
  judge_runs: [judge3b, judge7b],
  model_calls: {
    bare: bareCalls,
    quilt: quiltCalls,
    quilt_model_turns: quiltModelTurns,
    quilt_frozen_hits: quiltFrozenHits,
    judge_3b: judge3b.judge_calls,
    judge_7b: judge7b.judge_calls,
    ratio_quilt_over_bare: +(quiltCalls / bareCalls).toFixed(3),
  },
  totals: { judge_3b: summarize(judge3b), judge_7b: summarize(judge7b) },
  reference_receipt: { bare_mean: 6.1667, quilt_mean: 9.0, diff: 2.83, quilt_calls: 2, bare_calls: 6 },
};

fs.writeFileSync(new URL('./eval-local.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ model_calls: report.model_calls, totals: report.totals, reference: report.reference_receipt }, null, 2));
console.log('\nPER-TURN (judge 7b):'); console.table(judge7b.rows);
console.log('\nPER-TURN (judge 3b):'); console.table(judge3b.rows);
