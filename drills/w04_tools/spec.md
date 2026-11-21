# Drill 04 — tool schemas and malformed arguments

**Target:** 90% correct outcomes, zero state-changing calls without confirmation.

```
python3 run.py --drill w04_tools
```

You edit `task.py`. There are fourteen cases.

## The thing nobody tells you

Most agent bugs are not model bugs. They are the twenty lines between "the model
returned text" and "the tool ran". Fourteen requests, fourteen ways for that gap to
go wrong:

| case | what arrives |
|---|---|
| t01 | clean JSON, wrapped in a fence |
| t02 | valid call, valid enum |
| t03 | valid call |
| t04 | prose, then JSON |
| t05 | truncated mid-object |
| t06 | arguments as a *string* containing JSON |
| t07 | tool name that does not exist |
| t08 | required parameter missing |
| t09 | invented enum value |
| t10 | enum value in the wrong case |
| t11 | extra invented parameter |
| t12 | order id as a number, not a string |
| t13 | refund with `"confirm": true` written by the model |
| t14 | a refusal instead of a call |

## The rules that matter

1. **Degrade on shape, not on meaning.** Fences, prose, truncation, double-encoded
   arguments — all mechanical, all fixable. A refusal is `no_call`, not an error.
2. **Validate before you execute.** A handler that runs and then fails has already
   changed state.
3. **Unknown parameters are errors.** Silently dropping them is how a typo becomes
   a wrong write.
4. **Confirmation is a human act.** The model writing `"confirm": true` is the
   model's opinion about consent. It has no authority to have one.

The world in this drill validates nothing, on purpose. That is your job, and the
score inspects what actually ran — not what you say ran.

## Done looks like

- [ ] TARGET MET, and the `safe` metric is 100%
- [ ] `t13` returns `needs_confirmation` without refunding anything
- [ ] you can point at the line where a dangerous tool would have executed, and
      say why it cannot

## Why this generalises

Every tool-using system has this layer. MCP servers, function calling, a shell
wrapper, a browser driver. The model changes; the layer does not.
