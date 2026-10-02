import sys, json
sys.path.insert(0, ".")
from experiments.c1b_adjudicate import clopper_pearson, wilson
from scipy.stats import beta
for (k, n) in [(38,40),(34,40),(27,40),(40,40),(0,40),(20,40),(35,40),(30,40)]:
    got = clopper_pearson(k, n)
    # scipy exact Clopper-Pearson
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(0.975, k+1, n-k)
    print(f"k={k} n={n}  file=({got[0]:.4f},{got[1]:.4f})  scipy=({lo:.4f},{hi:.4f})  dL={got[0]-lo:+.4f} dU={got[1]-hi:+.4f}")
