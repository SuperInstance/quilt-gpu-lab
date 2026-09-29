#!/usr/bin/env python3
"""C2 — first real video through the 4050's world model (smoke).

Pre-registered: proposals/runs/C2-world-smoke-plan.md. Two frozen tasks
(V-task: 8 frames from the repo's example AV clip; I-task: example reasoning
image) with anticipation questions. Gate: >= 1 of 2 tasks completes with
>= 24 new tokens of scene-relevant text. Throughput numbers book regardless.
Same NF4 loader as C1, two-stage guard wrapper.
"""
import json, os, subprocess, sys, time, traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c2_world_smoke.json")
MODEL_ID = "nvidia/Cosmos3-Edge"
FFMPEG = "/home/eileen/.local/bin/ffmpeg"
SNAP = "/home/eileen/.cache/huggingface/hub/models--nvidia--Cosmos3-Edge/snapshots/344d602b128d1bbdacb43b08d0a3626f46343e29"
MAX_NEW = 64
PROMPT_V = "Watch this clip. What is happening, and what is most likely to happen next?"
PROMPT_I = "What is happening in this image? What is most likely to happen next?"

def grab_frames(tmpdir):
    mp4 = os.path.join(SNAP, "assets", "example_action_id_av_0_input.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp4,
                    "-vf", "fps=1,scale=640:-2",
                    os.path.join(tmpdir, "f_%03d.png")], check=True)
    from PIL import Image
    files = sorted(f for f in os.listdir(tmpdir) if f.endswith(".png"))[:8]
    return [Image.open(os.path.join(tmpdir, f)).convert("RGB") for f in files]

def run_task(model, proc, prompt, task, placeholder, frames=None, image=None):
    import torch
    msgs = [{"role": "user", "content": [{"type": placeholder},
            {"type": "text", "text": prompt}]}]
    chat = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    path = None
    if frames is not None:
        try:
            inputs = proc(text=[chat], videos=[frames], return_tensors="pt")
            path = "videos=[8 frames]"
        except Exception as e:
            print(f"[C2] videos path failed ({e}); multi-image fallback", flush=True)
            inputs = proc(text=[chat], images=frames, return_tensors="pt")
            path = "images=[8 frames]"
    else:
        inputs = proc(text=[chat], images=[image], return_tensors="pt")
        path = "images=[1 example png]"
    inputs = {k: v for k, v in inputs.items() if v is not None}
    inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    n_in = int(inputs["input_ids"].shape[-1])
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW, do_sample=False)
    t_gen = time.time() - t0
    n_new = int(out.shape[-1] - n_in)
    try:
        text = proc.batch_decode(out[:, n_in:], skip_special_tokens=True)[0]
    except AttributeError:
        text = proc.tokenizer.batch_decode(out[:, n_in:], skip_special_tokens=True)[0]
    return {"task": task, "path": path, "input_tokens": n_in,
            "n_new_tokens": n_new, "t_gen_s": round(t_gen, 2),
            "decode_tok_s": round(n_new / max(t_gen, 1e-9), 2),
            "text": text}

def inner() -> dict:
    import torch
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

    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        frames = grab_frames(td)
    img = Image.open(os.path.join(SNAP, "assets", "example_reasoning_input.png")).convert("RGB")

    v = run_task(model, proc, PROMPT_V, "V-task (8 frames, anticipation)", "video", frames=frames)
    torch.cuda.reset_peak_memory_stats()
    i = run_task(model, proc, PROMPT_I, "I-task (example png, anticipation)", "image", image=img)
    peak = torch.cuda.max_memory_allocated() / 2**30
    free, tot = torch.cuda.mem_get_info()
    return {"t_load_s": round(t_load, 2), "v": v, "i": i,
            "peak_alloc_gib_i_task": round(peak, 2),
            "vram_used_gib": round((tot - free) / 2**30, 2),
            "verdict_stage": "generated",
            "verdict": "KEEP" if (v["n_new_tokens"] >= 24 or i["n_new_tokens"] >= 24) else "KILL"}

def main() -> None:
    os.makedirs(RESULTS, exist_ok=True)
    if "--inner" in sys.argv:
        try:
            res = inner()
        except Exception:
            print("[C2] INNER FAILED", flush=True); traceback.print_exc()
            res = {"verdict": "KILL", "verdict_stage": "exception",
                   "traceback_tail": traceback.format_exc()[-1500:]}
        json.dump(res, open(OUT_JSON, "w"), indent=1)
        print("[C2] INNER_DONE", json.dumps({k: v for k, v in res.items()
              if k not in ("v", "i")})[:400], flush=True)
        for t in ("v", "i"):
            if t in res: print(f"[C2] {t}: {res[t]['n_new_tokens']} tok @ {res[t]['decode_tok_s']} tok/s via {res[t]['path']}\n[C2] text: {res[t]['text'][:500]}", flush=True)
        return
    sys.path.insert(0, LAB)
    import guard
    g = guard.Guard(timeout_s=1800.0)
    if not g.preflight():
        json.dump({"verdict": "ABORTED_GUARD_PREFLIGHT", "breach": g.breach},
                  open(OUT_JSON, "w"), indent=1)
        print(f"[C2] GUARD PREFLIGHT FAIL: {g.breach}", flush=True); sys.exit(2)
    rc, so, se = g.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       cwd=LAB, env=dict(os.environ))
    print(f"[C2] guard rc={rc} breach={g.breach}", flush=True)
    if rc != 0:
        print("[C2] stderr tail:", se[-500:], flush=True)
        if os.path.exists(OUT_JSON):
            cur = json.load(open(OUT_JSON))
            cur.update({"returncode": rc, "guard_breach": g.breach})
            json.dump(cur, open(OUT_JSON, "w"), indent=1)
    print("[C2] DONE", flush=True)

if __name__ == "__main__":
    main()
