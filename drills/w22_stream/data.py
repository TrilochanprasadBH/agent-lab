"""Thirty streams that break, and the wire format they break in.

Every case is a short answer streamed as server-sent events, and every case dies somewhere in the
middle. The client's job is to end up with the exact answer, know whether it got there, and do it
without paying for the same tokens twice.

    cut                 the socket dies inside a frame: the buffer ends mid-JSON
    eof                 the stream ends at a frame boundary, with no terminator
    stall               the socket stays open and stops delivering; only a timeout notices
    cut_twice           it dies again on the first reconnect
    resume_duplicates   the server replays the boundary token on resume
    ignore_resume       the server ignores the resume point and starts from the beginning

The four failures a client can make are independent, which is why the drill measures them
separately:

1. **Treating EOF as completion.** A frame that stops is not an answer that finished. The only
   evidence of completion is the `event: done` frame, and a client that stops at the end of the
   socket cannot tell a complete answer from one that was cut in half.
2. **Keeping a partial frame.** `data: {"v": "par` is not a token. A parser that trusts the last
   element of a split will either raise or emit half a word.
3. **Resuming from the wrong place.** The wire contract here is that `resume_from` is exclusive:
   the server sends tokens whose id is greater. A client that asks for the last id it saw gets
   that token again, and a client that appends whatever arrives duplicates it.
4. **Appending by position rather than by id.** When the server ignores the resume point — which
   it is allowed to do — the second delivery repeats tokens the client already has. Appending
   them doubles the answer; de-duplicating by id is idempotent.

Restarting from scratch is the other way to survive all of this, and it is correct. It also pays
for the whole answer twice. The cost cap is what separates a working client from an efficient one,
and the sweep measures both.

The answers are authored rather than generated so that an exact-match comparison is meaningful:
one wrong token, one duplicate, or one missing word is a failure, and that is the standard a
streaming client is actually held to.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

FAULTS = ("cut", "eof", "stall", "cut_twice", "resume_duplicates", "ignore_resume")
CASES_PER_FAULT = 5

CHUNK_BYTES = 48

TOKEN_COST = 0.000001
CONNECT_COST = 0.00001

ANSWERS = (
    "Thanks for waiting. Refunds are processed within {value} business days and appear on your "
    "statement at the end of the following cycle. If the refund has not appeared by then, reply "
    "to this message and we will trace it with the payment provider directly.",
    "I have moved the delivery to {value}. The courier will attempt it between nine and eleven "
    "in the morning, and you will get a message when the van is two stops away. Nothing else on "
    "the order changes.",
    "The export is ready. It contains every message from the last {value} and nothing older, "
    "because the retention policy deletes the rest on a rolling basis. The download link is "
    "valid for seven days and requires you to be signed in.",
    "Your plan renews on the first of the month at the current rate of {value} per seat. Adding "
    "a seat is prorated from the day you add it, and removing one takes effect at the next "
    "renewal rather than immediately.",
    "We have escalated the fault to the network team and they have {value} to respond. You do "
    "not need to do anything while that happens, and the reference on the ticket is already "
    "attached to your account.",
    "The certificate is valid until {value}. Renewal is automatic as long as the domain still "
    "resolves to us, and the new certificate is installed without downtime. If the domain "
    "moves, tell us before the expiry date.",
)

VALUES = (
    "five", "thirty", "fourteen", "ten", "three", "ninety",
    "seven", "twenty", "forty-five", "sixty",
)


@dataclass(frozen=True)
class Case:
    id: str
    tokens: tuple[str, ...]
    fault: str
    cut_at: int
    second_cut_at: int
    gold: str
    raw: str = ""


@dataclass
class Stream:
    chunks: list[bytes]
    stalled: bool
    case_id: str
    delivered: int
    _index: int = 0

    def read(self) -> bytes:
        """The next slice of bytes. `b""` at the end, `Stalled` when the socket has gone quiet."""
        if self._index < len(self.chunks):
            chunk = self.chunks[self._index]
            self._index += 1
            return chunk
        if self.stalled:
            raise Stalled(f"{self.case_id}: no bytes for 30s, the socket is still open")
        return b""


class Stalled(RuntimeError):
    """The socket is open and silent. A client without a timeout waits here forever."""


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


def _frame(index: int, token: str) -> bytes:
    payload = json.dumps({"v": token})
    return f"id: {index}\nevent: token\ndata: {payload}\n\n".encode()


DONE = b"event: done\ndata: {}\n\n"


def build(seed: int = 2027) -> list[Case]:
    cases: list[Case] = []
    for index in range(len(FAULTS) * CASES_PER_FAULT):
        fault = FAULTS[index % len(FAULTS)]
        text = ANSWERS[index % len(ANSWERS)].format(value=VALUES[index % len(VALUES)])
        tokens = tuple(text.split())
        cut_at = max(3, int(len(tokens) * (0.55 + 0.35 * _unit(seed, index, "cut"))))
        second = min(len(tokens) - 2, cut_at + 3 + int(5 * _unit(seed, index, "second")))
        cases.append(
            Case(
                id=f"s{index + 1:02d}",
                tokens=tokens,
                fault=fault,
                cut_at=cut_at,
                second_cut_at=second,
                gold=" ".join(tokens),
                raw=f"{fault:<18} cut at token {cut_at} of {len(tokens)}, "
                f"{len(tokens)} tokens",
            )
        )
    return cases


class Fabric:
    """The server side, and the meter.

    `connect` builds the bytes for one connection under the case's fault. It also bills: one fee
    per connection plus one unit per token frame delivered, whether or not the client wanted it.
    """

    name = "sse-fabric"

    def __init__(self, cases: list[Case]) -> None:
        self.by_id = {case.id: case for case in cases}
        self.cost_usd = 0.0
        self.latencies: list[float] = []
        self.n_calls = 0
        self.calls: list[dict] = []
        self.stats: dict[str, dict] = {}
        self.reset()

    def reset(self) -> None:
        self.cost_usd = 0.0
        self.latencies = []
        self.calls = []
        self.stats = {
            case_id: {"connections": 0, "tokens": 0, "duplicates": 0, "seen": set()}
            for case_id in self.by_id
        }

    def connect(self, case_id: str, resume_from: int = 0) -> Stream:
        case = self.by_id[case_id]
        stat = self.stats[case_id]
        attempt = stat["connections"]
        stat["connections"] += 1
        self.n_calls += 1

        start = max(0, resume_from)
        if case.fault == "ignore_resume" and attempt > 0:
            start = 0
        if case.fault == "resume_duplicates" and attempt > 0:
            start = max(0, start - 1)

        available = [(index, token) for index, token in enumerate(case.tokens, 1) if index > start]
        deliver = len(available)
        truncate = False
        stall = False

        if attempt == 0 and case.fault in (
            "cut",
            "cut_twice",
            "resume_duplicates",
            "ignore_resume",
        ):
            deliver = max(0, case.cut_at - start)
            truncate = True
        elif attempt == 0 and case.fault == "eof":
            deliver = max(0, case.cut_at - start)
        elif attempt == 0 and case.fault == "stall":
            deliver = max(0, case.cut_at - start)
            stall = True
        elif case.fault == "cut_twice" and attempt == 1:
            deliver = max(0, case.second_cut_at - start)
            truncate = True

        delivered = available[:deliver]
        if truncate and delivered:
            # Stop inside the last frame, which is what a dying socket actually does. Cutting at
            # a percentage of the whole body can land on a frame boundary by accident and turn a
            # `cut` into an `eof` without anyone noticing.
            body = b"".join(_frame(index, token) for index, token in delivered[:-1])
            last = _frame(*delivered[-1])
            body += last[: max(1, int(len(last) * 0.55))]
        else:
            body = b"".join(_frame(index, token) for index, token in delivered)

        complete = len(delivered) == len(available) and not stall and not truncate
        if complete:
            body += DONE

        chunks = [body[offset : offset + CHUNK_BYTES] for offset in range(0, len(body), CHUNK_BYTES)]

        stat["tokens"] += len(delivered)
        for index, _ in delivered:
            if index in stat["seen"]:
                stat["duplicates"] += 1
            stat["seen"].add(index)

        self.cost_usd += CONNECT_COST + len(delivered) * TOKEN_COST
        self.latencies.append(12.0 + len(delivered) * 0.4)
        self.calls.append(
            {
                "case": case_id,
                "attempt": attempt,
                "resume_from": resume_from,
                "start": start,
                "delivered": len(delivered),
                "stalled": stall,
                "complete": complete,
            }
        )
        return Stream(chunks=chunks, stalled=stall, case_id=case_id, delivered=len(delivered))


def fabric(cases: list[Case]) -> Fabric:
    return Fabric(cases)
