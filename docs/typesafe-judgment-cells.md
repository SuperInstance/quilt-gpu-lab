# TypeSafe Jev — judgment cells (verified call format, 2026-09-29)

Grabbable: any agent with curl + the TYPESAFE_AI_KEY can run structured judgment calls.

## What it is
api.typesafe.ai is NOT a chat API — it's a structured **judgment service**
("System One" models). You supply `state` (the content) + named questions; it
returns graded answers. This is the **pincher/filter cell primitive** as a
tunable API gate — graded booleans make pinch thresholds adjustable.

## Endpoint (verified end-to-end 2026-09-29)

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer $TYPESAFE_AI_KEY
Content-Type: application/json

{
  "model": "jev-preview",            // or "jev-latest"
  "state": "<string | object | array — the content all questions refer to>",
  "questions": {
    "gate": {
      "type": "noul",                // yes/no question
      "question": "Does the signal pass the noise gate?",
      "instructions": "Answer true only if amplitude exceeds threshold with margin above the noise floor."
    }
  }
}
```

Response (verified):
```json
{"model": "jev-1.13.0",
 "answers": {"gate": {"type": "noul", "noul": 0.94}},
 "usage": {"input_tokens": 309, "output_tokens": 20}}
```

**`noul` is a GRADED float (0..1)** — calibrated confidence, not true/false.
Pinch thresholds are tunable per gate.

## Question types (from OpenAPI, discriminates on `type`)
- `noul` — yes/no, needs `instructions` (string) or `criteria` (OBJECT, not
  list — list form rejected). Minimal: {"type":"noul","question":"...","instructions":"..."}
- `choice` — selects one of the choices in `criteria` (dict)
- `score` — rates using the levels in `criteria` (dict, required)

## Gotchas learned (each cost one round-trip)
1. `questions` must be a DICT of named questions, not a list.
2. Every question needs `type` ("noul"|"choice"|"score").
3. `criteria` must be an object/dict, never a list.
4. `min`/`max` are not score fields — use `criteria` levels.
5. models endpoint: GET /v1/models → jev-latest, jev-preview. (Nimble/Tev1 are NOT on this API —
   "Unknown model" 2026-09-30; they ship via Ollama/Together/Bespoke distribution = the local
   student class.)
6. Marketing site (typesafe.ai) has no API — use api.typesafe.ai.
7. `score` criteria must be a LIST of ordered level descriptions (400-verified 2026-09-30);
   `choice` criteria stays a dict; noul takes instructions string or criteria object.
8. Response shape (jev-1.13.0, richer than first verified 09-29): every answer carries `confidence`
   + `probabilities`; `score` returns a graded FLOAT interpolated between levels (e.g. 2.12) plus an
   echoed `legend`; `choice` returns the chosen label + full probability dict.

## Where the key lives
`/mnt/c/Users/casey/key.txt` → TYPESAFE_AI_KEY (read at use-time, never store values).

## Fleet use
Judgment cells in the CM1 mesh: generative cells route, Jev cells pinch/filter
(graded noul = tunable gate). Also standalone: cheap content triage, routing
decisions, verification gates — anywhere a calibrated yes/no beats a chat call.

Smoke transcript: state = relay stimulus S7 (amplitude 0.82 / threshold 0.5 /
noise 0.31), question = pass the gate? → noul 0.94 (correct: yes with margin).
