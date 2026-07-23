# DVCon corpus analysis report

Self-contained HTML report that data-mines the 1,852-paper DVCon corpus to
answer 5 questions: world map of author origin, racing-bar of topics and
verification languages, company contributions, author analytics, and
reproducibility metrics.

**Live site:** served by GitHub Pages at the repo's site URL (configured via
repo Settings → Pages, source = `main` branch / `/docs` folder). The site's
entry point is [`docs/index.html`](./index.html).

## Quick start

```bash
# 1. (one-time) create the isolated venv
py -3 -m venv docs/.venv
docs/.venv/Scripts/python.exe -m pip install -r docs/requirements.txt

# 2. regenerate the report (after editing the curated CSVs or after new ingest)
docs/.venv/Scripts/python.exe docs/generate_report.py

# 3. open docs/index.html in a browser
```

The generator reads `data/dvcon.db` directly (read-only) and does not touch
the running backend or its venv.

## Layout

```
docs/
  README.md                       this file
  requirements.txt                plotly, pandas, pycountry
  generate_report.py              orchestrator: load -> classify -> render HTML
  build_companies_csv.py          one-shot: regenerate companies.csv from a Python list
  index.html                      GITHUB PAGES ENTRY POINT (committed; auto-regenerated)
  .venv/                          isolated venv (gitignored)
  data/
    topics.csv                    CURATED 16-topic DVCon taxonomy (checked in)
    companies.csv                 CURATED ~96-entity classification table (checked in)
    company_overrides_notes.md    rationale for tricky classifications (checked in)
    per_year_country.csv          Q1 derived (gitignored)
    per_year_topic.csv            Q2 derived (gitignored)
    per_year_language.csv         Q2b derived (gitignored)
    per_year_company_class.csv    Q3 derived (gitignored)
    per_year_company_top.csv      Q3 derived (gitignored)
    reproducibility.csv           Q5 derived (gitignored)
```

## Refining the curated tables

The classifier is only as good as the curated CSVs. To improve coverage:

1. **Companies**: open `docs/data/companies.csv`. Each row is
   `(name_pattern, canonical_name, sector, bucket_2010, bucket_2015,
   bucket_2020, bucket_2025, founded_year, is_eda_vendor, notes)`.
   The `name_pattern` is a regex matched case-insensitively against each
   affiliation fragment; use `|` for alternation. Edit the Python list in
   `docs/build_companies_csv.py` and re-run that script rather than
   editing the CSV directly (it avoids CSV-quoting bugs with patterns that
   contain commas).

2. **Topics**: open `docs/data/topics.csv`. Each row is
   `(topic, keywords)` where keywords is a `|`-separated list of phrases.
   A paper is tagged with a topic if any phrase matches in title + abstract.

3. **Countries**: the country map and city fallback are hard-coded constants
   in `generate_report.py` (`COUNTRY_ALIAS`, `CITY_TO_COUNTRY`).

After any edit, re-run `generate_report.py` and commit the regenerated
`docs/index.html` (GitHub Pages re-deploys automatically on push to `main`).

## Data quality

The structured `Affiliation` / `Company` tables in the DB are GROBID-noisy
(paper-body sentences leak through as affiliations). All Q3/Q1 analysis uses
the flattened `affiliations_text` block instead, which is far more reliable.
Classification coverage and gap disclosures are reported inline in each
section of the HTML.
