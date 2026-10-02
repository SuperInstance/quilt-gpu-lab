#!/usr/bin/env python3
"""CURL-1 — JEV↔JEPA curl mesh (quilt arrangement experiment).

Six cells, real typesafe JEV verdicts, one run, frozen bars from
proposals/runs/curl1-plan.md (pushed before fire: 1bd74be).

Cells:
  curl1.enc1     perception : frame -> 16x16 -> seeded random proj -> 64-d unit latent
  curl1.jepa1    prediction : online ridge, predicts the curl (z_{t+1} - z_t) in latent space
  curl1.persist1 baseline   : zero curl
  curl1.jev1     judgment   : typesafe jev-latest noul per 10-step window
  curl1.router1  pinch      : 2 bad windows -> pinch jepa; 2 consecutive good -> re-admit
  curl1.led1     receipt    : results/curl1/*
"""
import json, time, urllib.request, urllib.error
from pathlib import Path
import numpy as np
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "curl1"
OUT = ROOT / "results" / "curl1"
OUT.mkdir(parents=True, exist_ok=True)

# ---------- frozen config (from curl1-plan.md) ----------
CFG = dict(
    seed_enc=7, seed_inject=13,
    latent_dim=64, grid=16,
    warmup=24,               # pairs before first prediction
    window=10,               # steps per JEV window
    theta=0.6,               # JEV noul gate
    bad_to_pinch=2, good_to_readmit=2,
    inject=(81, 100),        # 1-indexed steps t where jepa's INPUT z_t is scrambled
    buffer_k=40,             # sliding window of admitted pairs (clarification, receipts)
    ridge_lambda=1e-3,
    jev_model="jev-latest",
    jev_budget=16,
)

def load_token():
    tok = Path.home() / ".config/typesafe/token"
    return tok.read_text().strip()

def jev_call(token, state, questions, usage, log):
    body = json.dumps({"model": CFG["jev_model"], "state": state, "questions": questions}).encode()
    req = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone", data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=45) as r:
                resp = json.loads(r.read())
            usage["calls"] += 1
            usage["input_tokens"] += resp.get("usage", {}).get("input_tokens", 0)
            usage["output_tokens"] += resp.get("usage", {}).get("output_tokens", 0)
            usage["wall_s"] += round(time.time() - t0, 2)
            return resp
        except Exception as e:  # noqa: BLE001 - fail loud in ledger, retry bounded
            log.append({"event": "jev_retry", "attempt": attempt + 1, "error": repr(e)})
            time.sleep(2 * (attempt + 1))
    usage["calls"] += 1
    return {"answers": None, "error": "jev_unreachable_after_retries"}

# ---------- cells ----------
rng = np.random.default_rng(CFG["seed_enc"])
PROJ = rng.standard_normal((CFG["grid"] * CFG["grid"], CFG["latent_dim"]))

def enc1(frame_img):
    """perception cell: 64x64 gray -> 16x16 mean-pool -> random proj -> unit norm."""
    a = np.asarray(frame_img, dtype=np.float64)
    g = a.reshape(CFG["grid"], 4, CFG["grid"], 4).mean(axis=(1, 3)).ravel() / 255.0
    z = g @ PROJ
    return z / (np.linalg.norm(z) + 1e-12)

class Jepa1:
    """prediction cell: online ridge on admitted buffer; predicts ẑ=z_{t+1}; curl Δẑ=ẑ−z_t."""
    def __init__(self):
        self.X, self.Y = [], []
    def observe(self, z_t, z_t1):
        self.X.append(z_t); self.Y.append(z_t1)
        if len(self.X) > CFG["buffer_k"]:
            self.X.pop(0); self.Y.pop(0)
    def fit(self):
        X = np.array(self.X); Y = np.array(self.Y)
        lam = CFG["ridge_lambda"]
        self.W = Y.T @ X @ np.linalg.inv(X.T @ X + lam * np.eye(X.shape[1]))
    def predict(self, z_t):
        return self.W @ z_t

def cos_u(a, b):
    return float(a @ b)  # both unit-norm

# ---------- load data ----------
frames = sorted(DATA.glob("f_*.png"))
assert len(frames) >= 120, f"need frames, found {len(frames)}"
Z = [enc1(Image.open(p)) for p in frames]
N = len(Z)
T0 = CFG["warmup"]              # first predicted step index (z[T0] predicted from z[T0-1])
TEND = N - 1                    # last t we predict from
inject_lo, inject_hi = CFG["inject"]
rng_inj = np.random.default_rng(CFG["seed_inject"])
INJ = {t for t in range(inject_lo, inject_hi + 1) if T0 <= t <= TEND}
scramble_map = {}
for t in sorted(INJ):
    v = rng_inj.standard_normal(CFG["latent_dim"])
    scramble_map[t] = v / (np.linalg.norm(v) + 1e-12)

# ---------- smoke JEV first (1 budgeted call) ----------
token = load_token()
usage = dict(calls=0, input_tokens=0, output_tokens=0, wall_s=0.0)
ledger = []
smoke = jev_call(token,
    {"smoke": True, "jepa_mean_err": 0.10, "persist_mean_err": 0.30, "n": 10},
    {"gate": {"type": "noul", "question": "Is the JEPA prediction cell adding value over the persistence baseline in this window?",
              "instructions": "Answer true only if jepa_mean_err is meaningfully below persist_mean_err or jepa wins most steps. If similar or worse, false."}},
    usage, ledger)
smoke_ok = bool(smoke.get("answers"))
ledger.append({"event": "jev_smoke", "ok": smoke_ok, "raw": smoke})

QUESTION = {"gate": {"type": "noul",
    "question": "Is the JEPA prediction cell adding value over the persistence baseline in this window?",
    "instructions": "Answer true only if jepa_mean_err is meaningfully below persist_mean_err or jepa wins most steps. If similar or worse, false."}}

# ---------- run the mesh ----------
jepa = Jepa1()
for t in range(0, T0 - 1):     # warmup pairs z_t -> z_{t+1}, t = 0..T0-2 (0-indexed)
    jepa.observe(Z[t], Z[t + 1])
jepa.fit()

admitted = True
bad_streak = good_streak = 0
trace = []          # per-step dicts
windows = []        # per-window JEV verdicts
route_events = []

e_j, e_p, e_routed, routed_is_jepa = [], [], [], []
for t in range(T0, TEND + 1):  # 0-indexed: predict Z[t] from Z[t-1]; step label = t+1 (1-indexed frame)
    step_label = t + 1
    z_prev = Z[t - 1]
    z_in = scramble_map.get(t, z_prev)  # injection: sick input path on labeled steps 81..100
    z_true = Z[t]

    # --- serving ---
    if admitted:
        jepa.fit()
        z_hat = jepa.predict(z_in)
        e_j_step = 1.0 - cos_u(z_hat, z_true)
    else:
        e_j_step = None
    z_pers = z_prev
    e_p_step = 1.0 - cos_u(z_pers, z_true)
    path = "jepa" if admitted else "persist"
    e_r_step = e_j_step if admitted else e_p_step

    trace.append(dict(step=step_label, e_jepa=e_j_step, e_persist=e_p_step,
                      e_routed=e_r_step, path=path, injected=t in INJ))
    if e_j_step is not None:
        e_j.append(e_j_step)
    e_p.append(e_p_step); e_routed.append(e_r_step); routed_is_jepa.append(admitted)

    # --- learning (gated: sick/pinched cell doesn't learn) ---
    if admitted:
        jepa.observe(z_in, z_true)

    # --- window boundary -> JEV judgment + pinch router ---
    wlen = CFG["window"]
    idx = len(trace)
    if idx % wlen == 0 or t == TEND:
        w = trace[-wlen:] if idx >= wlen else trace
        jw = [x["e_jepa"] for x in w if x["e_jepa"] is not None]
        pw = [x["e_persist"] for x in w]
        jmean = float(np.mean(jw)) if jw else None
        pmean = float(np.mean(pw))
        wins = sum(1 for x in w if x["e_jepa"] is not None and x["e_jepa"] < x["e_persist"])
        state = dict(window_steps=[w[0]["step"], w[-1]["step"]], n=len(w),
                     jepa_mean_err=round(jmean, 4) if jmean is not None else None,
                     persist_mean_err=round(pmean, 4),
                     jepa_wins=f"{wins}/{len(jw) if jw else 0}",
                     note="errors = 1 - cosine on 64-d unit latents; baseline predicts next latent = current latent (zero curl)")
        resp = jev_call(token, state, QUESTION, usage, ledger) if usage["calls"] < CFG["jev_budget"] else None
        ans = (resp or {}).get("answers", {}) or {}
        gate = (ans.get("gate") or {}).get("noul")
        good = None if gate is None else (gate >= CFG["theta"])
        truth = (jmean is not None and jmean < pmean)
        agree = None if good is None else (good == truth)
        if good is True:
            good_streak += 1; bad_streak = 0
        elif good is False:
            bad_streak += 1; good_streak = 0
        if admitted and bad_streak >= CFG["bad_to_pinch"]:
            admitted = False; good_streak = 0; bad_streak = 0
            route_events.append(dict(step=w[-1]["step"], action="PINCH",
                                     reason=f"{CFG['bad_to_pinch']} bad windows", jev_noul=gate))
        elif (not admitted) and good_streak >= CFG["good_to_readmit"]:
            admitted = True; bad_streak = 0; good_streak = 0
            route_events.append(dict(step=w[-1]["step"], action="READMIT",
                                     reason=f"{CFG['good_to_readmit']} good windows", jev_noul=gate))
        windows.append(dict(state=state, noul=gate, good=good, truth_arithmetic=truth,
                            jev_agrees=agree, admitted_after=admitted, raw=resp))

# ---------- metrics & frozen verdicts ----------
def span(sel):
    rows = [x for x in trace if sel(x)]
    rj = [x["e_jepa"] for x in rows if x["e_jepa"] is not None]
    rp = [x["e_persist"] for x in rows]
    rr = [x["e_routed"] for x in rows]
    clean = [x for x in rows if not x["injected"]]
    cj = [x["e_jepa"] for x in clean if x["e_jepa"] is not None]
    cp = [x["e_persist"] for x in clean]
    hit = float(np.mean([x["e_jepa"] < x["e_persist"] for x in clean if x["e_jepa"] is not None])) if cj else 0.0
    return dict(n=len(rows), jepa_mean=float(np.mean(rj)) if rj else None,
                persist_mean=float(np.mean(rp)), routed_mean=float(np.mean(rr)),
                clean_hitrate=round(hit, 4), clean_jepa_mean=float(np.mean(cj)) if cj else None,
                clean_persist_mean=float(np.mean(cp)) if cp else None)

allspan = span(lambda x: True)
injspan = span(lambda x: x["injected"])
cleanspan = span(lambda x: not x["injected"])

pinch_events = [e for e in route_events if e["action"] == "PINCH"]
readmit_events = [e for e in route_events if e["action"] == "READMIT"]
h3a_pinched = any(inject_lo <= e["step"] <= inject_hi + CFG["window"] for e in pinch_events)
h3a_err = (injspan["routed_mean"] is not None and
           injspan["routed_mean"] <= 1.1 * injspan["persist_mean"])
heal_pinched = any(e["step"] > inject_hi for e in pinch_events)
first_pinch_after = min((e["step"] for e in pinch_events if e["step"] > inject_hi), default=None)
readmit_step = min((e["step"] for e in readmit_events if first_pinch_after and e["step"] > first_pinch_after), default=None)
h3b = readmit_step is not None and (readmit_step - inject_hi) <= 2 * CFG["window"]

verdicts = dict(
    H1=dict(name="jepa beats persistence on clean steps", value=cleanspan["clean_hitrate"],
            bar=">= 0.55", keep=bool(cleanspan["clean_hitrate"] >= 0.55)),
    H2=dict(name="routed <= always-jepa (gating free when competent)",
            routed_mean=allspan["routed_mean"],
            always_jepa_mean=float(np.mean([x["e_jepa"] for x in trace if x["e_jepa"] is not None])),
            keep=bool(allspan["routed_mean"] <= float(np.mean([x["e_jepa"] for x in trace if x["e_jepa"] is not None])) + 1e-4)),
    H3=dict(name="gate catches sick cell + recovers",
            pinch_during_or_1window=h3a_pinched, routed_le_1_1x_persist_injected=h3a_err,
            readmit_within_2windows=h3b, pinch_steps=[e["step"] for e in pinch_events],
            readmit_step=readmit_step,
            keep=bool(h3a_pinched and h3a_err and h3b)),
)

# ---------- plot ----------
fig, ax = plt.subplots(figsize=(13, 5))
steps = [x["step"] for x in trace]
ax.plot(steps, [x["e_persist"] for x in trace], label="persist (zero curl)", color="#888", lw=1)
jx = [(x["step"], x["e_jepa"]) for x in trace if x["e_jepa"] is not None]
ax.plot([s for s, _ in jx], [v for _, v in jx], label="jepa (learned curl)", color="#26a", lw=1.2)
rx = [(x["step"], x["e_routed"]) for x in trace if x["path"] == "jepa"]
px = [(x["step"], x["e_routed"]) for x in trace if x["path"] == "persist"]
ax.scatter([s for s, _ in rx], [v for _, v in rx], s=6, color="#26a", zorder=3, label="routed via jepa")
ax.scatter([s for s, _ in px], [v for _, v in px], s=6, color="#a62", zorder=3, label="routed via persist (pinched)")
ax.axvspan(inject_lo, inject_hi, color="#d33", alpha=0.12, label="injected sick-cell span")
for e in route_events:
    ax.axvline(e["step"], color=e["action"] == "PINCH" and "#d33" or "#2a2", ls="--", lw=1)
    ax.annotate(e["action"], (e["step"], ax.get_ylim()[1]), fontsize=8, rotation=90, va="top")
ax.set_xlabel("step (1-indexed frame)"); ax.set_ylabel("error = 1 − cosine")
ax.set_title("CURL-1: JEV↔JEPA curl mesh — online latent prediction, JEV-gated routing")
ax.legend(fontsize=8, loc="upper right"); fig.tight_layout()
fig.savefig(OUT / "curl1-trace.png", dpi=110)

# ---------- quilt record (the arrangement, portable) ----------
cells = [
    ("curl1.enc1", "perception", "seed=7;proj=256->64;pool=16x16;norm=unit"),
    ("curl1.jepa1", "prediction", f"model=ridge;lambda={CFG['ridge_lambda']};warmup={CFG['warmup']};buffer_k={CFG['buffer_k']};target=latent-curl"),
    ("curl1.persist1", "baseline", "curl=zero"),
    ("curl1.jev1", "judgment", f"provider=typesafe;model={CFG['jev_model']};type=noul;theta={CFG['theta']}"),
    ("curl1.router1", "pinch", f"window={CFG['window']};bad_to_pinch={CFG['bad_to_pinch']};good_to_readmit={CFG['good_to_readmit']}"),
    ("curl1.led1", "receipt", "sink=results/curl1"),
]
links = [
    ("curl1.enc1", "curl1.jepa1", "latent-stream"),
    ("curl1.enc1", "curl1.persist1", "latent-stream"),
    ("curl1.enc1", "curl1.jev1", "window-stats"),
    ("curl1.jepa1", "curl1.jev1", "pred-err"),
    ("curl1.persist1", "curl1.jev1", "base-err"),
    ("curl1.jev1", "curl1.router1", "graded-verdict"),
    ("curl1.router1", "curl1.jepa1", "gate:serving+learning"),
    ("curl1.router1", "curl1.led1", "route-events"),
    ("curl1.jev1", "curl1.led1", "raw-verdicts"),
]
with open(OUT / "cells.csv", "w") as f:
    f.write("addr,kind,dials\n")
    for c in cells: f.write(",".join(c) + "\n")
with open(OUT / "links.csv", "w") as f:
    f.write("from,to,relation\n")
    for l in links: f.write(",".join(l) + "\n")

# ---------- results ----------
results = dict(
    experiment="CURL-1", prereg="proposals/runs/curl1-plan.md", prereg_commit="1bd74be",
    config=CFG, n_frames=N,
    spans=dict(all=allspan, injected=injspan, clean=cleanspan),
    verdicts=verdicts, route_events=route_events,
    jev_usage=usage, jev_windows=[{k: v for k, v in w.items() if k != "raw"} for w in windows],
    jev_agreement=float(np.mean([w["jev_agrees"] for w in windows if w["jev_agrees"] is not None])) if any(w["jev_agrees"] is not None for w in windows) else None,
    raw_windows=windows, ledger=ledger,
    buffer_note="buffer = sliding last-K admitted pairs (K=40): pre-reg said 'gated buffer' without length; "
                "sliding window lets poison wash out and is recorded here as the concrete reading.",
)
(OUT / "curl1-results.json").write_text(json.dumps(results, indent=1, default=str))

print(json.dumps(dict(verdicts=verdicts, spans=dict(all=allspan, injected=injspan, clean=cleanspan),
                      route_events=route_events, jev_usage=usage,
                      jev_agreement=results["jev_agreement"]), indent=1, default=str))
