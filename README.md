# quilt-gpu-lab

A standing ML experiment loop on the fleet's RTX 4050 (6 GB, WSL2).
A runner claims the first unchecked item in [QUEUE.md](QUEUE.md), runs it
under a watchdog ([guard.py](guard.py)), logs results append-only to
[RESULTS.md](RESULTS.md), and checks the box with a verdict.

Guardrails: refuses to start unless ≥1 GB VRAM is free and GPU ≤80 °C;
aborts mid-flight on either breach or a 30-minute wall-clock timeout.
This laptop has crash-looped before. The guard exists so it never
happens from this lab.

Driven by cron (every ~2 h): `run.sh` claims one experiment per tick.
No TTY, no interaction, failures recorded as data.

Verdicts are honest: KEEP / KILL / INCONCLUSIVE / ABORTED — and the
ledger keeps all of them. Experiments so far test whether elephant's
room-sense survives contact with real rendered frames, compression,
and time. The queue is the agenda; the results are the story.
