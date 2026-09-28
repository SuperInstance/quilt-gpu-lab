// JUDGE SLOT (JEV) — LOCAL MODEL IMPLEMENTATION, SIDECAR EDITION.
//
// The first LIVING CHECK: a local model living inside the arcade's judge
// slot interface. This module lives OUTSIDE quilt-arcade by design — the
// constraint was "do not modify quilt-arcade's tracked files" — and mimics
// the exact export shape of slots/judge.mjs so the arcade's own contract
// checks (assertSlotsValid invariants) hold for it unchanged:
//
//   createJudgeSlot(cfg) → {
//     slot:'judge', name:'JEV', version, status, hooks:[...],
//     credentials:{ env, configured },          // stub-shape parity
//     hooks:{ scorePosition, reviewMove },      // async, contract-honest
//   }
//
// Contract fidelity (from slots/judge.mjs):
//   scorePosition(snapshot) → { score, why } | null   (null = "no opinion")
//   reviewMove(move, verdict) → { agree, why } | null (null = "no opinion")
// Hooks NEVER throw and NEVER block the game: provider down, rate-limited,
// malformed JSON → null, honestly counted in .stats.refusals. The referee
// (rule cells) remains the law; the model's verdict is an opinion, a CHECK
// in the crystallization-loop sense — the thing the big model's call becomes.
//
// Model: local Ollama (default qwen2.5:0.5b — the only model currently
// pulled on this box). Config via cfg or env: QUILT_JUDGE_URL,
// QUILT_JUDGE_MODEL, and QUILT_SLOT_JUDGE_KEY (stub-parity only; a local
// model needs no external credential — documented in credentials.note).

export const JUDGE_SLOT = {
  slot: 'judge',
  name: 'JEV',
  version: '0.2.0-local',
  status: 'local-implementation',
  hooks: ['scorePosition', 'reviewMove'],
};

export function createJudgeSlot(cfg = {}) {
  const envVar = cfg.envVar ?? 'QUILT_SLOT_JUDGE_KEY';
  const apiKey = cfg.apiKey ?? (typeof process !== 'undefined' ? process.env[envVar] : undefined) ?? null;
  const url = String(cfg.url ?? (typeof process !== 'undefined' ? process.env.QUILT_JUDGE_URL : undefined) ?? 'http://127.0.0.1:11434').replace(/\/+$/, '');
  const model = cfg.model ?? (typeof process !== 'undefined' ? process.env.QUILT_JUDGE_MODEL : undefined) ?? 'qwen2.5:0.5b';
  const timeoutMs = cfg.timeoutMs ?? 30000;

  const stats = { calls: 0, opinions: 0, refusals: 0, agreed: 0, disagreed: 0, scores: 0 };

  const clamp01 = (n) => Math.max(0, Math.min(1, n));

  // ask() — one fenced Ollama call, JSON mode, temp 0. Returns a parsed
  // object or null. Every failure mode collapses to null ("no opinion"),
  // never a throw into the game loop.
  async function ask(prompt) {
    stats.calls++;
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    try {
      const res = await fetch(url + '/api/generate', {
        method: 'POST',
        signal: ac.signal,
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model,
          prompt,
          stream: false,
          format: 'json',
          options: { temperature: 0, num_predict: 128 },
        }),
      });
      if (!res.ok) throw new Error(`ollama http ${res.status}`);
      const out = await res.json();
      const parsed = JSON.parse(out.response);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('non-object reply');
      return parsed;
    } catch {
      stats.refusals++;
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  return {
    ...JUDGE_SLOT,
    impl: 'local-ollama',
    model,
    url,
    credentials: {
      env: envVar,
      configured: !!apiKey,
      note: 'local model — no external credential required; `configured` mirrors QUILT_SLOT_JUDGE_KEY only for stub-shape parity with slots/judge.mjs',
    },
    stats,
    health: async () => {
      try {
        const r = await fetch(url + '/api/tags', { signal: AbortSignal.timeout(4000) });
        const j = await r.json();
        const names = (j.models ?? []).map((m) => m.name);
        return { ok: true, url, models: names, hasModel: names.includes(model) };
      } catch (e) {
        return { ok: false, url, error: String(e) };
      }
    },
    hooks: {
      // async (snapshot) → { score, why } | null
      scorePosition: async (snapshot) => {
        const prompt = [
          'You are JEV, the judge of a board game. Score this position for the player to move.',
          'Scale: -100 = losing, 0 = balanced, +100 = winning.',
          'Position: ' + JSON.stringify(snapshot ?? null).slice(0, 1200),
          'Reply ONLY with strict JSON: {"score": <integer -100..100>, "note": "max 12 words"}',
        ].join('\n');
        const j = await ask(prompt);
        if (!j || typeof j.score !== 'number' || !Number.isFinite(j.score)) return null;
        stats.opinions++;
        stats.scores++;
        return {
          score: Math.max(-100, Math.min(100, Math.round(j.score))),
          why: String(j.note ?? j.why ?? '').slice(0, 160) || '(silent)',
          model,
        };
      },
      // async (move, verdict) → { agree, why } | null
      reviewMove: async (move, verdict) => {
        const prompt = [
          'You are JEV, the judge of a board game. A move was played and the referee (rule cells) returned a verdict.',
          'Move: ' + JSON.stringify(move ?? null).slice(0, 400),
          'Referee verdict: ' + JSON.stringify(verdict ?? null).slice(0, 600),
          'Semantics: verdict.ok===true means the move was legal and applied. verdict.ok===false means the referee REFUSED it' +
            (verdict && verdict.rule ? ` (rule ${verdict.rule})` : '') + '.',
          'The referee is the law: agree unless the verdict is plainly wrong.',
          'Reply ONLY with strict JSON: {"agree": <true|false>, "confidence": <0..1>, "note": "max 12 words"}',
        ].join('\n');
        const j = await ask(prompt);
        if (!j || typeof j.agree !== 'boolean') return null;
        stats.opinions++;
        if (j.agree) stats.agreed++; else stats.disagreed++;
        const confidence = typeof j.confidence === 'number' && Number.isFinite(j.confidence) ? clamp01(j.confidence) : null;
        return {
          agree: j.agree,
          confidence,
          why: String(j.note ?? j.why ?? '').slice(0, 160) || '(silent)',
          model,
        };
      },
    },
  };
}
