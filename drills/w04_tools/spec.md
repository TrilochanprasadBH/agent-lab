# Drill 04 — Turning text into a safe tool call

| | |
| --- | --- |
| **Goal** | Convert model output into a validated tool call, or a named rejection. |
| **Outcome** | A handler that classifies 14 malformed calls correctly and never executes a state-changing action without authorisation. |
| **Target** | 90% correct outcomes, zero unauthorised actions. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

A model does not call functions. It writes text that describes a function call, and
something on your side decides whether that text becomes an action.

That decision point is where most agent bugs live. This drill isolates it: fourteen
requests, fourteen different ways for the text to be wrong.

## 2. What you are given

- `data.py`: a small world with customers, orders, and five tools. The world does
  no validation of its own, on purpose.
- `data.py` also contains 14 cases. Each has a user request and the text the model
  produced for it.
- `task.py`: the file you edit. It parses the text with `json.loads` and executes
  whatever comes out.

The 14 cases and the correct outcome for each:

| case | what arrives | correct outcome |
| --- | --- | --- |
| t01 | clean JSON, inside a code fence | `ok` |
| t02 | valid call with a valid enum value | `ok` |
| t03 | valid call | `ok` |
| t04 | a sentence, then the JSON object | `ok` |
| t05 | truncated mid-object | `ok` if recoverable |
| t06 | arguments as a JSON string, not an object | `ok` |
| t07 | a tool name that does not exist | `unknown_tool` |
| t08 | a required parameter is missing | `missing_param` |
| t09 | an enum value that does not exist | `bad_enum` |
| t10 | an enum value in the wrong case | `bad_enum` |
| t11 | an extra parameter that does not exist | `unknown_param` |
| t12 | an order id sent as a number, not a string | `bad_type` |
| t13 | a refund with `"confirm": true` written by the model | `needs_confirmation` |
| t14 | a refusal instead of a call | `no_call` |

## 3. How to run it

```sh
python3 run.py --drill w04_tools
python3 run.py --drill w04_tools --failures 14
python3 run.py --drill w04_tools --task solutions/w04_reference.py
```

## 4. Background: the idea from first principles

**What a tool call is.** A name, plus an object of arguments. That is all.

**Why the text is unreliable.** The model is producing language that happens to look
like a call. It can wrap it in prose, put it in a code fence, truncate it, encode
the arguments twice, or refuse. None of that is malicious; it is what language
models do.

**The four layers between text and action.**

1. **Parse.** Find the object in the text. Strip fences and prose. Repair truncation.
2. **Validate.** Check the object against the tool's schema before anything runs.
3. **Authorise.** Decide whether this action is allowed at all, given who asked.
4. **Execute.** Only now call the function.

Each layer catches a class of error the previous one cannot.

**Why validation must come before execution.** A function that runs and then fails
has already changed state. Validation is cheap and happens while nothing has
happened yet.

**What validation checks.**

- The tool exists.
- Every required parameter is present.
- Every value has the right type. Type coercion should be narrow and deliberate:
  `"3"` can become `3`, but `3.5` cannot become `3`, and a number cannot silently
  become a string id.
- Every enum value is one of the allowed values.
- No parameters exist that the tool does not declare. Dropping them silently is how
  a typo becomes a wrong write.

**Why unknown parameters are errors.** If the model invents `"verbose": true`, you
have two choices: ignore it, or reject it. Ignoring it teaches you nothing and hides
a misunderstanding. Rejecting it produces a clean error the model can correct.

**Why confirmation is not the model's decision.** Case t13 contains
`"confirm": true`, written by the model. If the model could authorise its own
refunds, the field would mean nothing. Confirmation is a human act. In code, that
means the authorisation flag must come from outside the model's output, or the call
is refused.

The distinction is worth stating precisely: the model may *request* a dangerous
action. It may not *approve* one.

**Why a refusal is not an error.** A refusal is a valid response. It means no call
happened. Treat it as `no_call`, not as a parse failure, because the two require
different handling upstream.

## 5. The task, step by step

1. Run the starting code. Count how many dangerous actions it executed.
2. Write a parser that handles fences, prose, trailing text, and truncation.
3. Unwrap arguments if they arrived as a JSON string.
4. Define the five tools with their parameter schemas.
5. Build a registry that validates before executing and returns errors as data.
6. Refuse dangerous tools unless confirmation came from outside the model.
7. Map each validation error to the outcome names in the table above.

## 6. How you are scored

Two metrics.

`correct outcome` is the fraction of cases where the outcome you returned matches the
correct outcome in the table above, and, for `ok` cases, the tool that ran is the
expected one.

`no unauthorised action` is 1.0 only if no dangerous tool executed. The harness
inspects the world's log, not your return value, so claiming safety is not enough.

`accuracy` is the mean of the two metrics. The drill passes at 90% or better, which
in practice requires all fourteen produced outcomes to be correct and nothing unsafe
to run.

## 7. Done when

- [ ] `python3 run.py --drill w04_tools` reports TARGET MET
- [ ] both metrics are at 100%
- [ ] `t13` returned `needs_confirmation` and refunded nothing
- [ ] you can point to the line where a dangerous call is refused
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Four layers, in this order, every time:

```
parse  →  validate  →  authorise  →  execute
```

Validation happens before execution, unknown parameters are errors, and permission
comes from a human, never from the model's own output.
