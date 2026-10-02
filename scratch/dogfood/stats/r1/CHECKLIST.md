Bounds & Tails:
1. TEST: In lower() CP bisection, verify if (1.0 - cdf(k-1,n,mid)) > alpha/2 moves lo or hi. FAILURE: inverted direction yields wrong tail targeting.
2. TEST: In upper() CP bisection, verify if cdf(k,n,mid) > alpha/2 moves lo or hi. FAILURE: inverted direction targets wrong tail.
3. TEST: Verify lower bound early-return for k==0 returns 0.0 and upper bound for k==n returns 1.0 exactly. FAILURE: missing early return produces degenerate CI.
4. TEST: Check that cdf(x,n,p) indexing uses sum(i=0..x) and matches scipy.stats.beta.ppf reference intervals. FAILURE: off-by-one in CDF sum bounds inverts interval.
5. TEST: Verify margin logic: MARGIN_MIN <= mg <= upper_bound - lower_bound. FAILURE: margin larger than interval width collapses CI.
6. TEST: In gate_verdict, confirm monotonicity: increasing knob k1 should not flip verdict from PASS to FAIL if design is correct. FAILURE: non-monotonic verdict indicates inverted comparison.

Bisection & Search:
7. TEST: In any bisection loop, verify the update direction (lo=mid vs hi=mid) correctly narrows the interval given the condition outcome. FAILURE: wrong direction causes divergence or convergence to wrong root.
8. TEST: Verify bisection tolerance (e.g. 1e-6 or interval width < tol) is checked and loop terminates. FAILURE: missing tolerance or wrong tolerance yields non-convergent or stale results.
9. TEST: In compound bisection (comp2_corpus_gate.py), verify nm = round(((a + best)/2) if best else ((a+b)/2), 3) uses the correct best reference and rounding. FAILURE: stale best or wrong rounding stalls convergence.

Indexing & Off-by-one:
10. TEST: In guard.py sample loops, verify window boundaries (start/end indices) do not exceed array length or include negative indices. FAILURE: off-by-one reads garbage or crashes.
11. TEST: In guard.py energy integration, verify summing power samples is equivalent to integrating over dt (i.e. sum * dt_step). FAILURE: missing dt factor or wrong accumulation unit (Wh vs J).
12. TEST: In comp2_corpus_gate.py, verify a,b bounds for near_miss bisection are set to known-hard/known-easy extremes and direction (up= easier) is consistent. FAILURE: swapped bounds or inverted direction breaks monotonicity.

Degenerate Inputs:
13. TEST: In c1b_finalize.py, test k=0 and k=n cases explicitly; verify returned CI matches [0,1] or exact bounds. FAILURE: unhandled edge cases produce NaN or wrong bounds.
14. TEST: In guard.py, test sample_power and sample_full with n=0 or zero-energy inputs; verify no division by zero or inverted verdict. FAILURE: degenerate inputs crash or give wrong power.

Verdict Inversion:
15. TEST: In guard.py validate_receipt/emit_receipt, verify GREEN/FAIL labels match the actual energy/power conditions. FAILURE: inverted verdict logic masks failures.
16. TEST: In comp2_corpus_gate.py, verify gate_verdict(pb) returns PASS/FAIL consistent with pb["metrics"] thresholds. FAILURE: inverted verdict logic misclassifies configurations.
17. TEST: In c1b_adjudicate.py lower() bisection, verify the condition targets the lower tail correctly (P(X >= k) vs P(X <= k)). FAILURE: inverted tail produces wrong confidence level.
18. TEST: In c1b_adjudicate.py upper() bisection, verify the condition targets the upper tail correctly. FAILURE: inverted tail produces wrong confidence level.

Integration/Accumulation:
19. TEST: In guard.py _energy, verify energy accumulation sums power * dt and units are Wh (watt-hours), not Watts or raw samples. FAILURE: wrong unit conversion or accumulation gives incorrect energy readings.
20. TEST: In comp2_corpus_gate.py, verify mg = max(MARGIN_MIN, 5.0*pb["full_std"]) uses the correct standard deviation and multiplier. FAILURE: wrong std or multiplier sets inappropriate clearance.
