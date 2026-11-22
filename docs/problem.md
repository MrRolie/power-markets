# The price at the border: what the spike learned (2026-11-20)

The spike read the operator's documents and its public archive from 2016-01 to 2025-10. It never fetched a
price file for 2025-11 or later: the fetcher refused any month on or after 2025-11 before touching the
network, and a test shows the refusal. The product is built from this page and from `plan.md`, never from the
spike's code (folder `spike/`, kept as reference).

Sources are cited by the operator's own section numbers:
- **MST**: NYISO Market Administration and Control Area Services Tariff, full PDF as read on 2026-11-20
  (<https://nyisoviewer.etariff.biz/ViewerDocLibrary/MasterTariffs/9FullTariffNYISOMST.pdf>, sections
  effective up to 2026-09-16).
- **M-11**: NYISO Manual 11, Day-Ahead Scheduling Manual, version 10.1, effective 2026-09-03.
- **Virtual trading course**: NYISO Market Training, "Virtual Trading", New York Market Orientation Course,
  October 2026.

## 1. What "H Q" is

The zonal files carry fifteen names: eleven New York load zones and four external zones, among them `H Q`,
PTID 61844. The tariff says the external zonal prices are posted "for informational purposes only" and that
"each external zonal LBMP is equal to the LBMP of the Proxy Generator Bus associated with that external zone";
for `HQ` that bus is `HQ_GEN_WHEEL`, PTID 23651 (MST 17.1, table of external zones). Settlements for external
transactions use the proxy generator bus price, so the series forecast here is the price at that bus.

Hydro-Québec has several proxy generator buses (MST 4.4.4 table, page 140): `HQ_GEN_IMPORT`, `HQ_GEN_WHEEL`,
`HQ_GEN_CEDARS_PROXY` (the Dennison scheduled line), `HQ_CHPE_GEN` (Champlain Hudson Power Express) and their
load counterparts. **Every one of them is marked Non-Competitive.** `HQ_GEN_WHEEL` is hourly scheduled.

## 2. How the price is built, and the sign of congestion

The tariff writes the price at a bus as the reference-bus energy price plus a losses component plus a
congestion component, `γi = λR + γLi + γCi`, with `γCi = −Σk GFik μk` (MST 17.1.1).

The posted files have three numbers per hour: the price, "Marginal Cost Losses" and "Marginal Cost Congestion".
Which sign the posted congestion column carries is measured in section 5, not assumed.

At a non-competitive proxy bus, the real-time price follows special rules (MST 17.1.6.3.3). When the
fifteen-minute look-ahead (RTC15) finds the interface constrained for imports, then if the RTC15 bus price is
positive the real-time price is the dispatch price plus "External Interface Congestion"; otherwise the
real-time price is the minimum of the dispatch price and zero. When such a rule sets the price to zero, the
congestion component is redefined as minus the sum of energy and losses (MST 17.1.6.5). So at this location
the real-time congestion component partly records an administrative rule, not only flow limits. The model and
the monitor must treat a real-time price pinned at or below zero as a regime, not as noise.

## 3. Decision times

**Day-ahead.** "Finalized Day-Ahead bids must be submitted by 05:00 a.m. (or by 4:50 a.m. for some External
Transaction bids pursuant to MST Section 4.2.1.1) on the day prior to the Dispatch Day" (M-11 §2.2). The 4:50
list in MST 4.2.1.1 names the Cross-Sound, Neptune, Linden VFT and HTP scheduled lines and the Champlain Hudson
Power Express; `HQ_GEN_WHEEL` is not among them. **Decision time for the day-ahead forecast of operating day D:
05:00 Eastern prevailing time on D−1.** The forecast covers the hours of D, 19 to 43 hours ahead.

The day-ahead results are posted "by 11:00 a.m. on the day prior to the Dispatch Day" (M-11 §2.2). In the
archive, each daily day-ahead file's zip entry time is the morning of D−1 (section 5 gives the distribution).
So at the decision time for D, the day-ahead prices of D−1 and earlier are known.

**Real-time.** The real-time forecast is made at the same decision time, 05:00 on D−1, for the hourly
integrated real-time price of each hour of D. Reason: the decision this serves is the day-ahead one (what to
offer at the border, whether day-ahead or real-time pricing is expected to be higher), and that decision is
taken at the day-ahead deadline. A forecast made closer to real time (the hour-ahead bid close) is a different
product and is not built here.

The target is the operator's own **time-weighted/integrated hourly real-time zonal price** (list P-4A), not an
average the project computes from the 5-minute file. A day's real-time file carries an archive time near the
end of that day (section 5). At 05:00 on D−1 the last complete real-time day is D−2; the hours of D−1 before
05:00 are not admitted (the earlier time is used where the posting time of a partial day is not established).

## 4. Inputs and their availability at the decision time

| Input | Known at 05:00 on D−1 | Evidence |
|---|---|---|
| Day-ahead prices and components, days ≤ D−1 | yes | M-11 §2.2 posting by 11:00 on D−2; archive entry times |
| Real-time integrated prices, days ≤ D−2 | yes | archive entry times near the end of each day |
| Real-time prices, hours of D−1 | no | not complete; not admitted |
| Calendar, NERC holidays | yes | fixed in advance |
| NYISO load forecast (list P-7) | see section 5 | "posted to the NYISO website by 08:00 a.m. every day, or as soon thereafter as is reasonably possible" (M-11 §6.2.1) |
| Weather, fuel prices, outages, interface limits | not admitted in this piece | no free archive with issue times was established in the spike |

Corrections: the operator marks dates with corrected prices on its list pages and states that "updated
historical LBMPs have been posted in the archived files section". The archive fetched in 2026 therefore holds
corrected values where corrections were made; the value as first posted is not recoverable from it. This
affects lagged price inputs and targets alike and is a stated limitation.

## 5. Measurements on the fenced archive

Measured by `spike/explore.py` and `spike/lags.py` (folder `spike/`, outputs in `spike/out/`) over
2016-01-01 to 2025-10-31: 3,592 operating days per product.

**Sign of the posted congestion column.** For each hour, `LBMP − losses + posted congestion` is the same for
all fifteen names to within 0.02 $/MWh (the files' rounding) at the 99th percentile of hours, day-ahead and
real-time. With the other sign, the spread across names reaches 269 $/MWh (day-ahead) and 556 $/MWh
(real-time) at the 99th percentile. So **the posted price is energy + losses − posted congestion**: the posted
column is the tariff's congestion component with its sign reversed. This piece forecasts the posted column,
under its posted sign, and states this identity wherever it is shown. A positive posted value at `H Q` lowers
the price there relative to the reference bus.

**Clock changes.** Time stamps are hour-beginning in Eastern prevailing time. The spring day has 23 rows
(02:00 missing); the autumn day has 25 rows with 01:00 written twice and nothing to tell the two apart but
their order. The loader must map rows to UTC by order on those days, and must fail if a day has any other
count.

**Posting times.** The monthly archives carry an entry time for each daily file:

| File | Median entry time | Entries stamped after 05:00 on F (the decision time for F+1) |
|---|---|---|
| Day-ahead prices, day F | 09:33 on F−1 (14.4 h before F) | 1 of 3,592 |
| ISO load forecast named F (covers F to F+5, 144 hours) | 07:05 on F−1 (16.9 h before F); 99th percentile 09:00 on F−1 | 33 of 3,592 (24 of them stamped 05:00:xx on F, seconds after that decision time) |
| Real-time integrated prices, day F | 23:57 on F (24.0 h after F starts) | not applicable: the next table row |

For real-time files, 160 of 3,592 are stamped after 05:00 on F+1, the decision time for which F is the latest
real-time day that could qualify.

These times agree with the operator's stated schedule (day-ahead by 11:00, load forecast by 08:00) and with the
"Last Updated" column of the live list pages read on 2026-11-20 (`spike/out/listing-2026-11-20.json`): the
day-ahead file for F shows F−1 at 09:32–09:33 for each of the eleven days listed, and the load forecast for F
shows F−1 at 07:10–09:00. The same table row reading also places the day-ahead file for 2026-11-21 on 2026-11-20,
which can only be a posting on the day before, so the load-forecast reading "file F issued on F−1" follows from
the same row structure.

What the entry time does and does not prove:
- It moves when a file is rewritten: the real-time file of 2026-11-20 showed "Last Updated" 14:07 on that day,
  while earlier real-time days show 23:57, and the file of 2026-11-19 still showed 23:57 a day later. A
  real-time file is rewritten through its day; its last stamp, 23:57, falls before the end of its own last hour.
  The real-time price is an ex ante computation (MST 17.1.1), so the last hour's prices may exist before the hour
  ends; the spike did not establish this. A stamp therefore bounds when a file was last written, not when its
  last hour became final.
- The tariff allows corrections after the fact: a day-ahead price can be corrected up to two business days
  after its operating day, a real-time price up to four (MST 20.3). Those windows run past the decision times
  at which such prices are admitted. No list page read on 2026-11-20 marked a corrected date, so how a corrected
  file is stamped in the archive was not observed. A late stamp is consistent with a corrected file, but the
  spike did not show it.
- How often it happens: the operator's price-validation group reported that "There have been no Day-Ahead
  price corrections since NYISO started performing price validation function in-house in 2007", with its
  counts of real-time corrections from 2012 to 2017-09-30 (NYISO, "Proposed Revision to Price Correction
  Deadlines", Market Issues Working Group, 2017-11-02). No count after that date was found.
- **Stated limitation**: a corrected value may enter a feature with its original, on-time stamp; the archive
  cannot show the uncorrected value. For day-ahead prices the operator reported no correction from 2007 to
  2017-09. For real-time prices it reported 78 market days with corrections from 2013 to 2017-09-30, each
  processed within one to four days (same source): about 16 a year, close to the 160 late real-time stamps
  in ten years of the archive (section 5 table), which is consistent with late stamps being corrections but
  does not prove it. Real-time lag features of the real-time targets carry this risk. Corrections from 2017-10 to
  2025-10 are not known from the sources read.

**Rule: a file is admitted for a decision only if its archive entry time, read as Eastern prevailing time
(an ambiguous autumn hour takes the later reading), is at least 60 minutes before that decision time.** The
margin changes the admission of no typical file: no day-ahead or load-forecast file is stamped within 5 hours
before its deadline. A file that does not qualify is replaced in its slot by the latest earlier file that does.

Consequences for the day-ahead decision for D (05:00 on D−1):
- day-ahead prices of D−1 are admitted (posted about 09:33 on D−2);
- the ISO load forecast admitted is the file named D−1, issued about 07:05 on D−2; its hours of D are 41 to 65
  hours after its issue (19 to 43 hours after the decision). The file named D is issued on the morning of D−1,
  after the deadline, and is not admitted;
- real-time prices of D−2 are admitted on about 95.5 % of days; they are inputs of the real-time targets only
  (plan §2), because the real-time stamp is the weakest of the three.

**The location.** Ten years of hourly day-ahead prices at `H Q`, yearly means from 14 $/MWh (2020) to 52 $/MWh
(2025 to October). It follows `NORTH` closely (correlation 0.974, mean difference +0.89 $/MWh). Autocorrelation
of the day-ahead price at 24, 48 and 168 hours: 0.84, 0.74, 0.60.

**Congestion at `H Q`.** The day-ahead posted congestion is non-zero in 31–51 % of hours in 2016–2022 and in
15–19 % in 2023–2025; its 1st and 99th percentiles in 2025 are −2.5 and +7.0 $/MWh. It is mostly zero, with
rare, larger values. A point forecast of it under absolute error is dominated by the zeros; the plan scores it
also as a probability that congestion is non-zero.

**The real-time floor regime.** The share of real-time hours at `H Q` with a price at or below zero was 4.9 to
13.0 % each year from 2016 to 2023 and 0.4 to 0.6 % in 2024 and 2025. This is consistent with the non-competitive
pricing rule of section 2 (an import-constrained interface pins the price at or below zero) occurring far less
often; a dispatch price at or below zero with no interface constraint gives the same observation, and the two
were not separated. Why
it changed is not established from the operator's documents here; a change in the flows over the interface is
one candidate. The validation period (2022-11 to 2025-10) straddles the change, which the report must show by
year.

**Day-ahead minus real-time at `H Q`.** Over the ten years, a mean of +0.94 $/MWh with a standard deviation of
34.4 $/MWh (hourly).

## 6. Can a position be taken at this location?

- **Virtual trading**: the tariff defines a Virtual Transaction as a bid "submitted at a load bus specified
  for Virtual Transactions" (MST 2, definitions). The operator's training material describes virtual bidding as
  done "at the zonal level", with bids "submitted at the bus level specific to a zone", and gives its examples
  by internal zones (Virtual trading course, slides 17–21). No document read shows a virtual bus at an external
  proxy bus. So a day-ahead/real-time spread at `H Q` cannot be taken with a virtual position on the evidence
  read.
- **Physical transactions**: an import or export at `HQ_GEN_WHEEL` is an External Transaction scheduled by a
  NYISO customer, which also needs energy and transmission on the Québec side. Who can do this, and at what
  cost on both sides, was not established from the operator's documents in the spike.
- **Consequence**: there is no profit line in this piece. The worked deal value (plan §7) is a valuation of a
  stated physical block at the day-ahead price, with its assumptions listed; it is not a trading result.
