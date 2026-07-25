# DVCon LLM Wiki

A Karpathy-style synthesized wiki of EDA / functional-verification knowledge,
built from the 1,852-paper DVCon corpus (2010–2026). **50 pages**, each grounded
in 8–15 real DVCon papers with inline citations and a "Grounded in these DVCon
papers" reference list.

The wiki is organized into 7 sections:
- **Foundations** (8 pages) — SystemVerilog, UVM, UPF, SystemC, OVM/VMM, design patterns, verification planning, the DVCon conference
- **UVM deep dives** (10 pages) — testbench architecture, sequences, register layer, factory, phasing, callbacks, config_db, VIPs, scoreboards, reuse
- **Formal verification** (6 pages) — FPV, connectivity, hybrid, equivalence checking, security, signoff
- **Coverage** (5 pages) — functional, closure, code, regression, data management
- **AI/ML for verification** (4 pages) — ML for coverage, LLM testbench generation, AI for formal, smart regression
- **Domain-specific** (10 pages) — CDC, RDC, low-power, power-aware, emulation, AMS, SVA, security, RISC-V, SoC integration
- **Modern/emerging** (7 pages) — PSS, chiplets/UCIe, property-driven dev, DPI, IP-XACT, debug, future of verification

## How to read

Open [`index.md`](index.md) for the table of contents with one-line blurbs and
links to every page. Each page opens with a Karpathy-style motivational hook,
drops into neutral reference prose, and ends with cross-links + the grounding
citation list. Renders natively on GitHub, in VS Code, or any markdown viewer.

## How to regenerate

The wiki is built in two phases that decouple corpus querying from writing:

### Phase 1 — extract per-topic sources

```bash
docs/.venv/Scripts/python.exe llm-wiki/build_sources.py
```

For each of the 50 topics in the manifest at the top of `build_sources.py`,
this queries `data/dvcon.db` (read-only) and writes one JSON file per topic to
`llm-wiki/_sources/<slug>.json` containing:
- 8–15 most relevant papers (title, year, authors, abstract excerpt)
- 5–10 most relevant chunks (heading + body excerpt + source paper)
- 8 most-cited references for the topic
- cross-link targets (slugs of related topics)

It also writes `llm-wiki/_topics.json` — the canonical manifest of
slug / title / category / blurb / see_also used by the index and cross-links.

### Phase 2 — write the markdown pages

Each page is written by an LLM agent (originally GLM-5.2) from its source JSON.
The page template is:

```
# <Title>
> *<Karpathy-style hook>*
## <Reference H2 section 1>
## <Reference H2 section 2>
## <Reference H2 section 3>
## See also
## Grounded in these DVCon papers
```

Style rules (enforced in the original prompts):
- **Hook** is first-person, conversational, motivational — analogies, vivid pain points, "let's dig in" energy
- **Body** is neutral, third-person, factual
- Every claim cites a real paper inline as `[Title, Year]`
- The "Grounded in" list contains ONLY real papers from the source JSON
- Cross-links use the format `[Display Title](slug.md)` with display titles looked up from `_topics.json`
- Pure markdown — no images, no Mermaid, no HTML

To regenerate the pages, re-invoke the LLM agent for each topic, pointing it at
`llm-wiki/_sources/<slug>.json` and `llm-wiki/_topics.json`. The original
invocation used 10 parallel agents, each writing 5 pages.

## File layout

```
llm-wiki/
  README.md                       this file
  index.md                        wiki home (TOC + cross-links + methodology note)
  build_sources.py                Phase 1 extractor (run with docs/.venv)
  _topics.json                    canonical 50-topic manifest (committed)
  _sources/                       one JSON source file per topic (gitignored)
    systemverilog.json
    uvm-overview.json
    ...
  systemverilog.md                the 50 wiki pages (committed)
  uvm-overview.md
  uvm-sequences.md
  ...
```

## Editing

Each `.md` page is hand-editable. If you edit a page and want to preserve the
citation integrity, the papers it's grounded in are listed at the bottom under
"Grounded in these DVCon papers" — verify any new claim against that list or
against the corpus via the MCP server (`/skill dvcon-papers`).

If you want to add a new page: add an entry to the `TOPICS` list at the top of
`build_sources.py`, re-run Phase 1 to get the source JSON, then invoke the LLM
to write the page. Update `index.md` with the new entry.
