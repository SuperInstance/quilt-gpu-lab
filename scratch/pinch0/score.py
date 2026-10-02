#!/usr/bin/env python3
"""PINCH0 LANE 2 — STEP 3/4 scoring against pre-registered gate.

Gate (pre-registered in CRAWL-RECEIPT.md before scoring):
    PINCH0_VIABLE iff precision@1 >= 0.50 AND MRR >= 0.60 on the 24 delivered edge rows.

Query = src card purpose+setup text. Candidates = all repo cards (full card text).
Cosine similarity via @cf/baai/bge-m3 embeddings.
"""
import json, os, sys
import numpy as np

sys.path.insert(0, "/home/eileen/projects/quilt-gpu-lab/scratch/pinch0")
import cf_embed as ce

SCRATCH = ce.SCRATCH
EMBDIR = ce.EMBDIR
DIM = ce.DIM
GATE_P1, GATE_MRR = 0.50, 0.60


def load_index():
    cards = ce.load_cards()
    ids = [json.loads(l)["repo"] for l in open(os.path.join(EMBDIR, "ids.jsonl"))]
    V = np.fromfile(os.path.join(EMBDIR, "vectors.f32"), dtype="<f4").reshape(-1, DIM)
    assert len(ids) == V.shape[0], (len(ids), V.shape)
    # align cards to ids (ids are in cards order, possibly truncated on incomplete run)
    by_repo = {c["repo"]: c for c in cards}
    ok = [i for i, r in enumerate(ids) if r in by_repo]
    ids = [ids[i] for i in ok]
    V = V[ok]
    V = V / np.linalg.norm(V, axis=1, keepdims=True)
    return cards, by_repo, ids, V


def query_text(c):
    """purpose + setup fields only (per lane instruction)."""
    s = c.get("setup") or {}
    parts = [c.get("purpose", "")]
    parts.append(str(s.get("layout", "")))
    parts.append(str(s.get("build_run", "")))
    ents = s.get("entrypoints") or []
    if ents:
        parts.append("entrypoints: " + ", ".join(map(str, ents)))
    return " | ".join(p for p in parts if p)


def embed_queries(texts):
    tok, acct = ce.get_token()
    out = []
    for i in range(0, len(texts), 12):
        out.extend(ce.embed(texts[i:i + 12], tok, acct))
    return np.array(out, dtype=np.float32)


def rank_of(qvec, ids, V, target):
    sims = V @ qvec
    order = np.argsort(-sims)
    ranked = [ids[i] for i in order]
    return ranked.index(target) + 1, ranked, sims[order]


def main():
    cards, by_repo, ids, V = load_index()
    edges = json.load(open(os.path.join(SCRATCH, "edges_referral.json")))
    probes = json.load(open(os.path.join(SCRATCH, "probes.json")))

    # ---- edges
    rows = []
    used = [e for e in edges if e["from"] in by_repo and e["to"] in ids]
    qtexts = [query_text(by_repo[e["from"]]) for e in used]
    Q = embed_queries(qtexts)
    Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)
    hit1 = 0
    rr = 0.0
    for e, qv in zip(used, Q):
        r, ranked, sims = rank_of(qv, ids, V, e["to"])
        rows.append({"from": e["from"], "to": e["to"], "status": e["status"],
                     "rank": r, "p@1": 1 if r == 1 else 0, "rr": 1.0 / r,
                     "top1": ranked[0], "top3": ranked[:3]})
        hit1 += 1 if r == 1 else 0
        rr += 1.0 / r
    n = len(used)
    p1 = hit1 / n
    mrr = rr / n

    def subset(pred):
        s = [x for x in rows if pred(x)]
        if not s:
            return None
        return {"n": len(s), "p@1": sum(x["p@1"] for x in s) / len(s),
                "mrr": sum(x["rr"] for x in s) / len(s)}

    verdict = "VIABLE" if (p1 >= GATE_P1 and mrr >= GATE_MRR) else "NOT_VIABLE"

    # ---- probes
    pq = embed_queries([p["query"] for p in probes])
    pq = pq / np.linalg.norm(pq, axis=1, keepdims=True)
    pres = []
    for p, qv in zip(probes, pq):
        r, ranked, _ = rank_of(qv, ids, V, p["target"])
        pres.append({"query": p["query"], "target": p["target"], "rank": r,
                     "p@1": 1 if r == 1 else 0, "top3": ranked[:3]})
    probe_p1 = sum(x["p@1"] for x in pres) / len(pres)
    probe_mrr = sum(1.0 / x["rank"] for x in pres) / len(pres)

    out = {
        "crawl": {"n_cards": len(cards), "n_embedded": len(ids),
                  "coverage": len(ids) / len(cards), "dim": DIM,
                  "model": ce.MODEL},
        "gate_preregistered": {"precision@1_min": GATE_P1, "mrr_min": GATE_MRR,
                               "primary_set": "24 delivered edge rows"},
        "edges": {"n": n, "precision@1": p1, "mrr": mrr,
                  "bysubset": {"verified_labeled": subset(lambda x: x["status"] == "VERIFIED"),
                               "pending_labeled": subset(lambda x: x["status"] == "PENDING")},
                  "rows": rows},
        "probes": {"n": len(pres), "precision@1": probe_p1, "mrr": probe_mrr, "rows": pres},
        "verdict": verdict,
    }
    dest = "/home/eileen/projects/quilt-gpu-lab/results/pinch0/SCORES.json"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps({k: out[k] for k in ("crawl", "gate_preregistered")}, indent=2))
    print("EDGES n=%d p@1=%.3f MRR=%.3f" % (n, p1, mrr))
    print("PROBES n=%d p@1=%.3f MRR=%.3f" % (len(pres), probe_p1, probe_mrr))
    print("VERDICT:", verdict)
    print("wrote", dest)


if __name__ == "__main__":
    main()
