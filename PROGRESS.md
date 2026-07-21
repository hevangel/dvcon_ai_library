# Progress Against Plan

This document checks the current repository state against the original DVCon Paper RAG Web App plan.

## Overall Status

The project is substantially implemented and is already functional end to end for a small ingested corpus.

Broad status by plan area:

- Scaffold and core architecture: complete
- DVCon crawl and paper download: complete
- PDF extraction and local data storage: complete
- Keyword and semantic indexing: complete
- React UI shell and tabbed workflow: complete
- Paper-grounded chat integration: implemented
- Local run scripts and Dockerfile: implemented
- Verification and production hardening: complete
- Full-corpus ingest and large-scale validation: complete

## Plan Checklist

### 1. Scaffold backend, frontend, config, local scripts, and container build

Status: complete

Implemented:

- `FastAPI` backend under `backend/`
- `React` + `TypeScript` + `Vite` frontend under `frontend/`
- root `.gitignore`
- `.env.example`
- local startup scripts in `scripts/`
- `Dockerfile`
- `compose.yaml` for the full app + GROBID container stack
- `CONTRIBUTION.md`
- `README.md`
- `AGENTS.md`
- `data.example/` checked-in sample corpus for the Horace Chan paper subset

Notes:

- The backend serves built frontend assets in production mode.
- A local dev override file `frontend/.env.local` is used for frontend-to-backend API routing during development.
- Local backend startup now brings up GROBID automatically by default.
- Docker Compose now runs both the app container and the GROBID sidecar together.
- Local and container startup now wait for GROBID readiness instead of only process launch.
- The GROBID liveness probe was corrected to use `8070` rather than `8071`.
- Docker Compose now publishes the app on host port `8011` by default to avoid conflict with the local backend on `8010`.
- The local GROBID startup scripts now support both `docker compose` and legacy `docker-compose`.

### 2. Implement DVCon crawler and resumable PDF download into `data/paper/`

Status: complete

Implemented:

- human-search-form crawling from the DVCon website UI
- paper-only filtering based on detail-page metadata
- direct PDF download
- resumable manifest at `data/ingest_manifest.json`
- storage under `data/paper/{year}/{location}/{slug}.pdf`

Notes:

- The crawler uses a browser-like user agent to avoid DVCon `403` responses.
- The crawler now treats the live document search UI as the authoritative discovery surface rather than the incomplete WordPress sitemap or archive-only paths.
- The implementation intentionally skips non-paper DVCon items.

### 3. Implement PDF-to-markdown extraction, image export, and metadata normalization into `data/`

Status: complete

Implemented:

- PDF to markdown extraction using `pymupdf4llm`
- image extraction to `data/markdown/{year}/{location}/images/{slug}/`
- markdown storage at `data/markdown/{year}/{location}/{slug}.md`
- optional TEI export at `data/tei/{year}/{location}/{slug}.tei.xml`
- markdown image links rewritten to relative `images/...` paths so local VS Code preview works
- frontend markdown rendering resolves those relative image links through the backend asset route during app usage
- hybrid metadata extraction:
  - markdown and images from `PyMuPDF` / `pymupdf4llm`
  - title, abstract, authors, affiliations, and references enriched from local GROBID when available
  - heuristic fallback retained when GROBID is disabled or unavailable
- SQLite persistence of papers, conferences, authors, structured affiliations (with company + city/state/country), references, and chunks

Partial / limitations:

- the current sidecar defaults to the lighter CRF GROBID image for broad compatibility, so metadata quality is improved but not maximal
- exact IEEE-style reference normalization is still only as strong as the upstream PDF / GROBID extraction quality

### 4. Build SQLite FTS + Chroma indexing and hybrid search APIs

Status: complete

Implemented:

- SQLite `FTS5` keyword index
- ChromaDB semantic index
- hybrid merge of keyword and semantic hits
- chunking of extracted markdown
- semantic search constrained to selected papers when needed
- local sentence-transformer embedding service
- flattened search text preserved alongside richer structured metadata

Important update versus original plan:

- semantic embeddings now use a local model instead of the OpenAI embeddings API
- the repo default local embedding model is now `BAAI/bge-m3`
- local model runs through `torch` and is CUDA-capable
- CUDA was verified on this machine

Notes:

- Chroma collection reset logic is present to handle embedding model changes cleanly
- switching from the prior `all-MiniLM-L6-v2` default requires a forced reindex because the dense vector dimension changes
- duplicate GROBID author entries are now deduplicated before `PaperAuthor` rows are persisted
- image storage is now directly colocated with the markdown tree; no backward-compatibility migration path remains in the extractor

### 5. Build the React UI with the four left-panel tabs and right-side chat

Status: complete

Implemented:

- professional title bar
- live subtitle counts for papers, years, and conference collections
- bold inline count emphasis in the subtitle instead of title-bar chips
- resizable left/right split layout on desktop
- left panel tabs:
  - Search Results
  - PDF
  - Markdown
  - Metadata Graph
- search results with:
  - polished query input and filter container styling
  - keyword / semantic / hybrid mode selector
  - year filter
  - location filter
  - checkbox multi-select
  - independent result-list scrolling inside the left panel
- click-on-paper behavior that activates the paper and switches to the PDF tab
- PDF download moved to a compact outlined icon-only button beside the next-page control, using the same styling and fixed dimensions as the pager buttons instead of a separate `Open PDF` button
- PDF-tab page rendering now auto-resizes to fit the current left-panel width instead of using a fixed page width
- PDF-tab pagination controls are now kept on a single dedicated line, separate from the wrapping paper title
- left-panel tab content now suppresses horizontal overflow so the workspace does not show an unnecessary horizontal scrollbar
- Markdown-tab diagrams now resolve markdown-relative image links through the backend asset route so extracted inline images render correctly during local Vite development and when served by the backend
- markdown rendering with embedded extracted images
- graph view using Cytoscape
- right-side chat panel with:
  - transcript
  - typed support for `/help`, `/clear`, and `/summarize`
  - command-aware help display that returns after `/clear`
  - Enter to submit
  - Shift+Enter for newline
  - submit button
  - visible loading state while the assistant reply is in flight
  - auto-scroll to the newest assistant reply
  - compact numbered citation chips plus matching `[n]` labels on selected-paper scope chips
  - visible active paper scope

Partial / limitations:

- the filter model is based on year and location, not a richer explicit conference entity selector
- the graph currently focuses on paper, conference, author, company, and reference nodes, but does not yet compute deeper cross-paper relationship graphs

### 6. Integrate OpenAI Responses API for paper-scoped chat

Status: implemented and validated

Implemented:

- chat service using the OpenAI Responses API
- configurable `OPENAI_BASE_URL` and `OPENAI_API_KEY`
- retrieval-grounded prompt construction
- support for selected paper scope
- end-to-end `previous_response_id` propagation so eligible follow-up turns can continue the prior Responses API conversation and save tokens
- selected-paper fallback context that preserves the chosen scope for generic prompts like "compare the two papers"
- selected-paper full-text escalation that estimates prompt tokens against the configured model context window and sends full selected paper content when it fits
- numbered citation metadata returned to the UI alongside title/year lookup data
- scraper URL discovery now uses the homepage Year and Location filters plus the live human search form results, so ingestion no longer depends on the incomplete WordPress document sitemap path

Validated:

- backend loads chat configuration from `.env`
- chat path is implemented in backend and wired to frontend
- live chat requests now complete successfully against the configured `gpt-5-mini` OpenAI-compatible endpoint
- the chat service no longer hard-codes `temperature`, which previously caused `400` errors from providers that reject that Responses API parameter for this model
- backend regression tests now cover generic compare prompts so scoped chat does not widen to unrelated papers when `selected_paper_ids` are present
- backend regression tests now also cover full selected-paper prompt escalation vs fallback section mode based on context-window budget
- backend smoke tests now cover `previous_response_id` forwarding through `/api/chat` and continuation requests in the chat service
- backend smoke tests now cover the human-interface scraper path that reads homepage filters and posts through the document search form directly

Notes:

- local runtime needed a port move from `8000` to `8010` because another unrelated service was already using `8000`
- the full-text escalation currently uses a conservative approximate token estimate and can be tuned per provider with `OPENAI_CHAT_MODEL_CONTEXT_WINDOW` and `CHAT_CONTEXT_OUTPUT_RESERVE_TOKENS`
- the live DVCon WordPress document sitemap path is incomplete for current content, so the scraper now treats the visible document search UI as the authoritative discovery surface

### 7. Add smoke tests and basic validation for scrape, extract, search, and chat endpoints

Status: complete

Implemented:

- backend smoke tests in `backend/tests/test_smoke.py`
- TEI parser tests in `backend/tests/test_tei_parser.py`
- hybrid and fallback extractor tests in `backend/tests/test_extractor_grobid.py`
- API route tests in `backend/tests/test_api_routes.py` (stats, search mode dispatch, paper detail 200/404, chat 503, ingest happy path + 409 + token guard)
- hardening unit tests in `backend/tests/test_hardening.py` (PDF validation, per-paper isolation, Chroma wipe protection, retry backoff, atomic manifest save)
- shared `backend/tests/conftest.py` resetting `@lru_cache` singletons between tests
- frontend Vitest suite (`npm --prefix frontend test`) with component tests for `search_results_tab` and `chat_panel`
- tests currently cover:
  - health endpoint
  - detail-page parsing helper
  - abstract / affiliation / reference extraction helpers
  - chunking and embedding-device fallback logic
  - TEI parsing for title, abstract, authors, affiliations, and references
  - TEI structured affiliation fields (company name, city, state, country)
  - extractor behavior with GROBID enrichment enabled
  - extractor behavior with GROBID unavailable
  - API route layer for stats, search, papers, chat (503), and admin ingest (incl. 409 and 401)
  - PDF integrity validation, per-paper ingest isolation, Chroma no-silent-wipe, retry backoff
- selected-paper chat scope preservation for generic compare prompts

Validated manually during development:

- backend imports
- frontend production build
- one-paper live ingest
- semantic search results
- local embedding generation on CUDA
- full-corpus (1646-paper) Chroma/SQL consistency check and search latency
- 5-paper forced re-ingest through the hardened pipeline with GROBID live (0 errors)

Missing or still thin:

- no end-to-end browser tests (Playwright); Vitest component tests only
- no full live Docker container smoke test in this session (only `docker compose config` validation)


## Storage and Ignore Rules

Status: complete

Implemented:

- `/data/` is gitignored
- `.env` is gitignored
- frontend local dev env override is gitignored
- generated corpus data and secrets are not intended for git

## Local Embedding and CUDA Status

Status: complete

Implemented:

- local embedding model via `sentence-transformers`
- `torch` installed from the CUDA wheel index
- embedding device resolution with CUDA preference and CPU fallback
- default chat model updated to `gpt-5-mini` in runtime env/config templates

Verified:

- CUDA available to PyTorch
- current GPU detected: NVIDIA GeForce RTX 3060 Ti
- the previous local embedding configuration generated 384-dim vectors
- the current Chroma collection metadata now reports `BAAI/bge-m3`
- the local `.env` was updated to `BAAI/bge-m3` so future restarts stay aligned with the rebuilt index
- Dockerfile and `compose.yaml` now honor `DATA_DIR` for the runtime data mount and container path

## Current Verified Progress

These items were explicitly verified during implementation:

- backend imports successfully
- frontend builds successfully with `npm run build`
- backend smoke tests pass with `uv run pytest`
- targeted chat regression coverage passes with `uv run --project backend pytest backend/tests/test_smoke.py`
- one live DVCon paper was ingested successfully
- extracted content was indexed into SQLite and Chroma
- semantic API search returned the ingested paper
- local manifest-based reindex completed successfully for 37 downloaded papers using `BAAI/bge-m3`
- old local ingest artifacts were cleared and replaced with a fresh 10-paper 2025 test corpus
- all 8 paper records authored by Horace Chan were identified, downloaded, extracted, and added to the local corpus, bringing the current indexed total to 18 papers
- a checked-in example corpus was created under `data.example/` with the 8 Horace Chan PDFs and their extracted markdown, TEI, and image assets
- structured affiliations (`Company` table + `Affiliation` location fields) are parsed from TEI, persisted with `_ensure_column` migrations, and rendered in the metadata graph with deterministic slug-based node ids
- the `keyword_search` selected-scope bug (local `paper_ids` reassignment shadowing the caller's filter) was fixed; the scope parameter is now authoritative
- `get_stats` now uses `SELECT COUNT(*)` and distinct-column queries instead of loading full rows
- deprecated `datetime.utcnow()` calls were replaced with timezone-aware `datetime.now(timezone.utc)` across models and indexer
- the chat continuation fallback now logs the swallowed error at debug level instead of silently retrying
- an MCP server (`backend/src/backend/mcp_server.py`, `dvcon-mcp` console script) exposes the service layer over stdio transport; all six tools register and import cleanly
- a workspace agent skill at `.agents/skills/dvcon-papers/SKILL.md` documents the MCP tool surface
- an Anthropic Claude plugin marketplace (`.claude-plugin/marketplace.json`) plus a self-contained `dvcon-papers` plugin (skill + `/dvcon` command + MCP server) validate as JSON
- the local corpus has since been ingested in full and incrementally refreshed: the original archive crawl brought it to 1646 papers across 16 years (2010–2025) and 41 conference collections, and a subsequent scoped 2025+2026 ingest added 206 more (now **1852 papers across 17 years 2010–2026, 42 conferences, 38761 chunks** indexed in both SQLite and Chroma)
- the full archive crawl completed (`ingest_manifest.json` now records 3321 `downloaded` and 2016 `skipped` non-paper items, up from the first-pass 1646/1951 after the 2025+2026 refresh), so "full-corpus ingest" is no longer a gap
- the scraper's document discovery was rewritten to follow the live site's **Document Library Pro** AJAX path: the search form now returns only a header skeleton, so `_search_form_document_urls` POSTs the search form to obtain a page-bound `table_id`, then pages through `admin-ajax.php` with `action=dlp_load_posts` and parses `/document/` links from each returned row; a legacy server-rendered table parse is kept as a fallback
- a `--years` CLI flag was added (`ingest --years 2025,2026`) to scope the crawl to specific year filters, skipping the pointless re-walk of older years already in the DB — this is the recommended way to fetch new papers incrementally
- a scoped 2025+2026 ingest added **206 new papers** to the corpus (now 1852 total across 17 years, including DVCon US 2026 and the full 2025 India / Europe / US sets); Chroma (38761) and SQL (38761) chunk counts still match exactly after the run
- backend tests grew to cover the new AJAX discovery path (table_id extraction, pagination, filter non-leakage into the AJAX payload) and the `--years` filter; 12 hardening tests pass
- metadata-graph nodes are now clickable with type-specific behavior: author / company nodes filter Search Results by name (keyword FTS), conference nodes filter by year + location, and reference nodes whose `normalized_title` resolves to an in-corpus paper jump to that paper's PDF tab (unresolved references render non-clickable). The graph response now carries per-node payload fields (`paper_id`, `author_name`, `company_name`, `conference_name`, `year`, `location`, `reference_id`) so the frontend decides click behavior without parsing id slugs. Reference resolution is exact normalized-title match (case-insensitive, punctuation-stripped) against a one-shot corpus title index. Verified live: paper 1648 has 14 references of which 4 resolve to in-corpus papers.
- frontend GraphElementData type was tightened from `Record<string, string>` to a typed interface; the graph tab passes the `cy` callback to `CytoscapeComponent` and registers a `tap node` handler; clickable nodes get a blue accent border + pointer cursor; backend (44 tests) and frontend (14 tests) suites both pass and the production build still succeeds

## Production Hardening (verified)

These hardening changes were implemented and exercised against the full 1646-paper corpus:

- SQLite WAL mode (`journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=60000`) is active on the live DB (`dvcon.db-wal` / `dvcon.db-shm` sidecar files present), so read endpoints stay responsive during writes
- `run_ingestion` isolates per-paper failures (a bad PDF / GROBID hiccup / embedding OOM logs and continues instead of aborting the batch) and records `status="index_error"` in the manifest
- `POST /api/admin/ingest` is serialized by a `threading.Lock` (second concurrent call returns HTTP 409) and optionally gated by `INGEST_ADMIN_TOKEN` (401 without a matching `X-Admin-Token` header when configured)
- PDF downloads are integrity-validated (`%PDF-` magic bytes, `Content-Length`, `fitz` page-count check); HTML interstitials and truncated downloads are rejected and deleted rather than persisted as `.pdf`
- Chroma/SQL consistency: `index_seed` commits SQL as the source of truth and compensates (deletes just-added Chroma ids) if the commit fails; on the live corpus, SQL chunk count (34454) equals the Chroma collection count (34454) and 200/200 sampled ids match
- the Chroma client/collection are cached singletons; an embedding-model mismatch now raises (with guidance to run `ingest --force`) instead of silently wiping the index, unless `ALLOW_CHROMA_WIPE=1`
- the chat `OpenAI` client is a cached singleton with explicit `timeout`/`max_retries`; `RateLimitError`, `APITimeoutError`, `APIConnectionError`, `AuthenticationError` map to HTTP 503 instead of 500
- the ingest manifest is written atomically (`.tmp` + `os.replace`) and saved every 25 papers during a crawl
- HTTP retries use exponential backoff with jitter and honor `Retry-After` on 429
- a 5-paper forced re-ingest through the hardened pipeline (with GROBID live) completed with 0 errors; hybrid and keyword search on the full corpus return coherent results

## Test Coverage (verified)

- backend: 39 tests pass (`uv run --project backend pytest`), including new API route tests (`test_api_routes.py`) covering `/api/stats`, `/api/search` mode dispatch, `/api/papers/{id}` 200/404, `/api/chat` 503 error path, and `/api/admin/ingest` happy path + concurrency 409 + token guard, plus hardening unit tests (`test_hardening.py`) for PDF validation, per-paper isolation, Chroma wipe protection, retry backoff, and atomic manifest save
- frontend: a Vitest + @testing-library/react + jsdom suite is wired up (`npm --prefix frontend test`) with 9 passing component tests for `search_results_tab` and `chat_panel`; the production build still succeeds with the test files present
- a shared `backend/tests/conftest.py` resets module-level `@lru_cache` singletons (chat client, Chroma collection, embedding model) between tests so monkeypatched fakes don't leak across tests
- Docker compose config validation is available via `scripts/validate_compose.{sh,ps1}` (`docker compose config -q`); `compose.yaml` validates cleanly

## Known Gaps and Risks

These are the main remaining gaps relative to the plan:

- the checked-in `data.example/` sample intentionally excludes SQLite, Chroma, and model-cache artifacts, and still mirrors the smaller Horace Chan subset rather than the full 1646-paper local corpus
- no full live Docker container smoke test in this session (only `docker compose config` validation); the runtime stack itself is exercised locally on the host, not inside the container image
- no frontend E2E / browser test suite (Vitest component tests only)
- `/admin/ingest` still runs synchronously in the threadpool with a 409 concurrency guard, rather than as a background job with progress reporting; a real job queue (RQ/Celery) is a future architectural change
- chat/auth is a single optional admin token, not a full auth framework

## Current Resume Priority

If work resumes from here, the recommended next steps are:

1. Verify backend health on `http://127.0.0.1:8010/api/health` (note: an unrelated "Trade History API" service has been observed occupying port 8010 on this host — if `/api/health` 404s, pick a free port in `.env` `PORT`).
2. Run a forced re-ingest over the full corpus (`uv run --project backend ingest --force`) to backfill the new structured-affiliation fields and company graph across all 1646 papers (a 5-paper sample already verified this path).
3. Add end-to-end browser tests (Playwright) on top of the existing Vitest component tests.
4. Improve metadata extraction quality further, especially reference normalization.
5. Validate the Docker image and full container startup path (only `docker compose config` has been validated so far).

## Bottom Line

The repository is beyond scaffolding and has reached a working prototype / early product stage.

It already satisfies most of the original plan in code:

- crawl
- download
- extract
- index
- search
- browse
- graph
- chat

What remains is mostly validation, hardening, richer metadata quality, and full-scale ingestion rather than core feature invention.
