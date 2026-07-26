# DVCon LLM Wiki

A Karpathy-style synthesized wiki of EDA / functional-verification knowledge,
built from the 1,852-paper DVCon corpus (2010–2026). **100 pages**, each grounded
in 8–15 real DVCon papers with inline citations and a "Grounded in these DVCon
papers" reference list.

The wiki is organized into 13 sections:
- **Foundations** (8 pages) — SystemVerilog, UVM, UPF, SystemC, OVM/VMM, design patterns, verification planning, the DVCon conference
- **UVM deep dives** (10 pages) — testbench architecture, sequences, register layer, factory, phasing, callbacks, config_db, VIPs, scoreboards, reuse
- **UVM mechanics** (5 pages) — TLM ports/exports, reporting/verbosity, component vs object graph, transaction recording, BFMs/virtual interfaces
- **Formal verification** (6 pages) — FPV, connectivity, hybrid, equivalence checking, security, signoff
- **Coverage** (5 pages) — functional, closure, code, regression, data management
- **AI/ML for verification** (4 pages) — ML for coverage, LLM testbench generation, AI for formal, smart regression
- **Methodology and flow** (10 pages) — CRV, signoff, coverage-driven generation, regression management, VIP reuse, shift-left, agile, MDV, triage, tapeout case studies
- **Standards and protocols** (10 pages) — AXI/AMBA, PCIe/CXL, USB, Ethernet, DDR, I2C/SPI/UART, cache coherency, NoC, interrupt controllers, register blocks
- **Power, clock, and analog** (6 pages) — PLL/DLL/CDR, isolation/retention, DVFS, RTL power estimation, real number modeling, Verilog-AMS
- **Functional safety and security** (5 pages) — ISO 26262, DO-254, fault injection/SEU, side-channel, X-propagation/4-state
- **Tools and ecosystem** (8 pages) — cocotb, OSVVM, SystemC TLM-2.0, C reference models via DPI, cloud farms, CI/CD for RTL, constrained-random tuning, random stability
- **Domain-specific** (10 pages) — CDC, RDC, low-power, power-aware, emulation, AMS, SVA, security, RISC-V, SoC integration
- **SoC and system depth** (6 pages) — SW-driven verification, glitch/metastability, pre-to-post-silicon handoff, post-silicon validation, chip-to-board, SerDes/CDR
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

For each of the 100 topics in the manifest at the top of `build_sources.py`,
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
invocation used 10 parallel agents, each writing 5 pages (with sequential
retries for any batches that hit rate limits).

## File layout

```
llm-wiki/
  README.md                       this file
  index.md                        wiki home (TOC + cross-links + methodology note)
  build_sources.py                Phase 1 extractor (run with docs/.venv)
  build_index.py                  Phase 3 index regenerator (run with docs/.venv)
  _topics.json                    canonical 100-topic manifest (committed)
  _sources/                       one JSON source file per topic (gitignored)
    systemverilog.json
    uvm-overview.json
    ...
  systemverilog.md                the 100 wiki pages (committed)
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
