import sys; sys.path.insert(0,"/home/eileen/projects/quilt-gpu-lab")
import json, numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from experiments.comp1_federation2 import feat_word, KINDS
rows=[json.loads(l) for l in open("results/comp1/corpus.jsonl")]
tr=[r for r in rows if int(r["sha256"][0],16)<12]; he=[r for r in rows if int(r["sha256"][0],16)>=12]
Xtr=np.stack([feat_word(r) for r in tr]); ytr=np.array([1 if r["label"]=="canon" else 0 for r in tr])
Xhe=np.stack([feat_word(r) for r in he]); yhe=np.array([1 if r["label"]=="canon" else 0 for r in he])
accs=[]
for s in (2718,2719,2720):
    clf=LogisticRegression(C=1.0,solver="lbfgs",max_iter=5000,random_state=s).fit(Xtr,ytr)
    accs.append((clf.predict(Xhe)==yhe).mean())
print("COMP1 corpus n_train",len(tr),"n_held",len(he))
print("probe full acc per seed",[round(a,4) for a in accs],"mean",round(float(np.mean(accs)),4),"std",round(float(np.std(accs)),6))
for k in KINDS:
    idx=[i for i,r in enumerate(he) if r["kind"]==k]
    clf=LogisticRegression(C=1.0,solver="lbfgs",max_iter=5000,random_state=2718).fit(Xtr,ytr)
    print(f"  {k}: {(clf.predict(Xhe[idx])==yhe[idx]).mean():.4f} (n={len(idx)}, chance={max(yhe[idx].mean(),1-yhe[idx].mean()):.4f})")
