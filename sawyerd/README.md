# sawyerd — the always-on local orchestrator ("Tom Sawyer")

*A low-level GPU-handler engineer that **orchestrates rather than grinds** —
a Tom Sawyer who gets others to paint the fence. Status: **P1 skeleton**, 2026-09-27.*

Sawyer owns **no compute**. It holds **leases**. The unit of orchestration is a
preemptible, resource-declared **job contract** (`claw.json` — see
[`claw.json.schema.md`](claw.json.schema.md)), not a process. That single choice
makes throttling trivial (the ramp is just "how many contracts do we honour"),
recruitment symmetric across silicon (CUDA kernel / Ryzen NPU bot / CPU lane /
fleet subagent), and the daemon crash-safe: an absent receipt means the job
never happened.

## What's in here

| File | What it is |
|---|---|
| `sawyerd.py` | the daemon skeleton — sensor bus, four-level ramp, spool, registry, ledger, lane rule. 420 lines (≈320 of code+comments), stdlib only. |
| `claw.json.schema.md` | the job-contract schema — VRAM ceiling, duration class, I/O schema, seed policy, runner ABI, admission rules |
| `state/ramp.json` | written each tick: current level, EMA, throttle value, VRAM headroom (atomic replace) |
| `spool/jobs.jsonl` | append-only job log on ext4 — the record of intent and of every preemption |
| `claws/<name>/claw.json` | self-describing workers; discovery is a glob, never a registration call |

Run it:

```bash
python3 sawyerd.py --once                 # one tick, prints sensor/ramp JSON
python3 sawyerd.py --ticks 5              # five ticks, then exit
python3 sawyerd.py                        # block forever (systemd owns this)
```

Installed form: systemd unit with `Restart=always`, `MemoryMax` set, state on
**ext4** (never `/mnt/c`). One flat poll loop at 1 s, O(queue) memory, spool
checkpointed to disk — the crash-safe footprint is deliberate.

## The throttle ramp — Parked → Trickle → Cruise → Harvest

A **ramp with detents, not a switch**. Signals (GPU util, VRAM headroom, 1-min
load) are combined into an idle score, smoothed with an EMA (`α = 0.30`), and a
transition is committed only after the smoothed score has cleared the relevant
boundary by `HYSTERESIS = 0.08` **and** the level has been held for
`DWELL_S = 45 s`. It cannot flap.

| Level | Idle score | Capacity | What Sawyer honours |
|---|---|---|---|
| **L0 Parked** | < 0.30 | 0 leases | sensors + spool only; chiaroscuro frame-skips; existing leases preempted |
| **L1 Trickle** | ≥ 0.30 | 1 lease | one cheap worker (low-res ASCII, CPU/NPU bot) |
| **L2 Cruise** | ≥ 0.60 | 3 leases | multiple cudaclaws, honouring the 1792 MB headroom reserve |
| **L3 Harvest** | ≥ 0.85 | 8 leases | full queue drain, video batch, long kernels, overnight windows |

Degraded telemetry (WSL2 NVML quirks) ⇒ score 0.0 ⇒ Parked. Conservative by
construction: if we cannot see the GPU, we assume the human is using it.

Throttling of a running claw is cooperative and boring: Sawyer writes a control
value 0.0–1.0 to `state/job.<id>.throttle`; the claw reads it at its next chunk
boundary (≤ 2 s). No chunk boundary may exceed ~2 s of unthrottleable work.
Preemption is `SIGTERM → checkpoint → requeue`, with a `"dishonest death"` ledger
entry if the deadline is ignored.

## The two lanes — free vs metered

**Local silicon is free and harvested. LLM calls are metered and are guides,
never grinders.** A contract's lane is derived from its `kind`: local kinds
(`cudaclaw`, `chipbot`, `chiaroscuro`) are **free**; anything else is **metered**
and needs ledger headroom (`24 calls/epoch` in the skeleton) before it may run.
Guides never displace grinders, and the default posture is autonomous drift work
— humans and LLMs only nudge direction.

## Routing table — the brain

| Role | Model | Provider | When |
|---|---|---|---|
| **Default** | **glm-5.3-flash** | z.ai | everything |
| Clever / challenging friends | Seed-2.0-mini | DeepInfra | soundboarding, devil's advocate, novel angles |
| Task runners | glm-5.3-flash / turbo | z.ai | bulk lanes |
| Deep iterators (occasional) | glm-5.3 (full) + deepseek-v4-pro | z.ai / DeepSeek | high-level synthesis |
| Iterative, outside the big two | other DeepInfra models | DeepInfra | sparingly — conversations the big two can't hold |
| **Rate-limit fallback** | **deepseek flash** | DeepSeek | automatic understudy on z.ai 429s (hit live 09-27) |

Sawyer itself never calls a cloud model to grind. It posts **task cards** to the
fleet queue; the main agent dispatches subagents when their lanes are free.
Subagent output lands back in the spool as new jobs or contracts.

## Phases

- **Phase 1 — The Fence.** chiaroscuro gains the Screen door (screen-region
  capture → ASCII), video ingestion, two-panel viewer. Ship `sawyerd` v0:
  sensor bus + Parked/Trickle only, one cudaclaw contract (the chiaroscuro
  kernel chain). *Success = always-on without ever visibly stealing from
  Casey's foreground work.* ← **this increment: the skeleton above.**
- **Phase 2 — The Painters.** Full four-level ramp, spool + registry, 3–5
  cudaclaws (frame-diff, edge-detect, palette LUT, batch transcode), first NPU
  bot, VRAM headroom enforcement, budget ledger with nightly harvest windows.
  *Success = the overnight video queue drains itself at Harvest and yields
  before morning use.*
- **Phase 3 — The Crew.** Subagent task-card recruitment, guide escalation
  (local drift → stuck → one glm-5.3 consult → resume local), self-telemetry
  ("what did the machine think about all week?"), and a Director door composing
  long-form output from harvested queues. *Success = Sawyer plans its own next
  jobs from leftover artifacts.*

## The growth loop

Low-level training produces **custom models in our own framework** — LoRA
adapters (D15b's tone-channel reader, reading the channel at 0.94), local
Liquid/LFM models, quilt cell-kernels. Those become Sawyer's own recruitable
organs, and each generation helps build the next experiment. Intelligence that
starts helping at the most basic level — a tone-channel reader, a correlate
kernel — and compounds.

## Honest limits of this skeleton (P1)

- Leasing is real; **launching is not.** `_admit()` writes a lease and comments
  the P2 hook. No worker process is spawned yet.
- Per-job throttle files (`state/job.<id>.throttle`) are specified but only the
  level value in `state/ramp.json` is published so far.
- Size note: 420 lines against the informal 150–250-line skeleton budget. The
  overage is docstrings plus the reserve/lane/ledger machinery — nothing here is
  a pretend implementation; everything above is exercised by the smoke tests.
- Co-residency math is declared-only; the "VRAM trust score" is specified, not
  implemented.
- No SQLite queue yet (flat JSONL spool), no systemd unit shipped, no
  chiaroscuro integration, no subagent task-card poster.
- Telemetry is `nvidia-smi` + `/proc/loadavg` only; the Windows foreground-app
  bridge from the spec is future work.
