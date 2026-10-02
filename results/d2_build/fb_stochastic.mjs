// dba/stochastic.mjs — D2 stochastic-worlds patch configuration (driver-side).
// Scope (prereg §1, §6.1): driver-side only. Draws live in the WORLD TICK;
// agent cell logic (kernels.mjs, engine/cells/*) is untouched (F8).
// Default-off: core.mjs without `stochastic:true` is byte-identical to the
// unmodified pinned path (W-DET canary).
export const STO_DEFAULTS = {
  respawnJitter: 16,  // respawn delay = RESPAWN_DELAY + [-8..+8], drawn per event
  teacherP: 0.75,     // P(apply an executed curriculum switch), else discard
  sensorNoise: 0.08,  // delivered salience += U(-0.08,+0.08), never crosses 0.8
};
export const STO_LABEL = 'sto:v1-driver-only';
