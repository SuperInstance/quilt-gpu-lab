#!/usr/bin/env python3
"""C2 attempt-4 — vision-path isolation probe (descriptive, no science gate).

Question: C1 text-only was coherent under NF4; all vision tasks garble.
Sampler exonerated in attempt-3 (repo prompt + full sampling still loops).
Cells (all greedy, MAX_NEW=96, repo example prompt verbatim):
  A text-only + enable_thinking=True   (C1-coherence reproduction)
  B image    + enable_thinking=False
  C image    + enable_thinking=True
Localization: whichever flip restores coherence names the poison
(vision-token injection vs thinking flag vs quantization ceiling).
Verbatim texts + a repetition metric booked; verdict judged in booking.
List-form subprocess only (house law). Output: results/c2_probe_vision_path.json
"""
import json, os, subprocess, sys, time, traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c2_probe_vision_path.json")
MODEL_ID = "nvidia/Cosmos3-Edge"
SNAP = "/home/eileen/.cache/huggingface/hub/models--nvidia--Cosmos3-Edge/snapshots/344d602b128d1bbdacb43b08d0a3626f46343e29"
MAX_NEW = 96


def preflight():
    out = subprocess.run(["/usr/lib/wsl/lib/nvidia-smi",
                          "--query-gpu=memory.free,temperature.gpu",
                          "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    free, temp = [int(x.strip()) for x in out.strip().split(",")]
    assert free >= 1024, f"guard: free VRAM {free}MiB < 1024"
    assert temp <= 80, f"guard: temp {temp}C > 80"
    return {"free_mib": free, "temp_c": temp}


def shingle_loop_frac(text, n=3):
    words = text.split()
    if len(words) < n + 3:
        return 0.0
    from collections import Counter
    c = Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))
    return round(c.most_common(1)[0][1] / max(1, len(words) - n + 1), 3)


def cell(model, proc, prompt, name, placeholder, image=None, thinking=True):
    import torch
    content = ([{"type": placeholder}] if placeholder else []) + \
              [{"type": "text", "text": prompt}]
    msgs = [{"role": "user", "content": content}]
    chat = proc.apply_chat_template(msgs, add_generation_prompt=True,
                                    tokenize=False, enable_thinking=thinking)
    kwargs = {"text": [chat]}
    if image is not None:
        kwargs["images"] = [image]
    inputs = proc(**kwargs, return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, do_sample=False, max_new_tokens=MAX_NEW)
    t_gen = time.time() - t0
    new = out[0][inputs["input_ids"].shape[1]:]
    text = proc.decode(new, skip_special_tokens=True)
    n_new = int(new.shape[0])
    return {"cell": name, "placeholder": placeholder or "none",
            "thinking": thinking,
            "input_tokens": int(inputs["input_ids"].shape[1]),
            "n_new_tokens": n_new, "t_gen_s": round(t_gen, 2),
            "decode_tok_s": round(n_new / max(t_gen, 1e-6), 2),
            "loop_frac": shingle_loop_frac(text), "text": text}


def inner():
    import torch
    from PIL import Image
    from transformers import AutoProcessor, BitsAndBytesConfig
    try:
        from transformers import Cosmos3EdgeForConditionalGeneration as M
    except ImportError:
        from transformers.models.cosmos3_edge.modeling_cosmos3_edge import \
            Cosmos3EdgeForConditionalGeneration as M
    proc = AutoProcessor.from_pretrained(MODEL_ID)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16)
    t0 = time.time()
    model = M.from_pretrained(MODEL_ID, quantization_config=quant,
                              device_map="auto", torch_dtype=torch.bfloat16)
    model.eval()
    t_load = time.time() - t0
    torch.cuda.reset_peak_memory_stats()
    with open(os.path.join(SNAP, "assets", "example_reasoning_prompt.json")) as f:
        prompt_i = json.load(f)["prompt"]
    img = Image.open(os.path.join(SNAP, "assets",
                     "example_reasoning_input.png")).convert("RGB")
    a = cell(model, proc, prompt_i, "A-text-thinking", None, thinking=True)
    torch.cuda.empty_cache()
    b = cell(model, proc, prompt_i, "B-image-nothink", "image",
             image=img, thinking=False)
    torch.cuda.empty_cache()
    c = cell(model, proc, prompt_i, "C-image-thinking", "image",
             image=img, thinking=True)
    peak = torch.cuda.max_memory_allocated() / 2**30
    return {"t_load_s": round(t_load, 2), "cells": [a, b, c],
            "peak_alloc_gib": round(peak, 2), "max_new": MAX_NEW,
            "verdict_stage": "descriptive-probe", "verdict": "BOOK"}


def main():
    os.makedirs(RESULTS, exist_ok=True)
    if "--inner" in sys.argv:
        try:
            res = {"preflight": preflight(), **inner(), "done": True}
        except Exception:
            res = {"verdict": "KILL", "verdict_stage": "exception",
                   "traceback_tail": traceback.format_exc()[-1500:],
                   "done": True}
        with open(OUT_JSON, "w") as f:
            json.dump(res, f, indent=1)
        print("[P4] INNER_DONE", flush=True)
        return
    pf = preflight()
    print(f"[P4] preflight {pf}", flush=True)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       capture_output=True, text=True)
    print("[P4] guard rc=%d" % r.returncode, flush=True)
    if r.stderr:
        print("[P4] stderr tail:", r.stderr[-500:], flush=True)
    try:
        with open(OUT_JSON) as f:
            d = json.load(f)
    except Exception as e:
        print("[P4] no results json:", e, flush=True)
        return
    print("[P4] verdict=%s" % d.get("verdict"), flush=True)
    for c in d.get("cells", []):
        print("[P4] %s in=%d new=%d tok/s=%s loop_frac=%s"
              % (c["cell"], c["input_tokens"], c["n_new_tokens"],
                 c["decode_tok_s"], c["loop_frac"]), flush=True)
        print("[P4]   text: %s" % c["text"][:200].replace("\n", " "),
              flush=True)
    print("[P4] DONE", flush=True)


if __name__ == "__main__":
    main()
