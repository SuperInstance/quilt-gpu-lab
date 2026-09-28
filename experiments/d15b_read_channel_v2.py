#!/usr/bin/env python3
"""D15b — read-the-channel v2: attack the 0.35 -> 0.80 gap D15 left on the table.

D15 (full-scale) landed INCONCLUSIVE: tuned 0.3509 vs base 0.2658, gate 0.80/0.30.
The LoRA learned the FORMAT (emit d/f/u/h codes, well above chance) but not the
channel READ. D15b changes four things, each aimed at a named failure mode:

  1. LONGER TRAINING, DONE RIGHT. D15's step math was inconsistent with its
     grad-accum (steps computed len*epochs//8 but the loop consumed accum=4
     examples per step), so "2 epochs" over 400 pairs was really ~1 pass.
     D15b runs 5 REAL epochs (steps derived from the actual accum) over a 450-
     pair curriculum, on a bigger base. Mechanism: the read is a per-byte
     modular subroutine; D15's +0.085 margin after ~1 pass says undertraining,
     not impossibility — so first buy more gradient steps before concluding.

  2. FEW-SHOT WORKED EXAMPLES in the prompt (train AND eval, both arms). D15's
     prompt stated the RULE in prose; D15b shows four fully worked byte
     decodings (0x86->d, 0xca->f, 0x47->u, 0x05->h) covering all four timbres
     and all four momenta, generated programmatically from the codec and
     asserted against latin_decode at startup. Mechanism: gives the model the
     byte->(timbre,data)->mod-4-subtract->code procedure as an input-output
      pattern to imitate, instead of asking it to compile prose to arithmetic
     on its own. Same prompt for base and tuned: the comparison stays honest.

  3. CURRICULUM, SHORT -> LONG. All D15 texts encoded to 30-56-byte streams,
     so every training example demanded per-byte decoding AND 30-56-way output
     alignment at once. D15b builds three stages by truncating the TEXT before
     encoding (still codec-exact pairs, roundtrip asserted): A = first 12 chars
     (~13 bytes), B = first 24 chars (~25 bytes), C = full length. Epoch plan:
     ep1 = A, ep2 = A+B, ep3-5 = A+B+C. Mechanism: learn the per-byte decode
     subroutine where output alignment is trivial, then extend stamina to
     long trajectories. Held-out gate eval stays FULL-LENGTH (pre-registered);
     a short-stream held-out diagnostic (same unseen texts, 12-char truncs)
     separates "can't decode a byte" from "can't hold alignment over 56 bytes"
     in the INCONCLUSIVE case.

  4. BIGGER BASE. Full mode tries Qwen/Qwen2.5-3B-Instruct in 4-bit NF4 first;
     after load it checks free VRAM headroom (mem_get_info). If the 4-bit load
     fails OR free VRAM after load < 1500 MiB (training headroom), it frees and
     falls back to Qwen/Qwen2.5-1.5B-Instruct. The JSON SAYS which base ran and
     why. Mechanism: capacity — D15's honest first rung named "bigger model" as
     one of the live levers; 3B at 4-bit (~2 GB weights + ~0.6 GB LoRA/AdamW)
     should fit the 6 GB 4050 with checkpointing at batch 1.

Task, gate, corpus discipline UNCHANGED from D15 (pre-registered, do not drift):
  input = hex byte stream + public rule; output = one momentum code per byte
  (d/f/u/h), scored per-token over the trajectory (chance 0.25). Split BY TEXT:
  held-out texts never appear in training. Momentum = (timbre - data%4) mod 4
  via the D14 Latin square, so plaintext carries zero momentum bits — >= 0.80
  can ONLY be reached by actually reading timbre+context.

Pre-registered gate (FULL runs only): KEEP iff tuned >= 0.80 AND base <= 0.30;
KILL iff tuned <= base; else INCONCLUSIVE. fp16/fp32 quant fallback forces
INCONCLUSIVE (4-bit is part of the protocol). SMOKE runs are pipeline proofs:
verdict INCONCLUSIVE regardless of numbers.

SMOKE (default, D15B_FULL unset): Qwen2.5-0.5B, curriculum code path exercised
with 4 short + 4 full train pairs (2 optimizer steps), 10 full-length held-out
pairs + 5 short diagnostics.
FULL (D15B_FULL=1): 3B-if-it-fits chain (see above), LoRA r=16 alpha=32 on
q/k/v/o/gate/up/down, grad checkpointing (use_reentrant=False), batch 1 x
grad-accum 8, seq <= 1024, lr 2e-4 AdamW, 5 curriculum epochs over 450 pairs
(150 per stage), eval on 60 full-length held-out pairs (20 unseen texts x 3
draws) + 20 short diagnostics. ~2.5-3.5 h wall on the RTX 4050 6 GB.
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

RESULTS_JSON = LAB / "results" / "d15b_eval.json"
RESULTS_MD = LAB / "RESULTS.md"

SEED = 2718
SMOKE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
FULL_CANDIDATES = ["Qwen/Qwen2.5-3B-Instruct",   # try first: fits 6 GB at 4-bit?
                   "Qwen/Qwen2.5-1.5B-Instruct"]  # D15's base, the known-good floor
HEADROOM_FLOOR_MIB = 1500  # free VRAM required AFTER 4-bit load to attempt training
LORA_R, LORA_ALPHA, LORA_DROPOUT = 16, 32, 0.05
GRAD_ACCUM = 8             # batch 1 x accum 8 = eff batch 8 (D15 full recipe)
MAX_SEQ = 1024             # worked examples lengthen prompts vs D15's 768
LR = 2e-4
MAX_BYTES = 64
NEW_TOKEN_CAP = 160
SMOKE_HELDOUT = 10
STAGE_PAIRS = 150          # full mode: 150 pairs per curriculum stage (450 total)
SMOKE_STAGE_PAIRS = 4      # smoke: 4 short + 4 full = 8 train pairs
TRUNC_A, TRUNC_B = 12, 24  # curriculum stage text truncations (chars)
FULL_HELDOUT = 60          # 20 unseen texts x 3 tone draws, FULL-LENGTH (gate set)
CLAIM_TUNED = 0.80         # pre-registered, unchanged from D15
CLAIM_BASE = 0.30          # pre-registered, unchanged from D15 (chance 0.25)

# momentum state -> output code (compact, tokenizer-friendly)
CODE = {MOMENTUM["down"]: "d", MOMENTUM["flat"]: "f",
        MOMENTUM["up"]: "u", MOMENTUM["hold"]: "h"}
CODE_OF_TOKEN = {"d": MOMENTUM["down"], "f": MOMENTUM["flat"],
                 "u": MOMENTUM["up"], "h": MOMENTUM["hold"]}
WORD_OF_TOKEN = {"down": MOMENTUM["down"], "flat": MOMENTUM["flat"],
                 "up": MOMENTUM["up"], "hold": MOMENTUM["hold"]}
LEGEND = "d=down, f=flat, u=up, h=hold"

# --- worked examples: four REAL QTHE bytes covering all four timbres AND all
# four momenta. Asserted against latin_decode at startup so prompt and codec
# can never drift apart. momentum = ((b>>6) - ((b & 0x3F) % 4)) mod 4.
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
HELD_TEXTS_FULL = 20  # 20 unseen texts x 3 tone draws = 60 full-length held-out

# curriculum: epoch -> list of stages to train on (short trajectories first)
SCHEDULE = {
    "smoke": [["A"], ["A", "C"]],
    "full": [["A"], ["A", "B"], ["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"]],
}


def make_tone(rng: random.Random, n: int) -> list[int]:
    """A seeded momentum TRAJECTORY: 2-4 runs of pairwise-distinct momenta,
    run lengths 1-4, proportionally scaled to n tokens (identical to D15)."""
    moms = rng.sample(list(CODE.keys()), rng.randint(2, 4))
    lens = [rng.randint(1, 4) for _ in moms]
    total = sum(lens)
    out: list[int] = []
    for m, ln in zip(moms, lens):
        out += [m] * max(1, round(ln * n / total))
    out = out[:n]
    while len(out) < n:
        prev = out[-1] if out else None
        choices = [m for m in CODE if m != prev] if prev is not None else list(CODE)
        out.append(rng.choice(choices))
    return out


def make_pair(rng: random.Random, text: str, tag: str) -> dict:
    """(text, tone) -> QTHE byte-stream example, with codec roundtrip proof."""
    data = data_encode(text)
    tone = make_tone(rng, len(data))
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
    genuinely short but still a codec-exact (text, tone) pair."""
    t = text if trunc is None else text[:trunc]
    return make_pair(rng, t, tag)


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


def build_held(rng: random.Random, held_texts: list[str],
               mode: str) -> tuple[list[dict], list[dict]]:
    """Held-out: FULL-LENGTH pairs are the pre-registered gate set; short
    12-char truncations of the same unseen texts are the diagnostic set."""
    draws = 3 if mode == "full" else 1
    held: list[dict] = []
    for t in held_texts:
        for k in range(draws):
            held.append(make_pair(rng, t, f"held-{t[:12]}-{k}"))
    n_short = len(held_texts) if mode == "full" else 5
    short = [make_stage_pair(rng, t, TRUNC_A, f"heldshort-{t[:10]}")
             for t in held_texts[:n_short]]
    return held, short


def build_corpus(rng: random.Random, mode: str) -> tuple[dict, list[dict], list[dict], dict]:
    """Seeded corpus, split BY TEXT (identical discipline to D15)."""
    texts = list(TEXTS)
    rng.shuffle(texts)
    n_held_texts = HELD_TEXTS_FULL if mode == "full" else SMOKE_HELDOUT
    held_texts, train_texts = texts[:n_held_texts], texts[n_held_texts:]
    stages = build_train_stages(rng, train_texts, mode)
    held, held_short = build_held(rng, held_texts, mode)
    stats = {"pool_texts": len(TEXTS), "held_texts": len(held_texts),
             "train_texts": len(train_texts),
             "stage_sizes": {k: len(v) for k, v in stages.items()},
             "trunc_a_chars": TRUNC_A, "trunc_b_chars": TRUNC_B}
    return stages, held, held_short, stats


def target_modules() -> list[str]:
    # Qwen2 attention + MLP projections (D4-proven adapter spec)
    return ["q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"]


def worked_examples_block() -> str:
    """Four fully-worked single-byte decodings, generated FROM the codec and
    asserted against latin_decode in main() — prompt can't drift from math."""
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
    """Bigger-base chain: try 3B in 4-bit; on load failure, non-NF4 outcome, or
    post-load free VRAM < HEADROOM_FLOOR_MIB, free and fall back to 1.5B.
    Returns (tok, model, quant, note, model_used, tried, fallback_note)."""
    env_model = os.environ.get("D15B_MODEL")
    mode = "full" if os.environ.get("D15B_FULL") == "1" else "smoke"
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
    """Batch-1 greedy generation; short/misaligned outputs count wrong."""
    model.eval()
    was_cache = getattr(model.config, "use_cache", True)
    model.config.use_cache = True
    accs: list[float] = []
    exact = 0
    wellformed = 0
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
        a, x = score(pred, ex["gold"])
        accs.append(a)
        exact += x
        wellformed += int(len(pred) == len(ex["gold"]))
        if len(samples) < keep_samples:
            samples.append({"id": ex["id"], "gold": ex["gold_str"],
                            "pred": " ".join(CODE[p] for p in pred[:len(ex["gold"])]),
                            "raw": text[:120], "acc": round(a, 3)})
    model.config.use_cache = was_cache
    n = len(examples)
    return {
        "n": n,
        "acc": round(sum(accs) / n, 4),
        "exact_match": round(exact / n, 4),
        "wellformed_rate": round(wellformed / n, 4),
        "mean_stream_bytes": round(sum(len(e["stream"]) for e in examples)
                                   / max(1, n), 1),
        "seconds": round(time.time() - t0, 1),
        "samples": samples,
    }


def train_epochs(tok, model, schedule: list[list[str]], stages: dict[str, list[dict]],
                 grad_accum: int) -> dict:
    """Real curriculum training: per epoch, concatenate the scheduled stages,
    steps = round(pairs/accum) so '5 epochs' means 5 real passes. Same LoRA
    attach, batch-1 + grad-accum, clip-1.0 AdamW loop as D15 otherwise."""
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
    mode = "full" if os.environ.get("D15B_FULL") == "1" else "smoke"
    seed = int(os.environ.get("D15B_SEED", str(SEED)))
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

    ok, breach, gv = preflight()
    if not ok:
        return _finish({"experiment": "D15b read-the-channel v2", "mode": mode,
                        "device": dev, "seed": seed, "verdict": "ABORTED",
                        "reason": breach,
                        "guard": {"free_mib": gv[0], "temp_c": gv[1]}}, mode)

    stages, held_ex, held_short, cstats = build_corpus(rng, mode)
    schedule = SCHEDULE[mode]

    tok, base, quant_mode, quant_note, model_used, tried, fallback_note = \
        load_candidate_chain(dev)
    base_eval = evaluate(tok, base, held_ex)
    base_eval_short = evaluate(tok, base, held_short)

    t_out = train_epochs(tok, base, schedule, stages, GRAD_ACCUM)
    tuned = t_out.pop("model")
    tuned_eval = evaluate(tok, tuned, held_ex)
    tuned_eval_short = evaluate(tok, tuned, held_short)
    adapter_dir = LAB / "results" / ("d15b_adapter_full" if mode == "full"
                                     else "d15b_adapter_smoke")
    try:
        tuned.save_pretrained(str(adapter_dir))
        adapter_path = str(adapter_dir)
    except Exception as e:
        adapter_path = f"save failed: {type(e).__name__}: {str(e)[:80]}"
    if dev == "cuda":
        torch.cuda.empty_cache()

    margin = round(tuned_eval["acc"] - base_eval["acc"], 4)
    if mode == "smoke":
        verdict = "INCONCLUSIVE"
        reason = (f"smoke pass: pipeline proof only ({t_out['optimizer_steps_total']} steps, "
                  f"{sum(len(v) for v in stages.values())} train pairs, {len(held_ex)} held-out); "
                  f"the gate (tuned>={CLAIM_TUNED}, base<={CLAIM_BASE}) is full-scale")
    elif quant_mode.startswith("fp16-fallback") or quant_mode == "fp32-cpu":
        verdict = "INCONCLUSIVE"
        reason = f"precision gate not met: {quant_note}"
    elif tuned_eval["acc"] >= CLAIM_TUNED and base_eval["acc"] <= CLAIM_BASE:
        verdict = "KEEP"
        reason = (f"tuned reads the channel at {tuned_eval['acc']} (>= {CLAIM_TUNED}) "
                  f"vs base {base_eval['acc']} (<= {CLAIM_BASE}); plaintext alone carries "
                  "zero momentum bits, so the tuned model must be decoding timbre+context")
    elif tuned_eval["acc"] <= base_eval["acc"]:
        verdict = "KILL"
        reason = (f"tuned fails to beat base ({margin:+.4f}) even with 5 curriculum epochs, "
                  f"worked-example prompts, and base {model_used}; the read may need more "
                  "than a LoRA on this scale")
    else:
        gap_read = (f"short-stream diagnostic: tuned {tuned_eval_short['acc']} vs base "
                    f"{base_eval_short['acc']} — "
                    + ("per-byte decode is the bottleneck, not length"
                       if tuned_eval_short["acc"] < tuned_eval["acc"] + 0.1
                       else "length/alignment is the bottleneck, per-byte decode is closer"))
        reason = (f"tuned beats base ({margin:+.4f}) but misses the pre-registered gate: "
                  f"tuned {tuned_eval['acc']} vs {CLAIM_TUNED} / base {base_eval['acc']} "
                  f"vs {CLAIM_BASE}. {gap_read}")

    out = {
        "experiment": "D15b read-the-channel v2 (few-shot + curriculum + 5 real epochs + bigger base)",
        "vision_layer": "Layer 3 reading gate (text-model proxy; VLM step follows this gate)",
        "changes_vs_d15": [
            "5 REAL curriculum epochs (D15's steps/accum mismatch meant ~1 effective pass)",
            "few-shot worked examples: 4 codec-asserted byte decodings in the prompt (both arms)",
            "curriculum short->long: stage A=12-char texts, B=24-char, C=full; ep1=A, ep2=A+B, ep3-5=all",
            "bigger base chain: Qwen2.5-3B 4-bit first, VRAM-headroom fallback to 1.5B",
            "short-stream held-out diagnostic separates read-bottleneck from alignment-bottleneck",
        ],
        "mode": mode,
        "device": dev,
        "seed": seed,
        "model_used": model_used,
        "model_candidates_tried": tried,
        "fallback_note": fallback_note,
        "quant": quant_mode,
        "quant_note": quant_note,
        "qlora": {"r": LORA_R, "alpha": LORA_ALPHA, "dropout": LORA_DROPOUT,
                  "target_modules": target_modules(),
                  "grad_checkpointing": True, "batch": 1, "grad_accum": GRAD_ACCUM,
                  "seq_max": MAX_SEQ, "lr": LR},
        "curriculum": {"schedule": schedule, "stage_truncs": {"A": TRUNC_A, "B": TRUNC_B, "C": None},
                       "worked_example_bytes": {f"{b:02x}": CODE[latin_decode(b >> 6, (b & 0x3F) % 4)]
                                                for b in WORKED_BYTES}},
        "data": {"source": "qthe_codec.encode() seeded foundry (~/projects/qthe-codec)",
                 "split": "BY TEXT: held-out texts never appear in training",
                 **cstats,
                 "train_pairs": sum(len(v) for v in stages.values()),
                 "heldout_pairs_full": len(held_ex),
                 "heldout_pairs_short_diag": len(held_short),
                 "codec_roundtrip": "asserted on every pair"},
        "base_eval": base_eval,
        "base_eval_short_diag": base_eval_short,
        "tuned_eval": tuned_eval,
        "tuned_eval_short_diag": tuned_eval_short,
        "margin_token_acc": margin,
        "preregistered": {"tuned_acc_gte": CLAIM_TUNED, "base_acc_lte": CLAIM_BASE,
                          "chance": 0.25, "gate_set": "FULL-LENGTH held-out only"},
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
            "FULL-SCALE RECIPE (D15B_FULL=1): base chain Qwen2.5-3B -> 1.5B (4-bit NF4 "
            "double-quant; 3B kept only if free VRAM after load >= "
            f"{HEADROOM_FLOOR_MIB} MiB); LoRA r={LORA_R} alpha={LORA_ALPHA} "
            f"dropout={LORA_DROPOUT} on q/k/v/o/gate/up/down; grad checkpointing "
            "(use_reentrant=False); batch 1 x grad-accum {GRAD_ACCUM}; seq<=1024; lr 2e-4 "
            "AdamW; 5 curriculum epochs over 450 pairs (A=12-char, B=24-char, C=full, "
            "150 each): ep1=A, ep2=A+B, ep3-5=all; eval on 60 FULL-LENGTH held-out pairs "
            "(20 unseen texts x 3 draws; pre-registered gate set) + 20 short diagnostics. "
            f"Gate: tuned token-acc >= {CLAIM_TUNED} AND base <= {CLAIM_BASE} (chance 0.25), "
            "unchanged from D15. The decode rule AND worked examples are public in the "
            "prompt for BOTH arms; plaintext carries zero momentum bits (D14), so >= 0.80 "
            "can only be reached by actually reading timbre+context. Expected VRAM ~4-4.5 "
            "GB peak on 3B, ~2.5-3.5 h wall on the RTX 4050 6 GB; smoke takes minutes. "
            "Other lanes contend: preflight floor 1024 MiB free / 80 C; run via runner.py "
            "guard. This pass quant: " + quant_mode + "."
        ),
    }
    return _finish(out, mode)


def _finish(out: dict, mode: str) -> dict:
    RESULTS_JSON.parent.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(out, indent=2) + "\n")
    if os.environ.get("D15B_LEDGER") == "1":
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with RESULTS_MD.open("a") as f:
            f.write(f"\n## D15b — read-the-channel v2 ({out['mode']} pass)\n"
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
        _finish({"experiment": "D15b read-the-channel v2",
                 "mode": "full" if os.environ.get("D15B_FULL") == "1" else "smoke",
                 "device": "cuda" if torch.cuda.is_available() else "cpu",
                 "seed": SEED, "verdict": "ABORTED",
                 "reason": f"{err[-1]} | {err[-2] if len(err) > 1 else ''}"[:400]},
                "smoke")
