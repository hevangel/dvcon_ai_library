# An AI Interface to 17 Years of DVCon

> The DVCon proceedings are one of the richest public records of industrial
> verification practice, but today they behave more like a PDF archive than a
> living knowledge system. This extended abstract presents the DVCon AI Library,
> an open-source project designed equally for human use and AI-agent use. It
> crawls the proceedings, converts papers into structured and searchable data,
> and exposes one shared corpus through human-facing web interfaces and
> machine-facing tools: a web application, grounded chat, a Model Context
> Protocol (MCP)
> server, and agent skills. The result supports more than
> retrieval-augmented generation: an engineer can discover and compare prior
> work from an editor, agents can mine the archive and synthesize cited
> reference material, and an author can use a guarded workflow to format and
> submit a new contribution to DVCon. We report a full-corpus build of 1,852
> papers spanning 2010-2026 across 42 conference collections, yielding 38,761
> indexed chunks, 3,342 authors, and 12,135 parsed references. From that
> foundation we generate a reproducible industry-trends report and a 100-page
> knowledge wiki grounded in the original papers. Together these capabilities
> turn DVCon from a site that AI can merely search into a conference knowledge
> loop that AI can help read, analyze, teach, and contribute back to.

## Motivation

Every verification engineer has rediscovered a solution that someone presented
at DVCon years earlier. The knowledge exists, but normal web search sees mostly
titles and isolated PDFs. A question such as "how do teams reuse a module-level
testbench at the SoC level?" may not match a title even when a paper answers it
in detail. General-purpose language models can respond fluently, but without
access to this literature they cannot reliably distinguish established
practice from plausible invention.

The deeper problem is not simply that DVCon lacks a chatbot. The proceedings
have not been assembled as infrastructure that software and agents can inspect,
cite, transform, and use within an engineering workflow. This project asks what
becomes possible when the conference archive is treated as an interface rather
than a collection of downloads.

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

The pipeline is idempotent and resumable. It isolates failures per paper and
validates downloads, allowing a full-archive ingest to continue through corrupt
files, parser outages, and interrupted runs.

## One Corpus for Humans and AI Agents

Two indexes are maintained over the same content. Keyword search uses SQLite
FTS5; semantic search uses a vector database populated by a local multilingual
embedding model producing 1,024-dimensional vectors on a consumer GPU. No paper
text leaves the machine during indexing. Hybrid search combines both because
they fail differently: semantic retrieval handles paraphrase, while keywords
remain better for exact signal names, standards, and tool flags.

The corpus is deliberately built for two audiences. For humans, the web
interface supports search, PDF and markdown reading, metadata-graph exploration,
and paper-scoped chat. Chat keeps a user's selected papers authoritative, even
for a generic request such as "compare these two," and returns citations to the
source papers. These views let an engineer inspect the evidence directly rather
than treating an AI answer as the final interface.

For AI agents, the same service layer is exposed through an MCP server. A packaged
DVCon Papers agent skill teaches an AI assistant when and how to invoke tools
for search, paper text, metadata, citation graphs, corpus statistics, and
grounded comparison. This changes the interaction model: instead of visiting a
separate RAG site, an engineer can ask about prior DVCon work while writing a
test plan, reviewing code, or investigating a regression in the editor where
the work is already happening.

## From Archive to New Knowledge

Treating the proceedings as data yields a picture of the field that no
individual paper contains. A reproducible analysis report answers questions such
as the geographic distribution of contributions over time, the rise and fall of
verification languages and methodologies, the balance between industry and
academia, and the concentration of output among companies and repeat authors.
One finding is uncomfortable and worth stating plainly: only about ten percent
of papers link to a public repository, so most published methodology is not
directly reproducible by a reader.

A second artifact is a 100-page knowledge wiki synthesized by LLM agents from
topic-specific evidence bundles. It covers foundations, UVM, formal
verification, coverage, safety and security, protocols, SoC verification, and
emerging AI-assisted flows. Each page cites the papers used to create it and
closes with a source bibliography. The pipeline separates retrieval from
writing, making each generated page auditable and regenerable rather than
merely plausible. This demonstrates a different way to interact with DVCon:
agents can reorganize many years of papers into a navigable technical textbook
without severing the connection to the original authors.

## Closing the Conference Knowledge Loop

Interaction should not stop at consuming past papers. The repository also
contains a DVCon Submit agent skill for the path back into the conference. It
converts a paper written in Markdown into the official IEEE-styled Word and PDF
formats, checks extended-abstract constraints such as word count and
double-blind author removal, discovers the current Oxford Abstracts submission
stage, and can populate the live form and upload the PDF through a visible
browser. Credentials remain with the author, required metadata is never
invented, and the final Submit action requires explicit human confirmation.

This abstract itself was prepared with that workflow. The example illustrates
an important boundary for AI-assisted engineering: automate repetitive,
verifiable mechanics while preserving human control over identity, attestations,
technical claims, and publication. Combined with corpus access, the two skills
form a practical loop—read DVCon from an engineering agent, develop and validate
a new contribution, then prepare it for DVCon through the same agent
environment.

## Open-Source Availability

The full pipeline has been run end to end on the complete archive. The DVCon AI
Library is an open-source project: its corpus builder, human and agent
interfaces, agent skills, analysis report, wiki generator, tests, and
reproducible container stack are publicly available in the GitHub repository
[6]. Raw proceedings PDFs are not redistributed; the tooling retrieves them
from the official site.

## References

[1] Lewis, P., et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," Advances in Neural Information Processing Systems, 2020.

[2] Chen, J., Xiao, S., Zhang, P., et al., "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation," 2024.

[3] Lopez, P., "GROBID: Combining Automatic Bibliographic Data Recognition and Term Extraction for Scholarship Publications," Research and Advanced Technology for Digital Libraries, 2009.

[4] Anthropic, "Model Context Protocol Specification," 2024.

[5] SQLite Consortium, "SQLite FTS5 Full-Text Search Extension," SQLite Documentation.

[6] "DVCon AI Library," GitHub repository. [Online]. Available: https://github.com/hevangel/dvcon_ai_library
