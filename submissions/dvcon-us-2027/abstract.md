# An Interface to 17 Years of DVCon

## Abstract

For many years, the DVCon proceedings have represented a valuable but difficult-to-use archive. The papers contain practical knowledge about verification languages, tools, methodologies, and production experience, yet that knowledge is scattered across PDF files and is not easily searchable, comparable, or reusable. Finding an answer often depends on guessing the title or exact terminology of the right paper. There has been no simple way to ask questions across many years of proceedings while preserving a direct path back to the original evidence.

This project began in 2025, around the time Andrew Karpathy popularized the idea of “vibe coding.” Initially, I wanted to build a retrieval-augmented generation (RAG) system and chatbot for the DVCon archive. I am a hardware engineer pretending to be a software engineer, so the project was also an experiment in whether modern AI could help me build software outside my traditional expertise. As AI coding systems improved, the project changed character. Instead of carefully designing every component myself, I could increasingly describe what I wanted and let the software take shape. I have worked on this open-source project since the early days of vibe coding. With the release of Opus 4.6 and GPT-5, AI agents finally became capable of debugging generated code, repairing integration problems, and making the system work end to end.

The result is the DVCon AI Library, an open-source application that turns the proceedings into an evidence-preserving knowledge system for both engineers and AI agents. It combines a searchable corpus, semantic retrieval, paper reading, metadata exploration, grounded chat, trend analysis, and an agent-accessible service layer. The goal is not simply to produce plausible answers. It is to make DVCon knowledge easier to inspect, compare, cite, and reuse while retaining links to the original papers.

## The Application

The application begins with a crawler that discovers DVCon papers across years and conference locations. It reproduces the behavior of the DVCon document-search site, follows paper detail pages, and retrieves available PDFs. Each paper is processed through a hybrid extraction pipeline that recovers Markdown text, figures, scholarly metadata, authors, affiliations, and references. The resulting corpus is indexed using both SQLite FTS5 for exact keyword search [5] and vector embeddings for semantic search [2]. Hybrid retrieval combines these approaches because exact terminology and semantic similarity fail in different ways. Retrieval-augmented generation then connects retrieved evidence to grounded responses [1].

A web interface allows users to search the corpus, read PDFs and extracted Markdown, explore authors and references, compare selected papers, and ask questions grounded in specific sources. The same capabilities are exposed through a Model Context Protocol server [4], allowing an AI agent to use DVCon knowledge from within an engineering workflow. A packaged skill explains how an agent should search, inspect papers, compare evidence, and cite sources.

The final paper will provide more details about the implementation, including the crawler, extraction pipeline, indexing strategy, metadata model, and evaluation. However, the implementation itself is becoming less important. An AI coding agent can now rapidly assemble much of an application like this. When I built the system, I still had to guide the agent and make human decisions about the technology stack, data model, and workflow. By the time DVCon meets next year, it may be enough to describe the desired application and let the agent handle nearly everything else.

## The LLM-Wiki

One of the most interesting results of the project is the LLM-wiki, inspired in part by Andrew Karpathy’s LLM-wiki project. The DVCon LLM-wiki is an open-source, generated, cited technical wiki built from the DVCon corpus and available in the project repository. Instead of answering one question at a time, an agent organizes the papers into broader topics such as UVM, formal verification, coverage, safety and security, protocols, SoC verification, and AI-assisted verification flows. Each page is generated from a saved evidence bundle containing the papers and passages used to support its claims. The pages can therefore be regenerated, inspected, and audited rather than treated as untraceable generated prose.

The LLM-wiki is useful for more than search and chat. Search helps locate papers, and chat helps answer questions, but a wiki provides a persistent map of the field. It reveals how concepts connect, which techniques recur across years, how terminology changes, and where different communities discuss similar problems using different language. It also gives engineers a starting point for learning a topic, preparing a design review, writing a verification plan, or identifying prior art before beginning a new project.

The wiki demonstrates a broader idea: once a conference archive is represented as structured, inspectable data, an AI agent can reorganize the archive into new forms of technical knowledge without breaking the connection to the original authors and papers. It also connects this project to an emerging pattern in which language models are used not merely to retrieve documents, but to construct durable, cited, and continuously revisable knowledge bases.

## Insights and Trends

The corpus also supports analysis across the full archive. The project examines changes in verification languages and methodologies, geographic and organizational participation, industry and academic representation, and the availability of public artifacts. It can show which terms rise and fall over time, which topics persist, and how new approaches enter the DVCon vocabulary.

Several findings are especially interesting because they are difficult to notice when papers are read individually. The analysis can identify which author has contributed the most papers, which organizations and research groups appear most consistently, and which authors have published continuously across the longest span. It can also reveal who published in the earliest year represented in the corpus and was still publishing as recently as 2025. Other patterns show technologies that appear suddenly and then become part of the background vocabulary, as well as topics that remain present for many years but change meaning as tools and methodologies evolve.

Authors, companies, and research groups also form patterns that are easier to see through metadata and citation relationships than through ordinary reading. These include recurring collaborations, shifts in industry and academic participation, and the movement of ideas between communities.

The full DVCon paper and presentation will include more of these observations, along with additional visualizations and examples of how the corpus can be used to explore the history of verification practice.

## Open Source and an AI-Native Workflow

The project is open source. The LLM-wiki, application code, analysis scripts, generated insight slides, and agent skills are available in the repository. Because of copyright concerns, the repository does not redistribute the DVCon PDFs. Users must run the scraper themselves to download papers from the official proceedings and generate their own local corpus. This keeps the project focused on open tooling and derived knowledge while respecting ownership of the original documents.

The application is also intended as a next-generation environment in which humans and AI agents work together. The central design concern is an AI-native workflow: the AI should be able to see everything the human can see, and the AI should be able to do everything the human can do. A separate chatbot that receives copied text is not enough. The agent needs access to the same papers, search results, metadata, graphs, statistics, and reading interfaces available to the engineer.

The application therefore includes an MCP control plane through which an agent can invoke skills. An agent can search for relevant DVCon papers, read the full text, inspect figures and references, compare approaches, and use the evidence in a verification workflow. In the future, the agent should also be able to read a paper and try the experiment described in it, using available tools to confirm or challenge the paper’s findings. This turns the proceedings from a passive archive into an active engineering resource.

The repository also includes a DVCon submission skill. This skill is intended to help an agent understand the submission process, organize a paper, check its structure and completeness, and support the author through revisions. The abstract submitted through this skill was authored by me, with substantial assistance from AI for grammar correction and sentence polishing. The exact workflow is still evolving, but the direction is clear: AI agents should not only retrieve prior knowledge; they should help engineers create, validate, and submit new knowledge.

Because this area is changing so quickly, much of what is written here will probably be outdated by the time the conference takes place next March. The application will likely be reimplemented several more times. The architecture, tools, and agent capabilities may all change, but the underlying goal will remain the same: make technical knowledge accessible to both humans and machines while preserving evidence and authorship.

## Conclusion

The DVCon AI Library began with a simple problem: there was no easy way to use the DVCon proceedings across many years. It became an experiment in vibe coding, AI-assisted software development, retrieval-augmented generation, structured technical knowledge, and human–agent collaboration.

The project transforms a difficult-to-search PDF archive into an open, locally deployable knowledge system. It provides hybrid search, paper-grounded chat, metadata exploration, trend analysis, an LLM-wiki, MCP services, and agent skills. More importantly, it preserves the path from generated insight back to the original papers.

I invite the DVCon community to collaborate, contribute ideas, test the tools, and improve the workflows. Contributions are especially welcome for older proceedings, particularly papers published before 2010 that are not currently downloadable through the existing archive. Recovering those papers would make the historical view much more complete and help ensure that the next generation of AI tools can learn from the full history of DVCon.

## References

[1] P. Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,” NeurIPS, 2020.

[2] J. Chen, S. Xiao, P. Zhang, et al., “BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation,” 2024.

[3] P. Lopez, “GROBID: Combining Automatic Bibliographic Data Recognition and Term Extraction for Scholarship Publications,” TPDL, 2009.

[4] Anthropic, “Model Context Protocol Specification,” 2024.

[5] SQLite Consortium, “SQLite FTS5 Full-Text Search Extension.”

[6] “DVCon AI Library.” Available: [https://github.com/hevangel/dvcon\_ai\_library](https://github.com/hevangel/dvcon_ai_library)

[7] Andrew Karpathy, “LLM-Wiki.” Available: [project URL to be added]
