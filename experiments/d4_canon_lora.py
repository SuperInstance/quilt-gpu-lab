"""D4 — canon-lora: can a QLoRA-tuned small instruct model run the doctrinal
read LOCALLY (jev_oracle.py's canon/distortion probe battery, no paid API)?

Probe foundry is seeded from jev-quilt doctrine (jev_oracle.py CANON_STATE +
PROBES): synthetic submissions built from the 8 canon doctrine sentences, the
5 canonical inversions (misquotes), numerical-substance facts, and neutral
Fleet-Radio hull text. Each (submission, probe) pair gets a deterministic
gold yes/no by rule:
  doctrine_X  -> yes iff the submission states canon X correctly
  misquote_X  -> yes iff the submission contains the X inversion
  substance   -> yes iff numerical substrate facts present
  alignment   -> yes iff canon mention present and no inversion

Split is BY SUBMISSION (item-level), then exploded to probes: the held-out
eval never shares a submission with training. Voice probes (2 of the cloud
battery's 14) are intentionally NOT synthesized — they need real Fleet-Radio
prose (full-scale recipe: seed from jev-quilt essays or the D5 dataset).

QLoRA per GPU-DOCKET D4: 4-bit NF4 base (double-quant) + LoRA r=16 alpha=32
on attn/MLP projections, gradient checkpointing, batch 1 + grad-accum,
seq <= 1024, seed 2718.

Pre-registered gate (FULL runs): KEEP iff tuned held-out accuracy beats the
untuned base by >= 0.15 (base is the honest reference — the tuned model must
BUY its keep or the fleet keeps paying the cloud oracle: booked KILL if it
can't). 0 < margin < 0.15: INCONCLUSIVE. SMOKE runs (default, D4_FULL unset)
are a pipeline proof only: verdict INCONCLUSIVE regardless of numbers — a
2-step run can neither KEEP nor KILL the hypothesis, only prove the loop runs.

Guard policy (same floor/ceil as guard.py): preflight refuses if free VRAM
< 1024 MiB or temp > 80 C — other lanes may contend on this 6 GB card.
Any crash: prints ONE JSON with verdict ABORTED, exit 0 (failures are data).

SMOKE (default):  Qwen/Qwen2.5-0.5B-Instruct, 4-bit NF4, 2 optimizer steps
(batch 1 x accum 4) on 8 synthetic probes, eval base-vs-tuned on 20 held-out
probes. If the 4-bit load fails: fp16 fallback, and the JSON says so.
FULL (D4_FULL=1): Qwen/Qwen2.5-1.5B-Instruct, same adapter spec, 2 epochs.
Data: D5 probes.jsonl (deduped, content-addressed) when present, split by
sha256 parity (D5's hash-split discipline); falls back to the synthetic
foundry (55 submissions -> 660 probes). ~60 held-out probes, ~1 h scale on
the RTX 4050. D4_DATA=d5|synthetic forces the source (default: d5 in full,
synthetic in smoke).
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

RESULTS_JSON = LAB / "results" / "d4_eval.json"
RESULTS_MD = LAB / "RESULTS.md"

SEED = 2718
SMOKE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
FULL_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_R, LORA_ALPHA, LORA_DROPOUT = 16, 32, 0.05
GRAD_ACCUM = 4
MAX_SEQ = 1024
LR = 2e-4
MAX_NEW_TOKENS = 4
PREREG_MARGIN = 0.15
SMOKE_TRAIN_EXAMPLES = 8   # 2 optimizer steps x accum 4
SMOKE_STEPS = 2
SMOKE_HELDOUT = 20
FULL_HELDOUT = 60
FULL_EPOCHS = 2

# --- doctrine canon + inversions, verbatim from jev-quilt/jev_oracle.py ----
CANON = {
    "scar": "Cells are scars, not parameters.",
    "witness": "The witness log is the prediction.",
    "grown": "The substrate is grown, not designed.",
    "oracle": "The oracle is heard, not stored.",
    "lenia": "Lenia flows where Conway stands still.",
    "canary": "The canary hash 0xcbf29ce484222325 is the offset basis of all things.",
    "ports": "Thirteen ports, byte-exact.",
    "humility": "JEV says JEV is barely useful at substrate.",
}
INVERTED = {
    "scar": "Cells are parameters, not scars.",
    "witness": "The witness log is the past only, with no future.",
    "grown": "The substrate is designed rather than grown.",
    "oracle": "The oracle is stored, not heard.",
    "ports": "Fifteen ports, byte-exact.",
}
FACTS = [
    "FNV-1a, 64-bit, canary offset basis 0xcbf29ce484222325.",
    "Xoshiro turns on four state words.",
    "Box-Muller: z = sqrt(-2*ln(u1))*cos(2*pi*u2).",
    "Cosine similarity: (A.B)/(||A||*||B||).",
    "Bell phi-plus: (|00> + |11>)/sqrt(2).",
]
HULLS = [
    "Transmission open. The hull sings and the quilt holds its breath.",
    "Watch log: rigging taut, signal clean, the record runs.",
    "// fleet relay // passive sweep complete, nothing on the horizon but weather.",
    "The quartermaster tallies salt and wire.",
    "Engines idling, antenna wet, the log keeps itself.",
    "The sonar pings once and the deep answers slow.",
    "Steady as she goes; the ledger keeps its own columns.",
    "Night watch: cold coffee, warm valves, the chart unrolls.",
]
# probe battery (verbatim questions from jev_oracle.py PROBES; voice probes
# excluded — synthetic voice text would be a strawman, see docstring)
PROBES = {
    "doctrine_scar": "Does this correctly state that cells are scars, not parameters?",
    "doctrine_witness": "Does this correctly state that the witness log is also a prediction?",
    "doctrine_grown": "Does this correctly state that the substrate is grown, not designed?",
    "doctrine_oracle": "Does this correctly state that the oracle is heard, not stored?",
    "doctrine_lenia": "Does this correctly state that Lenia flows where Conway stands still?",
    "misquote_scar_params": "Does this contain any misquote saying cells are parameters, not scars?",
    "misquote_witness_past": "Does this say the witness log is past only, with no future?",
    "misquote_designed": "Does this say the substrate is designed rather than grown?",
    "misquote_15ports": "Does this mention fifteen ports instead of thirteen?",
    "misquote_oracle_stored": "Does this say the oracle is stored, not heard?",
    "substance_numerical": "Does this contain numerical substrate facts (FNV-1a hashes, cosine formula, etc.)?",
    "substrate_alignment": "Overall, does this align with substrate canon?",
}
DOCTRINE_PROBES = {  # probe name -> canon key it checks
    "doctrine_scar": "scar", "doctrine_witness": "witness", "doctrine_grown": "grown",
    "doctrine_oracle": "oracle", "doctrine_lenia": "lenia",
}
MISQUOTE_PROBES = {
    "misquote_scar_params": "scar", "misquote_witness_past": "witness",
    "misquote_designed": "grown", "misquote_15ports": "ports",
    "misquote_oracle_stored": "oracle",
}


def build_items(rng: random.Random) -> list[dict]:
    """Synthetic submissions with deterministic mention structure.

    Seeded hull variants per doctrine/fact so the FULL split can hold out
    whole submissions (item-level) without starving the train side.
    """
    hulls = rng.sample(HULLS, len(HULLS))
    facts = rng.sample(FACTS, len(FACTS))
    items = []
    for i, key in enumerate(CANON):  # 24 canon items (8 doctrines x 3 hulls)
        for v in range(3):
            items.append({"id": f"canon-{key}-{v}",
                          "text": f"{CANON[key]} {hulls[(i + v * 3) % len(hulls)]}",
                          "mentions": {key: "canon"}, "has_fact": False})
    for i, key in enumerate(INVERTED):  # 15 distorted items (5 inversions x 3 hulls)
        for v in range(3):
            items.append({"id": f"distorted-{key}-{v}",
                          "text": f"{INVERTED[key]} {hulls[(i + 1 + v * 2) % len(hulls)]}",
                          "mentions": {key: "inverted"}, "has_fact": False})
    for i, fact in enumerate(facts):  # 10 fact items (substance, no doctrine)
        for v in range(2):
            items.append({"id": f"fact-{i}-{v}",
                          "text": f"{fact} {hulls[(i + 5 + v) % len(hulls)]}",
                          "mentions": {}, "has_fact": True})
    for i in range(6):  # 6 neutral items
        items.append({"id": f"neutral-{i}", "text": hulls[(i + 1) % len(hulls)],
                      "mentions": {}, "has_fact": False})
    return items


def gold_label(probe: str, item: dict) -> str:
    if probe in DOCTRINE_PROBES:
        return "yes" if item["mentions"].get(DOCTRINE_PROBES[probe]) == "canon" else "no"
    if probe in MISQUOTE_PROBES:
        return "yes" if item["mentions"].get(MISQUOTE_PROBES[probe]) == "inverted" else "no"
    if probe == "substance_numerical":
        return "yes" if item["has_fact"] else "no"
    if probe == "substrate_alignment":
        m = item["mentions"]
        return "yes" if ("canon" in m.values() and "inverted" not in m.values()) else "no"
    raise KeyError(probe)


def probe_family(probe: str) -> str:
    if probe.startswith("doctrine_"):
        return "doctrine"
    if probe.startswith("misquote_"):
        return "misquote"
    return "substance" if probe.startswith("substance") else "alignment"


def split_items(rng: random.Random, items: list[dict], n_held: int) -> tuple[list[dict], list[dict]]:
    """Type-stratified submission split: round-robin canon/distorted/fact/
    neutral so held-out eval covers every probe family and both labels.
    Remainder -> train. Still submission-level: no item on both sides."""
    by_type: dict[str, list[dict]] = {}
    for it in items:
        by_type.setdefault(it["id"].split("-")[0], []).append(it)
    for lst in by_type.values():
        rng.shuffle(lst)
    types = [t for t in ("canon", "distorted", "fact", "neutral") if by_type.get(t)]
    held: list[dict] = []
    i = 0
    while len(held) < n_held and any(by_type[t] for t in types):
        t = types[i % len(types)]
        if by_type[t]:
            held.append(by_type[t].pop())
        i += 1
    train = [it for t in types for it in by_type[t]]
    rng.shuffle(train)
    return held, train


def build_examples(rng: random.Random, heldout_items: list[dict], n_eval: int,
                   train_items: list[dict], n_train: int | None) -> tuple[list[dict], list[dict]]:
    """Item-level split, then explode to (probe, submission, gold) examples.

    Held-out eval is label-stratified (half yes / half no when the pool
    allows) so accuracy is interpretable; train side is a plain seeded draw.
    """
    heldout = [{"item_id": it["id"], "probe": p, "question": q, "submission": it["text"],
                "gold": gold_label(p, it), "family": probe_family(p)}
               for it in heldout_items for p, q in PROBES.items()]
    rng.shuffle(heldout)
    heldout = _stratified_sample(heldout, n_eval, rng)
    train = [{"item_id": it["id"], "probe": p, "question": q, "submission": it["text"],
              "gold": gold_label(p, it), "family": probe_family(p)}
             for it in train_items for p, q in PROBES.items()]
    rng.shuffle(train)
    if n_train is not None:
        train = train[:n_train]
    assert len({e["gold"] for e in heldout}) == 2, "degenerate eval: single gold label"
    return train, heldout


def _stratified_sample(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    if n >= len(pool):
        return pool
    by_gold = {g: [e for e in pool if e["gold"] == g] for g in ("yes", "no")}
    pick = []
    for g in ("yes", "no"):
        take = min(n // 2, len(by_gold[g]))
        pick += by_gold[g][:take]
    rest = [e for e in pool if e not in pick]
    rng.shuffle(rest)
    return pick + rest[:n - len(pick)]


TARGET_MODULES = {
    "qwen2": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "opt": ["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"],
}


def build_d5_split(n_held: int) -> tuple[list[dict], list[dict]] | None:
    """D5 foundry rows (probes.jsonl) -> canon-reader examples.

    claim/evidence pair -> 'does the EVIDENCE support the CLAIM?'; gold yes
    iff label canon. Split by sha256 parity — deterministic, seed-independent
    (D5's own hash-split discipline). Eval half label-stratified. Returns
    None when the dataset is absent or too thin to be worth a full run.
    """
    path = LAB / "probes.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(rows) < 40:
        return None
    held: list[dict] = []
    train: list[dict] = []
    for r in rows:
        ex = {"item_id": r["sha256"][:16], "probe": f"d5_{r['kind']}",
              "question": "Does the EVIDENCE support the CLAIM? "
                          "Answer with exactly one word: yes or no.",
              "submission": f"CLAIM: {r['claim']}\nEVIDENCE: {r['evidence']}",
              "gold": "yes" if r["label"] == "canon" else "no",
              "family": r["kind"]}
        (held if int(r["sha256"], 16) % 2 else train).append(ex)
    rng2 = random.Random(SEED * 7 + 1)  # separate stream; foundry rng untouched
    rng2.shuffle(held)
    rng2.shuffle(train)
    return train, _stratified_sample(held, min(n_held, len(held)), rng2)


def target_modules_for(model_type: str) -> list[str]:
    for key, mods in TARGET_MODULES.items():
        if key in model_type.lower():
            return mods
    return ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def build_prompt(tok, question: str, submission: str) -> str:
    submission = submission[:3000]  # jev_oracle truncates submissions the same way
    user = f"{question}\n\n---\nSUBMISSION:\n{submission}\n---\n\nAnswer with exactly one word: yes or no."
    msgs = [
        {"role": "system", "content": "You are the Fleet-Radio canon reader. "
         "Judge submissions against substrate canon. Answer with exactly one word: yes or no."},
        {"role": "user", "content": user},
    ]
    try:
        return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        return f"System: judge canon. Answer yes or no.\n\nUser: {user}\n\nAnswer:"


def full_text_and_prompt_len(tok, question: str, submission: str, gold: str) -> tuple[str, int]:
    prompt = build_prompt(tok, question, submission)
    try:
        full = tok.apply_chat_template(
            [{"role": "system", "content": "You are the Fleet-Radio canon reader. "
              "Judge submissions against substrate canon. Answer with exactly one word: yes or no."},
             {"role": "user", "content": f"{question}\n\n---\nSUBMISSION:\n{submission[:3000]}\n---\n\n"
              f"Answer with exactly one word: yes or no."},
             {"role": "assistant", "content": gold}],
            tokenize=False)
    except Exception:
        full = prompt + gold
    return full, len(tok(prompt, add_special_tokens=False).input_ids)


def encode_example(tok, ex: dict) -> dict:
    full, plen = full_text_and_prompt_len(tok, ex["question"], ex["submission"], ex["gold"])
    ids = tok(full, truncation=True, max_length=MAX_SEQ, add_special_tokens=False).input_ids
    labels = list(ids)
    for i in range(min(plen, len(labels))):
        labels[i] = -100  # loss only on the gold answer token(s)
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


def answer_of(text: str) -> str:
    t = text.strip().lower()
    if t.startswith("yes"):
        return "yes"
    if t.startswith("no"):
        return "no"
    return "unparseable"


def evaluate(tok, model, examples: list[dict]) -> dict:
    """Batch-1 greedy generation; unparseable counts as wrong (honest)."""
    model.eval()
    was_cache = getattr(model.config, "use_cache", True)
    model.config.use_cache = True
    per_family: dict[str, list[int]] = {}
    correct = 0
    parsed = 0
    t0 = time.time()
    for ex in examples:
        prompt = build_prompt(tok, ex["question"], ex["submission"])
        ids = tok(prompt, return_tensors="pt", truncation=True, max_length=MAX_SEQ).to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS,
                                 do_sample=False, pad_token_id=tok.pad_token_id)
        pred = answer_of(tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True))
        ok = int(pred == ex["gold"])
        parsed += int(pred != "unparseable")
        correct += ok
        per_family.setdefault(ex["family"], []).append(ok)
    model.config.use_cache = was_cache
    n = len(examples)
    return {
        "n": n,
        "acc": round(correct / n, 4),
        "parse_rate": round(parsed / n, 4),
        "seconds": round(time.time() - t0, 1),
        "per_family": {k: round(sum(v) / len(v), 4) for k, v in sorted(per_family.items())},
        "per_family_n": {k: len(v) for k, v in sorted(per_family.items())},
    }


def train_steps(tok, model, examples: list[dict], optimizer_steps: int,
                grad_accum: int) -> dict:
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                            gradient_checkpointing_kwargs={"use_reentrant": False})
    lora = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
                      bias="none", task_type=TaskType.CAUSAL_LM,
                      target_modules=target_modules_for(model.config.model_type))
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
    mode = "full" if os.environ.get("D4_FULL") == "1" else "smoke"
    model_id = os.environ.get("D4_MODEL") or (FULL_MODEL if mode == "full" else SMOKE_MODEL)
    seed = int(os.environ.get("D4_SEED", str(SEED)))
    rng = random.Random(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    ok, breach, gv = preflight()
    if not ok:
        return _finish({"experiment": "D4 canon-lora", "mode": mode, "model": model_id,
                        "device": dev, "seed": seed, "verdict": "ABORTED",
                        "reason": breach, "guard": {"free_mib": gv[0], "temp_c": gv[1]}}, mode)

    # --- probe data: D5 dataset (hash-split) when present, else foundry ---
    n_held = FULL_HELDOUT if mode == "full" else SMOKE_HELDOUT
    accum = GRAD_ACCUM if mode == "smoke" else 8  # full recipe: eff batch 8
    use_d5 = os.environ.get("D4_DATA", "d5" if mode == "full" else "synthetic") == "d5"
    d5 = build_d5_split(n_held) if use_d5 else None
    items = build_items(rng)  # synthetic foundry: smoke data + pool stats
    rng.shuffle(items)
    if d5:
        train_ex, held_ex = d5
        data_source = ("D5 probes.jsonl (content-addressed, sha256-parity "
                       "split, label-stratified eval)")
        if mode == "smoke":
            train_ex = train_ex[:SMOKE_TRAIN_EXAMPLES]
    else:
        data_source = "synthetic foundry (jev_oracle canon battery templates)"
        held_items, train_items = split_items(rng, items, max(2, n_held // 3))
        # item counts: heldout ~6 items smoke / 20 items full -> 20 / 60 probe examples
        n_eval = min(n_held, len(held_items) * len(PROBES))
        n_train = SMOKE_TRAIN_EXAMPLES if mode == "smoke" else None
        train_ex, held_ex = build_examples(rng, held_items, n_eval, train_items, n_train)
    if mode == "smoke":
        steps = SMOKE_STEPS
    else:  # 2 epochs over the full train pool, expressed as optimizer steps
        steps = max(1, (len(train_ex) * FULL_EPOCHS) // accum)

    # --- base model: 4-bit NF4 (fp16 fallback says so) --------------------
    tok, base, quant_mode, quant_note = load_base(model_id, dev)
    base_eval = evaluate(tok, base, held_ex)

    # --- QLoRA train + tuned eval -----------------------------------------
    t_out = train_steps(tok, base, train_ex, steps, accum)
    tuned = t_out.pop("model")
    tuned_eval = evaluate(tok, tuned, held_ex)
    adapter_dir = LAB / "results" / ("d4_adapter_full" if mode == "full" else "d4_adapter_smoke")
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
        reason = (f"smoke pass: pipeline proof only ({steps} steps, {len(train_ex)} train probes, "
                  f"{len(held_ex)} held-out); the KEEP/KILL gate (|{PREREG_MARGIN}|) is full-scale")
    elif quant_mode.startswith("fp16-fallback") or quant_mode == "fp32-cpu":
        verdict = "INCONCLUSIVE"
        reason = f"precision gate not met: {quant_note}"
    elif margin >= PREREG_MARGIN:
        verdict = "KEEP"
        reason = f"tuned beats base by {margin:+.4f} >= {PREREG_MARGIN} on {len(held_ex)} held-out probes"
    elif margin <= 0:
        verdict = "KILL"
        reason = f"tuned fails to beat base ({margin:+.4f}); fleet keeps the cloud oracle, honestly"
    else:
        verdict = "INCONCLUSIVE"
        reason = (f"positive but under the pre-registered margin: {margin:+.4f} < {PREREG_MARGIN}")

    out = {
        "experiment": "D4 canon-lora (QLoRA local canon reader)",
        "mode": mode,
        "device": dev,
        "seed": seed,
        "model": model_id,
        "quant": quant_mode,
        "quant_note": quant_note,
        "qlora": {"r": LORA_R, "alpha": LORA_ALPHA, "dropout": LORA_DROPOUT,
                  "target_modules": target_modules_for(getattr(tuned.config, "model_type",
                                                               getattr(base.config, "model_type", ""))),
                  "grad_checkpointing": True, "batch": 1, "grad_accum": accum,
                  "seq_max": MAX_SEQ, "lr": LR, "optimizer_steps": steps},
        "data": {"source": data_source, "pool_items": len(items), "train_examples": len(train_ex),
                 "heldout_examples": len(held_ex),
                 "heldout_gold_yes": sum(1 for e in held_ex if e["gold"] == "yes"),
                 "heldout_gold_no": sum(1 for e in held_ex if e["gold"] == "no"),
                 "split": "by submission item, then exploded to probes; no submission in both sides"},
        "base_eval": base_eval,
        "tuned_eval": tuned_eval,
        "margin": margin,
        "preregistered_margin": PREREG_MARGIN,
        "train": {"steps": t_out["steps"], "losses": t_out["losses"],
                  "trainable_params": t_out["trainable_params"], "seconds": t_out["seconds"]},
        "adapter_path": adapter_path,
        "peak_vram_mib": (round(torch.cuda.max_memory_allocated() / 2**20, 1)
                          if dev == "cuda" else None),
        "wall_seconds": round(time.time() - t_start, 1),
        "versions": versions(),
        "verdict": verdict,
        "reason": reason,
        "note": (
            "SMOKE numbers above are pipeline proof on a 0.5B proxy (2 optimizer steps), "
            "not the hypothesis test. FULL-SCALE RECIPE (D4_FULL=1): model "
            f"{FULL_MODEL}; 4-bit NF4 double-quant + LoRA r={LORA_R} alpha={LORA_ALPHA} dropout="
            f"{LORA_DROPOUT} on q/k/v/o/gate/up/down; grad checkpointing (use_reentrant=False); "
            "batch 1 x grad-accum 8; seq<=1024; lr 2e-4 AdamW; 2 epochs; data source "
            f"this pass: {data_source}; synthetic fallback pool = {len(items)} submissions "
            f"x {len(PROBES)} probes = {len(items) * len(PROBES)} probes; this pass used "
            f"{len(train_ex)} train + {len(held_ex)} held-out; D5's recipe scales to "
            "thousands. Eval on "
            "~60 held-out probes + spot-agreement vs cloud oracle if a key is present. "
            "Expected VRAM ~4-4.5 GB peak (0.5B smoke measured above), ~1 h wall on the "
            "RTX 4050 6 GB. Voice probes need real Fleet-Radio prose (jev-quilt essays). "
            "Other lanes contend: preflight floor 1024 MiB free / 80 C; run via runner.py guard."
        ),
    }
    return _finish(out, mode)


def _finish(out: dict, mode: str) -> dict:
    RESULTS_JSON.parent.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(out, indent=2) + "\n")
    if os.environ.get("D4_LEDGER") == "1":
        _append_ledger(out)
    print(json.dumps(out, indent=2))
    return out


def _append_ledger(out: dict) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = (
        f"\n## D4 — canon-lora ({out['mode']} pass)\n"
        f"- ran: {ts}\n- verdict: **{out['verdict']}**\n"
        f"- result: ```json\n{json.dumps(out, indent=2)}\n```\n"
        f"- note: {out['reason']}\n"
    )
    with RESULTS_MD.open("a") as f:
        f.write(block)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc().strip().splitlines()
        _finish({"experiment": "D4 canon-lora",
                 "mode": os.environ.get("D4_FULL") == "1" and "full" or "smoke",
                 "device": "cuda" if torch.cuda.is_available() else "cpu",
                 "seed": SEED, "verdict": "ABORTED",
                 "reason": f"{err[-1]} | {err[-2] if len(err) > 1 else ''}"[:400]}, "smoke")
