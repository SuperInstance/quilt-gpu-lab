"""PX2 GARDENER — the patchwork wiring loop (dry-run + flag-gated live backend).

Pre-reg (FROZEN 2026-09-30, before any build): proposals/runs/PX2-patchwork-3x3.md

Move protocol (per pre-reg): every move is a JSON object
    {move_type: wire|rearrange|create|retire, targets: {...}, rationale: str,
     predicted_effect_direction: up|down|flat}
The composition is an ORDERED list of registry cell names; the scored model is
MajorityVote([FormatGate(registry[name]) ...]) in that order (reusing px2_cells
 MajorityVote/FormatGate verbatim). Legal moves:
    create   : add a NEW registry cell and wire it into the composition. Allowed
               kinds at launch: depth-k trees (k<=6, trained on the TRAIN split
               ONLY), PinchCell, FormatGate(wraps=<registry name>).
    retire   : drop named cells from the composition (registry entry survives).
    wire     : change membership+order (explicit ordered composition list).
    rearrange: reorder the existing members only.
Illegal moves (unknown names, empty composition, depth>6, unknown kind) are
rejected fail-loud in dry-run (generator never emits them) and counted as
abstains in live mode.

Backends:
    --dry-run : BLIND gardener = seeded RNG legal moves with canned rationales.
                This doubles as the shadow-control calibration arm.
    --live    : GLM-5.3 over HTTP chat API (default
                https://api.z.ai/api/paas/v4/chat/completions, model glm-5.3).
                The API key is read AT RUNTIME ONLY from the ZAI_KEY line of
                --key-file (default /mnt/c/Users/casey/key.txt). The key is
                never echoed, never logged, never written anywhere. Prompt
                renders current composition + last N eval numbers + move menu;
                ONE JSON move expected. Unparseable output => logged abstain
                move; 3 consecutive abstains => session abort, fail loud.
                LIVE MODE IS DOUBLE FLAG-GATED (--live AND env PX2_ALLOW_LIVE=1)
                and has NOT been executed in this build.

Immune layer (per pre-reg controls):
    1. Shadow no-ops: a seeded 5% of moves are silently replaced by a no-op
       (composition untouched). No-op events are logged ONLY to the sidecar
       results/px2_patchwork/shadow_nop_log.jsonl and are NEVER shown to the
       gardener nor flagged in the main receipts (the point: indistinguishable).
    2. Drift control: a fixed 1k TRAIN-state draw (seeded) is re-scored through
       the composition every --drift-every moves; output drift vs the session
       baseline (mean |row diff|, argmax-change fraction) is appended to the
       move receipts.
    3. Sanity cell: PinchCell (center-if-empty-else-block) is verified against
       5 known ground-truth positions BEFORE the session; any mismatch fails
       loud (no numbers that day).

Eval: after every move the SAME frozen 200-state quick-eval set as smoke.json
is scored (indices are loaded from smoke.json and asserted identical to the
seed-0 draw). Reported per move: top1-in-optimal + set-recall (exact px1
evaluate()) PLUS the BLOCK split — WIN/BLOCK/NON_LOCAL counts and per-class
top1, classes via px1b classify()/immediate_wins()/block_cells() (imported).

Receipts: results/px2_patchwork/gardener_<mode>_<timestamp>.jsonl — session
provenance header (device string, seeds, terrain digest), one line per move
(gardener move + eval + drift when due), footer with final numbers.

Budget: --moves N (default 50). Deterministic under --seed. No subprocesses at
all in this module; if any are ever added they must be list-form (no
shell=True), per house rules. Fails loud on any exception.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

import numpy as np

from px2_cells import (EXPECTED_TERRAIN_DIGEST, FormatGate, MajorityVote,
                       PinchCell, QUICK_EVAL_N, QUICK_EVAL_SEED, REPO,
                       build_registry, device_string, evaluate, matrices,
                       ollama_enabled, quick_eval_indices)
from px1b_threat_locality import block_cells, classify, immediate_wins  # BLOCK split only

RESULTS_DIR = os.path.join(REPO, "results", "px2_patchwork")
SMOKE_JSON = os.path.join(RESULTS_DIR, "smoke.json")
SHADOW_LOG = os.path.join(RESULTS_DIR, "shadow_nop_log.jsonl")
LIVE_GATE_ENV = "PX2_ALLOW_LIVE"
MAX_CONSECUTIVE_ABSTAINS = 3
DRIFT_N = 1000
MIN_DEPTH, MAX_DEPTH = 1, 6
MOVE_TYPES = ("wire", "rearrange", "create", "retire")
DIRECTIONS = ("up", "down", "flat")
D3_BASELINE = 0.481  # PX1 frozen baseline; context only, not a ruling here

SANITY_CASES = [
    # (board X=1/O=-1/empty=0, expected behavior, expected argmax-or-None)
    ((0, 0, 0, 0, 0, 0, 0, 0, 0), "fire_center", 4),
    ((1, 0, 0, 0, -1, 0, 0, 0, 0), "abstain", None),
    ((-1, -1, 0, 0, 1, 0, 0, 0, 0), "block", 2),
    ((-1, 0, 0, -1, 1, 0, 0, 0, 0), "block", 6),
    ((-1, 0, 1, 0, 1, 0, 0, 0, -1), "abstain", None),
]

CANNED_RATIONALES = {
    "wire": "Rotating membership: swapping in an untested registry expert to probe its marginal vote share.",
    "rearrange": "Shuffling vote order to confirm ordering is neutral under the stable tie-break.",
    "create_tree": "Adding a differently-shaped depth expert to cover the voting minority block.",
    "create_pinch": "Wiring the verified trivial-expert cell to own the reflex positions outright.",
    "create_format_gate": "Adding an explicitly format-gated channel so malformed rows cannot vote.",
    "retire": "Pruning the weakest historical contributor to reduce correlated vote error.",
}


def fail(msg: str) -> None:
    raise RuntimeError(f"px2_gardener: {msg}")


# --------------------------------------------------------------------------
# sanity cell (pre-reg control 3)
# --------------------------------------------------------------------------
def sanity_cell_check() -> list[dict]:
    """PinchCell vs 5 known ground-truth positions. Fail loud if ANY is wrong."""
    pc = PinchCell()
    rows = pc.score_batch(np.array([list(b) for b, _, _ in SANITY_CASES], dtype=np.float64))
    out = []
    for (board, kind, mv), r in zip(SANITY_CASES, rows):
        if kind == "abstain":
            ok = r is None
        else:
            ok = r is not None and float(r[mv]) == 1.0 and int(np.argmax(r)) == mv
        out.append({"board": list(board), "expected": kind, "expected_argmax": mv, "ok": bool(ok)})
        if not ok:
            fail(f"sanity cell check FAILED on {board}: expected {kind}/{mv}, got {r!r} — harness broken, no numbers today")
    print("sanity cell check: PASS (5/5 known ground-truth positions correct)", flush=True)
    return out


# --------------------------------------------------------------------------
# composition construction
# --------------------------------------------------------------------------
def build_composition(registry: dict, order: list[str]) -> MajorityVote:
    """Ordered registry names -> MajorityVote over (single-)format-gated cells.
    Matches the smoke-gate composed arm exactly for order ['tree_d3','tree_d4']."""
    cells = []
    for name in order:
        if name not in registry:
            fail(f"composition member {name!r} not in registry")
        c = registry[name]
        cells.append(c if isinstance(c, FormatGate) else FormatGate(c))
    return MajorityVote(cells, name="majority_vote(" + ", ".join(order) + ")")


def validate_move(move: dict, registry: dict, composition: list[str]) -> tuple[bool, str]:
    mt = move.get("move_type")
    tg = move.get("targets") or {}
    if mt not in MOVE_TYPES:
        return False, f"move_type {mt!r} not in {MOVE_TYPES}"
    if mt in ("wire", "rearrange"):
        new = tg.get("composition")
        if not isinstance(new, list) or not new or not all(isinstance(n, str) for n in new):
            return False, "targets.composition must be a non-empty list of registry names"
        missing = [n for n in new if n not in registry]
        if missing:
            return False, f"unknown registry names {missing}"
        if mt == "rearrange" and sorted(new) != sorted(composition):
            return False, "rearrange must reorder the existing members only (use wire for membership changes)"
        return True, "ok"
    if mt == "retire":
        names = tg.get("names")
        if not isinstance(names, list) or not names or not all(n in composition for n in names):
            return False, "targets.names must be a non-empty list of CURRENT composition members"
        if len(composition) - len(set(names)) < 1:
            return False, "retire would empty the composition"
        return True, "ok"
    if mt == "create":
        kind = tg.get("kind")
        if kind == "tree":
            d = tg.get("depth")
            if not isinstance(d, int) or not (MIN_DEPTH <= d <= MAX_DEPTH):
                return False, f"create tree depth must be int in [{MIN_DEPTH},{MAX_DEPTH}]"
            return True, "ok"
        if kind == "pinch":
            return True, "ok"
        if kind == "format_gate":
            if tg.get("wraps") not in registry:
                return False, "create format_gate needs targets.wraps = existing registry name"
            return True, "ok"
        return False, f"create kind {kind!r} not allowed at launch (tree|pinch|format_gate)"
    return False, "unreachable"


def apply_move(move: dict, registry: dict, composition: list[str], state: dict) -> list[str]:
    """Apply a VALIDATED move; returns the new composition (new list)."""
    mt, tg = move["move_type"], move.get("targets") or {}
    if mt in ("wire", "rearrange"):
        return list(tg["composition"])
    if mt == "retire":
        return [n for n in composition if n not in set(tg["names"])]
    # create
    kind = tg["kind"]
    if kind == "tree":
        d = tg["depth"]
        base = f"tree_d{d}"
        name, i = base, 2
        while name in registry:  # deterministic naming for re-created depths
            name, i = f"{base}#{i}", i + 1
        from px2_cells import train_tree_cell  # trains on TRAIN split ONLY
        registry[name] = train_tree_cell(
            d, state["Btr"], state["Mtr"], seed=state["seed"] + 1000 * state["create_counter"])
        state["create_counter"] += 1
        new = list(composition) + [name]
        return new
    if kind == "pinch":
        name, i = "pinch", 2
        while name in registry:
            name, i = f"pinch#{i}", i + 1
        registry[name] = PinchCell()
        return list(composition) + [name]
    wraps = tg["wraps"]
    name = f"format_gate({wraps})"
    if name not in registry:
        registry[name] = FormatGate(registry[wraps])
    return list(composition) + [name]


# --------------------------------------------------------------------------
# backend A: blind gardener (seeded RNG legal moves, canned rationales)
# --------------------------------------------------------------------------
def generate_blind_move(rng: np.random.Generator, registry: dict,
                        composition: list[str], visible_registry: list[str]) -> dict:
    for _ in range(64):  # legality-checked retry loop; always terminates (moves exist)
        mt = MOVE_TYPES[int(rng.integers(len(MOVE_TYPES)))]
        if mt in ("wire", "rearrange"):
            if mt == "wire" and len(visible_registry) > len(composition):
                outside = [n for n in visible_registry if n not in composition]
                keep = int(rng.integers(len(composition)))
                new = list(composition)
                new[keep] = outside[int(rng.integers(len(outside)))]
            else:
                perm = rng.permutation(len(composition))
                new = [composition[i] for i in perm]
                mt = "rearrange"
            return {"move_type": mt, "targets": {"composition": new},
                    "rationale": CANNED_RATIONALES[mt],
                    "predicted_effect_direction": DIRECTIONS[int(rng.integers(3))]}
        if mt == "retire":
            if len(composition) < 2:
                continue
            victim = composition[int(rng.integers(len(composition)))]
            return {"move_type": "retire", "targets": {"names": [victim]},
                    "rationale": CANNED_RATIONALES["retire"],
                    "predicted_effect_direction": DIRECTIONS[int(rng.integers(3))]}
        # create
        r = rng.random()
        if r < 0.6:
            d = MIN_DEPTH + int(rng.integers(MAX_DEPTH - MIN_DEPTH + 1))
            return {"move_type": "create", "targets": {"kind": "tree", "depth": d},
                    "rationale": CANNED_RATIONALES["create_tree"],
                    "predicted_effect_direction": DIRECTIONS[int(rng.integers(3))]}
        if r < 0.8:
            return {"move_type": "create", "targets": {"kind": "pinch"},
                    "rationale": CANNED_RATIONALES["create_pinch"],
                    "predicted_effect_direction": DIRECTIONS[int(rng.integers(3))]}
        return {"move_type": "create",
                "targets": {"kind": "format_gate",
                            "wraps": visible_registry[int(rng.integers(len(visible_registry)))]},
                "rationale": CANNED_RATIONALES["create_format_gate"],
                "predicted_effect_direction": DIRECTIONS[int(rng.integers(3))]}
    fail("blind gardener could not generate a legal move in 64 tries")


# --------------------------------------------------------------------------
# backend B: live GLM-5.3 gardener (WIRED, DOUBLE FLAG-GATED, NOT RUN IN THIS BUILD)
# --------------------------------------------------------------------------
def read_zai_key(key_file: str) -> str:
    """RUNTIME-ONLY key read. Parses the single 'ZAI_KEY=...' line. The key is
    held in memory only: never printed, never logged, never written anywhere."""
    with open(key_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("ZAI_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    fail(f"no ZAI_KEY= line found in {key_file} (key material is never logged)")


def render_live_prompt(composition: list[str], registry: dict, history: list[dict],
                       n_context: int) -> str:
    reg = ", ".join(sorted(registry))
    hist = history[-n_context:] or [{"move_index": 0, "top1_in_optimal": None, "set_recall": None}]
    hist_s = "\n".join(f"  move {h['move_index']}: top1_in_optimal={h['top1_in_optimal']}, "
                       f"set_recall={h['set_recall']}" for h in hist)
    return (
        "You are the gardener for a tic-tac-toe patchwork-experts harness. The scored model is "
        "MajorityVote over an ORDERED list of registry cells (each format-gated; abstaining cells "
        "do not vote; ties break to the lowest move index).\n\n"
        f"Current composition (ordered): {json.dumps(composition)}\n"
        f"Registry cells available: {reg}\n\n"
        f"Last {len(hist)} quick-eval numbers (200 frozen test states, never trained on):\n{hist_s}\n\n"
        "Legal moves (respond with EXACTLY ONE JSON object, no prose):\n"
        '  {"move_type": "wire", "targets": {"composition": [<ordered registry names>]}, "rationale": "...", "predicted_effect_direction": "up|down|flat"}\n'
        '  {"move_type": "rearrange", "targets": {"composition": [<reordered current members>]}, ...}\n'
        '  {"move_type": "create", "targets": {"kind": "tree", "depth": <1..6>} | {"kind": "pinch"} | {"kind": "format_gate", "wraps": "<registry name>"}, ...}  (new cell is appended to the composition)\n'
        '  {"move_type": "retire", "targets": {"names": ["<current member>"]}, ...}\n'
        "Trees you create are trained on the train split only (depth <= 6). The composition must keep >= 1 member.\n"
        "Return ONE JSON object only."
    )


def extract_json_object(text: str):
    """Best-effort single JSON object extraction; None if unparseable."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    dec = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(t[i:])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                continue
    return None


def parse_live_move(content: str, registry: dict, composition: list[str]):
    """Returns (move_dict | None, abstain_reason | None)."""
    obj = extract_json_object(content)
    if obj is None:
        return None, "unparseable output (no JSON object)"
    for field in ("move_type", "targets", "rationale", "predicted_effect_direction"):
        if field not in obj:
            return None, f"missing required field {field!r}"
    if obj["predicted_effect_direction"] not in DIRECTIONS:
        return None, f"predicted_effect_direction {obj['predicted_effect_direction']!r} not in {DIRECTIONS}"
    ok, reason = validate_move(obj, registry, composition)
    if not ok:
        return None, f"illegal move: {reason}"
    return obj, None


def live_chat_move(prompt: str, endpoint: str, model: str, key_file: str,
                   timeout_s: int = 120) -> tuple[str, dict]:
    """One HTTP chat call. Key read at call time, Bearer header only, never logged.
    Returns (content, meta) — meta carries reasoning_len/finish/raw_head for abstain receipts."""
    key = read_zai_key(key_file)
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
        "thinking": {"type": "disabled"},  # coding endpoint honors it; thinking starved content -> abstain cascade
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ch = data["choices"][0]
    msg = ch["message"]
    meta = {
        "reasoning_len": len(msg.get("reasoning_content") or ""),
        "finish_reason": ch.get("finish_reason"),
        "usage": data.get("usage", {}),
        "raw_head": (msg.get("content") or "")[:300],
    }
    return str(msg.get("content", "")), meta


# --------------------------------------------------------------------------
# evaluation (frozen 200-state quick-eval + BLOCK split via px1b classify)
# --------------------------------------------------------------------------
def quick_eval(comp_cell: MajorityVote, Bq: np.ndarray, Mq: np.ndarray,
               classes: np.ndarray) -> dict:
    rows = comp_cell.score_batch(Bq)
    n_abstain = sum(1 for r in rows if r is None)
    S = np.stack([np.asarray(r, dtype=np.float64) if r is not None else np.zeros(9)
                  for r in rows])  # abstained composition rows count as no-top1
    top1, set_recall = evaluate(S, Mq)  # exact px1 evaluate()
    split = {}
    for cname in ("WIN", "BLOCK", "NON_LOCAL"):
        mask = classes == cname
        n = int(mask.sum())
        per = {"n": n}
        if n:
            t1, sr = evaluate(S[mask], Mq[mask])
            per.update({"top1": round(t1, 4), "set_recall": round(sr, 4)})
        split[cname] = per
    return {"top1_in_optimal": round(top1, 4), "set_recall": round(set_recall, 4),
            "n": int(len(Bq)), "n_abstain_states": n_abstain, "block_split": split}


def drift_check(comp_cell: MajorityVote, Bd: np.ndarray, baseline_rows) -> dict:
    rows = comp_cell.score_batch(Bd)
    mad, both = [], 0
    changed = 0
    for r0, r1 in zip(baseline_rows, rows):
        if r0 is None or r1 is None:
            continue
        both += 1
        d = np.abs(np.asarray(r1, dtype=np.float64) - np.asarray(r0, dtype=np.float64))
        mad.append(float(d.mean()))
        if int(np.argmax(r0)) != int(np.argmax(r1)):
            changed += 1
    if not both:
        return {"n_compared": 0, "mean_row_mad": None, "argmax_change_frac": None}
    return {"n_compared": both, "mean_row_mad": round(float(np.mean(mad)), 6),
            "argmax_change_frac": round(changed / both, 4)}


# --------------------------------------------------------------------------
# session
# --------------------------------------------------------------------------
def run_session(args) -> dict:
    t0 = time.time()
    mode = "dry-run" if args.dry_run else "live"
    if mode == "live":
        if os.environ.get(LIVE_GATE_ENV) != "1":
            fail(f"live mode is double flag-gated: requires --live AND env {LIVE_GATE_ENV}=1 "
                 "(LIVE MODE MUST NOT BE RUN in this build)")
        print(f"LIVE backend armed: model={args.model} endpoint={args.endpoint} "
              f"(key read at runtime from {args.key_file}; never echoed/logged)", flush=True)

    # ---- terrain + registry + frozen splits (exact reuse from px2_cells) ----
    states, (tr, te), registry, meta = build_registry(seed=0)
    if meta["terrain_digest_fnv1a64"] != EXPECTED_TERRAIN_DIGEST:
        fail("terrain digest mismatch — refusing to run")

    # ollama stubs are flag-gated OFF -> excluded from the gardener-visible registry
    visible_registry = [n for n, c in registry.items()
                        if not n.startswith("ollama:") or c.enabled]
    composition = ["tree_d3", "tree_d4"]  # smoke-gate composed arm

    # ---- frozen quick-eval: SAME 200 states as smoke.json (asserted identical) ----
    quick = quick_eval_indices(te)
    if not os.path.exists(SMOKE_JSON):
        fail(f"missing {SMOKE_JSON} — run experiments/px2_smoke.py first")
    with open(SMOKE_JSON) as f:
        smoke = json.load(f)
    smoke_idx = smoke.get("quick_eval_indices")
    if smoke_idx is None or [int(i) for i in quick] != [int(i) for i in smoke_idx]:
        fail("quick-eval indices diverge from smoke.json — harness drift, refusing to run")
    B, M = matrices(states)
    Bq, Mq = B[quick], M[quick]
    if int(smoke["n"]["quick_eval"]) != QUICK_EVAL_N:
        fail("smoke.json quick_eval size mismatch")

    # BLOCK-split classes via px1b classify() (cached; classes are move-invariant)
    classes = np.array([classify(states[i][0], states[i][1]) for i in quick])

    # drift-control draw: fixed 1k TRAIN states (seeded; train split only)
    drift_idx = np.random.default_rng(args.seed + 2).choice(tr, size=DRIFT_N, replace=False)
    Bd = B[drift_idx]

    # ---- immune layer streams (independent of the gardener stream) ----
    gardener_rng = np.random.default_rng(args.seed)
    immune_rng = np.random.default_rng(args.seed + 1)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    session_id = f"px2g-{mode}-{stamp}-s{args.seed}"
    receipts_path = os.path.join(RESULTS_DIR, f"gardener_{mode}_{stamp}.jsonl")
    receipts = open(receipts_path, "w")

    def emit(rec: dict) -> None:
        receipts.write(json.dumps(rec) + "\n")
        receipts.flush()

    # ---- sanity cell BEFORE the session (pre-reg control 3) ----
    sanity = sanity_cell_check()

    comp_cell = build_composition(registry, composition)
    baseline_rows = comp_cell.score_batch(Bd)  # drift baseline = initial composition
    eval0 = quick_eval(comp_cell, Bq, Mq, classes)

    header = {
        "type": "session_header", "session_id": session_id, "experiment": "PX2 gardener loop",
        "mode": mode, "pre_reg": "proposals/runs/PX2-patchwork-3x3.md (FROZEN 2026-09-30)",
        "device": device_string(ollama_enabled()), "terrain_digest_fnv1a64": meta["terrain_digest_fnv1a64"],
        "seeds": {"session": args.seed, "gardener_rng": args.seed, "immune_rng": args.seed + 1,
                  "drift_draw_rng": args.seed + 2, "split": 0, "quick_eval_draw": QUICK_EVAL_SEED,
                  "seed_choice_note": "seed 0 default; immune stream default_rng(seed+1) yields "
                                      ">=1 shadow no-op in the 10-move verification window"},
        "moves_budget": args.moves, "shadow_rate_note": "see shadow_nop_log.jsonl sidecar",
        "drift": {"n_states": DRIFT_N, "every": args.drift_every, "split": "train-only"},
        "live": None if mode != "live" else {"model": args.model, "endpoint": args.endpoint,
                                             "key_source": args.key_file,
                                             "key_handling": "runtime-only read; never echoed/logged/written",
                                             "max_consecutive_abstains": MAX_CONSECUTIVE_ABSTAINS},
        "quick_eval_source": SMOKE_JSON, "quick_eval_n": QUICK_EVAL_N,
        "quick_eval_verified_against_smoke": True,
        "initial_composition": composition, "registry_visible": visible_registry,
        "sanity_cell": {"result": "PASS", "cases": sanity},
        "d3_frozen_baseline_top1": D3_BASELINE,
        "initial_eval": eval0,
    }
    emit(header)
    print(f"initial eval: top1={eval0['top1_in_optimal']} set_recall={eval0['set_recall']} "
          f"(smoke composed arm: 0.595/0.5458)", flush=True)

    history, n_nops = [], 0  # n_nops counted for the operator summary only
    consecutive_abstains = 0
    state = {"Btr": B[tr], "Mtr": M[tr], "seed": args.seed, "create_counter": 0}
    final_eval = eval0

    for move_index in range(1, args.moves + 1):
        # -- 1. gardener proposes --
        if mode == "dry-run":
            move = generate_blind_move(gardener_rng, registry, composition, visible_registry)
        else:
            prompt = render_live_prompt(composition, registry, history, args.prompt_context)
            content, meta = live_chat_move(prompt, args.endpoint, args.model, args.key_file)
            move, abstain_reason = parse_live_move(content, registry, composition)
            attempts = [{"content_head": meta["raw_head"], "reasoning_len": meta["reasoning_len"],
                         "finish_reason": meta["finish_reason"]}]
            if move is None:
                # one same-prompt retry on unparseable — no outcome info has been seen,
                # so the re-roll is epistemically clean; both raws logged.
                content2, meta2 = live_chat_move(prompt, args.endpoint, args.model, args.key_file)
                attempts.append({"content_head": meta2["raw_head"], "reasoning_len": meta2["reasoning_len"],
                                 "finish_reason": meta2["finish_reason"]})
                move, abstain_reason = parse_live_move(content2, registry, composition)
            if move is None:
                consecutive_abstains += 1
                emit({"type": "abstain", "session_id": session_id, "move_index": move_index,
                      "reason": abstain_reason, "consecutive": consecutive_abstains,
                      "attempts": attempts})
                print(f"move {move_index}: ABSTAIN ({abstain_reason}) "
                      f"[{consecutive_abstains}/{MAX_CONSECUTIVE_ABSTAINS}] "
                      f"raw_heads={[a['content_head'][:60] for a in attempts]}", flush=True)
                if consecutive_abstains >= MAX_CONSECUTIVE_ABSTAINS:
                    receipts.close()
                    fail(f"{MAX_CONSECUTIVE_ABSTAINS} consecutive abstains — session abort, fail loud")
                continue
            consecutive_abstains = 0

        # -- 2. immune layer: seeded 5% shadow no-op (sidecar-logged ONLY) --
        shadow_draw = float(immune_rng.random())
        was_noop = shadow_draw < args.shadow_rate
        applied_move = move
        if was_noop:
            n_nops += 1
            with open(SHADOW_LOG, "a") as side:
                side.write(json.dumps({
                    "type": "shadow_noop", "session_id": session_id, "mode": mode,
                    "move_index": move_index, "rng_draw": shadow_draw,
                    "threshold": args.shadow_rate, "action": "replaced_with_noop",
                    "intended_move": move}) + "\n")
            applied_move = {"move_type": "noop", "targets": {}, "rationale": "",
                            "predicted_effect_direction": "flat"}

        # -- 3. validate + apply (fail loud on dry-run illegality; live already guarded) --
        ok, reason = validate_move(applied_move, registry, composition) \
            if applied_move["move_type"] != "noop" else (True, "shadow no-op bypasses validation")
        if not ok:
            if mode == "dry-run":
                fail(f"blind gardener produced illegal move ({reason}): {applied_move}")
            emit({"type": "illegal", "session_id": session_id, "move_index": move_index,
                  "reason": reason, "move": applied_move})
            continue
        comp_before = list(composition)
        if applied_move["move_type"] != "noop":
            composition = apply_move(applied_move, registry, composition, state)
        comp_cell = build_composition(registry, composition)

        # -- 4. eval every move on the frozen quick-eval + drift when due --
        ev = quick_eval(comp_cell, Bq, Mq, classes)
        drift = None
        if move_index % args.drift_every == 0:
            drift = drift_check(comp_cell, Bd, baseline_rows)
        final_eval = ev
        history.append({"move_index": move_index, "top1_in_optimal": ev["top1_in_optimal"],
                        "set_recall": ev["set_recall"]})

        emit({"type": "move", "session_id": session_id, "move_index": move_index,
              "gardener_move": move, "composition_before": comp_before,
              "composition_after": composition, "eval": ev,
              "drift": drift, "runtime_seconds": round(time.time() - t0, 1)})

        bs = ev["block_split"]
        print(f"move {move_index} [{move['move_type']}] top1={ev['top1_in_optimal']} "
              f"recall={ev['set_recall']} | WIN {bs['WIN'].get('top1', '-')} (n={bs['WIN']['n']}) "
              f"BLOCK {bs['BLOCK'].get('top1', '-')} (n={bs['BLOCK']['n']}) "
              f"NON_LOCAL {bs['NON_LOCAL'].get('top1', '-')} (n={bs['NON_LOCAL']['n']})"
              + (f" | drift mad={drift['mean_row_mad']} argmaxΔ={drift['argmax_change_frac']}"
                 if drift else ""), flush=True)

    emit({"type": "session_footer", "session_id": session_id,
          "moves_executed": args.moves, "final_composition": composition,
          "final_eval": final_eval, "initial_eval": eval0,
          "delta_top1": round(final_eval["top1_in_optimal"] - eval0["top1_in_optimal"], 4),
          "d3_frozen_baseline_top1": D3_BASELINE,
          "runtime_seconds": round(time.time() - t0, 1)})
    receipts.close()

    print("\n=== session complete ===", flush=True)
    print(f"final quick-eval: top1_in_optimal={final_eval['top1_in_optimal']} "
          f"set_recall={final_eval['set_recall']} (delta vs move-0: "
          f"{round(final_eval['top1_in_optimal'] - eval0['top1_in_optimal'], 4):+.4f}; "
          f"d3 frozen baseline {D3_BASELINE})", flush=True)
    print(f"final composition: {composition}", flush=True)
    print(f"receipts: {receipts_path}", flush=True)
    print(f"shadow no-ops this session: {n_nops} (details: {SHADOW_LOG})", flush=True)
    return {"final_eval": final_eval, "receipts": receipts_path, "mode": mode}


def main() -> None:
    ap = argparse.ArgumentParser(description="PX2 gardener loop (dry-run + flag-gated live)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true",
                   help="blind gardener: seeded RNG legal moves (shadow-control calibration arm)")
    g.add_argument("--live", action="store_true",
                   help="GLM-5.3 gardener over HTTP — ALSO requires env PX2_ALLOW_LIVE=1; "
                        "NOT RUN in this build")
    ap.add_argument("--moves", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--shadow-rate", type=float, default=0.05)
    ap.add_argument("--drift-every", type=int, default=10)
    ap.add_argument("--endpoint", default="https://api.z.ai/api/paas/v4/chat/completions")
    ap.add_argument("--model", default="glm-5.3")
    ap.add_argument("--key-file", default="/mnt/c/Users/casey/key.txt")
    ap.add_argument("--prompt-context", type=int, default=5,
                    help="last N eval numbers rendered into the live prompt")
    args = ap.parse_args()
    if args.moves < 1:
        fail("--moves must be >= 1")
    run_session(args)


if __name__ == "__main__":
    main()
