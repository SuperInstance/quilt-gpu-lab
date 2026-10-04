import json, numpy as np, sys
sys.path.insert(0,'.')
from experiments.comp1_federation2 import pearson, y_of
REG=["semantic","counting-address","negation-scope","agent-role"]
SENS=["S1","S2","S3","S4"]
MATCH={"semantic":"S2","counting-address":"S1","negation-scope":"S4","agent-role":"S3"}
REG_OF={v:k for k,v in MATCH.items()}
z=np.load('scratch/comp2_smoke/raw/features.npz')
Ftr={s:z[f"tr_{s}"] for s in SENS}; Fhe={s:z[f"he_{s}"] for s in SENS}
items=[json.loads(l) for l in open('results/comp2_corpus/corpus.jsonl')]
tr=[it for it in items if int(it['sha256'][0],16)<12]; he=[it for it in items if int(it['sha256'][0],16)>=12]
reg_tr=np.array([it['kind'] for it in tr]); reg_he=np.array([it['kind'] for it in he])
# Variant B: per-sensor centroid of the regime that sensor is MATCHED to
sc=np.zeros((len(he),4))
for k,s in enumerate(SENS):
    r=REG_OF[s]; cent=Ftr[s][reg_tr==r].mean(axis=0)
    for i in range(len(he)): sc[i,k]=pearson(Fhe[s][i],cent)
top=np.array([REG_OF[SENS[k]] for k in sc.argmax(1)])
print("Variant B per-sensor centroid-of-matched-regime top1:", round((top==reg_he).mean(),4))
# Variant B2: all per-(sensor,regime) centroids; score of sensor k = pearson(item_Sk, cent_{k,r_k}) -- same as B
# Variant C: COMP1 verbatim S1 per-regime centroids, top1
cent={r:Ftr["S1"][reg_tr==r].mean(axis=0) for r in REG}
sc2=np.stack([[pearson(Fhe["S1"][i],cent[r]) for r in REG] for i in range(len(he))])
print("Variant C COMP1-S1 per-regime centroid top1:", round((np.array(REG)[sc2.argmax(1)]==reg_he).mean(),4))
# Variant D: average over sensors of per-(sensor,regime) centroid pearson
scd=np.zeros((len(he),4))
for k,s in enumerate(SENS):
    for ri,r in enumerate(REG):
        c=Ftr[s][reg_tr==r].mean(axis=0)
        scd[:,ri]+=np.array([pearson(Fhe[s][i],c) for i in range(len(he))])
print("Variant D sensor-averaged per-regime centroid top1:", round((np.array(REG)[scd.argmax(1)]==reg_he).mean(),4))
# Variant E: max over sensors of per-(sensor,regime) pearson
sce=np.zeros((len(he),4))
for k,s in enumerate(SENS):
    for ri,r in enumerate(REG):
        c=Ftr[s][reg_tr==r].mean(axis=0)
        sce[:,ri]=np.maximum(sce[:,ri],np.array([pearson(Fhe[s][i],c) for i in range(len(he))]))
print("Variant E sensor-max per-regime centroid top1:", round((np.array(REG)[sce.argmax(1)]==reg_he).mean(),4))
