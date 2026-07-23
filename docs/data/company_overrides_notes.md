# Company classification — override notes

This document captures the non-obvious decisions behind
`report/data/companies.csv`. The CSV is the source of truth; this file is the
rationale. Year-aware buckets (`bucket_2010/2015/2020/2025`) classify the
same company differently over time.

## Bucket definitions

| Bucket              | Meaning                                                           |
| ------------------- | ----------------------------------------------------------------- |
| `large_cap`         | S&P 500-tier public company (or equivalent revenue for private)   |
| `mid_cap`           | Smaller public company                                            |
| `startup`           | Private company, small headcount / niche player                  |
| `academic`          | University / college                                              |
| `research_institute`| National lab, DFKI, imec, Fraunhofer, CEA, etc.                  |
| `industry_other`    | Industry-looking string not matched by any rule (heuristic only) |
| `unknown`           | Paper has no classifiable affiliation                            |

## Sector definitions (orthogonal to size bucket)

| Sector              | Examples                                              |
| ------------------- | ----------------------------------------------------- |
| `eda`               | Cadence, Synopsys, Mentor/Siemens, Keysight, Ansys   |
| `intel`             | Intel, NVIDIA, AMD, Qualcomm, Arm                     |
| `samsung`           | Samsung, TSMC, Infineon, NXP, STMicro, Broadcom, etc.|
| `auto`              | Bosch, Continental, ZF, Denso, Aptiv, Valeo          |
| `academic`          | Any university / college / polytechnic                |
| `research_institute`| DFKI, imec, Fraunhofer, CEA, BARC, ISRO               |
| `industry_other`    | Unmatched industry-looking string (heuristic)         |

## Tricky classifications

- **Mentor Graphics / Siemens EDA**: pre-2017 it was Mentor Graphics (public
  large-cap); acquired by Siemens in 2017 and renamed Siemens EDA. We keep it
  as `large_cap` in all buckets but set `is_eda_vendor=yes` consistently.

- **AMD**: was mid-cap pre-2017 (struggling), became large-cap after the Zen
  launch and the Xilinx acquisition (2022). `bucket_2010/2015=mid_cap`,
  `bucket_2020/2025=large_cap`.

- **Arm**: was private (large-cap by revenue, IP licensing model) until the
  2023 IPO. We treat it as `large_cap` throughout — pre-IPO valuation already
  exceeded many S&P 500 names.

- **Tensilica / NetSpeed / Duolog**: small EDA players acquired by Cadence
  (2013, 2018, 2014). Treated as `startup` for all years — they appear in
  pre-acquisition DVCon papers under their own name.

- **Altera**: Intel PSG since 2015, spun back out in 2024. Treated as
  `large_cap` throughout (Intel-subsidiary scale).

- **Cypress Semiconductor / LSI / Cavium / Aquantia / Dialog**: all mid-cap
  semis that were acquired by larger players; we use their independent
  identity across all years since DVCon papers predate the acquisitions.

- **Lattice Semiconductor**: struggled pre-2018 (treated as `startup` in
  2015), recovered to mid-cap afterwards.

- **Accellera**: standards body (UVM, VIP), non-profit but small. Treated as
  a `startup`-class EDA contributor since their papers represent the
  standards community.

- **Academic / research catch-all patterns**: `University|Universit`,
  `Institute of Technology`, `college|polytechnic`, `school of engineering`,
  etc. — these broad patterns catch IIT/IISc/MIT-style affiliations
  uniformly. The `sector=academic` is checked first in the classifier so
  these never accidentally fall into a company bucket.

- **DFKI / Fraunhofer / imec / CEA-LIST / BARC / ISRO**: each is a national
  research lab, not a company. Classified as `research_institute` (size
  bucket = `research_institute`, sector = `research_institute`).

## Coverage

After the curated list (~96 rules) plus the heuristic fallback for unknown
industry-looking strings, approximately **70%** of affiliation fragments
match a curated rule and ~30% fall through to the heuristic
`industry_other` bucket. The unmatched remainder is visible in the Q3
"Industry (unclassified)" stacked-bar segment so the gap is observable.

To improve coverage, edit `build_companies_csv.py`, re-run it to regenerate
`companies.csv`, then re-run `generate_report.py`.
