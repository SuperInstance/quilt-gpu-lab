# LFM2.5-230M — first contact (2026-10-02 ~22:45 AKDT)

**Model**: hf.co/LiquidAI/LFM2.5-230M-GGUF:Q8_0 (246MB) → ollama `lfm2.5:230m` (cp'd from hf.co pull — no native ollama tag exists; library `lfm2.5` only ships 8B-A1B).

**Question**: can the 230M nano hold the cascade's dial-quantization contract (the job qwen2.5:3b does in the playground /api/measure)?

**Result: concept-competent, contract-incompetent.**
- Integer-JSON contract: **0/6 valid**. Raw output shows it picks the RIGHT SEMANTIC POLES but emits words not numbers ("mood":"joyful"), then repeat-loops mid-object (known nano failure mode).
- Label-JSON contract (coarser): **0/6 valid**. Same loop-and-degrade.
- Verdict: 230M cannot be a cascade quantizer cell under ANY JSON contract tried. If it ever serves, it needs a format-first gate + constrained decode (grammar) — consistent with the CM1 format-gate doctrine: generators break format, gates catch what generators can't hold.

**Fleet-hash work (same night, Round 20 "yes")**:
- quilt-cloudflare `5baf034` — ocean.test.js café pin made TRUE: fnv1a64('café Δ 日本語')=77ff2029b867f2b5 asserted, UTF-8 divergent 24a555471370b18d asserted-NOT (all vectors node-verified before pinning; test suite fail 0).
- quilt-loom `de4247e` — witness_fnv now governs what it claims: spec UTF-16-unit scoped, genInput alphabet extended (éΔ本語), café falsifier probe added; oracle+probe verified 77ff2029b867f2b5 live. A UTF-8 implementation now FAILS the witness.
- Origin truth: quilt-cloudflare/src/ocean.ts fnv1a64 iterates charCodeAt = UTF-16 code units. Every seal downstream inherits this. UTF-8 hashes DO NOT verify against ocean receipts. (Migration to UTF-8 would break chains — NOT done; needs Casey's explicit call.)
