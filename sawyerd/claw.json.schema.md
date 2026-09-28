# claw.json.schema.md — the job-contract schema

*Sawyer's load-bearing decision: the unit of orchestration is a **preemptible,
resource-declared job contract**, not a process. Every worker — CUDA kernel, NPU
bot, CPU lane model, cloud subagent — advertises its cost in a manifest like the
one below, and Sawyer leases it. Discovery is `claws/*/claw.json`; there is no
central registration.*

Two documents, one contract:

| Artifact | Written by | Where |
|---|---|---|
| `claw.json` — the **declaration** (static, versioned, lives in the claw dir) | the claw author | `claws/<claw>/claw.json` |
| `job.json` — the **instance** (one per evocation, spooled append-only) | Sawyer | `spool/jobs.jsonl` |

Declared vs measured is kept forever: first contact runs a tiny calibration
probe and records the real VRAM/time *beside* the declared numbers. Drift
between them is a signal, not an error.

---

## 1. `claw.json` — the static declaration

```jsonc
{
  "name": "correlate-cuda",              // required · stable id; job contracts reference this
  "version": "0.1.0",                    // required · semver; receipts pin name+version
  "abi": "cudaclaw-v1",                  // runner contract: stdin JSON -> stdout JSON receipt
  "kind": "cudaclaw",                    // required · cudaclaw | chipbot | chiaroscuro | subagent
                                         //   LOCAL kinds => FREE lane; anything else => METERED

  "vram_ceiling_bytes": 6291456000,      // required · DECLARED worst-case VRAM reservation
                                         //   (may also be given as vram_ceiling_mb)
  "duration_class": "ms-small",          // required · us | ms-small | ms | s | long
                                         //   long => HARVEST level only, never co-resident
  "chip": "cuda",                        // cuda | npu | cpu | igpu | remote
  "cancel_poll_interval_ms": 1000,       // required for evictable claws; chunk boundary <= 2 s

  "input_schema":  { "type": "object", "required": ["files"], "properties": { /* JSON Schema */ } },
  "output_schema": { "type": "object", "properties": { /* JSON Schema */ } },

  "determinism_policy": "seed=2718",     // required · fixed seed 2718 is the fleet default
  "seed_policy": {                       // how a job's seed is chosen / carried
    "mode": "fixed",                     // fixed | derive-from-input | random-but-recorded
    "default": 2718,
    "derive": "sha256(inputs)[:8]"       // when mode=derive-from-input
  },
  "preemption": {                        // cooperative eviction semantics
    "mode": "cooperative",               // cooperative | none | checkpoint
    "checkpoint": "auto",                // writes job.<id>.ckpt at chunk boundary
    "requeue": true                      // preempted => re-queued, not failed
  },
  "telemetry": { "mode": "heartbeat-stderr-every-2s",
                 "fields": ["vram_mb","gpu_temp_c","util_pct","items_per_sec","progress","phase"] },
  "resources": { "vram_mb": 6000, "sm_pct": 80, "cpu_threads": 2 }   // advisory, for co-residency math
}
```

### Runner contract (ABI)

One process per job. Boring on purpose — no sockets, no shm, no daemon.

- **in:** one JSON job descriptor on **stdin**.
- **out:** exactly one JSON receipt on **stdout**, then exit.
- **progress/heartbeat:** stderr only, every ≤2 s, stdout stays clean.
- **cancel:** honour `SIGTERM` and the control file `state/job.<id>.throttle`
  (0.0–1.0) at chunk boundaries; exit `{"status":"preempted","progress":x}`.
- **exit codes:** `0` ok · `10` preempted · `20` bad input · `30` resource refusal · `40` internal.
- **rule:** no chunk boundary may exceed ~2 s of unthrottleable work.
- **honesty:** a receipt is written on failure too, and never edited. Absent
  receipt = the job never happened. Ignoring SIGTERM past the deadline earns a
  `"dishonest death"` entry in the ledger.

Example receipt:

```json
{"status":"ok","progress":1.0,"seed":2718,"wall_seconds":1.42,
 "peak_vram_mb":412,"throughput":184000.0,"output_hash":"sha256:...",
 "telemetry":"ok","verdict":"matches CPU reference within float tolerance"}
```

---

## 2. `job.json` — the runtime instance (what Sawyer spools)

`spool/jobs.jsonl` is append-only; one line per state change; last line per
`job_id` wins on replay. Fields mirror `JobContract` in `sawyerd.py`:

| Field | Meaning |
|---|---|
| `job_id` | unique; idempotent re-submission collapses to the same id |
| `claw` | which declared claw honours it |
| `lane` | `free` (local silicon, harvested) · `metered` (LLM guide, capped per epoch) |
| `vram_ceiling_mb` | admission number; `ceiling + 1792 MB reserve <= free VRAM` |
| `duration_class` | drives the ramp: `long` only ever leased at HARVEST |
| `seed` | defaults to 2718; recorded so the run is reproducible |
| `io` | `{"in": {...}, "out": {...}}` — concrete values for this evocation |
| `priority` | higher first; ties break by submission order |
| `submitted_by` | `sawyerd` · `chiaroscuro` · `casey` · subagent id |
| `state` | `queued` → `running` → `done`/`preempted`/`failed` |
| `progress` | 0.0–1.0, updated from heartbeats |

---

## 3. Admission rules (v1, 6 GB card)

1. **Reserve first.** `VRAM_RESERVE_MB = 1792` is untouchable — foreground
   work must never stall because a cudaclaw got greedy.
2. **Best-fit by declared ceiling**, then amended by the calibration measurement.
3. **Co-residency:** small jobs may share below ~80% of 6 GB; one heavy job at a
   time. Long-duration claws are HARVEST-only.
4. **Lane rule:** if `kind` is not local, the job is metered and needs ledger
   headroom this epoch. Guides never displace grinders.
5. **Degraded telemetry** (`"telemetry":"degraded"`, e.g. WSL2 NVML quirks)
   ⇒ idle score 0.0 ⇒ PARKED ⇒ sensor-only until measurement returns.
6. **Dishonest claws lose trust:** a claw that under-reports VRAM and OOM-kills
   the card gets a lower VRAM trust score and a wider measured margin.

### Open questions (carried from the cudaclaw spec)

- Co-residency accounting when claws under-report VRAM → "VRAM trust score".
- Do NPU/iGPU bots speak `claw.json`, or a sibling `npuclaw.json`? Current
  answer in the skeleton: same manifest, `"kind": "chipbot"`, `"chip": "npu"`.
