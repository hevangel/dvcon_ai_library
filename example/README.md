# Example Corpus

This directory contains a checked-in sample corpus built from the 7 DVCon papers authored by Horace Chan that were downloaded during development.

Layout:

- `example/paper/`: raw PDF files using the same year/location/slug layout as the runtime `paper/` directory
- `example/data/markdown/`: extracted markdown and colocated image assets
- `example/data/tei/`: saved GROBID TEI XML outputs
- `example/data/horace_chan_manifest.json`: manifest of the included sample papers

This sample intentionally excludes the local runtime SQLite database, Chroma vector store, model cache, and other generated artifacts so the repository stays portable and reasonably small.
