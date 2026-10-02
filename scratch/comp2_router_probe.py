import json, numpy as np, sys
sys.path.insert(0,'.')
from sklearn.linear_model import LogisticRegression
from experiments.comp2_arms import (load_corpus, featurize, _centroid_scores, _cheap_margins, SENSORS, REGIMES, MATCH, REGIME_OF_SENSOR)
from pathlib import Path
tr,he=load_corpus(Path('results/comp2_corpus/corpus.jsonl'))
z=np.load('scratch/comp2_smoke/raw/features.npz')
Ftr={s:z[f"tr_{s}"] for s in SENSORS}; Fhe={s:z[f"he_{s}"] for s in SENSORS}
ytr=np.array([1 if it['label']=='canon' else 0 for it in tr],dtype=np.float32)
reg_tr=np.array([it['regime'] for it in tr]); reg_he=np.array([it['regime'] for it in he])
cen_tr=_centroid_scores(Ftr,Ftr,reg_tr); cen_he=_centroid_scores(Ftr,Fhe,reg_tr)
_,mar_tr=_cheap_margins(Ftr,ytr,Ftr); _,mar_he=_cheap_margins(Ftr,ytr,Fhe)
print('cen feature means train', cen_tr.mean(0).round(3), 'std', cen_tr.std(0).round(3))
print('mar feature means train', mar_tr.mean(0).round(3))
def fit(Xtr,Xhe,tag):
    c=LogisticRegression(solver='lbfgs',C=1.0,max_iter=3000,random_state=2718).fit(Xtr,reg_tr)
    p=c.predict(Xhe); a=(p==reg_he).mean()
    print(f"{tag}: train_top1={ (c.predict(Xtr)==reg_tr).mean():.4f} held_top1={a:.4f}")
    return c
c1=fit(cen_tr,cen_he,'centroid-only')
c2=fit(mar_tr,mar_he,'margins-only')
c3=fit(np.c_[cen_tr,mar_tr],np.c_[cen_he,mar_he],'both')
print('coef both\n', c3.coef_.round(3))
