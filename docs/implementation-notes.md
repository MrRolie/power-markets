# Implementation decisions taken after the tag `plan-v1` and before the held-out replay

None changes `docs/plan.md` or `pieces/hq-price/plan.toml`. Each fills a case the plan leaves undefined or
fixes code that did not do what the plan says. All were made before any held-out price was fetched. The
validation and rehearsal runs were made again after them; the earlier runs stay in `runs/` and are superseded.

From the pre-replay code review (2026-11-20):

- **P0 window (plan §5).** P0 now averages the latest 28 days whose target file was posted at least 60 minutes
  before the decision. Before, it took 28 consecutive days ending at the latest admitted day, so a late-posted
  day inside the window counted. That affected 114 of 1,056 validation decision days on T4 and none on T2.
- **M1 with a missing input (plan §5 leaves it undefined).** A forecast row with a missing feature value gets
  that hour's training median, as for a failed fit; a training day with a missing value is left out of the
  fit. Neither occurred in validation.
- **Monitor data signal (plan §8).** It is now built from each target's own inputs, and a missing input sets it.
  Before, one flag was built from all inputs, so a real-time file posted late set the signal for the day-ahead
  targets, which do not use real-time inputs.
- **Monitor state runs (plan §8).** States are computed once over the validation and held-out days, so a run
  of relative-error days is not cut at the period boundary.
- **Replay gates (plan §10).** Every check that can fail (targets equal the registered set, raw data present, the
  prior run's forecasts match its record) runs before the ledger is written or anything is fetched. After the
  fetch the ledger is marked `fetched`, and any later replay is refused without `--departure`, which also writes
  `docs/departures.md`.
- **Records (plan §10).** Each run record lists the SHA-256 of every raw file read, not only a digest of the list.
- **Direction of the load-forecast test (plan §9).** Records store the test "M1 lower than M1−LF".

After the held-out replay (2026-11-21). These change code for future runs; no held-out number was recomputed.

- **Missing outcomes.** The July 2026 real-time archive holds 12 of 31 daily files, so 456 held-out hours of T3
  and T4 have no outcome. The replay's interval coverage counted those hours as misses, and its Brier scores and
  monitor regime shares counted them as "no congestion" or "above zero". The code now leaves an hour with no
  outcome out of every score and records the count of such hours. Re-scoring the held-out year with the fixed code
  is the owner's call and would be a departure.
- **Validation robustness (plan §9).** The validation run recorded robustness by year only. A `derive` run
  re-scores the saved validation forecasts, after checking each file against its record's hash, to add season,
  hour group and price decile. It refuses held-out records.
- **Second replay (departure, 2026-11-22).** The owner allowed re-fetching July 2026 and replaying the held-out
  year with the fixed scoring. The re-fetched archive still holds 12 of 31 daily files, so only the scoring
  changed; the forecasts are identical. That run's record marks the tree dirty at its start: the replay command
  checked the tree clean, then wrote its own ledger entry, then took the snapshot the record keeps. The record now
  keeps the state checked before the ledger write.
