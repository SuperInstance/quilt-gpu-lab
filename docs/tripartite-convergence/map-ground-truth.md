# Map: Ground Truth (the physicist) → what the fleet actually runs

*Tripartite-convergence series. The Ground Truth agent asks one question:
**"what IS the state of this system, physically?"** — not what the model
claims, not what the reward channel says. What the instruments read. This
doc maps each concrete artifact in the fleet onto the part of the physicist
it instantiates.*

---

## 1. `quilt-gpu-lab/guard.py` — the physicist's admissibility gate

**What it measures:** free VRAM (MiB) and GPU temperature (°C) via
`/usr/lib/wsl/lib/nvidia-smi`, sampled at preflight and every 5 s in flight,
plus wall-clock time against a hard 30-min timeout. Policy: refuse to start /
abort if free VRAM < 1024 MiB or temp > 80 °C. `summary()` reports what was
actually observed (min free VRAM, max temp, breach reason, timed-out).

**Which part of the physicist:** the **measurement-before-theory veto**. A
physicist will not accept a result gathered on an overheating, out-of-memory
apparatus: the physical envelope decides whether a claim is even admissible.
The guard makes that a hard precondition — the state of the silicon can kill
the run no matter what the experiment wants to report. And it reports honestly
about its own sampling, not about intent. E6 verified all breach paths
(low-VRAM refuses, high-temp refuses, healthy accepts).

## 2. `quilt-gpu-lab/RESULTS.md`, entry **D13d** — the physicist's verdict, booked

**What it measures:** partner_identification_acc = **1.0** (target 0.90) at
seed 2718, 8 cells, 200 observations, p_corr = 0.9 — a cell finds its true
partner by max |correlation| of atom streams, with **no reward signal at all**.
Set against the arc: D13 (Hebbian) 0.233, D13b (confidence-weighted) 0.30,
D13c (REINFORCE+baseline) 0.217, chance 0.143 — all KILL. D13d: KEEP.

**Which part of the physicist:** the **verdict discipline**. A number with its
seed, N, and target; a KEEP/KILL that follows the number, not the hope. Three
reward-based mechanisms falsified in a row, and the record says so plainly.
Also the instrument-honesty clause: the first D13d run used a cyclic pairing
(scrambled streams, 0.375) and is **booked as a bug** — the physicist records
the instrument error alongside the clean result, because a clean result with a
hidden calibration fault is not clean.

## 3. `elephant/elephant/vmf.py` — the physicist's estimator, with error bars

**What it measures:** a von Mises–Fisher MLE over the room's trailing
dial-window samples on S⁶: mean direction **μ̂**, concentration **κ**, ρ,
warmth as a fixed linear read of μ̂ (`warmth_vmf = Ŵ·μ̂`), bootstrap CI on κ,
jackknife SE(μ̂), saturation flags. Guards: returns `None` when N < 10 (κ not
identifiable — *never a fake number*), ρ clamped at 0.999, κ capped at 500
(dial saturation), and a documented small-sample bias warning that travels
with the code. `edge()` derives drift with a jackknife-SE deadband (`real`
only when ‖Δμ̂‖ > 2·max(SE)); `record_with()` books `imbalance ≡ d_mu` into
the cell ledger against a **sealed pre-outcome** `expected`.

**Which part of the physicist:** the **honest estimator**. "What is the
state?" answered as a direction + concentration + uncertainty — and answered
with a refusal (`None`) when the data cannot identify it, rather than a
plausible-looking number. The deadband is measurement-noise discipline: change
is not declared real until it clears the noise floor. This is D13d's verb
spoken at room scale: fit the co-variation, read its direction.

## 4. `elephant/elephant/field.py` — the physicist's state variables

**What it measures:** the room as a 7-dial ensemble vector (`RoomField`):
mood, volume, earnestness, cynicism, joke_landing, panic, presence.
Observables: `warmth()` (fixed weighted projection), `distance()` (room-to-room
gap), `sauna_plunge_gap()` (signed contrast on entry). Dynamics:
`acclimation_curve()` (exponential relaxation of agent toward room, rate =
skill), `acclimation_rate_from()` (**inverts** the curve to recover the
physical parameter from observation), `charisma_pull()` (room bending toward
an agent per interaction).

**Which part of the physicist:** the **state-variable layer and
phenomenological laws**. The dial ensemble is the room's state vector;
warmth/contrast are its macroscopic observables; acclimation is a stated
dynamical law whose parameter is *estimated by inversion*, the way you recover
a drag coefficient from a decay trace. And it models instrument retirement:
vmf.py explicitly bans the v0 `concentration()` proxy (2·‖v − 0.5·𝟙‖) from
comparison paths because it is collinear with |warmth| — a biased instrument
kept for back-compat logging, barred from measurement. That is physicist
conduct toward one's own early apparatus.

## 5. `~/.openclaw/workspace/SYSTEM.md` — the physicist's apparatus sheet

**What it measures:** the measurement device itself. RTX 4050 Laptop, 6141 MiB
VRAM, compute capability 8.9; driver 616.92 / CUDA 13.4; WSL2 dxg passthrough
status; 15 GiB visible RAM with the autoMemoryReclaim OOM scar; ext4 fast lane
vs /mnt/c slow lane; NVENC/NVDEC benchmarks verified live (165 fps 1080p60
h264_nvenc); crash-loop history with the driver fix and date attached.

**Which part of the physicist:** the **calibration sheet for the apparatus**.
Ground truth about the instrument, not the sample: what the lab can physically
do, what breaks it, what was verified live and when. This is the same
knowledge as guard.py at a different altitude — SYSTEM.md is the record
("this laptop crash-looped; here is why and when it was fixed"), guard.py is
the policy that record justifies ("therefore 1024 MiB floor, 80 °C ceiling, on
every run"). The two must agree, and they do.

## 6. `quilt-gpu-lab/docs/RELATIONAL-CORRELATION-PRIMITIVE.md` — the physicist's theory page

**What it measures:** nothing directly — it distills the D12/D13 arc's
measurements into a claim: the relational primitive is **correlation
detection** (compute the co-variation, read its direction), not reward
accumulation. Then it pre-registers the falsification: D18 sweeps scale
(N ∈ {8, 32, 100, 300}), noise (p_corr ∈ {0.9 … 0.55}), and re-runs the best
RL variant as control, with the deciding numbers written down *before* the
run.

**Which part of the physicist:** the **theory step, done honestly**. A
measurement becomes physics only when it is generalized into a claim that
predicts where it breaks — and the doc does exactly that, naming the regime
("dies *at* the information bound, not before it") in which the principle
would retire. The claim is explicitly conditional on D18.

---

## The through-line

D13d proved that **"correlation, not reward" IS the Ground Truth primitive**:
to know the state of a relational system you do not consult the reward channel
— a noisy scalar *opinion* about the past — you compute the co-variation
between streams and read the direction it points. That is the same verb as
vmf.py fitting (μ̂, κ) to a room's co-moving dials ("which way is this room
leaning, how tightly"), the same verb as field.py's contrast and inversion
dynamics, the same verb D17's compiler exploits in reverse (a receiver with
context decodes the co-variation; a context-free observer can neither read nor
compress it). Around that core, guard.py and SYSTEM.md form the admissibility
envelope — the physical conditions under which any reading counts — and
RESULTS.md supplies the verdict discipline that turns readings into KEEP/KILL.
One verb, one envelope, one ledger.

---

## The claim

**The fleet's Ground Truth agent is now a working physicist of two strata: an
admissibility envelope (SYSTEM.md's verified vessel spec + guard.py's live
VRAM/thermal watchdog) that decides which physical states may be measured at
all, wrapped around a direction-reading estimator stack (elephant's vmf.py
fitting (μ̂, κ, CI) to the room, field.py's dial-state variables with
inversion-estimated dynamics, and D13d's max-|correlation| partner discovery
in the quilt substrate) that answers "what IS the state?" by computing
co-variation and reading where it points — never by asking a reward, and
never faking a number when the data is too thin (κ = None under N < 10,
mis-pairings booked as bugs, KEEP/KILL that follows the measurement). And it
grew from a single-number safety reflex — a crash-looped laptop teaching
itself to watch its own temperature — into exactly the primitive the
Relational-Correlation doc names: the verb D13d cracked at 1.0 ("who moves
with me") is the verb the room-sense already spoke ("what way is this room
leaning"), unified on paper and pointed at D18, the falsifiable scale/noise
test that will say whether the primitive generalizes or honestly retires.**
