# Progress log

One entry per drill. The score is the evidence. The written note is what makes it
stay.

## How to use this file

After each drill, add an entry using the template at the bottom. Four short
sentences is enough. The point is to record what you changed and what happened,
while you still remember it.

## Scoreboard

Fill in the `best` and `date` columns as you go. Leave them blank until you have
done the drill.

| # | drill | starting score | your best | target | date |
| --- | --- | --- | --- | --- | --- |
| 01 | schema repair | 70.8% | | 90% | |
| 02 | retrieval | 71.7% | | 88% | |
| 03 | context packing | 11.1% | | 90% | |
| 04 | tool calls | 10.7% | | 90% | |
| 05 | agent loop | 20.0% | | 90% | |
| 06 | evals | 50.0% | | 90% | |
| 07 | judge calibration | 66.7% | | 85% | |
| 08 | routing | 100% but $0.060 | | 92% under $0.030 | |
| 09 | injection defence | 0.0% | | 95% | |
| 10 | trace triage | 18.3% | | 90% | |
| 11 | capstone | 20.8% | | 90% and zero unsafe | |
| 12 | significance | 60.0% | | 90% | |
| 13 | eval sets | 31.2% | | 90% | |
| 14 | trajectory eval | 42.9% | | 85% | |
| 15 | regression gating | 63.3% | | 90% | |
| 16 | semantic cache | 0.0% | | 68%, wrong hits under 5% | |
| 17 | PII redaction | 0.0% (25% recall, 80% precision) | | 93% recall, precision ≥ 90% | |
| 18 | constrained JSON | 0.0% (36.7% valid, 33.3% correct) | | 82% correct, validity ≥ 99% | |
| 19 | memory | 30.8% (26.9% wrong, 42.3% abstained) | | 85% retained | |
| 20 | debug a wrong answer | 14.3% | | 90% joint diagnosis | |
| 21 | first-token latency | 0.0% (97.7% quality, p95 480s) | | 92%, p95 ≤ 900ms, $0.0008 | |
| 22 | streaming | 16.7% exact, 100% claimed complete | | 95% exact, under $0.0026 | |
| 23 | fine-tune or RAG | 12.5% | | 90% of decisions | |

## Entry template

Copy this block for each drill.

```md
### Drill NN — name

Date:
Start: NN.N%   Best: NN.N%   Cost: $0.NNNN

What I changed
-

What moved the number
-

What surprised me
-

The rule I am taking forward
-
```

## Entries

Nothing yet. Add your first entry after drill 01.
