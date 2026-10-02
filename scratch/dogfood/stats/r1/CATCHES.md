(i) c1b_adjudicate.py inverted bisection:
The legacy lower() code read: `if binom_cdf(k - 1, n, mid) > alpha / 2: lo = mid; else: hi = mid`.
This is wrong because the Clopper-Pearson lower bound solves P(X >= k | n, L) = alpha/2. The condition must compare the *upper* tail probability 1 - cdf(k-1, n, mid) against alpha/2. With the inverted comparison, when the true upper tail is large (mid too small), the code executes `lo = mid`, pushing the interval upward instead of downward, walking the bisection in the wrong direction and targeting the wrong tail. For k=38, n=40, the inverted bisection returns lower ~0.9843 and upper 0.0, whereas the correct CP 95% CI is [0.8308, 0.9939].

(ii) c1b_finalize.py verification:
The file is CLEAN — verified. The clopper_pearson(k=38, n=40) returns [0.8308, 0.9939] and clopper_pearson(k=40, n=40) returns [0.9119, 1.0], matching the scipy.stats.beta.ppf reference exactly. All bisection directions, tail targets, indexing, and degenerate k==0/k==n early returns are correct.

(iii) comp2_corpus_gate.py and guard.py:
comp2_corpus_gate.py: CLEAN — the bisection on near_miss uses correct bounds a,b, the direction (up = easier) is consistent with monotonicity, and the margin mg = max(0.02, 5.0*pb["full_std"]) is correctly applied. No inverted comparisons or off-by-one indexing found.

guard.py: CLEAN — window accounting uses correct array bounds with no off-by-one errors; energy integration sums power samples multiplied by dt_step yielding Wh; validate_receipt verdict labels GREEN/FAIL match the energy/power conditions; no degenerate input crashes observed. The code is sound.
