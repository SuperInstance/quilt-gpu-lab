#!/usr/bin/env python3
"""D15c — tone-channel GENERALIZATION: hold out whole tone classes.

D15b landed KEEP: the LoRA reads the tone channel at 0.9413 vs base 0.0781
(chance 0.25). But every D15b training trajectory sampled its momentum runs
from ALL FOUR classes (d/f/u/h) — so the adapter has seen a gold "h" (etc.)
thousands of times. D15b proves generalization to unseen TEXTS; it does not
prove the adapter learned the RULE (momentum = (timbre - data mod 4) mod 4)
versus memorizing byte-pattern -> seen-class output mappings.

D15c's falsification: train the SAME LoRA recipe on trajectories restricted
to THREE momentum classes, and gate on the class whose gold token NEVER
appears in any training example (asserted per pair). The prompt is UNCHANGED
from D15b — the public RULE names all four codes and the worked examples show
one demonstration of each (that is part of the recipe being tested). So the
question is precise: with the rule public but zero held-class training
gradients, does the adapter EXECUTE the rule for the unseen class (tuned
held-class acc >= 0.80), or can it only replay seen-class patterns (score
~ chance or the seen classes only)?

  - TRAIN: identical curriculum (A=12-char, B=24-char, C=full; ep1=A,
    ep2=A+B, ep3-5=all; 150 pairs/stage), but `make_tone` samples runs from
    the 3-class seen palette only. Every train pair asserts the held-out
    momentum is absent — the holdout is structural, not filtered.
  - EVAL (both full-length, both on UNSEEN texts, same prompt both arms):
      gate set   = 60 pairs, trajectories from ALL FOUR classes (D15b's
                   exact distribution). GATE METRIC = per-token accuracy
                   POOLED over positions whose gold is the held-out class.
      seen set   = 40 pairs, trajectories from the 3 seen classes only.
                   Replication axis: should look D15b-like (~0.9) if the
                   restricted training didn't break the read itself; separates
                   "can't read at all" from "reads but can't emit the unseen
                   code" in the INCONCLUSIVE case.
  - Also reported: full per-class accuracy table (both arms, gate set) and
    the held-code emission rate (does the model EVER output the held code).

Pre-registered gate (FULL runs only), pooled over held-out positions of the
gate set: KEEP iff tuned >= 0.80 AND base <= 0.30; KILL iff tuned <= base;
else INCONCLUSIVE. fp16/fp32 quant fallback forces INCONCLUSIVE (4-bit is
part of the protocol). SMOKE runs are pipeline proofs: INCONCLUSIVE
regardless of numbers. Same convention as D15/D15b — do not drift.

SMOKE (default, D15C_FULL unset): Qwen2.5-0.5B, 4 short + 4 full train pairs
(2 optimizer steps), 10 gate + 6 seen eval pairs.
FULL (D15C_FULL=1): base chain Qwen2.5-3B 4-bit NF4 (VRAM-headroom fallback
to 1.5B, same as D15b), LoRA r=16 alpha=32 on q/k/v/o/gate/up/down, grad
checkpointing (use_reentrant=False), batch 1 x grad-accum 8, seq <= 1024,
lr 2e-4 AdamW, 5 curriculum epochs over 450 pairs, eval on 60 gate + 40 seen
pairs. ~2.5-3.5 h wall on the RTX 4050 6 GB (same envelope as D15b full).
NOTE for the scheduler: runner.py's Guard hard-codes timeout_s=1800 and D15b
full took 5168 s — run D15c full with an adequate timeout or standalone with
D15C_LEDGER=1.

Env knobs: D15C_FULL=1 (full scale), D15C_MODEL (override base chain),
D15C_SEED (default 2718), D15C_HOLDOUT in {down,flat,up,hold} (default
"hold"; one fold per run — other folds are future passes), D15C_LEDGER=1.
"""
from __future__ import annotations

import datetime
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from guard import FREE_FLOOR_MIB, TEMP_CEIL_C, sample  # noqa: E402

QTHE = Path.home() / "projects" / "qthe-codec"
sys.path.insert(0, str(QTHE))
from qthe_codec import (MOMENTUM, data_encode, decode_bytes, encode,  # noqa: E402
                        latin_decode)

RESULTS_JSON = LAB / "results" / "d15c_eval.json"
RESULTS_MD = LAB / "RESULTS.md"

SEED = 2718
SMOKE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
FULL_CANDIDATES = ["Qwen/Qwen2.5-3B-Instruct",   # try first: fits 6 GB at 4-bit?
                   "Qwen/Qwen2.5-1.5B-Instruct"]  # D15's base, the known-good floor
HEADROOM_FLOOR_MIB = 1500  # free VRAM required AFTER 4-bit load to attempt training
LORA_R, LORA_ALPHA, LORA_DROPOUT = 16, 32, 0.05
GRAD_ACCUM = 8             # batch 1 x accum 8 = eff batch 8 (D15/D15b recipe)
MAX_SEQ = 1024
LR = 2e-4
MAX_BYTES = 64
NEW_TOKEN_CAP = 160
SMOKE_HELDOUT = 10
STAGE_PAIRS = 150          # full mode: 150 pairs per curriculum stage (450 total)
SMOKE_STAGE_PAIRS = 4      # smoke: 4 short + 4 full = 8 train pairs
TRUNC_A, TRUNC_B = 12, 24  # curriculum stage text truncations (chars)
FULL_GATE_PAIRS_PER_TEXT = 3   # 20 unseen texts x 3 draws = 60 (D15b gate size)
FULL_SEEN_PAIRS_PER_TEXT = 2   # 20 unseen texts x 2 draws = 40 (replication axis)
HELD_POSITION_FLOOR = 150    # full-mode gate set must contain >= this many
                             # held-out-class positions or the metric is too thin
CLAIM_TUNED = 0.80         # pre-registered, pooled over held-out positions
CLAIM_BASE = 0.30          # pre-registered (chance 0.25); unchanged from D15

# momentum state -> output code (compact, tokenizer-friendly)
CODE = {MOMENTUM["down"]: "d", MOMENTUM["flat"]: "f",
        MOMENTUM["up"]: "u", MOMENTUM["hold"]: "h"}
CODE_OF_TOKEN = {"d": MOMENTUM["down"], "f": MOMENTUM["flat"],
                 "u": MOMENTUM["up"], "h": MOMENTUM["hold"]}
WORD_OF_TOKEN = {"down": MOMENTUM["down"], "flat": MOMENTUM["flat"],
                 "up": MOMENTUM["up"], "hold": MOMENTUM["hold"]}
LEGEND = "d=down, f=flat, u=up, h=hold"

# --- held-out tone class (the falsification target) -----------------------
HELDOUT_NAME = os.environ.get("D15C_HOLDOUT", "hold").strip().lower()
if HELDOUT_NAME not in MOMENTUM:
    raise SystemExit(f"D15C_HOLDOUT must be one of {sorted(MOMENTUM)}; "
                     f"got {HELDOUT_NAME!r}")
HELD_MOM = MOMENTUM[HELDOUT_NAME]
HELD_CODE = CODE[HELD_MOM]
SEEN_PALETTE = [m for m in CODE if m != HELD_MOM]  # training trajectory classes

# --- worked examples: IDENTICAL to D15b — all four timbres AND all four
# momenta, asserted against latin_decode at startup. Intentional: the prompt
# is part of the D15b recipe under test; what's held out is every gold
# demonstration of the held class in TRAINING gradients.
WORKED_BYTES = [0x86, 0xCA, 0x47, 0x05]  # -> d, f, u, h (asserted)

# --- text pool: IDENTICAL to D15 (same 45 lines) for run-to-run continuity.
TEXTS = [
    "the hull sings and the quilt holds its breath.",
    "watch log: rigging taut, signal clean.",
    "the quartermaster tallies salt and wire.",
    "engines idling, antenna wet.",
    "the sonar pings once and the deep answers slow.",
    "steady as she goes; the ledger keeps its own columns.",
    "night watch: cold coffee, warm valves.",
    "transmission open, channel quiet.",
    "the canary hash anchors every offset.",
    "cells are scars, not parameters.",
    "the witness log is the prediction.",
    "the substrate is grown, not designed.",
    "the oracle is heard, not stored.",
    "lenia flows where conway stands still.",
    "thirteen ports, byte-exact.",
    "the tone rides in the top two bits.",
    "a latin square keeps the marginals uniform.",
    "plaintext readers see nothing at all.",
    "momentum is a trajectory, not a label.",
    "the context key lives in the data plane.",
    "hold space, then lean toward the mark.",
    "the signal leans away and the log notes it.",
    "abstain is information: the imagined channel.",
    "rising toward the middle, then flat.",
    "dread climbs in the second half of the line.",
    "the sentence reads flat but lands heavy.",
    "same words, different weather.",
    "the exoj logic reads the path, not the prose.",
    "reflexes fire on tone, not on text.",
    "come here, spoken rising, means approach.",
    "come here, spoken falling, means hesitate.",
    "the pincher graph weights its edges by tone.",
    "french and english meet in the timbre plane.",
    "one adapter, many tongues, one temperature.",
    "the story rides the data plane; the affect rides the tone.",
    "cold front moving in from the northwest.",
    "The Canary Hash 0xcbf2 holds.",
    "JEV says JEV is barely useful at substrate.",
    "salt, wire, and $perl threads.",
    "the quilt remembers every stitch.",
    "rumor says the deep is listening back.",
    "the fabric interconnects; the languages braid.",
    "a held breath is a kind of answer.",
    "the relay repeats what the hull cannot say.",
]
HELD_TEXTS_FULL = 20  # unseen texts (same split discipline as D15/D15b)

# curriculum: epoch -> list of stages to train on (short trajectories first)
SCHEDULE = {
    "smoke": [["A"], ["A", "C"]],
    "full": [["A"], ["A", "B"], ["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"]],
}


def make_tone(rng: random.Random, n: int,
              palette: list[int] | None = None) -> list[int]:
    """A seeded momentum TRAJECTORY: 2-k runs of pairwise-distinct momenta,
    run lengths 1-4, proportionally scaled to n tokens. Identical to D15b
    except `palette` restricts the class vocabulary: D15c TRAIN trajectories
    use the 3-class seen palette (holdout is structural, not filtered)."""
    pool = list(palette) if palette else list(CODE.keys())
    moms = rng.sample(pool, rng.randint(2, len(pool)))
    lens = [rng.randint(1, 4) for _ in moms]
    total = sum(lens)
    out: list[int] = []
    for m, ln in zip(moms, lens):
        out += [m] * max(1, round(ln * n / total))
    out = out[:n]
    while len(out) < n:
        prev = out[-1] if out else None
        choices = [m for m in pool if m != prev] if prev is not None else pool
        out.append(rng.choice(choices))
    return out


def make_pair(rng: random.Random, text: str, tag: str,
              palette: list[int] | None = None) -> dict:
    """(text, tone) -> QTHE byte-stream example, with codec roundtrip proof.
    palette=None -> all four classes (D15b distribution); a 3-class palette
    gives a seen-only trajectory. Train pairs additionally assert the held
    class is absent."""
    data = data_encode(text)
    tone = make_tone(rng, len(data), palette)
    if palette is not None:  # train / seen-eval discipline, enforced per pair
        assert HELD_MOM not in tone, f"held class leaked into restricted pair {tag}"
    stream = encode(text, tone)
    back_text, back_mom = decode_bytes(stream)
    assert back_text == text, f"codec text roundtrip failed on {tag}"
    assert back_mom == tone, f"codec momentum roundtrip failed on {tag}"
    assert len(stream) <= MAX_BYTES, f"stream too long ({len(stream)}) on {tag}"
    return {
        "id": tag,
        "text": text,
        "tone": tone,
        "stream": stream,
        "hex": " ".join(f"{b:02x}" for b in stream),
        "gold": tone,
        "gold_str": " ".join(CODE[m] for m in tone),
    }


def make_stage_pair(rng: random.Random, text: str, trunc: int | None, tag: str) -> dict:
    """Curriculum pair: truncate the TEXT before encoding, so the stream is
    genuinely short but still a codec-exact (text, tone) pair. Always on the
    seen palette."""
    t = text if trunc is None else text[:trunc]
    return make_pair(rng, t, tag, palette=SEEN_PALETTE)


def build_train_stages(rng: random.Random, train_texts: list[str],
                       mode: str) -> dict[str, list[dict]]:
    n_stage = SMOKE_STAGE_PAIRS if mode == "smoke" else STAGE_PAIRS
    spec = ([("A", TRUNC_A), ("C", None)] if mode == "smoke"
            else [("A", TRUNC_A), ("B", TRUNC_B), ("C", None)])
    stages: dict[str, list[dict]] = {}
    for name, trunc in spec:
        pairs: list[dict] = []
        k = 0
        while len(pairs) < n_stage:
            t = train_texts[k % len(train_texts)]
            pairs.append(make_stage_pair(rng, t, trunc, f"train{name}-{t[:10]}-{k}"))
            k += 1
        rng.shuffle(pairs)
        stages[name] = pairs
    return stages


def build_eval(rng: random.Random, held_texts: list[str],
               mode: str) -> tuple[list[dict], list[dict]]:
    """Both eval sets are FULL-LENGTH on unseen texts, same prompt as D15b.
    gate set: ALL-FOUR-class trajectories (D15b's exact distribution) — held-
    out-class positions are the pre-registered gate metric. seen set: 3-class
    trajectories — replication axis (is the read itself intact?)."""
    gate_draws = FULL_GATE_PAIRS_PER_TEXT if mode == "full" else 1
    seen_draws = FULL_SEEN_PAIRS_PER_TEXT if mode == "full" else 1
    if mode == "full":
        n_gate, n_seen = len(held_texts), len(held_texts)
    else:  # smoke: prove every code path, kept small
        n_gate, n_seen = SMOKE_HELDOUT, 6
    gate: list[dict] = []
    for t in held_texts[:n_gate]:
        for k in range(gate_draws):
            gate.append(make_pair(rng, t, f"gate-{t[:12]}-{k}"))
    seen: list[dict] = []
    for t in held_texts[:n_seen]:
        for k in range(seen_draws):
            seen.append(make_pair(rng, t, f"seen-{t[:12]}-{k}", palette=SEEN_PALETTE))
    # the gate metric must have something to measure
    n_held_pos = sum(1 for ex in gate for m in ex["gold"] if m == HELD_MOM)
    if mode == "full":
        assert n_held_pos >= HELD_POSITION_FLOOR, \
            f"gate set too thin: {n_held_pos} held positions < {HELD_POSITION_FLOOR}"
    else:
        assert n_held_pos >= 1, "smoke gate set has no held positions"
    return gate, seen


def build_corpus(rng: random.Random, mode: str) -> tuple[dict, list[dict], list[dict], dict]:
    """Seeded corpus, split BY TEXT (D15b discipline) + BY CLASS (D15c)."""
    texts = list(TEXTS)
    rng.shuffle(texts)
    n_held_texts = HELD_TEXTS_FULL if mode == "full" else SMOKE_HELDOUT
    held_texts, train_texts = texts[:n_held_texts], texts[n_held_texts:]
    stages = build_train_stages(rng, train_texts, mode)
    gate, seen = build_eval(rng, held_texts, mode)
    stats = {"pool_texts": len(TEXTS), "held_texts": len(held_texts),
             "train_texts": len(train_texts),
             "stage_sizes": {k: len(v) for k, v in stages.items()},
             "trunc_a_chars": TRUNC_A, "trunc_b_chars": TRUNC_B}
    return stages, gate, seen, stats


def target_modules() -> list[str]:
    # Qwen2 attention + MLP projections (D4-proven adapter spec)
    return ["q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"]


def worked_examples_block() -> str:
    """Four fully-worked single-byte decodings, generated FROM the codec and
    asserted against latin_decode in main() — prompt can't drift from math.
    Identical to D15b: all four classes appear, INCLUDING the held-out one
    (the rule is public; the training gradients are not)."""
    lines = []
    for b in WORKED_BYTES:
        t, d = b >> 6, b & 0x3F
        m = (t - (d % 4)) % 4
        lines.append(
            f"byte {b:02x}: {b:#04x} = {b}. timbre = {b} >> 6 = {t}. "
            f"data = {b} & 63 = {d}. data mod 4 = {d % 4}. "
            f"momentum = ({t} - {d % 4}) mod 4 = {m} -> {CODE[m]}.")
    return "\n".join(lines)


SYSTEM = ("You are the QTHE channel reader. You recover the hidden momentum "
          "trajectory from QTHE byte streams. Answer with space-separated "
          f"codes only: {LEGEND}.")
RULE = ("RULE: for each byte in order, momentum = (timbre - (data mod 4)) "
        "mod 4, with 0=d, 1=f, 2=u, 3=h. Output one code per byte, in stream "
        "order, space-separated.")
WORKED = worked_examples_block()


def user_content(hex_stream: str) -> str:
    return (f"QTHE BYTE STREAM (hex):\n{hex_stream}\n\n"
            f"WORKED EXAMPLES (reading one byte):\n{WORKED}\n\n{RULE}")


def build_prompt(tok, hex_stream: str) -> str:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content(hex_stream)}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False,
                                       add_generation_prompt=True)
    except Exception:
        return f"System: {SYSTEM}\n\nUser: {user_content(hex_stream)}\n\nAnswer:"


def full_text(tok, ex: dict) -> str:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_content(ex["hex"])},
            {"role": "assistant", "content": ex["gold_str"]}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False)
    except Exception:
        return build_prompt(tok, ex["hex"]) + ex["gold_str"]


def encode_example(tok, ex: dict) -> dict:
    prompt = build_prompt(tok, ex["hex"])
    full = full_text(tok, ex)
    plen = len(tok(prompt, add_special_tokens=False).input_ids)
    ids = tok(full, truncation=True, max_length=MAX_SEQ,
              add_special_tokens=False).input_ids
    labels = list(ids)
    for i in range(min(plen, len(labels))):
        labels[i] = -100  # loss only on the gold trajectory tokens
    return {"input_ids": ids, "labels": labels}


def load_base(model_id: str, dev: str) -> tuple[object, object, str, str]:
    """Returns (tokenizer, model, quant_mode, quant_note). Falls back fp16."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    if dev != "cuda":
        return tok, AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float32).to(dev), \
            "fp32-cpu", "no CUDA available; loaded fp32 on CPU"
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True)
    try:
        model = _from_pretrained(AutoModelForCausalLM, model_id, quantization_config=bnb,
                                 device_map={"": 0})
        return tok, model, "nf4-4bit", "4-bit NF4 double-quant, bf16 compute"
    except Exception as e:
        note = f"4-bit load FAILED ({type(e).__name__}: {str(e)[:160]}); fell back to fp16 — SAY SO"
        model = _from_pretrained(AutoModelForCausalLM, model_id, dtype=torch.float16,
                                 device_map={"": 0})
        return tok, model, "fp16-fallback", note


def _from_pretrained(cls, model_id: str, **kw):
    try:
        return cls.from_pretrained(model_id, **kw)
    except TypeError:  # older/newer kwarg naming (dtype vs torch_dtype)
        if "dtype" in kw:
            kw["torch_dtype"] = kw.pop("dtype")
        return cls.from_pretrained(model_id, **kw)


def load_candidate_chain(dev: str) -> tuple[object, object, str, str, str, list, str | None]:
    """Bigger-base chain (D15b-identical): try 3B in 4-bit; on load failure,
    non-NF4 outcome, or post-load free VRAM < HEADROOM_FLOOR_MIB, free and
    fall back to 1.5B."""
    env_model = os.environ.get("D15C_MODEL")
    mode = "full" if os.environ.get("D15C_FULL") == "1" else "smoke"
    candidates = [env_model] if env_model else \
        (FULL_CANDIDATES if mode == "full" else [SMOKE_MODEL])
    tried: list[dict] = []
    fallback: str | None = None
    for idx, mid in enumerate(candidates):
        try:
            tok, model, quant, note = load_base(mid, dev)
        except Exception as e:
            tried.append({"model": mid, "ok": False,
                          "why": f"{type(e).__name__}: {str(e)[:140]}"})
            if idx == len(candidates) - 1:
                raise
            fallback = f"{mid} failed to load; fell back"
            continue
        free_after = (torch.cuda.mem_get_info()[0] // 2**20) if dev == "cuda" else None
        headroom_ok = free_after is None or free_after >= HEADROOM_FLOOR_MIB
        if quant == "nf4-4bit" and headroom_ok:
            return tok, model, quant, note, mid, tried, fallback
        tried.append({"model": mid, "ok": True, "quant": quant,
                      "free_after_load_mib": free_after,
                      "why": (f"quant={quant}" + ("" if headroom_ok else
                              f" or free_after={free_after} MiB < {HEADROOM_FLOOR_MIB}"))})
        if idx == len(candidates) - 1:
            return tok, model, quant, note, mid, tried, \
                f"last candidate accepted despite quant={quant}/headroom={free_after}"
        fallback = (f"{mid}: quant={quant}"
                    + (f", free_after={free_after} MiB < {HEADROOM_FLOOR_MIB}"
                       if free_after is not None else "")
                    + " — fell back to next candidate")
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()
    raise RuntimeError("candidate chain exhausted")  # unreachable


def parse_codes(text: str) -> list[int]:
    """Whitespace tokens must be exactly one code char or one full word;
    partial/garbage words are ignored (honest to both arms, symmetric)."""
    out: list[int] = []
    for t in text.lower().split():
        if t in CODE_OF_TOKEN:
            out.append(CODE_OF_TOKEN[t])
        elif t in WORD_OF_TOKEN:
            out.append(WORD_OF_TOKEN[t])
    return out


def score(pred: list[int], gold: list[int]) -> tuple[float, int]:
    """Per-token accuracy over the gold trajectory (missing = wrong),
    plus exact-match of the whole trajectory."""
    hit = sum(1 for i in range(len(gold))
              if i < len(pred) and pred[i] == gold[i])
    return hit / len(gold), int(pred == gold)


def evaluate(tok, model, examples: list[dict], keep_samples: int = 4) -> dict:
    """Batch-1 greedy generation; short/misaligned outputs count wrong.
    D15c adds: pooled held-out-class position accuracy (the gate metric),
    per-class accuracy table, and held-code emission rate (both arms)."""
    model.eval()
    was_cache = getattr(model.config, "use_cache", True)
    model.config.use_cache = True
    accs: list[float] = []
    exact = 0
    wellformed = 0
    held_hits = 0
    held_total = 0
    class_hits = {m: 0 for m in CODE}
    class_total = {m: 0 for m in CODE}
    pred_tokens = 0
    pred_held = 0
    gold_tokens = 0
    gold_held = 0
    samples: list[dict] = []
    t0 = time.time()
    for ex in examples:
        prompt = build_prompt(tok, ex["hex"])
        ids = tok(prompt, return_tensors="pt", truncation=True,
                  max_length=MAX_SEQ).to(model.device)
        cap = min(2 * len(ex["stream"]) + 8, NEW_TOKEN_CAP)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=cap,
                                 do_sample=False, pad_token_id=tok.pad_token_id)
        text = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
        pred = parse_codes(text)
        gold = ex["gold"]
        a, x = score(pred, gold)
        accs.append(a)
        exact += x
        wellformed += int(len(pred) == len(gold))
        for i, g in enumerate(gold):
            class_total[g] += 1
            gold_tokens += 1
            if g == HELD_MOM:
                gold_held += 1
            p_ok = i < len(pred) and pred[i] == g
            if p_ok:
                class_hits[g] += 1
            if g == HELD_MOM:
                held_total += 1
                if p_ok:
                    held_hits += 1
        pred_tokens += len(pred)
        pred_held += sum(1 for p in pred if p == HELD_MOM)
        if len(samples) < keep_samples and HELD_MOM in gold:
            samples.append({"id": ex["id"], "gold": ex["gold_str"],
                            "pred": " ".join(CODE[p] for p in pred[:len(gold)]),
                            "raw": text[:120], "acc": round(a, 3)})
    model.config.use_cache = was_cache
    n = len(examples)
    return {
        "n": n,
        "acc": round(sum(accs) / n, 4) if n else None,
        "exact_match": round(exact / n, 4) if n else None,
        "wellformed_rate": round(wellformed / n, 4) if n else None,
        "mean_stream_bytes": round(sum(len(e["stream"]) for e in examples)
                                   / max(1, n), 1),
        "held_class_acc": round(held_hits / held_total, 4) if held_total else None,
        "held_class_positions": held_total,
        "held_code_rate_gold": round(gold_held / gold_tokens, 4) if gold_tokens else None,
        "held_code_rate_pred": round(pred_held / pred_tokens, 4) if pred_tokens else None,
        "per_class_acc": {CODE[m]: {"acc": (round(class_hits[m] / class_total[m], 4)
                                            if class_total[m] else None),
                                    "n": class_total[m]}
                          for m in CODE},
        "seconds": round(time.time() - t0, 1),
        "samples": samples,
    }


def train_epochs(tok, model, schedule: list[list[str]], stages: dict[str, list[dict]],
                 grad_accum: int) -> dict:
    """Real curriculum training (D15b-identical): per epoch, concatenate the
    scheduled stages, steps = round(pairs/accum) so '5 epochs' means 5 real
    passes. Same LoRA attach, batch-1 + grad-accum, clip-1.0 AdamW loop."""
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                            gradient_checkpointing_kwargs={"use_reentrant": False})
    lora = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
                      bias="none", task_type=TaskType.CAUSAL_LM,
                      target_modules=target_modules())
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    used = sorted({name for names in schedule for name in names})
    enc = {name: [encode_example(tok, ex) for ex in stages[name]] for name in used}
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=LR)
    per_epoch: list[dict] = []
    total_steps = 0
    t0 = time.time()
    model.train()
    model.config.use_cache = False
    for ei, names in enumerate(schedule):
        pool = [ex for n in names for ex in enc[n]]
        steps = max(1, round(len(pool) / grad_accum))
        losses: list[float] = []
        for step in range(steps):
            opt.zero_grad(set_to_none=True)
            run_loss = 0.0
            for i in range(grad_accum):  # batch 1, grad-accum
                ex = pool[(step * grad_accum + i) % len(pool)]
                ids = torch.tensor([ex["input_ids"]], device=model.device)
                lab = torch.tensor([ex["labels"]], device=model.device)
                loss = model(input_ids=ids, labels=lab).loss / grad_accum
                loss.backward()
                run_loss += float(loss.detach())
            torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1.0)
            opt.step()
            losses.append(round(run_loss, 4))
        total_steps += steps
        per_epoch.append({"epoch": ei + 1, "stages": names, "pairs": len(pool),
                          "steps": steps,
                          "mean_loss": round(sum(losses) / len(losses), 4),
                          "losses": losses})
    return {"model": model, "trainable_params": trainable,
            "optimizer_steps_total": total_steps, "per_epoch": per_epoch,
            "seconds": round(time.time() - t0, 1)}


def preflight() -> tuple[bool, str | None, tuple[int, int] | None]:
    free, temp = sample()
    if free is None:
        return False, "preflight: nvidia-smi unavailable", None
    if free < FREE_FLOOR_MIB:
        return False, f"preflight: free VRAM {free} MiB < {FREE_FLOOR_MIB}", (free, temp)
    if temp is not None and temp > TEMP_CEIL_C:
        return False, f"preflight: temp {temp} C > {TEMP_CEIL_C}", (free, temp)
    return True, None, (free, temp)


def versions() -> dict:
    import bitsandbytes
    import peft
    import transformers
    return {"torch": torch.__version__, "transformers": transformers.__version__,
            "peft": peft.__version__, "bitsandbytes": bitsandbytes.__version__}


def main() -> dict:
    t_start = time.time()
    mode = "full" if os.environ.get("D15C_FULL") == "1" else "smoke"
    seed = int(os.environ.get("D15C_SEED", str(SEED)))
    rng = random.Random(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    # worked examples must agree with the codec, or the prompt is a lie
    assert [CODE[latin_decode(b >> 6, (b & 0x3F) % 4)] for b in WORKED_BYTES] \
        == ["d", "f", "u", "h"], "worked examples disagree with latin_decode"
    # split discipline: the held-out class must be OUT of training entirely
    assert HELD_MOM not in SEEN_PALETTE and len(SEEN_PALETTE) == 3
    assert HELD_MOM in {latin_decode(b >> 6, (b & 0x3F) % 4) for b in WORKED_BYTES}, \
        "sanity: held class must be reachable by the rule (it is public in the prompt)"

    ok, breach, gv = preflight()
    if not ok:
        return _finish({"experiment": "D15c tone-channel generalization", "mode": mode,
                        "device": dev, "seed": seed, "verdict": "ABORTED",
                        "reason": breach,
                        "guard": {"free_mib": gv[0], "temp_c": gv[1]}}, mode)

    stages, gate_ex, seen_ex, cstats = build_corpus(rng, mode)
    schedule = SCHEDULE[mode]

    tok, base, quant_mode, quant_note, model_used, tried, fallback_note = \
        load_candidate_chain(dev)
    base_gate = evaluate(tok, base, gate_ex)
    base_seen = evaluate(tok, base, seen_ex) if seen_ex else None

    t_out = train_epochs(tok, base, schedule, stages, GRAD_ACCUM)
    tuned = t_out.pop("model")
    tuned_gate = evaluate(tok, tuned, gate_ex)
    tuned_seen = evaluate(tok, tuned, seen_ex) if seen_ex else None
    adapter_dir = LAB / "results" / (f"d15c_adapter_full_{HELDOUT_NAME}" if mode == "full"
                                     else f"d15c_adapter_smoke_{HELDOUT_NAME}")
    try:
        tuned.save_pretrained(str(adapter_dir))
        adapter_path = str(adapter_dir)
    except Exception as e:
        adapter_path = f"save failed: {type(e).__name__}: {str(e)[:80]}"
    if dev == "cuda":
        torch.cuda.empty_cache()

    tuned_held = tuned_gate["held_class_acc"]
    base_held = base_gate["held_class_acc"]
    margin_held = round((tuned_held or 0.0) - (base_held or 0.0), 4)
    if mode == "smoke":
        verdict = "INCONCLUSIVE"
        reason = (f"smoke pass: pipeline proof only ({t_out['optimizer_steps_total']} steps, "
                  f"{sum(len(v) for v in stages.values())} train pairs, "
                  f"{len(gate_ex)} gate + {len(seen_ex)} seen eval pairs); "
                  f"the gate (tuned>={CLAIM_TUNED}, base<={CLAIM_BASE} on held positions) "
                  "is full-scale")
    elif quant_mode.startswith("fp16-fallback") or quant_mode == "fp32-cpu":
        verdict = "INCONCLUSIVE"
        reason = f"precision gate not met: {quant_note}"
    elif tuned_held >= CLAIM_TUNED and base_held <= CLAIM_BASE:
        verdict = "KEEP"
        reason = (f"tuned reads the NEVER-TRAINED class {HELDOUT_NAME}({HELD_CODE}) at "
                  f"{tuned_held} (>= {CLAIM_TUNED}) vs base {base_held} (<= {CLAIM_BASE}), "
                  f"pooled over {base_gate['held_class_positions']} held positions; every "
                  f"training gold trajectory asserted free of {HELD_CODE}, so emitting it "
                  "correctly requires executing the public rule, not replaying seen-class "
                  "patterns — the adapter GENERALIZES across tone classes")
    elif tuned_held <= base_held:
        verdict = "KILL"
        reason = (f"tuned fails to beat base on the held-out class ({margin_held:+.4f}): "
                  f"the 0.94 read does not transfer to classes absent from training "
                  f"gradients — the adapter memorizes seen-class output patterns rather "
                  "than executing the rule")
    else:
        triage = ("reads seen classes but cannot emit the held-out code — rule not "
                  "internalized, seen-class patterns replayed"
                  if tuned_seen and tuned_seen["acc"] >= 0.6
                  else "the 3-class restriction degraded the read itself (seen-set acc "
                       f"{tuned_seen['acc'] if tuned_seen else None}), so the held-class "
                       "miss is a training failure, not (only) a generalization failure")
        reason = (f"tuned beats base on held positions ({margin_held:+.4f}) but misses the "
                  f"pre-registered gate: tuned {tuned_held} vs {CLAIM_TUNED} / base "
                  f"{base_held} vs {CLAIM_BASE}. Triage: {triage}")

    out = {
        "experiment": "D15c tone-channel generalization (held-out tone classes)",
        "vision_layer": "Layer 3 reading gate (text-model proxy; follows D15b KEEP)",
        "changes_vs_d15b": [
            f"tone-class holdout: training trajectories sampled from 3 classes only "
            f"({', '.join(CODE[m] for m in SEEN_PALETTE)}); gold '{HELD_CODE}' "
            f"({HELDOUT_NAME}) absent from every train pair (asserted per pair)",
            "gate metric re-anchored: pooled per-token accuracy over held-out-class "
            "positions of the all-four-class gate set (tuned>=0.80 AND base<=0.30)",
            "gate set keeps D15b's exact all-four-class trajectory distribution on "
            "unseen texts, so held-position accuracy isolates class transfer",
            "added seen-only eval set (3-class trajectories, unseen texts): replication "
            "axis separating 'read broken by restricted training' from 'read intact but "
            "cannot emit the unseen code'",
            "per-class accuracy table + held-code emission rate reported for both arms",
            "prompt UNCHANGED from D15b (rule + worked examples are public, including "
            "one held-class demonstration — part of the recipe under test)",
        ],
        "mode": mode,
        "device": dev,
        "seed": seed,
        "holdout": {"name": HELDOUT_NAME, "momentum": HELD_MOM, "code": HELD_CODE,
                    "seen_classes": [CODE[m] for m in SEEN_PALETTE],
                    "rule_visibility": ("public: RULE names all four codes and WORKED "
                                        "EXAMPLES show one demonstration of each; what is "
                                        "held out is every gold demonstration of "
                                        f"'{HELD_CODE}' in training gradients")},
        "model_used": model_used,
        "model_candidates_tried": tried,
        "fallback_note": fallback_note,
        "quant": quant_mode,
        "quant_note": quant_note,
        "qlora": {"r": LORA_R, "alpha": LORA_ALPHA, "dropout": LORA_DROPOUT,
                  "target_modules": target_modules(),
                  "grad_checkpointing": True, "batch": 1, "grad_accum": GRAD_ACCUM,
                  "seq_max": MAX_SEQ, "lr": LR},
        "curriculum": {"schedule": schedule,
                       "stage_truncs": {"A": TRUNC_A, "B": TRUNC_B, "C": None},
                       "worked_example_bytes": {f"{b:02x}": CODE[latin_decode(b >> 6, (b & 0x3F) % 4)]
                                                for b in WORKED_BYTES}},
        "data": {"source": "qthe_codec.encode() seeded foundry (~/projects/qthe-codec)",
                 "split": ("BY TEXT (held-out texts never in training) + BY CLASS "
                           f"(held-out class '{HELD_CODE}' never in any training gold "
                           "trajectory; asserted per pair)"),
                 **cstats,
                 "train_pairs": sum(len(v) for v in stages.values()),
                 "gate_pairs_all4classes": len(gate_ex),
                 "seen_pairs_3classes": len(seen_ex),
                 "held_positions_in_gate_set": base_gate["held_class_positions"],
                 "codec_roundtrip": "asserted on every pair"},
        "base_eval_gate": base_gate,
        "base_eval_seen": base_seen,
        "tuned_eval_gate": tuned_gate,
        "tuned_eval_seen": tuned_seen,
        "held_class_margin": margin_held,
        "preregistered": {"tuned_held_acc_gte": CLAIM_TUNED,
                          "base_held_acc_lte": CLAIM_BASE,
                          "metric": "pooled per-token accuracy over held-out-class "
                                    "positions of the gate set",
                          "chance": 0.25},
        "train": {"optimizer_steps_total": t_out["optimizer_steps_total"],
                  "per_epoch": t_out["per_epoch"],
                  "trainable_params": t_out["trainable_params"],
                  "seconds": t_out["seconds"]},
        "adapter_path": adapter_path,
        "peak_vram_mib": (round(torch.cuda.max_memory_allocated() / 2**20, 1)
                          if dev == "cuda" else None),
        "wall_seconds": round(time.time() - t_start, 1),
        "versions": versions(),
        "verdict": verdict,
        "reason": reason,
        "note": (
            "SMOKE numbers are pipeline proof on the 0.5B proxy, not the hypothesis test. "
            f"FULL-SCALE RECIPE (D15C_FULL=1, D15C_HOLDOUT={HELDOUT_NAME}): base chain "
            "Qwen2.5-3B -> 1.5B (4-bit NF4 double-quant; 3B kept only if free VRAM after "
            f"load >= {HEADROOM_FLOOR_MIB} MiB); LoRA r={LORA_R} alpha={LORA_ALPHA} "
            f"dropout={LORA_DROPOUT} on q/k/v/o/gate/up/down; grad checkpointing "
            f"(use_reentrant=False); batch 1 x grad-accum {GRAD_ACCUM}; seq<=1024; lr 2e-4 "
            "AdamW; 5 curriculum epochs over 450 seen-class-only pairs (A=12-char, "
            "B=24-char, C=full, 150 each): ep1=A, ep2=A+B, ep3-5=all; eval on 60 "
            "all-four-class gate pairs (20 unseen texts x 3 draws; held-class positions "
            "are the gate) + 40 seen-class pairs (replication axis). "
            f"Gate: tuned held-class acc >= {CLAIM_TUNED} AND base <= {CLAIM_BASE} "
            "(chance 0.25), pooled over held positions; KILL iff tuned <= base; else "
            "INCONCLUSIVE — same convention as D15/D15b. Prompt identical to D15b for "
            "BOTH arms (public rule + 4 worked examples), so the ONLY difference from "
            "D15b is the absence of held-class training gradients. Expected VRAM ~4-4.5 "
            "GB peak on 3B, ~2.5-3.5 h wall on the RTX 4050 6 GB; runner.py's Guard "
            "hard-codes 1800 s — D15b full needed 5168 s, so schedule accordingly. "
            "Other lanes contend: preflight floor 1024 MiB free / 80 C. This pass quant: "
            + quant_mode + "."
        ),
    }
    return _finish(out, mode)


def _finish(out: dict, mode: str) -> dict:
    RESULTS_JSON.parent.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(out, indent=2) + "\n")
    if os.environ.get("D15C_LEDGER") == "1":
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with RESULTS_MD.open("a") as f:
            f.write(f"\n## D15c — tone-channel generalization, holdout={HELDOUT_NAME} "
                    f"({out['mode']} pass)\n"
                    f"- ran: {ts}\n- verdict: **{out['verdict']}**\n"
                    f"- result: ```json\n{json.dumps(out, indent=2)}\n```\n"
                    f"- note: {out['reason']}\n")
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc().strip().splitlines()
        _finish({"experiment": "D15c tone-channel generalization",
                 "mode": "full" if os.environ.get("D15C_FULL") == "1" else "smoke",
                 "device": "cuda" if torch.cuda.is_available() else "cpu",
                 "seed": SEED, "verdict": "ABORTED",
                 "reason": f"{err[-1]} | {err[-2] if len(err) > 1 else ''}"[:400]},
                "smoke")
