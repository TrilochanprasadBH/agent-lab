"""Drill 22 — Streaming and disconnects.

Goal
    Turn a stream of server-sent events into the exact answer, know whether it is
    complete, and survive a socket that dies at the worst moment.

Return
    {"text": the answer, "complete": whether the stream ended with its terminator}

Run
    python3 run.py --drill w22_stream

Starting point
    Read until the socket closes, keep every complete frame, and retry once from
    scratch if the socket goes quiet. It is what most first clients do: it
    treats the end of the socket as the end of the answer, and it never asks the
    server to resume.

Full brief
    drills/w22_stream/spec.md
"""

from __future__ import annotations

import json

from .data import Stalled


def _tokens(buffer: bytes) -> list[str]:
    tokens = []
    for frame in buffer.split(b"\n\n")[:-1]:
        for line in frame.decode("utf-8", "ignore").splitlines():
            if line.startswith("data: "):
                try:
                    payload = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if "v" in payload:
                    tokens.append(payload["v"])
    return tokens


def stream(case, fabric) -> dict:
    tokens: list[str] = []
    for _ in range(2):
        buffer = b""
        tokens = []
        try:
            session = fabric.connect(case.id)
            while True:
                chunk = session.read()
                if not chunk:
                    break
                buffer += chunk
            tokens = _tokens(buffer)
            break
        except Stalled:
            continue
    return {"text": " ".join(tokens), "complete": bool(tokens)}
