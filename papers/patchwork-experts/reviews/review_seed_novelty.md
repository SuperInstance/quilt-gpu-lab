# Review — seed_novelty (ByteDance/Seed-2.0-mini)

latency: 63.0s

Would a first-time reader follow it? No. The paper buries critical experimental disclosures, uses jargon without upfront definition, mixes reporting protocols without clarification, and delays core findings until late in the manuscript, making it difficult for a first-time reader to trust or follow the analysis.

One-sentence contribution: Using the fully enumerated, exact-labeled set of 3x3 tic-tac-toe game states as a falsifiable microcosm, this paper demonstrates that composed shallow-specialist patchwork systems require explicit veto primitives to avoid catastrophic defensive failure, perform no better on static rosters than the best single shallow tree, show that LLM-as-judge distillation targets often lack meaningful structural signal due to near-constant judge labeling, and find that the empirical routing surface of cell success predicts composition performance far better than hand-authored threat taxonomies.

Flagged issues:
- Buries the lede: The paper’s core methodological finding about empirical routing surfaces outperforming hand-authored taxonomies is presented in §7 (near the end) rather than highlighted in the introduction or abstract.
- Loses the thread: The paper references pre-registered experiments PX0-PX5 without explicitly mapping each experiment to the abstract’s three core findings, making it hard for first-time readers to connect individual tests to the overarching argument.
- Uses jargon before defining: Terms like "top1-in-optimal," "pinch cell," "format gate," and "immune layer" are used before being formally defined, and mutual information is referenced before its definition in §7.
- Buries critical disclosures: Pre-registration deviations (PX1b’s post-hoc commit, blind gardener budget violation) are hidden in parentheticals at the end of sections rather than flagged upfront.

Novelty rating: 8/10. This work introduces a novel, fully falsifiable microcosm for studying composed patchwork systems, identifies a previously understudied defensive failure mode of additive voting, and provides a measurable empirical routing surface metric that avoids the limitations of hand-authored taxonomies, while building on existing mixture-of-experts and LLM-as-judge research.

VERDICT: major revision

TOP CRITIQUES:
1. **Section 2 (Related Work):** Over 10 key citations are marked [CITE-MISSING] with no verified or placeholder bibliographic data, and the paper fails to clearly distinguish between jointly trained mixture-of-experts routers and its own post-hoc empirical routing analysis, leaving first-time readers unable to situate this work within existing machine learning literature.
2. **Section 4 (Collapse of Additive Voters):** The critical disclosure that PX1b’s pre-registration was committed post-hoc alongside results is buried in a parenthetical at the end of the section, rather than flagged at the start where PX1b’s results are first presented, undermining trust in the experimental integrity of this core finding.
3. **Section 5 (Patchwork Composition):** The comparison between static patchwork performance (0.7437, single deterministic score) and the depth-6 tree (0.7481, 3-seed mean) uses the same test split but different reporting protocols, with no explicit justification for this cross-protocol comparison, leading to a misleading presentation of the patchwork’s parity with the best single shallow tree.
4. **Section 6 (LLM-as-Judge):** The paper claims the near-constant judge labeling failure is a generalizable check but only tests it on two 96-cell synthetic fields, with no demonstration of the issue on real-world evaluation benchmarks, leaving first-time readers unsure if this problem applies beyond the narrow microcosm tested.
5. **Section 7 (Signature Map):** The paper labels PX5 as an exploratory analysis but does not clearly separate exploratory findings from confirmatory results, and fails to provide a held-out test split for the routing surface orthogonality claim, meaning the key finding that empirical cell signatures outperform hand-authored taxonomies is not independently validated.

CONSISTENCY:
1. The paper mixes single deterministic performance scores (static patchwork, 0.7437) with 3-seed mean scores (depth-6 tree, 0.7481) when comparing results, with no explicit labeling to distinguish the two reporting protocols, creating a factual inconsistency in how model performance is quantified across experiments.
2. Critical pre-registration deviations (PX1b’s post-hoc commit, blind gardener budget violation) are disclosed only in buried parentheticals, rather than upfront, creating an inconsistency between the paper’s stated commit-first experimental discipline and its actual execution that is not clearly communicated to first-time readers.
3. The paper references a "final adjudication" for the pending GLM-5.3 gardener in both §5 and the Artifact Map, but no such adjudication exists at the time of writing, creating a factual inconsistency in the paper’s stated provenance for live experimental results.
4. The abstract refers to the oracle router score of 0.8698 as "headroom" without clarifying it is a measured upper bound, while §7 explicitly labels it as such, creating a minor but unnecessary inconsistency in terminology across the paper.
5. The paper states in §3 that all headline comparisons are model-vs-model on the same split, but the static patchwork vs depth-6 tree comparison violates this rule without explicit justification.

ONE CHANGE: The single most impactful change is to add a prominent upfront disclosure of all pre-registration deviations (PX1b’s post-hoc commit, blind gardener budget violation) at the start of §3 (the experimental methods section), revise all performance metric tables and text to explicitly label whether each score is a single deterministic value or a multi-seed mean, and add a 1-paragraph "Reader’s Guide" at the start of the paper that maps each pre-registered experiment (PX0-PX5) to the abstract’s three core findings to help first-time readers connect individual tests to the overarching argument.
