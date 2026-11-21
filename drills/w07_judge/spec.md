# Drill 07 — judge calibration

**Target:** 85% agreement with human preference labels, under a $0.015 cap.

```
python3 run.py --drill w07_judge
```

You edit `task.py`. Implement `judge(pair, model) -> "A" | "B" | "tie"`.

## Two defects, two different fixes

The judge is right about 90% of the time on a clean read, and it has two problems:

**Position bias.** When it is unsure, it prefers whichever response you printed
first. This is *systematic*, and systematic errors are fixable: ask the same
question twice with the order swapped, and map the verdicts back to the same
coordinate system. If the judge says "A" both times, it agreed with itself across
both positions, which is real evidence.

**Noise.** About one call in ten picks the worse answer for no reason. This is
*random*, and you cannot swap it away. You can only outvote it — which costs money,
and the cap is real.

## The trap that catches almost everyone

The judge is deterministic. Give it the same prompt twice and it returns the same
verdict, every time. Two identical calls is not two samples, it is one sample
counted twice — and it will make your accuracy look stable while measuring nothing.

To actually resample you have to vary the prompt. A salt line is enough.

## The second trap

Balanced orders or it does not work. Two forward and one swapped is *worse than
random*, because the imbalance amplifies the bias instead of cancelling it. If you
sample, sample symmetrically.

## Done looks like

- [ ] TARGET MET under the cap
- [ ] your sample count is even, and you can say why
- [ ] you re-ask with a different prompt, not the identical one
- [ ] you tally ties as a real outcome instead of dropping them

## Why this matters

Model-as-judge is how you evaluate anything open-ended: tone, helpfulness, whether
a summary is faithful. Every one of those pipelines has position bias and every one
of them is quietly resampling a deterministic prompt somewhere. The difference
between a judge you can trust and one you cannot is usually this drill.
