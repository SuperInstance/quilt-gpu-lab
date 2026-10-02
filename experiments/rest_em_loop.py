#!/usr/bin/env python3
"""
rest_em_loop.py — ReST-EM / Absolute-Zero style self-improvement loop (local, zero-metered spend).

Loop: generate -> verify (EXECUTABLE: sympy + property tests, NO LLM judge) -> select -> QLoRA/tiny fine-tune -> repeat.

Generation backends:
  - ollama  : local OpenAI-compat server (http://127.0.0.1:11434/v1/chat/completions), used for round-0
              base-policy sampling (+ base parity eval). Falls back to HF on transport failure (logged).
  - hf      : transformers generate() on the CURRENT policy (LoRA adapter attached) — required from round >= 1
              so that generation tracks the improving policy (true ReST-EM self-play).

Training: QLoRA (peft + bitsandbytes NF4) if CUDA; peft fp32 LoRA on CPU; hand-rolled LoRA fallback.
See proposals/runs/REST-EM-prereg.md for the frozen pre-registration (sizes/gates there; smoke sizes here
are engineering validation only).
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import sympy
    from sympy import Rational, Symbol, simplify, expand
    from sympy.parsing.sympy_parser import (
        implicit_multiplication_application,
        convert_xor,
        parse_expr,
        standard_transformations,
    )
    HAVE_SYMPY = True
except Exception:  # pragma: no cover
    HAVE_SYMPY = False

import torch
import torch.nn as nn
import torch.nn.functional as F

# --------------------------------------------------------------------------------------
# Frozen prompt (identical for generation, selection, SFT, eval)
# --------------------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a careful math assistant. Reason briefly, then always end your reply with a "
    "line of the form 'Answer: <result>'."
)
FEWSHOT = [
    {"role": "user", "content": "Compute 47 + 85."},
    {"role": "assistant", "content": "47 + 85 = 132\nAnswer: 132"},
    {"role": "user", "content": "Simplify the expression: (3*x + 2) + (x - 5). Give the result in terms of x."},
    {"role": "assistant", "content": "Combining like terms: 3*x + x = 4*x and 2 - 5 = -3, so the result is 4*x - 3.\nAnswer: 4*x - 3"},
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------------------
# Task generation (frozen seeds; see prereg section 4)
# --------------------------------------------------------------------------------------
@dataclass
class Task:
    tid: int
    kind: str          # 'arith' | 'symb'
    family: str        # add2/add3/sub/mul/mixed | lin_add/lin_sub/sq_collect/dist
    expr: str
    prompt_user: str
    target_str: str
    target_expr: object = None  # sympy expr for symb tasks


def _arith_task(rng: random.Random, tid: int, family: str) -> Task:
    if family == "add2":
        a, b = rng.randint(13, 499), rng.randint(13, 499)
        expr, ans = f"{a} + {b}", a + b
    elif family == "add3":
        a, b, c = (rng.randint(5, 99) for _ in range(3))
        expr, ans = f"{a} + {b} + {c}", a + b + c
    elif family == "sub":
        a = rng.randint(120, 999)
        b = rng.randint(11, a - 5)
        expr, ans = f"{a} - {b}", a - b
    elif family == "mul":
        a, b = rng.randint(12, 29), rng.randint(3, 12)
        expr, ans = f"{a} * {b}", a * b
    elif family == "mixed":
        a, b, c = rng.randint(5, 99), rng.randint(5, 99), rng.randint(3, 9)
        expr, ans = f"({a} + {b}) * {c}", (a + b) * c
    elif family == "mul2x3":
        a, b = rng.randint(100, 999), rng.randint(10, 99)
        expr, ans = f"{a} * {b}", a * b
    elif family == "nested2":
        a, b, c, d = (rng.randint(2, 30), rng.randint(2, 30), rng.randint(2, 12), rng.randint(2, 99))
        expr, ans = f"(({a} + {b}) * {c}) - {d}", (a + b) * c - d
    else:
        raise ValueError(family)
    return Task(tid, "arith", family, expr, f"Compute {expr}.", str(ans), None)


def _symb_task(rng: random.Random, tid: int, family: str) -> Task:
    if family == "lin_add":
        a, c = rng.randint(2, 12), rng.randint(2, 12)
        b, d = rng.randint(1, 20), rng.randint(1, 20)
        expr = f"({a}*x + {b}) + ({c}*x - {d})"
    elif family == "lin_sub":
        a, c = rng.randint(2, 12), rng.randint(2, 12)
        b, d = rng.randint(1, 20), rng.randint(1, 20)
        expr = f"({a}*x + {b}) - ({c}*x + {d})"
    elif family == "sq_collect":
        a, c = rng.randint(2, 9), rng.randint(2, 9)
        b, d = rng.randint(2, 9), rng.randint(2, 9)
        expr = f"{a}*x**2 + {b}*x - ({c}*x**2 - {d}*x)"
    elif family == "dist":
        a, c = rng.randint(2, 9), rng.randint(2, 9)
        b = rng.randint(2, 15)
        expr = f"{a}*(x + {b}) + {c}*x"
    elif family == "poly2":
        a, b, c, d = (rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 9))
        expr = f"({a}*(x + {b}) - {c}) * (x + {d})"
    else:
        raise ValueError(family)
    e = expand(simplify(sym(expr)))
    return Task(tid, "symb", family, expr,
                f"Simplify the expression: {expr}. Give the result in terms of x.",
                str(e), e)


ARITH_FAMILIES = ["add2", "add3", "sub", "mul", "mixed"]
SYMB_FAMILIES = ["lin_add", "lin_sub", "sq_collect", "dist"]
# Amendment A1 (2026-10-02, keeper): frozen HARD distribution — selected only via --difficulty hard.
ARITH_FAMILIES_HARD = ["mul2x3", "nested2", "mul", "mixed", "add3"]
SYMB_FAMILIES_HARD = ["poly2", "sq_collect", "dist", "lin_add"]


def gen_task_pool(seed: int, n_arith: int, n_symb: int, start_tid: int = 0,
                  difficulty: str = "registered") -> list:
    arith_families = ARITH_FAMILIES_HARD if difficulty == "hard" else ARITH_FAMILIES
    symb_families = SYMB_FAMILIES_HARD if difficulty == "hard" else SYMB_FAMILIES
    rng = random.Random(seed)
    tasks, tid = [], start_tid
    for i in range(n_arith):
        tasks.append(_arith_task(rng, tid, arith_families[i % len(arith_families)]))
        tid += 1
    for i in range(n_symb):
        tasks.append(_symb_task(rng, tid, symb_families[i % len(symb_families)]))
        tid += 1
    rng.shuffle(tasks)
    return tasks


# --------------------------------------------------------------------------------------
# Verifier — EXECUTABLE ONLY (regex extraction + int equality / sympy + numeric property test)
# --------------------------------------------------------------------------------------
X = Symbol("x")  # single shared symbol; never real=True here (assumption mismatch = invisible bug)


def sym(s: str):
    """sympify with the SAME x symbol the verifier uses (avoids assumption-identity bugs)."""
    return sympy.sympify(s, locals={"x": X})
LOCAL_DICT = {"x": X}
TRANSFORMS = standard_transformations + (convert_xor, implicit_multiplication_application)
PROBE_POINTS = [Rational(-7, 3), Rational(-1, 2), Rational(1, 5), Rational(2), Rational(13, 4)]
UNSAFE_SUBSTRINGS = ["__", "lambda", ";", "import", "eval", "exec", "open(", "input("]
ANSWER_RE = re.compile(r"(?is)answer\s*[:\-]\s*([^\n]+)")


def extract_answer(text: str):
    """Return the last 'Answer: ...' payload, or None."""
    if not text:
        return None
    matches = ANSWER_RE.findall(text)
    if not matches:
        return None
    return matches[-1].strip().rstrip(".").strip()


def check_arith(ans_str: str, target: int):
    s = ans_str.replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+", s):
        return False, "not_int"
    return int(s) == target, "exact" if int(s) == target else "wrong_value"


def check_symbolic(ans_str: str, target_expr):
    s = ans_str.strip()
    if any(b in s for b in UNSAFE_SUBSTRINGS):
        return False, "unsafe"
    try:
        expr = parse_expr(s, local_dict=LOCAL_DICT, transformations=TRANSFORMS, evaluate=True)
    except Exception:
        return False, "parse_error"
    try:
        if not (getattr(expr, "free_symbols", set()) <= {X}):
            return False, "bad_symbols"
    except Exception:
        return False, "bad_symbols"
    try:
        if simplify(expr - target_expr) == 0:
            return True, "exact_simplify"
    except Exception:
        pass
    # Property test: numeric substitution at frozen rational points.
    try:
        for pt in PROBE_POINTS:
            d = abs(complex((expr - target_expr).subs({X: pt}).evalf()))
            if not (d == d) or d > 1e-9:  # NaN or mismatch
                return False, "numeric_mismatch"
        return True, "numeric_property"
    except Exception:
        return False, "numeric_error"


class Verifier:
    """Executable verifier. check() -> (ok, reason). No LLM anywhere in this path."""

    def check(self, task: Task, text: str):
        ans = extract_answer(text)
        if ans is None:
            return False, "no_answer_tag"
        if task.kind == "arith":
            return check_arith(ans, int(task.target_str))
        return check_symbolic(ans, task.target_expr)

    # Negative-control self-test (prereg N1). Must be 100% or the run aborts.
    def self_test(self) -> dict:
        t_add = Task(-1, "arith", "add2", "47 + 85", "Compute 47 + 85.", "132", None)
        t_mul = Task(-2, "arith", "mul", "17 * 8", "Compute 17 * 8.", "136", None)
        t_sym = Task(-3, "symb", "lin_add", "(3*x + 2) + (x - 5)",
                     "Simplify", "4*x - 3", expand(sym("(3*x+2)+(x-5)")))
        t_sq = Task(-4, "symb", "sq_collect", "5*x**2 + 3*x - (3*x**2 - 2*x)",
                    "Simplify", "2*x**2 + 5*x", expand(sym("5*x**2+3*x-(3*x**2-2*x)")))
        accept_cases = [
            (t_add, "47 + 85 = 132\nAnswer: 132"),
            (t_add, "I think it is 132.\nAnswer: 132"),
            (t_mul, "Answer: 136"),
            (t_sym, "Combining: 4*x - 3\nAnswer: 4*x - 3"),
            (t_sym, "Answer: -3 + 4*x"),
            (t_sym, "Answer: 4x - 3"),          # implicit-multiplication leniency (intended)
            (t_sq, "Answer: 2*x**2 + 5*x"),
            (t_sq, "Answer: 5*x + 2*x^2"),      # convert_xor leniency (intended)
        ]
        reject_cases = [
            (t_add, "Answer: 131"),             # off by one
            (t_add, "Answer: 133"),             # off by one
            (t_add, "Answer: 132.0"),           # strict integer format
            (t_add, "the answer is 132"),       # no Answer tag
            (t_add, ""),                        # empty
            (t_mul, "Answer: 135"),
            (t_sym, "Answer: 5*x - 3"),         # wrong coefficient
            (t_sym, "Answer: 4*y - 3"),         # wrong variable
            (t_sym, "Answer: 4*x - 3 + 1"),     # wrong constant
            (t_sym, "Answer: banana"),          # garbage
            (t_sq, "Answer: 2*x**2 + 5"),       # dropped term
            (t_sq, "Answer: x**3"),
        ]
        a_fail = [(c[1], self.check(c[0], c[1])) for c in accept_cases if not self.check(c[0], c[1])[0]]
        r_fail = [(c[1], self.check(c[0], c[1])) for c in reject_cases if self.check(c[0], c[1])[0]]
        return {
            "n_accept_cases": len(accept_cases), "n_reject_cases": len(reject_cases),
            "accept_failures": a_fail, "reject_failures": r_fail,
            "passed": (not a_fail) and (not r_fail),
        }


# --------------------------------------------------------------------------------------
# Ollama backend (OpenAI-compat, local only)
# --------------------------------------------------------------------------------------
class OllamaBackend:
    def __init__(self, url: str, model: str, timeout_s: int = 180, workers: int = 4):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.workers = workers
        self.transport_failures = 0

    def _one(self, messages, temperature, max_tokens, greedy):
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0 if greedy else temperature,
            "stream": False,
        }
        if not greedy:
            body["top_p"] = 0.95
        req = urllib.request.Request(
            self.url + "/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.transport_failures += 1
            return None

    def chat_many(self, messages_list, temperature, max_tokens, greedy=False):
        """Threaded generation; returns list[str|None] (None = transport failure, NOT a verifier reject)."""
        out = [None] * len(messages_list)
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = {ex.submit(self._one, m, temperature, max_tokens, greedy): i
                    for i, m in enumerate(messages_list)}
            for fut in cf.as_completed(futs):
                out[futs[fut]] = fut.result()
        return out


# --------------------------------------------------------------------------------------
# HF backend (current policy: base model + LoRA adapter)
# --------------------------------------------------------------------------------------
class HFBackend:
    def __init__(self, model, tok, device, max_batch: int = 8):
        self.model, self.tok, self.device, self.max_batch = model, tok, device, max_batch

    def render(self, messages) -> str:
        return self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    @torch.no_grad()
    def generate(self, messages_list, greedy, temperature=0.8, top_p=0.95, max_new=200):
        self.model.eval()
        self.model.config.use_cache = True
        self.tok.padding_side = "left"
        outs = []
        for i in range(0, len(messages_list), self.max_batch):
            batch = messages_list[i:i + self.max_batch]
            texts = [self.render(m) for m in batch]
            enc = self.tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to(self.device)
            kw = dict(max_new_tokens=max_new,
                      pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
                      do_sample=not greedy)
            if not greedy:
                kw.update(temperature=temperature, top_p=top_p)
            torch.manual_seed(1234 + i)
            ids = self.model.generate(**enc, **kw)
            for j in range(len(batch)):
                outs.append(self.tok.decode(ids[j][enc["input_ids"].shape[1]:], skip_special_tokens=True))
        return outs


def messages_for(task: Task):
    return ([{"role": "system", "content": SYSTEM_PROMPT}] + FEWSHOT +
            [{"role": "user", "content": task.prompt_user}])


# --------------------------------------------------------------------------------------
# LoRA: peft (QLoRA on CUDA / fp32 on CPU) with hand-rolled fallback
# --------------------------------------------------------------------------------------
class HandLoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, r=8, alpha=16, dropout=0.05):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)
        dt = base.weight.dtype
        self.lora_A = nn.Parameter((torch.randn(r, base.in_features, dtype=dt) / math.sqrt(r)))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, dtype=dt))
        self.scale = alpha / r
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        return self.base(x) + self.scale * (self.drop(x) @ self.lora_A.T @ self.lora_B.T)


def build_lora(model, impl: str, targets=("q_proj", "k_proj", "v_proj")):
    """Returns (model, info). peft preferred; hand-rolled wraps named linears in-place."""
    if impl == "peft":
        from peft import LoraConfig, get_peft_model
        cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                         target_modules=list(targets), bias="none", task_type="CAUSAL_LM")
        model = get_peft_model(model, cfg)
        n = sum(p.numel() for p in model.parameters() if p.requires_grad)
        return model, {"impl": "peft", "trainable_params": n}
    # hand-rolled
    wrapped = 0
    for name, module in list(model.named_modules()):
        last = name.split(".")[-1]
        if last in targets and isinstance(module, nn.Linear):
            parent = model
            parts = name.split(".")
            for p in parts[:-1]:
                parent = getattr(parent, p)
            setattr(parent, parts[-1], HandLoRALinear(module))
            wrapped += 1
    n = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return model, {"impl": "handroll", "wrapped_layers": wrapped, "trainable_params": n}


# --------------------------------------------------------------------------------------
# SFT training (loss on completion tokens only)
# --------------------------------------------------------------------------------------
def make_sft_samples(tasks, completions, tok, max_len=448):
    samples = []
    for t, c in zip(tasks, completions):
        prompt_text = tok.apply_chat_template(messages_for(t), tokenize=False, add_generation_prompt=True)
        prompt_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
        comp_ids = tok(c, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
        samples.append((prompt_ids[-(max_len - 32):], comp_ids[: max_len - 32]))
    return samples


def sft_train(model, tok, samples, device, lr=1e-4, epochs=2, batch_size=4, accum=2,
              max_steps=80, seed=20261002, max_len=448):
    rng = random.Random(seed)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)

    def sched_lambda(step):
        if step < 10:
            return step / 10
        p = (step - 10) / max(1, min(max_steps, epochs * math.ceil(len(samples) / batch_size)) - 10)
        return 0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * min(1.0, p)))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, sched_lambda)
    model.train()
    model.config.use_cache = False

    # GPU-seat ramp receipt (WSL2 idle-saturation law): 3 warmup forwards before timing.
    if samples:
        warm = samples[0]
        ids = torch.tensor([warm[0] + warm[1][:64]], device=device)
        for _ in range(3):
            with torch.no_grad():
                model(ids[:, :-1])
        log("[train] ramp receipt: 3 warmup fwd passes done")

    losses, step, done = [], 0, False
    for ep in range(epochs):
        order = list(range(len(samples)))
        rng.shuffle(order)
        micro = [order[i:i + batch_size] for i in range(0, len(order), batch_size)]
        for bi, idxs in enumerate(micro):
            if done:
                break
            seqs, labels = [], []
            for k in idxs:
                p_ids, c_ids = samples[k]
                seqs.append((p_ids + c_ids)[:max_len])
                labels.append(([-100] * len(p_ids) + c_ids)[:max_len])
            L = max(len(s) for s in seqs)
            input_ids = torch.tensor([s + [tok.pad_token_id or tok.eos_token_id] * (L - len(s)) for s in seqs], device=device)
            attn = torch.tensor([[1] * len(s) + [0] * (L - len(s)) for s in seqs], device=device)
            lab = torch.tensor([l + [-100] * (L - len(l)) for l in labels], device=device)
            logits = model(input_ids=input_ids, attention_mask=attn).logits
            loss = F.cross_entropy(logits[:, :-1].float().reshape(-1, logits.shape[-1]),
                                   lab[:, 1:].reshape(-1), ignore_index=-100)
            (loss / accum).backward()
            losses.append(loss.item())
            if (bi + 1) % accum == 0:
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % 20 == 0:
                    log(f"[train] step {step}/{max_steps} loss {sum(losses[-20:]) / len(losses[-20:]):.4f}")
                if step >= max_steps:
                    done = True
        if done:
            break
    model.eval()
    model.config.use_cache = True
    first = losses[:10] or [float("nan")]
    last = losses[-10:] or [float("nan")]
    return {"steps": step, "micro_batches": len(losses),
            "loss_first10": round(sum(first) / len(first), 4),
            "loss_last10": round(sum(last) / len(last), 4)}


# --------------------------------------------------------------------------------------
# Eval
# --------------------------------------------------------------------------------------
def eval_pass1(backend, tasks: list, verifier: Verifier, greedy=True, max_new=200, label=""):
    msgs = [messages_for(t) for t in tasks]
    outs = backend.generate(msgs, greedy=greedy, max_new=max_new)
    ok, per_kind = 0, {}
    for t, o in zip(tasks, outs):
        good, _ = verifier.check(t, o)
        ok += int(good)
        per_kind.setdefault(t.kind, [0, 0])
        per_kind[t.kind][0] += int(good)
        per_kind[t.kind][1] += 1
    res = {
        "n": len(tasks), "pass1": round(ok / max(1, len(tasks)), 4),
        "arith_pass1": None, "symb_pass1": None,
    }
    for k, (g, n) in per_kind.items():
        res[f"{k}_pass1"] = round(g / n, 4)
    if label:
        log(f"[eval:{label}] pass@1 {res['pass1']:.3f} (arith {res['arith_pass1']}, symb {res['symb_pass1']}) n={res['n']}")
    return res


def eval_pass1_ollama(ollama: OllamaBackend, tasks, verifier: Verifier, label=""):
    msgs = [messages_for(t) for t in tasks]
    outs = ollama.chat_many(msgs, temperature=0.0, max_tokens=200, greedy=True)
    ok = sum(int(verifier.check(t, o)[0]) for t, o in zip(tasks, outs) if o is not None)
    n = len(tasks)
    res = {"n": n, "pass1": round(ok / max(1, n), 4), "transport_none": sum(1 for o in outs if o is None)}
    if label:
        log(f"[eval:{label}] ollama pass@1 {res['pass1']:.3f} n={n} (transport failures: {res['transport_none']})")
    return res


# --------------------------------------------------------------------------------------
# Selection (prereg section 7)
# --------------------------------------------------------------------------------------
def select_winners(pairs, verifier: Verifier, max_per_task=2):
    """pairs: list[(Task, list[str|None])] -> winners list[(Task, str)], stats."""
    winners = []
    stats = {"n_gen": 0, "n_verified": 0, "n_tasks_with_winner": 0}
    for t, cands in pairs:
        stats["n_gen"] += len(cands)
        good = [(c, verifier.check(t, c)) for c in cands if c is not None]
        verified = [c for c, (ok, _) in good if ok]
        stats["n_verified"] += len(verified)
        seen, kept = set(), []
        for c in sorted(verified, key=len):
            ans = extract_answer(c)
            if ans in seen:
                continue
            seen.add(ans)
            kept.append(c)
            if len(kept) >= max_per_task:
                break
        if kept:
            stats["n_tasks_with_winner"] += 1
        winners.extend([(t, c) for c in kept])
    return winners, stats


# --------------------------------------------------------------------------------------
# Model loading
# --------------------------------------------------------------------------------------
def pick_device(requested: str, min_free_gb=2.5):
    if requested != "auto":
        return requested, f"requested={requested}"
    if not torch.cuda.is_available():
        return "cpu", "no-cuda"
    free, total = torch.cuda.mem_get_info()
    note = f"free={free / 1e9:.2f}GB/total={total / 1e9:.2f}GB"
    if free / 1e9 >= min_free_gb:
        return "cuda", note
    return "cpu", f"GPU seat busy ({note}) -> serialized to CPU"


def load_policy(hf_model: str, device: str, want_qlora: bool):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(hf_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    mode = "fp32/fp16"
    kwargs = {}
    if device == "cuda" and want_qlora:
        try:
            from transformers import BitsAndBytesConfig
            import bitsandbytes  # noqa: F401
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
            mode = "qlora-nf4"
        except Exception as e:
            log(f"[load] bnb unavailable ({type(e).__name__}); falling back to non-quantized: {e}")
            kwargs["dtype"] = torch.bfloat16
    elif device == "cuda":
        kwargs["dtype"] = torch.bfloat16
    else:
        kwargs["dtype"] = torch.float32
    try:
        model = AutoModelForCausalLM.from_pretrained(hf_model, device_map=device, **kwargs)
    except TypeError:
        dt = kwargs.pop("dtype", None)
        if "quantization_config" in kwargs:
            kwargs.pop("quantization_config")
            mode = "fp32/fp16"
        model = AutoModelForCausalLM.from_pretrained(hf_model, device_map=device, torch_dtype=dt, **kwargs)
    model.eval()
    if mode == "qlora-nf4":
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    return model, tok, mode


# --------------------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------------------
ORACLE_SFT = [  # experimenter-authored demonstrations (C2 control; NOT policy samples)
    ("Compute 128 + 259.", "128 + 259: 8 + 9 = 17 (carry 1), 2 + 5 + 1 = 8, 1 + 2 = 3.\nAnswer: 387"),
    ("Compute 17 * 8.", "17 * 8 = (10 * 8) + (7 * 8) = 80 + 56 = 136.\nAnswer: 136"),
    ("Compute 503 - 268.", "503 - 268: 503 - 200 = 303, then 303 - 68 = 235.\nAnswer: 235"),
    ("Compute (34 + 21) * 5.", "34 + 21 = 55, and 55 * 5 = 275.\nAnswer: 275"),
    ("Compute 23 + 41 + 16.", "23 + 41 = 64, and 64 + 16 = 80.\nAnswer: 80"),
    ("Simplify the expression: (5*x + 7) + (2*x - 3). Give the result in terms of x.",
     "Like terms: 5*x + 2*x = 7*x, and 7 - 3 = 4.\nAnswer: 7*x + 4"),
    ("Simplify the expression: (6*x + 9) - (2*x + 5). Give the result in terms of x.",
     "6*x - 2*x = 4*x, and 9 - 5 = 4.\nAnswer: 4*x + 4"),
    ("Simplify the expression: 3*(x + 4) + 2*x. Give the result in terms of x.",
     "3*(x + 4) = 3*x + 12; adding 2*x gives 5*x + 12.\nAnswer: 5*x + 12"),
]


def oracle_tasks():
    out = []
    for i, (q, a) in enumerate(ORACLE_SFT):
        if q.startswith("Compute"):
            fam = "oracle"
            expr = q[len("Compute "):].rstrip(".")
            tgt = str(expand(simplify(sym(expr))))
            t = Task(9000 + i, "arith", fam, expr, q, tgt, None)
        else:
            expr = q.split("expression: ")[1].split(". Give")[0]
            e = expand(simplify(sym(expr)))
            t = Task(9000 + i, "symb", "oracle", expr, q, str(e), e)
        out.append((t, a))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--train-pool", type=int, default=24)
    ap.add_argument("--heldout", type=int, default=16)
    ap.add_argument("--n-cand", type=int, default=4)
    ap.add_argument("--max-steps", type=int, default=80)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lora-impl", choices=["auto", "peft", "handroll"], default="auto")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    ap.add_argument("--hf-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--ollama-model", default="qwen2.5:0.5b")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--seed", type=int, default=20261002)
    ap.add_argument("--seed-heldout", type=int, default=20261003)
    ap.add_argument("--seed-shuffle-probe", type=int, default=20261004)
    ap.add_argument("--out-json", default="results/rest_em_smoke.json")
    ap.add_argument("--adapter-dir", default="results/rest_em_adapter")
    ap.add_argument("--parity-n", type=int, default=8)
    ap.add_argument("--skip-parity", action="store_true")
    ap.add_argument("--skip-ollama", action="store_true", help="force HF for round 0 (deviation logged)")
    ap.add_argument("--with-controls", action="store_true")
    ap.add_argument("--max-new", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--difficulty", choices=["registered", "hard"], default="registered",
                    help="hard = Amendment A1 (2026-10-02) frozen harder distribution")
    ap.add_argument("--selftest-only", action="store_true")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    verifier = Verifier()

    # ---- verifier negative-control self-test (aborts run on failure) ----
    st = verifier.self_test()
    log(f"[verifier] self-test: accepts {st['n_accept_cases'] - len(st['accept_failures'])}/{st['n_accept_cases']} "
        f"correct, rejects {st['n_reject_cases'] - len(st['reject_failures'])}/{st['n_reject_cases']} wrong "
        f"-> {'PASS' if st['passed'] else 'FAIL'}")
    if not st["passed"]:
        log(f"[verifier] failures: {st['accept_failures']} {st['reject_failures']}")
        sys.exit(2)
    if args.selftest_only:
        pool = gen_task_pool(args.seed, 12, 12, difficulty=args.difficulty)
        held = gen_task_pool(args.seed_heldout, 8, 8, start_tid=10000)
        overlap = {t.expr for t in pool} & {t.expr for t in held}
        log(f"[selftest-only] pool/heldout overlap: {overlap or 'none'}")
        log("[selftest-only] sample tasks: " + " | ".join(f"{t.family}:{t.expr}=>{t.target_str}" for t in pool[:4]))
        return

    # ---- tasks + contamination check (N4) ----
    n_ar, n_sy = args.train_pool // 2, args.train_pool // 2
    h_ar, h_sy = args.heldout // 2, args.heldout // 2
    train_pool = gen_task_pool(args.seed, n_ar, n_sy, difficulty=args.difficulty)
    heldout = gen_task_pool(args.seed_heldout, h_ar, h_sy, start_tid=10000, difficulty=args.difficulty)
    overlap = {t.expr for t in train_pool} & {t.expr for t in heldout}
    log(f"[tasks] pool={len(train_pool)} heldout={len(heldout)} contamination_overlap={len(overlap)}")
    if overlap:
        log(f"[tasks] CONTAMINATION: {overlap} — aborting per prereg N4")
        sys.exit(2)

    out = {"config": vars(args), "honest_notes": [], "rounds": [], "controls": {}}

    # ---- device + policy model ----
    device, dev_note = pick_device(args.device)
    log(f"[device] {device} ({dev_note})")
    want_qlora = device == "cuda"
    model, tok, load_mode = load_policy(args.hf_model, device, want_qlora)
    impl = "peft" if (args.lora_impl == "auto" or args.lora_impl == "peft") else "handroll"
    try:
        model, lora_info = build_lora(model, impl)
    except Exception as e:
        log(f"[lora] peft path failed ({type(e).__name__}: {e}) -> hand-rolled fallback")
        model, lora_info = build_lora(model, "handroll")
        out["honest_notes"].append(f"peft unavailable ({e}); hand-rolled LoRA used")
    log(f"[load] {args.hf_model} mode={load_mode} lora={lora_info}")
    hf = HFBackend(model, tok, device)

    ollama = OllamaBackend(args.ollama_url, args.ollama_model, workers=args.workers)
    use_ollama_r0 = not args.skip_ollama

    # ---- base eval (held-out, greedy, HF policy) ----
    base_eval = eval_pass1(hf, heldout, verifier, label="base-hf")
    out["base_eval_hf"] = base_eval

    # ---- ollama parity check (prereg section 3) ----
    if not args.skip_parity:
        sub = heldout[: args.parity_n]
        par = eval_pass1_ollama(ollama, sub, verifier, label="base-ollama-parity")
        out["parity_ollama"] = par
        gap = abs(par["pass1"] - eval_pass1(hf, sub, verifier, label="parity-hf-subset")["pass1"])
        out["parity_gap_abs"] = round(gap, 4)
        log(f"[parity] |ollama - hf| = {gap:.3f} (registered tolerance 0.12)")
        if gap > 0.12 + 1e-9:
            use_ollama_r0 = False
            out["honest_notes"].append(f"parity gap {gap:.3f} > 0.12: round-0 generation moved to HF (registered fallback)")

    # ---- C2 oracle-SFT control (before treatment rounds? after; keep adapter slots separate) ----
    def run_round(r: int):
        """One ReST-EM cycle: generate -> verify -> select -> train -> eval."""
        backend_note = "ollama(base twin)" if (r == 0 and use_ollama_r0) else "hf(current policy)"
        log(f"[round {r}] generate via {backend_note}, n_cand={args.n_cand}")
        cand_by_task = {}
        transport_fail = 0
        if r == 0 and use_ollama_r0:
            msgs_all, index = [], []
            for t in train_pool:
                for _ in range(args.n_cand):
                    msgs_all.append(messages_for(t))
                    index.append(t.tid)
            outs = ollama.chat_many(msgs_all, temperature=0.8, max_tokens=args.max_new)
            transport_fail = sum(1 for o in outs if o is None)
            by_tid = {}
            for tid, o in zip(index, outs):
                by_tid.setdefault(tid, []).append(o)
            # HF top-up only for transport-failed tasks (same base policy; logged)
            topup = [t for t in train_pool if all(o is None for o in by_tid[t.tid])]
            if topup:
                log(f"[round {r}] ollama transport failures: {transport_fail}; HF base top-up for {len(topup)} tasks")
                out["honest_notes"].append(f"round {r}: {len(topup)} tasks topped up from HF base after ollama transport failures")
                for t in topup:
                    msgs = [messages_for(t)] * args.n_cand
                    gens = hf.generate(msgs, greedy=False, temperature=0.8, max_new=args.max_new)
                    by_tid[t.tid] = gens
            pairs = [(t, by_tid[t.tid]) for t in train_pool]
        else:
            pairs = []
            for i in range(0, len(train_pool), 8):
                chunk = train_pool[i:i + 8]
                msgs = []
                for t in chunk:
                    msgs.extend([messages_for(t)] * args.n_cand)
                gens = hf.generate(msgs, greedy=False, temperature=0.8, max_new=args.max_new)
                k = 0
                for t in chunk:
                    pairs.append((t, gens[k:k + args.n_cand]))
                    k += args.n_cand

        winners, gstats = select_winners(pairs, verifier)
        win_tasks = [w[0] for w in winners]
        win_texts = [w[1] for w in winners]
        log(f"[round {r}] gen={gstats['n_gen']} verified={gstats['n_verified']} "
            f"({gstats['n_verified'] / max(1, gstats['n_gen']):.1%}) winners={len(winners)} "
            f"tasks_covered={gstats['n_tasks_with_winner']}/{len(train_pool)} transport_fail={transport_fail}")
        if len(winners) < 3:
            out["honest_notes"].append(f"round {r} aborted: <3 winners")
            return None
        samples = make_sft_samples(win_tasks, win_texts, tok)
        free_note = ""
        if device == "cuda":
            free, _ = torch.cuda.mem_get_info()
            free_note = f" (vram_free={free / 1e9:.2f}GB before train)"
        log(f"[round {r}] SFT on {len(samples)} winner samples{free_note}")
        tr = sft_train(model, tok, samples, device, lr=args.lr, epochs=args.epochs,
                       batch_size=args.batch_size, accum=args.grad_accum,
                       max_steps=args.max_steps, seed=args.seed + r)
        log(f"[round {r}] train done: {tr}")
        ev = eval_pass1(hf, heldout, verifier, label=f"round{r}-post")
        return {"round": r, "gen_backend": backend_note, "gen": gstats["n_gen"],
                "verified": gstats["n_verified"], "verified_rate": round(gstats["n_verified"] / max(1, gstats["n_gen"]), 4),
                "winners": len(winners), "train": tr, "heldout_pass1_post": ev["pass1"],
                "heldout_detail": ev}

    # ================= treatment arm =================
    prev = base_eval["pass1"]
    for r in range(args.rounds):
        res = run_round(r)
        if res is None:
            break
        res["heldout_pass1_pre"] = prev
        res["delta"] = round(res["heldout_pass1_post"] - prev, 4)
        log(f"[round {r}] held-out pass@1 {prev:.3f} -> {res['heldout_pass1_post']:.3f} "
            f"(Δ {res['delta']:+.3f})")
        prev = res["heldout_pass1_post"]
        out["rounds"].append(res)
        # save adapter snapshot
        try:
            ad = Path(args.adapter_dir + f"_r{r}")
            ad.mkdir(parents=True, exist_ok=True)
            if lora_info["impl"] == "peft":
                model.save_pretrained(str(ad))
            else:
                sd = {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad}
                torch.save(sd, ad / "handroll_lora.pt")
        except Exception as e:
            out["honest_notes"].append(f"adapter save r{r} failed: {e}")

    cycles = len(out["rounds"])
    out["summary"] = {
        "cycles_completed": cycles,
        "pass1_base": base_eval["pass1"],
        "pass1_final": out["rounds"][-1]["heldout_pass1_post"] if out["rounds"] else None,
        "delta_total": round((out["rounds"][-1]["heldout_pass1_post"] - base_eval["pass1"]), 4) if out["rounds"] else None,
        "verifier_selftest_passed": st["passed"],
        "device": device, "device_note": dev_note, "load_mode": load_mode, "lora": lora_info,
    }

    # ================= mini controls (code-path exercise; smoke only) =================
    if args.with_controls and cycles >= 1:
        # C1: no-finetune — generate/verify/select bookkeeping, no training; eval must stay ~flat
        try:
            pool_c1 = train_pool[: max(4, len(train_pool) // 2)]
            pairs_c1 = []
            for i in range(0, len(pool_c1), 8):
                chunk = pool_c1[i:i + 8]
                msgs = []
                for t in chunk:
                    msgs.extend([messages_for(t)] * 2)
                gens = hf.generate(msgs, greedy=False, temperature=0.8, max_new=args.max_new)
                k = 0
                for t in chunk:
                    pairs_c1.append((t, gens[k:k + 2]))
                    k += 2
            _, gs = select_winners(pairs_c1, verifier)
            ev_c1 = eval_pass1(hf, heldout, verifier, label="C1-noft-eval(current-adapter-in-process)")
            out["controls"]["C1_no_finetune"] = {"gen_stats": gs, "heldout_pass1": ev_c1["pass1"],
                                                 "note": "IN-PROCESS SMOKE ONLY: this eval reflects the adapter trained by the "
                                                         "treatment rounds (same process) — NOT the base. Gen/selection stats are "
                                                         "the valid part. Full run must execute C1 in a separate fresh process."}
        except Exception as e:
            out["controls"]["C1_no_finetune"] = {"error": repr(e)}

        # C2: oracle-SFT one-shot (experimenter-authored), matched budget
        try:
            ot = oracle_tasks()
            base_c2 = eval_pass1(hf, heldout, verifier, label="C2-oracle-pre").copy()
            samples = make_sft_samples([t for t, _ in ot], [a for _, a in ot], tok)
            tr = sft_train(model, tok, samples, device, lr=args.lr, epochs=3,
                           batch_size=args.batch_size, accum=args.grad_accum,
                           max_steps=30, seed=args.seed_shuffle_probe)
            ev_c2 = eval_pass1(hf, heldout, verifier, label="C2-oracle-post")
            out["controls"]["C2_oracle_sft"] = {"train": tr, "pre": base_c2["pass1"], "post": ev_c2["pass1"],
                                                "note": "one-shot SFT on 8 authored demos; NOTE: pollutes the treatment adapter (smoke only)"}
            out["honest_notes"].append("C2 control trained on the SAME adapter slot after treatment rounds — "
                                       "its post-treatment numbers are contaminated for gate purposes (smoke-only exercise)")
        except Exception as e:
            out["controls"]["C2_oracle_sft"] = {"error": repr(e)}

    out["honest_notes"].append("smoke run = engineering validation; gate (prereg §8) applies only to the full run")
    out["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")

    p = Path(args.out_json)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str))
    log(f"[done] cycles={cycles} base={out['summary']['pass1_base']} final={out['summary']['pass1_final']} "
        f"Δ={out['summary']['delta_total']} -> {p}")


if __name__ == "__main__":
    main()
