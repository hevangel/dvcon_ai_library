"""Build llm-wiki/index.md from _topics.json + stats from the written .md files.

Run after all 50 pages are written:
    docs/.venv/Scripts/python.exe llm-wiki/build_index.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WIKI_DIR = Path(__file__).resolve().parent
TOPICS = json.loads((WIKI_DIR / "_topics.json").read_text(encoding="utf-8"))

# group by category (preserve manifest order within category)
by_cat: dict[str, list[dict]] = {}
for t in TOPICS:
    by_cat.setdefault(t["category"], []).append(t)

# stats from written pages
total_words = 0
total_citations = 0
written = 0
missing: list[str] = []
for t in TOPICS:
    p = WIKI_DIR / f"{t['slug']}.md"
    if not p.exists():
        missing.append(t["slug"])
        continue
    written += 1
    text = p.read_text(encoding="utf-8")
    total_words += len(text.split())
    # count "Grounded in" entries (lines starting with "- **")
    m = re.search(r"## Grounded in these DVCon papers\s+(.*?)(?=\n---|\Z)", text, re.DOTALL)
    if m:
        total_citations += len(re.findall(r"^-\s+\*\*", m.group(1), re.MULTILINE))

lines: list[str] = []
lines.append("# DVCon LLM Wiki")
lines.append("")
lines.append("> *A synthesized wiki of EDA / functional-verification knowledge, "
             "built from the 1,852-paper DVCon corpus (2010–2026). Every page "
             "opens with a Karpathy-style hook, drops into neutral reference "
             "prose, and cites 8–15 real DVCon papers so every claim is "
             "traceable to the source.*")
lines.append("")
lines.append(f"**{written} of {len(TOPICS)} pages written** · "
             f"~{total_words:,} words total · "
             f"{total_citations} paper citations across the wiki.")
if missing:
    lines.append(f"\n> ⚠️ {len(missing)} pages still missing: {', '.join(missing)}\n")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## Table of contents")
lines.append("")
for cat, items in by_cat.items():
    lines.append(f"### {cat} ({len(items)} pages)")
    lines.append("")
    for t in items:
        # link + blurb on one line; flag missing pages
        suffix = " *(not yet written)*" if t["slug"] in missing else ""
        lines.append(f"- **[{t['title']}]({t['slug']}.md)** — {t['blurb']}{suffix}")
    lines.append("")

lines.append("---")
lines.append("")
lines.append("## How this wiki was built")
lines.append("")
lines.append("1. **Source extraction** (`build_sources.py`): for each of the 50 topics, "
             "the script queries `data/dvcon.db` and picks the 8–15 most relevant "
             "DVCon papers + 5–10 most relevant chunks + 8 most-cited references. "
             "Result: one JSON file per topic under `_sources/`.")
lines.append("2. **Page synthesis**: an LLM agent (GLM-5.2) reads each source JSON "
             "and writes a markdown page in two voices — a Karpathy-style "
             "motivational hook, then neutral reference prose with inline citations.")
lines.append("3. **Cross-linking**: every page links to 3–6 related pages via the "
             "`see_also` slugs in `_topics.json`. The index you're reading is "
             "generated from that same manifest.")
lines.append("")
lines.append("See [`README.md`](README.md) for regeneration instructions.")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## Methodology notes")
lines.append("")
lines.append("- **No external sources.** Every claim is grounded in a real DVCon paper. "
             "If a page mentions IEEE 1800 or UPF, it's because DVCon papers cite those "
             "standards — not because the wiki authors looked them up independently.")
lines.append("- **Citation format.** Inline citations look like `[Paper Title, 2018]` "
             "and the full reference appears in the page's \"Grounded in these DVCon "
             "papers\" section.")
lines.append("- **Voice.** The hook is first-person and motivational (Karpathy-style). "
             "The body is neutral and reference-like. The two voices are deliberately "
             "different — the hook pulls you in, the body teaches you.")
lines.append("- **Coverage.** The 50 topics span the full DVCon domain: foundations "
             "(SystemVerilog, UVM, UPF, SystemC), UVM deep dives, formal verification, "
             "coverage, AI/ML for verification, domain-specific topics (CDC, RDC, "
             "low-power, AMS, RISC-V, security), and emerging themes (PSS, chiplets, "
             "LLMs for verification, the future of the field).")
lines.append("- **Gaps.** Some topics have thinner source material than others "
             "(e.g. UVM callbacks had only 6 papers in the corpus). Those pages are "
             "necessarily shorter and rely more heavily on the smaller set of sources.")
lines.append("")
lines.append(f"*Last regenerated: 50 pages, ~{total_words:,} words, "
             f"{total_citations} citations. Run `docs/.venv/Scripts/python.exe "
             f"llm-wiki/build_index.py` to refresh this index.*")

(WIKI_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote index.md: {written}/{len(TOPICS)} pages, "
      f"{total_words:,} words, {total_citations} citations.")
if missing:
    print(f"Missing: {missing}")
