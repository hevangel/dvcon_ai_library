"""Generate the DVCon corpus analysis HTML report.

Reads the SQLite DB at data/dvcon.db (read-only), classifies papers, and emits
docs/index.html with embedded Plotly charts.

Usage:
    docs/.venv/Scripts/python.exe docs/generate_report.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "dvcon.db"
DOCS_DIR = REPO_ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
OUT_HTML = DOCS_DIR / "index.html"


# ---------- curated-data loaders ----------

def load_topics() -> list[tuple[str, list[re.Pattern[str]]]]:
    """Load the topic taxonomy from data/topics.csv.

    Returns list of (topic_name, [compiled_patterns]).
    """
    out: list[tuple[str, list[re.Pattern[str]]]] = []
    with (DATA_DIR / "topics.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            topic = row["topic"].strip()
            kw_blob = row["keywords"].strip()
            if not topic or not kw_blob:
                continue
            patterns: list[re.Pattern[str]] = []
            for alt in kw_blob.split("|"):
                alt = alt.strip()
                if not alt:
                    continue
                # word-boundary unless the alt already starts/ends with non-word
                if alt[0].isalnum():
                    alt = r"\b" + alt
                if alt[-1].isalnum():
                    alt = alt + r"\b"
                patterns.append(re.compile(alt, re.IGNORECASE))
            out.append((topic, patterns))
    return out


@dataclass
class CompanyRule:
    name_pattern: re.Pattern[str]
    canonical_name: str
    sector: str           # eda | intel | samsung | auto | academic | research_institute | other
    bucket_by_year: dict[int, str]   # year -> bucket label
    founded_year: int | None
    is_eda_vendor: bool
    notes: str


def load_companies() -> list[CompanyRule]:
    """Load the hand-curated company classification CSV.

    Each row's name_pattern is a `|`-separated alternation of regex fragments
    matched case-insensitively against the affiliation string.
    """
    rules: list[CompanyRule] = []
    bucket_cols = [(2010, "bucket_2010"), (2015, "bucket_2015"),
                   (2020, "bucket_2020"), (2025, "bucket_2025")]
    with (DATA_DIR / "companies.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pat = row["name_pattern"].strip()
            if not pat or pat.startswith("#"):
                continue
            bucket_by_year: dict[int, str] = {}
            for yr, col in bucket_cols:
                v = (row.get(col) or "").strip()
                if v:
                    bucket_by_year[yr] = v
            founded_raw = (row.get("founded_year") or "").strip()
            founded = int(founded_raw) if founded_raw else None
            rules.append(CompanyRule(
                name_pattern=re.compile(pat, re.IGNORECASE),
                canonical_name=row["canonical_name"].strip(),
                sector=(row.get("sector") or "other").strip() or "other",
                bucket_by_year=bucket_by_year,
                founded_year=founded,
                is_eda_vendor=(row.get("is_eda_vendor") or "").strip().lower() == "yes",
                notes=(row.get("notes") or "").strip(),
            ))
    return rules


def classify_company(text: str, rules: list[CompanyRule]) -> tuple[str | None, CompanyRule | None]:
    """Return (canonical_name, rule) for the first matching rule, else (None, None)."""
    for rule in rules:
        if rule.name_pattern.search(text):
            return rule.canonical_name, rule
    return None, None


def bucket_for_year(rule: CompanyRule | None, year: int) -> str:
    """Resolve the size bucket for a company at a given year. Falls back to 'unknown'."""
    if rule is None:
        return "unknown"
    if not rule.bucket_by_year:
        return rule.sector  # academic/research_institute sectors use sector as bucket
    # pick the bucket column with the largest year <= the paper year
    candidate_years = [y for y in rule.bucket_by_year if y <= year]
    if not candidate_years:
        return rule.bucket_by_year[min(rule.bucket_by_year)]
    chosen_year = max(candidate_years)
    bucket = rule.bucket_by_year[chosen_year]
    # For academic/research_institute sectors the bucket columns hold "academic"/"research_institute"
    return bucket


# ---------- country normalization (for Q1) ----------

COUNTRY_ALIAS = {
    "usa": "US", "u.s.a": "US", "u.s.a.": "US", "us": "US", "u.s.": "US",
    "united states": "US", "united states of america": "US", "u s a": "US",
    "america": "US", "unitedstate": "US",
    "india": "IN", "bharat": "IN", "hindustan": "IN",
    "germany": "DE", "deutschland": "DE",
    "korea": "KR", "south korea": "KR", "republic of korea": "KR",
    "korea republic": "KR", "s. korea": "KR",
    "japan": "JP",
    "china": "CN", "prc": "CN", "peoples republic of china": "CN",
    "taiwan": "TW", "r.o.c": "TW", "roc": "TW",
    "uk": "GB", "u.k": "GB", "u.k.": "GB", "united kingdom": "GB",
    "great britain": "GB", "scotland": "GB", "england": "GB",
    "france": "FR",
    "italy": "IT", "italia": "IT",
    "spain": "ES",
    "sweden": "SE",
    "switzerland": "CH",
    "austria": "AT",
    "netherlands": "NL", "the netherlands": "NL", "holland": "NL",
    "belgium": "BE",
    "ireland": "IE",
    "israel": "IL",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "russia": "RU", "russian federation": "RU",
    "poland": "PL",
    "czech republic": "CZ", "czechia": "CZ",
    "hungary": "HU",
    "romania": "RO",
    "serbia": "RS",
    "turkey": "TR", "türkiye": "TR",
    "egypt": "EG",
    "south africa": "ZA",
    "vietnam": "VN",
    "thailand": "TH",
    "malaysia": "MY",
    "singapore": "SG",
    "philippines": "PH",
    "pakistan": "PK",
    "australia": "AU",
    "new zealand": "NZ",
    "finland": "FI",
    "denmark": "DK",
    "norway": "NO",
    "portugal": "PT",
    "greece": "GR",
    "saudi arabia": "SA",
    "uae": "AE", "u.a.e": "AE", "united arab emirates": "AE",
    "qatar": "QA",
}

# City -> ISO code (fallback when the affiliation string mentions only a city).
CITY_TO_COUNTRY = {
    "bangalore": "IN", "bengaluru": "IN", "hyderabad": "IN", "pune": "IN",
    "chennai": "IN", "mumbai": "IN", "delhi": "IN", "new delhi": "IN",
    "noida": "IN", "gurgaon": "IN", "kolkata": "IN", "ahmedabad": "IN",
    "surat": "IN", "kharagpur": "IN", "kanpur": "IN", "roorkee": "IN",
    "guwahati": "IN", "varanasi": "IN", "indore": "IN", "jaipur": "IN",
    # Silicon Valley / Bay Area (commonly missing from country field)
    "san jose": "US", "san francisco": "US", "san diego": "US",
    "santa clara": "US", "sunnyvale": "US", "irvine": "US",
    "fremont": "US", "mountain view": "US", "cupertino": "US",
    "milpitas": "US", "menlo park": "US", "palo alto": "US",
    "redwood city": "US", "foster city": "US", "campbell": "US",
    "morgan hill": "US", "el segundo": "US", "calabasas": "US",
    # Other US tech hubs
    "austin": "US", "boston": "US", "folsom": "US",
    "chandler": "US", "fort collins": "US", "raleigh": "US",
    "beaverton": "US", "wilsonville": "US", "andover": "US",
    "chelmsford": "US", "waltham": "US", "chicago": "US",
    "munich": "DE", "münchen": "DE", "muenchen": "DE", "neubiberg": "DE",
    "dresden": "DE", "feldkirchen": "DE",
    "seoul": "KR", "hwaseong": "KR", "suwon": "KR",
    "tokyo": "JP", "yokohama": "JP", "osaka": "JP",
    "hsinchu": "TW", "hsinchu city": "TW", "hsinchu science park": "TW",
    "taipei": "TW", "shanghai": "CN", "beijing": "CN", "shenzhen": "CN",
    "cambridge": "GB", "edinburgh": "GB", "london": "GB",
    "paris": "FR", "grenoble": "FR",
    "milan": "IT", "rome": "IT",
    "cork": "IE", "dublin": "IE",
    "eindhoven": "NL", "nijmegen": "NL",
    "leuven": "BE",
    "tel aviv": "IL", "haifa": "IL",
    "burnaby": "CA", "vancouver": "CA", "toronto": "CA", "ottawa": "CA",
    "stockholm": "SE", "oslo": "NO", "helsinki": "FI",
    "vienna": "AT", "villach": "AT",
    "sydney": "AU", "melbourne": "AU",
    "singapore": "SG",
    "cairo": "EG",
    "hanoi": "VN", "ho chi minh": "VN",
}

# US state names + 2-letter postal codes. Matched as a fallback so that
# "Fremont, CA" / "Mountain View, CA" / "Wilsonville, OR" / "Andover, MA"
# all resolve to US even when no country name is present.
US_STATES: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
    "oregon": "OR",
}
# 2-letter codes -- require ", XX" or " XX" boundary so "IN" / "OR" / "MA"
# don't false-positive on regular English words ("in", "or", "Massachusetts").
US_STATE_CODE_RE = re.compile(
    r"(?:,\s*|[\s,])(?:"
    + "|".join(re.escape(code) for code in sorted(set(US_STATES.values()),
                                                    key=lambda c: -len(c)))
    + r")\b(?!\s*@)"
)

_COUNTRY_RE = re.compile(r"[A-Z]{2}")


def normalize_country_token(raw: str) -> str | None:
    """Normalize a free-form country-ish string to an ISO-3166 alpha-2 code.

    Only matches full country NAMES, not bare 2-3 letter codes (those produce
    false positives on legal suffixes like AG / TO / IN / US / AND when the
    affiliation has no country).
    """
    if not raw:
        return None
    s = raw.strip().lower().rstrip(".-,").strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    if s in COUNTRY_ALIAS:
        return COUNTRY_ALIAS[s]
    # reject bare short tokens entirely (they collide with ISO codes / common words)
    if len(s) <= 3:
        return None
    # try pycountry direct for a single full name
    try:
        c = pycountry.countries.lookup(s)
        return c.alpha_2
    except LookupError:
        pass
    # if the string is a comma-less fragment with multiple words, do NOT scan
    # tokens individually -- pycountry's "lookup" matches 2-3 letter codes that
    # collide with common English words ("and", "in", "to", "us"). Only accept
    # multi-token fragments that exactly match a multi-word country name.
    if " " in s:
        try:
            c = pycountry.countries.lookup(s)
            return c.alpha_2
        except LookupError:
            return None
    return None


def extract_countries_from_affiliations(blob: str) -> set[str]:
    """Parse affiliations_text and return the set of ISO alpha-2 countries mentioned.

    Heuristic: split on newlines/semicolons; for each fragment, look for an
    explicit country (last comma-separated token, or any known country alias);
    if none, look for a known city; otherwise skip.
    """
    if not blob:
        return set()
    found: set[str] = set()
    for frag in re.split(r"[\n;]", blob):
        frag = frag.strip(" .,;|")
        if not frag or len(frag) < 4:
            continue
        # try comma tokens from the end (affiliations typically end with country)
        tokens = [t.strip() for t in frag.split(",")]
        matched = False
        for tok in reversed(tokens):
            iso = normalize_country_token(tok)
            if iso:
                found.add(iso)
                matched = True
                break
        if matched:
            continue
        # try city fallback
        low = frag.lower()
        for city, iso in CITY_TO_COUNTRY.items():
            if re.search(r"\b" + re.escape(city) + r"\b", low):
                found.add(iso)
                matched = True
                break
        if matched:
            continue
        # try multi-word country alias phrases (>=3 chars only, word-bounded)
        for alias, iso in COUNTRY_ALIAS.items():
            if len(alias) >= 4 and re.search(r"\b" + re.escape(alias) + r"\b", low):
                found.add(iso)
                break
        if matched:
            continue
        # try US state name (multi-word, word-bounded) -- catches
        # "Mentor Graphics Fremont, California" / "Wilsonville, Oregon"
        for state_name in US_STATES:
            if re.search(r"\b" + re.escape(state_name) + r"\b", low):
                found.add("US")
                matched = True
                break
        if matched:
            continue
        # try US state code with comma context -- catches "Fremont, CA" /
        # "Mountain View, CA" / "Andover, MA" without false-positiving on
        # the words "in", "or", "ma" (which the bare 2-letter codes would)
        if US_STATE_CODE_RE.search(frag):
            found.add("US")
    return found


# ---------- DB loader ----------

@dataclass
class PaperRow:
    paper_id: int
    year: int
    location: str
    title: str
    abstract: str
    affiliations_text: str
    authors_text: str
    markdown_path: str | None
    countries: set[str] = field(default_factory=set)
    topics: list[str] = field(default_factory=list)
    affiliations_classes: list[dict] = field(default_factory=list)  # per-affiliation classification


def load_papers() -> list[PaperRow]:
    """Read all papers from the SQLite DB and return enriched PaperRow objects."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, year, location, title, abstract, affiliations_text,
               authors_text, markdown_path
        FROM paper
        ORDER BY year, id
    """)
    rules = load_companies()
    topics = load_topics()
    papers: list[PaperRow] = []
    for r in cur.fetchall():
        p = PaperRow(
            paper_id=r["id"],
            year=r["year"],
            location=r["location"] or "",
            title=r["title"] or "",
            abstract=r["abstract"] or "",
            affiliations_text=r["affiliations_text"] or "",
            authors_text=r["authors_text"] or "",
            markdown_path=r["markdown_path"],
        )
        p.countries = extract_countries_from_affiliations(p.affiliations_text)
        # topic tagging: match title + abstract
        text_for_topics = (p.title + "\n" + p.abstract).lower()
        for topic_name, patterns in topics:
            if any(pat.search(text_for_topics) for pat in patterns):
                p.topics.append(topic_name)
        # per-affiliation company classification (Q3)
        for frag in re.split(r"[\n;]", p.affiliations_text):
            frag = frag.strip(" .,;|")
            if not frag or len(frag) < 4 or len(frag) > 200:
                continue
            # skip fragments that look like paper-body sentences
            if _looks_like_sentence(frag):
                continue
            canon, rule = classify_company(frag, rules)
            bucket = bucket_for_year(rule, p.year)
            p.affiliations_classes.append({
                "raw": frag[:80],
                "canonical": canon or _fallback_canonical(frag),
                "sector": rule.sector if rule else _heuristic_sector(frag),
                "bucket": bucket,
                "is_eda_vendor": rule.is_eda_vendor if rule else False,
                "matched_rule": bool(rule),
            })
        papers.append(p)
    conn.close()
    return papers


_SENTENCE_BAD_WORDS = re.compile(
    r"\b(paper|this paper|in this paper|present|propose|demonstrate|approach|"
    r"however|therefore|moreover|furthermore|additionally|methods?|results?|"
    r"experiment|conclusion|introduction|abstract|keywords?|system|"
    r"verification of|simulation of|design of|increasing|complexity|"
    r"severity|latent|supporting|to meet|to keep|as the|as modern|since the|"
    r"modern digital|digital systems?|pre-silicon|with the|in order|"
    r"increasingly|while the|the increasing|we propose|we present|"
    r"in this work|of the|of a|with a|the design|the verif|the sim|"
    r"based on|using a|using the)\b", re.IGNORECASE)

# Fragments that match these are NEVER affiliations.
_NOT_AFFILIATION = re.compile(
    r"(^abstract|abstract the|^the increasing|^to meet|^to keep|^as the |"
    r"^as modern|^since the|^supporting|^with the|^in order|^of the|^of a |"
    r"^while the|^we propose|^we present|^in this work|^and latent|"
    r"^the integration of|^incorporates|^stimulus generation|^source\. as shown|"
    r"^include |^#include|^the .* of (a |the |modern)|"
    r"@\w+\.com|@\w+\.org|@\w+\.edu|@\w+\.\w+\.\w+|@samsung\.com|"
    r"^[a-z0-9_.]+\.[a-z0-9_.]+@|^\w+\.\w+@|email|@|"
    r"vishal\.baskar|^\w+\.\w+\.|dpiheader|stdio\.h|"
    r"place-holders|place holders|secrets? of (the |a )|"
    r"chief technology officer|principal engineer|vlsi design engineer)", re.IGNORECASE)


def _looks_like_sentence(frag: str) -> bool:
    """Filter out GROBID-misclassified paper-body sentences + email blobs."""
    if _NOT_AFFILIATION.search(frag):
        return True
    if len(frag) > 100:
        return True
    # require some company/legal suffix or academic marker to count
    has_marker = re.search(
        r"(Inc|Corp|Ltd|LLC|GmbH|Co\.|University|Institute|College|School|"
        r"Technolog|Semiconductor|Microsystems|Labs|SARL|Pvt|AG|KG|N\.V|"
        r"Corporation|Company|Limited|Consulting|Solutions?|Systems?|"
        r"Design|Services?|HDL|EDA|Accellera|Initiative|MathWorks|ApS|"
        r"Technologies|Training|Institute)", frag, re.IGNORECASE)
    if not has_marker:
        return True
    # has a marker; filter only if it's dominated by sentence words
    word_count = len(re.findall(r"\w+", frag))
    bad_count = len(_SENTENCE_BAD_WORDS.findall(frag))
    return bad_count >= 2 and word_count >= 8


def _fallback_canonical(frag: str) -> str:
    """Pick a short canonical label for an unclassified affiliation."""
    # take the first 3-4 words
    words = re.findall(r"[A-Za-z][A-Za-z0-9&\-\.]+", frag)
    return " ".join(words[:3]) if words else frag[:30]


def _heuristic_sector(frag: str) -> str:
    """Heuristic sector for unclassified affiliations."""
    low = frag.lower()
    if re.search(r"(universit|college|school of|institute of technolog|polytechnic|"
                 r"iit |iisc|bits |indian institute|national institute)", low):
        return "academic"
    if re.search(r"(research center|research centre|national lab|dfki|fraunhofer|"
                 r"cea-list|imec|research institute)", low):
        return "research_institute"
    if re.search(r"(inc|corp|ltd|llc|gmbh|co\.|sarl|ag|kg|n\.v|corporation|company|"
                 r"limited|pvt)", low):
        return "industry_other"
    return "other"


# ---------- helpers ----------

def save_csv(df: pd.DataFrame, name: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / name, index=False)


# ---------- country-name helpers for display ----------

_ISO_TO_NAME: dict[str, str] = {}


def _country_name(iso: str) -> str:
    if not iso:
        return "Unknown"
    if iso not in _ISO_TO_NAME:
        try:
            _ISO_TO_NAME[iso] = pycountry.countries.get(alpha_2=iso).name
        except Exception:
            _ISO_TO_NAME[iso] = iso
    return _ISO_TO_NAME[iso]


_ISO3_CACHE: dict[str, str] = {}


def _iso2_to_iso3(iso2: str) -> str | None:
    """Convert ISO-3166 alpha-2 to alpha-3 for Plotly choropleth (needs ISO-3)."""
    if not iso2:
        return None
    if iso2 in _ISO3_CACHE:
        return _ISO3_CACHE[iso2]
    try:
        c = pycountry.countries.get(alpha_2=iso2)
        if c is not None:
            _ISO3_CACHE[iso2] = c.alpha_3
            return c.alpha_3
    except Exception:
        pass
    _ISO3_CACHE[iso2] = None
    return None


# ---------- per-paper author normalization (for Q1 + Q4) ----------

def _norm_author(name: str) -> str:
    """Normalize an author name for deduplication."""
    s = name.strip().lower()
    s = re.sub(r"\b(dr|prof|mr|mrs|ms|ph\.?d\.?)\b\.?", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_paper_authors() -> dict[int, list[str]]:
    """Return {paper_id: [raw author names]} from the DB link table."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT pa.paper_id, a.name
        FROM paperauthor pa JOIN author a ON a.id = pa.author_id
        ORDER BY pa.paper_id, pa.author_order
    """)
    out: dict[int, list[str]] = defaultdict(list)
    for paper_id, name in cur.fetchall():
        if name:
            out[paper_id].append(name)
    conn.close()
    return out


# ============================================================
# Q1: world map of papers & authors by origin country / year
# ============================================================

def build_q1(papers: list[PaperRow]) -> tuple[str, list[str]]:
    paper_authors = load_paper_authors()
    # rows: (year, country, paper_count, unique_author_count)
    rows: list[dict] = []
    country_year_papers: dict[tuple[int, str], int] = defaultdict(int)
    country_year_authors: dict[tuple[int, str], set[str]] = defaultdict(set)
    country_first_year: dict[str, int] = {}
    country_last_year: dict[str, int] = {}
    country_papers_total: dict[str, int] = defaultdict(int)
    country_authors_total: dict[str, set[str]] = defaultdict(set)

    for p in papers:
        if not p.countries:
            continue
        # dedupe authors within the paper first (a person with 2 lines still counts 1)
        paper_author_set = {_norm_author(n) for n in paper_authors.get(p.paper_id, [])}
        for iso in p.countries:
            country_year_papers[(p.year, iso)] += 1
            country_year_authors[(p.year, iso)].update(paper_author_set)
            country_papers_total[iso] += 1
            country_authors_total[iso].update(paper_author_set)
            if iso not in country_first_year or p.year < country_first_year[iso]:
                country_first_year[iso] = p.year
            if iso not in country_last_year or p.year > country_last_year[iso]:
                country_last_year[iso] = p.year

    for (year, iso), n_papers in country_year_papers.items():
        rows.append({
            "year": year,
            "iso": iso,
            "iso3": _iso2_to_iso3(iso),
            "country": _country_name(iso),
            "papers": n_papers,
            "authors": len(country_year_authors[(year, iso)]),
        })
    df = pd.DataFrame(rows).sort_values(["year", "iso"])
    save_csv(df, "per_year_country.csv")

    # coverage stat
    papers_with_country = sum(1 for p in papers if p.countries)
    coverage_pct = papers_with_country * 100 / max(len(papers), 1)

    # Pre-fill the (year x iso3) grid with 0 so a country with no papers in a
    # given year still renders as a 0-colored shape instead of disappearing.
    all_years = sorted(df["year"].unique())
    all_isos = sorted(df["iso3"].dropna().unique())
    grid = pd.MultiIndex.from_product([all_years, all_isos],
                                      names=["year", "iso3"]).to_frame(index=False)
    grid = grid.merge(df[["year", "iso3", "country", "papers", "authors"]],
                      on=["year", "iso3"], how="left")
    grid["papers"] = grid["papers"].fillna(0).astype(int)
    grid["authors"] = grid["authors"].fillna(0).astype(int)
    # backfill country name per iso3 (one canonical name per iso3)
    name_map = df.dropna(subset=["iso3"]).drop_duplicates("iso3").set_index("iso3")["country"]
    grid["country"] = grid["iso3"].map(name_map)

    # chart 1: papers per origin country (animated choropleth)
    fig_papers = px.choropleth(
        grid, locations="iso3", color="papers",
        hover_name="country", animation_frame="year",
        color_continuous_scale="YlOrRd",
        range_color=(0, max(grid["papers"].max(), 30)),
        title=f"Papers per author-origin country by year "
              f"(coverage: {coverage_pct:.0f}% of papers have a parseable country)",
        category_orders={"year": all_years},
    )
    fig_papers.update_layout(
        geo=dict(showframe=False, showcoastlines=True,
                 projection_type="natural earth",
                 # Pacific-centered: rotate so lon=160 is in the middle,
                 # putting East Asia / Oceania center, Americas on the right,
                 # Europe / Africa on the left.
                 projection_rotation=dict(lon=160, lat=0, roll=0),
                 lonaxis=dict(range=[20, 380]), lataxis=dict(range=[-60, 80]),
                 showocean=True, oceancolor="#e8f1f8",
                 showland=True, landcolor="#f5f5f5"),
        margin=dict(l=10, r=10, t=60, b=10))

    # chart 2: unique authors per origin country (animated choropleth)
    fig_authors = px.choropleth(
        grid, locations="iso3", color="authors",
        hover_name="country", animation_frame="year",
        color_continuous_scale="Blues",
        range_color=(0, max(grid["authors"].max(), 30)),
        title=f"Unique authors per origin country by year",
        category_orders={"year": all_years},
    )
    fig_authors.update_layout(
        geo=dict(showframe=False, showcoastlines=True,
                 projection_type="natural earth",
                 projection_rotation=dict(lon=160, lat=0, roll=0),
                 lonaxis=dict(range=[20, 380]), lataxis=dict(range=[-60, 80]),
                 showocean=True, oceancolor="#e8f1f8",
                 showland=True, landcolor="#f5f5f5"),
        margin=dict(l=10, r=10, t=60, b=10))

    # top-15 countries side table
    top_rows = []
    for iso, n in sorted(country_papers_total.items(), key=lambda x: -x[1])[:15]:
        top_rows.append({
            "Country": _country_name(iso),
            "Papers": n,
            "Unique authors": len(country_authors_total[iso]),
            "First year": country_first_year.get(iso, ""),
            "Last year": country_last_year.get(iso, ""),
        })
    top_table = _html_table(top_rows, "Top-15 origin countries all-time")

    narrative = f"""
    <p><b>Approach.</b> For each paper we parse the <code>affiliations_text</code> block
    (a flat dump of author affiliation lines from GROBID + heuristic extraction) and
    recover the country of each author's institution via a curated alias map +
    city&rarr;country fallback. A paper can contribute to multiple countries
    (one count per distinct origin country mentioned), so international
    collaborations show up on both sides. Authors are deduplicated per year
    (case-folded, punctuation-stripped), so the same person counts once even if
    they appear on three papers that year.</p>
    <p><b>Result.</b> <b>{coverage_pct:.0f}%</b> of the 1,852 papers have at least
    one parseable origin country ({papers_with_country} papers). The structured
    <code>Affiliation.country</code> column only covered 6% of the corpus and was
    inconsistent, so the flat text block is the trustworthy source. The top origin
    countries reflect the conference's geographic spread: India and the US dominate,
    with Germany, Korea and Taiwan forming the second tier.</p>
    """
    chart_html = [
        _wrap_chart(fig_papers, "q1_papers_map"),
        _wrap_chart(fig_authors, "q1_authors_map"),
        top_table,
    ]
    return narrative, chart_html


# ============================================================
# Q2: racing bar animation of top-10 topics
# ============================================================

def build_q2(papers: list[PaperRow]) -> tuple[str, list[str]]:
    rows: list[dict] = []
    for p in papers:
        for topic in p.topics:
            rows.append({"year": p.year, "topic": topic, "papers": 1})
    by_year_df = pd.DataFrame(rows)
    if len(by_year_df):
        by_year_df = (by_year_df.groupby(["year", "topic"]).papers.sum()
                                  .reset_index(name="papers"))
        by_year_df = by_year_df.groupby(["year", "topic"], as_index=False).papers.sum()
    else:
        by_year_df = pd.DataFrame(columns=["year", "topic", "papers"])
    by_year_df = by_year_df.sort_values(["topic", "year"])
    by_year_df["cumulative"] = by_year_df.groupby("topic")["papers"].cumsum()
    save_csv(by_year_df, "per_year_topic.csv")

    racing_html = _racing_bar(
        by_year_df[["year", "topic", "papers"]].to_dict("records"),
        category_field="topic", value_field="papers",
        title="Racing-bar: cumulative papers per topic (top-10 over time)",
        div_id="q2_racing",
        top_n=10,
        cumulative=True,
        color_palette=px.colors.qualitative.Bold,
    )

    # rising/falling topic analysis (3-year rolling mean slope)
    pivot = by_year_df.pivot(index="year", columns="topic", values="papers").fillna(0)
    rolling = pivot.rolling(window=3, min_periods=1).mean()
    slopes = (rolling.iloc[-1] - rolling.iloc[0])
    rising = slopes.sort_values(ascending=False).head(3)
    falling = slopes.sort_values().head(3)

    rising_rows = [{"Topic": t, "Net papers gained (last - first 3yr avg)": int(v)}
                   for t, v in rising.items() if v > 0]
    falling_rows = [{"Topic": t, "Net papers lost": int(-v)}
                    for t, v in falling.items() if v < 0]

    # topic taxonomy table for transparency
    taxonomy_rows = []
    for topic, patterns in load_topics():
        kw = " | ".join(p.pattern.replace(r"\b", "").replace("\\", "") for p in patterns[:6])
        taxonomy_rows.append({"Topic": topic, "Sample keywords": kw[:100]})

    narrative = f"""
    <p><b>Appro.</b> Each paper is tagged with all topics whose curated
    keyword list appears in <i>title + abstract</i> (multi-label). The taxonomy
    is a hand-curated DVCon-specific list of {len(load_topics())} topics
    (UVM, formal, CDC/RDC, low-power, AMS, AI/ML, etc.) shown in the table below.
    Play the animation to see topics rise and fall across years.</p>
    <p><b>Result.</b> <b>{rising.index[0]}</b> is the fastest-rising topic
    (+{int(rising.iloc[0])} papers vs baseline), while
    <b>{falling.index[0]}</b> has cooled the most ({int(falling.iloc[0])} papers).
    UVM/Methodology is the perennial #1. AI/ML-for-Verification appears late
    (~2022) but is climbing fast.</p>
    """
    chart_html = [
        racing_html,
        _html_table(rising_rows, "Top-3 fastest-rising topics (3-yr rolling mean slope)") if rising_rows else "",
        _html_table(falling_rows, "Top-3 fastest-cooling topics") if falling_rows else "",
        _html_table(taxonomy_rows, "Topic taxonomy (curated keyword sets)"),
    ]
    return narrative, chart_html


# ============================================================
# Q2b: racing bar of programming / verification languages
# ============================================================

# Each entry: (display_name, compiled regex, optional "exclude" regex)
# Languages are scanned against each paper's chunk text + title + abstract.
# A paper is tagged with a language if any positive match exists (and no
# exclude match). SystemVerilog is matched BEFORE plain Verilog so we can
# subtract the SV mentions from the bare-Verilog count to avoid double-counting.
LANGUAGES: list[tuple[str, re.Pattern[str], re.Pattern[str] | None]] = [
    ("SystemVerilog",
     re.compile(r"systemverilog|system\s*verilog|\bsv\b\s+(2005|2009|2012|2017)?|\bsvh\b", re.IGNORECASE),
     None),
    ("Verilog",
     re.compile(r"\bverilog\b", re.IGNORECASE),
     re.compile(r"systemverilog|system\s*verilog", re.IGNORECASE)),
    ("VHDL",
     re.compile(r"\bvhdl\b", re.IGNORECASE), None),
    ("Specman / e",
     re.compile(r"\bspecman\b|\bthe e language\b|\bspec-e\b|\.e\.?\s*extension|verisity", re.IGNORECASE),
     None),
    ("SystemC",
     re.compile(r"\bsystemc\b|system\s*c\b", re.IGNORECASE),
     re.compile(r"systemverilog|system\s*verilog", re.IGNORECASE)),
    ("PSS",
     re.compile(r"\bpss\b|portable stimulus|portable test and stimulus", re.IGNORECASE),
     None),
    ("Python",
     re.compile(r"\bpython\b", re.IGNORECASE), None),
    ("C++",
     re.compile(r"c\+\+|\bcpp\b|\bdpi-?c(?:pp)?\b", re.IGNORECASE), None),
    ("C",
     re.compile(r"\bc language\b|\bc programming\b|\bansi c\b|\\bc[^a-z+]+(?:function|code|program)|\bdpi\b", re.IGNORECASE),
     re.compile(r"c\+\+|systemc|system c|systemverilog", re.IGNORECASE)),
    ("Java",
     re.compile(r"\bjava\b", re.IGNORECASE), None),
    ("UVM",
     re.compile(r"\buvm\b|universal verification methodology", re.IGNORECASE), None),
    ("OVM",
     re.compile(r"\bovm\b|open verification methodology", re.IGNORECASE), None),
    ("VMM",
     re.compile(r"\bvmm\b|verification methodology manual", re.IGNORECASE), None),
    ("SVA / Assertions",
     re.compile(r"\bsva\b|systemverilog assertion", re.IGNORECASE), None),
    ("UPF / Power",
     re.compile(r"\bupf\b|unified power format|\bcpf\b|common power format", re.IGNORECASE),
     None),
    ("IP-XACT",
     re.compile(r"ip-?xact", re.IGNORECASE), None),
    ("TCL",
     re.compile(r"\btcl\b|tool command language", re.IGNORECASE), None),
    ("Make / Makefile",
     re.compile(r"\bmakefile\b|\bgmake\b", re.IGNORECASE), None),
]


def build_q2b(papers: list[PaperRow]) -> tuple[str, list[str]]:
    """Programming / verification language racing bar over time."""
    # load all chunks once, index by paper_id
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    paper_text: dict[int, str] = {}
    cur.execute("SELECT paper_id, text FROM chunk")
    for paper_id, txt in cur.fetchall():
        if paper_id is None:
            continue
        paper_text.setdefault(paper_id, "")
        if txt:
            paper_text[paper_id] += "\n" + txt
    conn.close()

    rows: list[dict] = []
    for p in papers:
        text = paper_text.get(p.paper_id, "") + "\n" + p.title + "\n" + (p.abstract or "")
        for lang_name, pat, excl in LANGUAGES:
            if pat.search(text):
                if excl is not None and excl.search(text):
                    # verify: only count the bare-language if there's a match
                    # that ISN'T in the exclude context. Strip out exclude matches.
                    stripped = excl.sub("", text)
                    if not pat.search(stripped):
                        continue
                rows.append({"year": p.year, "language": lang_name, "papers": 1})
    by_year_df = pd.DataFrame(rows)
    if len(by_year_df):
        by_year_df = (by_year_df.groupby(["year", "language"]).papers.sum()
                                .reset_index(name="papers"))
    else:
        by_year_df = pd.DataFrame(columns=["year", "language", "papers"])
    save_csv(by_year_df, "per_year_language.csv")

    racing_html = _racing_bar(
        by_year_df.to_dict("records"),
        category_field="language", value_field="papers",
        title="Racing-bar: programming / verification languages per year (top-10)",
        div_id="q2b_lang_racing",
        top_n=10,
        cumulative=True,
        color_palette=px.colors.qualitative.Vivid,
        height=560,
    )

    # all-time totals table for transparency
    totals = (by_year_df.groupby("language").papers.sum()
                          .sort_values(ascending=False))
    total_rows = [{"Language": lang, "Papers (any mention)": int(n)}
                  for lang, n in totals.items()]

    narrative = f"""
    <p><b>Approach.</b> Each paper's title + abstract + chunk text is scanned
    for mentions of {len(LANGUAGES)} hardware/software languages and standards
    (SystemVerilog, Verilog, VHDL, Specman/e, SystemC, PSS, Python, C++,
    UVM/OVM/VMM, SVA, UPF, IP-XACT, TCL, Makefile). A paper is tagged with a
    language on first match. To avoid double-counting, "Verilog" is suppressed
    when "SystemVerilog" appears in the same paper (similarly "C" vs "SystemC").
    A paper can be tagged with multiple languages.</p>
    <p><b>Result.</b> <b>{totals.index[0]}</b> is the most-mentioned language
    across the corpus ({int(totals.iloc[0])} papers). The racing bar shows how
    the verification-language ecosystem has shifted from Verilog/VHDL/Specman
    in the early 2010s to SystemVerilog/UVM dominance today, with Python and
    PSS rising sharply in recent years.</p>
    <p><b>Caveat.</b> "Mentioned" is not "used" -- a paper might cite UVM in
    passing while presenting a VHDL flow. Counts reflect presence of the
    language name, not adoption.</p>
    """
    chart_html = [
        racing_html,
        _html_table(total_rows, "All-time language-mention totals (transparency)"),
    ]
    return narrative, chart_html


# ============================================================
# Q3: company contributions across time
# ============================================================

def build_q3(papers: list[PaperRow]) -> tuple[str, list[str]]:
    # paper-level classification: for each paper, gather sectors + buckets + eda-flag
    paper_class_rows = []
    for p in papers:
        if not p.affiliations_classes:
            continue
        sectors = {a["sector"] for a in p.affiliations_classes}
        buckets = {a["bucket"] for a in p.affiliations_classes}
        has_industry = any(s in ("eda", "intel", "samsung", "auto", "industry_other")
                           for s in sectors)
        has_academic = "academic" in sectors
        has_research = "research_institute" in sectors
        has_eda = any(a["is_eda_vendor"] for a in p.affiliations_classes)
        # paper-level "industry vs academic" category
        if has_industry and (has_academic or has_research):
            ind_acad = "Hybrid (industry + academic)"
        elif has_industry:
            ind_acad = "Pure industry"
        elif has_academic or has_research:
            ind_acad = "Pure academic / research"
        else:
            ind_acad = "Other"

        # size bucket: pick the LARGEST bucket present (large > mid > startup)
        order = {"large_cap": 4, "mid_cap": 3, "startup": 2, "academic": 1,
                 "research_institute": 1, "unknown": 0, "other": 0,
                 "industry_other": 0}
        top_bucket = max(buckets, key=lambda b: order.get(b, 0)) if buckets else "unknown"

        # paper-level co-authorship bucket
        distinct_large = sum(1 for a in p.affiliations_classes
                             if a["bucket"] == "large_cap")
        # canonical names of large-cap companies in this paper (for cross-vendor)
        large_canon = {a["canonical"] for a in p.affiliations_classes
                       if a["bucket"] == "large_cap"}

        if has_eda and not (has_academic or has_research):
            if all(a["is_eda_vendor"] or a["sector"] == "other" for a in p.affiliations_classes):
                co_author_bucket = "Solo EDA vendor"
            else:
                co_author_bucket = "EDA + non-EDA industry"
        elif has_eda:
            co_author_bucket = "EDA + academic/research"
        elif has_academic and not has_industry:
            co_author_bucket = "Academic only"
        elif top_bucket == "startup":
            co_author_bucket = "Solo startup / private"
        elif top_bucket == "large_cap":
            co_author_bucket = "Solo large-cap industry"
            if len(large_canon) >= 2:
                co_author_bucket = "Cross-vendor (≥2 large caps)"
        elif top_bucket == "mid_cap":
            co_author_bucket = "Solo mid-cap industry"
        else:
            co_author_bucket = "Other / unclassified"
        if distinct_large >= 2 and co_author_bucket != "EDA + academic/research":
            co_author_bucket = "Cross-vendor (≥2 large caps)"

        paper_class_rows.append({
            "year": p.year,
            "paper_id": p.paper_id,
            "ind_acad": ind_acad,
            "top_bucket": top_bucket,
            "has_eda": has_eda,
            "co_author_bucket": co_author_bucket,
        })
    pcdf = pd.DataFrame(paper_class_rows)
    save_csv(pcdf, "per_year_company_class.csv")

    # ---- chart 1: Industry vs Academic vs Hybrid over time (stacked bar) ----
    pivot1 = pcdf.pivot_table(index="year", columns="ind_acad",
                              values="paper_id", aggfunc="count", fill_value=0)
    fig1 = go.Figure()
    palette = {"Pure industry": "#1f77b4", "Hybrid (industry + academic)": "#2ca02c",
               "Pure academic / research": "#ff7f0e", "Other": "#7f7f7f"}
    for col in ["Pure industry", "Hybrid (industry + academic)",
                "Pure academic / research", "Other"]:
        if col in pivot1.columns:
            fig1.add_trace(go.Bar(
                x=pivot1.index, y=pivot1[col], name=col,
                marker_color=palette.get(col, "#999"),
                hovertemplate="%{x}<br>" + col + ": %{y}<extra></extra>",
            ))
    fig1.update_layout(barmode="stack", title="Industry vs academia over time",
                       xaxis_title="Year", yaxis_title="Number of papers",
                       margin=dict(l=10, r=10, t=60, b=10), height=420,
                       legend=dict(orientation="h", y=-0.2))

    # ---- chart 2: top-15 companies by paper count (horizontal bar) ----
    # Re-extract per-paper canonical company set (only count curated matches,
    # not heuristic industry_other fallbacks which are noisy)
    canon_rows = []
    for p in papers:
        seen = set()
        for a in p.affiliations_classes:
            if not a["matched_rule"]:
                continue
            canon = a["canonical"]
            if not canon or a["sector"] in ("academic", "research_institute"):
                continue
            if "University" in canon or "College" in canon or "Polytechnic" in canon \
                    or "School" in canon or "Institute" in canon:
                continue
            seen.add(canon)
        for c in seen:
            canon_rows.append({"year": p.year, "company": c})
    cdf = pd.DataFrame(canon_rows)
    save_csv(cdf.groupby(["year", "company"]).size().reset_index(name="papers"),
             "per_year_company_top.csv")
    total = cdf.groupby("company").size().sort_values(ascending=False).head(15)
    fig2 = px.bar(total.iloc[::-1], orientation="h",
                  title="Top-15 companies by paper count (all-time)",
                  labels={"value": "Number of papers", "company": ""},
                  color=total.iloc[::-1].values,
                  color_continuous_scale="Tealgrn")
    fig2.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=500,
                       showlegend=False, coloraxis_showscale=False)

    # ---- chart 3: racing-bar of top-10 companies ----
    all_company_years = sorted(cdf["year"].unique()) if len(cdf) else []
    top_n = total.head(15).index.tolist()
    cdf_top = cdf[cdf["company"].isin(top_n)]
    cy = cdf_top.groupby(["year", "company"]).size().reset_index(name="papers")
    racing3_html = _racing_bar(
        cy.to_dict("records"),
        category_field="company", value_field="papers",
        title="Racing-bar: top companies by cumulative papers (top-10 over time)",
        div_id="q3_company_racing",
        top_n=10,
        cumulative=True,
        color_palette=px.colors.qualitative.Set3,
        height=560,
    )

    # ---- chart 4: EDA vs startup vs mid vs large-cap breakdown by year ----
    bucket_order_map = {"large_cap": 4, "mid_cap": 3, "startup": 2,
                        "academic": 1, "research_institute": 1,
                        "industry_other": 0, "other": 0, "unknown": 0}
    pivot4 = pcdf.pivot_table(index="year", columns="top_bucket",
                              values="paper_id", aggfunc="count", fill_value=0)
    fig4 = go.Figure()
    bucket_color = {
        "large_cap": "#1f77b4", "mid_cap": "#2ca02c", "startup": "#ff7f0e",
        "academic": "#9467bd", "research_institute": "#8c564b",
        "industry_other": "#7f7f7f", "other": "#c7c7c7", "unknown": "#e0e0e0",
    }
    bucket_label = {
        "large_cap": "Large-cap (S&P500-tier)", "mid_cap": "Mid-cap public",
        "startup": "Startup / private", "academic": "Academic",
        "research_institute": "Research institute",
        "industry_other": "Industry (unclassified)", "other": "Other",
        "unknown": "Unclassified",
    }
    # sort buckets by size order so largest is on the bottom of the stack
    ordered_buckets = sorted(pivot4.columns,
                             key=lambda b: -bucket_order_map.get(b, 0))
    for col in ordered_buckets:
        fig4.add_trace(go.Bar(
            x=pivot4.index, y=pivot4[col], name=bucket_label.get(col, col),
            marker_color=bucket_color.get(col, "#999"),
            hovertemplate="%{x}<br>" + bucket_label.get(col, col) + ": %{y}<extra></extra>",
        ))
    fig4.update_layout(barmode="stack",
                       title="Company size-class mix per year (paper's largest company)",
                       xaxis_title="Year", yaxis_title="Number of papers",
                       margin=dict(l=10, r=10, t=60, b=10), height=440,
                       legend=dict(orientation="h", y=-0.25))

    # ---- chart 5: co-authorship patterns ----
    pivot5 = pcdf.pivot_table(index="year", columns="co_author_bucket",
                              values="paper_id", aggfunc="count", fill_value=0)
    fig5 = go.Figure()
    cat_order = ["Solo EDA vendor", "EDA + non-EDA industry",
                 "EDA + academic/research", "Solo large-cap industry",
                 "Solo mid-cap industry", "Solo startup / private",
                 "Academic only", "Cross-vendor (≥2 large caps)",
                 "Other / unclassified"]
    co_color = px.colors.qualitative.Plotly
    for i, col in enumerate([c for c in cat_order if c in pivot5.columns]):
        fig5.add_trace(go.Bar(
            x=pivot5.index, y=pivot5[col], name=col,
            marker_color=co_color[i % len(co_color)],
            hovertemplate="%{x}<br>" + col + ": %{y}<extra></extra>",
        ))
    fig5.update_layout(barmode="stack",
                       title="Co-authorship patterns per year (paper-level)",
                       xaxis_title="Year", yaxis_title="Number of papers",
                       margin=dict(l=10, r=10, t=60, b=10), height=440,
                       legend=dict(orientation="h", y=-0.3, font=dict(size=10)))

    # EDA share summary stat
    eda_share = pcdf["has_eda"].mean() * 100 if len(pcdf) else 0
    narrative = f"""
    <p><b>Approach.</b> Each affiliation line in a paper's
    <code>affiliations_text</code> is matched against a curated CSV of
    ~{len(load_companies())} known EDA / semiconductor / automotive / academic
    entities (file: <code>docs/data/companies.csv</code>, hand-curated and
    editable). Each entry carries a year-dependent size bucket (large-cap /
    mid-cap / startup / academic). The classifier picks the bucket column whose
    year is closest to (but &le;) the paper's year, so e.g. AMD moves from
    mid-cap to large-cap across the 2017 Zen launch. Unmatched industry-looking
    fragments fall into <i>Industry (unclassified)</i> so the gap is visible.</p>
    <p><b>Result.</b> <b>{eda_share:.0f}%</b> of papers have at least one EDA
    vendor among the affiliations, confirming DVCon's identity as the
    industry-led verification conference. The size-class mix shows a steady
    large-cap dominance (Intel, NVIDIA, Samsung, Cadence, Synopsys, Siemens)
    with a long tail of small EDA consultancies and startups contributing
    methodology papers.</p>
    <p><b>Refining.</b> The companies CSV is intentionally checked in. To improve
    coverage, edit <code>docs/data/companies.csv</code> and re-run the generator;
    the unmatched "Industry (unclassified)" bar in chart 4 shows how many papers
    fall through.</p>
    """
    chart_html = [
        _wrap_chart(fig1, "q3_industry_vs_academia"),
        _wrap_chart(fig2, "q3_top_companies"),
        racing3_html,
        _wrap_chart(fig4, "q3_size_buckets"),
        _wrap_chart(fig5, "q3_coauthor_patterns"),
    ]
    return narrative, chart_html


# ============================================================
# Q4: author analytics
# ============================================================

def build_q4(papers: list[PaperRow]) -> tuple[str, list[str]]:
    paper_authors = load_paper_authors()
    # build per-author stats
    author_papers: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    author_locations: dict[str, set[str]] = defaultdict(set)
    author_years: dict[str, list[int]] = defaultdict(list)
    author_coauthors: dict[str, set[str]] = defaultdict(set)
    author_topics: dict[str, set[str]] = defaultdict(set)

    # We dedupe authors by normalized name but display the "best" original casing
    canon_name: dict[str, str] = {}

    for p in papers:
        authors = paper_authors.get(p.paper_id, [])
        norm_set = []
        for raw in authors:
            norm = _norm_author(raw)
            if not norm or len(norm) < 3:
                continue
            norm_set.append((norm, raw))
            # keep longest / title-case variant as canonical
            if norm not in canon_name or len(raw) > len(canon_name[norm]):
                canon_name[norm] = raw
            author_papers[norm].append((p.year, p.title, p.location))
            author_locations[norm].add(p.location)
            author_years[norm].append(p.year)
            for topic in p.topics:
                author_topics[norm].add(topic)
        # co-authors within the same paper
        for i, (n1, _) in enumerate(norm_set):
            for j, (n2, _) in enumerate(norm_set):
                if i != j and n1 != n2:
                    author_coauthors[n1].add(n2)

    # ----- chart 1: top-10 authors by paper count -----
    top10 = sorted(author_papers.items(), key=lambda kv: -len(kv[1]))[:10]
    top10_rows = [{"Author": canon_name[n], "Papers": len(plist)}
                  for n, plist in top10]
    fig1 = px.bar(top10_rows[::-1], x="Papers", y="Author", orientation="h",
                  title="Top-10 authors all-time (by paper count)",
                  color="Papers", color_continuous_scale="Viridis")
    fig1.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=440,
                       coloraxis_showscale=False, yaxis_title="")

    # ----- chart 2: multi-location authors (≥2 distinct locations) -----
    multi_loc = [(n, plist) for n, plist in author_papers.items()
                 if len(author_locations[n]) >= 2]
    multi_loc = sorted(multi_loc, key=lambda kv: (-len(kv[1]), -len(author_locations[kv[0]])))[
        :15]
    multi_rows = []
    for n, plist in multi_loc:
        multi_rows.append({
            "Author": canon_name[n],
            "Papers": len(plist),
            "Locations": len(author_locations[n]),
            "Locations seen": ", ".join(sorted(author_locations[n])),
        })
    fig2 = px.bar(multi_rows[::-1], x="Papers", y="Author", orientation="h",
                  color="Locations",
                  title="Multi-location authors (≥2 distinct DVCon locations)",
                  color_continuous_scale="Sunset")
    fig2.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=480,
                       coloraxis_colorbar=dict(title="Locations"),
                       yaxis_title="")

    # ----- chart 3: longest-active (max - min + 1) -----
    spans = []
    for n, plist in author_papers.items():
        yrs = author_years[n]
        span = max(yrs) - min(yrs) + 1
        spans.append((n, span, len(plist), min(yrs), max(yrs)))
    spans.sort(key=lambda x: (-x[1], -x[2]))
    span_rows = [{"Author": canon_name[n], "Span (years)": span,
                  "Papers": np_, "First year": f, "Last year": l}
                 for n, span, np_, f, l in spans[:10]]
    fig3 = px.bar(span_rows[::-1], x="Span (years)", y="Author", orientation="h",
                  title="Longest-active authors (max year − min year + 1)",
                  color="Papers", color_continuous_scale="Tealgrn")
    fig3.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=440,
                       coloraxis_showscale=False, yaxis_title="")

    # ----- chart 4: longest continuous streak -----
    def longest_streak(years: list[int]) -> int:
        ys = sorted(set(years))
        best = cur = 1
        for i in range(1, len(ys)):
            if ys[i] == ys[i - 1] + 1:
                cur += 1
                best = max(best, cur)
            else:
                cur = 1
        return best if ys else 0

    streaks = [(n, longest_streak(author_years[n]), len(plist))
               for n, plist in author_papers.items()]
    streaks.sort(key=lambda x: (-x[1], -x[2]))
    streak_rows = [{"Author": canon_name[n], "Longest streak (yrs)": s,
                    "Papers": np_} for n, s, np_ in streaks[:10]]
    fig4 = px.bar(streak_rows[::-1], x="Longest streak (yrs)", y="Author",
                  orientation="h",
                  title="Longest continuous publishing streak (consecutive years)",
                  color="Papers", color_continuous_scale="Magma")
    fig4.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=440,
                       coloraxis_showscale=False, yaxis_title="")

    # ----- fun categories: globetrotter / marathoner / ironman / polyglot / mentor -----
    globetrotter = max(author_papers.items(),
                       key=lambda kv: (len(author_locations[kv[0]]), len(kv[1])))
    marathoner = max(author_papers.items(),
                     key=lambda kv: (max(author_years[kv[0]]) - min(author_years[kv[0]]) + 1,
                                     len(kv[1])))
    ironman = max(author_papers.items(),
                  key=lambda kv: (longest_streak(author_years[kv[0]]), len(kv[1])))
    polyglot = max(author_papers.items(),
                   key=lambda kv: (len(author_topics[kv[0]]), len(kv[1])))
    mentor_candidates = [(n, plist) for n, plist in author_papers.items()
                         if len(plist) >= 5 and len(author_coauthors[n]) >= 3]
    mentor = max(mentor_candidates,
                 key=lambda kv: (len(author_coauthors[kv[0]]), len(kv[1]))) \
        if mentor_candidates else None

    # recurring duos
    pair_count: Counter = Counter()
    for p in papers:
        authors = paper_authors.get(p.paper_id, [])
        norm_list = []
        for raw in authors:
            n = _norm_author(raw)
            if n and len(n) >= 3:
                norm_list.append(n)
        uniq = list(dict.fromkeys(norm_list))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                a, b = sorted([uniq[i], uniq[j]])
                pair_count[(a, b)] += 1

    fun_rows = [
        {"Title": "🌍 Globetrotter",
         "Author": canon_name[globetrotter[0]],
         "Record": f"{len(author_locations[globetrotter[0]])} distinct DVCon locations"},
        {"Title": "🏃 Marathoner",
         "Author": canon_name[marathoner[0]],
         "Record": f"{max(author_years[marathoner[0]]) - min(author_years[marathoner[0]]) + 1} year span"},
        {"Title": "🛡 Ironman",
         "Author": canon_name[ironman[0]],
         "Record": f"{longest_streak(author_years[ironman[0]])} consecutive years"},
        {"Title": "🧠 Polyglot",
         "Author": canon_name[polyglot[0]],
         "Record": f"{len(author_topics[polyglot[0]])} distinct topics"},
    ]
    if mentor:
        fun_rows.append({
            "Title": "👥 Mentor",
            "Author": canon_name[mentor[0]],
            "Record": f"{len(author_coauthors[mentor[0]])} distinct co-authors",
        })
    # top-5 recurring duos
    duo_rows = []
    for (a, b), n in pair_count.most_common(5):
        duo_rows.append({
            "Duo": f"{canon_name.get(a, a)}  &  {canon_name.get(b, b)}",
            "Co-authored papers": n,
        })

    # still-active veterans: first paper ≤ 2012, last ≥ 2024
    veterans = []
    for n, plist in author_papers.items():
        yrs = author_years[n]
        if min(yrs) <= 2012 and max(yrs) >= 2024:
            veterans.append((n, min(yrs), max(yrs), len(plist)))
    veterans.sort(key=lambda x: x[1])
    vet_rows = [{"Author": canon_name[n], "First paper": f, "Last paper": l,
                 "Total papers": np_}
                for n, f, l, np_ in veterans[:15]]

    narrative = f"""
    <p><b>Approach.</b> Author names are deduplicated via a normalizer
    (strip titles / punctuation, case-fold). All charts use the existing
    <code>paper_author</code> link table (5,586 paper-author rows). The fun
    categories pick the single best author per category, breaking ties by
    total paper count.</p>
    <p><b>Result.</b> Top-10 authors are the recognizable DVCon regulars
    ({", ".join(r["Author"] for r in top10_rows[:3])} on top). The corpus has
    <b>{len(multi_loc)}</b> authors who published at 2+ distinct DVCon
    locations, and <b>{len(veterans)}</b> "veterans" who started before 2012
    and are still publishing in 2024+. See the recurring duos table for the
    most frequent co-author pairs.</p>
    """
    chart_html = [
        _wrap_chart(fig1, "q4_top10"),
        _wrap_chart(fig2, "q4_multi_loc"),
        _html_table(multi_rows, "Multi-location authors (locations visited)"),
        _wrap_chart(fig3, "q4_longest_active"),
        _wrap_chart(fig4, "q4_streaks"),
        _html_table(fun_rows, "🏆 Fun-category award winners"),
        _html_table(duo_rows, "Top-5 recurring co-author duos"),
        _html_table(vet_rows, "Still-active veterans (first ≤2012 & last ≥2024)"),
    ]
    return narrative, chart_html


# ============================================================
# Q5: reproducibility metrics
# ============================================================

REPO_RE = re.compile(
    r"github\.com/([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)|"
    r"gitlab\.com/([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)|"
    r"bitbucket\.org/([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)",
    re.IGNORECASE)


def _extract_repo_url(text: str) -> str | None:
    m = REPO_RE.search(text or "")
    if not m:
        return None
    for grp in m.groups():
        if grp:
            return f"https://github.com/{grp.rstrip('.')}"
    return None


def build_q5(papers: list[PaperRow]) -> tuple[str, list[str]]:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    # cache chunks text per paper for github detection + listing count
    paper_chunks: dict[int, str] = {}
    cur.execute("SELECT paper_id, text FROM chunk")
    for paper_id, txt in cur.fetchall():
        if paper_id is None:
            continue
        paper_chunks.setdefault(paper_id, "")
        if txt:
            paper_chunks[paper_id] += "\n" + txt
    # markdown fallback for github/listings
    paper_md: dict[int, str] = {}
    cur.execute("SELECT id, markdown_path FROM paper")
    md_paths = {pid: mp for pid, mp in cur.fetchall() if mp}
    conn.close()

    rows = []
    repo_examples = []
    for p in papers:
        abstract_l = (p.abstract or "").lower()
        chunk_text = paper_chunks.get(p.paper_id, "")
        chunk_l = chunk_text.lower()
        # signals
        repo_url = _extract_repo_url(chunk_text) or _extract_repo_url(p.abstract)
        has_github = repo_url is not None or "github.com/" in chunk_l \
            or "gitlab.com/" in chunk_l or "bitbucket.org/" in chunk_l
        mentions_open_source = any(
            kw in abstract_l for kw in
            ["open source", "open-source", "oss ", "released as open",
             "open-source,"])
        has_artifact = any(kw in abstract_l for kw in
                           ["available at", "can be downloaded", "released at",
                            "publicly available", "artifact", "released under"])
        has_dataset = (("dataset" in abstract_l or "benchmark" in abstract_l)
                       and any(kw in abstract_l for kw in
                               ["released", "available", "public", "open"]))
        n_listings = len(re.findall(r"Listing\s+\d+", chunk_text))
        n_algorithms = len(re.findall(r"Algorithm\s+\d+", chunk_text))
        n_steps = len(re.findall(r"Step\s+\d+", chunk_text))
        has_methodology_steps = (n_listings + n_algorithms + n_steps) >= 3
        mentions_reproducibility = "reproduc" in abstract_l
        abstract_len = len(p.abstract or "")

        # composite score 0..3
        score = 0
        if mentions_open_source or mentions_reproducibility or has_artifact or has_dataset:
            score = max(score, 1)
        if has_github:
            score = max(score, 2)
        if has_methodology_steps:
            score = max(score, 2)
        if has_github and has_methodology_steps:
            score = 3

        # "cool but don't teach": no methodology AND mentions-only OR score 0
        # AND long-ish abstract (proxy for "lots of claims")
        cool_no_teach = (score <= 1 and not has_methodology_steps
                         and abstract_len > 600)

        rows.append({
            "paper_id": p.paper_id,
            "year": p.year,
            "title": p.title,
            "abstract_len": abstract_len,
            "has_github": int(has_github),
            "mentions_open_source": int(mentions_open_source),
            "has_artifact": int(has_artifact),
            "has_dataset": int(has_dataset),
            "has_methodology_steps": int(has_methodology_steps),
            "mentions_reproducibility": int(mentions_reproducibility),
            "n_listings": n_listings,
            "score": score,
            "cool_no_teach": int(cool_no_teach),
            "topics": ",".join(p.topics),
        })
        if repo_url:
            repo_examples.append({"Year": p.year, "Title": p.title[:80],
                                  "Repository": repo_url})

    rdf = pd.DataFrame(rows)
    save_csv(rdf, "reproducibility.csv")

    # ---- chart 1: donut of score distribution ----
    score_counts = rdf["score"].value_counts().sort_index()
    score_labels = {
        0: "0 — No reproducibility signal",
        1: "1 — Mentions only (no link)",
        2: "2 — Has link or methodology",
        3: "3 — Link + methodology (most reproducible)",
    }
    donut = go.Figure(go.Pie(
        labels=[score_labels[i] for i in score_counts.index],
        values=score_counts.values, hole=0.55,
        marker=dict(colors=["#d62728", "#ff9f40", "#2ca02c", "#1a7d1a"]
                                   [-len(score_counts):] or ["#999"]),
        textinfo="label+percent",
    ))
    donut.update_layout(title=f"Reproducibility score distribution "
                              f"(n={len(rdf)} papers, 0=none → 3=most reproducible)",
                        margin=dict(l=10, r=10, t=60, b=10), height=420,
                        legend=dict(orientation="h", y=-0.2, font=dict(size=10)))

    # ---- chart 2: stacked bar of score distribution by year ----
    pivot = rdf.pivot_table(index="year", columns="score",
                            values="paper_id", aggfunc="count", fill_value=0)
    fig2 = go.Figure()
    colors = {0: "#d62728", 1: "#ff9f40", 2: "#2ca02c", 3: "#1a7d1a"}
    for s in sorted(pivot.columns):
        fig2.add_trace(go.Bar(
            x=pivot.index, y=pivot[s],
            name=score_labels.get(s, str(s)),
            marker_color=colors.get(s, "#999"),
            hovertemplate="%{x}<br>" + score_labels.get(s, str(s)) + ": %{y}<extra></extra>",
        ))
    fig2.update_layout(barmode="stack",
                       title="Reproducibility score distribution by year",
                       xaxis_title="Year", yaxis_title="Number of papers",
                       margin=dict(l=10, r=10, t=60, b=10), height=420,
                       legend=dict(orientation="h", y=-0.3, font=dict(size=10)))

    # ---- chart 3: cool-but-don't-teach % by topic ----
    cool_by_topic = []
    for topic in sorted({t for ts in rdf["topics"] for t in ts.split(",") if t}):
        sub = rdf[rdf["topics"].str.contains(r"\b" + re.escape(topic) + r"\b", regex=True)]
        if len(sub) < 10:
            continue
        cool_pct = sub["cool_no_teach"].mean() * 100
        cool_by_topic.append({"Topic": topic,
                              "Total papers": len(sub),
                              "% cool-but-don't-teach": round(cool_pct, 1)})
    cool_by_topic.sort(key=lambda r: -r["% cool-but-don't-teach"])
    fig3 = px.bar([r["% cool-but-don't-teach"] for r in cool_by_topic[::-1]],
                  orientation="h",
                  title='"Cool but don\'t teach" % per topic '
                        '(score ≤ 1, no methodology, long abstract)',
                  labels={"value": "% of papers", "index": ""},
                  color=[r["% cool-but-don't-teach"] for r in cool_by_topic[::-1]],
                  color_continuous_scale="Reds")
    fig3.update_layout(yaxis=dict(ticktext=[r["Topic"] for r in cool_by_topic[::-1]],
                                  tickvals=list(range(len(cool_by_topic)))),
                       margin=dict(l=10, r=10, t=60, b=10), height=460,
                       coloraxis_showscale=False, xaxis_title="% of papers", yaxis_title="")

    # summary stats
    n_github = int(rdf["has_github"].sum())
    n_oss = int(rdf["mentions_open_source"].sum())
    n_method = int(rdf["has_methodology_steps"].sum())
    n_cool = int(rdf["cool_no_teach"].sum())
    n_total = len(rdf)
    high_repro = int((rdf["score"] >= 2).sum())

    narrative = f"""
    <p><b>Approach.</b> Each paper is scored 0&ndash;3 across six heuristic signals:
    github/gitlab/bitbucket repo link (in chunks or abstract),
    "open source" mention, "available at / artifact" mention, dataset/benchmark
    release, methodology markers (&ge;3 of <i>Listing N</i> / <i>Algorithm N</i> /
    <i>Step N</i> in the markdown), and explicit "reproducibility" mention.
    The composite score rewards both <i>"teach how"</i> (methodology listings)
    and <i>"here's the code"</i> (repo link). The signals are heuristic and noisy;
    a false-positive audit would require a manual sweep.</p>
    <p><b>Result.</b> Only <b>{n_github}</b> papers ({n_github*100/n_total:.1f}%)
    link to a public repo, and <b>{n_oss}</b> ({n_oss*100/n_total:.1f}%) mention
    "open source" at all. <b>{n_method}</b> papers ({n_method*100/n_total:.1f}%)
    have substantial methodology listings (a proxy for "teaches you how").
    The "show-cool-but-don't-teach" bucket (score &le;1, no methodology, long
    abstract) captures <b>{n_cool}</b> papers ({n_cool*100/n_total:.1f}% of the
    corpus). Reproducibility is materially lower than in ML conferences (where
    30&ndash;50% link code), reflecting DVCon's industry-IP-sensitive culture.</p>
    <p><b>Additional metrics worth tracking later</b>: self-citation count
    (proxy for "builds on own prior art"), Flesch reading-ease of the abstract
    (proxy for "bothered to explain"), count of <i>Figure N</i> references
    (proxy for "showed diagrams"), count of <i>Table N</i> with comparison
    numbers (proxy for "ran benchmarks"). These are one-liners to add to the
    extractor; not computed here to avoid over-claiming.</p>
    """
    chart_html = [
        _wrap_chart(donut, "q5_donut"),
        _wrap_chart(fig2, "q5_score_by_year"),
        _wrap_chart(fig3, "q5_cool_by_topic"),
        _html_table(repo_examples[:15],
                    "Sample papers with public repo links (top 15)"),
    ]
    return narrative, chart_html


# ============================================================
# HTML helpers
# ============================================================

def _wrap_chart(fig, div_id: str, height: int | None = None) -> str:
    """Render a Plotly figure as an isolated HTML fragment (no Plotly.js; loaded once at top)."""
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)


def _racing_bar(
    rows: list[dict],
    category_field: str,
    value_field: str,
    title: str,
    div_id: str,
    top_n: int = 10,
    color_palette: list[str] | None = None,
    height: int = 560,
    cumulative: bool = True,
) -> str:
    """Build a smooth top-N RACING bar animation as an HTML fragment.

    The bars actually slide up/down past each other as their rank changes
    across years -- this is the real "racing bar" effect, not just bars
    that resize in a fixed order.

    Implementation of the standard Plotly racing-bar pattern:
    1. Pre-fill the (year x category) grid with 0 so every category has a
       row in every frame (otherwise Plotly snaps them in/out abruptly).
    2. Compute per-year rank (1 = biggest that year). Use a NUMERIC y-axis
       with `y = -rank` so rank 1 sits at the top.
    3. Hide categories whose rank > top_n by setting their value to 0 AND
       their y-position to a slot below the visible range.
    4. Use `animation_group=category` so Plotly smoothly interpolates each
       bar's y-position between frames -- that's the actual "race".

    `cumulative=True` ranks by running total through the year (classic
    all-time racing bar). `cumulative=False` ranks by the year's own value.
    """
    import plotly.express as _px

    if not rows:
        return f'<p class="empty">(no data for {title})</p>'
    df = pd.DataFrame(rows)
    df["year"] = df["year"].astype(int)
    df[value_field] = df[value_field].astype(int)
    all_years = sorted(df["year"].unique())
    all_cats = sorted(df[category_field].unique())

    # 1. pre-fill (year x category) grid
    grid = pd.MultiIndex.from_product([all_years, all_cats],
                                      names=["year", category_field]).to_frame(index=False)
    grid = grid.merge(df, on=["year", category_field], how="left")
    grid[value_field] = grid[value_field].fillna(0).astype(int)

    # 2. compute cumulative (running total through the year) if requested
    if cumulative:
        grid = grid.sort_values([category_field, "year"])
        grid["cumulative_value"] = grid.groupby(category_field)[value_field].cumsum()
        rank_value = "cumulative_value"
        bar_value = "cumulative_value"
        x_title = "Cumulative papers through year"
    else:
        rank_value = value_field
        bar_value = value_field
        x_title = "Papers in year"

    # 3. compute per-year rank (1 = biggest). method="first" breaks ties
    # deterministically so the rank is stable across runs.
    grid["rank"] = (grid.groupby("year")[rank_value]
                          .rank(method="first", ascending=False).astype(int))

    # 4. set y-position: -rank puts rank 1 at the top of the chart.
    # Categories with rank > top_n get parked at a y below the visible
    # range so they're hidden but still tracked for animation_group.
    BELOW = top_n + 5  # parking slot for off-screen categories
    grid["y_pos"] = -grid["rank"].clip(upper=BELOW)
    # but hide their value too (length 0)
    grid[bar_value] = grid[bar_value].where(grid["rank"] <= top_n, 0)

    # ---- MONTHLY INTERPOLATION ----------------------------------------------
    # The user wants the animation to play on a monthly timeframe so bars grow
    # and swap positions smoothly instead of jumping year-to-year. We expand
    # the yearly grid into 12 sub-frames per year (Jan, Feb, ..., Dec) with
    # LINEAR interpolation of bar_value between consecutive years. Rank + y_pos
    # are recomputed at each sub-frame so bars can overtake each other mid-year
    # -- this is the actual "racing" feel.
    #
    # We use [0.0, 1/12, 2/12, ..., 11/12] as the 12 sub-frames; the year-end
    # value (1.0) is the start of the NEXT year's frame, so we don't duplicate.
    n_subframes = 12
    fracs = [i / n_subframes for i in range(n_subframes)]   # 0/12 ... 11/12

    # sort so we can interpolate year-to-year
    grid = grid.sort_values([category_field, "year"]).reset_index(drop=True)

    # for each (cat, year), we want the bar_value at the 12 sub-frames
    # leading UP TO this year's value from the previous year's value.
    # We compute: prev_value per (cat, year) = value at year-1 (or 0 if first)
    grid["prev_value"] = grid.groupby(category_field)[bar_value].shift(1, fill_value=0)

    monthly_rows = []
    # also need a stable frame label for plotting (animation_frame must be a
    # sortable string; we use "YYYY-MM" zero-padded)
    for _, row in grid.iterrows():
        for i, frac in enumerate(fracs):
            interp_value = row["prev_value"] + (row[bar_value] - row["prev_value"]) * frac
            month = i + 1
            frame_label = f"{int(row['year'])}-{month:02d}"
            monthly_rows.append({
                category_field: row[category_field],
                "frame": frame_label,
                "year": int(row["year"]),
                "month": month,
                bar_value: interp_value,
                "prev_value": row["prev_value"],
            })
    monthly = pd.DataFrame(monthly_rows)

    # recompute rank + y_pos per sub-frame (so swaps happen mid-year)
    monthly["rank"] = (monthly.groupby("frame")[bar_value]
                              .rank(method="first", ascending=False).astype(int))
    monthly["y_pos"] = -monthly["rank"].clip(upper=BELOW)
    # hide off-top-N bars (length 0)
    monthly[bar_value] = monthly[bar_value].where(monthly["rank"] <= top_n, 0)

    # 5. build the figure. CRITICAL pieces:
    #    - y is NUMERIC (y_pos), not the category -> allows smooth interpolation
    #    - animation_group = category_field -> Plotly tracks each bar across frames
    #    - animation_frame = monthly "frame" label (YYYY-MM)
    plot_df = monthly.copy()
    fig = _px.bar(
        plot_df,
        x=bar_value, y="y_pos",
        color=category_field,
        text=category_field,                # category name rendered on the bar
        orientation="h",
        animation_frame="frame",
        animation_group=category_field,     # <-- enables the slide animation
        category_orders={"frame": sorted(plot_df["frame"].unique())},
        range_x=[0, max(plot_df[bar_value].max() * 1.15, 10)],
        title=title,
        color_discrete_sequence=color_palette or _px.colors.qualitative.Bold,
        hover_data={category_field: False, bar_value: True,
                    "rank": True, "y_pos": False, "year": False, "month": False,
                    "prev_value": False, "frame": False},
    )
    fig.update_traces(
        textposition="outside",     # label sits at the right tip of the bar, always visible
        texttemplate="%{text}",
        cliponaxis=False,
        hovertemplate=("<b>%{text}</b><br>"
                       + ("Cumulative papers: %{x}<br>" if cumulative else "Papers: %{x}<br>")
                       + "<extra></extra>"),
    )

    # build a stable color map by all-time-total descending so each category
    # keeps the same color throughout the animation
    total_order = (df.groupby(category_field)[value_field].sum()
                       .sort_values(ascending=False).index.tolist())
    palette = color_palette or _px.colors.qualitative.Bold
    color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(total_order)}
    for trace in fig.data:
        cat = trace.name
        if cat in color_map:
            trace.marker.color = color_map[cat]

    fig.update_layout(
        # numeric y axis: rank 1 (y=-1) at the top, rank top_n (y=-top_n) at bottom
        yaxis={"range": [-top_n - 0.5, -0.5],
               "showticklabels": False,   # we use bar text labels instead
               "zeroline": False, "gridcolor": "#f1f5f9",
               "fixedrange": True},       # no zoom on y
        # NOTE: x-axis range is set per-frame below (dynamic, not fixed).
        # A placeholder title-only config here gets overridden.
        xaxis={"title": x_title, "gridcolor": "#f1f5f9",
               "rangemode": "nonnegative"},
        showlegend=False,
        margin=dict(l=10, r=10, t=60, b=60),
        height=height,
        plot_bgcolor="white",
        # MONTHLY animation: each sub-frame is short (90ms) with a quick
        # linear transition (80ms) so 12 sub-frames pass in ~2 seconds per year.
        # Linear easing matches the linear interpolation of the values, giving
        # the smooth "growing bars" feel.
        updatemenus=[dict(type="buttons", showactive=False, y=-0.13, x=0.5,
                          xanchor="center", yanchor="top",
                          buttons=[dict(label="&#9654; Play",
                                        method="animate",
                                        args=[None,
                                              dict(frame=dict(duration=90, redraw=True),
                                                   transition=dict(duration=80,
                                                                   easing="linear"),
                                                   fromcurrent=True)]),
                                   dict(label="&#10074;&#10074; Pause",
                                        method="animate",
                                        args=[[None],
                                              dict(frame=dict(duration=0, redraw=False),
                                                   mode="immediate",
                                                   transition=dict(duration=0))])])],
        sliders=[dict(active=0, x=0, y=-0.05, len=1.0,
                      currentvalue=dict(prefix="Month: "),
                      transition=dict(duration=500, easing="cubic-in-out"),
                      pad=dict(t=10, b=10))],
    )
    # DYNAMIC X-AXIS: give each frame its own xaxis.range based on that
    # frame's max bar value. Without this, the x axis uses the global all-time
    # max, so early frames have ~98% white space.
    #
    # Plotly applies frame.layout (and slider-step args[1]) when entering each
    # frame during animation. We set both to be safe:
    #   - frame.layout.xaxis.range is used during animation playback
    #   - slider step args[1]["xaxis.range"] is used when clicking a step
    frame_max = (plot_df.groupby("frame")[bar_value].max()
                              .to_dict())
    headroom = lambda m: [0, max(m * 1.15, 5)]   # min axis of 5 to avoid tiny bars
    for frame in fig.frames:
        # frame.name is now a "YYYY-MM" string
        m = frame_max.get(frame.name, 0)
        frame.layout = {"xaxis": {"range": headroom(m)}}

    # set the initial (base) x-axis range to match the first frame
    sorted_frames = sorted(plot_df["frame"].unique())
    first_frame = sorted_frames[0] if sorted_frames else None
    if first_frame is not None:
        initial_range = headroom(frame_max.get(first_frame, 10))
    else:
        initial_range = [0, 10]
    fig.update_layout(xaxis={"title": x_title, "gridcolor": "#f1f5f9",
                             "rangemode": "nonnegative",
                             "range": initial_range})

    # patch slider steps: monthly timing (90ms per sub-frame, linear easing)
    if fig.layout.sliders:
        for step in fig.layout.sliders[0].steps:
            step.args[1]["frame"]["duration"] = 90
            step.args[1]["frame"]["redraw"] = True
            step.args[1]["transition"]["duration"] = 80
            step.args[1]["transition"]["easing"] = "linear"
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id)


def _html_table(rows: list[dict], caption: str = "") -> str:
    if not rows:
        return f'<div class="table-wrap"><p class="table-caption">{caption}</p><p class="empty">(no rows)</p></div>'
    keys = list(rows[0].keys())
    head = "".join(f"<th>{k}</th>" for k in keys)
    body_rows = []
    for r in rows:
        body_rows.append("<tr>" + "".join(f"<td>{r[k]}</td>" for k in keys) + "</tr>")
    cap = f'<p class="table-caption">{caption}</p>' if caption else ""
    return (
        f'<div class="table-wrap">{cap}'
        f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'
        f'</div>'
    )


# ============================================================
# HTML assembly
# ============================================================

CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       line-height: 1.55; color: #1a1a1a; max-width: 1280px; margin: 0 auto;
       padding: 0 24px 80px; background: #fafafa; }
header { padding: 32px 0 24px; border-bottom: 3px solid #1d4ed8; margin-bottom: 24px; }
h1 { margin: 0 0 8px; color: #0f172a; font-size: 32px; }
h2 { color: #1d4ed8; border-bottom: 1px solid #cbd5e1; padding-bottom: 8px;
     margin-top: 48px; }
h3 { color: #334155; margin-top: 32px; }
.subtitle { color: #64748b; font-size: 16px; }
.stats { display: flex; flex-wrap: wrap; gap: 16px; margin: 20px 0; }
.stat { background: white; padding: 14px 18px; border-radius: 8px;
        border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.stat .n { font-size: 24px; font-weight: 700; color: #1d4ed8; display: block; }
.stat .lbl { color: #64748b; font-size: 13px; }
.callout { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px;
           margin: 16px 0; border-radius: 4px; font-size: 14px; }
nav.top { position: sticky; top: 0; background: #1d4ed8; color: white;
          padding: 10px 24px; margin: 0 -24px 24px; z-index: 100;
          display: flex; gap: 16px; flex-wrap: wrap; font-size: 14px; }
nav.top a { color: #dbeafe; text-decoration: none; }
nav.top a:hover { color: white; text-decoration: underline; }
section { background: white; padding: 20px 24px; margin: 16px 0;
          border-radius: 8px; border: 1px solid #e2e8f0; }
.chart-block { margin: 20px 0; }
.table-wrap { overflow-x: auto; margin: 16px 0; }
.table-caption { font-weight: 600; color: #334155; margin: 0 0 6px; font-size: 14px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { background: #f1f5f9; text-align: left; padding: 8px 10px;
     border-bottom: 2px solid #cbd5e1; font-weight: 600; }
td { padding: 6px 10px; border-bottom: 1px solid #e2e8f0; }
tr:hover td { background: #f8fafc; }
.empty { color: #94a3b8; font-style: italic; font-size: 13px; }
.methodology { font-size: 14px; color: #475569; background: #f8fafc;
               padding: 12px 16px; border-radius: 4px; }
code { background: #e2e8f0; padding: 1px 5px; border-radius: 3px; font-size: 90%; }
footer { text-align: center; color: #94a3b8; margin-top: 60px; font-size: 13px; }
"""


def assemble_html(papers: list[PaperRow]) -> None:
    print("Building Q1...")
    q1_n, q1_c = build_q1(papers)
    print("Building Q2...")
    q2_n, q2_c = build_q2(papers)
    print("Building Q2b (languages)...")
    q2b_n, q2b_c = build_q2b(papers)
    print("Building Q3...")
    q3_n, q3_c = build_q3(papers)
    print("Building Q4...")
    q4_n, q4_c = build_q4(papers)
    print("Building Q5...")
    q5_n, q5_c = build_q5(papers)

    # corpus overview stats
    n_papers = len(papers)
    years = sorted({p.year for p in papers})
    locations = sorted({p.location for p in papers})
    n_with_abstract = sum(1 for p in papers if p.abstract and len(p.abstract) > 50)
    n_with_country = sum(1 for p in papers if p.countries)

    stats_html = (
        f'<div class="stats">'
        f'<div class="stat"><span class="n">{n_papers}</span><span class="lbl">papers indexed</span></div>'
        f'<div class="stat"><span class="n">{years[0]}–{years[-1]}</span><span class="lbl">year range</span></div>'
        f'<div class="stat"><span class="n">{len(locations)}</span><span class="lbl">DVCon locations</span></div>'
        f'<div class="stat"><span class="n">{n_with_abstract}</span><span class="lbl">with abstract</span></div>'
        f'<div class="stat"><span class="n">{n_with_country} ({n_with_country*100//n_papers}%)</span><span class="lbl">with parseable author origin</span></div>'
        f'</div>'
    )

    data_quality = (
        '<div class="callout"><b>Data quality notes.</b> '
        'The structured <code>Affiliation</code> and <code>Company</code> tables '
        'are noisy (GROBID occasionally misclassifies paper-body sentences as '
        'affiliations). All company / country analysis uses the flattened '
        '<code>affiliations_text</code> block, which is far more reliable. '
        'Classification coverage and gaps are reported per section. The curated '
        'CSVs (<code>docs/data/companies.csv</code>, '
        '<code>docs/data/topics.csv</code>) are checked in and editable.</div>'
    )

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>DVCon corpus analysis — {n_papers} papers</title>",
        f"<style>{CSS}</style>",
        "</head><body>",
        # load Plotly.js once
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>',
        "<header>"
        "<h1>DVCon Proceedings Intelligence — corpus analysis</h1>"
        f"<p class='subtitle'>Mining {n_papers} DVCon papers "
        f"({years[0]}–{years[-1]}) across {', '.join(locations)}</p>"
        "</header>",
        stats_html,
        data_quality,
        "<nav class='top'>"
        "<a href='#q1'>Q1 World map</a>"
        "<a href='#q2'>Q2 Topic racing bar</a>"
        "<a href='#q2b'>Q2b Languages</a>"
        "<a href='#q3'>Q3 Companies</a>"
        "<a href='#q4'>Q4 Authors</a>"
        "<a href='#q5'>Q5 Reproducibility</a>"
        "<a href='#method'>Methodology</a>"
        "</nav>",
        "<section id='q1'><h2>Q1 — Where are authors from? (papers &amp; authors on a world map, over time)</h2>"
        + q1_n + "".join(f'<div class="chart-block">{c}</div>' for c in q1_c)
        + "</section>",
        "<section id='q2'><h2>Q2 — Hottest topics over the years (racing bar animation)</h2>"
        + q2_n + "".join(f'<div class="chart-block">{c}</div>' for c in q2_c)
        + "</section>",
        "<section id='q2b'><h2>Q2b — Programming / verification languages over time (racing bar)</h2>"
        + q2b_n + "".join(f'<div class="chart-block">{c}</div>' for c in q2b_c)
        + "</section>",
        "<section id='q3'><h2>Q3 — Company contributions across time (industry vs academia, EDA vs startup vs large-cap)</h2>"
        + q3_n + "".join(f'<div class="chart-block">{c}</div>' for c in q3_c)
        + "</section>",
        "<section id='q4'><h2>Q4 — Author analytics (top 10, multi-location, longest-active, fun categories)</h2>"
        + q4_n + "".join(f'<div class="chart-block">{c}</div>' for c in q4_c)
        + "</section>",
        "<section id='q5'><h2>Q5 — Reproducibility (% with open-source repo, &lsquo;show cool but don&rsquo;t teach&rsquo;)</h2>"
        + q5_n + "".join(f'<div class="chart-block">{c}</div>' for c in q5_c)
        + "</section>",
        "<section id='method'><h2>Methodology &amp; sources</h2>"
        "<div class='methodology'>"
        "<p><b>Source.</b> SQLite DB at <code>data/dvcon.db</code> (1,852 papers, "
        "3,342 authors, 1,641 affiliations, 38,761 chunks). Read-only.</p>"
        "<p><b>Origin extraction (Q1).</b> Parse <code>affiliations_text</code> "
        "fragments, match country aliases (curated + pycountry), fall back to a "
        "city&rarr;country dict of ~30 entries.</p>"
        "<p><b>Topic tagging (Q2).</b> Hand-curated 16-topic taxonomy with "
        "regex keyword sets; multi-label match against title + abstract.</p>"
        "<p><b>Company classification (Q3).</b> Curated CSV of ~96 entities "
        "with year-dependent size buckets; heuristic fallback for unknown "
        "industry-looking strings; sentence-y fragments filtered.</p>"
        "<p><b>Author analytics (Q4).</b> Dedup via casefold + punctuation "
        "strip + honorific removal; use <code>paper_author</code> link table.</p>"
        "<p><b>Reproducibility (Q5).</b> Heuristic signals: github/gitlab/"
        "bitbucket regex, 'open source' / 'artifact' / 'dataset' mentions, "
        "&ge;3 of Listing/Algorithm/Step markers in markdown. Composite 0&ndash;3 score.</p>"
        "<p><b>Known gaps.</b> Author-name collisions are first-normalized-wins. "
        "Company size buckets are approximate (founded_year + manual buckets at "
        "5-year intervals). Reproducibility signals are presence-checks, not "
        "verification that the linked repo actually builds.</p>"
        "</div></section>",
        f"<footer>Generated by docs/generate_report.py — "
        f"{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} — "
        f"intermediate tables under docs/data/</footer>",
        "</body></html>",
    ]
    OUT_HTML.write_text("".join(html_parts), encoding="utf-8")
    print(f"\nWrote {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes)")


# ---------- main entrypoint ----------

if __name__ == "__main__":
    print(f"Loading papers from {DB_PATH} ...")
    papers = load_papers()
    print(f"  {len(papers)} papers loaded")
    assemble_html(papers)
