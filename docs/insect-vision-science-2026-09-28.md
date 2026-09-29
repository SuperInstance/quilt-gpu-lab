# Insect-Vision Science for ie1 — the real correlator, the real numbers (2026-09-28)

**Lane:** Casey directive — deep research for **ie1 (temporal fam codes / the LP build)**:
Reichardt correlators over the glyph lattice → 4 motion-direction codes; text-only reader
recovers drift direction from the motion-code stream alone (gate: direction R² ≥ 0.5 at ≥2
densities, c1 house gate).

**Discipline:** every claim is tagged **[PRIMARY]** (source fetched and verified today,
2026-09-28) or **[TEXTBOOK]** (standard literature; cited but not independently re-verified —
canon, not receipt). We are building, not canonizing.

---

## 1. The Reichardt correlator (Hassenstein–Reichardt correlator, HRC)

### 1.1 Provenance

- **Hassenstein & Reichardt 1956** (Z. Naturforsch. 11b: 513–524): inferred from the turning
  responses of the weevil *Chlorophanus* to two-point apparent motion ("phi" stimuli). Four
  signed contrast combinations; two turn with the sequence (phi), two turn *against* it
  (reverse phi). **[PRIMARY — described in Clark et al. 2011, fetched today]**
- **Reichardt 1961** ("Autocorrelation, a principle for the evaluation of sensory information
  by the central nervous system," in *Sensory Communication*, MIT Press): the delay-and-multiply
  elementary motion detector (EMD) formalized. **[TEXTBOOK]**
- **Reichardt & Poggio 1976** (Q. Rev. Biophys. 9: 311–75 and 377–438): full quantitative theory
  of the fly's optomotor orientation behavior, including the closed-loop equations.
  **[PRIMARY — PubMed abstracts verified]**
- **Borst & Egelhaaf 1989** (Trends Neurosci. 12: 297–306): the "few equivalent computational
  principles across the animal kingdom" review — the canonical modern statement of the HRC.
  **[PRIMARY — abstract verified]**

### 1.2 The exact math

One **elementary motion detector** = two mirror-symmetrical half-detectors:

```
Input L(t) = I(x, t)          ← left receptor
Input R(t) = I(x+Δφ, t)       ← right receptor (Δφ = angular pitch between them)

Arm A (prefers rightward):  L_filtered(t) = (h ∗ L)(t)      multiply by  R(t)
Arm B (prefers leftward):   R_filtered(t) = (h ∗ R)(t)      multiply by  L(t)

D(t) = [L_f · R] − [R_f · L]        ← SUBTRACTION = direction selectivity
```

where the delay filter `h` is (modern form) a **first-order low-pass** with time constant τ:

```
H(ω) = 1 / (1 + iωτ),   |H| = 1/√(1+ω²τ²),   phase lag φ_h = arctan(ωτ)
```

(Reichardt's original used a pure delay ε → temporal tuning sin(ωε); the low-pass form is what
modern work fits and what you should implement.)

**Analytic response** to a drifting sinusoid `I = I₀ + c·sin(2π(x/λ − f·t))`, with spatial
phase shift ψ = 2πΔφ/λ and angular temporal frequency ω = 2πv/λ (v = angular velocity):

```
R = c² · sin(ψ) · ωτ / (1 + (ωτ)²)
```

Derivation sketch (do this once so you trust it): arm A = ⟨LP[L]·R⟩ = (c²/2)|H|·cos(φ_h−ψ);
arm B = ⟨L·LP[R]⟩ = (c²/2)|H|·cos(φ_h+ψ); difference = (c²/2)|H|·2·sin(φ_h)·sin(ψ) → the form
above. The non-directional sum of arms carries the position/DC term (cos terms) — pooling
cancels it; if you want figure/ground discrimination later, keep it around.

**The four signature properties** (these are what behavioral experiments actually measured):

1. **Quadratic in contrast:** R ∝ c². This is *the* fingerprint of a multiplicative step.
   Verified behaviorally in Drosophila: the turning response is a *linear* function of the
   HRC-kernel prediction (product of bar contrasts). **[PRIMARY — Clark et al. 2011]**
2. **Band-pass temporal tuning, peak at ωτ = 1.** The detector is matched to a "best
   velocity" v* = λ/(2πτ): bigger features → faster best speed. **[TEXTBOOK + implied by
   Clark's measured delay filter, below]**
3. **Spatial tuning sin(2πΔφ/λ): zero at λ = Δφ, sign flip (aliasing!) at λ = 2Δφ.**
   A grating with period twice the lattice pitch makes the detector signal motion in the
   *wrong direction*. Your density sweeps must avoid landing exactly on the alias.
   **[TEXTBOOK — standard HRC result]**
4. **Reverse-phi:** flipping the contrast polarity of one input flips the sign of R.
   Flies turn *opposite* to the spatial sequence for opposite-sign pulse pairs — verified
   behaviorally, and the delay arm carries contrast for **at least 1 s**. **[PRIMARY —
   Clark et al. 2011]**

### 1.3 Measured filter values (Drosophila, bright light, walking flies)

| quantity | value | source |
|---|---|---|
| delay-filter peak | **~25 ms** (kernel peaks 20–30 ms) | **[PRIMARY] Clark et al. 2011** (behavioral two-bar white-noise kernel; consistent w/ Harris, O'Carroll & Laughlin 1999 electrophysiology in larger flies) |
| delay filter adaptation | τ shifts with light level/adaptation (shorter in bright) | **[PRIMARY — abstract-level] Harris et al. 1999, Vision Res 39:2603** ("Adaptation and the temporal delay filter of fly motion detectors") |
| LMC/high-pass arm timescale | 50–100 ms (contrast high-pass in bright light) | **[PRIMARY — quoted in Clark 2011 from Juusola et al. 1995; Laughlin et al. 1987]** |
| behavioral delay arm memory | carries contrast ≥ 1 s | **[PRIMARY] Clark et al. 2011** (reverse-phi pairs with 1 s ISI still work) |
| optomotor temporal optimum (walk) | ~1–2 Hz grating drift | **[TEXTBOOK — Tammero et al. 2004 cited by Clark; consistent with ωτ=1, τ≈25–80 ms]** |

⚠️ Note: τ is *not* universal. 25 ms is the bright-light walking-fly behavioral estimate.
Blowfly electrophysiology at various light levels spans tens to ~100+ ms. **Set τ as an
explicit dial in ie1 and sweep it** — that is more faithful to the biology than picking one
number.

### 1.4 ON/OFF structure (what modern fly vision proved about the multiplier)

This is the part most toy implementations get wrong, and it matters for glyph coding:

- Photoreceptor signals split in the lamina into **L1 = ON (brightness increments)** and
  **L2 = OFF (brightness decrements)** pathways. Blocking L1 kills responses to moving *light*
  edges; blocking L2 kills responses to moving *dark* edges. **[PRIMARY — Joesch et al. 2010,
  Nature 468:300]**
- **Only same-sign detectors exist: ON-ON and OFF-OFF.** Direction-selective responses to
  same-sign pulse sequences (ON-ON, OFF-OFF); *no* dedicated detectors for ON-OFF sequences.
  Two detectors, not four. **[PRIMARY — Eichner et al. 2011, Neuron 70:1155]**
- But L1/L2 pathways are **not** pure half-wave rectifiers (their calcium signals are
  approximately linear in contrast); edge polarity selectivity emerges from **differential
  weighting of the four signed unit multiplications** (phi + reverse-phi quadrants) across the
  two pathways — the "weighted quadrant" model. Reverse-phi is not an illusion; it's how the
  circuit becomes *edge-polarity selective*. **[PRIMARY — Clark et al. 2011]**
- L1 and L2 are electrically coupled (which is why single-pathway silencing experiments
  confused the field). **[PRIMARY — Joesch et al. 2010]**
- **The plain HRC underestimates the direction selectivity of the real T4/T5 neurons.** The
  better fit adds preferred-direction enhancement + null-direction suppression in one stage
  (divisive/interactive form). **[PRIMARY — Borst lab modeling page, fetched today; Arenz et
  al. 2017 Curr Biol 27:929; also Gruntman, Tomani & Reiser 2018 Nat Neurosci 21:250 — fast
  excitation + offset, delayed inhibition]**

**Implementation takeaway for ie1:** plain HRC arithmetic (LP + multiply + subtract, signed
inputs) is *sufficient* for a direction-code reader, and it is what the behavioral gate
measures. The ON/OFF + P-D-suppression refinements are upgrades if the R² gate misses, not
day-one requirements.

### 1.5 Port-ready pseudocode (glyph-lattice form)

```python
# ---- one correlator, cells at lattice positions x and x+Δ, direction RIGHT ----
# signed contrast: c[i] = (glyph luminance deviation from local mean) / mean
# keep the SIGN — phi/reverse-phi arithmetic and the c² fingerprint both need it

# delay arm: exact first-order low-pass (zero-order-hold discrete)
#   alpha = 1 - exp(-dt/tau);   stable for any dt; dt << tau makes alpha ≈ dt/tau
lp[x] += alpha * (c[x] - lp[x])

# optional high-pass arm on the un-delayed input (biology: LMC transient, 50-100 ms):
#   hp[x] = c[x] - lp[x]      (or its own faster LP minus c)

D_right = lp[x]    * c[x+d]
D_left  = c[x]     * lp[x+d]
D       = D_right - D_left          # signed direction signal, E ~ c² near optimum

# ---- ON/OFF two-detector form (Eichner 2011: ON-ON and OFF-OFF only) ----
on  = max( lp[x], 0); off = max(-lp[x], 0)
D_on   = on[x]*on[x+d]  - on[x+d]*on[x]        # note: same sign convention
D_off  = off[x]*off[x+d] - off[x+d]*off[x]
D      = w_on*D_on + w_off*D_off               # Clark 2011 weighted quadrants;

# ---- LP-style wide-field pooling (see §2) ----
code[dir] = Σ_cells D / N_active               # 4 codes = 4 cardinal directions
```

Tuning table (so you don't have to re-derive): with τ = 25 ms → best temporal frequency
f* = 1/(2πτ) ≈ 6.4 Hz; feature of angular period λ* moving at v* has v* = λ*/(2πτ)
(e.g. λ* = 30° → v* ≈ 190°/s). At glyph-frame rate dt = 10 ms (100 fps): α = 1 − e^(−0.4) ≈ 0.33.
If your effective glyph-frame rate is slower, either raise τ or the correlator starves —
this interacts directly with the CFF budget of §3.

---

## 2. The lobula plate: thousands of correlators → ~60 wide-field neurons

### 2.1 The real counts

- **58 lobula-plate tangential (LPT) neurons per hemisphere** in the Janelia whole-brain EM
  volume — a comprehensive catalog including types never before described.
  **[PRIMARY — Zhao, Nern, Koskela, ... Chiappe, Reiser 2023 bioRxiv 2023.10.16.562634]**
- The classic "about 60 LPTCs" figure per optic lobe is confirmed at 58 by the EM survey; the
  older blowfly literature (Hausen 1982/1984) established the HS/VS taxonomy in Calliphora.
  **[TEXTBOOK — Hausen; flagged]**
- **Horizontal system in Drosophila = 3 cells (HSN, HSE, HSS)**, all excited by front-to-back
  motion in the ipsilateral field, inhibited by back-to-front; receptive fields cover both
  hemispheres via coupling; contrast/velocity tuning consistent with the correlation model.
  **[PRIMARY — Schnell et al. 2010, J Neurophysiol 103:1646 — first whole-cell recordings of
  Drosophila HS cells]**
- **Vertical system (VS cells)** + FD (figure detection) + CH (chiasm) + H1/H2 and other
  output neurons make up the rest of the 58. **[PRIMARY — Zhao 2023 for the catalog;
  TEXTBOOK for the classic taxonomy]**
- The optic lobe per hemisphere: **~700–900 ommatidia/columns** (Lappalainen's connectome
  model tiles **721 columns** for the central visual field). **[PRIMARY — Lappalainen et al.
  2024, Nature 634:1132; Fischbach & Dittrich 1989 atlas TEXTBOOK]**
- Full visual-system model scale: **45,669 neurons, 1,513,231 synapses, 64 cell types** in the
  motion pathways. **[PRIMARY — Lappalainen et al. 2024]**

### 2.2 The compression: columns → LP

- **T4 (ON) and T5 (OFF) are the first direction-selective neurons**, with **four subtypes
  each (T4a-d, T5a-d) tuned to the four cardinal directions**. These are the fly's hardware
  implementation of the correlator arms — one set per column, tiled across the lattice.
  **[PRIMARY — Lappalainen et al. 2024 + refs therein]**
- Known inputs: T4 gets Mi1, Tm3, Mi4 (ON pathway); T5 gets Tm1, Tm2, Tm9 (OFF pathway).
  Tm3/Tm4 have broad receptive fields (two-column radius, 11.6°); the rest are narrow
  (single-column, 5.8°) — i.e. the fly's correlator mixes spatial scales of delay-line span.
  **[PRIMARY — Lappalainen et al. 2024]**
- Downstream: T4/T5 subtypes pool by preferred direction onto the ~58 LPT neurons, which
  compute wide-field optic-flow patterns (rotation vs translation components); HS/VS cells are
  electrically coupled ipsilaterally and to contralateral partners. Output: descending neurons
  → steering. **[PRIMARY — Schnell 2010 (coupling); Zhao 2023 (catalog); descending stage
  TEXTBOOK]**
- The **H1 cell**: a spiking lobula-plate output neuron, excited by ipsilateral horizontal
  back-to-front motion (note: opposite preferred direction to HS cells), contrast-invariant,
  projects to the contralateral lobula plate — the classic "one spike train, whole-field
  motion" cell used in information-theoretic work. **[TEXTBOOK — Hausen; H1 in Calliphora also
  referenced in Supple et al. 2022, fetched today]**

### 2.3 Why ~60 is the right arity (and what it means for ie1)

The fly compresses ~10³–10⁴ local correlator outputs (T4/T5 per column per direction subtype)
into **58 wide-field channels** — and 58 is *more* than the behavior needs (heading rotation
needs ~3 axes; the surplus encodes figure vs ground, small-object motion, and pattern
subtractability, cf. FD cells **[TEXTBOOK]**). For ie1: **4 motion-direction codes is the
faithful arity** (T4a-d / T5a-d cardinal directions), and the pooling operator is
`mean/sum of signed correlator outputs per direction`. That's the LP build. If 4 pooled codes
don't clear R² ≥ 0.5 at ≥2 densities, add the *next-faithful* thing: spatially tiled
pools (N/E/S/W × 2 tiles) — the fly's HS cells themselves are tiled (HSN/HSE/HSS cover
dorsal/equatorial/ventral) — before reaching for heavier readers.

---

## 3. Flicker fusion / CFF — the measured values and the ecology

### 3.1 Definition and the knobs

CFF = the modulation frequency at which flicker becomes perceptually steady (50% detection).
Depends on: frequency, modulation depth, mean illumination, wavelength, retinal position,
adaptation state, physiology (age/sex/fatigue). **[TEXTBOOK — standard psychophysics;
parameters list verified against Wikipedia "Flicker fusion threshold", fetched today]**
Key physiology: rod-mediated vision fuses ~15 Hz; cone-mediated plateaus **~60 Hz at very
high luminance** (humans range ~50–90 Hz for cones). **[TEXTBOOK]**

### 3.2 Cross-species values

| animal | CFF (approx) | status |
|---|---|---|
| human | ~50–90 Hz (cones, bright light; ~60 plateau) | **[TEXTBOOK]** |
| honeybee | ~200 Hz at high luminance (Autrum & Stöcker 1950) | **[TEXTBOOK — classic, not re-verified today]** |
| blowfly / housefly | ~250 Hz (Autrum-era ERG/behavioral) | **[TEXTBOOK — classic]** |
| Drosophila | tens–~250 Hz depending on method/light; photoreceptors encode fast bursts | **[PRIMARY-adjacent — Juusola et al. 2017 eLife 6:e26117, fetched: R1-R6 encoding capacity maximized for fast high-contrast bursts]** |
| dragonflies | among the fastest in the kingdom (pursuit predators) | **[PRIMARY — Haarlem et al. 2026, qualitative; specific ~300 Hz figure not verified]** |
| Lepidoptera | diurnal butterflies > skippers (intermediate) > nocturnal moths | **[PRIMARY — Chatterjee et al. 2020, J Comp Physiol A 206:671, abstract verified]** |

### 3.3 The tradeoff ecology (the "Luke et al." correction)

The flicker-fusion meta-analysis Casey remembers as "Luke et al." is **Healy K, McNally L,
Ruxton GD, Cooper N, Jackson AL (2013), "Metabolic rate and body size are linked with
perception of temporal information," Animal Behaviour 86:685–696** **[PRIMARY — PubMed +
PMC full text fetched]**:

- Across a wide vertebrate phylogeny, **CFF increases with metabolic rate** (mass-corrected)
  and **decreases with body mass** — quantified: **≈ −2 Hz CFF per +10 kg body mass**.
- **Low light lowers CFF** (sensitivity–resolution tradeoff).
- The mechanism is the metabolic/physiological budget: fast photoreceptor and neural
  kinetics cost energy; small, hot-running, fast-lived animals buy temporal resolution.
- The 2026 successor: **Haarlem et al. 2026, Nature Ecology & Evolution 10:712–720, "Pace of
  ecology drives the tempo of visual perception across the animal kingdom"** — 237 species
  from jellyfish to vertebrates; **flying and pursuit-predating species have higher temporal
  resolution**; ambush predators' tempo is context-mediated. Autrum's hypothesis, finally
  kingdom-wide. **[PRIMARY — abstract verified]**

### 3.4 What this buys ie1/ie2

The fly's CFF is set by photophysics + metabolism; **ie1's CFF is set by renderer fps,
glyph budget (chars/sec), and the delta-stream's temporal kernel.** ie2 (the CFF-curve
experiment) is exactly the right measurement: sweep glyph-fps at fixed chars/sec against a
fHz pulsed scene, find where the delta stream can no longer resolve on/off. Expect the
correlator's usable band (ωτ=1) to sit *well below* the raw CFF — the fly's behavioral
temporal optimum (~1–6 Hz) sits far below its ~250 Hz photoreceptor CFF. Design so the
reflex channel (fast, pooled, few codes) and the planning channel (slower, content) get
different parts of the band — that split is §1.4's lesson, not decoration.

---

## 4. Motion hyperacuity — displacements finer than Δφ

**The claim, and its bounds:** insects detect/discriminate displacements well below their
interommatidial angle Δφ. For Drosophila, Δφ ≈ **5.1°** with photoreceptor acceptance angle
≈ **5.7°** (blur > sampling pitch — the optics already smear before sampling).
**[PRIMARY — Stavenga 2003 as cited/used in Clark et al. 2011, whose bar-pair stimuli were
designed on these numbers]**

**Verified mechanisms and measurements:**

1. **Active mechanical scanning.** The CurvACE compound-eye robot achieves target-edge
   localization with "hyperacuity, i.e. much finer resolution than the coarse inter-receptor
   angle" by *imposed scanning at 50 Hz* + Gaussian receptive-field summation — a direct
   biomimetic receipt that scanning + pooling beats the sampling pitch (modeled on hoverfly
   *Syritta* pursuit). **[PRIMARY — Colonnier et al. 2019, Bioinspir Biomim 14:036002]**
2. **Microsaccadic photoreceptor sampling.** Drosophila R1-R6 photoreceptors maximize their
   encoding capacity for fast high-contrast bursts; combined with the fly's saccadic turning
   behavior, measured visual performance *beats* the classic sampling-limited prediction
   ("see the world far better than predicted from the classic theories").
   **[PRIMARY — Juusola et al. 2017, eLife 6:e26117]** (note: this mechanism paper is
   influential but not uncontested; treat magnitude claims as upper bounds. **[FLAG]**)
3. **Correlation + population pooling.** The HRC array itself converts *temporal* precision
   into *spatial* precision: velocity/displacement estimates pooled across thousands of
   detectors are finer than any single detector's pitch. The blowfly H1 neuron encodes
   motion with sub-pitch precision in real time (classic information-theoretic work:
   de Ruyter van Steveninck & Bialek 1995, Proc R Soc B 262:349). **[TEXTBOOK/SECONDARY —
   not re-verified today; flagged]**

**For ie1:** don't expect a *single* correlator to resolve sub-glyph displacements. The
readout path that earns hyperacuity is: many correlators → signed pooled codes → reader
estimates *continuous* drift from the code stream (exactly the planned ridge/MLP reader).
That is the same compression the fly uses — the regressive reader plays the role of the
LPTC pool + downstream motor decode.

---

## 5. The optomotor closed loop — correlator → motor reflex

**Loop structure** (Reichardt & Poggio's flight simulator, formalized in the 1976 Q Rev
Biophys pair): yaw torque R(EMD output) → changes angular velocity → changes retinal slip →
negative feedback on R. Closed-loop gain stabilizes heading; the *open-loop* measured
quantities below are what you implement. **[PRIMARY — Reichardt & Poggio 1976 abstracts
verified; equations TEXTBOOK]**

**Measured latencies and dynamics (the real reflex budget):**

| stage | value | source |
|---|---|---|
| EMD delay-filter peak | ~25 ms | **[PRIMARY] Clark 2011** |
| behavioral response filter | consistent with known fly response times (tens of ms) | **[PRIMARY] Clark 2011** |
| **optomotor lift: constant reaction delay** | **75 ms**, gain linear-decreasing, LTI behavior confirmed, control band **≤ ~6 Hz** | **[PRIMARY] Graetzel, Nelson & Fry 2010, J R Soc Interface 7:1603** |
| yaw torque latency (classic figure) | ~40–60 ms | **[TEXTBOOK — Götz 1964; not independently re-verified]** |
| photoreceptor → LPTC conduction | ~20–40 ms | **[TEXTBOOK]** |

**Audit of the "<50 ms reflex path" claim:** roughly right for *yaw torque* in large flies at
warm temperature, but the carefully-measured Drosophila *lift* loop is **75 ms** and capped at
~6 Hz of controllable oscillation. Budget ie1's reflex lane at **50–100 ms** and assume the
usable closed-loop bandwidth is single-digit Hz — matching the fly. **[audited against
Graetzel 2010]**

Also note: optomotor gains are **behavior-state dependent** (walking vs flying vs treadmill)
and the delay filter adapts to light level **[PRIMARY for delay adaptation — Harris 1999;
state-dependence TEXTBOOK]** — two more reasons τ and gain should be *dials*, not constants.

---

## 6. What ie1 should copy vs depart from

### COPY (biology says this is load-bearing)

1. **Delay-LP + multiply + mirror-subtract, signed inputs.** The two-arm subtraction is the
   direction operator; signed contrast keeps reverse-phi arithmetic (and thus edge-polarity
   information) intact. Day-one implementation. (§1.2, §1.5)
2. **τ ≈ 25–50 ms as the first dial**, peak response at ωτ=1; sweep τ across densities
   instead of hardcoding. The fly's τ itself adapts with light level — adaptive τ is faithful,
   not fancy. (§1.3)
3. **Four cardinal-direction codes on the lattice** = T4a-d/T5a-d arity. Pool signed
   correlator outputs per direction (mean over active cells) → the "LP build." (§2.2)
4. **ON/OFF split only if needed:** Eichner's two-detector form (ON-ON, OFF-OFF) + Clark's
   weighted quadrants are the *upgrade path* if plain HRC misses the R² gate — e.g., when
   glyph scenes are edge-polarity-coded. (§1.4)
5. **Population pooling earns hyperacuity.** Sub-pitch drift readout comes from the reader on
   pooled codes, never from single correlators. (§4)
6. **Keep the c² fingerprint.** Response should grow ~quadratically with contrast — that's a
   cheap unit test of a correct correlator (linear response to the *product*, not to either
   input alone; Clark 2011 verified this in the fly). (§1.2)
7. **Reflex budget 50–100 ms, single-digit Hz closed-loop bandwidth.** Separate fast pooled
   reflex codes from slower content-carrying streams. (§5, §3.4)

### DEPART (where copying would be cargo cult)

1. **No biophysical multiplier.** Arenz/Gruntman divisive-ON-OFF refinements and conductance
   models explain the *neuron*; ie1 needs the *code*. Plain HRC arithmetic is the right cost
   point; revisit only if the c1 gate fails. (§1.4)
2. **Rectangular + toroidal lattice ≠ hex eye — own the difference.** The hex eye has 3 axes
   at 60°; a rectangular lattice has axis-aligned pairs (Δφ = pitch) and diagonal pairs
   (Δφ = pitch·√2) with different tuning curves. Fly eyes are also anisotropic (horizontal
   vs vertical acuity differ), so anisotropy is authentic — but *document per-axis* tuning
   (aliasing flips at λ = 2Δφ differ per axis). ie3's toroidal wrap is the right move for
   heading-continuous motion. (§1.2 property 3, chiaroscuro doc)
3. **No scanning hardware.** The fly's scanning hyperacuity (retinal microsaccades, wing/head
   oscillations) has no glyph-lattice analogue; don't fake it. Let pooling + reader do the
   sub-pitch work. (§4)
4. **CFF is yours to set, not inherit.** Fly CFF is photophysics; yours is renderer/glyph
   budget. Measure it (ie2) and couple the correlator band to the measured curve — expect the
   usable motion band to sit ~1–2 orders below raw CFF, exactly as in the fly. (§3.4)
5. **58 channels is the ceiling, 4 is the floor.** The fly spends surplus channels on figure/
   ground and small-object motion. ie1 starts with 4 direction codes; add tiled pools before
   adding opcodes. (§2.3)
6. **Don't re-implement the lamina.** Lateral inhibition/contrast gain control upstream of the
   correlator is a real fly stage (LMC high-pass, 50–100 ms), and a cheap *optional* prefilter
   (local mean subtraction) for glyph scenes — but it's a prefilter, not a required stage for
   the c1 gate. (§1.3, §1.5)

---

## 7. Source ledger

**Fetched & verified today (2026-09-28):**

- Clark DA, Bursztyn L, Horowitz MA, Schnitzer MJ, Clandinin TR (2011) "Defining the
  computational structure of the motion detector in Drosophila." Neuron (PMC3121538). — HRC
  kernel, 25 ms delay peak, four signed unit computations, reverse-phi, weighted quadrants,
  Δφ=5.1°/5.7° optics.
- Borst lab (MPI-BI) modeling page — modern HRC statement; Arenz 2017 division; Gruntman 2018;
  "HRC underestimates T4/T5 direction selectivity."
- Joesch M, Schnell B, Raghu SV, Reiff DF, Borst A (2010) "ON and OFF pathways in Drosophila
  motion vision." Nature 468:300. — L1=ON, L2=OFF, electrical coupling.
- Eichner H, Joesch M, Schnell B, Reiff DF, Borst A (2011) "Internal structure of the fly
  elementary motion detector." Neuron 70:1155. — two detectors (ON-ON, OFF-OFF), not four.
- Schnell B, Joesch M, Forstner F, Raghu SV, Otsuna H, Ito K, Borst A, Reiff DF (2010)
  "Processing of horizontal optic flow in three visual interneurons of the Drosophila brain."
  J Neurophysiol 103:1646. — HSN/HSE/HSS, correlation-model consistency, ipsi/contra coupling.
- Zhao A, Nern A, Koskela S, ... Chiappe E, Reiser MB (2023) "A comprehensive neuroanatomical
  survey of the Drosophila Lobula Plate Tangential Neurons." bioRxiv 2023.10.16.562634. —
  **58 LPT neurons per hemisphere** (the EM catalog).
- Lappalainen JK, Tschopp FD, ... Turaga SC (2024) "Connectome-constrained networks predict
  neural activity across the fly visual system." Nature 634:1132 (PMC11525180). — 45,669
  neurons / 1.5M synapses / 64 types / 721 columns; T4a-d/T5a-d cardinal directions; T4/T5
  input cell types and RF widths.
- Matsliah A, Yu SC, ... Seung HS, FlyWire (2024) "Neuronal parts list and wiring diagram for
  a visual system." Nature 634:166. — optic-lobe cell-type atlas (context for counts).
- Healy K, McNally L, Ruxton GD, Cooper N, Jackson AL (2013) "Metabolic rate and body size are
  linked with perception of temporal information." Anim Behav 86:685 (PMC3791410). —
  **this is the real "flicker fusion" meta-analysis** (not "Luke et al."): −2 Hz per +10 kg,
  metabolism positive, low light negative.
- Haarlem CS, Hynes C, Jackson AL, Mitchell KJ, O'Connell RG, Healy K (2026) "Pace of ecology
  drives the tempo of visual perception across the animal kingdom." Nat Ecol Evol 10:712. —
  237 species; flight + pursuit predation → higher CFF.
- Chatterjee P, Mohan U, Krishnan A, Sane SP (2020) "Evolutionary constraints on flicker
  fusion frequency in Lepidoptera." J Comp Physiol A 206:671. — diurnal > crepuscular >
  nocturnal temporal sensitivity.
- Graetzel CF, Nelson BJ, Fry SN (2010) "Frequency response of lift control in Drosophila."
  J R Soc Interface 7:1603. — **75 ms** constant delay, LTI, ≤6 Hz control band.
- Juusola M, Dau A, ... Takalo J (2017) "Microsaccadic sampling of moving image information
  provides Drosophila hyperacute vision." eLife 6:e26117. — hyperacute vision mechanism
  (flagged: contested upper bounds).
- Colonnier F, Ramirez-Martinez S, Viollet S, Ruffier F (2019) "A bio-inspired sighted robot
  chases like a hoverfly." Bioinspir Biomim 14:036002. — scanning hyperacuity in CurvACE.
- Supple JA, ... Krapp HG (2022) J Exp Biol 225:jeb244087. — H1 as the Calliphora LP
  optic-flow cell (peripheral confirmation).
- Reichardt W, Poggio T (1976) Q Rev Biophys 9:311–75, 377–438. — quantitative optomotor
  theory (abstracts verified; equations TEXTBOOK).
- Borst A, Egelhaaf M (1989) "Principles of visual motion detection." Trends Neurosci 12:297.
- Wikipedia "Flicker fusion threshold" (fetched) — CFF parameters, human rod/cone plateaus.

**Textbook-level, cited but NOT independently re-verified today (canon, not receipt):**

- Hassenstein B & Reichardt W (1956) Z Naturforsch 11b:513 — original correlator inference.
- Reichardt W (1961) in *Sensory Communication* — the EMD formalization.
- Autrum H & Stöcker M (1950) — honeybee CFF ~200 Hz; Autrum-era blowfly ~250 Hz figures.
- Hausen K (1982/1984) J Comp Physiol A — HS/VS taxonomy in Calliphora.
- Fischbach KF & Dittrich AP (1989) — optic-lobe columnar atlas (~700–900 columns).
- Götz KG (1964) Biol Cybern 2:77 — yaw optomotorics, ~40–60 ms latency figure.
- Harris RA, O'Carroll DC, Laughlin SB (1999) Vision Res 39:2603 — delay-filter adaptation
  (abstract-level PRIMARY; parameter details textbook).
- de Ruyter van Steveninck RR & Bialek W (1995) Proc R Soc B 262:349 — H1 real-time
  information transfer.

---

## 8. Receipts-for-builders box (the numbers ie1 will actually use)

```
Δφ (lattice pitch analogue, Drosophila)      5.1°  [Clark 2011 / Stavenga]
acceptance angle (blur, PSF analogue)        5.7°  [same]
delay filter τ (first dial)                  25–50 ms, peak at ωτ=1  [Clark 2011]
behavioral delay-arm memory                  ≥ 1 s (reverse-phi at 1 s ISI) [Clark 2011]
LP/HP prefilter timescale                    50–100 ms [Clark 2011 / Juusola, Laughlin]
response nonlinearity                        c² quadratic [Clark 2011]
spatial aliasing                             sign flip at λ = 2Δφ [textbook HRC]
T4/T5 arity                                  4 cardinal directions × ON/OFF [Lappalainen 2024]
LP pool size                                 58 wide-field neurons/hemisphere [Zhao 2023]
HS cells                                     3 (HSN/HSE/HSS) [Schnell 2010]
reflex latency                               ~50 ms yaw (textbook) / 75 ms lift (measured)
closed-loop bandwidth                        ≤ ~6 Hz [Graetzel 2010]
human CFF                                    ~60 Hz cone plateau [textbook]
honeybee CFF                                 ~200 Hz [textbook Autrum]
blowfly CFF                                  ~250 Hz [textbook Autrum]
CFF–body mass                                ≈ −2 Hz per +10 kg; +metabolic rate = +CFF
                                             [Healy 2013]
CFF–ecology                                  flight & pursuit predation → higher CFF
                                             [Haarlem 2026]
```

*Written by the ie1 science lane, 2026-09-28. Sibling docs: chiaroscuro-insect-eye (ie1–ie3
specs), quilt-insect-brain (the fly-sim deconstruction).*
