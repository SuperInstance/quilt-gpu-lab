"""Smoke test: exec the REAL mutated model classes from train.py (everything above the
flat-script section), build a tiny GPT on GPU, forward+backward with the real FA3 kernel.
Catches shape/slicing/compile bugs in the delta-attention mutation in ~60s instead of 9min."""
import re, sys, torch

src = open("train.py").read()
# Cut the flat script at setup start; keep all defs/classes + kernel load
cut = src.index("t_start = time.time()")
header = src[:cut]
ns = {"__name__": "smoke_ns"}
exec(compile(header, "train.py", "exec"), ns)

GPT, GPTConfig, norm = ns["GPT"], ns["GPTConfig"], ns["norm"]

cfg = GPTConfig(sequence_len=512, vocab_size=1024, n_layer=2, n_head=4, n_kv_head=4, n_embd=256)
model = GPT(cfg).cuda()
model.init_weights()

B, T = 2, 512
idx = torch.randint(0, cfg.vocab_size, (B, T), device="cuda")
targets = torch.randint(0, cfg.vocab_size, (B, T), device="cuda")

# sanity: head split as expected
attn0 = model.transformer.h[0].attn
assert (attn0.n_normal_head, attn0.n_delta_head, attn0.n_normal_kv_head, attn0.n_delta_kv_head) == (2, 2, 2, 2), \
    f"bad split: {attn0.n_normal_head}, {attn0.n_delta_head}, {attn0.n_normal_kv_head}, {attn0.n_delta_kv_head}"
assert sum(p.numel() for p in model.parameters()) > 0

with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
    loss = model(idx, targets)
loss.backward()
torch.cuda.synchronize()

gq = model.transformer.h[0].attn.c_q.weight.grad
assert gq is not None and torch.isfinite(gq).all(), "c_q grad missing/NaN"
n_nan = sum((p.grad.isnan().any() or p.grad.isinf().any()).item() for p in model.parameters() if p.grad is not None)
assert n_nan == 0, f"{n_nan} params with NaN/inf grads"
print(f"SMOKE OK — loss={loss.item():.4f} finite, all grads finite, head split 2+2 verified, VRAM peak "
      f"{torch.cuda.max_memory_allocated()/1024/1024:.0f}MB")

# eager-vs-compiled parity spot check (delta path must not break compile)
compiled = torch.compile(model, dynamic=False)
with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
    loss2 = compiled(idx, targets)
loss2.backward()
torch.cuda.synchronize()
assert torch.isfinite(loss2).all()
print(f"COMPILE OK — compiled loss={loss2.item():.4f} (same graph, same inputs -> should match eager {loss.item():.4f})")
