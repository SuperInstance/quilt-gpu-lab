# DIAL-LIB v0 — the fleet's artist-decomposition dials (2026-10-02)

Born from duke-lab canon:1 ("a GAN with words", 16-feature ruler) + Casey's thesis:
*the next artist mimic will have the dial already figured out; the more artists we do,
the more dials we learn; future artists cost fewer and fewer cloud calls.*

A **dial** = one legible dimension of "how an artist sounds feels", with three faces:
1. **Ruler face** — deterministic extractor from the per-note trace (duke-lab `extractFeatures`,
   0..1 normalized). Names are the critic's vocabulary.
2. **JEV cell face** — a typesafe judgment cell (noul/score) that grades a candidate on this
   dial from its trace/plainsong text; the cell is the cloud-call face, used only where the
   ruler can't reach (feel, intent).
3. **Field face** — ExoJ amplitude: γ = calibrated confidence in the dial reading,
   η = surprise (how far this artist sits from the library prior), Δ = identity fragments
   (signature dial COMBOS, never single dials). Conservation γ+η ≤ 1 per cell.

## The 16 seed dials (from duke-lab engine.js, pinned verbatim 2026-10-02)

| # | id | label | extractor note |
|---|----|-------|----------------|
| 1 | registerSpread | REGISTER SPREAD | pitch span of the take |
| 2 | trebleActivity | TREBLE ACTIVITY | upper-register note share |
| 3 | dynRange | DYNAMIC RANGE | velocity spread |
| 4 | dynContour | DYNAMIC CONTOUR | velocity shape over time |
| 5 | swingFeel | SWING FEEL | mean deviation of half-beat gaps from straight 0.5 (÷0.33) |
| 6 | syncopation | SYNCOPATION | off-beat attack share |
| 7 | downbeatWeight | DOWNBEAT ORTHODOXY | how much attacks land on downbeats |
| 8 | harmonicComplex | HARMONIC COMPLEXITY | chord/pitch-class diversity |
| 9 | chromaticism | CHROMATICISM | non-diatonic share |
| 10 | repetition | REPETITION | motif reuse rate |
| 11 | callReply | CALL / REPLY | antecedent-consequent structure |
| 12 | density | DENSITY | events per bar |
| 13 | phraseVariance | PHRASE VARIANCE | phrase length/shape diversity |
| 14 | restRatio | REST RATIO | silence share |
| 15 | bassMovement | BASS MOVEMENT | bass-line motion rate/span |
| 16 | cadenceRegular | CADENCE REGULARITY | cadence periodicity |

Weights side (critic personas) are dials too: purist / engineer / romantic / historian.

## JEV cell template (typesafe, api.typesafe.ai/v1/systemone, model jev-latest)

```json
{"model":"jev-latest",
 "state":"<per-note trace summary OR plainsong text>",
 "questions":{
   "swingFeel":{"type":"score",
     "question":"Rate the swing feel of this take on the dial.",
     "criteria":["mechanically straight eighths","hints of layback",
                 "syrupy late-jazz swing","extreme displaced swing"]}}}
```
Rules from the verified doc: questions = dict; criteria dict for choice, LIST for score;
noul takes instructions string. Key read at use-time from /mnt/c/Users/casey/key.txt.

## Artist-field format (ARTIST-FIELD.md per artist)

```yaml
artist: DUKE ELLINGTON
canon_source: SuperInstance/duke-lab engine.js ARTISTS.duke (pinned 2026-10-02)
centroid: {registerSpread: .78, trebleActivity: .72, dynRange: .55, dynContour: .62,
  swingFeel: .62, syncopation: .70, downbeatWeight: .45, harmonicComplex: .82,
  chromaticism: .58, repetition: .38, callReply: .80, density: .62,
  phraseVariance: .60, restRatio: .30, bassMovement: .78, cadenceRegular: .50}
signature_fragments: [jungle-harmony, plunger-growl, call-reply-high+bassMovement-high]
blurb: "Jungle harmony, the plunger growl, voicings nobody else could voice."
dials_reused: 16   # at seed
dials_new: 0       # library born from him
cloud_calls: 0     # decomposition predates the library
```

## Seeded artists (all three pinned from engine.js ARTISTS)

- **DUKE ELLINGTON** — Bb2 anchor. Jungle harmony, plunger growl.
- **BILL EVANS** (F) — "Cluster voicings held like breath; the quietest loud music ever
  made." dynRange .88, dynContour .90, harmComplex .92, restRatio .66, repetition .22.
- **THELONIOUS MONK** — "Angular cells, sudden stops, notes that land like dropped tools."
  syncopation .82, repetition .74, phraseVariance .85, restRatio .72, downbeatWeight .18,
  cadenceRegular .18.

## SPLINE protocol (how other artists' feel-vecs interpolate)

1. Pick two artist fields A,B and λ ∈ [0,1]; centroid' = (1−λ)·A + λ·B (per dial).
2. Generate with the interpolated params (duke-lab engine, plainsong out).
3. Extract features from the generated take; verify distance(extracted, centroid') ≤ ε
   (generator controllability = **the dial explains the output** — this is ExoJ legibility:
   a person sees WHICH dials carried the sound).
4. JEV cells grade the take blind on the signature fragments of A and B; the receipt
   records whether the cells hear the spline where the ruler does.
5. Receipt every hop (receiptd chain, corr = the spline session).

## REUSE-LEDGER (the compounding proof)

| artist | dials reused | dials new | cloud calls | notes |
|--------|--------------|-----------|-------------|-------|
| DUKE ELLINGTON | — (seed) | 16 (born here) | 0 | duke-lab, prior work |
| BILL EVANS | 16 | 0 | 0 | centroid already in engine |
| THELONIOUS MONK | 16 | 0 | 0 | centroid already in engine |
| *(next artist)* | ? | ? | ? | the falsifiable claim: fewer than the seed |

Library law: a dial enters the library only with a receipted calibration (separates at
least two artists, or measurably fails — a failed dial is still a learned dial if journaled).
