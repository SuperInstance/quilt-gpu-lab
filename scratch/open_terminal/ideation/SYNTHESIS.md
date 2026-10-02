# SYNTHESIS — open-terminal ideation v2 (converged architecture)
2026-10-02 ~11:00 AKDT · 4 models × 2 rounds (deepseek-chat ×2, GLM-5.3, Seed-2.0-mini) · cross-hearing: attack own, steal 2, revise top-5. Receipts: round1_{a,b,c,d}.md, round2_{a,b,c,d}.md.

## THE CONVERGENCE (independent, post-hearing)

All four models arrived at the same skeleton. That's the finding.

1. **receiptd IS the product.** Out-of-process daemon, unix socket + CLI twin (ssh-agent pattern), append-only JSONL hash-chain per lane (SHA-256, `h_prev/h`), record: `{seq, ts, lane, corr, room, verb, kind, claim, v∈{-1,0,+1}, usage{tok,wh,usd}, evidence, h_prev, h}`. Canonical JSON for hashing. Trust = re-execution: verify spawns champion_audit in a sandbox lane, writes a DERIVATIVE receipt (`re:` edge) — never mutates the parent. Chronological edges (`prev`) + causal edges (`re`) → "audit the audits" is a chain walk; disagreement query (std==0 across re-executions ⇒ INCONCLUSIVE) falls out free.
2. **OSC 1338 envelope is the one transport.** `ESC]1338;v=1;<verb>;<corr>;<budget>;<tier>;<room>;<hash>BEL` + plain text. Ignored by stock terminals → invisible to humans, zero SDK for agents (any `write()` joins). Carries exactly the four things every other design tried to bolt on separately. Skeptic's extension makes it load-bearing: envelope carries the emitter's claimed receipt-head; receiver diffs against its chain view → `verb=drift` on mismatch = continuously-verified transport. Unknown verbs → passthrough untouched, never break rendering. v1.1 hardening: lane-scoped HMAC against envelope spoofing.
3. **fleetd + tmux control-mode lanes = the fleet console.** Stateless JSON-lines pub/sub on /run/si/fleet.sock; owns tmux `-CC` connections (local + SSH remotes, DDKinger's proved seam); translates %output/%window-add into lane lifecycle events. Terminal is a READ-ONLY SUBSCRIBER. The load-bearing property: **terminal dies, nothing agent-side dies** — the exact resilience this box demanded twice today.
4. **Conservation = receipt fields, not a product.** Meters sampled OUT-OF-BAND (AI telemetry catalog, nvidia-smi per-PID) — never self-reported (self-report is what an optimizer cheats). Budget in the envelope (`budget=usd:0.25|tok:50k|wh:3`), typed `budget-exceeded` events, abstain deadlines (fleet never blocks on a silent human), attention hysteresis on the human lane.
5. **Pinch palette = the zero-token routing reflex.** Resident pinchd on its OWN socket (keystroke path, no broker hop), mmap index over the 5,138 cards, top-3 with why, two-step confirm, dispatch → receipt kind:pin.

## Process doctrine (converged)

Daemons are the fleet; the terminal is a view. `receiptd` owns the ONLY append-only file; `fleetd` is stateless fan-out; `pinchd` is latency-isolated. Degraded-mode contracts per daemon (three-valued verdicts applied to infrastructure: a down pinchd is UNKNOWN, not FAIL — "you'll pay tokens" is an honest state). Pane badge = receipt-head indicator (✓ re-executed+matched / ? never re-executed / ✗ diverged); right-click audit → itself a receipt in `room=_audit` (trust graph is a DAG). Tier is a property of the pane's ECHO, not the receipt — "the receipt is the substrate, the tier is the projection"; nothing is hidden, just not painted. Write-side contract: answering agent emits only tier-appropriate echo to the PTY; full fidelity lives in receiptd.

## What the hearing killed

- Ternary CommandPredictor (the 392-line ensign core) — KILLED; sole salvage: the {-1,0,+1} verdict enum.
- Plato rooms as rendered panes → rooms are receipt-stream filters + a `room=` field.
- Griot-as-service → receipt queries; there is no separate history.
- conservd-as-product → usage fields on receipts + one sampler daemon.
- In-tree chrome (IPaneDecorator hook lists) → grammar-on-data + existing OSC 8/0/9 affordances; fork diff shrinks toward keymaps only.
- Self-reported budgets, @receipt-as-typed-token (kept as CLI, demoted from the transport), pinch-in-process.

## Build order (each slice ships alone)

1. **receiptd, no terminal**: append/get/verify/by-corr/tail over unix socket + JSONL + SHA-256 chain + 20-line CLI. Test: two scripts produce receipts, a third verifies, a tampered line fails. *If this feels worse than a Telegram message, stop the whole program — say so out loud.*
2. **OSC 1338 tap**: tmux pipe-pane parser (3 verbs) + `si-say` shell library + corr index in receiptd. Demo: two panes, A asks B, gist-tier answer, one receipt chained; human sees ticks.
3. **fleetd lanes**: control-mode parse + lane table + `si lanes` + tmux status-right; one SSH remote.
4. **Budget fields**: meterd sampler + budget-exceeded + abstain timer.
5. **Pinch palette** (last, it's delight): pinchd CLI + palette + route-to-lane + pin receipt.

Terminal chrome is LAST. The fleet works headless from slice 1.

## Alignment with the day's constraints

Out-of-process daemons + JSONL on disk (+ /tmp-is-volatile lesson), crash-tolerant by construction (×2 GSOD), three-valued honesty (INCONCLUSIVE is a first-class state), zero-LLM reflex (pinch), receipts-not-displays (champion_audit). The ensign's soul survives as the verdict enum and the duty-log culture — its body stays in the git history where it belongs.
