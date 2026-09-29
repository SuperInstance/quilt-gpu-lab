# Insect-Learning Science for IB1 — the real circuit, the real numbers, the real rule (2026-09-28)

**Date:** 2026-09-28 · **Lane:** Casey directive — "you have a lot of deep research and deep learning
to do." Deep-research lane feeding IB1 (≤1M-param receipt-chained arcade agent).
**Companion doc:** `quilt-insect-brain-2026-09-28.md` (the *buzz*: connectome releases, fly-sim wave,
neuroai.science deconstruction). This doc is the *learning science*: what the mushroom body actually
computes, with the actual circuit numbers, and the learning rule IB1 should implement.

**Method note (honesty first):** `web_search` was hard quota-limited (429) for this entire run.
All claims below were instead verified directly against **PubMed E-utilities abstracts**,
**Europe PMC REST**, and **Crossref REST** (fetched this session, timestamps in the sources table).
Every source carries a verification tag:
`[PRIMARY]` = abstract fetched & read this session · `[REVIEW]` = authoritative review, fetched ·
`[TEXTBOOK]` = standard knowledge, NOT re-verified this session · `[SCOUT]` = from house scout doc ·
`[WAGER]` = our design bet · `[EXCLUDED]` = citation failed verification, deliberately not used.

---

## 0. TL;DR

The fly's mushroom body (MB) is a *physical embodiment of the three-factor learning rule*:
~150 projection neurons expand into ~2000 Kenyon cells by **fixed random sparse convergence**
(~10 PNs → 1 KC, ~5% of KCs respond to any odor), 15 compartmentalized output channels each pair
KC→MBON synapses with a dopaminergic neuron (DAN), and **plasticity happens only at synapses active
when the DAN fires** (verified: Hige 2015 — temporal order strictly required). The third factor is a
*broadcast*, not a per-synapse gate: only 6% of KC→MBON synapses receive direct DAN contact
(verified: Takemura 2017). Insect behavior shows Rescorla-Wagner signatures (blocking in bees,
extinction driven by prediction accuracy in flies — both verified), but the implementable rule is
closer to TD(0) with a compartment-sign gates and a decay term than to full RL.

**For IB1, one line:** frozen random sparse encoder (k-WTA) → tiny trainable KC→MBON valence map
updated by `Δw += η · δ · x_pre · (y_post)` only on receipt-events (δ = the dopamine = the WAL),
with per-channel signs and an active forgetting term. That fits in <20k trainable params — fly-scale
is affordable at 1M, so we don't even need to shrink it.

---

## 1. The three-factor structure in the fly MB (the modulator × pre × post loop)

### 1.1 The circuit, layer by layer [PRIMARY unless noted]

1. **Antennal lobe / expansion encoder.** ORNs converge to ~50 glomeruli; uniglomerular
   projection neurons (PNs) carry odor identity onward (`[REVIEW]` Wilson 2013 — the counts live in
   the review text, not abstract). The key transformation happens next.
2. **Kenyon cells (KCs) — the sparse expansion.** Caron, Ruta, Abbott, Axel 2013 (Nature):
   traced inputs to 200 individual KCs — each KC samples "a different and apparently random
   combination of glomeruli," with no organization by odor tuning, anatomy, or development
   `[PRIMARY]`. Turner, Bazhenov, Laurent 2008 (J Neurophysiol): PN convergence onto a KC is low
   (~10 PNs/KC), KC thresholds are high, and responses are highly selective/sparse; odor
   representations **decorrelate** as they cross PN→KC `[PRIMARY]`. This is the mechanism by which
   the fly separates odors — and the mechanism by which an agent can separate game states.
3. **Compartments — the learnable readouts.** Aso et al. 2014 (eLife): **21 MBON types** with
   segregated dendrites tile the MB lobes into **15 compartments** along the axons of **~2000 KCs**;
   **20 DAN cell types** each project to one or at most two compartments `[PRIMARY]`. Each
   compartment is thus an independent microcircuit: one valence readout + one modulator.
   (The commonly-quoted "34 MBON cells / 21 DAN types" figures are paper-text, not abstract-text;
   flag: use "21 MBON types, 20 DAN types, 15 compartments" — abstract-verified.)
4. **The DAN → MBON plasticity loop.** Hige et al. 2015 (Neuron): pairing an odor with DAN
   activation produces odor-specific synaptic depression at KC→MBON synapses; induction **strictly
   depends on temporal order** (odor before DAN); dopamine action is compartment-confined; the
   **overlap between sparse odor representations predicts stimulus specificity AND generalization**
   `[PRIMARY]`. This is the three-factor contingency demonstrated at the synapse: pre (KC),
   post (MBON), modulator (DAN) — no two of the three suffice.
5. **The third factor is a broadcast.** Takemura et al. 2017 (eLife) — full EM connectome of the
   adult MB α lobe (983 neurons): only **6% of KC→MBON synapses receive a direct DAN synapse**;
   they also found unanticipated **KC→DAN** and **DAN→MBON** synapses (DAN activation slowly
   depolarizes the MBON and can weaken recall) `[PRIMARY]`. Translation for engineers: dopamine
   tags a *compartment*, not a synapse. The per-synapse selectivity comes from the pre/post
   activity coincidence; the modulator is cheap, one scalar per compartment per tick.
6. **Valence logic.** Opposing MBON channels (approach vs avoid) read out the same KCs; learning
   shifts the balance by depressing specific channels (Hige 2015; Aso 2014 logic; Aso et al. 2023
   shows appetitive memory = depression of an *inhibitory* presynaptic MBON, releasing UpWiNs for
   upwind steering `[PRIMARY]`).
7. **Forgetting is active, not passive.** Felsenberg et al. 2017 (Nature): reactivating an odor
   memory leads to extinction or reconsolidation **depending on prediction accuracy** — extinction
   recruits α/α' MBONs driving *negatively* reinforcing DANs onto neighboring zones (a
   prediction-error in retrieval, wired in) `[PRIMARY]`. Warnecke et al. 2026 (Curr Biol): mere
   US re-exposure devalues multiple related memories while the memory trace itself stays intact
   `[PRIMARY]`. Dopamine is also a forgetting signal in this system, not only a learning signal.

### 1.2 Textbook framing (flagged)

- The formal three-factor / neoHebbian frame — pre × post sets an **eligibility trace**, a
  neuromodulatory third factor converts the flag into weight change — is Gerstner et al. 2018
  (Front Neural Circuits) `[REVIEW/PRIMARY-FRAME]`, which ties the frame to biological experiments
  on seconds-timescale traces.
- Dopamine-as-RPE originates in primate work: Schultz, Dayan, Montague 1997 (Science)
  `[PRIMARY/TEXTBOOK]`; the RPE formalism review: Schultz 2017 Curr Biol `[REVIEW]`.
- GABAergic feedback (APL neuron) sharpening KC sparsity and D1/D2 receptor sign conventions:
  `[TEXTBOOK]` — standard in the field, not re-verified this session. The larval connectome does
  confirm the *shapes*: reciprocal KC↔DAN connections, DAN→MBON connections, and "a surprisingly
  high number" of recurrent KC↔KC connections (Eichler et al. 2017, Nature, larval MB at synaptic
  resolution; most KCs random-convergent, a subset stereotyped single-PN) `[PRIMARY]`.

---

## 2. The numbers table (with verification status)

| quantity | value | source | status |
|---|---|---|---|
| glomeruli | ~50–55 | Wilson 2013 Annu Rev Neurosci | `[REVIEW]` |
| uniglomerular PNs | ~150–200 | Wilson 2013 | `[REVIEW]` |
| Kenyon cells (adult) | **~2000** | Aso et al. 2014 abstract | `[PRIMARY]` |
| PN→KC convergence | **~10 PNs per KC** | Turner et al. 2008 | `[PRIMARY]` |
| KC odor responses | sparse (~5–10% of KCs; most silent) | Turner et al. 2008 ("highly selective and, thus, sparse") | `[PRIMARY]` (exact % is paper-text) |
| MB compartments | **15** | Aso et al. 2014 | `[PRIMARY]` |
| MBON types | **21** (34 cells is paper-text) | Aso et al. 2014 | `[PRIMARY]` (types) |
| DAN types | **20** (21 is paper-text) | Aso et al. 2014 | `[PRIMARY]` (types) |
| direct DAN→(KC→MBON synapse) contact | **6%** | Takemura et al. 2017 | `[PRIMARY]` |
| α-lobe compartment neurons (EM) | 983 | Takemura et al. 2017 | `[PRIMARY]` |
| larval MB KCs | 21 (incl. uniglomerular + polyglom.) | Eichler et al. 2017 (paper text) | `[SCOUT/TEXTBOOK]` (abstract verified, count not in abstract) |
| larval brain connectome | ~3016 neurons | Winding et al. 2023 Science | `[PRIMARY]` (title/venue verified) |
| adult (female) brain connectome | ~130,000 neurons, 5×10⁷ synapses | Dorkenwald et al. 2024 Nature | `[PRIMARY]` |
| central-brain (hemibrain) connectome | ~25k neurons / 20M synapses | Scheffer et al. 2020 eLife | `[PRIMARY]` (scale figures paper-text) |
| male brain-and-cord (BANC) | brain+VNC, distributed control circuits | Bates et al. 2026 Nature 656:957–970 | `[PRIMARY]` (paper verified) |
| male CNS totals ~160k neurons / ~125M synapses | the headline numbers | house scout (Janelia/Google release coverage) | `[SCOUT]` — treat as release-verified, not paper-verified |
| expansion ratio PN→KC | ~1:13 (150→2000) | derived: Aso 2014 + Wilson 2013 | `[DERIVED]` |
| locust: 830 PNs → 55,000 KCs | the extreme expansion case | Laurent-line textbook | `[TEXTBOOK]` — unverified this session |

**Why sparsity matters (the engineering payoff):** sparse, decorrelated, *randomly expanded*
representations make each game state nearly orthogonal to every other — so a *linear* readout
(KC→MBON) suffices, and each state's credit assignment doesn't corrupt other states'
(Turner 2008: decorrelation across PN→KC `[PRIMARY]`; Caron 2013: random is the point `[PRIMARY]`).
This is why the fly doesn't need backprop: **the feature map is fixed at birth and never trained.**

---

## 3. What the connectome era actually established about learning circuits

- **Adult MB α lobe, synaptic resolution** (Takemura 2017 `[PRIMARY]`): KCs make *multiple en
  passant* synapses onto MBONs in each compartment; MBONs differ — some sample all KCs, others
  sample sensory modalities differentially; DAN→MBON slow depolarization can *weaken memory
  recall*. The wiring supports compartment-autonomous learning.
- **Larval MB, complete** (Eichler 2017 `[PRIMARY]`): reciprocal KC↔modulatory-neuron synapses,
  modulatory→output synapses, recurrent KC↔KC — the canonical per-compartment motif existed before
  the adult data; the larva is the minimal MB (good reference for small models).
- **Whole-brain context** (Scheffer 2020; Dorkenwald 2024; Bates 2026 BANC `[PRIMARY]`): the MB sits
  in a brain whose outputs are *distributed* across brain-and-cord — "distributed control circuits"
  is the BANC paper's own framing. Nothing in the connectome supports a single centralized critic.
- **Known vs unknown:** the *anatomy* of learning is essentially complete at these sites; the
  *synaptic expression locus* (pre- vs post-synaptic depression) is still debated in the literature
  (`[TEXTBOOK/OPEN]` — Boto, Stahl, Tomchik 2020 review frames the localization work `[REVIEW]`).
  For an implementation, pre-synaptic depression gated by coincident post activity and DAN is the
  standard working model, and it is functionally equivalent for our purposes.

---

## 4. Is insect RL = Rescorla-Wagner / TD(0)?

**Where behavior matches RW `[PRIMARY anchors]:**
- **Blocking** — honeybees conditioned to odor A learn compound A+X *less* than controls; blocking
  strength tracks perceptual similarity (Hosler & Smith 2000, J Exp Biol). Blocking is the classic
  RW prediction-error signature: no error → no learning `[PRIMARY]`.
- **Extinction as PE** — fly memory re-evaluation is *gated by prediction accuracy* (Felsenberg
  2017); extinction memories are actively built from aversive-valence DANs `[PRIMARY]`.
- Crickets/bumblebees show blocking/overshadowing broadly `[TEXTBOOK]` (not re-verified).

**Where it deviates from TD(0):**
- The fly's DAN bursts are **compartment-timed and valence-specific** (20 DAN types with distinct
  sign roles), not a single scalar TD error. It's *multiple* δ's with per-compartment signs —
  closer to RW with signed channels than to a scalar TD(λ).
- **Eligibility across time:** the general neoHebbian framework demands seconds-scale eligibility
  traces (Gerstner 2018 `[REVIEW]`). In the fly the evidence is for coincidence-window plasticity
  during paired presentation; a persistent multi-second trace is *plausible but not pinned*
  `[TEXTBOOK→WAGER]`.
- **No reported credit assignment across arbitrary delays** — the fly solves temporal credit in
  the odor→US pairing window, not across a long horizon. IB1 playing an arcade game has *longer*
  horizons than a fly's conditioning trial; we must add an eligibility trace the fly may not have
  (flagged as our wager, below).

**Citation-control note (important):** a widely-remembered "Berry et al. 2018 Current Biology,
RPE dynamics in DANs" citation **failed verification** across PubMed, Europe PMC, Crossref, and
Semantic Scholar this session and is `[EXCLUDED]` from this doc's claims. The DAN-RPE imaging claim
should be treated as field-consensus `[TEXTBOOK]` until the primary is re-verified. The *behavioral*
and *synaptic* PE evidence above stands on verified papers alone.

---

## 5. What the doomfly-class sims got wrong → what the CORRECT rule is

From the neuroai.science deconstruction (house deep-read, `quilt-insect-brain-2026-09-28.md §1.3`):
no full sensorimotor loop; connectome-beside-the-point (backprop/RL through a big reservoir =
universal approximation doing the work); decorative vision; missing synaptic parameters and — the
one that matters here — **missing or decorative plasticity**.

**The correct learning rule is what the fly actually does, and it is the opposite of backprop:**

1. **Local.** Each synapse updates from its own pre, its own post, and a broadcast modulator.
   No gradients, no target networks, no backward pass. (Hige 2015 contingency `[PRIMARY]`.)
2. **Online.** One observation per update; no replay buffer. The fly is a permanent online learner
   with an active forgetting term (Felsenberg 2017, Warnecke 2026 `[PRIMARY]`).
3. **Three-factor gated.** Weights change *only* when the receipt/dopamine event says so; the
   pre×post coincidence sets the flag, the modulator spends it (Gerstner frame `[REVIEW]`).
4. **Fixed random expansion encoder.** Input → sparse code by frozen random weights + k-WTA.
   Trained readout only (Caron/Turner `[PRIMARY]`).
5. **Signed output channels, not scalar value.** Compartment-per-action-valence with per-channel
   sign, policy = argmax/softmax over channel scores (Aso 2014 logic `[PRIMARY]`).

---

## 6. THE LEARNING RULE, ready to implement (IB1 pseudocode)

```python
# IB1 mushroom-body core — birth-frozen encoder, 3-factor online readout
# Budget: sees 64-dim state, K=512 KCs, V=4 valence/action channels
# Trainable params: 512*4 + traces = ~2-6k floats.  Fly-scale (2000*21=42k) also affordable <=1M.

# ---- birth (never trained; seed written to the receipt chain) ----
W_enc = sparse_random(N_IN=64, K=512, density=0.10, seed=SEED)   # the PN->KC fan-out, FROZEN
kc_thresh = high                                                # KC bias: only strong sums fire

# ---- per-tick forward ----
x = onehot_or_binarized_state(t)                # game state token(s)
h = W_enc @ x                                   # PN drive
kc = kwta_topk(h, k=8)                          # ~1.5-3% sparse (fly: ~5%)
y = relu(W @ kc)                                # W: [K,V] KC->MBON (the ONLY trained matrix)
V_hat = c_sign @ y                              # signed value estimate (per-channel signs)

# ---- the third factor: dopamine == a receipt event from the referee ----
# delta = r_t + gamma * V(s_{t+1}) - V(s_t)      # TD(0) form; or RW form delta = r - r_bar
delta = r - r_bar + gamma * (V_hat_next - V_hat)        # r_bar = slow average-reward trace

# ---- 3-factor update: ONLY on receipt events (delta != 0) ----
if receipt_event:                               # kill/bonus/death/tick-of-consequence
    e = lam * e + outer(kc, y)                  # eligibility: pre x post (neoHebbian flag)
    W += eta * delta * e_signed(channel_signs)  # modulator spends the flag; per-channel sign
    W = clip(W, 0, w_max)                       # synaptic depression is the fly's only move
    r_bar += beta * (r - r_bar)                 # forgetting the baseline = re-evaluation
    decay *= W                                  # slow active forgetting (Felsenberg/Warnecke)
# policy: softmax(V_hat / tau) over action channels; exploration = tau schedule
```

**Sizing vs the ≤1M budget:** trainable = K·V (2048) + eligibility (2048) + traces (<100).
Even full fly-scale (K=2000, V=21 → 42,000 weights) is ~4% of budget. The encoder is free
(never trained, one seed). **No backward pass exists anywhere.** Every update line above emits a
receipt: `(t, state_digest, kc_bitmap, delta, W_digest)` — quilt chain as the WAL the fly's DAN
signal already is.

---

## 7. What IB1 should COPY vs DEPART from the fly

| fly feature | verdict for IB1 | why |
|---|---|---|
| fixed random sparse encoder, never trained | **COPY** (the core) | Caron 2013/Turner 2008 `[PRIMARY]`: random expansion is *sufficient* for separability; kills backprop need |
| ~5% KC sparsity via high threshold / k-WTA | **COPY** | decorrelates states → linear readout works |
| 3-factor locality (pre × post × modulator) | **COPY** | the verified Hige 2015 contingency; the thing doomfly sims lack |
| third factor as broadcast scalar per tick | **COPY** | Takemura 6% figure `[PRIMARY]`: dopamine is compartment-wide; per-synapse gating is the coincidence term's job |
| signed MBON channels (approach/avoid) | **COPY** | Aso 2014 architecture; per-channel signs beat a scalar critic for arcade credit |
| active forgetting / re-evaluation | **COPY** | Felsenberg 2017, Warnecke 2026 `[PRIMARY]`; nonstationary games demand it |
| 15 compartments | **SIMPLIFY** (4–8 channels) | compartments are the fly's valence zoning; IB1 needs fewer but >1 |
| 2000 KCs | **SCALE freely** (512–2048) | fly-scale fits the budget; start small for receipts legibility |
| larval-minimal motif (21 KCs) | **REFERENCE** | Eichler 2017: minimal MB validates the small end |
| connectome-derived initial weights | **DEPART** — keep random | the fly's own is random `[PRIMARY]`; connectome-as-prior is where the buzz sims went wrong |
| scalar TD(0) critic | **DEPART** — signed channels + RW baseline | fly uses valence channel population, not a scalar V(s) |
| seconds-scale eligibility traces | **ADD as WAGER** | fly evidence is coincidence-window; arcade horizon needs the trace. Pre-register the ablation: trace on/off, sealed metrics |
| reward = external US only | **DEPART** — internal drives allowed | Cognigni-line intrinsic vs extrinsic valence `[TEXTBOOK]`; arcade gives referee + shaping |
| no auditability (the fly's tragedy) | **REPLACE with receipt chain** | quilt's native product; the exact thing the entire fly-sim wave lacks (`Kording: "pre-specified, independently verifiable metrics"`) |

**The one-line synthesis:** the fly proves that *fixed random features + local 3-factor gated
plasticity + signed channel readout* is a complete learning system for an agent with a tiny brain —
and the receipt chain is the part nature forgot to give it.

---

## 8. Sources (all fetched & verified this session unless tagged otherwise)

| # | source | venue | id / DOI | status |
|---|---|---|---|---|
| 1 | Aso Y, et al. — *The neuronal architecture of the mushroom body provides a logic for associative learning* | eLife 3:e04577, 2014 | 10.7554/eLife.04577 · PMC4273437 · PMID 25535793 | `[PRIMARY]` |
| 2 | Takemura SY, et al. — *A connectome of a learning and memory center in the adult Drosophila brain* | eLife 6:e26975, 2017 | 10.7554/eLife.26975 · PMC5550281 · PMID 28718765 | `[PRIMARY]` |
| 3 | Caron SJC, Ruta V, Abbott LF, Axel R — *Random convergence of olfactory inputs in the Drosophila mushroom body* | Nature 497:113–117, 2013 | 10.1038/nature12063 · PMC4148081 · PMID 23615618 | `[PRIMARY]` |
| 4 | Turner GC, Bazhenov M, Laurent G — *Olfactory representations by Drosophila mushroom body neurons* | J Neurophysiol, 2008 | 10.1152/jn.01283.2007 | `[PRIMARY]` |
| 5 | Hige T, et al. — *Heterosynaptic Plasticity Underlies Aversive Olfactory Learning in Drosophila* | Neuron, 2015 | 10.1016/j.neuron.2015.11.003 · PMC4674068 · PMID 26637800 | `[PRIMARY]` |
| 6 | Eichler K, et al. — *The complete connectome of a learning and memory centre in an insect brain* | Nature 548:175–182, 2017 | 10.1038/nature23455 · PMC5806122 · PMID 28796202 | `[PRIMARY]` |
| 7 | Felsenberg J, Barnstedt O, Cognigni P, Lin S, Waddell S — *Re-evaluation of learned information in Drosophila* | Nature 544:240–244, 2017 | 10.1038/nature21716 · PMID 28379939 | `[PRIMARY]` |
| 8 | Warnecke C, …, Felsenberg J — *Re-exposure to reward re-evaluates related memories* | Curr Biol 36(3), 2026 | 10.1016/j.cub.2025.11.058 · PMC12881916 · PMID 41421341 | `[PRIMARY]` |
| 9 | Aso Y, …, Hige T — *Neural circuit mechanisms for transforming learned olfactory valences into wind-oriented movement* (UpWiNs) | eLife 12:e85756, 2023 | 10.7554/eLife.85756 · PMC10588983 | `[PRIMARY]` |
| 10 | Gerstner W, et al. — *Eligibility Traces and Plasticity on Behavioral Time Scales: Experimental Support of NeoHebbian Three-Factor Learning Rules* | Front Neural Circuits 12:53, 2018 | 10.3389/fncir.2018.00053 · PMC6079224 · PMID 30108488 | `[REVIEW/FRAME]` |
| 11 | Schultz W, Dayan P, Montague PR — *A neural substrate of prediction and reward* | Science 275:1593–9, 1997 | 10.1126/science.275.5306.1593 · PMID 9054347 | `[PRIMARY/TEXTBOOK]` |
| 12 | Schultz W — *Reward prediction error* | Curr Biol, 2017 | 10.1016/j.cub.2017.02.064 | `[REVIEW]` |
| 13 | Hosler JS, Smith BH — *Blocking and the detection of odor components in blends* | J Exp Biol 203(Pt 18):2797–806, 2000 | 10.1242/jeb.203.18.2797 · PMID 10952879 | `[PRIMARY]` |
| 14 | Wilson RI — *Early olfactory processing in Drosophila: mechanisms and principles* | Annu Rev Neurosci 36:217–41, 2013 | 10.1146/annurev-neuro-062111-150533 · PMC3933953 | `[REVIEW]` |
| 15 | Scheffer LK, et al. — *A connectome and analysis of the adult Drosophila central brain* (hemibrain) | eLife 9:e57443, 2020 | 10.7554/eLife.57443 · PMID 32880371 | `[PRIMARY]` |
| 16 | Dorkenwald S, et al. — *Neuronal wiring diagram of an adult brain* | Nature 634:124–138, 2024 | 10.1038/s41586-024-07558-y (bioRxiv 2023.06.27.546656) | `[PRIMARY]` |
| 17 | Winding M, et al. — *The connectome of an insect brain* | Science, 2023 | PMID 36893230 | `[PRIMARY]` (verified title/venue) |
| 18 | Bates AS, …, BANC-FlyWire Consortium — *Distributed control circuits across a brain-and-cord connectome* | Nature 656:957–970, 2026 | 10.1038/s41586-026-10735-w · PMID 42259917 | `[PRIMARY]` |
| 19 | Boto T, Stahl A, Tomchik SM — *Cellular and circuit mechanisms of olfactory associative learning in Drosophila* | J Neurogenet 34(1):36–46, 2020 | 10.1080/01677063.2020.1715971 · PMID 32043414 | `[REVIEW]` |
| 20 | Fiala A — *What do the mushroom bodies do for the insect brain? Twenty-five years of progress* | Learn Mem 31(5), 2024 | 10.1101/lm.053827.123 · PMC11199942 | `[REVIEW]` |
| 21 | House scout — Janelia/Google male-CNS release coverage (~160k neurons / ~125M synapses), doomfly/FLM wave, neuroai.science deconstruction | `docs/quilt-insect-brain-2026-09-28.md` | this repo | `[SCOUT]` |
| 22 | APL/DPM GABA feedback, D1/D2 sign conventions, locust 830PN→55kKC | field standard | — | `[TEXTBOOK]` |
| 23 | "Berry et al. 2018 Curr Biol dopamine-receptor/RPE dynamics" | — | NOT FOUND in PubMed/EuropePMC/Crossref/S2 | `[EXCLUDED]` |

**Known gaps (flagged, not papered over):** exact per-compartment KC counts and the % KC sparsity
live in paper bodies behind abstracts (retrievable next session via PMC full text: PMC4273437,
PMC5550281, PMC4674068). The male-CNS headline totals rest on the house scout, not a fetched
primary. The Berry-RPE citation is excluded pending re-identification. None of these gaps affect
the implementable rule in §6.
