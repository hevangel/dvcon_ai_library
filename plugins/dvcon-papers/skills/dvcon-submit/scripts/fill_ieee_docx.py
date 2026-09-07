#!/usr/bin/env python3
"""Fill a DVCon IEEE-template .docx from markdown.

This is the non-Windows engine used by convert_md_to_docx.sh. It implements
the same markdown -> IEEE style mapping and inline-run splitting as
convert_md_to_docx.ps1, then rewrites word/document.xml inside a style-bearing
.docx (the bundled .doc converted via LibreOffice, or a .docx --template).

Windows conversion still goes through Word COM in the .ps1; this module exists
so macOS/Linux produce the same paragraph styles, author drop, and inline
formatting instead of a plain pandoc dump.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

STYLE_IDS = {
    "IEEE Title": "IEEETitle",
    "IEEE Abstract": "IEEEAbstract",
    "IEEE Heading 1": "IEEEHeading1",
    "IEEE Heading 2": "IEEEHeading2",
    "IEEE Text": "IEEEText",
    "IEEE List": "IEEEList",
    "IEEE Reference": "IEEEReference",
}

ALIGN = {
    "IEEE Title": "center",
    "IEEE Abstract": "both",
    "IEEE Heading 1": "center",
    "IEEE Heading 2": "left",
}

AUTHOR_HEADING = re.compile(
    r"^(Authors?|Affiliations?|Author Information)$",
    re.IGNORECASE,
)

# PowerShell -match is case-insensitive; keep these flags aligned.
RE_FENCE = re.compile(r"^```")
RE_H3 = re.compile(r"^###\s+(.*)$")
RE_H2 = re.compile(r"^##\s+(.*)$")
RE_H1 = re.compile(r"^#\s+(.*)$")
RE_REF = re.compile(r"^\[\s*\d+\s*\]")
RE_QUOTE = re.compile(r"^>\s?(.*)$")
RE_BULLET = re.compile(r"^[-*+]\s+(.*)$")
RE_NUMBERED = re.compile(r"^\d+\.\s+(.*)$")

INLINE_ESCAPES = (
    ("\\\\", "\ue000"),
    ("\\*", "\ue001"),
    ("\\_", "\ue002"),
    ("\\`", "\ue003"),
    ("\\[", "\ue004"),
    ("\\]", "\ue005"),
)

# Longest marker first so ***both*** does not leak a stray asterisk.
INLINE_PATTERN = re.compile(
    r"(?P<code>`[^`]+`)"
    r"|(?P<bolditalic>\*\*\*.+?\*\*\*)"
    r"|(?P<bolditalicu>___.+?___)"
    r"|(?P<bold>\*\*.+?\*\*)"
    r"|(?P<boldu>__.+?__)"
    r"|(?P<italic>\*[^*]+?\*)"
    r"|(?P<italicu>(?<!\w)_[^_]+?_(?!\w))"
    r"|(?P<link>\[(?P<ltext>[^\]]*)\]\((?P<lurl>[^)]*)\))",
)


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    mono: bool = False


@dataclass
class Para:
    style: str
    text: str
    mono: bool = False


def get_inline_runs(
    text: str,
    bold: bool = False,
    italic: bool = False,
    depth: int = 0,
) -> list[Run]:
    if depth > 4:
        return [Run(text, bold, italic, False)]
    runs: list[Run] = []
    pos = 0
    for m in INLINE_PATTERN.finditer(text):
        if m.start() < pos:
            continue
        if m.start() > pos:
            runs.append(Run(text[pos : m.start()], bold, italic, False))
        v = m.group(0)
        if m.group("code"):
            runs.append(Run(v[1:-1], bold, italic, True))
        elif m.group("bolditalic") or m.group("bolditalicu"):
            runs.extend(get_inline_runs(v[3:-3], True, True, depth + 1))
        elif m.group("bold") or m.group("boldu"):
            runs.extend(get_inline_runs(v[2:-2], True, italic, depth + 1))
        elif m.group("italic") or m.group("italicu"):
            runs.extend(get_inline_runs(v[1:-1], bold, True, depth + 1))
        elif m.group("link") is not None:
            ltext = m.group("ltext") or ""
            lurl = m.group("lurl") or ""
            shown = ltext if ltext != "" else lurl
            if re.match(r"^\s*https?://", lurl, re.I) and lurl.lower() not in shown.lower():
                shown = f"{shown} ({lurl})"
            runs.extend(get_inline_runs(shown, bold, italic, depth + 1))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:], bold, italic, False))
    return runs


def split_inline_markdown(text: str) -> list[Run]:
    protected = text
    for src, dst in INLINE_ESCAPES:
        protected = protected.replace(src, dst)
    out: list[Run] = []
    for run in get_inline_runs(protected):
        t = run.text
        for src, dst in INLINE_ESCAPES:
            t = t.replace(dst, src[1:])
        if t != "":
            out.append(Run(t, run.bold, run.italic, run.mono))
    if not out:
        out.append(Run(""))
    return out


def parse_markdown(text: str) -> list[Para]:
    lines = text.splitlines()
    paras: list[Para] = []
    in_code = False
    skip_authors = False
    code_buf: list[str] = []
    body_buf: list[str] = []
    abs_buf: list[str] = []

    def flush_body() -> None:
        if body_buf:
            paras.append(Para("IEEE Text", " ".join(body_buf), False))
            body_buf.clear()

    def flush_abs() -> None:
        if abs_buf:
            paras.append(Para("IEEE Abstract", " ".join(abs_buf), False))
            abs_buf.clear()

    def flush_code() -> None:
        if code_buf:
            paras.append(Para("IEEE Text", "\r\n".join(code_buf), True))
            code_buf.clear()

    def flush_all() -> None:
        flush_body()
        flush_abs()
        flush_code()

    for line in lines:
        trimmed = line.strip()

        if RE_FENCE.match(trimmed or ""):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_all()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        m = RE_H3.match(trimmed)
        if m:
            flush_all()
            if not skip_authors:
                paras.append(Para("IEEE Heading 2", m.group(1).strip()))
            continue

        m = RE_H2.match(trimmed)
        if m:
            flush_all()
            h = m.group(1).strip()
            if AUTHOR_HEADING.match(h):
                skip_authors = True
                continue
            skip_authors = False
            paras.append(Para("IEEE Heading 1", h))
            continue

        m = RE_H1.match(trimmed)
        if m:
            flush_all()
            if skip_authors:
                continue
            title_used = any(p.style == "IEEE Title" for p in paras)
            sty = "IEEE Heading 1" if title_used else "IEEE Title"
            paras.append(Para(sty, m.group(1).strip()))
            continue

        if trimmed == "":
            flush_body()
            flush_abs()
            continue

        if skip_authors:
            continue

        if RE_REF.match(trimmed):
            flush_body()
            flush_abs()
            paras.append(Para("IEEE Reference", trimmed))
            continue

        m = RE_QUOTE.match(trimmed)
        if m:
            flush_body()
            abs_text = m.group(1).strip()
            if abs_text:
                abs_buf.append(abs_text)
            continue

        m = RE_BULLET.match(trimmed)
        if m:
            flush_body()
            flush_abs()
            paras.append(Para("IEEE List", m.group(1).strip()))
            continue

        m = RE_NUMBERED.match(trimmed)
        if m:
            flush_body()
            flush_abs()
            paras.append(Para("IEEE List", trimmed))
            continue

        flush_abs()
        body_buf.append(trimmed)

    flush_all()
    return paras


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wt(text: str) -> str:
    esc = _xml_escape(text)
    space = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
    return f"<w:t{space}>{esc}</w:t>"


def _run_xml(run: Run) -> str:
    rpr_parts: list[str] = []
    if run.mono:
        rpr_parts.append(
            '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Consolas"/>'
        )
    if run.bold:
        rpr_parts.append("<w:b/>")
    if run.italic:
        rpr_parts.append("<w:i/>")
    rpr = f"<w:rPr>{''.join(rpr_parts)}</w:rPr>" if rpr_parts else ""
    chunks: list[str] = []
    parts = re.split(r"\r\n|\n|\r", run.text)
    for i, part in enumerate(parts):
        if i:
            chunks.append("<w:br/>")
        chunks.append(_wt(part))
    return f"<w:r>{rpr}{''.join(chunks)}</w:r>"


def _para_xml(para: Para) -> str:
    style_id = STYLE_IDS.get(para.style, "IEEEText")
    jc = ALIGN.get(para.style, "both")
    ppr = (
        "<w:pPr>"
        f'<w:pStyle w:val="{style_id}"/>'
        f'<w:jc w:val="{jc}"/>'
        "</w:pPr>"
    )
    if para.mono:
        body = _run_xml(Run(para.text, False, False, True))
    else:
        body = "".join(_run_xml(r) for r in split_inline_markdown(para.text) if r.text != "")
    return f"<w:p>{ppr}{body}</w:p>"


def render_body(paras: Iterable[Para], sect_pr: bytes) -> bytes:
    inner = "".join(_para_xml(p) for p in paras).encode("utf-8")
    return b"<w:body>" + inner + sect_pr + b"</w:body>"


def fill_docx(template_docx: Path, output_docx: Path, paras: list[Para]) -> None:
    if not paras:
        raise SystemExit(f"No content parsed from markdown")
    with zipfile.ZipFile(template_docx) as zin:
        document = zin.read("word/document.xml")
        names = zin.namelist()
        infos = {info.filename: info for info in zin.infolist()}
        files = {name: zin.read(name) for name in names}

    sect = b""
    m = re.search(rb"<w:sectPr[\s\S]*?</w:sectPr>", document)
    if m:
        sect = m.group(0)
    if not re.search(rb"<w:body[\s\S]*?</w:body>", document):
        raise SystemExit("template docx has no w:body")
    document = re.sub(
        rb"<w:body[\s\S]*?</w:body>",
        render_body(paras, sect),
        document,
        count=1,
    )
    files["word/document.xml"] = document

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_docx, "w") as zout:
        for name in names:
            info = infos[name]
            zout.writestr(info, files[name])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--docx", required=True)
    parser.add_argument(
        "--template-docx",
        required=True,
        help="A .docx that already contains the IEEE named styles (usually the "
        "bundled .doc after LibreOffice --convert-to docx).",
    )
    args = parser.parse_args(argv)

    md_path = Path(args.markdown)
    template = Path(args.template_docx)
    out = Path(args.docx)
    if not md_path.is_file():
        print(f"Error: markdown input not found: {md_path}", file=sys.stderr)
        return 1
    if not template.is_file():
        print(f"Error: template docx not found: {template}", file=sys.stderr)
        return 1

    paras = parse_markdown(md_path.read_text(encoding="utf-8"))
    fill_docx(template, out, paras)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
