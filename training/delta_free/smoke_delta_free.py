"""Smoke test (D2 delta-free): exec the REAL mutated model classes from train.py,
build a tiny GPT on GPU, forward+backward with the real FA3 kernel.
Catches shape/slicing/compile bugs in the free-delta mutation in ~60s instead of 9min."""
import re, sys, torch

src = open("train.py").read()
# Cut the flat script at setup start; keep all defs/classes + kernel load
cut = src.index("t_start = time.time()")
header = src[:cut]
assert "delta_x" not in header.split("class CausalSelfAttention")[1].split("class MLP")[0], \
    "stale D1 code: hidden-state delta_x path still present"
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

# micro-check: the post-projection diff semantics used by the mutation
# (D1 convention: previous position is a ZERO row at t=0, so k_d[0] = k[0])
kk = torch.randn(B, 8, 4, 16)
kd = kk[:, :, 2:]
kd = kd - torch.cat([torch.zeros_like(kd[:, :1]), kd[:, :-1]], dim=1)
assert torch.allclose(kd[:, 0], kk[:, 0, 2:]), "k_d[0] must equal k[0] (zero-row shift convention)"
assert torch.allclose(kd[:, 1], kk[:, 1, 2:] - kk[:, 0, 2:]), "diff semantics wrong"
print("DIFF SEMANTICS OK — k_d[0]=k[0], k_d[t]=k[t]-k[t-1] on row-slices")

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

# eager-vs-compiled parity spot check (delta-free path must not break compile)
compiled = torch.compile(model, dynamic=False)
with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
    loss2 = compiled(idx, targets)
loss2.backward()
torch.cuda.synchronize()
assert torch.isfinite(loss2).all()
d = abs(loss2.item() - loss.item())
assert d < 0.1, f"compiled loss diverged from eager: {loss2.item()} vs {loss.item()}"
print(f"COMPILE OK — compiled loss={loss2.item():.4f} vs eager {loss.item():.4f} (|d|={d:.2e})")
