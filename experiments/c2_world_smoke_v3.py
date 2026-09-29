#!/usr/bin/env python3
"""C2v3 — degenerate-output fix: sample per the model's shipped config and
use the repo's own example prompt pairing.

Pre-registered delta: proposals/runs/C2-attempt3-plan.md (frozen vs attempt-2).
Changes: (1) do_sample=True, temperature=1.0, top_p=1.0, top_k=50,
repetition_penalty=1.0 (generation_config.json says do_sample=true; the four
numerics are absent there -> pinned to GenerationConfig defaults explicitly),
seed 0 per task; (2) I-task prompt loaded verbatim from snapshot
assets/example_reasoning_prompt.json (repo's own pairing for
example_reasoning_input.png); (3) enable_thinking=True pinned on the chat
template (reference default); (4) MAX_NEW 64 -> 256. V-task prompt and
loader/frames/guard identical to attempt-2. Gate: >= 1 of 2 tasks with
>= 24 new tokens of scene-relevant text. List-form subprocess only.
"""
import json, os, subprocess, sys, time, traceback

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(LAB, "results")
OUT_JSON = os.path.join(RESULTS, "c2_world_smoke_v3.json")
MODEL_ID = "nvidia/Cosmos3-Edge"
FFMPEG = "/home/eileen/.local/bin/ffmpeg"
SNAP = "/home/eileen/.cache/huggingface/hub/models--nvidia--Cosmos3-Edge/snapshots/344d602b128d1bbdacb43b08d0a3626f46343e29"
MAX_NEW = 256
PROMPT_V = "Watch this clip. What is happening, and what is most likely to happen next?"
# Pinned sampling values: do_sample=true is the only sampling directive in the
# snapshot generation_config.json; temperature/top_p/top_k/repetition_penalty
# are absent there, so they are pinned to the transformers GenerationConfig
# defaults explicitly (reproducible across library versions).
GEN_PARAMS = dict(do_sample=True, temperature=1.0, top_p=1.0, top_k=50,
                  repetition_penalty=1.0)
SEED = 0

def load_prompt_i():
    """Repo's own example pairing for example_reasoning_input.png, verbatim."""
    with open(os.path.join(SNAP, "assets", "example_reasoning_prompt.json")) as f:
        spec = json.load(f)
    return spec["prompt"], int(spec.get("max_tokens", 4096))

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
    chat = proc.apply_chat_template(msgs, add_generation_prompt=True,
                                    tokenize=False, enable_thinking=True)
    path = None
    if frames is not None:
        try:
            inputs = proc(text=[chat], videos=[frames], return_tensors="pt")
            path = "videos=[8 frames]"
        except Exception as e:
            print(f"[C2v3] videos path failed ({e}); multi-image fallback", flush=True)
            inputs = proc(text=[chat], images=frames, return_tensors="pt")
            path = "images=[8 frames]"
    else:
        inputs = proc(text=[chat], images=[image], return_tensors="pt")
        path = "images=[1 example png]"
    inputs = {k: v for k, v in inputs.items() if v is not None}
    inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    n_in = int(inputs["input_ids"].shape[-1])
    torch.manual_seed(SEED)
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW, **GEN_PARAMS)
    t_gen = time.time() - t0
    n_new = int(out.shape[-1] - n_in)
    try:
        text = proc.batch_decode(out[:, n_in:], skip_special_tokens=True)[0]
    except AttributeError:
        text = proc.tokenizer.batch_decode(out[:, n_in:], skip_special_tokens=True)[0]
    return {"task": task, "path": path, "input_tokens": n_in,
            "n_new_tokens": n_new, "t_gen_s": round(t_gen, 2),
            "decode_tok_s": round(n_new / max(t_gen, 1e-9), 2),
            "gen_params": {**GEN_PARAMS, "max_new_tokens": MAX_NEW, "seed": SEED},
            "prompt": prompt, "text": text}

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

    prompt_i, repo_max_tokens = load_prompt_i()
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        frames = grab_frames(td)
    img = Image.open(os.path.join(SNAP, "assets", "example_reasoning_input.png")).convert("RGB")

    v = run_task(model, proc, PROMPT_V, "V-task (8 frames, anticipation)", "video", frames=frames)
    torch.cuda.reset_peak_memory_stats()
    i = run_task(model, proc, prompt_i, "I-task (example png, repo example prompt)", "image", image=img)
    peak = torch.cuda.max_memory_allocated() / 2**30
    free, tot = torch.cuda.mem_get_info()
    return {"t_load_s": round(t_load, 2), "v": v, "i": i,
            "i_prompt_source": "snapshot assets/example_reasoning_prompt.json [\"prompt\"]",
            "repo_example_max_tokens_noted": repo_max_tokens,
            "chat_template_kwargs": {"add_generation_prompt": True, "enable_thinking": True},
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
            print("[C2v3] INNER FAILED", flush=True); traceback.print_exc()
            res = {"verdict": "KILL", "verdict_stage": "exception",
                   "traceback_tail": traceback.format_exc()[-1500:]}
        json.dump(res, open(OUT_JSON, "w"), indent=1)
        print("[C2v3] INNER_DONE", json.dumps({k: v for k, v in res.items()
              if k not in ("v", "i")})[:400], flush=True)
        for t in ("v", "i"):
            if t in res: print(f"[C2v3] {t}: {res[t]['n_new_tokens']} tok @ {res[t]['decode_tok_s']} tok/s via {res[t]['path']}\n[C2v3] text: {res[t]['text'][:500]}", flush=True)
        return
    sys.path.insert(0, LAB)
    import guard
    g = guard.Guard(timeout_s=1800.0)
    if not g.preflight():
        json.dump({"verdict": "ABORTED_GUARD_PREFLIGHT", "breach": g.breach},
                  open(OUT_JSON, "w"), indent=1)
        print(f"[C2v3] GUARD PREFLIGHT FAIL: {g.breach}", flush=True); sys.exit(2)
    rc, so, se = g.run([sys.executable, os.path.abspath(__file__), "--inner"],
                       cwd=LAB, env=dict(os.environ))
    print(f"[C2v3] guard rc={rc} breach={g.breach}", flush=True)
    if rc != 0:
        print("[C2v3] stderr tail:", se[-500:], flush=True)
        if os.path.exists(OUT_JSON):
            cur = json.load(open(OUT_JSON))
            cur.update({"returncode": rc, "guard_breach": g.breach})
            json.dump(cur, open(OUT_JSON, "w"), indent=1)
    print("[C2v3] DONE", flush=True)

if __name__ == "__main__":
    main()
