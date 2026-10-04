#!/usr/bin/env python3
"""W5-B GATE-SEMANTICS SHOOTOUT — pure recompute over v5a_board.json (0 GPU).
Frozen before run:
  G1: min-gate (clip AND dino AND ijepa >= 0.80) rejects 4/4 morphs AND
      retains >= 50% of CLIP-alone-accepted non-morphs
  G2: dino-primary (dino >= 0.80) rejects 4/4 morphs AND retains >= 60% of
      CLIP-accepted non-morphs
  G3: some semantics in the scan (floor 0.70-0.90 x {majority,min,dino-primary})
      achieves morph-rejects >= 3/4 AND non-morph retention >= 80%
Honest FAIL allowed. Context: W5-A found DINOv2 is the only morph detector
(0.34-0.50 on morphs); IJEPA asleep (0.80-0.91); majority waves 2/4 through.
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
board = json.loads((HERE / "v5a_board.json").read_text())
arts = board["artifacts"]
J = ("clip", "dino", "ijepa")
FLOOR = 0.80

morphs = [a for a in arts if a["name"].startswith(("xcasey", "xlucineer"))]
non = [a for a in arts if a["name"] not in {m["name"] for m in morphs}]
legacy_accepts = [a for a in non if a["clip"] >= FLOOR]
n_legacy = len(legacy_accepts)

def evaluate(name, pred):
    kept = [a for a in non if pred(a)]
    kept_legacy = [a for a in kept if a["clip"] >= FLOOR]
    rej = [m["name"] for m in morphs if not pred(m)]
    return {"semantics": name, "morph_rejects": f"{len(rej)}/4",
            "rejected_morphs": rej,
            "nonmorph_accepts": len(kept), "legacy_accepts": n_legacy,
            "retention_of_legacy": round(len(kept_legacy) / max(1, n_legacy), 4)}

results = [
    evaluate("clip-alone (legacy)", lambda a: a["clip"] >= FLOOR),
    evaluate("majority-of-3 @0.80", lambda a: sum(a[j] >= FLOOR for j in J) > 1.5),
    evaluate("min-gate @0.80", lambda a: all(a[j] >= FLOOR for j in J)),
    evaluate("dino-primary @0.80", lambda a: a["dino"] >= FLOOR),
    evaluate("dino-primary @0.70", lambda a: a["dino"] >= 0.70),
    evaluate("dino-primary @0.60", lambda a: a["dino"] >= 0.60),
]

# G3 scan
best, best_score = None, None
for floor in (0.70, 0.75, 0.80, 0.85, 0.90):
    cands = {
        "majority": lambda a, f=floor: sum(a[j] >= f for j in J) > 1.5,
        "min": lambda a, f=floor: all(a[j] >= f for j in J),
        "dino-primary": lambda a, f=floor: a["dino"] >= f,
    }
    for kind, pred in cands.items():
        rej = [m for m in morphs if not pred(m)]
        kept_legacy = [a for a in non if pred(a) and a["clip"] >= FLOOR]
        ret = len(kept_legacy) / max(1, n_legacy)
        score = (len(rej) >= 3) + (ret >= 0.80)
        if best_score is None or (score, ret, len(rej)) > (best_score[0], best_score[1], best_score[2]):
            best = {"floor": floor, "kind": kind, "morph_rejects": f"{len(rej)}/4",
                    "retention_of_legacy": round(ret, 4)}
            best_score = (score, ret, len(rej))
g3_pass = best_score[0] == 2 if best_score else False

r = {m: {k: v for k, v in e.items() if k != "rejected_morphs"} for m, e in
     zip([e["semantics"] for e in results], results)}
claims = {
    "G1": {"claim": "min-gate @0.80 rejects 4/4 morphs, retains >=50% legacy",
           **{k: results[2][k] for k in ("morph_rejects", "retention_of_legacy")},
           "pass": len(results[2]["rejected_morphs"]) == 4 and results[2]["retention_of_legacy"] >= 0.50},
    "G2": {"claim": "dino-primary @0.80 rejects 4/4 morphs, retains >=60% legacy",
           **{k: results[3][k] for k in ("morph_rejects", "retention_of_legacy")},
           "pass": len(results[3]["rejected_morphs"]) == 4 and results[3]["retention_of_legacy"] >= 0.60},
    "G3": {"claim": "scanned semantics hits >=3/4 morph rejects AND >=80% legacy retention",
           "best": best, "pass": bool(g3_pass)},
}
out = {"experiment": "w5b-gate-semantics", "n": len(arts),
       "morphs": len(morphs), "nonmorphs": len(non), "legacy_accepts": n_legacy,
       "claims_frozen_in_header": True, "results": results, "claims": claims}
(HERE / "v5b_gate_semantics.json").write_text(json.dumps(out, indent=1))
print("CLAIMS", json.dumps({k: v["pass"] for k, v in claims.items()}))
for e in results:
    print(f"  {e['semantics']:22s} morphs {e['morph_rejects']}  legacy-retention {e['retention_of_legacy']}  accepts {e['nonmorph_accepts']}")
print("G3 best:", json.dumps(best))
