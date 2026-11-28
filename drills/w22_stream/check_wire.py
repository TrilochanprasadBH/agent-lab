#!/usr/bin/env python3
"""Check the wire, not a set of labels.

    python3 drills/w22_stream/check_wire.py

The corpus is generated, so what needs checking is that each fault produces the bytes it claims
and that the reference client recovers from all of them:

1. every case's gold is exactly its token list joined with spaces
2. `cut` and its variants end inside a frame, with no terminator
3. `eof` ends at a frame boundary, with no terminator, and is short
4. `stall` delivers bytes, then raises `Stalled` instead of returning end-of-stream
5. `cut_twice` dies again on the first reconnect
6. `resume_duplicates` replays the boundary token on reconnect
7. `ignore_resume` starts the second connection at token 1
8. a connection with no fault delivers every token and the `done` frame
9. the reference client returns the exact gold text for all 30 cases
10. resuming is cheaper than restarting, and the cap separates them
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w22_stream import data  # noqa: E402
from drills.w22_stream.data import Stalled, build, fabric  # noqa: E402
from solutions.w22_reference import stream as reference  # noqa: E402


def read_all(session) -> tuple[bytes, bool]:
    """(bytes, stalled)."""
    raw = b""
    try:
        while True:
            chunk = session.read()
            if not chunk:
                break
            raw += chunk
    except Stalled:
        return raw, True
    return raw, False


def main() -> int:
    cases = build()
    problems: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    for case in cases:
        check(case.gold == " ".join(case.tokens), f"{case.id}: gold is not the joined tokens")
        check(0 < case.cut_at < len(case.tokens), f"{case.id}: cut point outside the answer")
        check(
            case.fault != "cut_twice" or case.second_cut_at > case.cut_at,
            f"{case.id}: the second cut is not after the first",
        )

        server = fabric([case])
        raw, stalled = read_all(server.connect(case.id))
        check(not raw.endswith(b"\n\n") or case.fault in ("eof", "stall"), f"{case.id}: cut shape")
        check(b"event: done" not in raw, f"{case.id}: the first connection terminated cleanly")

        if case.fault in ("cut", "cut_twice", "resume_duplicates", "ignore_resume"):
            check(
                not raw.endswith(b"\n\n"),
                f"{case.id}: a cut must end inside a frame",
            )
        if case.fault == "eof":
            check(raw.endswith(b"\n\n"), f"{case.id}: an eof must end on a frame boundary")
        if case.fault == "stall":
            check(stalled, f"{case.id}: a stall must raise instead of returning end-of-stream")
        else:
            check(not stalled, f"{case.id}: only a stall fault may raise")

        if case.fault == "cut_twice":
            second, _ = read_all(server.connect(case.id, resume_from=case.cut_at))
            check(not second.endswith(b"event: done"), f"{case.id}: the second cut did not happen")
            check(b"event: done" not in second, f"{case.id}: the second connection completed")

        if case.fault == "resume_duplicates":
            payload, _ = read_all(server.connect(case.id, resume_from=case.cut_at))
            first_id = payload.split(b"\n", 1)[0]
            check(
                first_id == f"id: {case.cut_at}".encode(),
                f"{case.id}: the replay does not begin with the boundary token",
            )

        if case.fault == "ignore_resume":
            payload, _ = read_all(server.connect(case.id, resume_from=case.cut_at))
            check(
                payload.startswith(b"id: 1\n"),
                f"{case.id}: ignore_resume did not restart at token 1",
            )

        # A fresh client on the same case, after the faulted attempts, gets a clean stream.
        clean_server = fabric([case])
        clean_server.stats[case.id]["connections"] = 2 if case.fault == "cut_twice" else 1
        clean, _ = read_all(clean_server.connect(case.id, resume_from=case.cut_at))
        check(b"event: done" in clean, f"{case.id}: a clean connection has no terminator")
        check(
            clean.endswith(b"\n\n"),
            f"{case.id}: a clean connection does not end on a frame boundary",
        )

    # The reference recovers every case, exactly.
    server = fabric(cases)
    for case in cases:
        result = reference(case, server)
        check(result["text"] == case.gold, f"{case.id}: the reference text is not exact")
        check(result["complete"] is True, f"{case.id}: the reference did not mark completion")

    gold_tokens = sum(len(case.tokens) for case in cases)
    resume_cost = server.cost_usd
    restart_tokens = 2 * gold_tokens
    restart_cost = restart_tokens * data.TOKEN_COST + 2 * len(cases) * data.CONNECT_COST
    cap = 0.0026
    check(
        resume_cost < cap < restart_cost,
        f"the cap {cap} does not separate resume (${resume_cost:.5f}) from "
        f"restart (${restart_cost:.5f})",
    )

    if problems:
        print(f" {len(problems)} problem(s)")
        for problem in problems:
            print(f" - {problem}")
        return 1

    print(f" ok: {len(cases)} streams, {gold_tokens} gold tokens, {len(data.FAULTS)} fault types")
    print(
        f" reference: exact text on all {len(cases)}, {server.n_calls} connections, "
        f"${resume_cost:.5f}"
    )
    print(
        f" cap ${cap:.4f} sits between resume (${resume_cost:.5f}) and "
        f"restart (${restart_cost:.5f}, {restart_tokens / gold_tokens:.2f}x the tokens)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
