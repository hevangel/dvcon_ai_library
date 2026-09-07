# An Interface to 17 Years of DVCon

## Abstract

The DVCon proceedings contain years of practical knowledge about verification languages, tools, methodologies, and production experience, but that knowledge is distributed across PDFs and difficult to search or synthesize. This work presents the **DVCon AI Library**, an open-source, locally deployable knowledge system that converts the proceedings into searchable, evidence-preserving data for engineers and AI agents. The system combines hybrid retrieval, grounded question answering, metadata exploration, trend analysis, an LLM-generated cited wiki, and Model Context Protocol (MCP) access. Beyond document search, the project explores an AI-native workflow in which agents can inspect, compare, cite, and eventually reproduce technical results while preserving links to original papers.

## 1. Background

The DVCon proceedings are a valuable technical archive, but using many years of papers remains difficult. Finding relevant work often requires knowing the right title or terminology in advance, and comparing ideas across years requires substantial manual effort. The project began in 2025 as an experiment in retrieval-augmented generation (RAG) [1] and in “vibe coding”: could a hardware engineer use modern AI coding agents to build a complete software system outside his primary expertise?

As coding agents improved, the project changed from hand-designing every component to specifying desired behavior and supervising the generated implementation. The resulting DVCon AI Library transforms the archive into a system intended not merely to generate plausible answers, but to make technical knowledge searchable, inspectable, citable, and reusable.

## 2. Application

A crawler discovers DVCon papers across conference years and locations, follows paper detail pages, and retrieves available PDFs. The ingestion pipeline converts papers to Markdown and extracts figures, while GROBID enriches scholarly metadata such as titles, abstracts, authors, affiliations, and references [2]. The corpus is indexed using SQLite FTS5 for exact full-text search [3] and BGE-M3 embeddings for semantic retrieval [4]. Combining lexical and semantic search is useful because exact terminology and semantic similarity fail in different ways. Retrieved evidence can then support paper-grounded RAG responses [1].

The web application supports corpus search, PDF and Markdown reading, metadata and reference exploration, paper comparison, and grounded chat. The same knowledge is exposed through an MCP server [5], allowing compatible AI agents to search papers, inspect full text and metadata, compare evidence, and use DVCon material inside engineering workflows. The repository also includes an agent skill that describes how to search, inspect, compare, and cite the corpus [6].

## 3. LLM-Wiki

A major extension is the DVCon LLM-wiki, inspired by Karpathy’s LLM Wiki pattern [7]. Search answers “Where is the relevant paper?” and chat answers “What do these papers say?” A wiki serves a different purpose: it creates a persistent, revisable map of the field.

An agent organizes the corpus into topics such as UVM, formal verification, coverage, safety and security, protocols, SoC verification, and AI-assisted verification. Each page is generated from a saved evidence bundle containing the papers and passages used for its claims. Pages can therefore be regenerated, inspected, and audited instead of becoming untraceable generated prose.

This structure helps engineers learn a topic, prepare reviews, build verification plans, and identify prior art. More broadly, it demonstrates that once a conference archive is represented as structured and inspectable data, an AI agent can reorganize it into new technical knowledge while retaining provenance to the original authors and papers.

## 4. Insights Across 17 Years

The structured corpus also enables longitudinal analysis that is difficult when papers are read individually. The project examines changes in verification languages and methodologies, geographic and organizational participation, industry versus academic contribution, collaboration patterns, and the availability of public artifacts.

Simple questions become surprisingly informative: Which authors contributed the most papers? Which organizations appear most consistently? Who published over the longest span? Which authors appear in the earliest year represented by the corpus and were still publishing in 2025? Term-frequency and metadata analysis can also show technologies that rise rapidly, topics that persist while changing meaning, and communities that discuss similar problems using different terminology.

These analyses turn the archive from a collection of documents into a dataset about the history of verification practice. The full paper and presentation will include quantitative results, visualizations, and examples derived from the completed corpus.

## 5. Open Source and AI-Native Workflow

The implementation, LLM-wiki, analysis scripts, generated insights, and agent skills are open source [6]. The repository does not redistribute the DVCon proceedings archive; users run the crawler against the official proceedings to construct a local corpus. This preserves a direct connection to the source material while avoiding redistribution of conference PDFs.

The larger design goal is an **AI-native engineering workflow**: the agent should be able to access the same papers, metadata, search results, graphs, and statistics available to the human user. A separate chatbot receiving copied text is insufficient. Through MCP and packaged skills, an agent can operate on the corpus directly.

A future extension is experimental reproduction. Given a paper and suitable tools, an agent could attempt the described experiment, compare the result with the publication, and record supporting or contradictory evidence. The repository also includes a DVCon submission skill to help authors organize submissions, check structure and completeness, and revise technical writing. This extended abstract itself was authored by the author with AI assistance for editing and language polishing.

## 6. Conclusion

The DVCon AI Library began as a solution to a search problem and became an experiment in AI-assisted software development, RAG, structured technical knowledge, and human-agent collaboration. It provides hybrid search, grounded chat, metadata exploration, longitudinal analysis, a cited LLM-wiki, MCP services, and agent skills while preserving the path from generated insight back to original evidence.

The project is intended as a community resource. Contributions are especially welcome for older proceedings, particularly papers before 2010 that are not currently downloadable through the existing archive. Recovering them would make the historical analysis more complete and help future AI tools learn from a fuller record of verification practice.

## References

[1] P. Lewis *et al*., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” in *Advances in Neural Information Processing Systems*, vol. 33, 2020, pp. 9459–9474.

[2] P. Lopez, “GROBID: Combining Automatic Bibliographic Data Recognition and Term Extraction for Scholarship Publications,” in *Research and Advanced Technology for Digital Libraries*, Lecture Notes in Computer Science, vol. 5714, 2009, pp. 473–474, doi: 10.1007/978-3-642-04346-8_62.

[3] SQLite, “SQLite FTS5 Extension,” *SQLite Documentation*. [Online; accessed Sep. 7, 2026].

[4] J. Chen, S. Xiao, P. Zhang, K. Luo, D. Lian, and Z. Liu, “M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation,” in *Findings of the Association for Computational Linguistics: ACL 2024*, 2024, pp. 2318–2335, doi: 10.18653/v1/2024.findings-acl.137.

[5] Model Context Protocol, “Specification (2024-11-05),” 2024. [Online; accessed Sep. 7, 2026].

[6] “DVCon AI Library,” GitHub repository, 2026. [Online; accessed Sep. 7, 2026].

[7] A. Karpathy, “LLM Wiki,” GitHub Gist, Apr. 4, 2026. [Online; accessed Sep. 7, 2026].