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
- Verification and production hardening: partial
- Full-corpus ingest and large-scale validation: not yet completed

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

- sitemap crawling from the DVCon WordPress sitemap
- paper-only filtering based on detail-page metadata
- direct PDF download
- resumable manifest at `data/ingest_manifest.json`
- storage under `data/paper/{year}/{location}/{slug}.pdf`

Notes:

- The crawler uses a browser-like user agent to avoid DVCon `403` responses.
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
- SQLite persistence of papers, conferences, authors, structured affiliations, references, and chunks

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
- selected-paper fallback context that preserves the chosen scope for generic prompts like "compare the two papers"
- selected-paper full-text escalation that estimates prompt tokens against the configured model context window and sends full selected paper content when it fits
- title/year citation metadata returned to the UI
- scraper URL discovery now uses the homepage Year and Location filters plus the corresponding human-facing archive pages, so ingestion no longer depends on the incomplete WordPress document sitemap path

Validated:

- backend loads chat configuration from `.env`
- chat path is implemented in backend and wired to frontend
- live chat requests now complete successfully against the configured `gpt-5-mini` OpenAI-compatible endpoint
- the chat service no longer hard-codes `temperature`, which previously caused `400` errors from providers that reject that Responses API parameter for this model
- backend regression tests now cover generic compare prompts so scoped chat does not widen to unrelated papers when `selected_paper_ids` are present
- backend regression tests now also cover full selected-paper prompt escalation vs fallback section mode based on context-window budget
- backend smoke tests now cover the human-interface scraper path that reads homepage archive filters and crawls archive pages directly

Notes:

- local runtime needed a port move from `8000` to `8010` because another unrelated service was already using `8000`
- the full-text escalation currently uses a conservative approximate token estimate and can be tuned per provider with `OPENAI_CHAT_MODEL_CONTEXT_WINDOW` and `CHAT_CONTEXT_OUTPUT_RESERVE_TOKENS`
- the live DVCon WordPress document sitemap path is incomplete for current content, so the scraper now treats the visible archive UI as the authoritative discovery surface

### 7. Add smoke tests and basic validation for scrape, extract, search, and chat endpoints

Status: mostly complete

Implemented:

- backend smoke tests in `backend/tests/test_smoke.py`
- TEI parser tests in `backend/tests/test_tei_parser.py`
- hybrid and fallback extractor tests in `backend/tests/test_extractor_grobid.py`
- tests currently cover:
  - health endpoint
  - detail-page parsing helper
  - abstract / affiliation / reference extraction helpers
  - chunking and embedding-device fallback logic
  - TEI parsing for title, abstract, authors, affiliations, and references
  - extractor behavior with GROBID enrichment enabled
  - extractor behavior with GROBID unavailable
- selected-paper chat scope preservation for generic compare prompts

Validated manually during development:

- backend imports
- frontend production build
- one-paper live ingest
- semantic search results
- local embedding generation on CUDA

Missing or still thin:

- no frontend automated tests
- no end-to-end browser tests
- no dedicated API tests yet for `/api/chat`, `/api/search`, `/api/papers/{id}/graph`, or `/api/admin/ingest`
- no full end-to-end Docker runtime validation in this session beyond `docker compose config`

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
- one live DVCon paper was ingested successfully
- extracted content was indexed into SQLite and Chroma
- semantic API search returned the ingested paper
- local manifest-based reindex completed successfully for 37 downloaded papers using `BAAI/bge-m3`
- old local ingest artifacts were cleared and replaced with a fresh 10-paper 2025 test corpus
- all 8 paper records authored by Horace Chan were identified, downloaded, extracted, and added to the local corpus, bringing the current indexed total to 18 papers
- a checked-in example corpus was created under `data.example/` with the 8 Horace Chan PDFs and their extracted markdown, TEI, and image assets

## Known Gaps and Risks

These are the main remaining gaps relative to the plan:

- full archive ingest has not been run yet
- the current local corpus intentionally mixes the 2025 test set with 8 Horace Chan papers from 2012-2022
- the checked-in `data.example/` sample intentionally excludes SQLite, Chroma, and model-cache artifacts
- the new GROBID metadata path has not yet been validated against a larger real DVCon batch in this session
- no full Docker smoke test yet
- no automated frontend test suite yet
- no large-corpus performance validation yet

## Current Resume Priority

If work resumes from here, the recommended next steps are:

1. Finish a live backend health and chat verification on the moved local port `8010`.
2. Run a larger ingest batch, then eventually a full ingest.
3. Add more API and UI tests.
4. Improve metadata extraction quality, especially affiliations and references.
5. Validate the Docker image and container startup path.

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
