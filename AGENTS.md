# AGENTS.md

This repository contains a full-stack DVCon paper search and chat application.
This file is the handoff guide for future AI coding agents.

## Purpose

Build and maintain a web app that:

- downloads DVCon papers from `https://dvcon-proceedings.org/`
- stores raw PDFs under `data/paper/`
- extracts markdown, images, and metadata under `data/`
- supports keyword search and semantic search
- supports grounded chat over selected papers
- provides a professional React frontend and a FastAPI backend

## User Preferences

- Use `uv` for Python dependency management and Python commands.
- Use snake_case and 4-space indentation.
- Do not commit secrets or the full generated runtime corpus. A curated example corpus is acceptable only when explicitly requested by the user.
- Default interpretation of a change request: do the implementation work, update the code, update `AGENTS.md`, and update `PROGRESS.md` unless the user explicitly narrows the scope.

## Current Architecture

- Backend: `FastAPI`, `SQLModel`, `SQLite FTS5`, `ChromaDB`
- Frontend: `React`, `TypeScript`, `Vite`, `MUI`
- PDF extraction: `PyMuPDF`, `pymupdf4llm`
- Metadata enrichment: local `GROBID` sidecar producing TEI XML, enabled by default
- Scraping: `httpx`, `BeautifulSoup4`
- Chat: OpenAI Responses API via configurable `OPENAI_BASE_URL` and `OPENAI_API_KEY`
- Embeddings: local `sentence-transformers` model via `torch`
- Local embedding device: CUDA preferred, CPU fallback
- Agent access: MCP server (standalone FastMCP 4 over stdio, built on MCP SDK v2) reusing the service layer; Claude plugin marketplace + agent skill mirror the same tool surface

## Key Product Requirements

- Only index DVCon items whose detail page says `Type: Paper` and `Format: pdf`.
- Save PDFs at `data/paper/{year}/{location}/{slug}.pdf`.
- Save markdown at `data/markdown/{year}/{location}/{slug}.md`.
- Save extracted images at `data/markdown/{year}/{location}/images/{slug}/`.
- Save raw GROBID TEI at `data/tei/{year}/{location}/{slug}.tei.xml` when available.
- Extract and persist metadata such as:
  - title
  - authors
  - affiliations / company names
  - abstract
  - references
  - year
  - conference location
- Left panel tabs:
  - Search Results
  - PDF
  - Markdown
  - Metadata Graph
- Right panel:
  - chat transcript
  - input box
  - Enter submits
  - Shift+Enter inserts newline
- Metadata Graph nodes are clickable (per node type):
  - **author** / **company** → jump to Search Results filtered by that name (keyword FTS match against `authors` / `affiliations`)
  - **conference** → jump to Search Results filtered by that conference's year + location (precise, not free-text)
  - **reference** → if the citation's normalized title resolves to an in-corpus paper, jump to that paper's PDF tab; unresolved references render non-clickable
  - **paper** (the active paper) → no-op (already viewing it)
  - The graph tab stays mounted across author/company/conference clicks (graph_query is keyed on `active_paper_id`, which doesn't change), so the user returns to the graph by re-clicking the Metadata Graph tab.

## Repository Layout

- `backend/src/backend/main.py`: FastAPI app entrypoint
- `backend/src/backend/mcp_server.py`: MCP server over stdio (reuses the service layer)
- `backend/src/backend/core/config.py`: runtime settings from `.env`
- `backend/src/backend/db/models.py`: SQLModel schema
- `backend/src/backend/db/session.py`: SQLite engine and FTS setup
- `backend/src/backend/api/`: route layer and response schemas
- `backend/src/backend/services/scraper.py`: DVCon search-form crawl + PDF download
- `backend/src/backend/services/extractor.py`: PDF to markdown/image/metadata extraction
- `backend/src/backend/services/grobid.py`: GROBID REST client
- `backend/src/backend/services/tei_parser.py`: TEI-to-structured-metadata parser
- `backend/src/backend/services/embeddings.py`: local sentence-transformer embedding provider
- `backend/src/backend/services/indexer.py`: chunking, Chroma indexing, FTS sync, search
- `backend/src/backend/services/chat.py`: paper-grounded chat orchestration
- `backend/src/backend/services/graph.py`: metadata graph assembly
- `backend/src/backend/tasks/ingest.py`: CLI ingestion entrypoint
- `backend/tests/test_smoke.py`: smoke tests
- `backend/tests/test_tei_parser.py`: TEI parser coverage
- `backend/tests/test_extractor_grobid.py`: hybrid and fallback extractor coverage
- `frontend/src/App.tsx`: main UI shell
- `frontend/src/components/`: tab and panel components
- `frontend/src/api/client.ts`: frontend API client
- `CONTRIBUTION.md`: contributor workflow and open source etiquette guide
- `scripts/`: local startup scripts for bash and PowerShell, including `start_mcp.*`
- `compose.yaml`: repo-managed app + GROBID runtime stack
- `data/paper/`: raw downloaded papers
- `data/`: runtime corpus data root containing downloaded PDFs, extracted markdown, TEI cache, DB, Chroma, and model cache
- `data.example/`: checked-in Horace Chan sample corpus mirroring the curated `data/` content layout without local DB/vector artifacts
- `docs/`: standalone analysis workspace that data-mines the corpus and emits the GitHub Pages site (`generate_report.py` + curated `data/topics.csv`, `data/companies.csv`, served as `index.html`); see `docs/README.md`
- `llm-wiki/`: 100-page Karpathy-style knowledge wiki synthesized from the corpus (`build_sources.py` extracts per-topic source JSONs from the DB; an LLM agent writes each markdown page from its source; `build_index.py` generates the TOC); see `llm-wiki/README.md`
- `.agents/skills/dvcon-papers/SKILL.md`: workspace agent skill describing the MCP tools
- `plugins/dvcon-papers/skills/dvcon-submit/SKILL.md`: plugin skill that submits DVCon U.S. papers (extended abstract AND full paper) to Oxford Abstracts via `playwright-cli`, and converts a markdown paper to a template-styled `.docx`/`.pdf` via MS Word COM on Windows (`convert_md_to_docx.ps1`) or `fill_ieee_docx.py` + LibreOffice on macOS/Linux (`convert_md_to_docx.sh` delegates to the `.ps1` on Windows). The IEEE `.doc` template and both helpers live under `plugins/dvcon-papers/skills/dvcon-submit/`
- `.claude-plugin/marketplace.json`: Anthropic Claude plugin marketplace catalog
- `plugins/dvcon-papers/`: Claude plugin bundling the skill, `/dvcon` command, and `dvcon` MCP server
- `submissions/{conference}/`: papers this repo submits to DVCon. `abstract.md` is the hand-edited source; `abstract.pdf` is the exact artifact uploaded to Oxford Abstracts. The intermediate `abstract.docx` is gitignored (regenerate with the `dvcon-submit` converter). The DVCon U.S. 2027 abstract presents the library as an open-source project deliberately designed for both humans and AI agents across the broader conference lifecycle—reading, analyzing, synthesizing, and preparing contributions—not only RAG chat. Its current reference [6] uses the public `hevangel/dvcon_ai_library` URL at the author's explicit direction; that URL de-anonymizes the abstract and conflicts with the extended-abstract double-blind rule.

## Backend API Surface

- `GET /api/health`
- `GET /api/stats`
- `GET /api/search`
- `GET /api/papers/{paper_id}`
- `GET /api/papers/{paper_id}/pdf`
- `GET /api/papers/{paper_id}/markdown`
- `GET /api/papers/{paper_id}/graph`
- `POST /api/chat`
- `POST /api/admin/ingest`

The same capabilities are also exposed as MCP tools (see "MCP Server" below): `search_papers`, `get_paper_detail`, `get_paper_markdown`, `get_paper_graph`, `corpus_stats`, and `chat_with_papers`. Both surfaces are thin wrappers over the same `backend.services.*` functions, so behavior stays consistent.

## Search Design

- Keyword search uses SQLite `FTS5`.
- Semantic search uses ChromaDB with local embeddings.
- Hybrid search merges keyword and semantic results.
- Chat retrieval is constrained to selected paper IDs when available.
- Flattened search fields are preserved even when structured GROBID metadata is present.

## Scraping Design

- Corpus discovery walks the homepage Year x Location filter matrix and posts each combination through the human-facing document search form.
- The DVCon site renders its results table client-side via the **Document Library Pro** WordPress plugin (DataTables `serverSide: true`). The HTML table returned by the search form is just a header skeleton; the rows are fetched separately via an AJAX call to `admin-ajax.php` keyed by a page-bound `table_id` (a WordPress transient). Filters are bound into the `table_id` server-side by the search-form POST, so the AJAX call itself must NOT resend them.
- `_search_form_document_urls` therefore: (1) POSTs the search form to obtain a fresh `dlp_<hex>_<n>` `table_id`, (2) POSTs `action=dlp_load_posts` with that `table_id`, paging `start` by `AJAX_PAGE_SIZE` until `start >= recordsTotal`, and (3) parses `/document/` links from each returned row's `title` HTML.
- If the page shape ever changes and no `table_id` is present in the search response, the scraper falls back to the legacy server-rendered `<table class="posts-data-table">` parse so a partial site change doesn't wipe already-discovered URLs from the manifest.
- The CLI exposes a `--years` flag (e.g. `ingest --years 2025,2026`) to scope the crawl to specific year filters; this skips the pointless re-walk of older years you already have, which is the slow part of an unbounded crawl.
- Ingest is idempotent and resumable: papers already in the DB whose PDF + markdown artifacts still exist are skipped unless `--force` is passed.

## Extraction Design

- The markdown and image path remains `PyMuPDF` / `pymupdf4llm`.
- GROBID is an enrichment layer, not a replacement renderer.
- If GROBID is enabled and reachable, the extractor prefers GROBID title, abstract, structured authors, affiliations, and references.
- Local startup scripts should assume GROBID is part of the normal runtime, not an extra optional step.
- If GROBID is unavailable or errors, the extractor falls back to the existing heuristic metadata extraction without failing the ingest.
- Duplicate structured author entries from GROBID are deduplicated by normalized author name before `PaperAuthor` rows are written.
- Structured affiliations are persisted alongside the existing flattened `affiliations_text` field.
- Structured references are persisted alongside the existing flattened `references_text` field.
- Affiliations carry structured location fields (`city`, `state_province`, `country`) and an optional `company_id` foreign key into a `Company` table. When GROBID exposes `<orgName>`, `<settlement>`, `<region>`, `<country>` in the TEI, those populate the structured fields; otherwise the heuristic path records the flattened string as `name` and a coarse company guess.
- The metadata graph renders `Company` nodes via the `Affiliation.company` relationship and enriches company/affiliation node labels with city + country when present, falling back to the flattened affiliation name.
- Affiliation node ids in the graph are slug-based (`company-<slug>`) so they stay deterministic across processes; Python's randomized `hash()` is not used for node identity.

## MCP Server

- The MCP server lives at `backend/src/backend/mcp_server.py` and is launched by the `dvcon-mcp` console script (`uv run --project backend dvcon-mcp`).
- It uses standalone FastMCP (`from fastmcp import FastMCP`, package `fastmcp>=4`) and runs over stdio transport (`mcp.run()`). FastMCP 4 depends on MCP Python SDK v2; do not import `mcp.server.fastmcp` (that path existed only in SDK v1).
- It is a thin wrapper over `backend.services.*` — no business logic is duplicated between the HTTP API and MCP.
- Exposed tools: `search_papers`, `get_paper_detail`, `get_paper_markdown`, `get_paper_graph`, `corpus_stats`, `chat_with_papers`.
- Read tools work without GROBID or OpenAI configured; only `chat_with_papers` needs `OPENAI_BASE_URL` / `OPENAI_API_KEY`.
- The server calls `create_db_and_tables()` on startup so it can run standalone without the HTTP backend having started first.
- Tool payloads are plain JSON-serializable dicts (no SQLModel objects leak across the wire).

## Agent Skills

Two workspace skills live under `.agents/skills/` (cross-tool default location per the skill-creator convention).

### dvcon-papers (corpus reader)

- Skill: `.agents/skills/dvcon-papers/SKILL.md`.
- Frontmatter is intentionally minimal: only `name` and `description` (ZCode skill spec — no `model` or `allowed-tools` keys).
- The description is trigger-forward so the model picks it up when users ask about DVCon papers, EDA/verification methodology, or paper search/summarization even without saying "DVCon" or "MCP".
- A mirrored copy ships inside the Claude plugin at `plugins/dvcon-papers/skills/dvcon-papers/SKILL.md` so the plugin is self-contained.
- Use `/skill dvcon-papers` in a ZCode-style client to force-load it; otherwise it auto-triggers based on the description.

### dvcon-submit (paper conversion + submission)

- Skill: `plugins/dvcon-papers/skills/dvcon-submit/SKILL.md` with references at `references/submission_reference.md` (form field truth) and `references/conversion_reference.md` (markdown→PDF truth), interchangeable helpers at `scripts/convert_md_to_docx.ps1` (PowerShell) and `scripts/convert_md_to_docx.sh` (bash twin; delegates to the `.ps1` on Windows, else `fill_ieee_docx.py` + LibreOffice), and the bundled DVCon IEEE template at `references/dvcon_abstract_template.doc` (+ a `.pdf` rendering for visual reference).
- Two capabilities: (1) **convert** a markdown paper to a template-styled `.docx`/`.pdf` by filling the template's named IEEE styles via MS Word COM (this machine has Word 16.0; no LibreOffice/pandoc needed); (2) **submit** to Oxford Abstracts by driving a real browser with the `playwright-cli` command-line tool (verified v0.1.14 on PATH).
- Covers **both** DVCon submission stages: the initial **Extended Abstracts** stage (double-blind, 600–1200 words) and the later **Full Paper** stage (6–8 pages, author info included, plus a signed copyright form upload).
- Uses `playwright-cli` (NOT the ZCode in-app browser) precisely because `playwright-cli upload` can attach the PDF — the IAB runtime cannot do file uploads. The browser is launched `--headed --persistent` so the user can see it and log in; the skill never enters credentials.
- The markdown converter maps markdown constructs to the template's IEEE named styles (`# H1`→IEEE Title, `>`blockquote→IEEE Abstract, `## H2`→IEEE Heading 1, `### H3`→IEEE Heading 2, lists→IEEE List, `[n]` lines→IEEE Reference, body→IEEE Text, fenced code→IEEE Text monospace). It **drops `## Authors`/`## Affiliations`/`## Author Information` sections** so the abstract stays double-blind; for the full-paper stage the user renames the section or post-edits the `.docx`.
- Inline markers are converted to real Word character formatting rather than typed verbatim: `**bold**`/`__bold__`, `*italic*`/`_italic_`, `` `code` ``→Consolas, `[label](url)`, plus backslash escapes. Fenced code blocks stay verbatim.
- The submission is **double-blind for the abstract stage**: the PDF must not contain author names or affiliations (they go in the form's Authors section, hidden from reviewers). The skill warns if the body prose self-identifies.
- The Oxford Abstracts stage id changes every year (DVCon U.S. 2027 = stage `81951`); the skill never hardcodes it — it re-discovers the live "Submit Now" URL from `https://dvcon.org/submission-instructions/call-for-extended-abstracts`.
- The reference files are the source of truth for exact field labels, the 14 topic dropdown labels (short forms like `Formal/Assertions`, not the long homepage names), and the two country-dropdown label variants (`USA`/`UAE` on the affiliation dropdown vs `United States`/`United Arab Emirates` on the presenter dropdown).
- The final Submit click is never automated without explicit user confirmation (hard-to-reverse outward action). All other fields, the upload, and the click are driven by `playwright-cli`.
- Does NOT cover tutorial/workshop or panel submissions — those are separate Oxford Abstracts stages with different forms.

## Anthropic Marketplace Plugin

- The marketplace catalog is `.claude-plugin/marketplace.json` (camelCase schema; one plugin entry, `dvcon-papers`, with `source: "./plugins/dvcon-papers"`).
- The plugin manifest is `plugins/dvcon-papers/.claude-plugin/plugin.json`, declaring the skill, the `/dvcon` command (`commands/dvcon.md`), and the `dvcon` MCP server inline.
- The MCP server `command` is `uv run --project backend dvcon-mcp` with `cwd: ${CLAUDE_PLUGIN_ROOT}/../..` so it runs from the repo root regardless of where the plugin is installed.
- Install from a Claude Code session with `/plugin marketplace add hevangel/dvcon_ai_library` then `/plugin install dvcon-papers@dvcon-marketplace`.
- Plugin `name` is immutable after publish; change `displayName` for UI label changes and use the top-level `renames` map for migrations.

## Local Embedding Design

- Embeddings do not use the OpenAI API.
- Local model is configured in `.env` via:
  - `LOCAL_EMBEDDING_MODEL`
  - `LOCAL_EMBEDDING_DEVICE`
- Current default model: `BAAI/bge-m3`
- Expected vector dimension after reindex: `1024`
- `backend/src/backend/services/indexer.py` resets the Chroma collection if the embedding model changes, to avoid dimension mismatch with old vectors.
- CUDA is available on this machine and should be preferred.
- The CUDA torch wheel comes from the `pytorch-cu128` uv index with `explicit = true`, so only `torch` is resolved from that index. Leave it explicit: FastMCP 4 needs `idna>=3.18`, and the PyTorch wheel index still publishes `idna==3.4`, which would otherwise pin the resolver and fail the lock.

## Environment Files

- `.env` is local-only and gitignored.
- `.env.example` is the template.
- Chat-related keys:
  - `OPENAI_BASE_URL`
  - `OPENAI_API_KEY`
  - `OPENAI_CHAT_MODEL`
 - `OPENAI_CHAT_MODEL_CONTEXT_WINDOW`
 - `CHAT_CONTEXT_OUTPUT_RESERVE_TOKENS`
- Current default chat model: `gpt-5-mini`
- Docker-compose host port key:
  - `APP_HOST_PORT`
- Runtime data root key:
  - `DATA_DIR`
- GROBID-related keys:
  - `GROBID_ENABLED`
  - `GROBID_URL`
  - `GROBID_TIMEOUT_SECONDS`
- Embedding-related keys:
  - `LOCAL_EMBEDDING_MODEL`
  - `LOCAL_EMBEDDING_DEVICE`
- Production-hardening keys:
  - `INGEST_ADMIN_TOKEN` (optional guard for `POST /api/admin/ingest`)
  - `ALLOW_CHROMA_WIPE` (opt-in to silent collection reset on model change)

## Current Local Runtime Settings

- Backend currently configured to run on port `8010` via `.env`.
- Frontend local API target is `frontend/.env.local`:
  - `VITE_API_BASE_URL=http://127.0.0.1:8010/api`
- Port `8000` was already occupied by another unrelated local FastAPI service, so this app was moved to `8010`.

## Current Progress

Implemented:

- backend scaffold and API
- frontend shell and tabbed layout
- resizable left/right frontend split layout
- frontend chat command prompts and help display
- DVCon crawler and resumable download manifest
- PDF extraction to markdown and colocated image export
- hybrid metadata persistence with optional GROBID enrichment
- structured affiliations (`Company` table + `Affiliation` location fields) parsed from TEI and persisted with backfill migrations
- SQLite FTS keyword search
- Chroma semantic indexing
- local CUDA-backed embeddings
- grounded chat integration
- chat continuation token reuse via `previous_response_id`
- MCP server over stdio reusing the service layer (`dvcon-mcp`)
- workspace agent skill (`.agents/skills/dvcon-papers`) describing the MCP tools
- workspace agent skill (`.agents/skills/dvcon-submit`) that converts a markdown paper to a DVCon IEEE-template-styled `.docx`/`.pdf` via MS Word COM (`scripts/convert_md_to_docx.ps1` + the bash twin `convert_md_to_docx.sh`), and submits DVCon U.S. papers (extended abstract + full paper stages) to Oxford Abstracts via `playwright-cli` (real browser, supports PDF upload; bundled template + references for field labels, 14 topics, country-dropdown variants)
- Anthropic Claude plugin marketplace + self-contained `dvcon-papers` plugin (skill + `/dvcon` command + MCP server)
- Dockerfile
- repo-managed `compose.yaml` full app + GROBID stack
- contributor guide in `CONTRIBUTION.md`
- local run scripts (including `start_mcp.*`)
- smoke tests

Verified:

- backend imports successfully
- frontend production build succeeds
- smoke tests pass
- live ingest of at least one DVCon paper succeeded
- local embeddings run on CUDA
- semantic search returns results after reindex
- local manifest-based reindex completed for 37 downloaded papers with `BAAI/bge-m3`
- local corpus was later reset and rebuilt as a fresh 10-paper 2025 test set
- all 8 DVCon paper records authored by Horace Chan were then downloaded and added to the local corpus, bringing the current local total to 18 indexed papers
- a checked-in example corpus was created under `data.example/` containing the 8 Horace Chan PDFs plus extracted markdown, TEI, and image assets
- live `/summarize` chat requests now succeed against the configured `gpt-5-mini` OpenAI-compatible endpoint after removing the unsupported hard-coded `temperature` parameter
- selected-paper chat requests now preserve the chosen paper scope for generic prompts like "compare the two papers" instead of falling back to unrelated corpus-wide search results
- selected-paper chat now estimates prompt tokens against the configured chat model context window and sends full selected paper text when it fits; otherwise it falls back to curated sections
- chat requests now propagate `previous_response_id` end to end so follow-up turns can reuse the prior Responses API conversation state instead of always resending the full transcript
- the chat panel now shows an in-transcript loading indicator after submit, auto-scrolls to the newest assistant output, and uses compact numbered citation chips with matching `[n]` labels on the selected-paper scope row
- scraper URL discovery now uses the live document search UI by reading the homepage Year and Location filters and posting those combinations through the human-facing search form, instead of relying on the incomplete WordPress document sitemap path

## Important Gotchas

- The `dvcon-submit` skill drives Oxford Abstracts with the **`playwright-cli`** command-line tool (a real browser), NOT the ZCode in-app browser. This is deliberate: `playwright-cli upload` can attach the paper PDF, whereas the IAB runtime cannot do file uploads (`waitForEvent("filechooser")` / `setFiles` return `capability_unsupported`). Launch with `playwright-cli open --headed --persistent` so the user can see and log into the visible window; the skill never enters credentials.
- The `dvcon-submit` skill's final Submit click is never automated without explicit user confirmation (submission is a hard-to-reverse outward action). Everything else — field fills, the PDF upload, dropdowns, checkboxes — is driven by `playwright-cli`.
- The `dvcon-submit` skill must never hardcode the Oxford Abstracts stage id (it changes yearly: DVCon U.S. 2027 = `81951`). It re-discovers the live submitter URL from the dvcon.org "Submit Now" link each run.
- On the Oxford Abstracts form the **Choose File** control is a hidden `input[type=file].sr-only` with a `<label class="... fu-hover">` painted over it. `playwright-cli click` on the snapshot ref resolves to the input, the label intercepts pointer events, the click times out, and the follow-up `upload` fails with `can only be used when there is related modal state present`. Click `label.fu-hover` instead — a good click reports `### Modal state - [File chooser]`. Verified live on stage `81951`.
- The Oxford Abstracts **Title** counter (`0/50`) counts **words, not characters**, despite reading like a character budget. A 47-character, 9-word title shows `9/50`. Do not truncate titles to 50 characters.
- The dvcon.org "Submit Now" control opens the portal in a **new tab**; `playwright-cli click` reports the original page unchanged. Use `tab-list` / `tab-select 1` to reach the Oxford Abstracts tab.
- The `dvcon-submit` markdown converter ships as twins: `scripts/convert_md_to_docx.ps1` (PowerShell) and `scripts/convert_md_to_docx.sh` (bash). The PowerShell version requires **MS Word** (drives Word via COM; verified Word 16.0 on this host) and no LibreOffice/pandoc is installed locally. The bash version on Windows auto-detects `pwsh`/`powershell.exe`, converts paths via `cygpath -w`, and delegates to the `.ps1` (so output is identical); on macOS/Linux it converts the bundled `.doc` to `.docx` with LibreOffice and runs `scripts/fill_ieee_docx.py` (Python 3 stdlib) to stamp the same IEEE styles, author drop, and inline runs as the `.ps1`. pandoc is not used on either path. Both export PDF with embedded fonts via `ExportAsFixedFormat` (Windows) or `soffice --convert-to pdf` (non-Windows).
- The `.ps1` converter splits each paragraph into character runs (`Split-InlineMarkdown` / `Get-InlineRuns`) so `**bold**`, `*italic*`, `` `code` ``, and `[label](url)` become Word formatting instead of literal markers in the PDF. Between runs it calls `Font.Reset()` and only ever turns bold/italic **on** — never `Bold = 0`. Do not "simplify" that to an explicit off-toggle: `IEEE Abstract` is itself a bold style and forcing bold off would strip it. The `_italic_` form requires non-word characters on both sides so DOIs and identifiers like `dvcon_ai_library` survive. `scripts/fill_ieee_docx.py` is the same parser for the bash non-Windows path: it writes `w:b` / `w:i` / Consolas `w:rFonts` only when a run requests them (never `w:b w:val="0"`), maps style names to OOXML styleIds (`IEEE Title` → `IEEETitle`), and rewrites `word/document.xml` inside a style-bearing `.docx`. Keep the two parsers in lockstep.
- Regenerated `.docx` files under `submissions/` never appear in `git status` — `.gitignore` carries `submissions/**/*.docx`. A "the docx didn't update" report is almost always either that or a stale copy held open in Word; check the file's `LastWriteTime` before debugging the converter.
- DVCon extended-abstract submissions are **double-blind**: author names and affiliations must not appear inside the abstract PDF (they go in the form's Authors section, which is hidden from reviewers). The converter drops `## Authors`/`## Affiliations`/`## Author Information` sections, but the skill also warns if the body prose self-identifies. The **full-paper** stage is NOT blind — author info belongs in the PDF.
- `data/` is intentionally gitignored and may be empty in git status even after ingestion.
- `frontend/.env.local` is gitignored and contains the local backend URL override.
- New extractions place images under the markdown tree at `data/markdown/{year}/{location}/images/{slug}/`.
- New GROBID TEI files are stored under `data/tei/{year}/{location}/`.
- The backend serves built frontend assets from `frontend/dist` in production mode.
- During development, Vite serves the frontend separately.
- The frontend now uses a draggable desktop split between the left paper workspace and the right chat panel.
- The title bar subtitle emphasizes corpus counts inline instead of using title-bar chips.
- The search tab keeps its controls fixed while the result list itself scrolls.
- The chat panel still supports typed `/help`, `/clear`, and `/summarize` commands, but the top-of-panel quick-prompt chips were removed from the right panel UI; `/clear` should always return the panel to the help display.
- The PDF tab uses compact page navigation controls and now exposes PDF download via a small outlined icon-only button that shares the same styling and fixed button dimensions as the `<` and `>` pager controls beside the next-page `>` control instead of a separate `Open PDF` text button.
- The PDF tab now auto-resizes the rendered PDF page to fit the current left-panel width, including while the desktop split handle is dragged.
- The PDF tab title can wrap independently, but the pager label plus `<`, `>`, and download controls should stay together on a single line.
- The left panel should not show a horizontal scrollbar; PDF content is expected to wrap or clip horizontally and only scroll vertically inside its viewport.
- Extracted markdown now stores image references as markdown-relative `images/...` paths so VS Code preview works against the local filesystem.
- The Markdown tab resolves those relative image links through the configured backend asset origin so inline diagrams load correctly during frontend dev on `5173` as well as when served by the backend in production.
- The current local corpus is not year-pure anymore: it contains the 10-paper 2025 test set plus 8 Horace Chan papers from 2012-2022.
- The checked-in `data.example/` tree is a curated sample corpus and should not be confused with the gitignored runtime `data/` directory.
- The `docs/` directory has its own isolated `.venv` (gitignored) and does not share dependencies with `backend/.venv`; do not run `docs/generate_report.py` with the backend's Python.
- The `llm-wiki/` directory contains a 100-page Karpathy-style knowledge wiki synthesized from the corpus. `build_sources.py` and `build_index.py` run with `docs/.venv` (they only need stdlib + nothing else). The per-topic source JSONs under `llm-wiki/_sources/` are gitignored (regeneratable from the DB); the 100 markdown pages, `index.md`, `_topics.json`, `README.md`, and the two Python scripts are committed. To regenerate the pages themselves, an LLM agent must be invoked per topic (the original run used 10 parallel GLM-5.2 agents per batch of 50 pages, with sequential retries for any batches that hit rate limits).
- The report's curated CSVs (`docs/data/topics.csv`, `docs/data/companies.csv`) and `docs/data/company_overrides_notes.md` are deliberately checked in so the classifications are transparent and editable. The derived per-paper tables are gitignored (re-generatable from the CSVs + DB).
- `docs/index.html` is committed and served by GitHub Pages (source: `main` / `/docs`). After editing the curated CSVs, re-run `docs/generate_report.py` and commit the regenerated `index.html`.
- The report reads `data/dvcon.db` directly via `sqlite3` and never writes; it can run while the backend is up. The link table is `paperauthor` (no underscore) per SQLModel's table-naming convention.
- When chat requests include `selected_paper_ids`, the backend should keep that scope authoritative; if retrieval is weak for a generic query, it should still build context from the selected papers rather than broadening to the full corpus.
- The frontend only reuses `previous_response_id` when the selected-paper scope is unchanged; `/clear` and failed chat requests reset the stored continuation id so follow-up turns fall back to a full prompt safely.
- `scripts/start_backend.*` and `scripts/start_all.*` are expected to bring up GROBID automatically.
- `scripts/start_grobid.*` should wait for `http://127.0.0.1:8070/api/isalive` to return `true`.
- `docker compose up --build` is the default container path and should start both `app` and `grobid`.
- On machines without the Docker Compose plugin, the startup scripts should fall back to `docker-compose`.
- The compose app should publish to host port `8011` by default via `APP_HOST_PORT`, while the backend still listens on its internal `PORT`.
- The compose app mounts `${DATA_DIR}` on both the host and container sides, defaulting to `data`.
- The repo default embedding model is `BAAI/bge-m3`, and the local `.env` is now aligned with that default.
- If semantic search suddenly fails after changing embedding model or dimension, force a reindex. The collection reset logic should handle most cases.
- `pymupdf4llm` emits a layout suggestion warning; this is informational, not a failure.
- GROBID is expected at `http://127.0.0.1:8070` by default when running locally on the host.
- The repo-managed sidecar defaults to `grobid/grobid:0.8.2-crf` because it is the safest cross-platform choice, especially on Windows hosts.
- Hugging Face may warn about symlink caching on Windows. This is expected unless Windows Developer Mode is enabled.
- Some OpenAI-compatible providers used with `gpt-5-mini` reject the `temperature` parameter on the Responses API; keep the chat request payload free of hard-coded temperature overrides unless the target model explicitly supports them.
- Full selected-paper chat uses an approximate token estimate plus a configurable context-window override; if a provider exposes a smaller or larger limit than the repo default, set `OPENAI_CHAT_MODEL_CONTEXT_WINDOW` explicitly.
- Do not trust the WordPress document sitemap as the primary corpus discovery source. The live site UI exposes newer papers through the homepage filters and document search results even when the document sitemap path is incomplete or truncated.
- The DVCon results table is **not** populated server-side; it loads via the Document Library Pro `admin-ajax.php` endpoint keyed by a per-search-form-POST `table_id`. If `_search_form_document_urls` returns 0 URLs for a year you know has papers, the site's table plugin changed shape — re-extract the `table_id` regex and AJAX `action` name, and verify the legacy fallback path still parses.
- A full unbounded `ingest` re-walks all 17 years x 6 locations = 102 filter combos (each with a search POST + AJAX pagination). For incremental "fetch new papers" runs, always prefer `ingest --years <recent>` to scope the crawl.
- `keyword_search` keeps the caller's `paper_ids` scope filter authoritative; the local FTS-matched id list must use a different name (`matched_paper_ids`) so it never shadows the scope parameter. Do not reintroduce the old `paper_ids = [row[0] for row in rows]` reassignment.
- `get_stats` uses `SELECT COUNT(*)` / distinct-column queries rather than loading full `Paper` / `Conference` rows; keep it lightweight as the corpus grows.
- Structured affiliation fields (`Affiliation.city`, `.state_province`, `.country`, `.company_id`) are added via `_ensure_column` migrations in `session.py`; the `Company` table is created by `SQLModel.metadata.create_all`. Legacy `Affiliation` rows backfill their `company_id` and location fields on the next ingest of a paper that touches them.
- `datetime.utcnow()` is deprecated in Python 3.12+; the codebase uses `datetime.now(timezone.utc)` (and a `_utcnow` factory in `models.py` for column defaults).
- The MCP server is a separate process from the HTTP backend but shares the same `data/` corpus and `.env`. It is read-mostly; ingestion still goes through the HTTP `/api/admin/ingest` endpoint or the `ingest` CLI, not through MCP.
- The Claude plugin's MCP `command` relies on `cwd: ${CLAUDE_PLUGIN_ROOT}/../..` resolving to the repo root; if the plugin directory moves, update that path so `uv run --project backend` still finds the backend.

## Production Hardening

The backend is hardened for real single-node deployment. Key behaviors a future agent must not regress:

- **SQLite runs in WAL mode** (`PRAGMA journal_mode=WAL`, set in `_configure_sqlite_connection`), with `synchronous=NORMAL`, `foreign_keys=ON`, and `busy_timeout=60000`. WAL is a persistent database-level property — once any connection sets it, the `-wal`/`-shm` sidecar files appear and all connections (including raw `sqlite3` ones) benefit. This is what lets `/search`, `/papers`, `/stats`, and `/chat` keep responding while an ingest write transaction is open. Do not remove these PRAGMAs.
- **Per-paper error isolation in `run_ingestion`**: a single corrupt PDF, GROBID hiccup, embedding OOM, or Chroma error logs the failure and continues to the next seed (recording `status="index_error"` in the manifest) rather than aborting the whole batch. Only persistent `OperationalError` (DB wedged) re-raises. `OperationalError` retries use a separate helper `_index_seed_with_lock_retries`.
- **`POST /api/admin/ingest` is serialized** via a module-level `threading.Lock` and returns HTTP **409** if an ingest is already running (concurrent ingests corrupt Chroma and race the manifest). When `INGEST_ADMIN_TOKEN` is set, the endpoint also requires a matching `X-Admin-Token` header (401 otherwise); unset = open for local dev.
- **Chroma/SQL consistency**: `index_seed` commits SQL as the source of truth; if the commit fails after Chroma was mutated, `_rollback_chroma_ids` deletes the just-added vectors (best-effort compensation). The Chroma client and collection are cached singletons (`_cached_chroma_client` / `_cached_chroma_collection`).
- **No silent Chroma wipe**: if the on-disk collection was built with a different embedding model than the current setting, `_get_chroma_collection` raises (with guidance to run `ingest --force`) instead of destroying the index. Set `ALLOW_CHROMA_WIPE=1` to restore the legacy auto-reset behavior.
- **PDF download validation**: `download_pdf` checks `%PDF-` magic bytes, honors `Content-Length`, and opens the saved file with `fitz.open` to assert `page_count > 0`. HTML error pages / Cloudflare interstitials / truncated downloads are rejected and deleted so they can't crash extraction; `crawl_archive` records them in the manifest.
- **Chat resilience**: the `OpenAI` client is a cached singleton with explicit `timeout` and `max_retries`; `RateLimitError` / `APITimeoutError` / `APIConnectionError` / `AuthenticationError` are mapped to `RuntimeError`, which the route turns into HTTP 503 (instead of a 500 stack trace).
- **Atomic manifest writes**: `ManifestStore.save` writes to a `.tmp` sibling and `os.replace`s into place; `crawl_archive` saves every 25 successful downloads (plus on every error and once at the end) to avoid O(n²) full-manifest rewrites.
- **Retry backoff**: `_request_with_retries` uses exponential backoff with jitter and honors the `Retry-After` header on 429 responses.

## Runbook

### Backend

```bash
./scripts/start_backend.sh
```

### Frontend

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

### Small ingest test

```bash
uv run --project backend ingest --limit 1
```

### Scoped incremental ingest (recommended for "fetch new papers")

The crawl walks the homepage's Year x Location filter matrix. Scoping to
recent years skips a pointless re-walk of years you already have, which is
the slow part of an unbounded crawl.

```bash
# Crawl only 2025 and 2026 across all locations; index what's missing.
uv run --project backend ingest --years 2025,2026
```

The ingest is idempotent: papers already in the DB whose PDF + markdown
artifacts still exist are skipped, so this is safe to re-run. Pass `--force`
to re-extract and re-index existing papers in scope.

### Start only the GROBID sidecar

```bash
docker compose up -d grobid
```

### Start the container stack

```bash
docker compose up --build
```

### Start the MCP server (stdio)

```bash
./scripts/start_mcp.sh        # or: uv run --project backend dvcon-mcp
```

### Regenerate the corpus analysis report (GitHub Pages site)

```bash
# one-time venv setup
py -3 -m venv docs/.venv
docs/.venv/Scripts/python.exe -m pip install -r docs/requirements.txt

# regenerate (after editing docs/data/*.csv or after a new ingest)
docs/.venv/Scripts/python.exe docs/generate_report.py

# open locally, or push to main to deploy to GitHub Pages
docs/index.html
```

The report reads `data/dvcon.db` read-only and does NOT touch the running
backend or its venv. The curated CSVs (`docs/data/topics.csv`,
`docs/data/companies.csv`, `docs/data/company_overrides_notes.md`) are checked
in; the large derived per-paper tables are gitignored (re-generatable).
`docs/index.html` IS committed because GitHub Pages serves it directly from
the `main` branch's `/docs` folder.

### Regenerate the llm-wiki sources and index

```bash
# Phase 1: re-extract per-topic source JSONs from the DB (run after a new ingest)
docs/.venv/Scripts/python.exe llm-wiki/build_sources.py

# Phase 2: regenerate index.md from _topics.json + the written pages
docs/.venv/Scripts/python.exe llm-wiki/build_index.py
```

The wiki pages themselves (`llm-wiki/*.md`) are written by an LLM agent from
the source JSONs and are NOT auto-regenerated by these scripts. The original
run used 10 parallel GLM-5.2 agents. To rewrite a single page, invoke an
LLM with `llm-wiki/_sources/<slug>.json` + `llm-wiki/_topics.json` and the
template documented in `llm-wiki/README.md`.

### Install the Claude plugin from the marketplace

From a Claude Code session:

```
/plugin marketplace add hevangel/dvcon_ai_library
/plugin install dvcon-papers@dvcon-marketplace
```

### Force reindex after embedding changes

```bash
uv run --project backend ingest --limit 1 --force
```

### Backend tests

```bash
uv run --project backend pytest
```

### Frontend tests

```bash
npm --prefix frontend test          # vitest run (one-shot)
npm --prefix frontend run test:watch # vitest watch
```

The frontend uses Vitest + @testing-library/react + jsdom. The setup file
(`frontend/src/test/setup.ts`) polyfills `matchMedia`, `ResizeObserver`, and
`scrollIntoView` for jsdom and registers jest-dom matchers.

### Validate compose config

```bash
./scripts/validate_compose.sh      # or: .\scripts\validate_compose.ps1
```

Static check that `compose.yaml` parses and `${VAR}` references resolve. Does
not pull images or start containers.

## Recommended Next Checks For A Future Agent

- If resuming after a crash, first verify backend health on `http://127.0.0.1:8010/api/health`.
- If metadata quality looks weaker than expected, verify the GROBID sidecar is running and `GROBID_ENABLED=true`.
- For containerized runs, prefer `docker compose up --build` over manually wiring `docker run` commands.
- If `docker compose up --build` appears stuck at startup, check the GROBID liveness probe on `http://127.0.0.1:8070/api/isalive`.
- Confirm frontend dev server target still matches `frontend/.env.local`.
- If chat fails, verify `.env` still contains valid `OPENAI_BASE_URL` and `OPENAI_API_KEY`.
- If semantic results are empty after corpus changes, run a forced ingest to rebuild embeddings.
- Before changing ports, check for occupied local ports to avoid collisions with unrelated services.

## Safety Notes

- Do not overwrite `.env` unless the user explicitly asks.
- Do not delete `data/` or `data.example/` unless the user explicitly asks.
- Do not revert unrelated git changes.
- Prefer incremental fixes over broad refactors because the app is already end-to-end functional.
