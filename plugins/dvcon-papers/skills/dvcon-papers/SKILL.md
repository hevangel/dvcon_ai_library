---
name: dvcon-papers
description: Search, read, and ask grounded questions about the DVCon conference paper corpus (dvcon-proceedings.org) via the local dvcon MCP server. Use whenever the user asks about DVCon papers, EDA/verification methodology papers, wants to search the proceedings archive, summarize a paper, compare selected papers, look up authors/affiliations/references, or read extracted paper markdown — even if they don't explicitly say "DVCon" or "MCP". Provides the search_papers, get_paper_detail, get_paper_markdown, get_paper_graph, corpus_stats, and chat_with_papers tools.
---

# DVCon Papers

This skill gives the agent direct access to the local DVCon paper corpus through the
`dvcon` MCP server (defined in `backend/src/backend/mcp_server.py`). The corpus is the
same one served by the FastAPI backend and React UI; the MCP server just re-exposes it
as tools so agents can query it without going over HTTP.

## When to use

Trigger this skill when the user wants to:

- search the DVCon proceedings by keyword, topic, author, method, or concept
- read a specific paper's extracted markdown or full metadata
- summarize one paper or compare several papers
- look at the author / conference / company / reference graph for a paper
- ask a grounded question whose answer must come from the indexed papers
- get corpus counts (how many papers, years, locations)

## Prerequisites

The `dvcon` MCP server is bundled with this plugin and started automatically via
`uv run --project backend dvcon-mcp`. The corpus lives under `data/` at the repo root
and is configured via `.env`. The read tools (search, detail, markdown, graph, stats)
work without GROBID or OpenAI. The `chat_with_papers` tool requires `OPENAI_BASE_URL`
and `OPENAI_API_KEY`.

If the corpus is empty, seed it first with `uv run --project backend ingest --limit 5`,
then re-run search.

## Available tools

| Tool | Purpose |
|------|---------|
| `search_papers` | Keyword / semantic / hybrid search with year + location filters |
| `get_paper_detail` | Full metadata for one paper (abstract, authors, affiliations, references) |
| `get_paper_markdown` | Extracted markdown body of a paper (includes image refs) |
| `get_paper_graph` | Cytoscape-style nodes/edges for paper relationships |
| `corpus_stats` | Paper count, years, locations, conference count |
| `chat_with_papers` | Grounded Q&A; constrain to selected paper ids when comparing |

## Workflows

### 1. Find papers on a topic

Call `search_papers` with a free-text query. Hybrid mode (default) merges SQLite FTS5
keyword hits with bge-m3 semantic hits. Example call:

```
search_papers(query="UVM register abstraction layer", mode="hybrid", limit=10)
```

Expected return shape:

```json
{
  "mode": "hybrid",
  "count": 3,
  "items": [
    {
      "paper_id": 7,
      "title": "...",
      "abstract": "...",
      "authors": ["..."],
      "affiliations": ["..."],
      "year": 2024,
      "location": "united states",
      "conference_name": "DVCon United States 2024",
      "score": 0.82,
      "snippet": "..."
    }
  ]
}
```

Leave `query` empty to browse. Filter with `year=2024` or `location="india"`.

### 2. Read a paper

After finding a `paper_id`, fetch its detail and markdown:

```
get_paper_detail(paper_id=7)
get_paper_markdown(paper_id=7)
```

The markdown response includes the raw extracted text with markdown-relative image
references (`images/...`). Quote specific sections when answering the user.

### 3. Summarize or compare papers

Pass one or more `paper_id`s to `chat_with_papers` to constrain the answer to those
papers. With a selection, the server sends full paper text when it fits the model
context window, else curated sections. Without a selection, retrieval runs corpus-wide.

```
chat_with_papers(
  question="Compare the formal verification approaches in these two papers.",
  selected_paper_ids=[7, 12]
)
```

Returns:

```json
{
  "answer": "...",
  "citations": [{"index": "1", "paper_id": "7", "title": "...", "year": "2024"}],
  "scope_paper_ids": [7, 12]
}
```

Citation `index` numbers correspond to the order of `selected_paper_ids` / retrieval.

### 4. Explore relationships

```
get_paper_graph(paper_id=7)
```

Returns `nodes` and `edges` for the paper's conference, authors, companies, and
references. Node `type` is one of `paper`, `conference`, `author`, `company`,
`reference`.

## Output contract

- Always cite `paper_id` (and title + year when space allows) when referencing a paper.
- When the user asks to "summarize this paper" without a selection, first run
  `search_papers` to disambiguate, then `chat_with_papers` with the resolved id.
- If a tool returns `{"error": "..."}`, surface the error rather than fabricating a
  paper that does not exist in the corpus.
- Never invent DVCon paper content that did not come back from a tool call.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `search_papers` returns empty for every query | Corpus is empty — run `uv run --project backend ingest --limit 5` |
| `chat_with_papers` returns an error about OpenAI config | Set `OPENAI_BASE_URL` and `OPENAI_API_KEY` in `.env` |
| Semantic results look stale after an embedding-model change | Force a reindex: `uv run --project backend ingest --limit 1 --force` |
| `get_paper_markdown` says file is missing on disk | Re-ingest the paper; the markdown tree may have been cleared |
| MCP tools are not available | Ensure the `dvcon` MCP server is enabled in the client's MCP settings |
