# agent-network-grammar (deepseek-chat)

# The Agent-Network Prompt: 10 Mechanics

The core move: **a prompt issued by an agent is the same byte stream a human would type**, wrapped in a transport envelope only the terminal and the receiving agent interpret. Humans see ticks. Agents see grammar. No new UI chrome required.

The envelope (all mechanics below reference this):
```
\u001b]1338;v=1;<verb>;<corr>;<budget>;<tier>;<room>;<hash>\u0007
```
An APC/DCS-style OSC that current terminals already ignore (invisible), that WT can parse into pane state, that agents emit via `write()`. The *line after it* is the actual prompt text. Humans see the prompt text. Agents see prompt + envelope.

---

## 1. `ask` — addressed prompt to a sibling pane

**Asking agent:** emits envelope `verb=ask;corr=<uuid>;room=<platoid>;tier=full` then `\n` then the prompt. Does not block. Registers `corr` in its own pending map.

**Answering pane:** the WT pane runtime sees the OSC, tags the incoming line with `(from=<pane_id>, corr=<uuid>)`, and hands it to whatever agent session owns that pane. That agent's prompt library resolves the text; it responds with a normal `\n`-terminated answer preceded by `verb=answer;corr=<same-uuid>`.

**Human sees:** two panes: one prints a question, one prints an answer. Looks like a terminal ticking.

**Why this beats tmux for agents:** `corr` is a first-class correlation ID, not a scrape. Repair = replay corr, not re-parse scrollback.

---

## 2. `gist` — tiered pane echoes (plato tiers, mechanically)

Every assistant turn in a pane is *written once* at full fidelity to the pane's receipt ring, but the pane's *visible* echo is rendered at the pane's declared tier:

- `tier=full`: tokens stream, human-readable.
- `tier=gist`: first paragraph + `[+N lines, gist-tier; ^g to expand]` — one line of chrome.
- `tier=hint`: single line — `⟦agent-3 gisted 41 tok, corr=a7f…⟧`.

Tier is set per-pane by the asking agent (`verb=tier;tier=gist`), by the room's policy, or by the human (`Ctrl-Alt-G` cycles). The full text is *always* in the ring; expansion is a keystroke or an `expand(corr)` call.

**Asking agent:** sets the sibling's tier before a long query, so it doesn't flood its own viewport.

**Answering pane:** renders at declared tier, writes full to ring, emits `verb=demote;corr=<uuid>;tier=gist` when it demotes.

**Human:** sees business-as-usual; may never know the pane was demoted.

---

## 3. `handoff` — pane custody transfer with a receipt

When agent A hands a task to agent B (both own panes):

```
\u001b]1338;v=1;handoff;corr=<uuid>;from=paneA;to=paneB;envhash=<sha256>\u0007
```

Followed by the environment seed (cwd, last N scrollback lines, room tiles, active pins) as a compacted block. Pane B acknowledges by emitting `verb=accept;corr=<uuid>;receipt=<hash-of-its-own-seed>`.

**Asking agent (A):** sees `accept` and can *drop* local state; it now watches `corr` for closure.

**Answering agent (B):** receives a seed it did not have to re-derive; runs with it.

**Human:** sees a paste-looking block scroll by, followed by activity in the other pane. If they hit `Ctrl-Alt-R`, they get the handoff receipt as a one-line status.

Hash mismatch → B emits `verb=reject;corr=…;why=seed-drift`; A's pending map flags it. That's the pinch on handoff.

---

## 4. `interrupt` — cooperative cancel, not SIGINT

Agents don't pound the pane with `^C`. They emit:

```
\u001b]1338;v=1;interrupt;corr=<uuid>;why=<enum>\u0007
```

`why ∈ {superseded, timeout, budget, drift, human}`. The receiving agent decides how to honor it: yield between tool calls, checkpoint then yield, or finish the atomic step then yield. It responds with `verb=interrupted;corr=…;at=stepN`.

**Asking agent:** waits for `interrupted` (bounded) before reissuing.

**Answering agent:** gets a *cooperative* interrupt it can act on — no half-written file, no orphaned child.

**Human:** may press `^C` themselves; terminal translates human `^C` into the same envelope with `why=human`. Same code path. That's the trick.

---

## 5. `pin` — @-tokens that resolve against the agent network, not the shell

The khayashi family, generalized. `@pane-7` resolves to pane 7's *current corr and last full turn*. `@room` resolves to the room's tile set. `@scrollback-tail(80)` yields the last 80 lines. `@pin(<sha>)` dereferences any pinned artifact in the shared pin store.

Resolution happens in the pane runtime *before* the prompt reaches the agent, so the agent sees concrete bytes, but the pane records the *symbolic* form in the receipt — receipts cite `@pane-7`, not 80 lines of text.

**Asking agent:** writes `explain @pane-7 @diff` — compact, stable across reflow.

**Answering agent:** receives the resolved text plus the symbolic citation, so its answer cites the same symbols.

**Human:** `@pane-7` just works at the prompt too. Same feature, no agent required.

---

## 6. `room` — the plato room as a memoized multi-pane context

A room is not a window. It's a logical ID (`room=si-plato-42`) that N panes may be attached to. Every turn any attached pane produces is appended to the room's tile log with `(pane, corr, tier, hash)`. Panes in the same room see each other's *gist* tier by default and can `expand(corr)` into full.

Rooms are versioned by Lamport counter on the room's log, so concurrent turns don't need wall-clock ordering.

**Asking agent:** emits `room=si-plato-42;tier=full` on its next prompt; everyone in the room now gets full detail for that corr.

**Answering agents in room:** inherit the tier, append their tiles.

**Human:** if they `cd` a pane into a room, the room's tiles background-load as an extra scrollback region (visible only on `Ctrl-Alt-O`). Otherwise invisible.

---

## 7. `receipt` — every agent turn writes exactly one, chained

Pane runtime hashes `(prev_hash, corr, input_hash, output_hash, tier, room)` after each turn and appends to `~/.local/state/wt/receipts/<pane>.chain`. Line-of-scrollback output carries no visible marker. `Ctrl-Alt-R` shows the last receipt. `wt-receipt check <corr>` re-executes and compares — that's trust = re-execution, out of process.

**Asking agent:** can require `receipt-before-continue` on high-stakes corr (`verb=ask;ack=receipt-required`). The answering pane won't send its answer until its receipt head has advanced.

**Answering agent:** writes the receipt as a side effect of finishing.

**Human:** nothing changes on screen. Re-verification is a CLI they can run when they *care*.

This is the single most important mechanic: **it makes the terminal an audit substrate without making it look like an audit tool**.

---

## 8. `budget` — conservation as an envelope field, enforced at the seam

Each corr carries `budget=<tok|gpuwh|usd>`. The pane runtime meters the answering agent's cost (token count from the agent's own report; GPU-Wh from a `nvidia-smi` sampler the runtime owns) and, on overrun, emits `verb=budget-exceeded;corr=…;over_by=…`. The asking agent sees this as a typed failure, not a hang.

At the room level, budgets roll up; `Ctrl-Alt-B` shows a per-room burn bar for ~5 seconds, then fades (so it's not "always-on dashboard" — it's a peek).

**Asking agent:** supersedes with a smaller `tier=hint` corr, or escalates to a human-gated `verb=override`.

**Answering agent:** checks budget at each tool boundary; exits cleanly if it must.

**Human:** sees nothing until the peek key is pressed, or until a room hits 90% (then a one-line hint in the pane title).

---

## 9. `pinch` — zero-LLM intent match at the prompt line

The asking agent doesn't need to phrase; it emits `verb=pinch;purpose=<tag>` followed by `\n`. The runtime runs the pinch matcher over the room's repo-card index and returns the top-1 as a candidate prompt to the *calling* pane (not sent yet). Only on `verb=confirm` does it go out.

This is the "as an agent, do I already know who handles this?" reflex, hooked into the prompt line.

**Asking agent:** gets a candidate + score; confirms or refines.

**Candidate pane:** sees a normal `ask` only after confirmation. Never sees the rejection.

**Human:** if they type `:` followed by a purpose tag, they get the same routing suggestion as a completion menu. It's the shell's tab-completion, grown up.

---

## 10. `scratchpaper` — the off-attention clerk, addressable from any pane

A dedicated background agent (its own pane in a hidden room `room=_scratch`) accepts `verb=scratch;corr=…;subject=…;ttl=…`. It maintains a rolling thinking sheet; panes can `@scratch(<subject>)` to pull its current line into a prompt. Its own outputs are always `tier=hint` in the human-visible stream unless `Ctrl-Alt-S`.

**Asking agent:** offloads background reasoning (register pressure from a context) without polluting its own scrollback.

**Scratchpaper clerk:** receives subject + TTL, reasons, updates sheet, emits `verb=scratch-ready;corr=…;key=…`.

**Human:** sees basically nothing. Occasionally one line in the title bar: `scratch: 3 live`.

---

## What ties these together

Three invariants make the whole thing feel like a normal terminal to a human and like a network to an agent:

1. **One transport.** Every mechanic is the same OSC. Any agent that can `write()` can participate. No SDK.
2. **One correlation model.** `corr` threads every ask/answer/handoff/interrupt/receipt. Repair, replay, and audit all reduce to `corr` → chain lookup.
3. **One visibility rule.** Full fidelity is always in the ring. The screen is a *rendering* of the ring at the pane's declared tier. Humans see one tier; agents negotiate theirs. Nothing is hidden — it's just not *painted*.

## Out-of-process, per the crash constraint

- Pane runtime