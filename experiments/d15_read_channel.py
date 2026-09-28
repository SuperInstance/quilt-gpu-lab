#!/usr/bin/env python3
"""D15 — read-the-channel: teach a small QLoRA to READ the QTHE timbre
channel (VISION.md Layer 3 "reading gate", text-model proxy for the VLM).

Casey's named vision payoff. D14 proved the channel is information-clean:
a QTHE byte is 6 data bits + 2 timbre bits, momentum = (timbre - data%4) mod 4
via a Latin square, so plaintext readers see nothing and context-free timbre
readers see noise. This experiment asks the NEXT question: can a small model
LEARN to be the contextual decoder — recover the momentum trajectory from the
hex byte stream alone? Everything it needs is public (the context key rides
in the data plane), so success can ONLY come through reading the channel:
the plaintext alone carries zero bits about momentum (I(M;T)=0, D14).

Task shape: input = hex byte stream + the public decode rule; output = one
momentum code per byte, space-separated (d=down f=flat u=up h=hold). Accuracy
is per-token over the trajectory (4 states, chance 0.25).

QLoRA per the proven D4 recipe: 4-bit NF4 base (double-quant) + LoRA r=16
alpha=32 on attn/MLP projections, gradient checkpointing, batch 1 + grad
accum, seq <= 768, seed 2718.

Pre-registered gate (FULL runs, from VISION.md Layer 3):
  KEEP  iff tuned token-accuracy >= 0.80 AND base token-accuracy <= 0.30.
  KILL  iff tuned fails to beat base at all (tuned <= base).
  else  INCONCLUSIVE.
SMOKE runs (default, D15_FULL unset) are a pipeline proof only: 2 optimizer
steps (batch 1 x accum 4 on 8 train pairs), 10 held-out pairs, verdict
INCONCLUSIVE regardless of numbers. A 2-step run can neither KEEP nor KILL.

Corpus: seeded (seed 2718) (text, tone) pairs built with qthe_codec.encode()
from ~/projects/qthe-codec. Split is BY TEXT (item-level): held-out eval
never shares a text with training. Tone trajectories are seeded runs of
distinct momenta (2-4 segments, lengths 1-4), so the target is a real
trajectory, not a label. Codec roundtrip is asserted on every pair.

Guard policy (same floor/ceil as guard.py): preflight refuses if free VRAM
< 1024 MiB or temp > 80 C. If the 4-bit load fails: fp16 fallback, and the
JSON SAYS SO. Any crash: prints ONE JSON with verdict ABORTED, exit 0
(failures are data).

SMOKE (default):  Qwen/Qwen2.5-0.5B-Instruct, 4-bit NF4, 2 optimizer steps,
eval base-vs-tuned on 10 held-out pairs.
FULL (D15_FULL=1): Qwen/Qwen2.5-1.5B-Instruct, same adapter spec, 2 epochs
over 400 train pairs, 60 held-out pairs (20 unseen texts x 3 tone draws).
~1 h scale on the RTX 4050 under the lab guard.
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
from qthe_codec import MOMENTUM, data_encode, decode_bytes, encode  # noqa: E402

RESULTS_JSON = LAB / "results" / "d15_eval.json"
RESULTS_MD = LAB / "RESULTS.md"

SEED = 2718
SMOKE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
FULL_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_R, LORA_ALPHA, LORA_DROPOUT = 16, 32, 0.05
GRAD_ACCUM = 4
MAX_SEQ = 768
LR = 2e-4
MAX_BYTES = 64            # corpus cap: stream length <= 64 bytes
NEW_TOKEN_CAP = 160       # generation ceiling per eval example
SMOKE_STEPS = 2
SMOKE_TRAIN_EXAMPLES = 8  # 2 optimizer steps x accum 4
SMOKE_HELDOUT = 10
FULL_TRAIN = 400          # VISION.md: M=400 (caption, tone) pairs
FULL_HELDOUT = 60
FULL_EPOCHS = 2
CLAIM_TUNED = 0.80        # pre-registered: tuned >= 0.80 recovery
CLAIM_BASE = 0.30         # pre-registered: base <= 0.30 (chance 0.25)

# momentum state -> output code (compact, tokenizer-friendly)
CODE = {MOMENTUM["down"]: "d", MOMENTUM["flat"]: "f",
        MOMENTUM["up"]: "u", MOMENTUM["hold"]: "h"}
CODE_OF_TOKEN = {"d": MOMENTUM["down"], "f": MOMENTUM["flat"],
                 "u": MOMENTUM["up"], "h": MOMENTUM["hold"]}
WORD_OF_TOKEN = {"down": MOMENTUM["down"], "flat": MOMENTUM["flat"],
                 "up": MOMENTUM["up"], "hold": MOMENTUM["hold"]}
LEGEND = "d=down, f=flat, u=up, h=hold"

# --- text pool: short lines, mostly lowercase; a few uppercase / rare-char
# lines so the corpus exercises the UPPER-prefix and SHIFT-escape data paths
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
HELD_TEXTS_FULL = 20  # 20 unseen texts x 3 tone draws = 60 held-out pairs


def make_tone(rng: random.Random, n: int) -> list[int]:
    """A seeded momentum TRAJECTORY: 2-4 runs of pairwise-distinct momenta,
    run lengths 1-4, proportionally scaled to n tokens (tail padded with a
    momentum different from its predecessor). Distinct adjacent runs keep the
    target a genuine trajectory rather than a degenerate constant."""
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


def build_corpus(rng: random.Random, mode: str) -> tuple[list[dict], list[dict], dict]:
    """Seeded corpus, split BY TEXT: held-out texts never appear in training.

    smoke: 10 held-out texts x 1 tone draw; 8 train pairs (2 steps x accum 4).
    full:  20 held-out texts x 3 draws = 60 pairs; 400 train pairs (VISION M).
    """
    texts = list(TEXTS)
    rng.shuffle(texts)
    n_held_texts = HELD_TEXTS_FULL if mode == "full" else SMOKE_HELDOUT
    held_texts, train_texts = texts[:n_held_texts], texts[n_held_texts:]

    held: list[dict] = []
    draws = 3 if mode == "full" else 1
    for t in held_texts:
        for k in range(draws):
            held.append(make_pair(rng, t, f"held-{t[:12]}-{k}"))
    if mode == "smoke":
        held = held[:SMOKE_HELDOUT]

    train: list[dict] = []
    target = FULL_TRAIN if mode == "full" else SMOKE_TRAIN_EXAMPLES
    k = 0
    while len(train) < target:
        t = train_texts[k % len(train_texts)]
        train.append(make_pair(rng, t, f"train-{t[:12]}-{k}"))
        k += 1
    rng.shuffle(train)
    stats = {"pool_texts": len(TEXTS), "held_texts": len(held_texts),
             "train_texts": len(train_texts)}
    return train, held, stats


def target_modules() -> list[str]:
    # Qwen2 attention + MLP projections (D4-proven adapter spec)
    return ["q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"]


SYSTEM = ("You are the QTHE channel reader. You recover the hidden momentum "
          "trajectory from QTHE byte streams. Answer with space-separated "
          "codes only.")
RULE = ("Each byte = 6 data bits (low) + 2 timbre bits (top two). The "
        "momentum of each byte is (timbre - (data mod 4)) mod 4, over "
        f"states: {LEGEND}. Output one code per byte, in stream order, "
        "space-separated.")


def build_prompt(tok, hex_stream: str) -> str:
    user = f"QTHE BYTE STREAM (hex):\n{hex_stream}\n\n{RULE}"
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user}]
    try:
        return tok.apply_chat_template(msgs, tokenize=False,
                                       add_generation_prompt=True)
    except Exception:
        return f"System: {SYSTEM}\n\nUser: {user}\n\nAnswer:"


def full_text(tok, ex: dict) -> str:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"QTHE BYTE STREAM (hex):\n{ex['hex']}\n\n{RULE}"},
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
        "seconds": round(time.time() - t0, 1),
        "samples": samples,
    }


def train_steps(tok, model, examples: list[dict], optimizer_steps: int,
                grad_accum: int) -> dict:
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                            gradient_checkpointing_kwargs={"use_reentrant": False})
    lora = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
                      bias="none", task_type=TaskType.CAUSAL_LM,
                      target_modules=target_modules())
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    enc = [encode_example(tok, ex) for ex in examples]
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=LR)
    losses: list[float] = []
    t0 = time.time()
    model.train()
    model.config.use_cache = False
    for step in range(optimizer_steps):
        opt.zero_grad(set_to_none=True)
        run_loss = 0.0
        for i in range(grad_accum):  # batch 1, grad-accum
            ex = enc[(step * grad_accum + i) % len(enc)]
            ids = torch.tensor([ex["input_ids"]], device=model.device)
            lab = torch.tensor([ex["labels"]], device=model.device)
            loss = model(input_ids=ids, labels=lab).loss / grad_accum
            loss.backward()
            run_loss += float(loss.detach())
        torch.nn.utils.clip_grad_norm_(
            (p for p in model.parameters() if p.requires_grad), 1.0)
        opt.step()
        losses.append(round(run_loss, 4))
    return {"model": model, "trainable_params": trainable, "steps": optimizer_steps,
            "losses": losses, "seconds": round(time.time() - t0, 1)}


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
    mode = "full" if os.environ.get("D15_FULL") == "1" else "smoke"
    model_id = os.environ.get("D15_MODEL") or (FULL_MODEL if mode == "full" else SMOKE_MODEL)
    seed = int(os.environ.get("D15_SEED", str(SEED)))
    rng = random.Random(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    ok, breach, gv = preflight()
    if not ok:
        return _finish({"experiment": "D15 read-the-channel", "mode": mode,
                        "model": model_id, "device": dev, "seed": seed,
                        "verdict": "ABORTED", "reason": breach,
                        "guard": {"free_mib": gv[0], "temp_c": gv[1]}}, mode)

    train_ex, held_ex, cstats = build_corpus(rng, mode)
    steps = SMOKE_STEPS if mode == "smoke" else \
        max(1, (len(train_ex) * FULL_EPOCHS) // 8)  # full recipe: eff batch 8

    tok, base, quant_mode, quant_note = load_base(model_id, dev)
    base_eval = evaluate(tok, base, held_ex)

    t_out = train_steps(tok, base, train_ex, steps, GRAD_ACCUM)
    tuned = t_out.pop("model")
    tuned_eval = evaluate(tok, tuned, held_ex)
    adapter_dir = LAB / "results" / ("d15_adapter_full" if mode == "full"
                                     else "d15_adapter_smoke")
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
        reason = (f"smoke pass: pipeline proof only ({steps} steps, {len(train_ex)} train "
                  f"pairs, {len(held_ex)} held-out); the gate (tuned>={CLAIM_TUNED}, "
                  f"base<={CLAIM_BASE}) is full-scale")
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
        reason = f"tuned fails to beat base ({margin:+.4f}); the 0.5B proxy cannot learn the contextual decode"
    else:
        verdict = "INCONCLUSIVE"
        reason = (f"tuned beats base ({margin:+.4f}) but misses the pre-registered gate: "
                  f"tuned {tuned_eval['acc']} vs {CLAIM_TUNED} / base {base_eval['acc']} vs {CLAIM_BASE}")

    out = {
        "experiment": "D15 read-the-channel (LoRA learns the contextual timbre decoder)",
        "vision_layer": "Layer 3 reading gate (text-model proxy; VLM step follows this gate)",
        "mode": mode,
        "device": dev,
        "seed": seed,
        "model": model_id,
        "quant": quant_mode,
        "quant_note": quant_note,
        "qlora": {"r": LORA_R, "alpha": LORA_ALPHA, "dropout": LORA_DROPOUT,
                  "target_modules": target_modules(),
                  "grad_checkpointing": True, "batch": 1, "grad_accum": GRAD_ACCUM,
                  "seq_max": MAX_SEQ, "lr": LR, "optimizer_steps": steps},
        "data": {"source": "qthe_codec.encode() seeded foundry (~/projects/qthe-codec)",
                 "split": "BY TEXT: held-out texts never appear in training",
                 **cstats,
                 "train_pairs": len(train_ex),
                 "heldout_pairs": len(held_ex),
                 "mean_stream_bytes": round(sum(len(e["stream"]) for e in held_ex)
                                            / max(1, len(held_ex)), 1),
                 "codec_roundtrip": "asserted on every pair"},
        "base_eval": base_eval,
        "tuned_eval": tuned_eval,
        "margin_token_acc": margin,
        "preregistered": {"tuned_acc_gte": CLAIM_TUNED, "base_acc_lte": CLAIM_BASE,
                          "chance": 0.25},
        "train": {"steps": t_out["steps"], "losses": t_out["losses"],
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
            "SMOKE numbers are pipeline proof on the 0.5B proxy (2 optimizer steps), "
            "not the hypothesis test. FULL-SCALE RECIPE (D15_FULL=1): model "
            f"{FULL_MODEL}; 4-bit NF4 double-quant + LoRA r={LORA_R} alpha={LORA_ALPHA} "
            f"dropout={LORA_DROPOUT} on q/k/v/o/gate/up/down; grad checkpointing "
            "(use_reentrant=False); batch 1 x grad-accum 8; seq<=768; lr 2e-4 AdamW; "
            f"2 epochs over {FULL_TRAIN} seeded (text, tone) pairs from "
            f"{HELD_TEXTS_FULL and (len(TEXTS) - HELD_TEXTS_FULL)} train texts; eval on "
            f"{FULL_HELDOUT} held-out pairs (20 unseen texts x 3 tone draws). Gate: "
            f"tuned token-acc >= {CLAIM_TUNED} AND base <= {CLAIM_BASE} (chance 0.25). "
            "The decode rule is public in the prompt; plaintext alone carries zero "
            "momentum bits (D14 Latin square), so >= 0.80 can only be reached by "
            "actually reading timbre+context. Expected VRAM ~4-4.5 GB peak, ~1 h wall "
            "on the RTX 4050 6 GB. Other lanes contend: preflight floor 1024 MiB free "
            "/ 80 C; run via runner.py guard. This pass quant: " + quant_mode + "."
        ),
    }
    return _finish(out, mode)


def _finish(out: dict, mode: str) -> dict:
    RESULTS_JSON.parent.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(out, indent=2) + "\n")
    if os.environ.get("D15_LEDGER") == "1":
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with RESULTS_MD.open("a") as f:
            f.write(f"\n## D15 — read-the-channel ({out['mode']} pass)\n"
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
        _finish({"experiment": "D15 read-the-channel",
                 "mode": os.environ.get("D15_FULL") == "1" and "full" or "smoke",
                 "device": "cuda" if torch.cuda.is_available() else "cpu",
                 "seed": SEED, "verdict": "ABORTED",
                 "reason": f"{err[-1]} | {err[-2] if len(err) > 1 else ''}"[:400]},
                "smoke")
