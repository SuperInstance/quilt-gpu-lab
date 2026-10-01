# Review — hermes_adversarial (NousResearch/Hermes-3-Llama-3.1-405B)

latency: 16.2s

VERDICT: major revision

TOP CRITIQUES:
1. The static composition result (0.7437) being slightly below the best single shallow tree (0.7481) undermines the central claim that composition beats individual components. This negative result needs to be addressed more directly. (§5)
2. The live GLM-5.3 gardener result being pending leaves a key part of the story incomplete. The final adjudication needs to be included for the composition story to be fully evaluated. (§5)
3. The orthogonality claim between the signature map and authored taxonomy is intriguing but lacks a held-out confirmatory test. This limits the strength of the routing surface claims. (§7) 
4. The exact enumeration luxury of the microcosm limits generalizability to domains without such ground truth. Proxies for scaling this discipline need further development. (§9)
5. The judge constancy result is compelling but narrow, being based on only two synthetic 96-cell fields. Broader testing of judge degeneracy is needed. (§6)

CONSISTENCY:
- The pre-registration of PX1b being committed post-hoc (though frozen in docstring) is a notable deviation from the commit-first protocol. While disclosed, it introduces some doubt. (§4)
- The comparison between the static composition (single deterministic value) and depth-6 tree (3-seed mean) is a minor protocol inconsistency, though on the same split. (§5)

ONE CHANGE:
Include the final adjudication of the live GLM-5.3 gardener arm. This is the single most important addition to solidify the composition story. The current "pending" status is a major gap.
