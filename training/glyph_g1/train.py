"""
Autoresearch pretraining script. Single-GPU, single-file.
Cherry-picked and simplified from nanochat.
Usage: uv run train.py
"""

import os
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import gc
import math
import time
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F

from kernels import get_kernel
cap = torch.cuda.get_device_capability()
# varunneal's FA3 is Hopper only, use kernels-community on non-Hopper GPUs
repo = "varunneal/flash-attention-3" if cap == (9, 0) else "kernels-community/flash-attn3"
fa3 = get_kernel(repo, revision="main").flash_attn_interface

# G1: prepare.py pipeline replaced by glyph npz loader (see bottom)

# ---------------------------------------------------------------------------
# GPT Model
# ---------------------------------------------------------------------------

@dataclass
class GPTConfig:
    sequence_len: int = 6144
    vocab_size: int = 32
    n_layer: int = 12
    n_head: int = 6
    n_kv_head: int = 6
    n_embd: int = 768
    window_pattern: str = "SSSL"


def norm(x):
    return F.rms_norm(x, (x.size(-1),))


def has_ve(layer_idx, n_layer):
    """Returns True if layer should have Value Embedding (alternating, last always included)."""
    return layer_idx % 2 == (n_layer - 1) % 2


def apply_rotary_emb(x, cos, sin):
    assert x.ndim == 4
    d = x.shape[3] // 2
    x1, x2 = x[..., :d], x[..., d:]
    y1 = x1 * cos + x2 * sin
    y2 = x1 * (-sin) + x2 * cos
    return torch.cat([y1, y2], 3)


class CausalSelfAttention(nn.Module):
    def __init__(self, config, layer_idx):
        super().__init__()
        self.n_head = config.n_head
        self.n_kv_head = config.n_kv_head
        self.n_embd = config.n_embd
        self.head_dim = self.n_embd // self.n_head
        assert self.n_embd % self.n_head == 0
        assert self.n_kv_head <= self.n_head and self.n_head % self.n_kv_head == 0
        # --- DELTA-FREE MUTATION (D2): head split bookkeeping ---
        # First half of heads attend on absolute k/v (baseline path); second half use
        # q as-is and POST-projection temporal differences of the same k/v row-slices.
        # Zero new parameters (row-slices of the same c_q/c_k/c_v).
        assert self.n_head % 2 == 0 and self.n_kv_head % 2 == 0, \
            "delta-attention mutation requires even head counts"
        self.n_normal_head = self.n_head // 2
        self.n_delta_head = self.n_head - self.n_normal_head
        self.n_normal_kv_head = self.n_kv_head // 2
        self.n_delta_kv_head = self.n_kv_head - self.n_normal_kv_head
        self.c_q = nn.Linear(self.n_embd, self.n_head * self.head_dim, bias=False)
        self.c_k = nn.Linear(self.n_embd, self.n_kv_head * self.head_dim, bias=False)
        self.c_v = nn.Linear(self.n_embd, self.n_kv_head * self.head_dim, bias=False)
        self.c_proj = nn.Linear(self.n_embd, self.n_embd, bias=False)
        self.ve_gate_channels = 32
        self.ve_gate = nn.Linear(self.ve_gate_channels, self.n_kv_head, bias=False) if has_ve(layer_idx, config.n_layer) else None

    def forward(self, x, ve, cos_sin, window_size):
        B, T, C = x.size()
        # --- DELTA-FREE MUTATION (D2) ---
        # ONE projection pass: q/k/v from h as usual (no second linear, no hidden-state
        # shift). Delta heads (second half of each head dim) take q as-is; their
        # keys/values are the POST-projection temporal differences of the same
        # row-slices: k_d[t] = k[t] - k[t-1], v_d[t] = v[t] - v[t-1] (zero at t=0).
        # The differencing is one cheap elementwise op on projected tensors.
        # Rotary, norms, window, VE gate (absolute path), c_proj all unchanged.
        q = self.c_q(x).view(B, T, self.n_head, self.head_dim)
        k = self.c_k(x).view(B, T, self.n_kv_head, self.head_dim)
        v = self.c_v(x).view(B, T, self.n_kv_head, self.head_dim)

        kd = k[:, :, self.n_normal_kv_head:]
        kd = kd - torch.cat([torch.zeros_like(kd[:, :1]), kd[:, :-1]], dim=1)
        k = torch.cat([k[:, :, :self.n_normal_kv_head], kd], dim=2)
        vd = v[:, :, self.n_normal_kv_head:]
        vd = vd - torch.cat([torch.zeros_like(vd[:, :1]), vd[:, :-1]], dim=1)
        v = torch.cat([v[:, :, :self.n_normal_kv_head], vd], dim=2)
        # delta-head queries: q as-is (second half of q already in place)

        # Value residual (ResFormer): mix in value embedding with input-dependent gate per head
        if ve is not None:
            ve = ve.view(B, T, self.n_kv_head, self.head_dim)
            gate = 2 * torch.sigmoid(self.ve_gate(x[..., :self.ve_gate_channels]))
            # D2: the pre-projection delta path no longer exists, so ALL heads (delta
            # included) read the gate from the absolute path — identical to baseline.
            # The value embedding stays the absolute token embedding for both paths.
            v = v + gate.unsqueeze(-1) * ve

        cos, sin = cos_sin
        q, k = apply_rotary_emb(q, cos, sin), apply_rotary_emb(k, cos, sin)
        q, k = norm(q), norm(k)
        # PATCH (torch 2.14): inductor+autocast can feed fp32 into the FA3 custom op ->
        # "FlashAttention only supports fp16, bf16, and fp8_e4m3". Explicit casts restore
        # the upstream bf16-attention semantics. No-op when already bf16.
        q, k, v = q.bfloat16(), k.bfloat16(), v.bfloat16()

        y = fa3.flash_attn_func(q, k, v, causal=True, window_size=window_size)
        y = y.contiguous().view(B, T, -1)
        y = self.c_proj(y)
        return y


class MLP(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.c_fc = nn.Linear(config.n_embd, 4 * config.n_embd, bias=False)
        self.c_proj = nn.Linear(4 * config.n_embd, config.n_embd, bias=False)

    def forward(self, x):
        x = self.c_fc(x)
        x = F.relu(x).square()
        x = self.c_proj(x)
        return x


class Block(nn.Module):
    def __init__(self, config, layer_idx):
        super().__init__()
        self.attn = CausalSelfAttention(config, layer_idx)
        self.mlp = MLP(config)

    def forward(self, x, ve, cos_sin, window_size):
        x = x + self.attn(norm(x), ve, cos_sin, window_size)
        x = x + self.mlp(norm(x))
        return x


class GPT(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.window_sizes = self._compute_window_sizes(config)
        self.transformer = nn.ModuleDict({
            "wte": nn.Embedding(config.vocab_size, config.n_embd),
            "h": nn.ModuleList([Block(config, i) for i in range(config.n_layer)]),
        })
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        self.resid_lambdas = nn.Parameter(torch.ones(config.n_layer))
        self.x0_lambdas = nn.Parameter(torch.zeros(config.n_layer))
        # Value embeddings
        head_dim = config.n_embd // config.n_head
        kv_dim = config.n_kv_head * head_dim
        self.value_embeds = nn.ModuleDict({
            str(i): nn.Embedding(config.vocab_size, kv_dim)
            for i in range(config.n_layer) if has_ve(i, config.n_layer)
        })
        # Rotary embeddings
        self.rotary_seq_len = config.sequence_len * 10
        cos, sin = self._precompute_rotary_embeddings(self.rotary_seq_len, head_dim)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    @torch.no_grad()
    def init_weights(self):
        # Embedding and unembedding
        torch.nn.init.normal_(self.transformer.wte.weight, mean=0.0, std=1.0)
        torch.nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.001)
        # Transformer blocks
        n_embd = self.config.n_embd
        s = 3**0.5 * n_embd**-0.5
        for block in self.transformer.h:
            torch.nn.init.uniform_(block.attn.c_q.weight, -s, s)
            torch.nn.init.uniform_(block.attn.c_k.weight, -s, s)
            torch.nn.init.uniform_(block.attn.c_v.weight, -s, s)
            torch.nn.init.zeros_(block.attn.c_proj.weight)
            torch.nn.init.uniform_(block.mlp.c_fc.weight, -s, s)
            torch.nn.init.zeros_(block.mlp.c_proj.weight)
        # Per-layer scalars
        self.resid_lambdas.fill_(1.0)
        self.x0_lambdas.fill_(0.1)
        # Value embeddings
        for ve in self.value_embeds.values():
            torch.nn.init.uniform_(ve.weight, -s, s)
        # Gate weights init to zero (sigmoid(0)=0.5, scaled by 2 -> 1.0 = neutral)
        for block in self.transformer.h:
            if block.attn.ve_gate is not None:
                torch.nn.init.zeros_(block.attn.ve_gate.weight)
        # Rotary embeddings
        head_dim = self.config.n_embd // self.config.n_head
        cos, sin = self._precompute_rotary_embeddings(self.rotary_seq_len, head_dim)
        self.cos, self.sin = cos, sin
        # Cast embeddings to bf16
        self.transformer.wte.to(dtype=torch.bfloat16)
        for ve in self.value_embeds.values():
            ve.to(dtype=torch.bfloat16)

    def _precompute_rotary_embeddings(self, seq_len, head_dim, base=10000, device=None):
        if device is None:
            device = self.transformer.wte.weight.device
        channel_range = torch.arange(0, head_dim, 2, dtype=torch.float32, device=device)
        inv_freq = 1.0 / (base ** (channel_range / head_dim))
        t = torch.arange(seq_len, dtype=torch.float32, device=device)
        freqs = torch.outer(t, inv_freq)
        cos, sin = freqs.cos(), freqs.sin()
        cos, sin = cos.bfloat16(), sin.bfloat16()
        cos, sin = cos[None, :, None, :], sin[None, :, None, :]
        return cos, sin

    def _compute_window_sizes(self, config):
        pattern = config.window_pattern.upper()
        assert all(c in "SL" for c in pattern)
        long_window = config.sequence_len
        short_window = long_window // 2
        char_to_window = {"L": (long_window, 0), "S": (short_window, 0)}
        window_sizes = []
        for layer_idx in range(config.n_layer):
            char = pattern[layer_idx % len(pattern)]
            window_sizes.append(char_to_window[char])
        window_sizes[-1] = (long_window, 0)
        return window_sizes

    def estimate_flops(self):
        """Estimated FLOPs per token (forward + backward)."""
        nparams = sum(p.numel() for p in self.parameters())
        value_embeds_numel = sum(ve.weight.numel() for ve in self.value_embeds.values())
        nparams_exclude = (self.transformer.wte.weight.numel() + value_embeds_numel +
                          self.resid_lambdas.numel() + self.x0_lambdas.numel())
        h = self.config.n_head
        q = self.config.n_embd // self.config.n_head
        t = self.config.sequence_len
        attn_flops = 0
        for window_size in self.window_sizes:
            window = window_size[0]
            effective_seq = t if window < 0 else min(window, t)
            attn_flops += 12 * h * q * effective_seq
        return 6 * (nparams - nparams_exclude) + attn_flops

    def num_scaling_params(self):
        wte = sum(p.numel() for p in self.transformer.wte.parameters())
        value_embeds = sum(p.numel() for p in self.value_embeds.parameters())
        lm_head = sum(p.numel() for p in self.lm_head.parameters())
        transformer_matrices = sum(p.numel() for p in self.transformer.h.parameters())
        scalars = self.resid_lambdas.numel() + self.x0_lambdas.numel()
        total = wte + value_embeds + lm_head + transformer_matrices + scalars
        return {
            'wte': wte, 'value_embeds': value_embeds, 'lm_head': lm_head,
            'transformer_matrices': transformer_matrices, 'scalars': scalars, 'total': total,
        }

    def setup_optimizer(self, unembedding_lr=0.004, embedding_lr=0.2, matrix_lr=0.02,
                        weight_decay=0.0, adam_betas=(0.8, 0.95), scalar_lr=0.5):
        model_dim = self.config.n_embd
        matrix_params = list(self.transformer.h.parameters())
        value_embeds_params = list(self.value_embeds.parameters())
        embedding_params = list(self.transformer.wte.parameters())
        lm_head_params = list(self.lm_head.parameters())
        resid_params = [self.resid_lambdas]
        x0_params = [self.x0_lambdas]
        assert len(list(self.parameters())) == (len(matrix_params) + len(embedding_params) +
            len(lm_head_params) + len(value_embeds_params) + len(resid_params) + len(x0_params))
        # Scale LR ∝ 1/√dmodel (tuned at 768 dim)
        dmodel_lr_scale = (model_dim / 768) ** -0.5
        print(f"Scaling AdamW LRs by 1/sqrt({model_dim}/768) = {dmodel_lr_scale:.6f}")
        param_groups = [
            dict(kind='adamw', params=lm_head_params, lr=unembedding_lr * dmodel_lr_scale, betas=adam_betas, eps=1e-10, weight_decay=0.0),
            dict(kind='adamw', params=embedding_params, lr=embedding_lr * dmodel_lr_scale, betas=adam_betas, eps=1e-10, weight_decay=0.0),
            dict(kind='adamw', params=value_embeds_params, lr=embedding_lr * dmodel_lr_scale, betas=adam_betas, eps=1e-10, weight_decay=0.0),
            dict(kind='adamw', params=resid_params, lr=scalar_lr * 0.01, betas=adam_betas, eps=1e-10, weight_decay=0.0),
            dict(kind='adamw', params=x0_params, lr=scalar_lr, betas=(0.96, 0.95), eps=1e-10, weight_decay=0.0),
        ]
        for shape in sorted({p.shape for p in matrix_params}):
            group_params = [p for p in matrix_params if p.shape == shape]
            param_groups.append(dict(
                kind='muon', params=group_params, lr=matrix_lr,
                momentum=0.95, ns_steps=5, beta2=0.95, weight_decay=weight_decay,
            ))
        optimizer = MuonAdamW(param_groups)
        for group in optimizer.param_groups:
            group["initial_lr"] = group["lr"]
        return optimizer

    def forward(self, idx, targets=None, reduction='mean'):
        B, T = idx.size()
        assert T <= self.cos.size(1)
        cos_sin = self.cos[:, :T], self.sin[:, :T]

        x = self.transformer.wte(idx)
        x = norm(x)
        x0 = x
        for i, block in enumerate(self.transformer.h):
            x = self.resid_lambdas[i] * x + self.x0_lambdas[i] * x0
            ve = self.value_embeds[str(i)](idx) if str(i) in self.value_embeds else None
            x = block(x, ve, cos_sin, self.window_sizes[i])
        x = norm(x)

        softcap = 15
        logits = self.lm_head(x)
        logits = logits.float()
        logits = softcap * torch.tanh(logits / softcap)

        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1),
                                   ignore_index=-1, reduction=reduction)
            return loss
        return logits

# ---------------------------------------------------------------------------
# Optimizer (MuonAdamW, single GPU only)
# ---------------------------------------------------------------------------

polar_express_coeffs = [
    (8.156554524902461, -22.48329292557795, 15.878769915207462),
    (4.042929935166739, -2.808917465908714, 0.5000178451051316),
    (3.8916678022926607, -2.772484153217685, 0.5060648178503393),
    (3.285753657755655, -2.3681294933425376, 0.46449024233003106),
    (2.3465413258596377, -1.7097828382687081, 0.42323551169305323),
]

@torch.compile(dynamic=False, fullgraph=True)
def adamw_step_fused(p, grad, exp_avg, exp_avg_sq, step_t, lr_t, beta1_t, beta2_t, eps_t, wd_t):
    p.mul_(1 - lr_t * wd_t)
    exp_avg.lerp_(grad, 1 - beta1_t)
    exp_avg_sq.lerp_(grad.square(), 1 - beta2_t)
    bias1 = 1 - beta1_t ** step_t
    bias2 = 1 - beta2_t ** step_t
    denom = (exp_avg_sq / bias2).sqrt() + eps_t
    step_size = lr_t / bias1
    p.add_(exp_avg / denom, alpha=-step_size)

@torch.compile(dynamic=False, fullgraph=True)
def muon_step_fused(stacked_grads, stacked_params, momentum_buffer, second_momentum_buffer,
                    momentum_t, lr_t, wd_t, beta2_t, ns_steps, red_dim):
    # Nesterov momentum
    momentum = momentum_t.to(stacked_grads.dtype)
    momentum_buffer.lerp_(stacked_grads, 1 - momentum)
    g = stacked_grads.lerp_(momentum_buffer, momentum)
    # Polar express orthogonalization
    X = g.bfloat16()
    X = X / (X.norm(dim=(-2, -1), keepdim=True) * 1.02 + 1e-6)
    if g.size(-2) > g.size(-1):
        for a, b, c in polar_express_coeffs[:ns_steps]:
            A = X.mT @ X
            B = b * A + c * (A @ A)
            X = a * X + X @ B
    else:
        for a, b, c in polar_express_coeffs[:ns_steps]:
            A = X @ X.mT
            B = b * A + c * (A @ A)
            X = a * X + B @ X
    g = X
    # NorMuon variance reduction
    beta2 = beta2_t.to(g.dtype)
    v_mean = g.float().square().mean(dim=red_dim, keepdim=True)
    red_dim_size = g.size(red_dim)
    v_norm_sq = v_mean.sum(dim=(-2, -1), keepdim=True) * red_dim_size
    v_norm = v_norm_sq.sqrt()
    second_momentum_buffer.lerp_(v_mean.to(dtype=second_momentum_buffer.dtype), 1 - beta2)
    step_size = second_momentum_buffer.clamp_min(1e-10).rsqrt()
    scaled_sq_sum = (v_mean * red_dim_size) * step_size.float().square()
    v_norm_new = scaled_sq_sum.sum(dim=(-2, -1), keepdim=True).sqrt()
    final_scale = step_size * (v_norm / v_norm_new.clamp_min(1e-10))
    g = g * final_scale.to(g.dtype)
    # Cautious weight decay + parameter update
    lr = lr_t.to(g.dtype)
    wd = wd_t.to(g.dtype)
    mask = (g * stacked_params) >= 0
    stacked_params.sub_(lr * g + lr * wd * stacked_params * mask)


class MuonAdamW(torch.optim.Optimizer):
    """Combined optimizer: Muon for 2D matrix params, AdamW for others."""

    def __init__(self, param_groups):
        super().__init__(param_groups, defaults={})
        # 0-D CPU tensors to avoid torch.compile recompilation when values change
        self._adamw_step_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._adamw_lr_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._adamw_beta1_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._adamw_beta2_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._adamw_eps_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._adamw_wd_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._muon_momentum_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._muon_lr_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._muon_wd_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")
        self._muon_beta2_t = torch.tensor(0.0, dtype=torch.float32, device="cpu")

    def _step_adamw(self, group):
        for p in group['params']:
            if p.grad is None:
                continue
            grad = p.grad
            state = self.state[p]
            if not state:
                state['step'] = 0
                state['exp_avg'] = torch.zeros_like(p)
                state['exp_avg_sq'] = torch.zeros_like(p)
            state['step'] += 1
            self._adamw_step_t.fill_(state['step'])
            self._adamw_lr_t.fill_(group['lr'])
            self._adamw_beta1_t.fill_(group['betas'][0])
            self._adamw_beta2_t.fill_(group['betas'][1])
            self._adamw_eps_t.fill_(group['eps'])
            self._adamw_wd_t.fill_(group['weight_decay'])
            adamw_step_fused(p, grad, state['exp_avg'], state['exp_avg_sq'],
                            self._adamw_step_t, self._adamw_lr_t, self._adamw_beta1_t,
                            self._adamw_beta2_t, self._adamw_eps_t, self._adamw_wd_t)

    def _step_muon(self, group):
        params = group['params']
        if not params:
            return
        p = params[0]
        state = self.state[p]
        num_params = len(params)
        shape, device, dtype = p.shape, p.device, p.dtype
        if "momentum_buffer" not in state:
            state["momentum_buffer"] = torch.zeros(num_params, *shape, dtype=dtype, device=device)
        if "second_momentum_buffer" not in state:
            state_shape = (num_params, shape[-2], 1) if shape[-2] >= shape[-1] else (num_params, 1, shape[-1])
            state["second_momentum_buffer"] = torch.zeros(state_shape, dtype=dtype, device=device)
        red_dim = -1 if shape[-2] >= shape[-1] else -2
        stacked_grads = torch.stack([p.grad for p in params])
        stacked_params = torch.stack(params)
        self._muon_momentum_t.fill_(group["momentum"])
        self._muon_beta2_t.fill_(group["beta2"] if group["beta2"] is not None else 0.0)
        self._muon_lr_t.fill_(group["lr"] * max(1.0, shape[-2] / shape[-1])**0.5)
        self._muon_wd_t.fill_(group["weight_decay"])
        muon_step_fused(stacked_grads, stacked_params,
                        state["momentum_buffer"], state["second_momentum_buffer"],
                        self._muon_momentum_t, self._muon_lr_t, self._muon_wd_t,
                        self._muon_beta2_t, group["ns_steps"], red_dim)
        torch._foreach_copy_(params, list(stacked_params.unbind(0)))

    @torch.no_grad()
    def step(self):
        for group in self.param_groups:
            if group['kind'] == 'adamw':
                self._step_adamw(group)
            elif group['kind'] == 'muon':
                self._step_muon(group)

# ---------------------------------------------------------------------------
# Hyperparameters (edit these directly, no CLI flags needed)
# ---------------------------------------------------------------------------

# Model architecture
ASPECT_RATIO = 64       # model_dim = depth * ASPECT_RATIO
HEAD_DIM = 128          # target head dimension for attention
WINDOW_PATTERN = "SSSL" # sliding window pattern: L=full, S=half context

# Optimization
TOTAL_BATCH_SIZE = 4 * 6144 * 16  # G1: 393,216 tokens/step (16 accum)
EMBEDDING_LR = 0.6      # learning rate for token embeddings (Adam)
UNEMBEDDING_LR = 0.004  # learning rate for lm_head (Adam)
MATRIX_LR = 0.04        # learning rate for matrix parameters (Muon)
SCALAR_LR = 0.5         # learning rate for per-layer scalars (Adam)
WEIGHT_DECAY = 0.2      # cautious weight decay for Muon
ADAM_BETAS = (0.8, 0.95) # Adam beta1, beta2
WARMUP_RATIO = 0.0      # fraction of time budget for LR warmup
WARMDOWN_RATIO = 0.5    # fraction of time budget for LR warmdown
FINAL_LR_FRAC = 0.0     # final LR as fraction of initial

# Model size
DEPTH = 8               # number of transformer layers
DEVICE_BATCH_SIZE = 4  # G1: seq 6144 on 6GB


# ---------------------------------------------------------------------------
# G1: glyph-domain data pipeline + main (replaces prepare.py verbatim tail)
# ---------------------------------------------------------------------------
import os as _os
import numpy as np
from dataclasses import asdict

HERE = _os.path.dirname(_os.path.abspath(__file__))
DATA_NPZ = _os.path.join(HERE, _os.environ.get("G1_DATA", "data.npz"))
MAX_SEQ_LEN = 6144
TIME_BUDGET = 300
SEP = 31
DYNAMIC = ("life", "testsrc2", "mandelbrot")


def load_streams():
    d = np.load(DATA_NPZ)
    names = [str(n) for n in d["names"]]
    streams = {}
    for name in names:
        for split in ("tr", "va", "te"):
            arr = d[f"{name}_{split}"].astype(np.int64)
            if arr.shape[0] >= 3:
                streams[(name, split)] = arr
    return names, streams


def stream_tokens(frames):
    """(n,36,48) codes -> flat [F0 SEP F1 SEP ...] (spec pack, sliding-window)."""
    parts = []
    for i in range(frames.shape[0]):
        parts.append(frames[i].reshape(-1))
        parts.append(np.full((1,), SEP, dtype=np.int64))
    return np.concatenate(parts)


class GlyphLoader:
    """Infinite (x, y, epoch) batches sampled from the split's token stream."""

    def __init__(self, streams, split, batch, seq_len, seed=42):
        toks = [stream_tokens(s) for (nm, sp), s in streams.items() if sp == split]
        self.tokens = np.concatenate(toks)
        self.batch, self.T = batch, seq_len
        self.rng = np.random.default_rng(seed)
        self.epoch = 0
        self._calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        B, T = self.batch, self.T
        xs = np.zeros((B, T), dtype=np.int64)
        ys = np.zeros((B, T), dtype=np.int64)
        n = len(self.tokens)
        for b in range(B):
            i = int(self.rng.integers(0, n - T - 2))
            xs[b] = self.tokens[i:i + T]
            ys[b] = self.tokens[i + 1:i + 1 + T]
        self._calls += 1
        if self._calls % 500 == 0:
            self.epoch += 1
        import torch as _t
        return _t.from_numpy(xs).cuda(), _t.from_numpy(ys).cuda(), self.epoch


@torch.no_grad()
def evaluate_g1(model, streams, autocast_ctx):
    """Per-source test metrics: model acc/CE-per-cell vs persistence + majority."""
    import torch.nn.functional as F
    model.eval()
    results = {}
    T = MAX_SEQ_LEN
    for (name, split), frames in sorted(streams.items()):
        if split != "te":
            continue
        toks = stream_tokens(frames)
        n = len(toks)
        correct = total = 0
        changed_correct = changed_total = 0
        ce_sum = 0.0
        # G2 diagnostic: changed-cells mask (cell != previous frame's same cell)
        Lw = 1728 + 1  # frame + SEP stride
        chg_stream = np.zeros(n, dtype=bool)
        ii = np.arange(Lw, n)
        chg_stream[ii] = (toks[ii] != SEP) & (toks[ii] != toks[ii - Lw])
        for i in range(T, n - 1, T):
            x = torch.from_numpy(toks[i - T:i])[None].to(device)
            yt = torch.from_numpy(toks[i - T + 1:i + 1])[None].to(device)
            with autocast_ctx:
                logits = model(x)
            mask = yt[0] != SEP
            cmask = mask & torch.from_numpy(chg_stream[i - T + 1:i + 1]).to(device)
            pred = logits[0].argmax(-1)
            correct += (pred[mask] == yt[0][mask]).sum().item()
            total += int(mask.sum().item())
            changed_correct += (pred[cmask] == yt[0][cmask]).sum().item()
            changed_total += int(cmask.sum().item())
            ce_sum += F.cross_entropy(logits[0][mask].float(),
                                      yt[0][mask], reduction="sum").item()
        fr = frames
        fr_flat = fr.reshape(len(fr), -1)
        persist_acc = float((fr[1:] == fr[:-1]).mean())
        tr = streams.get((name, "tr"))
        mode = np.zeros(fr_flat.shape[1], dtype=np.int64)
        if tr is not None and len(tr):
            tr_flat = tr.reshape(len(tr), -1)
            for c in range(fr_flat.shape[1]):
                mode[c] = np.bincount(tr_flat[:, c], minlength=32).argmax()
        majority_acc = float((fr_flat == mode[None]).mean())
        results[name] = {
            "model_acc": correct / max(total, 1),
            "model_ce_per_cell": ce_sum / max(total, 1),
            "persist_acc": persist_acc,
            "majority_acc": majority_acc,
            "model_changed_acc": changed_correct / max(changed_total, 1),
            "changed_frac": float(chg_stream.mean()),
        }
    model.train()
    return results


def gate_verdict(results):
    dyn = [results[k] for k in DYNAMIC if k in results]
    pool_correct = sum(r["model_acc"] for r in results.values())
    pool_n = max(len(results), 1)
    model_overall = pool_correct / pool_n
    maj_overall = sum(r["majority_acc"] for r in results.values()) / pool_n
    persist_margins = {k: results[k]["model_acc"] - results[k]["persist_acc"]
                       for k in DYNAMIC if k in results}
    gate_persist = all(m >= 0.02 for m in persist_margins.values()) and len(persist_margins) == 3
    gate_majority = (model_overall - maj_overall) >= 0.15
    verdict = "KEEP" if (gate_persist and gate_majority) else (
        "KILL" if (model_overall - maj_overall) < 0.05 else "INCONCLUSIVE")
    return verdict, dict(persist_margins=persist_margins,
                         majority_margin=model_overall - maj_overall,
                         model_overall=model_overall, maj_overall=maj_overall)


def main():
    t_start = time.time()
    torch.manual_seed(42)
    torch.cuda.manual_seed(42)
    torch.set_float32_matmul_precision("high")
    global device, autocast_ctx
    device = torch.device("cuda")
    autocast_ctx = torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16)

    names, streams = load_streams()
    print(f"sources: {names}")

    def build_model_config(depth):
        base_dim = depth * ASPECT_RATIO
        model_dim = ((base_dim + HEAD_DIM - 1) // HEAD_DIM) * HEAD_DIM
        num_heads = model_dim // HEAD_DIM
        return GPTConfig(
            sequence_len=MAX_SEQ_LEN, vocab_size=32,
            n_layer=depth, n_head=num_heads, n_kv_head=num_heads,
            n_embd=model_dim, window_pattern=WINDOW_PATTERN,
        )

    config = build_model_config(DEPTH)
    print(f"Model config: {asdict(config)}")

    with torch.device("meta"):
        model = GPT(config)
    model.to_empty(device=device)
    model.init_weights()

    num_params = model.num_scaling_params()['total']
    print(f"params: {num_params:,}")

    tokens_per_fwdbwd = DEVICE_BATCH_SIZE * MAX_SEQ_LEN
    assert TOTAL_BATCH_SIZE % tokens_per_fwdbwd == 0
    grad_accum_steps = TOTAL_BATCH_SIZE // tokens_per_fwdbwd

    optimizer = model.setup_optimizer(
        unembedding_lr=UNEMBEDDING_LR, embedding_lr=EMBEDDING_LR,
        scalar_lr=SCALAR_LR, adam_betas=ADAM_BETAS, matrix_lr=MATRIX_LR,
        weight_decay=WEIGHT_DECAY,
    )

    model = torch.compile(model, dynamic=False)

    # FAIL-first untrained check: the untrained model must NOT beat persistence.
    with torch.no_grad():
        pre = evaluate_g1(model, {k: v for k, v in streams.items()
                                  if k[1] == "te" and k[0] in DYNAMIC[:1]},
                          autocast_ctx)
    untrained_ok = all(r["model_acc"] < r["persist_acc"] + 0.05
                       for r in pre.values())
    print(f"UNTRAINED FAIL-CHECK: {'OK' if untrained_ok else 'VIOLATION'} "
          f"({ {k: round(v['model_acc'],3) for k,v in pre.items()} })")
    if not untrained_ok:
        print(json.dumps({"experiment": "G1", "verdict": "FAIL_FIRST_VIOLATION"}))
        return

    train_loader = iter(GlyphLoader(streams, "tr", DEVICE_BATCH_SIZE, MAX_SEQ_LEN))
    x, y, epoch = next(train_loader)

    print(f"Time budget: {TIME_BUDGET}s | grad_accum: {grad_accum_steps}")

    def get_lr_multiplier(progress):
        if progress < WARMUP_RATIO:
            return progress / WARMUP_RATIO if WARMUP_RATIO > 0 else 1.0
        elif progress < 1.0 - WARMDOWN_RATIO:
            return 1.0
        else:
            cooldown = (1.0 - progress) / WARMDOWN_RATIO
            return cooldown * 1.0 + (1 - cooldown) * FINAL_LR_FRAC

    def get_muon_momentum(step):
        frac = min(step / 300, 1)
        return (1 - frac) * 0.85 + frac * 0.95

    def get_weight_decay(progress):
        return WEIGHT_DECAY * (1 - progress)

    t_start_training = time.time()
    smooth_train_loss = 0
    total_training_time = 0
    step = 0

    while True:
        torch.cuda.synchronize()
        t0 = time.time()
        for micro_step in range(grad_accum_steps):
            with autocast_ctx:
                loss = model(x, y)
            train_loss = loss.detach()
            loss = loss / grad_accum_steps
            loss.backward()
            x, y, epoch = next(train_loader)

        progress = min(total_training_time / TIME_BUDGET, 1.0)
        lrm = get_lr_multiplier(progress)
        muon_momentum = get_muon_momentum(step)
        muon_weight_decay = get_weight_decay(progress)
        for group in optimizer.param_groups:
            group["lr"] = group["initial_lr"] * lrm
            if group['kind'] == 'muon':
                group["momentum"] = muon_momentum
                group["weight_decay"] = muon_weight_decay
        optimizer.step()
        model.zero_grad(set_to_none=True)

        train_loss_f = train_loss.item()
        if math.isnan(train_loss_f) or train_loss_f > 100:
            print("FAIL")
            exit(1)

        torch.cuda.synchronize()
        t1 = time.time()
        dt = t1 - t0
        if step > 10:
            total_training_time += dt

        ema_beta = 0.9
        smooth_train_loss = ema_beta * smooth_train_loss + (1 - ema_beta) * train_loss_f
        debiased = smooth_train_loss / (1 - ema_beta**(step + 1))
        tok_per_sec = int(TOTAL_BATCH_SIZE / dt) if dt > 0 else 0
        print(f"\rstep {step:05d} ({100*progress:.1f}%) | loss {debiased:.4f} | "
              f"dt {dt*1000:.0f}ms | tok/s {tok_per_sec:,} | rem "
              f"{max(0, TIME_BUDGET-total_training_time):.0f}s   ", end="", flush=True)

        if step == 0:
            gc.collect(); gc.freeze(); gc.disable()
        elif (step + 1) % 5000 == 0:
            gc.collect()
        step += 1
        if step > 10 and total_training_time >= TIME_BUDGET:
            break

    print()
    results = evaluate_g1(model, streams, autocast_ctx)
    verdict, gate = gate_verdict(results)
    t_end = time.time()
    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024 / 1024
    out = {
        "experiment": "G1 glyph-domain next-frame predictor",
        "verdict": verdict, "gate": gate,
        "per_source": {f"{k[0]}/{k[1]}": {kk: round(vv, 4) if isinstance(vv, float) else vv
                                          for kk, vv in v.items()}
                       for k, v in results.items()},
        "train_loss_final": debiased,
        "num_steps": step, "num_params_M": round(num_params / 1e6, 1),
        "training_seconds": round(total_training_time, 1),
        "total_seconds": round(t_end - t_start, 1),
        "peak_vram_mb": round(peak_vram_mb, 1),
    }
    print("===G1_JSON===")
    import json as _j
    print(_j.dumps(out, indent=2))


if __name__ == "__main__":
    main()
