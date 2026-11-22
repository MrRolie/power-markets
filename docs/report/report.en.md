# The price at the border: NYISO's "H Q" zone

_English version. [Version française, la référence](report.fr.md)._

This repository forecasts and validates the hourly electricity price at the zone New York's grid operator (NYISO) names "H Q", the border with Québec, and the congestion component of that price, day-ahead and real-time. What matters here is the discipline, not the model: each forecast has a decision time taken from the operator's documents; no file archived less than 60 minutes before that time is admitted; the plan was frozen by a git tag before any replay of the held-out year.

## At a glance

- On the held-out year, **3 of 10 pairs** beat their baseline under the plan's rule: M1:T1_da_lbmp, M1:T3_rt_lbmp, M2:T3_rt_lbmp.
- Lower loss, but not significant after the Holm correction: P2:T2_da_mcc.
- Higher loss than the baseline: M1:T2_da_mcc, M1:T4_rt_mcc, M2:T1_da_lbmp, M2:T2_da_mcc, M2:T4_rt_mcc, P2:T4_rt_mcc.
- For congestion, no model beats the zero forecast (Z).
- "No edge" is a legal result, published as plainly as an edge would be. No profit line: nothing in the rules read shows the position can be taken at this location.
- M1:T1_da_lbmp: lower MAE than B0 in 12 of 12 months.
- M1:T3_rt_lbmp: lower MAE than B0 in 12 of 12 months.
- M2:T3_rt_lbmp: lower MAE than B0 in 12 of 12 months.
- Missing data: T3_rt_lbmp, T4_rt_mcc: 456 hours with no outcome (2026-07); scored on 8,304 hours. Verdict of P2:T4_rt_mcc undetermined (scoring defect). See Limits.
- Departure allowed by the owner: a second replay, hours with no outcome scored as missing: 3 of 10 pairs; verdicts changed: none. See "Departure from the plan".

_(run `20261120T233440Z-replay-8359cd`, held out)_

## Legend

- **Targets**: T1 day-ahead price; T2 its posted congestion component; T3 real-time integrated hourly price; T4 its posted congestion. Location: the "H Q" zone.
- **Models**: B0 = same hour of the latest known day of the same market (the day before for T1, T2; two days before for T3, T4); B1 = same hour seven days earlier; Z = zero; M1 = per-hour LASSO on transformed prices (LEAR); M2 = boosted trees; M1−LF = M1 without the load forecast; P0 = share of congested hours over 28 days; P2 = boosted-tree probability. Deciding baseline: B0 for T1, T3; Z for T2, T4; P0 for P2.
- **Held-out year**: operating days of months 2025-11 to 2026-10, inclusive.
- **Signs**: bias = forecast − realised (negative = under-forecast). Posted price = energy + losses − posted congestion: a positive posted congestion lowers the price at "H Q".
- **Units**: US dollars; MAE = mean absolute error, RMSE = root mean squared error, in US$/MWh.

## The location and its rules

- "H Q" (PTID 61844) is an external zone posted "for informational purposes only"; its price is that of the proxy generator bus `HQ_GEN_WHEEL` (PTID 23651), which settles external transactions (MST 17.1).
- Every Hydro-Québec proxy bus is designated non-competitive (MST 4.4.4): in real time, an import-constrained interface can pin the price at or below zero (MST 17.1.6.3.3).
- Measurements from the data spike, not a tracked run ([docs/problem.md](../problem.md) §5): the posted price is energy + losses − posted congestion (the fifteen names agree within 0.02 US$/MWh at the 99th percentile, archives 2016-01 to 2025-10); "H Q" tracks the NORTH zone (correlation 0.974).
- Frozen plan: [docs/plan.md](../plan.md).

## Discipline

- **Decision time**: 05:00 Eastern on the day before the operating day, the day-ahead bid deadline (NYISO Manual 11, §2.2; MST 4.2.1.1). The forecast covers the 23, 24 or 25 hours of the day, 19 to 43 hours ahead.
- **Admission**: no file whose archive stamp is later than 60 minutes before the decision time is admitted; otherwise the latest earlier qualifying day takes its slot.
- **Walk-forward validation**: one fold per month, refit at each fold start, purge by the targets' posting time, a 7-day embargo enforced by a check that refuses any violation.
- **Frozen plan**: tag `plan-v1`; plan files identical to the tag at validation and at the replay: yes.
- **Held-out replay**: 2 finished replay(s) recorded in `docs/replay-ledger.json`; registered replay: commit `3bc75c2`, tree clean at start and end: yes.
- **Departures from the plan**: see docs/departures.md. Registered targets not run: none. Decisions taken after the tag, before and after the replay: [docs/implementation-notes.md](../implementation-notes.md).
- Before the tag, a review measured on the validation window that Z beats B0 on T2; that is why Z decides for congestion (plan preamble).

## Results on the held-out year

| Pair | Model loss | Baseline loss | Difference | one-sided p (DM) | Holm p | Beats baseline |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 10.592 | 14.038 | −3.446 | < 0.001 | < 0.001 | yes |
| M2:T1_da_lbmp | 15.814 | 14.038 | 1.776 | 0.734 | 1.000 | no |
| M1:T2_da_mcc | 1.786 | 1.367 | 0.420 | 1.000 | 1.000 | no |
| M2:T2_da_mcc | 1.370 | 1.367 | 0.003 | 0.946 | 1.000 | no |
| P2:T2_da_mcc | 0.1067 | 0.1115 | −0.0048 | 0.021 | 0.148 | no |
| M1:T3_rt_lbmp | 17.600 | 25.816 | −8.216 | < 0.001 | < 0.001 | yes |
| M2:T3_rt_lbmp | 17.753 | 25.816 | −8.064 | < 0.001 | < 0.001 | yes |
| M1:T4_rt_mcc | 1.238 | 0.674 | 0.564 | 1.000 | 1.000 | no |
| M2:T4_rt_mcc | 0.675 | 0.674 | 0.001 | 0.843 | 1.000 | no |
| P2:T4_rt_mcc ¹ | 0.1001 | 0.0990 | 0.0011 | 0.669 | 1.000 | no |

Losses: MAE in US$/MWh; Brier score for P2. Difference = model − baseline; negative = better. Holm family: the 10 pairs. ¹ Computed counting hours with no outcome as "no congestion": a scoring defect; the sign of the difference could change, so the verdict is undetermined until these numbers are recomputed. See Limits. _(run `20261120T233440Z-replay-8359cd`, held out)_

### T1, day-ahead price

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 14.04 | 33.23 | 0.04 | 64.58 | 8,760 |
| B1 | 32.92 | 86.10 | 0.28 | 172.46 | 8,760 |
| M1 | 10.59 | 30.91 | −5.19 | 57.84 | 8,760 |
| M2 | 15.81 | 56.07 | −7.28 | 103.02 | 8,760 |

_(run `20261120T233440Z-replay-8359cd`, held out)_


By season and hour group (MAE):

| Season | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 33.91 | 28.48 | 45.54 |
| MAM | 7.69 | 4.59 | 5.68 |
| JJA | 9.12 | 5.49 | 7.60 |
| SON | 5.78 | 4.12 | 4.96 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

| Hours | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 11.08 | 9.25 | 12.10 |
| 07-22 | 15.52 | 11.21 | 17.63 |
| 23 | 11.05 | 10.11 | 12.82 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

### T2, day-ahead posted congestion

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 2.01 | 10.35 | 0.00 | — | 8,760 |
| B1 | 2.57 | 12.41 | 0.00 | — | 8,760 |
| Z | 1.37 | 8.95 | 0.80 | — | 8,760 |
| M1 | 1.79 | 8.87 | 0.76 | — | 8,760 |
| M2 | 1.37 | 8.95 | 0.79 | — | 8,760 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

M2's MAE differs from Z's (the zero forecast) by only 0.003 US$/MWh; the records do not keep the size of M2's forecasts. Under absolute loss, the conditional median of a mostly zero series is zero.

By season and hour group (MAE):

| Season | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 6.48 | 4.60 | 5.00 | 4.60 |
| MAM | 0.33 | 0.18 | 0.58 | 0.18 |
| JJA | 0.78 | 0.45 | 0.96 | 0.45 |
| SON | 0.54 | 0.30 | 0.66 | 0.31 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

| Hours | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 1.32 | 0.87 | 1.18 | 0.87 |
| 07-22 | 2.34 | 1.60 | 2.06 | 1.60 |
| 23 | 1.63 | 1.11 | 1.58 | 1.12 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

### T3, real-time integrated hourly price

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 25.82 | 59.48 | −0.10 | 94.15 | 8,304 |
| B1 | 31.17 | 66.42 | 0.39 | 115.47 | 8,304 |
| M1 | 17.60 | 45.55 | −10.20 | 86.79 | 8,304 |
| M2 | 17.75 | 46.09 | −8.72 | 85.13 | 8,304 |

_(run `20261120T233440Z-replay-8359cd`, held out)_


By season and hour group (MAE):

| Season | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 50.51 | 36.31 | 36.34 |
| MAM | 18.94 | 11.62 | 12.19 |
| JJA | 18.26 | 11.24 | 11.46 |
| SON | 14.41 | 10.24 | 10.05 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

| Hours | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 18.79 | 12.53 | 11.75 |
| 07-22 | 29.36 | 20.08 | 20.67 |
| 23 | 18.38 | 13.35 | 13.06 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

### T4, real-time posted congestion

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 1.31 | 10.60 | 0.01 | — | 8,304 |
| B1 | 1.32 | 10.60 | 0.00 | — | 8,304 |
| Z | 0.67 | 7.50 | −0.15 | — | 8,304 |
| M1 | 1.24 | 7.55 | 0.12 | — | 8,304 |
| M2 | 0.67 | 7.50 | −0.15 | — | 8,304 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

M2's MAE differs from Z's (the zero forecast) by only 0.001 US$/MWh; the records do not keep the size of M2's forecasts. Under absolute loss, the conditional median of a mostly zero series is zero.

By season and hour group (MAE):

| Season | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 1.72 | 0.88 | 1.80 | 0.88 |
| MAM | 1.03 | 0.53 | 0.93 | 0.53 |
| JJA | 1.33 | 0.69 | 1.20 | 0.69 |
| SON | 1.18 | 0.60 | 1.02 | 0.60 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

| Hours | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0.34 | 0.18 | 0.46 | 0.18 |
| 07-22 | 1.74 | 0.90 | 1.60 | 0.90 |
| 23 | 1.16 | 0.61 | 0.85 | 0.61 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

Congestion: each model against B0, for information only; the rule judges against Z.

| Target | Model | Model MAE | B0 MAE | one-sided p (DM, uncorrected) |
|---|---|---|---|---|
| T2_da_mcc | M1 | 1.786 | 2.012 | 0.132 |
| T2_da_mcc | M2 | 1.370 | 2.012 | 0.001 |
| T4_rt_mcc | M1 | 1.238 | 1.310 | 0.246 |
| T4_rt_mcc | M2 | 0.675 | 1.310 | < 0.001 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

### Where the error lies (T1)

MAE by month (US$/MWh).

| Month | B0 | M1 | M2 | Hours |
|---|---|---|---|---|
| 2025-11 | 7.03 | 5.00 | 7.35 | 721 |
| 2025-12 | 21.15 | 16.03 | 17.79 | 744 |
| 2026-01 | 58.05 | 49.90 | 83.97 | 744 |
| 2026-02 | 21.30 | 18.56 | 33.74 | 672 |
| 2026-03 | 8.95 | 4.57 | 6.00 | 743 |
| 2026-04 | 6.80 | 4.62 | 5.43 | 720 |
| 2026-05 | 7.28 | 4.58 | 5.59 | 744 |
| 2026-06 | 6.41 | 4.29 | 5.12 | 720 |
| 2026-07 | 15.11 | 8.41 | 13.75 | 744 |
| 2026-08 | 5.76 | 3.74 | 3.86 | 744 |
| 2026-09 | 5.51 | 3.91 | 3.34 | 720 |
| 2026-10 | 4.83 | 3.46 | 4.21 | 744 |

Bias (forecast − realised) by realised price decile; 9 = the 10 % most expensive hours.

| Decile | B0 | M1 | M2 |
|---|---|---|---|
| 0 | 3.84 | 1.39 | 3.72 |
| 1 | 2.15 | 0.39 | 1.42 |
| 2 | 1.49 | 0.22 | 0.73 |
| 3 | 0.83 | −0.07 | 0.25 |
| 4 | −0.49 | −0.95 | −0.65 |
| 5 | −0.18 | −1.84 | −1.56 |
| 6 | 1.37 | −1.67 | −1.07 |
| 7 | 0.30 | −2.01 | −1.84 |
| 8 | 0.06 | −6.04 | −6.86 |
| 9 | −9.09 | −41.72 | −67.54 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

## Departure from the plan: a second replay

Recorded reason: "The July 2026 real-time archive as first fetched held 12 of 31 daily files; re-fetched, and the held-out year replayed with missing outcomes scored as missing (post-replay scoring fix, docs/implementation-notes.md). Allowed by the owner on 2026-11-22, answering the card 'May I re-download it and run a second held-out replay, shown in the report beside the first as a recorded departure from the plan?': 'Yes, re-run (Recommended)'.". The registered result stays the first replay's; this second replay is shown beside it, never in its place. Pairs that beat their baseline: 3 of 10 (first replay: 3). Verdicts changed: none.

Its forecasts are identical to the first replay's (same SHA-256 hashes): only the scoring differs.

The record marks the tree dirty at the start: that is the ledger entry the command writes before this snapshot; the command refuses a dirty tree before writing it (fixed afterwards, see docs/implementation-notes.md).

T3_rt_lbmp, T4_rt_mcc: 456 hours with no outcome (2026-07); scored on 8,304 hours.

| Pair | Model loss | Baseline loss | Difference | one-sided p (DM) | Holm p | Beats baseline |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 10.592 | 14.038 | −3.446 | < 0.001 | < 0.001 | yes |
| M2:T1_da_lbmp | 15.814 | 14.038 | 1.776 | 0.734 | 1.000 | no |
| M1:T2_da_mcc | 1.786 | 1.367 | 0.420 | 1.000 | 1.000 | no |
| M2:T2_da_mcc | 1.370 | 1.367 | 0.003 | 0.946 | 1.000 | no |
| P2:T2_da_mcc | 0.1067 | 0.1115 | −0.0048 | 0.021 | 0.148 | no |
| M1:T3_rt_lbmp | 17.600 | 25.816 | −8.216 | < 0.001 | < 0.001 | yes |
| M2:T3_rt_lbmp | 17.753 | 25.816 | −8.064 | < 0.001 | < 0.001 | yes |
| M1:T4_rt_mcc | 1.238 | 0.674 | 0.564 | 1.000 | 1.000 | no |
| M2:T4_rt_mcc | 0.675 | 0.674 | 0.001 | 0.843 | 1.000 | no |
| P2:T4_rt_mcc | 0.1012 | 0.1035 | −0.0023 | 0.044 | 0.262 | no |

Losses: MAE in US$/MWh; Brier score for P2. Difference = model − baseline; negative = better. Holm family: the 10 pairs. _(run `20261122T183753Z-replay-38737f`, held out)_

| Target | Model | 90 % coverage | Hours |
|---|---|---|---|
| T1_da_lbmp | M1 | 88.7 % | 8,760 |
| T1_da_lbmp | M2 | 88.4 % | 8,760 |
| T2_da_mcc | M1 | 88.1 % | 8,760 |
| T2_da_mcc | M2 | 91.4 % | 8,760 |
| T3_rt_lbmp | M1 | 89.3 % | 8,304 |
| T3_rt_lbmp | M2 | 89.1 % | 8,304 |
| T4_rt_mcc | M1 | 92.5 % | 8,304 |
| T4_rt_mcc | M2 | 91.9 % | 8,304 |

_(run `20261122T183753Z-replay-38737f`, held out)_

## Rehearsal on the last validation year (November 2024 to October 2025, seen)

The same code as the replay, on a seen year: a stability signal, not a test.

| Pair | Model loss | Baseline loss | Difference | one-sided p (DM) | Holm p | Beats baseline |
|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 8.343 | 10.069 | −1.726 | < 0.001 | < 0.001 | yes |
| M2:T1_da_lbmp | 8.409 | 10.069 | −1.660 | < 0.001 | 0.001 | yes |
| M1:T2_da_mcc | 0.708 | 0.483 | 0.225 | 1.000 | 1.000 | no |
| M2:T2_da_mcc | 0.493 | 0.483 | 0.009 | 0.968 | 1.000 | no |
| P2:T2_da_mcc | 0.1048 | 0.1255 | −0.0207 | 0.004 | 0.023 | yes |
| M1:T3_rt_lbmp | 17.241 | 22.944 | −5.703 | < 0.001 | < 0.001 | yes |
| M2:T3_rt_lbmp | 15.777 | 22.944 | −7.166 | < 0.001 | < 0.001 | yes |
| M1:T4_rt_mcc | 1.944 | 1.166 | 0.778 | 1.000 | 1.000 | no |
| M2:T4_rt_mcc | 1.166 | 1.166 | 0.000 | 1.000 | 1.000 | no |
| P2:T4_rt_mcc | 0.1308 | 0.1363 | −0.0055 | 0.005 | 0.024 | yes |

Losses: MAE in US$/MWh; Brier score for P2. Difference = model − baseline; negative = better. Holm family: the 10 pairs. _(run `20261120T231232Z-rehearse-796e3f`, validation (seen))_

## Validation (seen), November 2022 to October 2025

These numbers set the thresholds and the intervals; they decide nothing.

Each model against its deciding baseline on the validation folds, for information: validation decides nothing.

| Target | Baseline | Model | Model loss | Baseline loss | one-sided p (DM, uncorrected) |
|---|---|---|---|---|---|
| T1_da_lbmp | B0 | M1 | 6.193 | 7.591 | < 0.001 |
| T1_da_lbmp | B0 | M2 | 6.494 | 7.591 | < 0.001 |
| T2_da_mcc | Z | M1 | 0.793 | 0.451 | 1.000 |
| T2_da_mcc | Z | M2 | 0.463 | 0.451 | 0.992 |
| T2_da_mcc | P0 | P2 | Brier 0.1257 | Brier 0.1323 | 0.022 |
| T3_rt_lbmp | B0 | M1 | 12.613 | 17.582 | < 0.001 |
| T3_rt_lbmp | B0 | M2 | 12.200 | 17.582 | < 0.001 |
| T4_rt_mcc | Z | M1 | 2.860 | 1.333 | 1.000 |
| T4_rt_mcc | Z | M2 | 1.333 | 1.333 | 0.920 |
| T4_rt_mcc | P0 | P2 | Brier 0.1211 | Brier 0.1250 | < 0.001 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

Congestion: each model against B0, for information only; the rule judges against Z.

| Target | Model | Model MAE | B0 MAE | one-sided p (DM, uncorrected) |
|---|---|---|---|---|
| T2_da_mcc | M1 | 0.793 | 0.728 | 0.960 |
| T2_da_mcc | M2 | 0.463 | 0.728 | < 0.001 |
| T4_rt_mcc | M1 | 2.860 | 2.555 | 0.802 |
| T4_rt_mcc | M2 | 1.333 | 2.555 | < 0.001 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

### T1, day-ahead price

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 7.59 | 16.49 | −0.01 | 27.57 | 26,304 |
| B1 | 13.38 | 28.28 | −0.12 | 45.77 | 26,304 |
| M1 | 6.19 | 12.85 | −1.39 | 24.55 | 26,304 |
| M2 | 6.49 | 13.75 | −0.42 | 23.12 | 26,304 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_


MAE by calendar year of the validation days (2022: November and December; 2025: January to October).

| Year | B0 | M1 | M2 |
|---|---|---|---|
| 2022 | 16.01 | 13.53 | 14.02 |
| 2023 | 6.22 | 4.81 | 5.23 |
| 2024 | 5.40 | 4.55 | 4.70 |
| 2025 | 10.18 | 8.36 | 8.65 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

By season and hour group (MAE):

| Season | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 13.85 | 11.79 | 12.00 |
| MAM | 4.65 | 3.83 | 3.94 |
| JJA | 6.77 | 5.08 | 5.59 |
| SON | 5.18 | 4.14 | 4.53 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

| Hours | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 6.10 | 5.00 | 4.57 |
| 07-22 | 8.37 | 6.77 | 7.40 |
| 23 | 5.48 | 5.34 | 5.40 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

### T2, day-ahead posted congestion

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 0.73 | 3.40 | 0.00 | — | 26,304 |
| B1 | 0.81 | 3.54 | 0.00 | — | 26,304 |
| Z | 0.45 | 2.58 | −0.31 | — | 26,304 |
| M1 | 0.79 | 2.56 | −0.02 | — | 26,304 |
| M2 | 0.46 | 2.54 | −0.28 | — | 26,304 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_


MAE by calendar year of the validation days (2022: November and December; 2025: January to October).

| Year | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 2022 | 0.61 | 0.32 | 0.80 | 0.35 |
| 2023 | 0.58 | 0.37 | 0.83 | 0.39 |
| 2024 | 0.75 | 0.49 | 0.77 | 0.49 |
| 2025 | 0.91 | 0.53 | 0.77 | 0.54 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

By season and hour group (MAE):

| Season | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 0.73 | 0.44 | 0.73 | 0.45 |
| MAM | 0.39 | 0.22 | 0.50 | 0.23 |
| JJA | 1.34 | 0.84 | 1.36 | 0.86 |
| SON | 0.46 | 0.30 | 0.57 | 0.32 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

| Hours | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0.45 | 0.27 | 0.49 | 0.28 |
| 07-22 | 0.87 | 0.54 | 0.94 | 0.55 |
| 23 | 0.44 | 0.29 | 0.56 | 0.31 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

### T3, real-time integrated hourly price

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 17.58 | 45.95 | −0.23 | 59.40 | 26,304 |
| B1 | 18.95 | 47.57 | −0.28 | 61.38 | 26,304 |
| M1 | 12.61 | 34.18 | −4.21 | 56.60 | 26,304 |
| M2 | 12.20 | 33.38 | −2.19 | 47.85 | 26,304 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_


MAE by calendar year of the validation days (2022: November and December; 2025: January to October).

| Year | B0 | M1 | M2 |
|---|---|---|---|
| 2022 | 40.42 | 28.65 | 28.32 |
| 2023 | 13.94 | 9.63 | 9.77 |
| 2024 | 12.23 | 8.72 | 8.50 |
| 2025 | 23.81 | 17.66 | 16.34 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

By season and hour group (MAE):

| Season | B0 | M1 | M2 |
|---|---|---|---|
| DJF | 28.19 | 22.11 | 20.69 |
| MAM | 11.33 | 8.00 | 7.93 |
| JJA | 18.27 | 11.76 | 11.70 |
| SON | 12.68 | 8.71 | 8.59 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

| Hours | B0 | M1 | M2 |
|---|---|---|---|
| 00-06 | 11.91 | 9.16 | 8.67 |
| 07-22 | 20.42 | 14.29 | 13.93 |
| 23 | 11.89 | 9.99 | 9.26 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

### T4, real-time posted congestion

| Model | MAE | RMSE | Bias | MAE, top decile | Hours |
|---|---|---|---|---|---|
| B0 | 2.56 | 35.04 | 0.01 | — | 26,304 |
| B1 | 2.58 | 34.77 | −0.01 | — | 26,304 |
| Z | 1.33 | 24.60 | −1.12 | — | 26,304 |
| M1 | 2.86 | 24.69 | −0.53 | — | 26,304 |
| M2 | 1.33 | 24.60 | −1.12 | — | 26,304 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

M2's MAE differs from Z's (the zero forecast) by only 0.000 US$/MWh; the records do not keep the size of M2's forecasts. Under absolute loss, the conditional median of a mostly zero series is zero.

MAE by calendar year of the validation days (2022: November and December; 2025: January to October).

| Year | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 2022 | 12.77 | 6.67 | 8.20 | 6.67 |
| 2023 | 2.20 | 1.13 | 2.99 | 1.13 |
| 2024 | 1.28 | 0.67 | 2.54 | 0.67 |
| 2025 | 2.47 | 1.31 | 2.02 | 1.31 |

_(run `20261120T221928Z-validate-ba9571`, validation (seen))_

By season and hour group (MAE):

| Season | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| DJF | 4.72 | 2.47 | 4.20 | 2.47 |
| MAM | 0.57 | 0.29 | 1.46 | 0.29 |
| JJA | 4.30 | 2.21 | 4.29 | 2.21 |
| SON | 0.65 | 0.37 | 1.50 | 0.37 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

| Hours | B0 | Z | M1 | M2 |
|---|---|---|---|---|
| 00-06 | 0.82 | 0.47 | 1.46 | 0.47 |
| 07-22 | 3.40 | 1.76 | 3.57 | 1.76 |
| 23 | 1.22 | 0.59 | 1.32 | 0.59 |

_(run `20261121T002222Z-derive-9213d8`, validation (seen))_

## 90 % intervals

| Period | Target | Model | Coverage | Mean width (US$/MWh) | Hours |
|---|---|---|---|---|---|
| validation (seen) | T1_da_lbmp | M1 | 87.2 % | 23.64 | 18,288 |
| validation (seen) | T1_da_lbmp | M2 | 87.4 % | 23.14 | 18,288 |
| validation (seen) | T2_da_mcc | M1 | 89.1 % | 3.07 | 18,288 |
| validation (seen) | T2_da_mcc | M2 | 89.2 % | 1.96 | 18,288 |
| validation (seen) | T3_rt_lbmp | M1 | 87.0 % | 48.07 | 18,288 |
| validation (seen) | T3_rt_lbmp | M2 | 87.0 % | 44.20 | 18,288 |
| validation (seen) | T4_rt_mcc | M1 | 91.1 % | 9.82 | 18,288 |
| validation (seen) | T4_rt_mcc | M2 | 90.2 % | 1.91 | 18,288 |
| held out | T1_da_lbmp | M1 | 88.7 % | 42.38 | 8,760 |
| held out | T1_da_lbmp | M2 | 88.4 % | 46.36 | 8,760 |
| held out | T2_da_mcc | M1 | 88.1 % | 4.13 | 8,760 |
| held out | T2_da_mcc | M2 | 91.4 % | 2.51 | 8,760 |
| held out | T3_rt_lbmp | M1 | 84.6 % ¹ | 77.22 | 8,760 |
| held out | T3_rt_lbmp | M2 | 84.4 % ¹ | 77.95 | 8,760 |
| held out | T4_rt_mcc | M1 | 87.7 % ¹ | 4.79 | 8,760 |
| held out | T4_rt_mcc | M2 | 87.1 % ¹ | 1.45 | 8,760 |

Coverage is measured, never assumed; residuals are autocorrelated, so no finite-sample guarantee is claimed. The first 11 validation folds have no interval (330 days of residuals are required). ¹ Computed counting hours with no outcome as outside the interval: a scoring defect that understates coverage; see Limits. _(run `20261121T002222Z-derive-9213d8`, validation (seen))_ _(run `20261120T233440Z-replay-8359cd`, held out)_

## Value of a variable: the operator's load forecast

M1 with and without the load forecast (M1−LF); one-sided test "M1 lower". A p near 1 means the load forecast hurts. The admitted forecast is the one issued about 07:00 on D−2, 41 to 65 hours before the hours of D: this is the value of that vintage, not of a recent forecast as a desk would use.

- validation (seen), T1_da_lbmp: M1 6.193; M1−LF 6.796; the load forecast helps; p < 0.001 _(run `20261120T221928Z-validate-ba9571`, validation (seen))_
- validation (seen), T2_da_mcc: M1 0.793; M1−LF 0.761; the load forecast hurts; "M1−LF lower": p < 0.001, for information _(run `20261120T221928Z-validate-ba9571`, validation (seen))_
- validation (seen), T3_rt_lbmp: M1 12.613; M1−LF 12.781; the load forecast helps; p = 0.004 _(run `20261120T221928Z-validate-ba9571`, validation (seen))_
- validation (seen), T4_rt_mcc: M1 2.860; M1−LF 2.742; the load forecast hurts; "M1−LF lower": p < 0.001, for information _(run `20261120T221928Z-validate-ba9571`, validation (seen))_
- held out, T1_da_lbmp: M1 10.592; M1−LF 12.906; the load forecast helps; p < 0.001 _(run `20261120T233440Z-replay-8359cd`, held out)_
- held out, T2_da_mcc: M1 1.786; M1−LF 1.767; the load forecast hurts; "M1−LF lower": p = 0.073, for information _(run `20261120T233440Z-replay-8359cd`, held out)_
- held out, T3_rt_lbmp: M1 17.600; M1−LF 18.587; the load forecast helps; p < 0.001 _(run `20261120T233440Z-replay-8359cd`, held out)_
- held out, T4_rt_mcc: M1 1.238; M1−LF 1.197; the load forecast hurts; "M1−LF lower": p < 0.001, for information _(run `20261120T233440Z-replay-8359cd`, held out)_

## The monitor

| Model: target | Relative-error threshold | Bias band | Regime band | Days per state (held out) | Signal days: error / bias / regime / data | "Stop" days on data-signal days | First "stop" |
|---|---|---|---|---|---|---|---|
| M1:T1_da_lbmp | 1.03 | [−11.41, 3.01] | [2.6 %, 54.4 %] | stop trusting 1, trust 328, watch 36 | 1 / 37 / 0 / 0 | 0 / 1 | 2026-01-29 |
| M2:T1_da_lbmp | 1.05 | [−5.88, 4.81] | [2.6 %, 54.4 %] | stop trusting 81, trust 239, watch 45 | 84 / 107 / 0 / 0 | 0 / 81 | 2025-11-01 |
| M1:T2_da_mcc | 8.37 | [−0.73, 0.89] | [2.6 %, 54.4 %] | trust 291, watch 74 | 0 / 74 / 0 / 0 | 0 / 0 | — |
| M2:T2_da_mcc | 1.21 | [−1.32, 0.01] | [2.6 %, 54.4 %] | trust 186, watch 179 | 0 / 179 / 0 / 0 | 0 / 0 | — |
| M1:T3_rt_lbmp | 0.86 | [−33.80, 6.43] | [0.0 %, 18.6 %] | stop trusting 20, trust 318, watch 27 | 0 / 27 / 0 / 20 | 20 / 20 | 2026-07-06 |
| M2:T3_rt_lbmp | 0.81 | [−18.33, 9.54] | [0.0 %, 18.6 %] | stop trusting 45, trust 298, watch 22 | 39 / 31 / 0 / 20 | 20 / 45 | 2025-11-27 |
| M1:T4_rt_mcc | 12.52 | [−10.02, 1.75] | [0.0 %, 18.6 %] | stop trusting 20, trust 345 | 0 / 0 / 0 / 20 | 20 / 20 | 2026-07-06 |
| M2:T4_rt_mcc | 1.00 | [−11.66, 0.01] | [0.0 %, 18.6 %] | stop trusting 42, trust 236, watch 87 | 28 / 81 / 0 / 20 | 20 / 42 | 2026-01-24 |

_(run `20261120T233440Z-replay-8359cd`, held out)_

"Trust" means "behaving as in validation"; it says nothing about whether the model beats its baseline. Thresholds and bands come from the validation days (seen); the states from the held-out year. The "data" signal is on when an input is missing or more than 3 days old; in this replay, hours with no outcome also counted in the regime statistic. Rule: "stop" when two statistical signals are on together, when the relative error exceeds its threshold seven days running, or when the data signal is on. On the first held-out day, the 28-day window holds only errors of validation days; "stop" that day, with the signals on: M2:T1_da_lbmp (relative error, bias).

Signals on the validation days, where the thresholds were fixed (in sample):

| Model: target | Days per state (validation, in sample) |
|---|---|
| M1:T1_da_lbmp | no verdict (window not full) 28, stop trusting 22, trust 959, watch 87 |
| M2:T1_da_lbmp | no verdict (window not full) 28, stop trusting 30, trust 954, watch 84 |
| M1:T2_da_mcc | no verdict (window not full) 28, stop trusting 50, trust 961, watch 57 |
| M2:T2_da_mcc | no verdict (window not full) 28, stop trusting 36, trust 960, watch 72 |
| M1:T3_rt_lbmp | no verdict (window not full) 29, stop trusting 53, trust 956, watch 58 |
| M2:T3_rt_lbmp | no verdict (window not full) 29, stop trusting 42, trust 949, watch 76 |
| M1:T4_rt_mcc | no verdict (window not full) 29, stop trusting 48, trust 932, watch 87 |
| M2:T4_rt_mcc | no verdict (window not full) 29, stop trusting 58, trust 929, watch 80 |

_(run `20261120T233440Z-replay-8359cd`, validation days: in sample)_

What it can miss: a short spike (the 28-day window dilutes it); a change that degrades the model and the baseline alike (the ratio stays flat); drift slow enough to stay inside the thresholds; anything in its first 28 days. Its thresholds come from a validation period that straddles a change in the market, so its bands are wide and can miss a move inside them.

## Next-day revenue of a 5×16 block

Stated deal: **50 MW delivered into New York at the `HQ_GEN_WHEEL` bus, hours beginning 07:00 to 22:00 (16 hours), each weekday that is not a NERC holiday (the 5×16 block), sold day-ahead at the resulting LBMP.** This is a forecast of next-day gross revenue, not a desk valuation against forward prices, nor a trading result: no profit line.

Days: 255; value at the settled price: US$15,561,928; posted congestion's part of that value: US$192,220 (−50 MW × posted congestion; positive when posted congestion is negative).

| Model | Forecast value (US$) | Versus settled | Mean absolute daily error (US$) | Daily bias (US$) | 90 % band coverage |
|---|---|---|---|---|---|
| B0 | 15,318,557 | −1.6 % | 11,361 | −954 | 87.8 % (255 d) |
| M1 | 14,618,270 | −6.1 % | 7,860 | −3,701 | 88.6 % (255 d) |
| M2 | 13,170,798 | −15.4 % | 13,632 | −9,377 | 88.2 % (255 d) |

By month (value, US$):

| Month | Settled | B0 | M1 | M2 | M1 band coverage | Days |
|---|---|---|---|---|---|---|
| 2025-11 | 911,244 | 877,956 | 860,615 | 782,033 | 100.0 % | 19 |
| 2025-12 | 1,926,044 | 1,845,620 | 1,783,798 | 1,679,735 | 77.3 % | 22 |
| 2026-01 | 3,647,658 | 3,626,504 | 3,114,221 | 1,930,379 | 52.4 % | 21 |
| 2026-02 | 1,881,414 | 2,044,488 | 1,949,094 | 2,042,696 | 55.0 % | 20 |
| 2026-03 | 887,487 | 885,080 | 878,524 | 878,847 | 100.0 % | 22 |
| 2026-04 | 755,468 | 729,112 | 707,003 | 691,052 | 100.0 % | 22 |
| 2026-05 | 678,508 | 675,507 | 665,188 | 680,667 | 100.0 % | 20 |
| 2026-06 | 919,868 | 850,139 | 916,273 | 864,338 | 100.0 % | 22 |
| 2026-07 | 1,456,198 | 1,329,080 | 1,327,922 | 1,181,558 | 78.3 % | 23 |
| 2026-08 | 926,654 | 894,666 | 891,593 | 927,478 | 100.0 % | 21 |
| 2026-09 | 778,694 | 780,714 | 746,896 | 766,884 | 100.0 % | 21 |
| 2026-10 | 792,692 | 779,690 | 777,142 | 745,131 | 100.0 % | 22 |

Congestion part as forecast by the T2 models (total; mean absolute daily error, US$): B0 184,770 (877); M1 −106 (972); M2 1,265 (782); settled: 192,220.

_(run `20261120T233440Z-replay-8359cd`, held out)_

Assumptions: the block clears in full as a price taker; no transmission, wheeling, uplift or other charges on either side of the border; no capacity value; US dollars. The report does not claim that anyone can schedule this block. Gross revenue: the cost of energy on the Québec side and the real-time balancing risk if the import is cut are not in it. The price-taker assumption holds least when the interface binds for imports, which is when the price is low. M1 and M2 are median-type forecasts; on prices skewed upward, their sum understates the expected value. The price used is the "H Q" zone price; which proxy bus (`HQ_GEN_IMPORT` or `HQ_GEN_WHEEL`) an ordinary import is scheduled at was not established.

## Limits

- **Missing outcomes.** T3_rt_lbmp, T4_rt_mcc: 456 hours with no outcome (2026-07); scored on 8,304 hours. The operator's monthly archive for July 2026 (list P-4A, real time), as fetched, passes an integrity test and holds only 12 of 31 daily files (the 19th and the 21st to the 31st; archive file listing on 2026-11-21, not a tracked run). Fetched again on 2026-11-22: still 12 files; the days are missing at the source. Two of the replay's computations count these hours wrongly: interval coverage (counted as outside the interval, which understates coverage) and the Brier score of P2 and P0 (counted as "no congestion"). The owner allowed a second replay with the fixed scoring: see "Departure from the plan".
- **A break inside the held-out year.** The Champlain Hudson Power Express line (CHPE, 1,250 MW, Québec to New York City) entered commercial operation on 2026-05-13 and was out from 2026-07-04 for most of July (S&P Global; GCN; MIT Technology Review: public sources, not a tracked run). The training data never saw it. The July days without real-time prices overlap that outage: T3 and T4 are scored without the summer's hardest real-time days.
- **What the baselines measure.** B0 for T3 is the real-time price two days earlier; M1 and M2 have day-ahead prices among their inputs, so their gain on T3 may be mostly day-ahead information. A "day-ahead price as the real-time forecast" baseline and the day-ahead − real-time spread, the actual decision between the two markets, were not registered and are not scored. T3 and T4 at 05:00 the day before do not forecast what a real-time scheduler sees, who decides about 75 minutes before the hour. B0 takes the previous day every day (Monday from Sunday); the usual naive benchmark takes D−7 on Monday, Saturday and Sunday.
- **The choice of loss.** Under absolute loss, the zero forecast is nearly unbeatable on a mostly zero series: "no model beats Z" is partly a property of the loss. Under squared error, M1 is slightly below Z on T2 (RMSE 8.87 against 8.95) _(run `20261120T233440Z-replay-8359cd`, held out)_, untested.
- **Archive stamps.** Their agreement with the operator's "Last Updated" column was checked on one day, in standard time; summer time was not checked. If the operator rebuilt a monthly archive with corrected values while keeping the original stamps, a corrected value would enter unseen; that case was not tested.
- **No profit line.** NYISO's training material describes virtual bidding at the zonal level, with internal-zone examples; no document read shows a virtual bid point at an external proxy bus. Who can schedule an import at `HQ_GEN_WHEEL`, and at what cost on both sides, was not established.
- **B0 is a floor, not a desk benchmark.** No weather, gas prices, outages or interface limits are admitted; the models are statistical, not fundamental.
- **Corrected values.** The archive holds corrected prices; a corrected file that kept its original stamp would let a corrected value in. NYISO's price-validation group reported no day-ahead price correction from 2007 to September 2017, and 78 market days with real-time corrections from 2013 to September 2017 (NYISO, MIWG, 2017-11-02); corrections after October 2017 are not known.
- **Procedural separation.** The held-out year was already past when this work was done; its separation rests on a fence on the fetch, the tag and the ledger. The authors' general knowledge of the 2025–26 winter cannot be excluded. The order of events (plan, tag, replay) can be checked only through this repository's history, whose dates the author sets; no external timestamp attests it.
- **No independent validation.** The model, the checks and this report come from AI agents working for one owner; reviews by other models are not independent validation. One held-out year; no periodic review.

## Sibling project

[valiwatt](https://github.com/MrRolie/valiwatt) validates and monitors a forecast of Québec's hourly electricity demand: the demand side. This repository covers the price at the New York border: the market side.
