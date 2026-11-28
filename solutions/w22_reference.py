"""Reference solution for the streaming drill: resume, and de-duplicate by id.

Four rules, each one covering a way the naive client loses.

**Only complete frames are tokens.** The buffer is split on the blank line, and the last piece is
kept for the next read. A `cut` leaves a half-written frame in that piece and it is thrown away
when the connection ends, which is correct: half a word is not a word.

**A connection ending is not an answer ending.** The only evidence of completion is the `done`
event. If the socket closes without it, the client reconnects, even though it has no idea how
much is missing.

**Resume from the last id accepted, exclusively.** The wire contract is that the server sends
tokens whose id is greater than `resume_from`. Asking for the last id you saw is the off-by-one
that duplicates a token.

**Append by id, not by position.** When the server ignores the resume point — `ignore_resume` in
this corpus — the second delivery repeats everything. `if ident > last` makes the append
idempotent: a replay costs bandwidth and changes nothing.

The result is the exact answer, a correct `complete` flag, and about 1.25x the gold tokens,
because a resumed connection only re-sends what was missing. Restarting from scratch is also
correct and costs 2x, which is what the cost cap is for.
"""

from __future__ import annotations

import json

from drills.w22_stream.data import Stalled

MAX_ATTEMPTS = 4


def _parse(frame: bytes) -> tuple[int | None, str | None, dict]:
    ident = None
    event = None
    payload: dict = {}
    for line in frame.decode("utf-8", "ignore").splitlines():
        if line.startswith("id: "):
            try:
                ident = int(line[4:])
            except ValueError:
                ident = None
        elif line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            try:
                payload = json.loads(line[6:])
            except json.JSONDecodeError:
                payload = {}
    return ident, event, payload


def stream(case, fabric) -> dict:
    accepted: dict[int, str] = {}
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
                        if ident > last:
                            accepted[ident] = payload["v"]
                            last = ident
        except Stalled:
            # The socket is open and silent. The budget is spent either way, so reconnect.
            pass

        if done:
            return {
                "text": " ".join(accepted[index] for index in sorted(accepted)),
                "complete": True,
            }

    return {
        "text": " ".join(accepted[index] for index in sorted(accepted)),
        "complete": False,
    }
