#!/usr/bin/env python3
"""correlate — the relational synthesis tool.

Reads N text artifacts and finds the *consistent target* via the correlation
primitive (D13d/D18): which artifacts co-vary (point at the same thing), what
they jointly converged on (cross-document agreement), and which are redundant
(near-duplicate). Correlation = cosine over TF-IDF-weighted feature-hashed
n-grams. Pure stdlib, O(chunk) memory, deterministic (hash seed 2718).

  - clusters: connected components above --min-corr (default 0.15)
  - redundant: pairs above --redundant (default 0.90) = near-duplicate lanes
  - consistent target: terms/phrases present in >= half the docs = the shared
    claims the fan-out converged on (the synthesis seed)

Usage:
  python3 tools/correlate.py [--min-corr F] [--redundant F] [--top-k N] [--json] FILES...
"""
import sys, re, json, math, hashlib, os
from collections import Counter, defaultdict

DIM = 4096
NGRAM = 2

STOP = set("a an and are as at be but by for from had has have he her his i if in into is it its of on or our she so that the their them they this to was we were what when which who will with you not no all also can may more most one two over under than then there these those about after before between during without through across each both few many such because while within against it".split())

def tokenize(text):
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    text = re.sub(r'`[^`]*`', ' ', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[#>*_|=\-]+', ' ', text)
    toks = re.findall(r"[a-z][a-z0-9_\-]{1,}", text.lower())
    return [t for t in toks if t not in STOP]

def h(s):
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:8], 'little') % DIM

def feats(toks):
    v = [0.0] * DIM
    for t in toks:
        v[h(t)] += 1.0
    for n in range(2, NGRAM + 1):
        for i in range(len(toks) - n + 1):
            v[h(' '.join(toks[i:i+n]))] += 1.0
    return v

def idf_weight(vectors):
    n = len(vectors)
    df = [0] * DIM
    for v in vectors:
        for f in range(DIM):
            if v[f] > 0:
                df[f] += 1
    return [math.log((n + 1) / (df[f] + 1)) + 1.0 for f in range(DIM)]

def cosine_matrix(vectors, idf):
    n = len(vectors)
    nrm = []
    for v in vectors:
        s = math.sqrt(sum((v[f] * idf[f]) ** 2 for f in range(DIM)))
        nrm.append([v[f] * idf[f] / s for f in range(DIM)] if s > 0 else [0.0] * DIM)
    R = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            c = sum(nrm[i][f] * nrm[j][f] for f in range(DIM))
            R[i][j] = R[j][i] = c
    return R

def clusters(R, thr):
    n = len(R)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            if R[i][j] >= thr:
                union(i, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=len, reverse=True)

def cross_doc_terms(all_tokens, frac=0.5):
    nd = len(all_tokens)
    df = Counter()
    tf = Counter()
    sets = []
    for toks in all_tokens:
        grams = set(toks)
        grams |= set(' '.join(toks[i:i+2]) for i in range(len(toks) - 1))
        sets.append(grams)
    for s in sets:
        for g in s:
            df[g] += 1
    for toks in all_tokens:
        for t in toks:
            tf[t] += 1
        for i in range(len(toks) - 1):
            tf[' '.join(toks[i:i+2])] += 1
    thr = int(nd * frac) + 1
    shared = [(g, df[g], tf[g]) for g in df if df[g] >= thr]
    shared.sort(key=lambda x: (-x[1], -x[2]))
    return shared

def main():
    argv = sys.argv[1:]
    min_corr, redundant, top_k, as_json = 0.15, 0.90, 25, False
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--min-corr' and i + 1 < len(argv):
            min_corr = float(argv[i+1]); i += 2
        elif a == '--redundant' and i + 1 < len(argv):
            redundant = float(argv[i+1]); i += 2
        elif a == '--top-k' and i + 1 < len(argv):
            top_k = int(argv[i+1]); i += 2
        elif a == '--json':
            as_json = True; i += 1
        else:
            files.append(a); i += 1
    if not files:
        print(__doc__)
        sys.exit(1)
    names = [os.path.basename(f) for f in files]
    all_tokens = []
    vectors = []
    for f in files:
        text = open(f, encoding='utf-8', errors='replace').read()
        toks = tokenize(text)
        all_tokens.append(toks)
        vectors.append(feats(toks))
    idf = idf_weight(vectors)
    R = cosine_matrix(vectors, idf)
    clus = clusters(R, min_corr)
    shared = cross_doc_terms(all_tokens)
    redundant_pairs = [(names[i], names[j], round(R[i][j], 3))
                       for i in range(len(files)) for j in range(i+1, len(files))
                       if R[i][j] >= redundant]
    pairs = [(names[i], names[j], round(R[i][j], 3))
             for i in range(len(files)) for j in range(i+1, len(files))]
    pairs.sort(key=lambda x: -x[2])
    out = {
        "n_artifacts": len(files),
        "names": names,
        "clusters": [[names[i] for i in c] for c in clus],
        "redundant_pairs": redundant_pairs,
        "top_correlations": pairs[:top_k],
        "consistent_target": shared[:top_k],
    }
    if as_json:
        print(json.dumps(out, indent=2))
    else:
        print(f"== correlate: {len(files)} artifacts ==")
        print(f"\n[clusters @ corr>={min_corr}]")
        for c in clus:
            if len(c) > 1:
                print("  • " + " <-> ".join(names[i] for i in c))
            else:
                print(f"  · {names[c[0]]}  (isolated)")
        if redundant_pairs:
            print(f"\n[redundant @ corr>={redundant}]")
            for a, b, r in redundant_pairs:
                print(f"  ! {a} ≈ {b}  ({r})")
        print("\n[top correlations]")
        for a, b, r in pairs[:15]:
            print(f"  {r:+.3f}  {a} <-> {b}")
        print(f"\n[consistent target (in ≥ {int(len(files)*0.5)+1} of {len(files)} docs)]")
        for g, d, t in shared[:top_k]:
            print(f"  {d}/{len(files)}  {g}  (freq {t})")

if __name__ == '__main__':
    main()
