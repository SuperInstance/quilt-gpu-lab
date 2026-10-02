"""look_again — the Look-Again meta-policy as a standalone block.

Harvested provenance (read-only sources; full citations in BLOCK.md):
  - experiments/d1b_lookagain_sweep.py  (RESULTS.md "D1b SMOKE" 2026-09-28 and
    "D1b FULL-SCALE" 2026-09-27 21:54, verdict KEEP, seed 2718)
  - experiments/d1_look_again_scale.py  (D1 origin, KEEP 2026-09-27 15:07 AKDT)

The ported mechanic, faithful to the source's `look_again_pred`
(experiments/d1b_lookagain_sweep.py:350-357):
  1. A first pass runs the base pool on every item.
  2. The TRIGGER fires where the second scorer HAS REACH — its witness is a
     non-abstain (+1/-1). That is D1b's actual rule
     (`has_reach = reach_witness != 0`), not a margin threshold.
  3. The POLICY is OVERRIDE: the second look's call replaces the base call
     exactly on fired items (`np.where(has_reach, pred(reach_witness), base)`).
  4. Witness semantics are the source's: +1 supported / -1 refuted /
     0 abstain (cannot reach). `pred(w) = 1 iff w > 0`, so abstain and
     refute both read "not supported" (the source's conservative convention).

House contracts baked in:
  - seed 2718 is the default everywhere.
  - Trigger and combination policy are FROZEN PARAMETER OBJECTS (frozen
    dataclasses with hashable data fields), validated at construction —
    never lambdas, never rules discovered mid-run.
  - The ORACLE arm is a label-peeked BOUND (the second look is placed exactly
    where it would change the answer). It refuses loudly without labels and
    every receipt marks it `is_bound: true, achievable: false`.
  - Source honesty rule: best-single selection happens on the calibration
    prefix ONLY; every reported accuracy is scored on the held-out eval
    suffix. The caller shuffles (seeded) before run().
  - std == 0 across seeded repeats => verdict INCONCLUSIVE (see __main__).
  - This block spawns no subprocesses. Any Scorer that does must use
    list-form argv and never shell=True, and must never print/copy secrets.

CPU-only. numpy 2.4.6 + stdlib; imports nothing from the lab (zero setup).
Self-test: `python3 blocks/look_again/block.py` -> final stdout line is
exactly one JSON object {"verdict": "PASS"}; exit 0 iff PASS; <10 s.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, is_dataclass

import numpy as np

SEED = 2718

WITNESS_DOMAIN = (-1, 0, 1)


def pred(witness) -> np.ndarray:
    """Witness in {-1,0,+1} -> a binary supported/not-supported call
    (elementwise). Abstain (0) and refute (-1) both read not-supported —
    conservative, matching D1's convention in the source."""
    return (np.asarray(witness) > 0).astype(np.int64)


class Scorer:
    """Base class: a named, cost-tiered witness scorer.

    __call__(item) -> int in {-1, 0, +1}:
      +1  the scorer's evidence supports the item's claim
      -1  the scorer's evidence refutes it
       0  abstain / cannot reach (the honest reach limit — D1b's symbolic
          reader abstains outside its grammar, and the trigger relies on it)
    `.cost` is a free-form tier label (e.g. "cheap" / "strong"); the receipt
    carries it so the second_look_rate can be priced per tier downstream.
    """

    name: str = "scorer"
    cost: str = "cheap"

    def __call__(self, item):  # pragma: no cover - interface
        raise NotImplementedError


_TRIGGER_REGISTRY = ("strong_reach", "cheap_abstain")


@dataclass(frozen=True)
class TriggerRule:
    """Frozen, named trigger spec. `params` is a tuple of (key, value) pairs
    and must be hashable DATA — that is what "frozen before evaluation"
    means: the rule is data, not a lambda."""

    name: str
    params: tuple = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or self.name not in _TRIGGER_REGISTRY:
            raise ValueError(
                f"unknown trigger rule {self.name!r}; supported: {list(_TRIGGER_REGISTRY)}"
            )
        for kv in self.params:
            if not (isinstance(kv, tuple) and len(kv) == 2 and isinstance(kv[0], str)):
                raise ValueError(f"params must be (key, value) pairs with string keys, got {kv!r}")
        hash(self)  # fields must be hashable data — refuses functions/lists/dicts

    def fires(self, strong_w: int, cheap_w: int) -> bool:
        if self.name == "strong_reach":
            # D1b's actual rule: the second scorer has evidence (non-abstain).
            return strong_w != 0
        if self.name == "cheap_abstain":
            # The first pass is uncertain (abstained) — the same family as a
            # low-margin rule, for generic scorer pairs whose cheap tier can
            # abstain. The source corpus's dense pool never abstains, so the
            # source run itself fired only on strong_reach.
            return cheap_w == 0
        raise AssertionError(f"unreachable: trigger {self.name!r} escaped __post_init__")


_POLICY_REGISTRY = ("override",)


@dataclass(frozen=True)
class CombinePolicy:
    """Frozen, named combination spec."""

    name: str = "override"
    params: tuple = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or self.name not in _POLICY_REGISTRY:
            raise ValueError(
                f"unknown combine policy {self.name!r}; supported: {list(_POLICY_REGISTRY)}"
            )
        hash(self)

    def combine(self, fired: np.ndarray, cheap_pred: np.ndarray,
                strong_pred: np.ndarray) -> np.ndarray:
        """The source's policy: trust the base call everywhere, EXCEPT on
        fired items, where the second look's call overrides it."""
        fired = np.asarray(fired, dtype=bool)
        return np.where(fired, strong_pred, cheap_pred).astype(np.int64)


def _check_frozen_spec(obj, kind: str) -> None:
    params = getattr(obj, "__dataclass_params__", None)
    if not (is_dataclass(obj) and params is not None and params.frozen):
        raise TypeError(
            f"{kind} must be a frozen dataclass spec, frozen before evaluation; got "
            f"{type(obj).__name__}. Lambdas or rules discovered mid-run are not allowed."
        )
    try:
        hash(obj)
    except TypeError as exc:
        raise TypeError(
            f"{kind} fields must be hashable data (no functions, lists, or dicts): {exc}"
        )


def _check_scorer(sc, role: str) -> None:
    if not callable(sc):
        raise TypeError(f"{role} scorer must be callable, got {type(sc).__name__}")
    for attr in ("name", "cost"):
        if not isinstance(getattr(sc, attr, None), str):
            raise TypeError(f"{role} scorer must carry a string .{attr} label")


def _checked_witness(w, scorer_name: str, item_id) -> int:
    if isinstance(w, bool) or not isinstance(w, (int, np.integer)):
        raise ValueError(
            f"scorer {scorer_name!r} returned a non-integer witness {w!r} on item {item_id}"
        )
    w = int(w)
    if w not in WITNESS_DOMAIN:
        raise ValueError(
            f"scorer {scorer_name!r} returned witness {w} on item {item_id}; "
            f"domain is {-1, 0, +1}"
        )
    return w


def _resolve_labels(items, labels, include_oracle: bool) -> np.ndarray:
    if labels is None:
        try:
            labels = [it["gold"] for it in items]
        except (KeyError, TypeError, IndexError):
            who = ("the ORACLE arm is a label-peeked bound and it" if include_oracle
                   else "accuracy")
            raise ValueError(
                f"labels required: {who} refuses to run without gold labels "
                "(pass labels= or give every item a 'gold' field in {0,1})"
            )
    arr = np.asarray(labels, dtype=np.int64).ravel()
    if arr.shape[0] != len(items):
        raise ValueError(f"labels length {arr.shape[0]} != n_items {len(items)}")
    bad = ~np.isin(arr, (0, 1))
    if bad.any():
        raise ValueError(f"labels must be binary 0/1, got {sorted(set(arr[bad].tolist()))}")
    return arr


class LookAgain:
    """Look-Again meta-policy: a first pass with the cheap pool on every
    item; items flagged by the frozen trigger get a second look from the
    strong scorer; the frozen combination policy makes the final call.

    Arms reported per run (mirroring the D1b sweep):
      BEST_SINGLE — strongest base member alone, SELECTED on the calibration
                    prefix, SCORED on the eval suffix (second_look_rate 0).
      LOOK_AGAIN  — the meta-policy (the accuracy + spend headline).
      ORACLE      — label-peeked upper bound: the second look placed exactly
                    where it would change the answer. Requires labels;
                    marked is_bound/achievable=false in the receipt.
    """

    def __init__(self, cheap, strong, trigger: TriggerRule, policy: CombinePolicy):
        pool = [cheap] if isinstance(cheap, Scorer) else list(cheap)
        if not pool:
            raise ValueError("cheap scorer pool is empty")
        for sc in pool:
            _check_scorer(sc, "cheap-pool")
        _check_scorer(strong, "strong")
        _check_frozen_spec(trigger, "trigger rule")
        _check_frozen_spec(policy, "combine policy")
        self.cheap_pool = pool
        self.strong = strong
        self.trigger = trigger
        self.policy = policy

    def run(self, items, labels=None, calib_frac: float = 0.25,
            include_oracle: bool = True, seed: int = SEED) -> dict:
        items = list(items)
        if not items:
            raise ValueError("items is empty")
        n = len(items)
        n_calib = max(8, int(round(n * calib_frac)))
        if n_calib >= n:
            raise ValueError(f"calib_frac={calib_frac} leaves no eval items at n={n}")
        gold = _resolve_labels(items, labels, include_oracle)
        ids = [it.get("id", i) if isinstance(it, dict) else i for i, it in enumerate(items)]

        # First pass: the cheap pool on every item; the strong scorer's
        # witness is computed for the record — the receipt's second_look_rate
        # is the share of items the policy would actually spend it on.
        cheap_w = np.array([
            [_checked_witness(sc(it), sc.name, ids[i]) for i, it in enumerate(items)]
            for sc in self.cheap_pool
        ], dtype=np.int64)
        strong_w = np.array([
            _checked_witness(self.strong(it), self.strong.name, ids[i])
            for i, it in enumerate(items)
        ], dtype=np.int64)

        calib = np.arange(n) < n_calib
        ev = ~calib
        ev_pos = np.where(ev)[0]
        gold_ev = gold[ev]

        # BEST_SINGLE: best calibration accuracy among the cheap pool,
        # scored on eval only (the source's honesty rule).
        calib_accs = [
            float((pred(cheap_w[j][calib]) == gold[calib]).mean())
            for j in range(len(self.cheap_pool))
        ]
        best_j = int(np.argmax(calib_accs))
        base_ev = pred(cheap_w[best_j][ev])
        bs_acc = float((base_ev == gold_ev).mean())

        # LOOK_AGAIN: trigger fires -> second look; policy combines.
        fired = np.array([
            bool(self.trigger.fires(int(strong_w[i]), int(cheap_w[best_j][i])))
            for i in ev_pos
        ])
        la_ev = self.policy.combine(fired, base_ev, pred(strong_w[ev]))
        la_acc = float((la_ev == gold_ev).mean())
        la_rate = float(fired.mean())

        receipt = {
            "arm_set": ["BEST_SINGLE", "LOOK_AGAIN"] + (["ORACLE"] if include_oracle else []),
            "seed": int(seed),
            "n_items": n,
            "n_calib": int(n_calib),
            "n_eval": int(n - n_calib),
            "split_rule": ("calibration prefix [0:n_calib), eval suffix; caller shuffles "
                           "(seeded) before run; selection on calib ONLY, accuracy on eval ONLY"),
            "cheap_pool": [{"name": sc.name, "cost": sc.cost} for sc in self.cheap_pool],
            "strong": {"name": self.strong.name, "cost": self.strong.cost},
            "best_single": {
                "scorer": self.cheap_pool[best_j].name,
                "calib_acc": calib_accs[best_j],
                "accuracy": bs_acc,
                "second_look_rate": 0.0,
            },
            "look_again": {"accuracy": la_acc, "second_look_rate": la_rate},
            "trigger_spec": {"name": self.trigger.name,
                             "params": {k: v for k, v in self.trigger.params}},
            "policy_spec": {"name": self.policy.name,
                            "params": {k: v for k, v in self.policy.params}},
        }

        if include_oracle:
            # ORACLE: label-peeked ceiling over second-look placements — use
            # the strong call exactly where it disagrees with the base AND is
            # right. A look can only be placed where the strong scorer has
            # reach (an abstain is not a look), and the base call is kept
            # everywhere else. Never achievable.
            strong_ev = pred(strong_w[ev])
            flip = (strong_w[ev] != 0) & (strong_ev != base_ev) & (strong_ev == gold_ev)
            or_ev = np.where(flip, strong_ev, base_ev)
            receipt["oracle"] = {
                "accuracy": float((or_ev == gold_ev).mean()),
                "second_look_rate": float(flip.mean()),
                "is_bound": True,
                "achievable": False,
                "note": ("label-peeked ceiling for ANY second-look placement (looks only "
                         "where the strong scorer has reach); computed from gold, never "
                         "an achievable arm"),
            }

        json.dumps(receipt)  # receipts must be JSON-safe by construction
        return receipt


# ============================================================ synthetic world
class _DenseLikeScorer(Scorer):
    """Cheap-tier stand-in for the source's dense pool: accurate on the easy
    majority, near chance on the hard minority. Deterministic per
    (scorer seed, item id)."""

    def __init__(self, name: str, seed: int, easy_slip: float = 0.10,
                 hard_hit: float = 0.55):
        self.name = name
        self.seed = seed
        self.cost = "cheap"
        self.easy_slip = easy_slip
        self.hard_hit = hard_hit

    def __call__(self, item) -> int:
        r = np.random.default_rng((self.seed, int(item["id"])))
        if item["kind"] == "easy":
            belief = item["gold"] if r.random() >= self.easy_slip else 1 - item["gold"]
        else:
            belief = item["gold"] if r.random() < self.hard_hit else 1 - item["gold"]
        return 1 if belief == 1 else -1


class _StrongReachScorer(Scorer):
    """Strong-tier stand-in for the counting-address reader: abstains outside
    its grammar (easy items; hard items whose format it cannot parse), and is
    near-perfect where it has reach."""

    def __init__(self, name: str, seed: int, hit: float = 0.90):
        self.name = name
        self.seed = seed
        self.cost = "strong"
        self.hit = hit

    def __call__(self, item) -> int:
        if item["kind"] != "hard" or not item["reachable"]:
            return 0
        r = np.random.default_rng((self.seed, int(item["id"])))
        belief = item["gold"] if r.random() < self.hit else 1 - item["gold"]
        return 1 if belief == 1 else -1


def draw_corpus(rng: np.random.Generator, n: int = 480, frac_hard: float = 0.20,
                reach_prob: float = 0.70) -> list:
    """Synthetic corpus where second looks genuinely help: 80% easy items the
    cheap pool binds well; 20% hard items it does not; the strong scorer
    reaches 70% of the hard items and is near-perfect there, abstaining
    honestly on everything else (so the trigger fires on ~14% of items, the
    cost claim). Shuffled with the caller's rng (the split rule)."""
    items = []
    for i in range(n):
        hard = bool(rng.random() < frac_hard)
        items.append({
            "id": i,
            "kind": "hard" if hard else "easy",
            "gold": int(rng.random() < 0.5),
            "reachable": bool(rng.random() < reach_prob) if hard else False,
        })
    rng.shuffle(items)
    return items


def _build_engine() -> LookAgain:
    return LookAgain(
        cheap=[_DenseLikeScorer("dense_a", seed=101),
               _DenseLikeScorer("dense_b", seed=202)],
        strong=_StrongReachScorer("symbolic_counting", seed=303),
        trigger=TriggerRule("strong_reach"),
        policy=CombinePolicy("override"),
    )


def _fail_loud_probes() -> list:
    """The block must refuse loudly, not degrade gracefully. Each probe
    returns a problem string iff the refusal did NOT happen as contracted."""
    problems = []
    items = draw_corpus(np.random.default_rng(1), n=64)

    # 1. ORACLE arm without labels -> loud refusal naming the bound.
    try:
        _build_engine().run([{k: v for k, v in it.items() if k != "gold"} for it in items])
        problems.append("oracle-without-labels did not refuse")
    except ValueError as exc:
        if "label" not in str(exc).lower():
            problems.append(f"oracle-without-labels raised wrong error: {exc}")

    # 2. A lambda trigger (a rule that is not a frozen parameter object).
    try:
        LookAgain(cheap=_DenseLikeScorer("d", 1), strong=_StrongReachScorer("s", 2),
                  trigger=lambda strong_w, cheap_w: True,
                  policy=CombinePolicy("override"))
        problems.append("lambda trigger accepted")
    except TypeError:
        pass

    # 3. An unknown trigger name must fail at construction, not mid-run.
    try:
        TriggerRule("margin_below_tau_discovered_mid_run")
        problems.append("unknown trigger name accepted")
    except ValueError:
        pass

    # 4. A witness outside {-1,0,+1} must fail loudly, naming scorer + item.
    class _BadScorer(Scorer):
        name = "bad"
        cost = "strong"

        def __call__(self, item):
            return 2

    try:
        LookAgain(cheap=_DenseLikeScorer("d", 1), strong=_BadScorer(),
                  trigger=TriggerRule("strong_reach"),
                  policy=CombinePolicy("override")).run(items)
        problems.append("out-of-domain witness accepted")
    except ValueError as exc:
        if "'bad'" not in str(exc):
            problems.append(f"witness probe raised wrong error: {exc}")

    # 5. Label/count mismatch.
    try:
        _build_engine().run(items, labels=[0, 1])
        problems.append("label-length mismatch accepted")
    except ValueError:
        pass

    return problems


def self_test() -> int:
    """Run the toy arms across >=5 seeded corpus draws (house contract:
    ordering on the MEAN, and std==0 across repeats => INCONCLUSIVE)."""
    n_draws = 6
    child_seeds = np.random.SeedSequence(SEED).spawn(n_draws)
    arms = ("best_single", "look_again", "oracle")
    accs = {a: [] for a in arms}
    la_rates = []
    spec_seen = None
    oracle_flags = None

    for cs in child_seeds:
        rng = np.random.default_rng(cs)
        items = draw_corpus(rng)
        receipt = _build_engine().run(items, seed=SEED)
        json.dumps(receipt)  # JSON-safe by construction — prove it per draw
        for a in arms:
            accs[a].append(receipt[a]["accuracy"])
        la_rates.append(receipt["look_again"]["second_look_rate"])
        spec_seen = (receipt["trigger_spec"], receipt["policy_spec"])
        oracle_flags = (receipt["oracle"]["is_bound"], receipt["oracle"]["achievable"])

    means = {a: float(np.mean(accs[a])) for a in arms}
    spreads = {a: float(np.std(accs[a], ddof=1)) for a in arms}
    mean_rate = float(np.mean(la_rates))

    problems = []
    if any((not np.isfinite(spreads[a])) or spreads[a] == 0.0 for a in arms):
        # Zero spread means the toy is deterministic across repeats — the
        # ordering would be unfalsifiable, so the verdict is INCONCLUSIVE.
        verdict = "INCONCLUSIVE"
        problems.append(f"zero/nonfinite spread across {n_draws} seeded draws: {spreads}")
    else:
        if not (means["oracle"] > means["look_again"] > means["best_single"]):
            problems.append(
                "mean ordering violated: require oracle > look_again > best_single, got "
                + ", ".join(f"{a}={means[a]:.4f}" for a in arms)
            )
        if not (0.0 < mean_rate <= 0.5):
            problems.append(
                f"look_again second-look rate {mean_rate:.4f} not in (0, 0.5] "
                "(must be meaningfully below 100%)"
            )
        if spec_seen != ({"name": "strong_reach", "params": {}},
                         {"name": "override", "params": {}}):
            problems.append(f"receipt does not carry the frozen specs: {spec_seen}")
        if oracle_flags != (True, False):
            problems.append(f"oracle arm not marked as a bound: {oracle_flags}")
        problems.extend(_fail_loud_probes())
        verdict = "PASS" if not problems else "FAIL"

    diag = {
        "n_draws": n_draws,
        "seed": SEED,
        "mean_accuracy": means,
        "spread_std_ddof1": spreads,
        "look_again_second_look_rate_mean": mean_rate,
        "checks": problems or "all checks passed",
    }
    print(json.dumps(diag, indent=2), file=sys.stderr)
    print(json.dumps({"verdict": verdict}))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(self_test())
