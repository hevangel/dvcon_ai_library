# Mining 17 Years of DVCon Papers with RAG Agents

> The DVCon proceedings are one of the richest public records of industrial
> verification practice, yet they are effectively unsearchable. Papers are
> published as standalone PDFs behind a per-conference document library with no
> full-text index, no semantic search, and no machine-readable metadata. This
> extended abstract describes an open-source platform that crawls the complete
> proceedings archive, extracts structured metadata and markdown from every PDF,
> and exposes the result through hybrid keyword-plus-semantic search,
> source-grounded chat, and a Model Context Protocol (MCP) server that lets AI coding
> agents query the corpus from inside the engineer's existing tooling. We report
> a full-corpus build of 1,852 papers spanning 2010-2026 across 42 conference
> collections, yielding 38,761 indexed chunks, 3,342 authors, and 12,135 parsed
> reference entries. We then show three things the indexed corpus makes
> possible: a reproducible data-mining report on 17 years of verification
> industry trends, a 100-page synthesized knowledge wiki in which every claim is
> grounded in cited papers, and an agent skill that answers methodology
> questions with citations instead of hallucinations.

## Motivation

Every verification engineer has had the experience of solving a problem that
someone already presented at DVCon five years earlier. The knowledge exists, but
retrieval does not. Searching the conference site returns title-level keyword
matches at best; a query like "how do teams reuse a module-level testbench at
the SoC level" matches nothing, because the answer lives in the body of a paper
whose title never uses those words. Meanwhile general-purpose language models
answer verification questions fluently and frequently wrongly, because they were
never grounded in this literature and cannot cite it.

The gap is not a modeling problem. It is a corpus problem: the proceedings have
never been assembled into a machine-readable form. This work closes that gap and
treats the resulting corpus as infrastructure.

## Corpus Construction

Discovery walks the conference site's Year x Location filter matrix and posts
each combination through the human-facing document search form. This proved
necessary rather than convenient: the site's published document sitemap is
incomplete, and the results table is rendered client-side by a WordPress plugin
that returns only a header skeleton to a naive scrape. Rows arrive through a
separate AJAX endpoint keyed by a page-bound token issued by the search POST, so
the crawler must reproduce the browser's two-step handshake. Only items whose
detail page declares a paper type and PDF format are downloaded.

Extraction is a hybrid. A PDF-to-markdown pass renders body text and exports
embedded figures, while a local instance of a scholarly document-analysis
service parses the header and bibliography into structured XML, from which we
recover title, abstract, per-author affiliations with city and country, and
individual reference entries. When that service is unavailable the pipeline
falls back to heuristic extraction rather than failing, so a partial outage
degrades metadata quality instead of aborting an ingest of thousands of papers.

The pipeline is idempotent, resumable, and isolates failures per paper: a
corrupt PDF, a parser hiccup, or an out-of-memory embedding call is logged and
skipped rather than abandoning the batch. Downloads are validated by magic
bytes, content length, and a page-count check, so error pages and truncated
transfers are rejected instead of being persisted as unreadable PDFs.

## Retrieval and Grounded Chat

Two indexes are maintained over the same content. Keyword search uses SQLite
FTS5 over flattened per-paper text; semantic search uses a vector database
populated by a local multilingual embedding model producing 1,024-dimensional
vectors on a consumer GPU. No text leaves the machine during indexing. A hybrid
mode merges both result sets, which matters because the two fail differently:
keyword search misses paraphrase, and dense retrieval misses exact signal names,
standard numbers, and tool flags.

Chat is retrieval-grounded and scope-aware. When the user selects specific
papers, that scope stays authoritative even for generic prompts such as "compare
these two," which naively implemented retrieval widens into unrelated results.
If the selected papers fit inside the model's context window the full text is
sent; otherwise the system falls back to curated sections. Every answer returns
numbered citations that resolve to the underlying paper and page.

## Agents, Not Just a Web App

The same service layer is exposed twice: as a REST API behind a browser UI with
PDF, markdown, and metadata-graph views, and as an MCP server over stdio. The
second surface is the interesting one. It lets an AI coding assistant already
running in the engineer's editor search the proceedings, pull a paper's
markdown, inspect its citation graph, and answer with references, without the
engineer leaving their workflow or trusting an ungrounded model. A packaged
agent skill ships the tool descriptions so the capability is discovered
automatically rather than invoked by hand.

## What the Corpus Reveals

Treating the proceedings as data yields a picture of the field that no
individual paper contains. A reproducible analysis report answers questions such
as the geographic distribution of contributions over time, the rise and fall of
verification languages and methodologies, the balance between industry and
academia, and the concentration of output among companies and repeat authors.
One finding is uncomfortable and worth stating plainly: only about ten percent
of papers link to a public repository, so most published methodology is not
directly reproducible by a reader.

A second artifact is a 100-page knowledge wiki synthesized from the corpus,
covering foundations, testbench methodology, formal verification, coverage,
safety and security, protocols, and emerging AI-assisted flows. Each page is
written from a retrieved evidence bundle and closes with a bibliography of the
real papers behind it, which makes the generated text auditable rather than
merely plausible.

## Status and Availability

The full pipeline has been run end to end on the complete archive. Index
consistency between the relational store and the vector store is verified after
every ingest, and the platform ships with automated backend and frontend test
suites plus a container stack for reproduction. The corpus builder, search
backend, web UI, agent server, analysis report, and wiki generator will be
released under an open-source license so that other teams can rebuild the index
locally and extend the analysis. Raw proceedings PDFs are not redistributed;
the tooling re-downloads them from the official site.

## References

[1] Lewis, P., et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," Advances in Neural Information Processing Systems, 2020.

[2] Chen, J., Xiao, S., Zhang, P., et al., "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation," 2024.

[3] Lopez, P., "GROBID: Combining Automatic Bibliographic Data Recognition and Term Extraction for Scholarship Publications," Research and Advanced Technology for Digital Libraries, 2009.

[4] Anthropic, "Model Context Protocol Specification," 2024.

[5] SQLite Consortium, "SQLite FTS5 Full-Text Search Extension," SQLite Documentation.
