#!/usr/bin/env python3
"""D12aa2 - direct k_eff(p=0.7) measurement by bisection.

D12aa showed the model floor is NOT linear in k (floor ~ k^2 via the
sigma->T coupling), so D12z's "implied k_eff 0.65-0.86" (ratio*k_extrap
at k_extrap=1.614) is not transferable. Measure k_eff(0.7) directly:
bisect k until the model floor best matches the SAVED D12z harness floors
(minimize sum |log ratio| over resolvable cells), then check G1 coverage.

Seed 2718. CPU-only, seconds, guard untouched.
"""
import json, math
import numpy as np

SEED=2718; N_CELLS=64; N_PAIRS=32; P=0.7
W_LIST=[4,8]; EPS_LIST=[0.0,0.05,0.1,0.2]
T_GRID=[1,2,3,4,5,6,8,10,15,20,30,50]
ALPHA=1.92; THRESH=0.5; MC=4000

def model_floor(W,eps,k,rng):
    s=P*(1-2*eps); sig=s**ALPHA if s>0 else 0.0
    for T in T_GRID:
        sigma=k/math.sqrt(W*T)
        null_max=rng.standard_normal((MC,N_CELLS-2)).max(axis=1)*sigma
        partner=rng.standard_normal(MC)*sigma+sig
        if np.mean(partner>null_max)>=THRESH: return T
    return None

def floors_for(k):
    rng=np.random.default_rng(SEED); out={}
    for W in W_LIST:
        for eps in EPS_LIST:
            out[(W,eps)]=model_floor(W,eps,k,rng)
    return out

with open("results/d12z_keff_p07_finegrid.json") as f: dz=json.load(f)
target={ (c["W"],c["eps"]):c["harness_floor"] for c in dz["cells"] }

def loss(k):
    mf=floors_for(k); tot=0.0; n=0
    for key,hf in target.items():
        if hf is None: continue
        m=mf[key]
        if m is None: tot+=2.0; n+=1; continue
        tot+=abs(math.log(hf/m)); n+=1
    return tot/n, mf

lo,hi=0.4,3.0
for _ in range(24):
    mid=(lo+hi)/2
    l,_=loss(mid)
    # k too small -> model floors too low -> ratios >1 -> loss high; loss decreases then increases; bisect on monotone branch via comparison
    if loss(lo)[0] < loss(hi)[0]:
        # can't blind-bisect a U-shape; do coarse scan instead
        break
    hi=mid
# coarse scan (robust): floor of loss over grid
ks=np.linspace(0.5,3.0,26)
vals=[(loss(k)[0],k) for k in ks]
lbest,kbest=min(vals)
# refine around kbest
for k in np.linspace(kbest-0.1,kbest+0.1,21):
    l,_=loss(k)
    if l<lbest: lbest,kbest=l,k
mf=floors_for(kbest)
rows=[]; g1=True; ratios=[]
for (W,eps),hf in target.items():
    m=mf[(W,eps)]
    r=hf/m if (hf and m) else None
    if r is not None:
        ratios.append(r); g1 = g1 and 0.5<=r<=2.0
    rows.append({"W":W,"eps":eps,"harness_floor":hf,"model_floor":m,"ratio":r})
    print(f"W={W} eps={eps}: harness={hf} model={m} ratio={r and round(r,3)}")
straddle = ratios and min(ratios)<1.0<max(ratios)
res={"seed":SEED,"p":P,"k_eff_p07":kbest,"fit_loss_logratio":lbest,
     "dz_linear_extrap":dz["k_extrap"],"cells":rows,"G1_pass":g1,
     "straddles_1":bool(straddle)}
import os; os.makedirs("results",exist_ok=True)
with open("results/d12aa2_keff_p07_bisect.json","w") as f: json.dump(res,f,indent=2)
print(f"\nk_eff(0.7) = {kbest:.3f} (linear extrapolation was {dz['k_extrap']:.3f})")
print("G1 (coverage [0.5,2.0]):","PASS" if g1 else "FAIL")
print("straddle 1.0:","YES" if straddle else "NO", f"({min(ratios):.2f}-{max(ratios):.2f})" if ratios else "")
