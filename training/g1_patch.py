#!/usr/bin/env python3
"""g1_patch.py — assemble training/glyph_g1/train.py from delta_free/train.py.

Surgery (per spec): replace prepare.py pipeline with the npz glyph-code loader,
V=32, seq 6144, B=4, __main__ guard, CE/accuracy eval vs persistence+majority.
Everything else (model, free-delta attention, MuonAdamW, schedules) verbatim.

G5: evaluate_g1 extended with the hybrid-refiner composite eval — predicted
frame = copy-last-frame (persistence), with the model's argmax substituted
where it is confident: p(argmax) − p(prev_cell) > thr AND argmax ≠ prev_cell.
Threshold sweep {0.1, 0.2, 0.3, 0.5}; pre-registered G5 gate in gate5().
"""
import re

SRC = "delta_free/train.py"
DST = "glyph_g1/train.py"

src = open(SRC).read()

# 1. Replace the prepare.py import with the G1 data module constants.
old_import = "from prepare import MAX_SEQ_LEN, TIME_BUDGET, Tokenizer, make_dataloader, evaluate_bpb"
assert old_import in src, "prepare import not found"
src = src.replace(old_import, "# G1: prepare.py pipeline replaced by glyph npz loader (see bottom)")

# 2. Config swaps.
assert "vocab_size: int = 32768" in src and "sequence_len: int = 2048" in src
src = src.replace("vocab_size: int = 32768", "vocab_size: int = 32")
src = src.replace("sequence_len: int = 2048", "sequence_len: int = 6144")

# 3. Batch size for 6GB at seq 6144.
src = re.sub(r"DEVICE_BATCH_SIZE = 8.*", "DEVICE_BATCH_SIZE = 4  # G1: seq 6144 on 6GB", src, count=1)
# TOTAL_BATCH must divide: tokens/fwdbwd = 4*6144 = 24576; 16 accum steps.
src = re.sub(r"TOTAL_BATCH_SIZE = 2\*\*19.*",
             "TOTAL_BATCH_SIZE = 4 * 6144 * 16  # G1: 393,216 tokens/step (16 accum)", src, count=1)

# 4. Cut everything from the Setup section onward; keep model+optimizer verbatim.
idx = src.index("# Setup: tokenizer")
cut = src.rindex("# ---------------------------------------------------------------------------", 0, idx)
head = src[:cut]

TAIL = '''
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
G5_THRESHOLDS = (0.1, 0.2, 0.3, 0.5)


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
        # G4: changed-cell loss mask (train only where the target differs from
        # the previous frame's same cell — the diff-target insight as a loss)
        self.loss_mask_mode = _os.environ.get("G4_LOSS_MASK", "0") == "1"
        if self.loss_mask_mode:
            Lw = 1728 + 1
            n = len(self.tokens)
            chg = np.zeros(n, dtype=bool)
            ii = np.arange(Lw, n)
            chg[ii] = (self.tokens[ii] != SEP) & (self.tokens[ii] != self.tokens[ii - Lw])
            self.chg = chg

    def __iter__(self):
        return self

    def __next__(self):
        B, T = self.batch, self.T
        xs = np.zeros((B, T), dtype=np.int64)
        ys = np.zeros((B, T), dtype=np.int64)
        n = len(self.tokens)
        for b in range(B):
            for _retry in range(20):
                i = int(self.rng.integers(0, n - T - 2))
                xs[b] = self.tokens[i:i + T]
                ys[b] = self.tokens[i + 1:i + 1 + T]
                if not self.loss_mask_mode:
                    break
                m = ~self.chg[i + 1:i + 1 + T]
                if int((~m).sum()) >= 100:  # need >=100 loss-bearing targets
                    ys[b][m] = -1
                    break
        self._calls += 1
        if self._calls % 500 == 0:
            self.epoch += 1
        import torch as _t
        return _t.from_numpy(xs).cuda(), _t.from_numpy(ys).cuda(), self.epoch


@torch.no_grad()
def evaluate_g1(model, streams, autocast_ctx):
    """Per-source test metrics: model acc/CE-per-cell vs persistence + majority,
    plus the G5 hybrid-refiner composite accuracy at each confidence threshold."""
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
        # G5 composite accumulators: per-threshold (full-cell, changed-cell) hits
        comp_correct = {thr: 0 for thr in G5_THRESHOLDS}
        comp_chg = {thr: 0 for thr in G5_THRESHOLDS}
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
            # G5 hybrid-refiner composite: prev_code = the previous frame's
            # same-cell token (global position j − (1728+1)); invalid before
            # the first frame → fall back to model argmax. Substitute the
            # model's argmax where (p_top − p(prev_code) > thr) AND
            # (argmax ≠ prev_code); persistence elsewhere.
            probs = logits[0].float().softmax(-1)
            p_top = probs.gather(1, pred[:, None]).squeeze(1)
            prev_idx = np.arange(i - T + 1, i + 1) - Lw
            prev_ok = prev_idx >= 0
            prev_code = torch.from_numpy(
                np.where(prev_ok, toks[np.clip(prev_idx, 0, None)], 0)).to(device)
            p_prev = probs.gather(1, prev_code[:, None]).squeeze(1)
            margin = p_top - p_prev
            prev_ok_t = torch.from_numpy(prev_ok).to(device)
            for thr in G5_THRESHOLDS:
                # invalid prev -> model argmax fallback; valid prev -> model
                # argmax only when confident it differs, else persistence
                use_model = (~prev_ok_t) | ((margin > thr) & (pred != prev_code))
                comp = torch.where(use_model, pred, prev_code)
                ok = (comp == yt[0]) & mask
                comp_correct[thr] += int(ok.sum().item())
                comp_chg[thr] += int((ok & cmask).sum().item())
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
            # On changed cells persistence is definitionally wrong (the mask is
            # prev_code != target), so persist_changed_acc is 0 wherever any
            # cell ever changed — recorded explicitly for the G5 gate.
            "persist_changed_acc": 0.0 if changed_total > 0 else None,
            "composite": {f"{thr}": {"acc": round(comp_correct[thr] / max(total, 1), 4),
                                     "changed_acc": round(comp_chg[thr] / max(changed_total, 1), 4)}
                          for thr in G5_THRESHOLDS},
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


def gate5(results):
    """G5 pre-registered gate: the composite must beat BOTH pure-persistence and
    the pure-model overall accuracy at some threshold, AND beat persistence on
    >=2 of 3 dynamic sources' changed-cell accuracy (at that same threshold).
    KILL if no threshold beats persistence overall; INCONCLUSIVE if persistence
    is beaten somewhere but the full KEEP bar is never met."""
    srcs = list(results)
    persist_overall = sum(results[s]["persist_acc"] for s in srcs) / len(srcs)
    model_overall = sum(results[s]["model_acc"] for s in srcs) / len(srcs)
    table = {}
    best_thr, best_acc = None, -1.0
    for thr in G5_THRESHOLDS:
        comp = sum(results[s]["composite"][f"{thr}"]["acc"] for s in srcs) / len(srcs)
        beats_persist_chg = sum(
            1 for s in DYNAMIC if s in results
            and results[s]["persist_changed_acc"] is not None
            and results[s]["composite"][f"{thr}"]["changed_acc"]
            > results[s]["persist_changed_acc"])
        table[f"{thr}"] = {"composite_overall": round(comp, 4),
                           "beats_persistence": comp > persist_overall,
                           "beats_model": comp > model_overall,
                           "dynamic_changed_beats": beats_persist_chg}
        if comp > persist_overall and comp > model_overall and beats_persist_chg >= 2 \
                and comp > best_acc:
            best_thr, best_acc = thr, comp
    if best_thr is not None:
        verdict = "KEEP"
    elif any(t["beats_persistence"] for t in table.values()):
        verdict = "INCONCLUSIVE"
    else:
        verdict = "KILL"
    return verdict, dict(persist_overall=round(persist_overall, 4),
                         model_overall=round(model_overall, 4),
                         best_threshold=best_thr,
                         best_composite_overall=round(best_acc, 4) if best_thr is not None else None,
                         thresholds=table)


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
        print(f"\\rstep {step:05d} ({100*progress:.1f}%) | loss {debiased:.4f} | "
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
    g5_verdict, g5_gate = gate5(results)
    legacy_verdict, legacy_gate = gate_verdict(results)
    verdict = g5_verdict
    t_end = time.time()
    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024 / 1024
    out = {
        "experiment": "G5 hybrid refiner composite (diff-trained model + persistence)",
        "verdict": verdict, "gate": g5_gate,
        "g1_style_gate": {"verdict": legacy_verdict, **legacy_gate},
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
'''

out = head + TAIL
open(DST, "w").write(out)
print(f"wrote {DST} ({len(out.splitlines())} lines)")
