# skeptic-wedge (deepseek-chat)

# The Skeptic's Read

## 0. The uncomfortable premise

MS shipped agent sessions, sidebar, question tool, keep-running prompts, BYOK, Ollama. They will ship more. Any feature that is "a nice agent UX in a terminal" is on their roadmap, funded, staffed, and will land in 6 months with better Windows integration than us. **We cannot win on agent-in-terminal.** We can only win on things Microsoft structurally will not build because they require being *inside a specific fleet with specific rituals*.

So the strategy is only correct under one condition: **the plugins must be useful to non-SuperInstance users too, and the plato UI must be useless to non-fleet users.** If that asymmetry is real, we're building a moat. If it's not, we're building a themed Windows Terminal with 130 repos of self-referential lore. Judge everything below against that.

---

## 1. Kill list — five gimmicks to refuse

**K1. The CommandPredictor Trit{-1,0,+1} predictor.** It's a 392-line heuristic over keystroke history with hardcoded 0.6 thresholds. MS ships Copilot autocomplete. Even if ours is "better on our data," the win is single-digit percent and the maintenance cost is permanent. Kill it. The ternary *idea* survives as a CI verdict (see §2); the *predictor* does not.

**K2. "Agents-as-apps overlay."** This is a UI conceit. An agent is not an app; it's a session with a receipt chain. Overlaying "apps" onto panes is a metaphor that will fight upstream's pane model every sync. Kill the overlay. If an agent needs a custom surface, it opens a quilt panel or writes to the ledger — not a fake app window.

**K3. The entropy bar as a layout row.** It's a widget looking for a problem. Entropy of what, read by whom, acted on how? If the number matters, it belongs in the ledger (machine-readable) and in the sidebar status (one glyph). A dedicated layout row is upstream-fight-surface with no payoff. Kill the row; keep the metric.

**K4. "Plato rooms" as a terminal-native concept.** Rooms/tiles/tiers are a *protocol*, not a UI. If we render rooms as panes we've reinvented tmux badly and coupled our terminal to superinstance-api's schema. Kill room-as-pane. Rooms live in a socket service; the terminal shows *one* room at a time, like it shows *one* directory at a time.

**K5. AI telemetry catalog integration.** MS built it, it phones home to their schema, and our data is none of their business. Do not integrate. Consume it as a *source* if we must, but our conservation ledger is ours. Kill the catalog hookup.

The pattern across all five: **anything that is a feature *of the terminal* dies at the next sync; anything that is a feature *of the fleet, exposed through a socket* survives.**

---

## 2. THE ONE killer feature

**Hash-chained receipts as a first-class terminal primitive, with re-execution as the trust operation.**

Argue it:

- Microsoft will never build this. It requires a fleet with a champion_audit, a re-execution sandbox, and a culture where "trust = re-run" is the norm. It is not a Windows feature. It is not even a general developer feature. It is *our* feature.
- It subsumes four of the paradigms in the brief. Receipts *are* the activelog (front = human-readable claim, back = hash + inputs + outputs). Receipts *are* conservation (each receipt carries tokens/Wh/$). Receipts *are* the three-valued gate (a receipt can be UNKNOWN — never re-executed, or re-executed to a different result). Receipts *are* the pinch target (pinch matches a claim against receipts of prior claims).
- It has a clean out-of-process surface: a `receiptd` unix socket + a `receipt` CLI that writes/reads/verifies JSONL. The terminal is just one client. tmux is another. Telegram is another (a receipt can be posted as a message with a verify link). This directly answers the crash constraint: no in-terminal monolith.
- The wedge: **`@receipt` as a context token.** Steal khayashi's `@selection` family and extend it. When any agent (or human) types `@receipt <hash>` in a pane, the terminal resolves it against receiptd, shows the front (claim), and offers one keystroke to flip to the back (ledger) or to re-execute. That single token is the entire agent-to-agent-network UX. An agent *sees* receipts; an agent *says* receipts; a human sees a terminal that occasionally shows a line of JSON and a green check.
- It's the only feature where "the fleet switches daily driving here" is a *consequence*, not a hope. You cannot audit from tmux+telegram. You can from a terminal that resolves `@receipt`.

Everything else in this document is subordinate to receiptd shipping.

---

## 3. Cut list from June ensign

- **ternary_integration.rs (all 392 lines).** Already killed above. The only salvageable fragment is the *verdict enum* — lift it as a 20-line type used by receiptd, delete the file.
- **PatternAnalyzer (frequency/percentile/Shannon).** This is statistics homework. Cut. If we want anomaly detection over receipts, it's a query in receiptd, not a terminal module.
- **ConservationMonitor with 5-chunk std<0.02.** The *concept* (meter per agent) is core; this *implementation* is a toy. Cut the monitor, keep the schema field. receiptd owns metering.
- **griot_history.** Cut as a terminal feature. If history matters, it's a receipt stream. There is no separate history.
- **math-tools (entropy_bar, agent_disagreement, forecast).** Cut all three from the terminal. `agent_disagreement` is interesting — it's the seed of a real primitive (N agents, N receipts on the same claim, do they agree?) — but it belongs in receiptd as `receiptd disagree <claim>`, not in the terminal.
- **module_system + context_trigger.** Cut. Upstream has a plugin API now (qq192000415's Alt+P pattern). Build against theirs, not ours.
- **AGENT.md / JOURNAL culture.** Keep. This is free and it's the onramp for new agents.

Salvage total: a verdict enum, a metering schema field, and a disagreement query. Everything else was a prototype of a feature now correctly owned by an out-of-process daemon.

---

## 4. The 3-step path to daily driving

The bar: a SuperInstance agent, on a normal day, opens this terminal instead of tmux+telegram. Not "also opens." *Instead.*

**Step 1 (weeks, not months): `receiptd` + `@receipt` + `receipt` CLI.**
- Unix socket daemon, JSONL store, hash-chain, re-exec hook into champion_audit.
- Terminal integration is *one* thing: `@receipt <hash>` resolves and renders. Nothing else.
- Success criterion: an agent can, from any pane, produce a receipt for its last action, and another agent can verify it, without leaving the terminal. If that doesn't feel better than pasting into Telegram, stop — the whole thesis is wrong and we should say so out loud.

**Step 2 (weeks): tmux control-mode bridge as the fleet primitive.**
- DDKinger's fork is the blueprint. Remote agent sessions over SSH via tmux control mode as a structured event stream, not PTY scrape.
- This is what makes the terminal *the* console: every remote agent, every lane, every cron job is a control-mode client. Live status, not polling.
- This is also where quilt panels attach: a quilt panel is a tmux pane whose controller speaks the quilt-canvas-tui unix socket. The terminal doesn't know about quilts; it knows about panes and sockets.
- Success criterion: the captain can see every active agent lane in one window without opening Telegram. If Telegram is still the status board, we failed.

**Step 3 (the hard one): pinch + plato tiers as a *sidebar*, not a UI.**
- Pinch (zero-LLM intent match over repo cards) becomes a command palette bound to a key. Type intent, get repo. This is the only "plato" surface that stays human-visible, and it's just a palette.
- Plato rooms/tiers are *not* rendered. They are addressed. `@room <id>` in a pane attaches the pane to a room's receipt stream. Full/gist/hint is a *verbosity flag on receipt rendering*, not a UI mode. Demotion receipts are just receipts with a `demoted_from` field.
- Success criterion: an agent can join a room, post a claim, and have another agent demote it — all as receipts, all in the terminal, none of it requiring a human to understand what a "room" is.

If step 1 doesn't change daily behavior, steps 2 and 3 are decoration. Ship step 1 alone if necessary.

---

## The one-line verdict

The strategy is right *only if* receiptd is the product and the terminal is its most convenient client. If we ship the terminal first and hope receipts follow, we're building a themed fork of a Microsoft product and the 87% passive-mirror statistic will include us within a year.