# Plan: the price at the border (piece `hq-price`), version 1

Written 2026-11-20, before any price of the held-out period was fetched, and before any full validation run.
It is frozen by the git tag `plan-v1`, which covers this page and `pieces/hq-price/plan.toml`. The held-out
replay refuses to run unless both files equal their content at that tag. A test fails if the code's constants
differ from `plan.toml`. Any change after the tag is a departure: it is recorded in `docs/departures.md`, shown
in the report, and allowed only by the repository's owner. The facts this plan rests on, with their sources,
are in `docs/problem.md`.

One fresh-context review of the draft was made before the tag, and every change it led to is in this text.
Two of them rest on numbers from the validation window, said here so no reader has to infer it:
- the reviewer measured on the validation window that a zero forecast of T2 has a lower MAE than B0 (0.45
  against 0.73 $/MWh), which is why Z decides for T2;
- before the tag, the author ran one validation fold (2024-07) of T1 and T2 as a smoke test of the code.
Neither number changed a model or a hyperparameter.

## 1. Targets

At the location `H Q` (PTID 61844), whose price equals that of the proxy generator bus `HQ_GEN_WHEEL`
(PTID 23651), for each hour of operating day D:

| Id | Target | Source file |
|---|---|---|
| T1 | Day-ahead LBMP | P-2A `damlbmp_zone` |
| T2 | Day-ahead posted congestion ("Marginal Cost Congestion", posted sign) | P-2A |
| T3 | Real-time time-weighted/integrated hourly LBMP | P-4A `rtlbmp_zone` |
| T4 | Real-time posted congestion | P-4A |

All four are registered. T3 and T4 may be dropped only before their first validation score exists, with the
drop and its time recorded in `docs/departures.md` (it narrows the scope, so it is shown, not hidden); after
that, they run on the held-out year with the others. A dropped target is reported as "registered, not run".
No target is added after the tag.

The posted price is energy + losses − posted congestion (measured, `problem.md` §5).

## 2. Decision time and admitted inputs

Decision time for every target of operating day D: **05:00 Eastern prevailing time on D−1** (M-11 §2.2,
MST 4.2.1.1). Horizon: the 23, 24 or 25 hours of D, 19 to 43 hours after the decision.

**Admission.** A file is admitted for a decision only if its archive entry time, read as Eastern prevailing
time (an ambiguous autumn hour takes the later reading), is at least 60 minutes before the decision time. A
lag slot whose file does not qualify is filled in place with the latest earlier day whose file does; the other
slots do not shift.

**Hours.** Hours of day are local hour-beginning, 0 to 23. In a 24-slot feature block, the spring day's
missing 02:00 slot copies 01:00, and the autumn day's two 01:00 values are averaged. As a target, every actual
hour is forecast and scored; the second 01:00 of the autumn day is forecast by the hour-1 model.

**Inputs** (the blocks each target uses are listed in §5):
- day-ahead LBMP and posted congestion at `H Q`, lag days D−1, D−2, D−3, D−7 (24 slots each);
- real-time LBMP and posted congestion at `H Q`, lag days D−2, D−3, D−4, D−7 (24 slots each; D−1 is never
  complete at the decision time);
- day-ahead LBMP at `NORTH` and at `N.Y.C.`, lag day D−1 only (24 slots each);
- the ISO load forecast (P-7), the latest qualifying issue (normally the file named D−1), its hours of D, for
  `NYISO` (the total), `North` and `Capitl` (24 slots each);
- calendar: day of week (7 dummies) and a NERC holiday dummy. NERC holidays: New Year's Day, Memorial Day,
  Independence Day, Labor Day, Thanksgiving Day and Christmas Day; one falling on a Sunday is observed on the
  Monday, one falling on a Saturday is not moved.

Nothing else is admitted. Weather, fuel prices, outages and interface limits are out of this piece. Real-time
prices are inputs of T3 and T4 only.

**Corrected values.** The archive holds corrected values where the operator corrected a price, under the
original or a later stamp (`problem.md` §5). Where the stamp is later, the rule above refuses the file until
then. Where a corrected file kept an on-time stamp, the corrected value enters a feature; this cannot be seen
in the archive, and the report states it as a limitation, with the operator's correction counts.

**Guards.** A guard refuses any design row in which a feature's file entry time is not at least 60 minutes
before the row's decision time. A guard refuses any fit using a training label whose entry time is not before
the fit's decision time (§4). Scores use realised targets and are exempt by name. Each guard has a test that
breaks it on purpose and shows it firing.

## 3. Periods

| Period | Operating days | Use |
|---|---|---|
| Training history | 2016-01-15 onward | fitting |
| Validation | 2022-11-01 to 2025-10-31, 36 monthly folds | model development (no tuning), thresholds, intervals |
| Held out | 2025-11-01 to 2026-10-31 | touched once, for every model run, together |

Prices from 2025-11-01 onward have never been fetched. The fetcher refuses them unless the held-out replay
calls it, after it has checked the tag. Prices from 2026-11-01 onward are not used by this plan.

## 4. Walk-forward, purge and embargo

Each fold is one calendar month of operating days. Every model is refitted once at the start of each fold, on
training samples admitted at the decision time of the fold's first day. It forecasts every day of that month
from that day's own admitted inputs. The held-out year uses the same monthly refit.

- **Purge**: a training sample (operating day d, all its hours) is used only if the entry time of its target
  file is at least 60 minutes before the decision time of the fold's first day. For day-ahead targets this keeps days up to T−1,
  where T is the fold's first day; for real-time targets, normally up to T−2. Sized to the horizon: no training label is newer than what the forecaster
  held.
- **Embargo**: 7 days, the longest feature lookback. It applies to any training sample that would follow a test
  fold. In this forward-only scheme no fit uses such a sample. A guard refuses any fit with a training day on or
  after the fold's first day, so the embargo is enforced as a refusal, not assumed.

## 5. Models

Hyperparameters are fixed here; nothing is tuned on the validation folds.

| Id | Model | Targets | Role |
|---|---|---|---|
| B0 | The same hour of the latest lag day of the same market: D−1 for T1, T2; D−2 (its slot) for T3, T4 | all | the baseline that decides "better" for T1, T3 |
| B1 | The same hour of D−7 in the same market | all | reported only |
| Z | Zero for every hour | T2, T4 | the baseline that decides "better" for T2, T4 |
| M1 | LEAR-style LASSO (below) | all | competing model |
| M2 | Gradient-boosted trees (below) | all | competing model |
| P0 | Probability that the posted congestion is non-zero (absolute value above 0.005 $/MWh): the share of non-zero hours at the same local hour over the latest 28 admitted days | T2, T4 event | baseline for the probability |
| P2 | `HistGradientBoostingClassifier` with M2's settings and features, for the same event | T2, T4 event | competing probability model |

Why Z decides for T2 and T4: the posted congestion is zero in most hours, and persistence pays twice for every
isolated spike. A zero forecast beats B0 by a wide margin, so beating B0 alone would prove nothing.

**M1.** One `LassoLarsIC` (criterion AIC) per local hour of the day, fitted on the latest 728 admitted days.
Features: for T1, the `H Q` day-ahead LBMP block (4 lag days × 24); for T2, the `H Q` day-ahead posted
congestion block (4 × 24); for T3, the `H Q` real-time LBMP block and the `H Q` day-ahead LBMP block (2 × 4 × 24);
for T4, the `H Q` real-time and day-ahead posted congestion blocks (2 × 4 × 24); for all, `NORTH` and `N.Y.C.`
D−1 (2 × 24), the load forecast (3 × 24), and the calendar (8). That is 224 features for T1 and T2, 320 for T3
and T4. Price-like columns (the `H Q`, `NORTH` and `N.Y.C.` blocks) and the target are centred on their median
and divided by their MAD (all `H Q` blocks, real-time ones included). Where the MAD is zero, the standard deviation is used, and where that is zero, 1. Then
asinh is applied. Load-forecast columns are centred and scaled the same way, without asinh; calendar columns
are left as 0/1. Every centre and scale is per column, fitted on the training window only, and applied
unchanged at forecast time. Forecasts are transformed back with sinh. If a per-hour fit
fails or its training target is constant, that hour's forecast is the training median of its target, and the
run record counts such hours.

**M2.** `HistGradientBoostingRegressor`, loss `absolute_error`, `max_iter=400`, `learning_rate=0.05`,
`max_leaf_nodes=31`, `min_samples_leaf=40`, `l2_regularization=1.0`, `random_state=0`, no early stopping. One
model for all hours: the same columns as M1 for the target, untransformed, plus the local hour (0–23) as a feature.
Training: all admitted days from 2018-01-01.

**Intervals.** For M1 and M2, a 90 % interval for each hour: the forecast plus the 5 % and 95 % quantiles,
for that local hour, of the model's own walk-forward residuals. The residuals used are those of the latest
365 days whose target entry time precedes the decision time of the fold's first day, earlier held-out days
included. A fold gets no interval unless at least 330 such days exist; the first 11 validation folds therefore
have none. Coverage is measured, never assumed; the residuals are autocorrelated, so no finite-sample guarantee
is claimed.

## 6. Scores and the rule that decides "better"

Scores, per target and model, over all hours: MAE (primary), RMSE, mean error (bias); for T1 also MAE over the
hours whose realised price is in the top decile of the period. For P0 and P2: the Brier score. For intervals:
coverage and mean width.

**Rule.** On the held-out year, a model beats its deciding baseline (B0 for T1 and T3, Z for T2 and T4, P0 for
P2) if both hold:
1. its loss (MAE; Brier for P2) over the held-out year is lower than the baseline's;
2. a one-sided Diebold–Mariano test on the daily mean losses rejects "not lower" at 5 % after a Holm
   correction over the family of every (model, target) pair run: {M1, M2} on each of T1–T4 and P2 on T2 and
T4, ten pairs if all four targets run; a dropped target's pairs leave the family. The daily loss is the mean
   over the day's hours of the absolute error (squared error of the probability for P2); the differences are
   model − baseline. The long-run variance uses a Bartlett kernel with 7 lags. The statistic gets the
   Harvey–Leybourne–Newbold small-sample correction for horizon h = 1 day, and its p-value comes from Student's
   t with n − 1 degrees of freedom. If the long-run variance is not positive (a model identical to its baseline),
the test does not reject.

For T2 and T4, the report also shows each model against B0, for information only.

A model that does not beat its baseline is reported as such, as plainly as one that does. The validation folds
produce the same scores, labelled "validation (seen)", and never decide the rule.

## 7. The worked deal

A stated deal, valued at each decision time over the held-out year from the T1 forecasts of B0, M1 and M2:
**50 MW delivered into New York at `HQ_GEN_WHEEL` in every hour beginning 07:00 to 22:00 (16 hours) of each
weekday that is not a NERC holiday, sold in the day-ahead market at the day-ahead LBMP.** For each day:
- its forecast value, Σ 50 MW × forecast price;
- a 90 % band: the forecast value plus the 5 % and 95 % quantiles of the same deal's earlier daily value
  errors (settled − forecast), over the same residual window as the intervals of §5 (at least 200 deal days
  required);
- the value at the settled price;
- the part of the value that is posted congestion, −50 MW × Σ posted congestion over the block, settled and
  as forecast by the T2 models (the identity of §1).

Over the year: forecast against settled value, by month, and the band's coverage.

Assumptions: the block clears in full as a price taker; no transmission, wheeling, uplift or other charges on
either side of the border; no capacity value; prices in US dollars. Nobody's ability to schedule the block is
claimed (`problem.md` §6). This is a valuation, not a trading result. There is no profit line.

## 8. The monitor

The monitor runs daily over the held-out year, for M1 and M2 on each target run. It uses only errors whose
target entry time precedes that day's decision time.

| Signal | Statistic over the latest 28 such days | On when, threshold fixed from the validation days |
|---|---|---|
| Relative error | model MAE / deciding baseline MAE (B0 for T1, T3; Z for T2, T4) | above the 95th percentile |
| Bias | mean error | outside the 2.5th–97.5th percentiles |
| Regime | T1, T2: share of hours with non-zero posted day-ahead congestion; T3, T4: share of real-time hours with a price at or below zero | outside the 1st–99th percentiles |
| Data | an admitted input missing, or a lag slot filled from a day more than 3 days older than its own | any occurrence |

State: *no verdict* until 28 days of errors are known; *trust* when no signal is on; *watch* when exactly one
statistical signal is on; *stop trusting* when the relative-error signal has been on for 7 consecutive days,
or when two statistical signals are on together, or when the data signal is on. The monitor recommends; it
never acts. If the baseline's MAE over a window is zero, the relative-error statistic is not computed for that
day and the signal is off; the record counts such days (none occurred on the validation window, where the
smallest 28-day MAE of Z was 0.025 $/MWh day-ahead and 0.058 real-time).

What it can miss, stated in the report: a short spike (the 28-day window dilutes it); a change that degrades
the model and the baseline alike (the ratio stays flat); drift slow enough to stay inside the thresholds;
anything in its first 28 days. Its thresholds come from a validation period that straddles a change in the
market (`problem.md` §5), so a band fitted across both regimes is wide and can miss a move inside it. Its
signals on the validation days, where the thresholds were fixed, are reported as in sample.

## 9. Robustness and the value of a variable

Reported for the validation folds and for the held-out year, none of them used by the rule of §6:
- scores by year, by season (Dec–Feb, Mar–May, Jun–Aug, Sep–Nov), by hour group (00–06, 07–22, 23) and, for T1,
  by realised price decile;
- **value of the load forecast**: M1 refitted without the load-forecast columns (M1−LF), its MAE against M1's
  and the same Diebold–Mariano test (one-sided, "M1 lower"), as a test of that variable's predictive value.

## 10. Records and versions

Every run writes a record: run id, git commit and whether the tree was clean, the `plan-v1` tag check, the
SHA-256 of every raw file read, package versions, the plan values, the scores, the SHA-256 of the forecasts
file, and the label of each number (in sample, validation (seen), held out). The report prints no number that
it cannot trace to a run record, and refuses to render otherwise. Run records are kept in `runs/` and
committed. Raw data, forecasts and fitted models are not committed; their hashes are. The held-out replay is
recorded in `docs/replay-ledger.json`. A second replay is refused without `--departure`, which also writes the
departure.

## 11. Order of work

1. Loader, admission, guards and their breaks.
2. B0, B1, Z, M1, M2, P0, P2 on T1 and T2 over the validation folds; intervals; M1−LF. Then T3 and T4, or
   their recorded drop.
3. Monitor thresholds from validation; the deal on validation.
4. One held-out replay of every model run, together.
5. Bilingual report (French first, then English), rendered from the run records.

Every model listed in §5 for each target run runs on the held-out year. If one must be dropped, the drop is recorded
with a time earlier than its first validation score, or it is a departure.
