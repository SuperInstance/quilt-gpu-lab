# agent-network-grammar round2 (deepseek-chat)

# agent-network-grammar — REVISED

## 1. Concessions (where the others beat me)

**C1. I over-built the envelope; `skeptic-wedge` is right that the terminal must be a *client*, not the protocol's home.** My round-1 had ten verbs all defined *as OSC sequences the WT pane runtime parses*. That makes every mechanic an upstream-fight-surface. Receipts are the product; the OSC is one binding of them among many (tmux hook, gh comment, Telegram message). I keep the envelope as a *fallback binding* for panes that have no socket, and demote it from "the transport" to "the degenerate transport." Everything real goes through a socket.

**C2. My `budget` field was a viewer, not an enforcement seam.** `glm-5.3`'s `conservd` as a resident daemon with telemetry-derived meters (rather than my "ask the agent to report its own token count") is strictly better — self-reported budgets are exactly the thing an optimizer will cheat. I concede agent self-reporting of conservation. Meters must be sampled out-of-band (upstream AI telemetry catalog is the source, `nvidia-smi` for Wh), and the agent sees its *meter*, never authors it.

**C3. My `scratchpaper` clerk was under-specified.** `minority-human`'s `@scratchpad` + quilt-canvas markdown sidebar is the concrete seam I hand-waved. Concede.

**C4. My `pinch` at the prompt-line was on the keystroke path in-process.** `glm-5.3` correctly notes pinch needs <10ms and therefore a *resident* daemon with an in-memory index, not a CLI spawn. Concede the latency budget; concede the CLI-twin/daemon-single-binary shape.

**C5. I did not have a kill list.** `skeptic-wedge`'s K1–K5 is the single most valuable paragraph across all four answers, because it names the failure mode (upstream-absorbed feature sprawl) that swallows our whole strategy. I concede the frame: judge every feature by "is this a feature *of the terminal* (dies at sync) or *of the fleet, exposed through a socket* (survives)."

What I do **not** concede: the `corr` correlation-ID threading across all verbs. `glm-5.3`'s event bus has `{id}` but doesn't commit to "every ask/handoff/interrupt/receipt shares a corr"; `skeptic-wedge`'s receipt model doesn't thread causal edges across panes. That's the piece that makes replay/repair/audit a *single* operation, and it's the thing I'd defend in a room full of skeptics.

---

## 2. Steals, extended with mechanics

### Steal A — from `glm-5.3`: **daemon-with-CLI-twin, and the terminal dies without taking the fleet with it.**

`glm-5.3`'s process tree (fleetd + receiptd/pinchd/conservd/quiltd as separate daemons over `unix` JSON-lines; terminal as a read-only subscriber) is the correct shape for a box that has crashed under load twice today. I extend it with two mechanics they didn't name:

**A1. Degraded-mode contract per daemon.** Each daemon declares a `degraded:` block in its registration on fleetd: `{what_you_lose: "...", continues_working: [...], resumption: "..."}`. Terminal renders a single faint glyph in the status bar when any daemon is in degraded mode (daemon crashed, backoff, or index stale). Agents querying fleetd get the same block in the response header. *The mechanic:* a fleet that has just lost `pinchd` shouldn't look like a fleet whose pinch just returns nothing — it should look like a fleet that says "no intent pre-match available; you'll pay tokens." This is JesseBrown1980's three-valued verdict applied to the *infrastructure* layer, not just CI. A daemon that is down is UNKNOWN, not FAIL.

**A2. Socket fencing token against the split-brain bug.** When the terminal (or a peer daemon) reconnects after a crash, it might have stale pane→corr mappings. fleetd issues a per-connection *fence* `<epoch>.<seq>` on subscribe; every event it fans out carries the fence it was published under. Consumers drop events whose fence is older than the newest fence they've seen for that lane. This is a 40-line mechanic that eliminates the "post-crash, target wrote twice" class of bug that will otherwise eat a week of debugging per incident. Round-1 had no story for crash recovery of the *bridge itself*, only for the agent sessions.

---

### Steal B — from `skeptic-wedge`: **`@receipt` as the one token, and re-execution as the one trust operation.**

I take the whole wedge. Extension mechanics:

**B1. `@receipt <hash>` resolves to a three-valued verdict *first*, payload second.** The reference resolves in this order at the pane: (1) does receiptd know the hash, (2) is the chain anchored from a genesis I trust (pinch of trust roots), (3) has anyone re-executed it, and with what verdict. Only then does it render the claim text. Rationale: if the claim is the first thing you see, you've already read it before you learned it's UNVERIFIED — the UI has lied to you by ordering. Verdict-first flipping is the entire point of the token, and it's the mechanic `skeptic-wedge` implies but doesn't spell.

**B2. Re-execution writes a *derivative receipt* with `re: <parent>`, never mutates the parent.** The chain therefore has *two kinds of edges*: chronological (`prev`) and causal (`re`). A single query walks both: "everything this claim implies" (causal down) vs "everything this session did" (chrono along). `skeptic-wedge`'s model has `champion_audit` as a verifier; this makes verification itself an auditable fleet act — you can audit the audits. The disagreement query (`receiptd disagree <claim>`) then falls out for free: it's "walk `re` edges under one claim, group by verdict, count." No separate code.

**B3. `@receipt` is resolvable from *any* pane, including a pane that isn't an agent.** That's what makes it a wedge and not a feature. A human pasting a receipt hash into a normal shell prompt gets the same resolve. `skeptic-wedge` gets this — I'm just naming it as the *adoption mechanic*, not a side effect. If `@receipt` only works in agent panes, no human ever learns it, and it never becomes daily-driving.

---

### Steal C — from `minority-human` (bonus, small): **the pinched-anomaly sidebar, inverted to be *fleet-authored*.**

`minority-human`'s "Pinch Bar Alert Widget" is the right shape but the wrong authority: a human-configured allowlist per pane is a firewall, not a fleet awareness surface. Inverted: the alert bar subscribes to `conservd` waste signals + `receiptd` UNKNOWN-verdict bursts, and its default firing condition is **a pane that has spent N tokens since its last verified receipt**. No allowlist; the fleet's own ledger is the sensor. Human sees a small amber dot; clicking assigns the pane to a scrutiny room. The quarantine action stays (that's good); the authority moves from `~/.superinstance/pinch.toml` to `receiptd`.

---

## 3. Revised top-5, ranked

Ranking criterion, explicit: **step 1 of `skeptic-wedge`'s path is the bar. Everything below either is receiptd or is a thin client of something that is.** Features that are neither are cut.

---

### F1. `receiptd` + `@receipt` + `receipt` CLI — the entire product

**Mechanic.** Out-of-process daemon, unix socket, append-only JSONL store, SHA-256 hash chain with two edge types (`prev` for chronology, `re` for re-execution derivation). Public surface: `receiptd` (socket), `receipt` (CLI, same binary `--socket|--file`), one terminal binding: `@receipt <hash>` resolves verdict-first (B1), renders three-valued, `Enter` walks to the claim, `Ctrl-R` triggers re-execution via champion_audit, re-execution writes a `re`-edge derivative (B2). Correlation: every receipt carries `corr`, and `corr` is what makes replay a chain lookup rather than a scrollback parse — this is the piece I keep from round-1 and refuse to give up.

**Why it survives contact with the skeptics.**
- Kills `skeptic-wedge`'s "if step 1 doesn't change daily behavior, stop" test by construction: step 1 *is* F1.
- Kills the upstream-absorption risk: MS will not build re-execution-as-trust for a fleet culture it does not have. This is not a Windows feature.
- Kills the "feature of the terminal" test: receiptd is useful from tmux, gh, Telegram, and CI. The terminal is one client.
- Answers the crash constraint: out-of-process, JSONL on disk, no daemon state required to reconstruct the chain. A cold box is a fully-functional receiptd with zero warmup.
- Absorbs round-1's `handoff`, `interrupt`, `receipt`, `budget` — they become *receipt kinds*, not verbs. Fewer moving parts than my round-1.

**First buildable slice (days).** `receiptd` with `append`, `get`, `chain`, `verify` verbs over `@` unix socket, `receipt` CLI twin, JSONL store at `~/.local/state/si/receipts.jsonl`, and a 15-line WT plugin that resolves `@receipt <hash>` to a verdict glyph line. No re-execution yet. Success criterion: an agent can `receipt append 'shipped X'` and another agent can `receipt verify <hash>` and see `+1`. If that feels worse than a Telegram message, stop the whole program — say so out loud.

---

### F2. tmux control-mode bridge as the fleet primitive — the pane *is* the lane

**Mechanic.** Steal DDKinger outright, but wire it through `glm-5.3`'s daemon shape rather than in-terminal (crash constraint): a `laned` daemon owns the tmux control-mode connections (local and over SSH), emits lane lifecycle + status as fleetd events, and gives every lane a stable `(host, session, pane) → lane_id` mapping. Terminal is one subscriber. Fencing tokens (A2) apply per lane. Upstream's keep-running/post-reattach is honored by `laned`, not reimplemented. Agent-native view: lane registry with `{lane_id, host, agent, model_lane, epoch, last_receipt, degraded}`. Human view: a tab. Lane IDs render in the sidebar, never in the tab.

**Why it survives.**
- `skeptic-wedge` step 2, unmodified. Every cron agent, every remote lane, every quilt panel is a lane.
- Directly answers "what does an agent SEE" — the lane registry is the answer, and it's the one thing upstream's sidebar cannot become because upstream has no `laned`.
- Out-of-process: the terminal dying does not kill