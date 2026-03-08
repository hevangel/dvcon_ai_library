# Sample Corpus

This directory contains a checked-in sample corpus built from the 8 DVCon papers authored by Horace Chan that were downloaded during development, including the 2022 paper "Is it a software bug? Is it a hardware bug?".

Layout:

- `paper/`: sample PDF files using the same year/location/slug layout as the runtime `data/paper/` directory
- `markdown/`: extracted markdown and colocated image assets
- `tei/`: saved GROBID TEI XML outputs
- `horace_chan_manifest.json`: manifest of the included sample papers, with paths relative to `data.example/`

This sample intentionally excludes the local runtime SQLite database, Chroma vector store, model cache, and other generated artifacts so the repository stays portable and reasonably small.
