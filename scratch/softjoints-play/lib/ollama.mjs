// lib/ollama.mjs — local-only LLM access for the quilt play.
// Repoints every "LLM provider" in the quilt-softjoints / quilt-storefront stack at
// the local ollama daemon. No metered calls, no API keys, fully offline.
//
//   contending models : qwen2.5:3b-instruct-q4_K_M   (the "small model" of the claim)
//   judge model       : qwen2.5:7b-instruct-q4_K_M   (local, still free; a distinct
//                        model so the judge is not the exact same weights as the bare
//                        contender — reduces self-preference, costs nothing)
//
// Provides two runJoint-compatible backends:
//   makeOllamaClassifierBackend — type 'typesafe-systemone' shaped: answer MUST be one
//                                 of `choices` (this is the storefront's intent.router
//                                 classifier wire — typed labels, no free text).
//   makeOllamaChatBackend       — type 'deepinfra-chat' shaped: free-text answer that
//                                 still carries the moment vector (greeter + refunder).

export const OLLAMA = 'http://127.0.0.1:11434';
export const SMALL = 'qwen2.5:3b-instruct-q4_K_M';
export const JUDGE = 'qwen2.5:7b-instruct-q4_K_M';

let CALLS = 0;              // every ollama chat completion, counted
export function callCount() { return CALLS; }
export function resetCalls() { CALLS = 0; }

export async function ollamaChat({ model = SMALL, messages, temperature = 0.3, max_tokens = 300, timeout_ms = 240000 }) {
  const t0 = Date.now();
  const res = await fetch(`${OLLAMA}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model, messages, stream: false,
      options: { temperature, num_predict: max_tokens },
    }),
    signal: AbortSignal.timeout(timeout_ms),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`ollama HTTP ${res.status}: ${JSON.stringify(body).slice(0, 160)}`);
  CALLS += 1;
  return {
    content: body.message?.content ?? '',
    usage: { prompt_tokens: body.prompt_eval_count ?? null, completion_tokens: body.eval_count ?? null },
    latency_ms: Date.now() - t0,
    finish: body.done_reason ?? null,
    model,
  };
}

function extractJson(text) {
  if (!text || typeof text !== 'string') return null;
  const cleaned = text.replace(/```(?:json)?/gi, '').trim();
  for (const [open, close] of [['{', '}'], ['[', ']']]) {
    const i = cleaned.indexOf(open);
    const j = cleaned.lastIndexOf(close);
    if (i !== -1 && j > i) {
      try { return JSON.parse(cleaned.slice(i, j + 1)); } catch { /* keep trying */ }
    }
  }
  return null;
}

function vectorTemplate(labels) {
  return '{' + labels.map((l) => `"${l}":0.0`).join(',') + '}';
}

// typesafe-shaped: the answer is a CHOICE from a closed label set (router classifier).
export function makeOllamaClassifierBackend(desc, { model = SMALL, choices } = {}) {
  const labels = desc?.vector?.labels ?? [];
  const allowed = choices ?? desc?.choices ?? [];
  return {
    type: 'typesafe-systemone',
    model,
    async call({ prompt, vectorLabels, state, choices: callChoices }) {
      const L = vectorLabels?.length ? vectorLabels : labels;
      const A = (callChoices?.length ? callChoices : allowed);
      const sys = 'You are the intent router of a corner-store digital assistant. '
        + 'Read the customer message and choose EXACTLY ONE route label. '
        + `Reply with STRICT JSON only, no prose: {"vector":${vectorTemplate(L)},"answer":"<ONE label>"}. `
        + `The "answer" value must be EXACTLY one of these labels, copied verbatim: ${A.join(', ')}.`;
      const user = `Customer message: ${JSON.stringify(state?.message ?? state)}\nTask: ${prompt ?? ''}`;
      const r = await ollamaChat({ model, messages: [{ role: 'system', content: sys }, { role: 'user', content: user }], temperature: 0, max_tokens: 200 });
      const parsed = extractJson(r.content);
      let answer = parsed?.answer != null ? String(parsed.answer).trim() : null;
      const match = (s) => A.find((c) => s === c) || A.find((c) => String(s).includes(c)) || null;
      if (!answer || !match(answer)) answer = match(r.content) || answer; // tolerant, but never invent a route
      if (!answer || !A.includes(answer)) throw new Error(`classifier: no valid route in reply (${JSON.stringify(r.content).slice(0, 120)})`);
      const vector = {};
      for (const l of L) vector[l] = Number(parsed?.vector?.[l] ?? 0.5);
      return { answer, vector, confidence: 0.6, usage: r.usage, latency_ms: r.latency_ms, model: r.model };
    },
  };
}

// deepinfra-shaped: free-text answer + a moment vector.
export function makeOllamaChatBackend(desc, { model = SMALL } = {}) {
  const labels = desc?.vector?.labels ?? [];
  return {
    type: 'deepinfra-chat',
    model,
    async call({ prompt, vectorLabels, state }) {
      const L = vectorLabels?.length ? vectorLabels : labels;
      const sys = 'You are one cell in a quilt — a small model at a soft joint. Read the moment as a vector, then answer. '
        + `Reply with STRICT JSON: {"vector":${vectorTemplate(L)},"answer":"..."} — no other keys, no prose.`;
      const user = JSON.stringify({ moment: state, task: prompt });
      const r = await ollamaChat({ model, messages: [{ role: 'system', content: sys }, { role: 'user', content: user }], temperature: 0.5, max_tokens: 400 });
      const parsed = extractJson(r.content);
      if (!parsed || typeof parsed.answer === 'undefined') throw new Error(`unparseable joint reply (${model}) :: ${JSON.stringify(r.content).slice(0, 120)}`);
      const vector = {};
      for (const l of L) vector[l] = Number(parsed?.vector?.[l] ?? 0.5);
      return { answer: String(parsed.answer), vector, confidence: 0.6, usage: r.usage, latency_ms: r.latency_ms, model: r.model };
    },
  };
}

// A plain one-shot chat (used for the bare contender and the judge).
export async function plainChat({ model = SMALL, system, user, max_tokens = 200, temperature = 0.3 }) {
  return ollamaChat({ model, messages: [{ role: 'system', content: system }, { role: 'user', content: user }], temperature, max_tokens });
}
