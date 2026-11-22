# Drill 07 — Getting a reliable answer out of a noisy judge

| | |
| --- | --- |
| **Goal** | Combine several noisy judgements into one reliable preference. |
| **Outcome** | A judge function that agrees with human preferences on 85% of 36 pairs, under a cost cap, despite a judge with position bias and random error. |
| **Target** | 85% agreement, cost under $0.015. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

Some output cannot be scored against an exact answer. Tone, helpfulness, whether a
summary is faithful. For those, you use a model as a judge.

A judge is a measuring instrument, and like any instrument it has error. If you do
not know your instrument's error, you do not know what your measurements mean.

This drill gives you a judge with two specific defects and asks you to design the
measurement procedure around them.

## 2. What you are given

- `data.py`: 36 pairs of responses to the same question.
- Each pair has a hidden human preference: `"A"`, `"B"`, or `"tie"`. There are 30
  decided pairs and 6 ties.
- A judge, `NoisyJudge`, with two defects:
  - **position bias**: 35% of the time it prefers whichever response is printed first;
  - **noise**: 10% of the time it picks the worse response for no reason.
- Each judge call costs $0.0001. The cap is $0.015, which allows 4 calls per pair
  and no more.
- `task.py`: the file you edit. It calls the judge once and returns the verdict.

## 3. How to run it

```sh
python3 run.py --drill w07_judge
python3 run.py --drill w07_judge --failures 10
python3 run.py --drill w07_judge --task solutions/w07_reference.py
```

## 4. Background: the idea from first principles

**The measurement.** For each pair you must output `"A"`, `"B"`, or `"tie"`. The
human labels are the truth. Your score is agreement with them.

**Defect 1: position bias.** The judge has a tendency to prefer the response you put
first. This is a *systematic* error: it always pushes in the same direction, given
the same layout.

Systematic errors can be measured and cancelled. Ask the same pair twice, once in
each order. Then translate the second verdict back into the first's coordinate
system:

```
call 1   A printed first   verdict "A"  →  A is better
call 2   B printed first   verdict "A"  →  B is better
```

If both calls say the same thing about the *content*, that is real evidence. If the
first says A and the second also favours A after translation, the judge agreed with
itself across both layouts.

**Defect 2: noise.** Random error has no direction. Swapping cannot cancel it,
because it does not favour anything. The only way to reduce it is to take more
samples and let the majority outvote the errors.

These two defects need two different fixes, and the fixes must be applied together.

**The trap that catches almost everyone.** The judge is deterministic. Give it the
same prompt twice and it returns the same verdict. So calling it twice with an
identical prompt is not two samples; it is one sample, counted twice. Your accuracy
will look stable while you measure nothing.

To obtain genuinely independent samples, the prompt must differ. A short marker at
the top of the prompt, such as `(sample 2)`, is enough. This is also true of real
models at temperature 0: the request must vary for the response to vary.

**The second trap: balance.** If you take three samples as *forward, swapped,
forward*, the two forward samples both carry the same positional advantage. You have
not cancelled the bias, you have amplified it: two votes lean one way, one leans the
other.

Samples must be balanced: two forward, two swapped. Even counts, half in each order.

**Combining the votes.** Count every outcome, including `tie`, and take the
plurality. Two mistakes are common here:

- Dropping ties before counting biases the result toward whichever of A or B
  survived, so a pair the judge called a tie becomes a confident preference.
- Requiring a strict majority of *all* samples (rather than of the votes cast)
  turns genuine 2-to-1 decisions into ties.

**Why ties are real.** When two responses are equally good, a judge that says "tie"
is correct. Scored against human labels, that answer earns a point. Treating ties as
failures is how teams end up with judges that manufacture differences.

## 5. The task, step by step

1. Run the starting code. Note that it is already right about two thirds of the time.
   A single call is not a bad instrument; it is an uncalibrated one.
2. Write a helper that calls the judge with a specified order and a sample number.
3. Translate verdicts from the swapped call back to a common coordinate system.
4. Take four samples: forward, swapped, forward, swapped, each with a distinct
   sample number.
5. Count A, B, and tie. Return the plurality, with ties resolving to `"tie"`.
6. Check your total cost is under $0.015. Four calls per pair is $0.0144.

## 6. How you are scored

`agreement` is the fraction of the 36 pairs where your verdict matches the human
label.

The drill passes at 85% or better, with total cost at or below $0.015. Four calls
per pair fits. Six does not.

The note reports how many calls you made. If it is not 144, check whether your
sampling is balanced.

## 7. Done when

- [ ] `python3 run.py --drill w07_judge` reports TARGET MET
- [ ] your sample count per pair is even
- [ ] each sample uses a different prompt, not an identical one
- [ ] ties are counted as an outcome, not discarded
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Two defects, two different fixes.

- **Bias** is directional: cancel it by measuring both orders.
- **Noise** is directionless: reduce it by sampling, which requires varying the
  prompt.

And balance your samples. An odd number of alternating samples quietly reintroduces
the bias you were trying to remove.
