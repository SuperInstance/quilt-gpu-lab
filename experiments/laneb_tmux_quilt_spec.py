"""Lane B — tmux-quilt integration spec (DeepSeek-Pro navigator).

Reads tmux-quilt's architecture docs, produces a concrete merge/integration spec:
how quilt-canvas-tui's bridge becomes tmux-quilt's mission-command panel.
Writes: /home/eileen/scratch/tmux_quilt_integration_spec.md
"""
import json
import os
import urllib.request

TQ = os.path.expanduser("~/projects/tmux-quilt-readonly")
KEY = open(os.path.expanduser("~/.config/deepseek/token")).read().strip()

context_parts = []
for rel, cap in [("ARCHITECTURE.md", 9000), ("MECHANICAL_OPERATIONS.md", 6000),
                 ("docs/IMPLEMENTATION.md", 5000), ("CLAUDE.md", 3000)]:
    p = os.path.join(TQ, rel)
    if os.path.exists(p):
        context_parts.append(f"===== {rel} =====\n" + open(p).read()[:cap])
canvas_ctx = """===== quilt-canvas-tui bridge (what exists) =====
- Fabric: bind/link/effect/view/tick/forget opcodes; cells = addr + dial array (uint32 fractions x10000) + kind; journal = receipt chain, FNV-1a64 digests; LINK cycle-rejected (DAG).
- controller.mjs: authoritative Fabric over unix socket (NDJSON, /tmp/quilt-canvas/socks/*.sock); PoEM gate: mutating ops only run if ledger verifies; broadcasts update diffs to all peers; canvas is a peer, not a display.
- fleet_board.mjs: dogfood board binding real lane receipts as cells (e.g. [4688, 9844] = control 0.4688).
- quilt-tui-c/: C99 TUI port mid-flight (journal byte-match pinned); chiaroscuro projection engine; signing.mjs receipt signing.
- claude-canvas lineage: tmux split panes render canvases; controller drives via socket; templates registry (calendar, document, flight) keyed kind:scenario."""

prompt = f"""You are the navigator (DeepSeek V4) producing an integration spec for two fleet repos.

TASK: Specify how quilt-canvas-tui's bridge becomes tmux-quilt's mission-command visualization
layer. The vision (fleet captain): any agent (OpenClaw, Claude Code) works in a tmux session;
a second panel is a live quilt fabric showing every agent lane as a cell lighting up on real
receipts — a projected switchboard. tmux-quilt already has: parallel Claude sessions with
sandboxes, shared memory, per-session repo branches, rollback. The right panel of the workbench
should be a spreadsheet, file-tree, or markdown-editor depending on the top tab; claude-canvas
templates should work as tiled tabs.

Deliver, concretely and file-level:
1. MAPPING TABLE: tmux-quilt primitives (session, sandbox, shared memory, branch, rollback) ->
   fabric opcodes/cells (bind/link/effect/tick/forget) -> what the viewer pane shows.
2. EVENT BUS: where tmux-quilt emits session lifecycle events today (name the exact files), and
   the minimal emitter patch to write NDJSON receipt lines that cudaclaw/fleet boards consume.
3. SOCKET TOPOLOGY: one controller per workbench vs per session; socket path conventions;
   how the PoEM receipt-gate maps to tmux-quilt's rollback (a refused op = a rollback trigger?).
4. PANEL/TAB PLAN: what a "tiled tab" is in the canvas-tui line today; the file-tree/spreadsheet/
   markdown-editor tabs as claude-canvas-template-compatible scenarios.
5. BUILD ORDER: 5 numbered steps, smallest shippable first, each with a FAIL-first pin.
6. RISKS: stale-fork hazards (the canvas-tui fork diverged from claude-canvas), node-vs-bun,
   the C port's scalar-vs-dial model split.

Be specific, cite file paths from the docs below. No fluff. Target ~1200-1800 words.

{chr(10).join(context_parts)}

{canvas_ctx}
"""

req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=json.dumps({"model": "deepseek-chat",
                     "messages": [{"role": "user", "content": prompt}],
                     "max_tokens": 4000, "temperature": 0.4}).encode(),
    method="POST",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as r:
    data = json.loads(r.read().decode())
text = data["choices"][0]["message"]["content"]
out = "/home/eileen/scratch/tmux_quilt_integration_spec.md"
with open(out, "w") as f:
    f.write(f"# tmux-quilt x quilt-canvas-tui — Integration Spec (lane B, DeepSeek-V4 navigator)\n\n{text}\n")
print(f"spec written: {out} ({len(text)} chars)")
