#!/usr/bin/env python3
"""c1_playtest_pong.py — lane C1-PLAYTEST: the local playtester, pong PoC.

Pre-registered h2h: does the pong DERIVED LAW beat the local 7B in >=90% of
matches? (results/c1_playtest/PREREG.md — written before the first match).

The Python driver owns the match loop, the ollama calls and the receipts; a
child `c1_pong_engine.mjs` owns the quilt-arcade engine tick (list-form
subprocess). Energy is booked by guard.py's G7 watt receipt: this script
re-execs itself as the guarded child (`--inner`) so the whole model window is
sampled system-wide.

  python3 experiments/c1_playtest_pong.py            # guarded, full N=40
  python3 experiments/c1_playtest_pong.py --inner --out <dir>   # child

House laws: seed 2718; fail loud; receipt or VOID; do NOT commit.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import guard  # noqa: E402  (the GPU law: preflight/run/emit_receipt)

HERE = Path(__file__).resolve().parent
HARNESS = HERE / "c1_pong_engine.mjs"
DEFAULT_OUT = LAB / "results" / "c1_playtest"

MODEL = "qwen2.5:7b-instruct-q4_K_M"
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
OLLAMA_PS = "http://127.0.0.1:11434/api/ps"

MASTER_SEED = 2718
TEMP = 0.7
N_GAMES = 40
MAX_TICKS = 3000
NUM_CTX = None  # None = server default (4096). OLLAMA_MAX_LOADED_MODELS=1 on
                # this host: a ctx that differs from a concurrent lane forces a
                # full model RELOAD per call (10 s/tick thrash). Aligned to the
                # server default so all lanes share the one resident runner.
NUM_PREDICT = 8
GAMES_JSONL_CAP = 2 * 1024 * 1024  # 2 MB cap on per-tick rows
BUDGET_S = None  # wall-clock budget for the inner loop; None = no limit


# ── deterministic RNG (mulberry32, python port of the engine's) ──────────────
def mulberry32(seed: int):
    a = seed & 0xFFFFFFFF

    def nxt() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        t = t ^ (t >> 14)
        return (t & 0xFFFFFFFF) / 4294967296.0

    return nxt


# ── engine harness child (JSON-lines over stdin/stdout) ──────────────────────
class Engine:
    def __init__(self):
        self.proc = subprocess.Popen(
            ["node", str(HARNESS)],
            cwd=str(LAB), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        hello = self._read()
        if not hello.get("ok"):
            raise RuntimeError(f"harness failed to boot: {hello}")

    def _read(self) -> dict:
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("harness died (no output)")
        return json.loads(line)

    def send(self, msg: dict) -> dict:
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        return self._read()

    def close(self):
        try:
            self.send({"cmd": "quit"})
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


# ── ollama ───────────────────────────────────────────────────────────────────
def ollama_chat(prompt: str, seed: int, timeout: float = 90.0) -> tuple[str, dict]:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": TEMP, "seed": seed,
            "num_predict": NUM_PREDICT, "top_p": 1.0, "stop": ["\n"],
        },
    }).encode()
    req = urllib.request.Request(
        OLLAMA_CHAT, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    meta = {
        "eval_count": d.get("eval_count"),
        "prompt_eval_count": d.get("prompt_eval_count"),
        "total_duration_ms": (d.get("total_duration") or 0) / 1e6,
    }
    return d.get("message", {}).get("content", ""), meta


def ollama_warm() -> tuple[bool, str]:
    """Load the 7B once (retry once after 90 s if another lane holds it)."""
    for attempt in (1, 2):
        try:
            t0 = time.time()
            _txt, meta = ollama_chat("Reply with the single letter S.", 1, timeout=180.0)
            return True, f"warm ok in {time.time() - t0:.1f}s (meta={meta})"
        except Exception as exc:  # noqa: BLE001
            if attempt == 1:
                time.sleep(90.0)
                continue
            return False, f"warm failed twice: {exc}"
    return False, "unreachable"


def parse_action(text: str) -> tuple[str | None, bool, bool]:
    """-> (letter, ok, illegal_first_alpha)."""
    for ch in text.strip():
        c = ch.upper()
        if c in "UDS":
            return c, True, False
        if c.isalpha():
            return c, False, True
    return None, False, False


def build_prompt(st: dict, side: str) -> str:
    py = st["left"] if side == "left" else st["right"]
    my = st["scoreLeft"] if side == "left" else st["scoreRight"]
    op = st["scoreRight"] if side == "left" else st["scoreLeft"]
    speed = 0.85 if side == "left" else 0.70
    goal = "x=0" if side == "left" else "x=100"
    # COMPACT state summary (pre-registered): one line, no chat history.
    return (
        f"Pong. You control the {side.upper()} paddle (y=0 top, y=60 bottom). "
        f"Your paddle centre y={py:.1f}, half-height 6, moves {speed:.2f}/tick. "
        f"Ball x={st['ballX']:.1f} y={st['ballY']:.1f} "
        f"vx={st['ballVx']:.2f} vy={st['ballVy']:.2f}, bounces off top/bottom walls. "
        f"Score you={my} opp={op}. You lose the point if the ball passes {goal}. "
        f"Move? One letter: U=up, D=down, S=stay."
    )


def _probe_state(st: dict, side: str) -> str:
    return "D" if st["ballY"] > (st["left"] if side == "left" else st["right"]) else "U"


# ── one match ────────────────────────────────────────────────────────────────
def run_match(eng: Engine, gi: int, model_side: str, out_rows, row_cap_hit: list) -> dict:
    seed = MASTER_SEED + gi
    newmsg = {"cmd": "new_game", "seed": seed}
    newmsg[model_side] = "model"
    newmsg["left" if model_side == "right" else "right"] = "law"
    r = eng.send(newmsg)
    if not r.get("ok"):
        return {"game_index": gi, "model_side": model_side, "seed": seed,
                "crashed": True, "error": r.get("error"), "law_win": False}

    st = r["state"]
    rng = mulberry32(MASTER_SEED + gi * 1000003)
    ticks = agree = decisions = parse_fail = illegal = ollama_err = engine_err = 0
    law_wins = model_wins = 0
    t0 = time.time()

    while st["tick"] < MAX_TICKS:
        prompt = build_prompt(st, model_side)
        letter = None
        ok = False
        try:
            txt, _meta = ollama_chat(prompt, MASTER_SEED + gi)
        except Exception:  # noqa: BLE001
            txt = ""
            ollama_err += 1
        letter, ok, ill = parse_action(txt)
        if ill:
            illegal += 1
        if not ok:
            parse_fail += 1
            letter = "UDS"[int(rng() * 3)]  # deterministic random fallback (counted)

        law_letter = _probe_state(st, model_side)
        decisions += 1
        if letter == law_letter:
            agree += 1

        mv = {"U": -1, "D": 1, "S": 0}[letter]
        moves = {model_side: mv}
        r = eng.send({"cmd": "step", "moves": moves})
        if not r.get("ok"):
            engine_err += 1
            return {"game_index": gi, "model_side": model_side, "seed": seed,
                    "crashed": True, "error": r.get("error"), "ticks": ticks,
                    "law_win": False, "ollama_errors": ollama_err}

        st = r["state"]
        ticks += 1
        if out_rows is not None and not row_cap_hit[0]:
            out_rows.write(json.dumps({
                "g": gi, "tick": ticks, "side": model_side, "letter": letter,
                "law_letter": law_letter, "ok": ok, "ballY": st["ballY"],
                "paddle": st["left"] if model_side == "left" else st["right"],
                "ballX": st["ballX"], "sL": st["scoreLeft"], "sR": st["scoreRight"],
            }) + "\n")
            if out_rows.tell() > GAMES_JSONL_CAP:
                row_cap_hit[0] = True
        if r.get("over"):
            break

    over = bool(st["phase"] == "over")
    winner = st["winner"]
    law_side = "right" if model_side == "left" else "left"
    if over and winner == law_side:
        law_wins = 1
    elif over and winner == model_side:
        model_wins = 1

    return {
        "game_index": gi, "model_side": model_side, "seed": seed,
        "ollama_seed": MASTER_SEED + gi,
        "ticks": ticks, "closed": over, "draw": (not over),
        "winner": winner, "score_left": st["scoreLeft"], "score_right": st["scoreRight"],
        "law_won": bool(law_wins), "model_won": bool(model_wins), "crashed": False,
        "decisions": decisions, "agree": agree,
        "agreement": round(agree / decisions, 4) if decisions else None,
        "parse_fail": parse_fail, "illegal_first_alpha": illegal,
        "ollama_errors": ollama_err, "engine_errors": engine_err,
        "wall_s": round(time.time() - t0, 2),
    }


# ── inner (guarded) run ──────────────────────────────────────────────────────
def run_inner(out_dir: Path, n_games: int, budget_s: float | None = None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps({
        "model": MODEL, "temperature": TEMP, "num_ctx": NUM_CTX,
        "num_ctx_note": "None = ollama server default (4096); a differing ctx with a "
                         "concurrent lane forces a per-call model reload under "
                         "OLLAMA_MAX_LOADED_MODELS=1 (ops fix, see RESULTS-ENTRY.md)",
        "num_predict": NUM_PREDICT, "master_seed": MASTER_SEED,
        "n_games": n_games, "max_ticks": MAX_TICKS,
        "seed_policy": "engine seed = 2718+i ; ollama seed = 2718+i",
        "substituted_cell": "ai.track (control switch law|model; movement budget identical)",
        "harness": str(HARNESS),
    }, indent=2))

    ok, msg = ollama_warm()
    print(f"[warm] {msg}", flush=True)
    if not ok:
        (out_dir / "match_summary.json").write_text(json.dumps(
            {"status": "NOT-RUN", "reason": msg}, indent=2))
        return 3

    eng = Engine()
    rows = open(out_dir / "games.jsonl", "w")
    cap_hit = [False]
    matches = []
    t_start = time.time()
    try:
        for gi in range(n_games):
            if budget_s and (time.time() - t_start) > budget_s:
                print(f"[budget] wall-clock budget {budget_s}s reached after {len(matches)}"
                      f" games — halting gracefully (status PARTIAL)", flush=True)
                break
            side = "right" if gi < n_games // 2 else "left"
            m = run_match(eng, gi, side, rows, cap_hit)
            matches.append(m)
            print(f"[g{gi:02d}] {m['model_side']:5s} ticks={m.get('ticks')} "
                  f"closed={m.get('closed')} winner={m.get('winner')} "
                  f"agree={m.get('agreement')} draw={m.get('draw')} "
                  f"crashed={m.get('crashed')} {m.get('wall_s')}s", flush=True)
    finally:
        rows.close()
        eng.close()

    law_wins = sum(1 for m in matches if m.get("law_won"))
    draws = sum(1 for m in matches if m.get("draw"))
    crashes = sum(1 for m in matches if m.get("crashed"))
    decisions = sum(m.get("decisions", 0) for m in matches)
    agree = sum(m.get("agree", 0) for m in matches)
    pf = sum(m.get("parse_fail", 0) for m in matches)
    ill = sum(m.get("illegal_first_alpha", 0) for m in matches)
    oe = sum(m.get("ollama_errors", 0) for m in matches)
    ee = sum(m.get("engine_errors", 0) for m in matches)
    rate = law_wins / len(matches) if matches else None
    complete = len(matches) == n_games and not any(m.get("crashed") for m in matches)

    summary = {
        "status": "RUN" if complete else "PARTIAL",
        "status_note": ("complete pre-registered run" if complete else
                        f"INCOMPLETE: {len(matches)}/{n_games} games completed within the "
                        "wall-clock window; the >=90% gate is NOT adjudicated on a partial "
                        "sample (reported as directional only)"),
        "claim": "derived law beats the local 7B at pong in >=90% of h2h matches",
        "gate": "KILLED iff law_win_rate < 0.90 (over the pre-registered N=40)",
        "n_games": len(matches), "n_games_prereg": n_games,
        "elapsed_s": round(time.time() - t_start, 1), "budget_s": budget_s,
        "games": matches,
        "law_wins": law_wins, "draws": draws, "model_wins": len(matches) - law_wins - draws,
        "law_win_rate": round(rate, 4) if rate is not None else None,
        "gate_outcome": ("NOT-ADJUDICATED-PARTIAL" if not complete else
                         ("CLAIM-KILLED" if (rate is not None and rate < 0.90)
                          else "CLAIM-SURVIVES")),
        "agreement_rate": round(agree / decisions, 4) if decisions else None,
        "decisions": decisions, "agree": agree,
        "parse_fail": pf, "parse_fail_rate": round(pf / decisions, 4) if decisions else None,
        "illegal_first_alpha": ill,
        "ollama_errors": oe, "engine_errors": ee,
        "crashes": crashes,
        "games_jsonl_capped": cap_hit[0],
        "games_jsonl_cap_bytes": GAMES_JSONL_CAP,
        "games_jsonl_bytes": (out_dir / "games.jsonl").stat().st_size,
    }
    (out_dir / "match_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in (
        "law_win_rate", "gate_outcome", "agreement_rate", "crashes",
        "parse_fail", "draws")}, indent=1), flush=True)
    return 0


# ── outer (guarded) run ──────────────────────────────────────────────────────
def run_outer(out_dir: Path, n_games: int, budget_s: float | None = None) -> int:
    g = guard.Guard(timeout_s=10800.0, task_id="C1-playtest-pong",
                    agent="quilt-gpu-lab keeper (Lucineer, main Super Z)",
                    seed=str(MASTER_SEED),
                    receipt_dir=str(out_dir / "guard"))
    if not g.preflight():
        print(f"PREFLIGHT REFUSED: {g.breach}", flush=True)
        g.emit_receipt(verdict="VOID", void_reason=f"preflight refused: {g.breach}")
        return 2

    cmd = [sys.executable, str(Path(__file__).resolve()),
           "--inner", "--out", str(out_dir), "--games", str(n_games)]
    if budget_s:
        cmd += ["--budget-s", str(budget_s)]
    rc, out, err = g.run(cmd, cwd=str(LAB), env=dict(os.environ))
    print(f"inner rc={rc}", flush=True)
    print(out[-2000:], flush=True)
    if err.strip():
        print("stderr tail:", err[-800:], flush=True)

    if rc == 0:
        rpath, receipt = g.emit_receipt()
        ok, msgv = g.validate_receipt(rpath)
        print(f"guard MEASURED receipt: {rpath} valid={ok} {msgv}", flush=True)
        e = (receipt or {}).get("energy", {})
        print(f"ENERGY: {e.get('wh') if 'wh' in e else e.get('watt_hours')} Wh "
              f"({e.get('joules')} J); gate={(receipt or {}).get('gate')}", flush=True)
        return 0
    g.emit_receipt(verdict="VOID", void_reason=f"inner rc={rc}")
    print("VOID receipt sealed for failed run", flush=True)
    return 2


def main() -> int:
    args = sys.argv[1:]
    inner = "--inner" in args
    out_dir = DEFAULT_OUT
    if "--out" in args:
        out_dir = Path(args[args.index("--out") + 1])
    n_games = N_GAMES
    if "--games" in args:
        n_games = int(args[args.index("--games") + 1])
    budget = float(args[args.index("--budget-s") + 1]) if "--budget-s" in args else BUDGET_S
    if inner:
        return run_inner(out_dir, n_games, budget)
    return run_outer(out_dir, n_games, budget)


if __name__ == "__main__":
    sys.exit(main())
