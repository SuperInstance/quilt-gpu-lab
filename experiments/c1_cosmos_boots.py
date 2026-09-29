#!/usr/bin/env python3
"""C1 — Cosmos 3 Edge boots test on the RTX 4050.

Pre-registered: proposals/runs/C1-cosmos-edge-boots-plan.md (frozen gate:
KEEP = 48-token greedy generation completes on 6 GB under guard via NF4;
KILL = OOM/crash on NF4 and one honest bf16+offload fallback).

Two-stage: the outer stage runs the inner stage under guard.Guard (VRAM/thermal
watchdog). Weights stay in the HF cache (never in git).
"""
import json, os, subprocess, sys, time, traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c1_cosmos_boots.json")
MODEL_ID = "nvidia/Cosmos3-Edge"
PROMPT = ("You are a deckhand on a fishing vessel in Alaska. In three short "
          "sentences, what should you watch for on deck right now?")
MAX_NEW = 48

def inner() -> dict:
    import torch
    from transformers import BitsAndBytesConfig

    t0 = time.time()
    try:
        from transformers import Cosmos3EdgeForConditionalGeneration as M
    except ImportError:
        from transformers.models.cosmos3_edge.modeling_cosmos3_edge import \
            Cosmos3EdgeForConditionalGeneration as M
    try:
        from transformers import AutoProcessor
        proc = AutoProcessor.from_pretrained(MODEL_ID)
        proc_path = "AutoProcessor"
    except Exception as e:
        print(f"[C1] AutoProcessor failed ({e}); direct class fallback", flush=True)
        from transformers.models.cosmos3_edge.processing_cosmos3_edge import \
            Cosmos3EdgeProcessor
        proc = Cosmos3EdgeProcessor.from_pretrained(MODEL_ID)
        proc_path = "Cosmos3EdgeProcessor"
    t_proc = time.time() - t0

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16)
    t1 = time.time()
    model = M.from_pretrained(MODEL_ID, quantization_config=quant,
                              device_map="auto", torch_dtype=torch.bfloat16)
    t_load = time.time() - t1
    model.eval()
    dmap = getattr(model, "hf_device_map", None)
    if not dmap:
        dmap = getattr(getattr(model, "model", None), "hf_device_map", None) or {}
    print(f"[C1] loaded nf4 in {t_load:.1f}s; device_map head:",
          {k: str(v) for k, v in list(dmap.items())[:4]}, flush=True)

    torch.cuda.reset_peak_memory_stats()
    built = {"prompt": PROMPT, "pixels": "none", "proc_path": proc_path}
    msgs = [{"role": "user", "content": [{"type": "text", "text": PROMPT}]}]
    try:
        chat_text = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        inputs = proc(text=[chat_text] if isinstance(chat_text, str) else chat_text,
                      return_tensors="pt")
        built["input_mode"] = "chat_template"
    except Exception as e:
        print(f"[C1] chat-template call failed ({e}); raw-text fallback", flush=True)
        try:
            inputs = proc(text=[PROMPT], return_tensors="pt")
            built["input_mode"] = "raw_text"
        except Exception as e2:
            print(f"[C1] raw-text call failed ({e2}); using repo example image", flush=True)
            from PIL import Image
            from huggingface_hub import hf_hub_download
            img_path = hf_hub_download(MODEL_ID, "assets/example_reasoning_input.png")
            inputs = proc(text=[PROMPT], images=[Image.open(img_path).convert("RGB")],
                          return_tensors="pt")
            built["pixels"] = "assets/example_reasoning_input.png"
            built["input_mode"] = "image+text"
    inputs = {k: v for k, v in inputs.items() if v is not None}
    inputs = {k: (v.to(model.device) if hasattr(v, "to") else v)
              for k, v in inputs.items()}

    t2 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW, do_sample=False)
    t_gen = time.time() - t2
    n_new = int(out.shape[-1] - inputs["input_ids"].shape[-1])
    try:
        text = proc.batch_decode(out[:, inputs["input_ids"].shape[-1]:],
                                 skip_special_tokens=True)[0]
    except AttributeError:
        text = proc.tokenizer.batch_decode(out[:, inputs["input_ids"].shape[-1]:],
                                           skip_special_tokens=True)[0]

    peak_alloc = torch.cuda.max_memory_allocated() / 2**30
    free, tot = torch.cuda.mem_get_info()
    return {**built, "verdict_stage": "generated",
            "t_proc_s": round(t_proc, 2), "t_load_s": round(t_load, 2),
            "t_gen_s": round(t_gen, 2), "n_new_tokens": n_new,
            "decode_tok_s": round(n_new / max(t_gen, 1e-9), 2),
            "peak_alloc_gib": round(peak_alloc, 2),
            "vram_used_gib": round((tot - free) / 2**30, 2),
            "gen_text": text}

def main() -> None:
    os.makedirs(RESULTS, exist_ok=True)
    if "--inner" in sys.argv:
        try:
            res = inner()
            res["verdict"] = "KEEP" if res.get("n_new_tokens", 0) >= 32 else "SHORT"
        except Exception:
            print("[C1] INNER FAILED", flush=True); traceback.print_exc()
            res = {"verdict": "KILL", "verdict_stage": "exception",
                   "traceback_tail": traceback.format_exc()[-1500:]}
        json.dump(res, open(OUT_JSON, "w"), indent=1)
        print("[C1] INNER_DONE", json.dumps({k: v for k, v in res.items()
              if k != "gen_text"})[:900], flush=True)
        if "gen_text" in res: print(f"[C1] GEN: {res['gen_text']}", flush=True)
        return

    sys.path.insert(0, LAB)
    import guard
    g = guard.Guard(timeout_s=1800.0)
    if not g.preflight():
        json.dump({"verdict": "ABORTED_GUARD_PREFLIGHT", "breach": g.breach},
                  open(OUT_JSON, "w"), indent=1)
        print(f"[C1] GUARD PREFLIGHT FAIL: {g.breach}", flush=True); sys.exit(2)
    rc, so, se = g.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       cwd=LAB, env=dict(os.environ))
    tail = {"returncode": rc, "guard_breach": g.breach, "guard_timed_out": g.timed_out,
            "peak_temp_c": max((t for _, _, t in g.samples if t is not None), default=None),
            "min_free_mib": min((f for _, f, _ in g.samples if f is not None), default=None)}
    print(f"[C1] guard rc={rc} breach={g.breach} tail={tail}", flush=True)
    print("[C1] stderr tail:", se[-600:], flush=True)
    if rc != 0 and os.path.exists(OUT_JSON):
        cur = json.load(open(OUT_JSON)); cur.update(tail); json.dump(cur, open(OUT_JSON, "w"), indent=1)
    print("[C1] DONE", flush=True)

if __name__ == "__main__":
    main()
