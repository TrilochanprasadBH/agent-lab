#!/usr/bin/env python3
"""Compare four ways to consume a stream that breaks.

    python3 drills/w22_stream/sweep.py

  read to eof        stop when the socket closes, never resume            the baseline
  restart until done  notice the missing terminator, reconnect from zero   correct, expensive
  resume blind       resume, append everything that arrives               fast, duplicates
  resume by id       resume, append only ids past the last accepted       the reference

Every number in `spec.md` comes from here. The lesson is in the third row: it recovers every
stream and still fails on text, because the two faults where the server replays tokens turn a
working answer into a doubled one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentlab.drill import run_drill  # noqa: E402

from drills.w22_stream import data  # noqa: E402
from drills.w22_stream.data import Stalled  # noqa: E402
from drills.w22_stream.drill import score  # noqa: E402
from solutions.w22_reference import _parse, stream as resume_by_id  # noqa: E402

MAX_ATTEMPTS = 4


def read_to_eof(case, fabric):
    from drills.w22_stream.task import stream as baseline

    return baseline(case, fabric)


def restart_until_done(case, fabric):
    tokens: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        tokens = []
        buffer = b""
        done = False
        try:
            session = fabric.connect(case.id)
            while True:
                chunk = session.read()
                if not chunk:
                    break
                buffer += chunk
                *frames, buffer = buffer.split(b"\n\n")
                for frame in frames:
                    _, event, payload = _parse(frame)
                    if event == "done":
                        done = True
                    elif event == "token" and "v" in payload:
                        tokens.append(payload["v"])
        except Stalled:
            pass
        if done:
            return {"text": " ".join(tokens), "complete": True}
    return {"text": " ".join(tokens), "complete": False}


def resume_blind(case, fabric):
    pieces: list[str] = []
    last = 0
    for _ in range(MAX_ATTEMPTS):
        buffer = b""
        done = False
        try:
            session = fabric.connect(case.id, resume_from=last)
            while True:
                chunk = session.read()
                if not chunk:
                    break
                buffer += chunk
                *frames, buffer = buffer.split(b"\n\n")
                for frame in frames:
                    ident, event, payload = _parse(frame)
                    if event == "done":
                        done = True
                    elif event == "token" and ident is not None and "v" in payload:
                        pieces.append(payload["v"])
                        last = ident
        except Stalled:
            pass
        if done:
            return {"text": " ".join(pieces), "complete": True}
    return {"text": " ".join(pieces), "complete": False}


CLIENTS = (
    ("read to eof", read_to_eof),
    ("restart until done", restart_until_done),
    ("resume blind", resume_blind),
    ("resume by id", resume_by_id),
)


def evaluate(client):
    cases = data.build()
    fabric = data.fabric(cases)
    results = run_drill(cases, client, fabric)
    return score(results, fabric, 0.95, 1.0), fabric, cases


def main() -> int:
    cases = data.build()
    gold_tokens = sum(len(case.tokens) for case in cases)
    print()
    print(
        f" {len(cases)} streams, {gold_tokens} gold tokens, "
        f"{len(data.FAULTS)} fault types, {data.CASES_PER_FAULT} each"
    )
    print()
    print(
        f" {'client':<20}{'exact':>7}{'complete':>10}{'both':>7}"
        f"{'conn':>6}{'tokens':>8}{'cost':>9}  notes"
    )
    notes = {
        "read to eof": "stops at the socket, so 25 streams are truncated",
        "restart until done": "correct, but every recovery re-sends the answer",
        "resume blind": "recovers everything and doubles 10 answers",
        "resume by id": "",
    }
    for name, client in CLIENTS:
        card, fabric, _ = evaluate(client)
        served = sum(stat["tokens"] for stat in fabric.stats.values())
        print(
            f" {name:<20}{card.per_field['exact text']:>7.1%}"
            f"{card.per_field['marked complete']:>10.1%}{card.accuracy:>7.1%}"
            f"{fabric.n_calls / len(cases):>6.2f}{served / gold_tokens:>7.2f}x"
            f"${fabric.cost_usd:>8.5f}  {notes[name]}"
        )
    print()
    print(" exact is the text; complete is the terminator flag; both is the score.")
    print(" tokens is everything the server sent, including replays, over the gold token count.")
    print()

    print(" where each client fails")
    print()
    header = f" {'client':<20}" + "".join(f"{fault[:9]:>10}" for fault in data.FAULTS)
    print(header)
    for name, client in CLIENTS:
        card, _, _ = evaluate(client)
        row = "".join(f"{card.per_field[fault.replace('_', ' ')]:>10.0%}" for fault in data.FAULTS)
        print(f" {name:<20}{row}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
