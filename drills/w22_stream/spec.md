# w22 — Finishing a stream that breaks

| | |
| --- | --- |
| **Goal** | Recover the exact answer from a server-sent-event stream that dies mid-flight, mark it complete only when it is, and do it without paying twice. |
| **Outcome** | 100% exact and complete, at 1.13× the gold tokens and $0.00198. |
| **Target** | exact text and correct terminator on ≥ 95% of 30 streams, under $0.0026 |
| **Time** | 45 to 75 minutes |

## 1. Why this drill exists

Streaming is the default user interface and it has a failure that does not look like one. A
connection that dies at token 30 of 45 produces a fluent, well-punctuated, *plausible* answer that
simply stops. There is no exception, no error frame, and nothing in the text that says it was cut.
The user reads it as an answer, because it is formatted like one.

Every case in this drill breaks. There is no happy path to compare against, because the happy path
is not where the bugs are:

```
cut                 the socket dies inside a frame: the buffer ends mid-JSON
eof                 the stream ends at a frame boundary, with no terminator
stall               the socket stays open and goes quiet; only a timeout notices
cut_twice           it dies again on the first reconnect
resume_duplicates   the server replays the boundary token on resume
ignore_resume       the server ignores the resume point and starts from token 1
```

The baseline — read until the socket closes, keep every complete frame, retry once from scratch on
a timeout — gets **16.7%**. It handles exactly the one fault that raises an exception and fails
the five that return end-of-stream.

## 2. What you are given

- `data.py`: the cases, the wire format, and the server.
- `data.Case.tokens` / `.gold`: the answer as tokens and as the exact string you must return.
- `data.Fabric.connect(case_id, resume_from=0)`: opens a connection. `resume_from` is **exclusive**
  — the server sends tokens whose id is greater. Each connection is billed: a fee plus one unit
  per token frame delivered.
- `data.Stream.read()`: the next slice of bytes, `b""` at the end, and `data.Stalled` when the
  socket is open and silent.
- `task.py`: the baseline.
- `sweep.py`: four clients and a per-fault breakdown.
- `check_wire.py`: verifies that each fault produces the bytes it claims.

The wire format is SSE-shaped:

```
id: 17
event: token
data: {"v": "refund"}

...

event: done
data: {}
```

`data.gold` is the tokens joined with single spaces, so an exact-match comparison catches one
missing word, one duplicated word, and one half-written word.

## 3. How to run it

```sh
python3 drills/w22_stream/check_wire.py
python3 drills/w22_stream/sweep.py
python3 run.py --drill w22_stream
python3 run.py --drill w22_stream --task solutions/w22_reference.py
```

## 4. Background: four rules and the fault each one covers

| client | exact | complete | both | conns | tokens | cost | fails |
| --- | --- | --- | --- | --- | --- | --- | --- |
| read to eof | 16.7% | 100% | 16.7% | 1.17 | 0.86× | $0.00136 | accuracy |
| restart until done | 100% | 100% | 100% | 2.17 | 1.82× | $0.00279 | cost |
| resume blind | 66.7% | 100% | 66.7% | 2.17 | 1.13× | $0.00198 | accuracy |
| **resume by id** | **100%** | **100%** | **100%** | **2.17** | **1.13×** | **$0.00198** | **nothing** |

And per fault, the joint score:

| client | cut | eof | stall | cut twice | resume duplicates | ignore resume |
| --- | --- | --- | --- | --- | --- | --- |
| read to eof | 0% | 0% | 100% | 0% | 0% | 0% |
| restart until done | 100% | 100% | 100% | 100% | 100% | 100% |
| resume blind | 100% | 100% | 100% | 100% | **0%** | **0%** |
| resume by id | 100% | 100% | 100% | 100% | 100% | 100% |

**Only complete frames are tokens.** The buffer splits on the blank line and the last piece is
kept for the next read. A `cut` leaves half a frame in that piece; it is thrown away when the
connection dies, which is correct, because half a word is not a word. This is the difference
between the first row and the third on the `cut` column.

**A connection ending is not an answer ending.** The `done` event is the only evidence of
completion. Two faults produce a clean end-of-stream with no terminator — `eof` at a frame
boundary and `stall` after a timeout — and a client that trusts the socket cannot tell either from
a finished answer. That is the whole of the first row's 16.7%: it only recovers the fault that
raises.

**Resume from the last id accepted, exclusively.** `resume_from=k` sends tokens after `k`. Asking
for the last id you *saw* is the off-by-one that makes `resume_duplicates` replay the boundary
token.

**Append by id, not by position.** The server is allowed to ignore the resume point. When it does,
the second delivery repeats everything the client already has. `if ident > last` makes the append
idempotent: a replay costs bandwidth and changes nothing. A client that appends whatever arrives
scores 0% on the last two columns and duplicates ten of thirty answers.

**Restarting is correct and costs twice as much.** It recovers every fault, needs no bookkeeping,
and re-sends the whole answer on every failure: 1.82× the tokens here. The cost cap is set at
$0.0026, which is 1.65× the gold tokens — above resuming, below restarting. That is the drill's
second question: not "does it work" but "what did it cost to make it work".

## 5. The task, step by step

1. Run the baseline and the sweep. Note that the baseline says `complete=True` on all 30 streams,
   including the 25 it truncated.
2. Parse frames properly: split the buffer on the blank line, keep the remainder, and only parse
   what came before it.
3. Replace `while chunk` with a loop that ends on the `done` event, and reconnects when the
   connection ends without one.
4. Track the highest id you have accepted and pass it as `resume_from`. Check what happens on
   `resume_duplicates` — you should see a token you already have.
5. Make the append idempotent and check `ignore_resume`.
6. Compare your cost with the restart client's. If they are equal, you are restarting.

Return `{"text": ..., "complete": bool}`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| exact text and complete | the accuracy line, target 95% |
| exact text | reported: the content was right |
| marked complete | reported: the terminator was handled |
| per fault | one bar each, so a hole is named rather than averaged |
| cost | cap $0.0026; a restart client exceeds it |
| connections | at least one per stream |

The two halves are separate on purpose. `exact text` without `marked complete` is a client that
recovers the answer and cannot tell you whether it did; `marked complete` without `exact text` is
the baseline, which claims success on everything.

## 7. Done when

- [ ] `python3 run.py --drill w22_stream --task solutions/w22_reference.py` reports TARGET MET
- [ ] you can explain why `eof` and `stall` are the same bug at different layers
- [ ] you can say what `resume_from=k` means and why `k-1` duplicates a token
- [ ] you can explain why `ignore_resume` is survivable and what makes it survivable
- [ ] your cost is under the cap and you can say why the restart client's is not
- [ ] `check_wire.py` passes

## 8. Carry forward

The general lesson is the one behind every resumable protocol: **completion is a message, not an
absence.** A closed socket, a null, an empty list and a `200 OK` are all "no more data", and none
of them is "finished". The same distinction is `w18`'s validity gate (a parseable object is not a
correct one) and `w20`'s first-failure ladder (a wrong answer is not a generation fault).

What this does not model, and you would meet all of it in production:

- **The real resume channel is the `Last-Event-ID` header**, sent automatically by `EventSource`,
  not a query parameter. The server is expected to honour it; `ignore_resume` is the adversarial
  case that teaches idempotency rather than a common one.
- **Keep-alive comments** (`: ping`) exist to stop proxies from dropping an idle stream. A client
  that treats any non-`data:` line as a frame boundary will break on them.
- **Backpressure and ordering** are absent: the server here always sends in order at a fixed rate.
- **A tool call can fire mid-stream**, and then a resume is not idempotent at the system level
  even when the text is. That is `triage` stage 04's approval gate, applied to a stream.

The connection between this drill and the previous one is worth stating: `w21` measures how long
the first token takes to arrive, and this one measures what happens after it does. A product that
gets the first token fast and then truncates the answer has moved the failure, not removed it.
