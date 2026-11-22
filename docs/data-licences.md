# Data licences

Read on 2026-11-20. Quotations are copied verbatim from the page named in the `Source:` line above them.

## What this project does with the data

- A fetch script downloads the operator's public files into `data/raw/`, which git ignores. Raw files are never
  committed and never redistributed.
- The repository publishes code, derived statistics, figures and reports. The owner has ruled that derived statistics are
  published (below); the notice grants no licence and forbids none in words.

## NYISO: public market data (`mis.nyiso.com/public`)

Files used: day-ahead zonal LBMP (list P-2A), real-time integrated zonal LBMP (list P-4A), real-time 5-minute
zonal LBMP (list P-24A), ISO load forecast (list P-7). The site carries no data-specific licence that we
found; the operator's site-wide notice applies.

Source: <https://www.nyiso.com/legal-notice>

> The NYISO maintains this Web site for the benefit of its Market Participants and other authorized users. The materials on this site are provided "as is."

> Access to this Web site does not confer any license or ownership interest in either the form or content of the Web site, including any confidential or proprietary information or intellectual property of any kind or nature, and the NYISO hereby expressly reserves such rights and property in its entirety.

> The NYISO expressly disclaims any obligation to correct or update the materials on this Web site.

What this means here (this project's reading, not legal advice): no licence to redistribute the files, so none is
redistributed. Archived prices can be corrected after posting (the P-2A page marks corrected dates in green), so
an archive fetched in 2026 is not guaranteed to equal what was on the site at a past decision time; the plan
states how that is handled.

## Owner's rulings

- 2026-11-22: publish the code under the MIT licence and the derived statistics only (scores, sums, shares, hashes in
  the report and `runs/`); no raw NYISO price is published. The repository goes public on GitHub; no showcase or post
  is requested.
