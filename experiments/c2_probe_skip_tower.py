#!/usr/bin/env python3
"""C2 attempt-5 — skip-tower isolation: vision tower + projector in bf16,
LM in NF4.

Pre-registered: proposals/runs/C2-attempt5-plan.md (frozen).
attempt-4 localized the poison to vision-token injection under NF4.
This run asks WHERE: quantized tower/projector, or the LM pathway.

Cells (repo example prompt verbatim, greedy, MAX_NEW=96):
  A2 text-only + thinking   (control — must stay coherent or INVALID_HARNESS)
  B2 image    + no-thinking
  Q  image    + thinking    (the question cell)
Gate (frozen in plan): KEEP if Q >= 24 new tokens of scene-relevant text
(no digit-cycle loop) AND A2 coherent. Receipt records visual dtype —
if not bf16, verdict INVALID_HARNESS.
List-form subprocess only (house law). Output: results/c2_probe_skip_tower.json
"""
import json, os, subprocess, sys, time, traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c2_probe_skip_tower.json")
MODEL_ID = "nvidia/Cosmos3-Edge"
SNAP = "/home/eileen/.cache/huggingface/hub/models--nvidia--Cosmos3-Edge/snapshots/344d602b128d1bbdacb43b08d0a3626f46343e29"
MAX_NEW = 96
SKIP_MODULES = ["visual", "projector", "model.visual", "model.projector"]
# visual/projector live on the INNER Cosmos3EdgeModel (modeling_cosmos3_edge
# line ~777: self.visual/self.projector in Cosmos3EdgeModel.__init__), and
# transformers bnb skip-matching may want either the short or qualified name.


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


def verdict_of(cells_by_name):
    q = cells_by_name["Q"]
    a = cells_by_name["A2"]
    a_coherent = a["n_new_tokens"] >= 24 and a["loop_frac"] < 0.25
    q_relevant = q["n_new_tokens"] >= 24 and q["loop_frac"] < 0.25 and \
        any(w in q["text"].lower() for w in ("flower", "bottle", "step",
                                             "plan", "task", "pick", "place"))
    if a_coherent and q_relevant:
        return "KEEP"
    if a_coherent:
        return "KILL-localization-keep"  # LM pathway implicated; science stands
    return "INVALID_HARNESS"


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
                               bnb_4bit_compute_dtype=torch.bfloat16,
                               llm_int8_skip_modules=SKIP_MODULES)
    t0 = time.time()
    model = M.from_pretrained(MODEL_ID, quantization_config=quant,
                              device_map="auto", torch_dtype=torch.bfloat16)
    model.eval()
    t_load = time.time() - t0
    m = getattr(model, "model", model)
    visual = getattr(model, "visual", None) or m.visual
    p0 = next(visual.parameters())
    visual_dtype = str(p0.dtype)
    visual_type = type(p0).__name__  # Parameter = not quantized; Params4bit = skip failed
    torch.cuda.reset_peak_memory_stats()
    with open(os.path.join(SNAP, "assets", "example_reasoning_prompt.json")) as f:
        prompt_i = json.load(f)["prompt"]
    img = Image.open(os.path.join(SNAP, "assets",
                     "example_reasoning_input.png")).convert("RGB")
    a2 = cell(model, proc, prompt_i, "A2-text-thinking", None, thinking=True)
    torch.cuda.empty_cache()
    b2 = cell(model, proc, prompt_i, "B2-image-nothink", "image",
              image=img, thinking=False)
    torch.cuda.empty_cache()
    q = cell(model, proc, prompt_i, "Q-image-thinking-towerbf16", "image",
             image=img, thinking=True)
    peak = torch.cuda.max_memory_allocated() / 2**30
    cells_by_name = {"A2": a2, "B2": b2, "Q": q}
    verdict = verdict_of(cells_by_name) if (visual_dtype == "torch.bfloat16"
                                            and visual_type == "Parameter") \
        else "INVALID_HARNESS"
    return {"t_load_s": round(t_load, 2),
            "skip_modules": SKIP_MODULES, "visual_dtype": visual_dtype,
            "visual_type": visual_type,
            "cells": [a2, b2, q],
            "peak_alloc_gib": round(peak, 2), "max_new": MAX_NEW,
            "verdict_stage": "gated", "verdict": verdict}


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
        print("[P5] INNER_DONE", flush=True)
        return
    pf = preflight()
    print(f"[P5] preflight {pf}", flush=True)
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       capture_output=True, text=True)
    print("[P5] guard rc=%d" % r.returncode, flush=True)
    if r.stderr:
        print("[P5] stderr tail:", r.stderr[-400:], flush=True)
    try:
        with open(OUT_JSON) as f:
            d = json.load(f)
    except Exception as e:
        print("[P5] no results json:", e, flush=True)
        return
    print("[P5] visual_dtype=%s visual_type=%s verdict=%s"
          % (d.get("visual_dtype"), d.get("visual_type"), d.get("verdict")),
          flush=True)
    for c in d.get("cells", []):
        print("[P5] %s in=%d new=%d tok/s=%s loop_frac=%s"
              % (c["cell"], c["input_tokens"], c["n_new_tokens"],
                 c["decode_tok_s"], c["loop_frac"]), flush=True)
        print("[P5]   text: %s" % c["text"][:200].replace("\n", " "),
              flush=True)
    print("[P5] DONE", flush=True)


if __name__ == "__main__":
    main()
