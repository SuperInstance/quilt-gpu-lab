"""D7 — quant-drift: does the reader's VERDICT survive fp16 -> int8 -> 4-bit?

Extends the queued E5 line (GPU-DOCKET D7). A small sentence-embedding
reader (BAAI/bge-small-en-v1.5) encodes a fixed held-out probe of synthetic
sentence pairs with known same/different labels through four precisions:
fp32 (control), fp16 (reference), int8 (bitsandbytes LLM.int8), and
4-bit NF4 (bitsandbytes, fp16 compute, double-quant).

Metrics per precision p (vs the fp16 reference):
  - mean cosine drift: mean over unique probe sentences of cos(emb_p, emb_fp16)
    (embeddings L2-normalized, so cosine = dot)
  - mean |pair-similarity delta| over probe pairs (does the SIMILARITY move?)
  - verdict-flip rate: fraction of probe pairs whose same/different decision
    differs from the fp16 decision at the SAME frozen threshold tau.

Pre-registered protocol (before any run):
  - lab seed 2718 seeds the probe generator; the probe set is fixed bytes.
  - tau is calibrated ONCE on a separate 60-pair calibration split under
    fp16 only (midpoint of mean same-pair and mean different-pair cosine),
    then frozen for every precision. The fp16 decisions define ground truth
    for flips; quantization is the treatment, not the threshold.
  - flip ceiling: 0.05. Smallest viable precision = nf4 if its flip rate is
    under the ceiling, else int8, else none.
  - fp32-vs-fp16 is run as a control: it prices the reference's own noise
    floor (drift + flips without any int8/NF4 quantization).
  - Verdict: KEEP iff some sub-fp16 precision holds flips under the ceiling
    (portable deploy is green, smallest viable named). If every quantization
    flips too many verdicts: KILL — the reader is not portable below fp16.
    Degenerate calibration (separation < 0.15) or a failed precision load:
    INCONCLUSIVE. Guard breach: ABORTED (booked by the wrapper, not here).

Runs in <2 GB VRAM; minutes per precision. Prints ONE JSON at the end.
"""
from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

import numpy as np
import torch

LAB = Path(__file__).resolve().parents[1]
RESULTS_MD = LAB / "RESULTS.md"
RESULTS_JSON = LAB / "results" / "d7_quant_drift.json"

SEED = 2718
MODEL_ID = "BAAI/bge-small-en-v1.5"
FLIP_CEILING = 0.05
MIN_SEPARATION = 0.15
N_PROBE_PAIRS = 240  # 120 same / 120 different (held out from calibration)
N_CAL_PAIRS = 60     # 30 same / 30 different (threshold calibration only)
MAX_SEQ = 64
BATCH = 64
PRECISIONS = ["fp32", "fp16", "int8", "nf4"]
BITS = {"fp32": 32, "fp16": 16, "int8": 8, "nf4": 4}

# 48 fully disjoint topics: subject x verb x object x place, every content
# word used by exactly one topic, so different-topic pairs share only
# stopwords. Verb tuples are (third-person, gerund) for template variety.
SUBJECTS = """chef carpenter dentist sailor librarian farmer pilot baker tailor plumber
judge banker miner barber painter poet dancer lawyer bishop mayor ranger coach surgeon
blacksmith clerk guard nurse priest actor singer author editor broker dealer driver welder
mason porter sentry scribe tutor usher vendor warden weaver brewer courier jeweler""".split()
VERBS = """builds paints mends guards carries studies writes bakes cleans repairs
measures plants raises drives serves teaches trades brews weaves polishes sorts folds
charts tracks lifts sweeps sketches inspects harvests barters carves stitches welds
hauls drafts files tunes calibrates verifies logs ships packs audits maps grades
sands solders lacquers""".split()
GERUNDS = """building painting mending guarding carrying studying writing baking cleaning repairing
measuring planting raising driving serving teaching trading brewing weaving polishing sorting folding
charting tracking lifting sweeping sketching inspecting harvesting bartering carving stitching welding
hauling drafting filing tuning calibrating verifying logging shipping packing auditing mapping grading
sanding soldering lacquering""".split()
OBJECTS = """lantern ledger compass crate violin anchor saddle mirror kettle chisel
bucket basket candle hammer ladder barrel net cleaver gyroscope hourglass
kaleidoscope locomotive marionette nutshell orb pendulum quilt sextant telescope urn
wheelbarrow xylophone yoke zither bellows drogue effigy furnace gargoyle jig
kite awning banister corbel dumbwaiter easel filigree gimbal""".split()
PLACES = """harbor orchard bakery forge library cellar attic meadow quarry studio
chapel tavern glacier canyon pier barn mill depot greenhouse lighthouse windmill
tunnel summit valley garden workshop observatory dockyard vineyard prairie hollow plateau
estuary tundra savanna courtyard cloister terrace rampart causeway thicket clearing grotto
ridge basin delta bluff marsh""".split()

TEMPLATES = [
    lambda s, v, vi, o, p: f"The {s} {v} the {o} near the {p}.",
    lambda s, v, vi, o, p: f"In the {p}, a {s} is {GERUNDS[vi]} the {o}.",
    lambda s, v, vi, o, p: f"A {s} {v} a {o} at the {p}.",
    lambda s, v, vi, o, p: f"{GERUNDS[vi].capitalize()} the {o}, the {s} works in the {p}.",
    lambda s, v, vi, o, p: f"The {s} who {v} the {o} is at the {p}.",
    lambda s, v, vi, o, p: f"At the {p}, the {o} is handled by a {s} who {v}.",
]

N_TOPICS = 48


def make_topics(rng: np.random.Generator) -> list[dict]:
    """Shuffle each vocab pool once; topic i takes slot i of every pool.

    Guarantees full content-word disjointness across topics (no shared
    subject/verb/object/place between any two topics).
    """
    pools = [rng.permutation(x).tolist() for x in (SUBJECTS, VERBS, OBJECTS, PLACES)]
    topics = []
    for i in range(N_TOPICS):
        topics.append({"s": pools[0][i], "v": pools[1][i], "vi": i, "o": pools[2][i], "p": pools[3][i]})
    return topics


def sentence(topic: dict, t_idx: int) -> str:
    return TEMPLATES[t_idx](topic["s"], topic["v"], topic["vi"], topic["o"], topic["p"])


def gen_pairs(topics: list[dict], rng: np.random.Generator, n_pairs: int) -> list[dict]:
    """Balanced same/different pairs with known labels."""
    pairs = []
    n_same = n_diff = n_pairs // 2
    for _ in range(n_same):
        t = topics[int(rng.integers(N_TOPICS))]
        a = int(rng.integers(len(TEMPLATES)))
        b = (a + 1 + int(rng.integers(len(TEMPLATES) - 1))) % len(TEMPLATES)
        pairs.append({"label": 1, "s1": sentence(t, a), "s2": sentence(t, b)})
    for _ in range(n_diff):
        i = int(rng.integers(N_TOPICS))
        j = (i + 1 + int(rng.integers(N_TOPICS - 1))) % N_TOPICS
        a = int(rng.integers(len(TEMPLATES)))
        b = int(rng.integers(len(TEMPLATES)))
        pairs.append({"label": 0, "s1": sentence(topics[i], a), "s2": sentence(topics[j], b)})
    return pairs


def model_kwargs(precision: str) -> dict:
    from transformers import BitsAndBytesConfig

    if precision == "fp32":
        return {"dtype": torch.float32}
    if precision == "fp16":
        return {"dtype": torch.float16}
    if precision == "int8":
        return {"dtype": torch.float16, "device_map": {"": 0}, "quantization_config": BitsAndBytesConfig(load_in_8bit=True,
                                                                                  llm_int8_threshold=6.0)}
    if precision == "nf4":
        return {"dtype": torch.float16, "device_map": {"": 0}, "quantization_config": BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True)}
    raise ValueError(precision)


def encode_all(precision: str, texts: list[str], dev: str) -> tuple[np.ndarray, float]:
    """Load MODEL_ID at `precision`, encode texts (L2-normalized), free VRAM."""
    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    kw = model_kwargs(precision)
    try:
        model = SentenceTransformer(MODEL_ID, device=dev, model_kwargs=kw)
    except TypeError:
        # transformers version expects the old kwarg name
        kw2 = {("torch_dtype" if k == "dtype" else k): v for k, v in kw.items()}
        model = SentenceTransformer(MODEL_ID, device=dev, model_kwargs=kw2)
    model.max_seq_length = MAX_SEQ
    emb = model.encode(texts, batch_size=BATCH, convert_to_numpy=True,
                       normalize_embeddings=True, show_progress_bar=False)
    secs = time.time() - t0
    del model
    if dev == "cuda":
        torch.cuda.empty_cache()
    return np.asarray(emb, dtype=np.float32), secs


def main() -> dict:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    rng = np.random.default_rng(SEED)

    # ---- probe construction (fixed bytes, seed 2718) --------------------
    assert len(VERBS) == len(GERUNDS), "verb/gerund pools out of parallel"
    assert all(len(x) == N_TOPICS and len(set(x)) == N_TOPICS for x in (SUBJECTS, VERBS, OBJECTS, PLACES)), \
        "vocab authoring bug: need 48 distinct entries per pool"
    topics = make_topics(rng)
    cal_pairs = gen_pairs(topics, rng, N_CAL_PAIRS)
    probe_pairs = gen_pairs(topics, rng, N_PROBE_PAIRS)
    texts = sorted({p["s1"] for p in cal_pairs + probe_pairs} | {p["s2"] for p in cal_pairs + probe_pairs})
    idx = {t: i for i, t in enumerate(texts)}

    # ---- run every precision -------------------------------------------
    embs: dict[str, np.ndarray] = {}
    loads: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for prec in PRECISIONS:
        try:
            embs[prec], secs = encode_all(prec, texts, dev)
            loads[prec] = {"seconds": round(secs, 2), "dim": int(embs[prec].shape[1])}
            print(f"[d7] {prec}: encoded {len(texts)} sentences in {secs:.1f}s", flush=True)
        except Exception as e:  # book the failure, keep the curve honest
            errors[prec] = f"{type(e).__name__}: {e}"
            print(f"[d7] {prec}: FAILED {errors[prec]}", flush=True)

    if "fp16" not in embs:
        raise RuntimeError("fp16 reference failed; nothing to compare against")

    ref = embs["fp16"]
    sim = lambda e: e @ e.T  # normalized -> dot = cosine

    cal_cos_fp16 = np.array([sim(ref)[idx[p["s1"]], idx[p["s2"]]] for p in cal_pairs])
    same = cal_cos_fp16[np.array([p["label"] for p in cal_pairs]) == 1]
    diff = cal_cos_fp16[np.array([p["label"] for p in cal_pairs]) == 0]
    m_same, m_diff = float(same.mean()), float(diff.mean())
    tau = (m_same + m_diff) / 2.0
    calibration_ok = (m_same - m_diff) >= MIN_SEPARATION

    S = ref @ ref.T
    probe_ref_cos = np.array([S[idx[p["s1"]], idx[p["s2"]]] for p in probe_pairs])
    decisions_ref = (probe_ref_cos >= tau)

    per_precision = {}
    for prec in PRECISIONS:
        if prec not in embs:
            per_precision[prec] = {"error": errors.get(prec, "not run")}
            continue
        e = embs[prec]
        drift = (e * ref).sum(1)  # per-sentence cosine to fp16 reference
        delta = np.abs(e @ e.T - S)  # pair-similarity movement vs reference
        pair_cos = np.array([ (e @ e.T)[idx[p["s1"]], idx[p["s2"]]] for p in probe_pairs ])
        flips = int(((pair_cos >= tau) != decisions_ref).sum())
        per_precision[prec] = {
            "bits": BITS[prec],
            "mean_cos_drift": float(drift.mean()),
            "min_cos_drift": float(drift.min()),
            "mean_pair_sim_absdelta": float(delta.mean()),
            "probe_flips": flips,
            "flip_rate": flips / len(probe_pairs),
        }

    sub_fp16 = ["int8", "nf4"]
    incomplete = [p for p in sub_fp16 if "flip_rate" not in per_precision[p]]
    qualifies = [p for p in sub_fp16 if "flip_rate" in per_precision[p]
                 and per_precision[p]["flip_rate"] < FLIP_CEILING]
    smallest_viable = next((p for p in ["nf4", "int8"] if p in qualifies), None)

    if not calibration_ok:
        verdict = "INCONCLUSIVE"
        reason = (f"degenerate calibration: same/diff means {m_same:.3f}/{m_diff:.3f} "
                  f"(need gap >= {MIN_SEPARATION})")
    elif incomplete:
        verdict = "INCONCLUSIVE"
        reason = f"precision load failure, curve incomplete: {incomplete} ({[errors[p] for p in incomplete]})"
    elif smallest_viable:
        verdict = "KEEP"
        reason = (f"{smallest_viable} holds probe flip-rate "
                  f"{per_precision[smallest_viable]['flip_rate']:.4f} < ceiling {FLIP_CEILING}")
    else:
        verdict = "KILL"
        reason = ("no sub-fp16 precision under flip ceiling "
                  f"{FLIP_CEILING}; reader not portable below fp16")

    out = {
        "experiment": "D7 quant-drift",
        "device": dev,
        "seed": SEED,
        "model": MODEL_ID,
        "max_seq_length": MAX_SEQ,
        "probe": {
            "n_unique_sentences": len(texts),
            "n_cal_pairs": len(cal_pairs),
            "n_probe_pairs": len(probe_pairs),
            "balanced_labels": True,
        },
        "calibration": {
            "threshold_tau": round(tau, 4),
            "fp16_mean_same_cos": round(m_same, 4),
            "fp16_mean_diff_cos": round(m_diff, 4),
            "separation": round(m_same - m_diff, 4),
            "protocol": "tau from fp16 cal split only, frozen for all precisions",
        },
        "flip_ceiling": FLIP_CEILING,
        "precisions": per_precision,
        "smallest_viable_precision": smallest_viable,
        "verdict": verdict,
        "reason": reason,
        "loads": loads,
        "versions": _versions(),
    }
    RESULTS_JSON.parent.mkdir(exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(out, indent=2) + "\n")
    append_ledger(out)
    print(json.dumps(out, indent=2))
    return out


def append_ledger(out: dict) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    n_probe = out["probe"]["n_probe_pairs"]
    rows = "\n".join(
        f"| {p} | {m['bits']} | {m['mean_cos_drift']:.4f} | {m['mean_pair_sim_absdelta']:.4f} "
        f"| {m['probe_flips']}/{n_probe} | {m['flip_rate']:.4f} |"
        for p, m in out["precisions"].items() if "flip_rate" in m)
    block = (
        f"\n## D7 — quant-drift (portability probe)\n"
        f"- ran: {ts}\n"
        f"- verdict: **{out['verdict']}**\n"
        f"- result: ```json\n{json.dumps(out, indent=2)}\n```\n"
        f"- drift/flip table (probe pairs={out['probe']['n_probe_pairs']}, "
        f"tau={out['calibration']['threshold_tau']}, ceiling={out['flip_ceiling']}):\n\n"
        f"| precision | bits | mean cos drift vs fp16 | mean pair-sim abs-delta | probe flips | flip rate |\n"
        f"|---|---|---|---|---|---|\n"
        f"{rows}\n\n"
        f"- note: {out['reason']}. fp32-vs-fp16 rows price the reference's own noise "
        f"floor (no int8/NF4 treatment). E5 line closes into D7 (cross-link: "
        f"GPU-DOCKET D7 'cross-link the closed E5 line').\n"
    )
    with RESULTS_MD.open("a") as f:
        f.write(block)


def _versions() -> dict:
    import bitsandbytes
    import sentence_transformers
    import transformers

    return {"torch": torch.__version__, "transformers": transformers.__version__,
            "sentence_transformers": sentence_transformers.__version__,
            "bitsandbytes": bitsandbytes.__version__}


if __name__ == "__main__":
    main()
