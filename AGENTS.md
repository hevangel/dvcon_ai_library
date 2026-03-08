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

## Repository Layout

- `backend/src/backend/main.py`: FastAPI app entrypoint
- `backend/src/backend/core/config.py`: runtime settings from `.env`
- `backend/src/backend/db/models.py`: SQLModel schema
- `backend/src/backend/db/session.py`: SQLite engine and FTS setup
- `backend/src/backend/api/`: route layer and response schemas
- `backend/src/backend/services/scraper.py`: DVCon sitemap crawl + PDF download
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
- `scripts/`: local startup scripts for bash and PowerShell
- `compose.yaml`: repo-managed app + GROBID runtime stack
- `data/paper/`: raw downloaded papers
- `data/`: runtime corpus data root containing downloaded PDFs, extracted markdown, TEI cache, DB, Chroma, and model cache
- `data.example/`: checked-in Horace Chan sample corpus mirroring the curated `data/` content layout without local DB/vector artifacts

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

## Search Design

- Keyword search uses SQLite `FTS5`.
- Semantic search uses ChromaDB with local embeddings.
- Hybrid search merges keyword and semantic results.
- Chat retrieval is constrained to selected paper IDs when available.
- Flattened search fields are preserved even when structured GROBID metadata is present.

## Extraction Design

- The markdown and image path remains `PyMuPDF` / `pymupdf4llm`.
- GROBID is an enrichment layer, not a replacement renderer.
- If GROBID is enabled and reachable, the extractor prefers GROBID title, abstract, structured authors, affiliations, and references.
- Local startup scripts should assume GROBID is part of the normal runtime, not an extra optional step.
- If GROBID is unavailable or errors, the extractor falls back to the existing heuristic metadata extraction without failing the ingest.
- Duplicate structured author entries from GROBID are deduplicated by normalized author name before `PaperAuthor` rows are written.
- Structured affiliations are persisted alongside the existing flattened `affiliations_text` field.
- Structured references are persisted alongside the existing flattened `references_text` field.

## Local Embedding Design

- Embeddings do not use the OpenAI API.
- Local model is configured in `.env` via:
  - `LOCAL_EMBEDDING_MODEL`
  - `LOCAL_EMBEDDING_DEVICE`
- Current default model: `BAAI/bge-m3`
- Expected vector dimension after reindex: `1024`
- `backend/src/backend/services/indexer.py` resets the Chroma collection if the embedding model changes, to avoid dimension mismatch with old vectors.
- CUDA is available on this machine and should be preferred.

## Environment Files

- `.env` is local-only and gitignored.
- `.env.example` is the template.
- Chat-related keys:
  - `OPENAI_BASE_URL`
  - `OPENAI_API_KEY`
  - `OPENAI_CHAT_MODEL`
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
- SQLite FTS keyword search
- Chroma semantic indexing
- local CUDA-backed embeddings
- grounded chat integration
- Dockerfile
- repo-managed `compose.yaml` full app + GROBID stack
- contributor guide in `CONTRIBUTION.md`
- local run scripts
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

## Important Gotchas

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
- When chat requests include `selected_paper_ids`, the backend should keep that scope authoritative; if retrieval is weak for a generic query, it should still build context from the selected papers rather than broadening to the full corpus.
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

### Start only the GROBID sidecar

```bash
docker compose up -d grobid
```

### Start the container stack

```bash
docker compose up --build
```

### Force reindex after embedding changes

```bash
uv run --project backend ingest --limit 1 --force
```

### Backend tests

```bash
uv run --project backend pytest
```

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
