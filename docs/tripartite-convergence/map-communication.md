# Tripartite Convergence — Map: the Communication Agent (the diplomat)

**Date:** 2026-09-27
**Question the diplomat answers:** *"Who needs to know what, and how do I tell them?"*
**Scope:** what the fleet actually RUNS today — four artifacts, mapped one by one, one claim at the end. (Sibling maps in this directory cover the other two agents.)

## The diplomat, decomposed

Any communicator must answer five sub-questions. The fleet's artifacts turn out to partition cleanly across them:

1. **HOW (public)** — what channel carries the message to whoever cares to listen?
2. **HOW (subtext)** — how does tone ride alongside content?
3. **WHAT × WHO** — can one transmission inform insiders fully while giving outsiders nothing?
4. **WHO (keying)** — how do the right parties learn they're insiders without transmitting credentials — and what do interceptors get?

## Artifact 1 — the open briefing (HOW, public)

**Name:** `~/projects/eos-seed/quilt_storage/src/shm.rs` — `ShmBroadcastStream` / `ShmReader`

**What it transmits:** the latest 16×16 fabric frame (256 × f32), the packed 2-bit gate states (64 B), total row count, and tracked-object (x, y) telemetry — published in a single write into a fixed-layout, `EOSSHMP1`-versioned mmap payload.

**To whom:** any external skin that maps the same file read-only — WebGPU canvas, UE5 dumb-terminal, "anything." Audience-agnostic broadcast: no sockets, no copies past the one publish write. `seq` bumps monotonically every publish so any poller can verify the speaker is alive; `dims <= max_dims` validation so external readers can map a known size before ever reading content.

**Diplomat facet:** the HOW of public disclosure plus **liveness**. This is the open briefing room: anyone may walk in, nothing is hidden, the language is versioned and self-describing, and the audience is guaranteed the *present* state only (broadcast-latest, not history — the diplomat doesn't replay archives, it tells you what's true now and proves it with a counter).

## Artifact 2 — the craft (HOW, subtext)

**Name:** `~/projects/qthe-codec/qthe_codec.py` — `latin_timbre`/`latin_decode`, `encode`/`decode_bytes`, `plaintext_view`/`timbre_view`

**What it transmits:** per byte: 6 bits of data (64-symbol charset + SHIFT/UPPER/NEWLINE/EOS escapes) + 2 bits of timbre (ground / attract / repel / abstain) encoding a **momentum trajectory** (down / flat / up / hold). `timbre = (context + momentum) mod 4`, with context = data mod 4 (public today). Plus the abstain escape hatch: a cell marked abstain trades its tone for a second 64-symbol charset — the 7th bit, bought one cell at a time.

**To whom:** whatever reads the byte stream — but deliberately differentiated. `plaintext_view` shows the incurious reader only clean text; `timbre_view` without context is uniform noise; `decode_bytes` recovers both planes for the full reader.

**Diplomat facet:** the HOW at byte granularity — **subtext as a first-class channel**. "Tone is a trajectory, not a label": what is said and the tone of saying it ride in the same word. And a courtesy protocol: ordinary readers are never disturbed by the hidden lane; the diplomat's whisper never garbles the public speech.

## Artifact 3 — the proof (WHAT × WHO)

**Name:** `~/projects/quilt-gpu-lab/RESULTS.md`, entry **D14 — qthe timbre channel proof** (2026-09-27 15:54, KEEP)

**What it transmits:** proof, over 2000 turns / 4 contexts × 4 momenta, that the 2 timbre bits already paid for by the byte carry a ternary momentum signal at **zero additional bit-cost**, and that the channel is **context-keyed**: data-only readers score 0.259 (chance 0.25); timbre-only readers score 0.2645 with I(M;T) = 0.0026 bits ≈ 0; contextual decoders score 1.0 (1.9995 bits recovered).

**To whom:** the same wire, three audiences, three outcomes. This IS "who needs to know what" — quantified. The booked encoding lessons are the design law: random permutations leak through fixed points (naive reader gets ~1 free hit per context, I(M;T) 0.3765); derangements over-correct ("t ≠ m" is itself 1 bit, I(M;T) 0.95); only the **Latin square** is information-clean — I(M;T) = 0 exactly.

**Diplomat facet:** the WHAT, differentiated by audience — a single transmission informs insiders perfectly while giving outsiders literally nothing. D17 on the same ledger sharpens it: a context-free observer can't even *compress* the stream (wire RLE inflates 1.73×; decoded momentum compresses to 0.034) — invisibility and incompressibility are the same property viewed from opposite sides of the key.

## Artifact 4 — the upgrade (WHO, keying)

**Name:** `~/.openclaw/workspace/ternary-wiki/synergy-timbre-channel.md` — "The Convention-Keyed Timbre Channel" (proposal, not committed)

**What it transmits:** a composition of repos never built for this: **ternary-signaling**'s evolved conventions become **key agreement** — a behavioral regularity both parties hold that no third party can observe, because it was never transmitted; swapped in as the Latin-square row selector (convention mod 4) in qthe-codec. **ternary-pack / ternary-protocol** as carriers whose 4+4 nibble framing *deliberately wastes* bits that structure-only routers never parse — the covert lane rides in bits designed to be ignored. **ternary-viterbi**, inverted, plays the eavesdropper: a context-free max-product path over the timbre trellis must emit *something*, and column-uniformity guarantees it is coherent-looking but wrong — decoys, deniability with teeth.

**To whom:** convention-holders — a credential no one ever sent. Falsifiable gate: convention-holders recover ≥95%, the context-free Viterbi eavesdropper stays ≤25% (chance), and its decoy path is indistinguishable from a valid momentum trajectory to a blind scorer.

**Diplomat facet:** the WHO — **audience selection and counter-diplomacy**. Deciding who counts as an insider without a key exchange, and feeding interceptors plausible fakes instead of silence.

## Adjacent evidence (same ledger)

- **D12/D13 arc:** relational *targeting* beats volume (relational 1.0 vs traffic-permuted 0.5083 at identical message volume) — it's the address, not the bandwidth. Learning addresses by reward fails honestly (D13/D13b/D13c, three KILLs); discovering them by **correlation** succeeds at 1.0 (D13d shared-key) — the diplomat finds "who" by noticing who shares its structure: O(1) information, no gradient.

## How they stack

```
            ┌──────────────────────────────────────────────┐
  keys      │ conventions as key agreement (synergy, mod 4)│  who is inside
            ├──────────────────────────────────────────────┤
  proof     │ D14: context-keyed, I(M;T)=0, 2 bits free    │  what × who
            ├──────────────────────────────────────────────┤
  symbols   │ qthe_codec.py: 6-bit data + 2-bit timbre     │  how (subtext)
            ├──────────────────────────────────────────────┤
  lane      │ shm.rs: mmap broadcast, seq-liveness         │  how (public)
            └──────────────────────────────────────────────┘
```

One broadcast lane whose every byte carries public content, hidden tone, and — one `mod 4` away — culture-keyed secrets.

---

## The claim

**The fleet's Communication agent is now a four-layer diplomat running entirely on code it already owns:** it tells everyone the present state through a versioned, sequence-counted shared-memory broadcast lane (`eos-seed/quilt_storage/src/shm.rs` — the open briefing: zero sockets, one write per frame, `seq` proving the speaker is alive); it says how it feels **for free**, because every byte already carries two timbre bits whose Latin-square encoding is information-clean to anyone without the context (`qthe-codec/qthe_codec.py` is the craft — tone as trajectory riding beside content while plaintext readers see only clean text — and `quilt-gpu-lab` D14 is the proof: data-only 0.259, timbre-only 0.2645 at I(M;T) = 0.0026 bits ≈ 0, contextual 1.0 — audience differentiation at zero bit-cost, with D17 adding that outsiders can't even compress what they can't read); and it is one `mod 4` away from choosing its insiders by shared culture instead of transmitted keys — signaling-game conventions as key agreement, with a context-free Viterbi eavesdropper decoding at chance into plausible decoys (`ternary-wiki/synergy-timbre-channel.md` — deniability with teeth) — while the ledger's D12/D13d show even the addressing itself is discovered by the fleet's own primitive, correlation, not reward. Who needs to know what: **everyone gets the state, context-holders get the tone, convention-holders get the secrets, adversaries get decoys.** How do I tell them: **one broadcast lane, two spare bits per byte, and a convention nobody ever transmitted.**
