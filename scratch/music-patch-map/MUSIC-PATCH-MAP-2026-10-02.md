# MUSIC PATCH MAP — 23-repo census (2026-10-02, Lucineer)

Census method: gh api metadata only (no clones); name|language|size|pushed_at|description pinned from API responses.
Directive: 'modular music tools that could be made into quilt patches to be stitched by agents and human'

## Casey's framing (16:57): MIDI = temporal understanding, first class
flux-tensor-midi was 'an early idea two for midi as a tool for temporal understanding
as first class' — this shop is not just instruments, it is the fleet's TEMPORAL SENSE
organs. MIDI = the fleet's first-class format for time-structured events.

## The two-layer bus (names vs bytes, again)
- plainsong = the WORD layer: human/agent-readable notation in markdown
- flux-tensor-midi = the BYTE layer: 4D tensor of MIDI events, 6 languages (PY/Rust/C/CUDA/Fortran/JS),
  room musicians, Eisenstein snap, INT8 saturation, side-channels
Patch manifests MUST pin the byte-spelling of the event schema (hash_spec lesson applies
to music: same notes, different tensors). A patch declares which layer it speaks.

## The insight
plainsong IS the patch bus: plain-text notation that compiles to MIDI and embeds in
markdown like mermaid. Agents stitch by writing notation into receipts; humans edit
the same markdown. One lingua, two species of musician.

## Patch taxonomy (quilt genome applied)
- BUS: plainsong (text->MIDI, markdown-embeddable)
- gen: duke-lab, q16-trajectories, fleet-midi-{rand,prob,emergent}, music-vibe-experiments, fleet-jepa-midi
- transduce: fleet-a2a-spectral (graph->MIDI), plato-room-musician (rooms->MIDI), si-sonic-shape (confidence->music)
- transform(theory): ternary-music, symplectic-music, spectral-music-v2, topo-sonata, musician-soul
- listen: plato-music-sync (groove/counterpoint), holonomy-harmony (progression analysis), fleet-music-theorist
- infra/pedagogy: fleet-sheet-music, fleet-midi-pedagogy; sonic-shape = twin/stub of si-sonic-shape (verify before patchifying)

## Proposed patch manifest (PATCH.md per repo)
{kind: gen|transduce|transform|listen|bus, input, output, interface, deterministic, seedable, receipt_verb}
Stitch = receiptd receipt chain (corr = the jam session id); each hop appends with the
built/planned verb split. Human edits the same plainsong markdown the agents read.

## Census table (pinned)
repo|lang|kind|note
flux-tensor-midi|6-lang|FORMAT(4D MIDI tensor)|temporal understanding first-class; the byte layer under the bus
duke-lab|JS|gen|generative music lab; the generative argument
q16-trajectories|JS|gen+browse|breeds duke-lab arguments in 16-dim rational space
musician-soul|Rust|transform+listen(soul)|vector-DB musician personas; MIDI digestion; jam sessions; Influence->What-Works->Soul
plainsong|PY|BUS(notate/render)|plain-text notation -> MIDI; embeds in markdown like mermaid (31MB)
fleet-jepa-midi|Rust|gen(3-layer intelligence)|LLM phrasing + JEPA pulse + algorithms in samples (20MB)
spectral-music-v2|Rust|transform(theory)|chords as nodes, voice-leading as edges, CR consonance, splines
si-sonic-shape|PY|transduce(confidence->music)|confidence-to-music mapping engine
sonic-shape|PY|transduce(stub)|confidence-to-music (2KB stub/twin of si-sonic-shape)
plato-music-sync|Rust|listen(sync/groove)|polyrhythmic scheduling, groove tracking, counterpoint for Plato rooms (9.7MB)
plato-room-musician|PY|transduce(rooms->MIDI)|rooms->MIDI; room=musician, tile=note
topo-sonata|Rust|transform(theory)|form as topological space; voice-leading as homotopy (25MB)
music-vibe-experiments|Rust|gen(vibe->MIDI)|vibe space -> MIDI; dimension sweeps; style prototypes
ternary-music|Rust|transform(theory)|ternary harmony theory
symplectic-music|PY|transform(theory)|Hamiltonian mechanics of harmony; symplectic integrators (1.3MB)
holonomy-harmony|PY|listen(analysis)|chord progression holonomy; modulations, modal interchange detection
fleet-sheet-music|PY|infra|fleet service (8KB)
fleet-music-theorist|PY|listen(theory svc)|fleet service (13KB)
fleet-midi-rand|Go|gen(agent-random)|aleatoric generation from agent randomness
fleet-midi-prob|Go|gen(markov)|Markov-transition music from agent state
fleet-midi-pedagogy|Makefile|pedagogy|theory education via fleet MIDI (2.3MB)
fleet-midi-emergent|PY|gen(interaction)|emergent patterns from agent interaction, no central control
fleet-a2a-spectral|PY|transduce(graph->MIDI)|Laplacian/Fiedler/Cheeger -> MIDI

## V0 stitch candidate (first receipted jam)
fleet-a2a-spectral (our graph -> MIDI) -> plainsong (notation) -> musician-soul (soul reaction)
-> holonomy-harmony (analysis) — every hop receipted, corr = session id. Falsifiable:
the chain either produces a playable score + analysis receipt, or names the missing patch interface.
