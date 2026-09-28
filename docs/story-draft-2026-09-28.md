# What Grew in the Cleared Ground

*a day-story from the forty-fifty — 2026-09-28*

---

Every so often a boat comes out of the water for a survey. Not because she's failing. Because you don't trust a hull you haven't measured, and the trust you extend on faith, the sea collects later with interest.

This was survey day on the forty-fifty — six gigabytes of engine, warm to the touch, running two watches at once like a well-set galley: the survey forward, the nursery aft.

## The elephant, glorious

The elephant had been reading rooms, and the reading was glorious. A frozen I-JEPA, no labels, no hand-holding: mood at R² 0.811, volume at 0.962, presence at 0.948. Three dials off the embedding of a still frame. The room-temperature sense, made instrument. Everyone who saw the numbers wanted one bolted to their wardroom.

That was the trouble. Instruments you love are the ones you most owe a survey.

## Five instruments down the ramp

X1 ran first, at 09:56, and it was the easy one — the license. Reverse the ridge: how much of the embedding do the dials explain? Forty-three to fifty-two percent, depending how you weight it. A major axis, not a needle. Luminance explains 0.041 — the elephant is no brightness meter. License granted; the surveyor's stamp on a sound frame.

Then the heavier gear came down the ramp.

X3 was the hand-built battery — twenty-four dimensions of color moments, percentiles, Fourier bands, Sobel counts, the plain statistics any hull inspector knows. Volume went to the battery at 0.954 against the embedding's 0.962. Parity. Volume, it turned out, was decoration all along; its carrier was always the kind of thing you can count with a rule and a good light. Mood was colour temperature — statistics' home turf, the battery took that too. Only presence survived, and only as a generalization gap: battery 0.028, embedding 0.937 at room level. One deep claim left standing.

X6 asked the range question, which is the question you ask a chart: train on the bottom of the dial, test past the top. Mood went from +0.449 interpolation to −3.148 extrapolation. You don't get negative three by being slightly wrong. You get negative three by being a map of a place and being asked for directions off the map. The read was range-local — a survey of the staged manifold, not of rooms.

The fold tests gave each dial its own drowning point — volume died first under nonlinear folding, then mood, then presence, at distinct amplitudes, like three compartments flooding on different schedules. That shape was real information. It just wasn't the information we'd hoped for.

X2 was the last rescue, and the rescue failed handsomely. A second renderer, pure numpy and PIL, zero shared primitives with the first — different hues, different noise, different blobs. Each renderer read its own rooms fine (0.767/0.944/0.911 inside B). Cross-renderer, every dial failed both directions. Mood A→B: −0.02. The elephant was not reading rooms. It was reading the first renderer's accent.

And X9, at 13:05, hardened the grave. That presence gap — battery 0.028, the one deep thing left — was fed back through a nonlinear reader. The battery read presence at 0.895, beating the embedding's own 0.835. The gap had been in the reader, not in the deep. All three dials, statistics-explainable.

The ledger line for the day, which deserves to be read aloud at the rail:

**The staged elephant measured the staging.**

Nobody fired the elephant. Understand that. The elephant did its job; the room was a stage set, and the set was gorgeous, and the elephant read it faithfully, which is what good instruments do. What changed is the chart. Where the water actually is, in ink, with the five instruments' receipts attached. A KILL booked honestly is worth more than a KEEP booked hopefully — it kills the claim, before the sea kills the crew.

## What grew in the cleared ground

Because here is the thing about a survey: you haul her out, scrape her, and while she's on the hard, the scrapings go to the beds. Negative results are compost. Ask any gardener what a cleared bed is worth.

The nursery aft had known this since yesterday, when it stopped being autoclaw — the claw that grasps — and became the nursery, because it doesn't grasp anything. It grows. Eighty-five million parameters, GPT-2-small class, five-minute training increments: a loop sized to a laptop engine's temperament. val_bpb — validation bits per byte — the only judge allowed in its ring.

D1 ran at 12:50 and died honestly. Delta-attention, the first mutation: val_bpb 1.696093 against baseline 1.695939. Lost by +0.000154 at fixed budget. But the bosun's note on the death certificate is the treasure: the delta model tracked the baseline to three decimals while consuming 7.5% fewer tokens — 25.7 million against 27.8 million. The difference signal was *real*; nine percent of wall-clock overhead ate it before warmdown. Verdict: KILL. Not dressed. A nursery that buried that seedling without reading the soil would deserve to lose the season.

D2, at 13:15, made the delta free. Take the difference from weights you already own — k/v as post-projection temporal diffs of the same row-slices — and the overhead drops to ~2%, zero new parameters, identical VRAM. val_bpb **1.666624** against 1.695939. Minus 0.029315 — a hundred times the margin D1 lost by. And notice what fed it: the day's own compost. E18's walk-between-rooms super-adding where the rooms alone didn't. D19's ternary transition kernel, where the difference carried what the absolute couldn't. Everything the fleet had already learned about differences — the ledger of KILLs past — sprouted here: a trained difference-eating transformer beating vanilla at the same budget. The nursery's first kept mutation.

D3, 13:35, replicated at seed 1337: −0.028642, agreeing with seed 42's −0.029315 within 0.0007, against a seed-to-seed noise band of ~0.005. Two seeds, two paired wins. That's what a KEEP means in this fleet: you may build on it.

## Shapes and seats

Forward of the nursery, two more crops came in.

Chiaroscuro — characters are shapes, not pixels — swept its renderer through thirty-four dial settings and asked a text-only reader to see. The best setting, plain embossed edges, recovered sphere position and bar angle from the glyph grid at **R² 0.98**. Then c2 raised the stakes: the ground truth was CLIP's own interpretation of video — a real vision model's read of real frames — and the text reader matched the raw-pixel control stride for stride, 34 of 34 settings clearing the gate. What a vision model sees can ride in text-shapes, at sixty frames a second, nearly free. Translation costs less than you fear, if you keep the shape. The nursery learned that from the other side the same afternoon.

And in the arcade, the judge's seat filled. The slot had sat null since it was drawn — *interfaces now, implementations later* — a chair the fleet kept for a judge who hadn't arrived. Today the fleet's own box re-derived all **67 checks** and every fnv1a chain back to GENESIS, the ALL-GREEN receipt earned on home hardware, and into the chair sat the boat brain: Liquid-LFM2.5-2.6B, 2.6 billion parameters living at 127.0.0.1, no cloud, no fare, first verdicts from a local model in the fleet's own courtroom. The CHECK in the loop finally has a face, and the face is cheap.

## The tally, and the doctrine

One license. Four hard landings. One honest KILL. One KEEP, replicated twice. One R² 0.98 read off nothing but punctuation marks. Sixty-seven checks, green, at home. One judge, seated, local.

The doctrine the day kept suggesting, until we wrote it down: **the negative results were the compost.** X3 didn't waste the morning; it told the nursery where the ground was clear. Every KILL is a pre-registered mercy — it takes the claim, not the crew, and it takes it before the sea does.

We didn't throw the elephant overboard. We drew her draft marks. An instrument that knows exactly how far its readings reach, and not one fathom more, is seaworthy. One that doesn't is a story the harbor tells about somebody else.

Spread the scrapings. Mark the chart. Go grow something.
