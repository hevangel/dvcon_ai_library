---
description: Search the DVCon paper corpus and answer with grounded citations. Pass a query, optional year/location filters, or nothing to browse.
argument-hint: [query]
allowed-tools: dvcon__search_papers, dvcon__get_paper_detail, dvcon__get_paper_markdown, dvcon__get_paper_graph, dvcon__corpus_stats, dvcon__chat_with_papers
---

Use the `dvcon` MCP server tools to handle this request against the DVCon paper corpus:

$ARGUMENTS

Follow this flow:

1. If the request looks like a search or topic question, call `dvcon__search_papers` with the query (hybrid mode by default). Present the top results as a numbered list with `paper_id`, title, year, location, and a one-line snippet.
2. If the request names or implies a specific paper, call `dvcon__get_paper_detail` and `dvcon__get_paper_markdown` for that `paper_id` and answer from the extracted content.
3. If the request asks for synthesis, comparison, or summarization across one or more papers, call `dvcon__chat_with_papers` with the resolved `selected_paper_ids` and the user's question. Cite claims with the returned `[n]` citation labels.
4. If the request asks for corpus size or coverage, call `dvcon__corpus_stats`.

Rules:
- Always cite the `paper_id` (and title + year when space allows) when referencing a paper.
- If a tool returns an `error` field, surface that error verbatim instead of fabricating content.
- Never invent DVCon paper content that did not come back from a tool call.
