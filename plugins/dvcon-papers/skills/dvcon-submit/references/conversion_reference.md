# DVCon Markdown → PDF Conversion Reference

Source of truth for converting a DVCon paper written in Markdown into a
template-compliant `.docx` and `.pdf` via MS Word COM. Covers the helper script,
the IEEE named styles the template defines, the markdown→style mapping, and
troubleshooting.

> The bundled template (`references/dvcon_abstract_template.doc`) is the IEEE
> single-column, single-spaced template DVCon ships for abstract submissions.
> It was captured from
> `https://confcats-siteplex.s3.amazonaws.com/dvconus/files/ieee_template_dv_con_us_2024_abstract_submission_1.doc`
> (linked from the dvcon.org instructions page). A read-only PDF rendering
> (`references/dvcon_abstract_template.pdf`) is included for visual reference.

## Why MS Word COM (not pandoc/LibreOffice)

This machine has **MS Word 16.0** installed but **no pandoc and no
LibreOffice/soffice**. Word COM is therefore the reliable local conversion path
and has two big advantages:

1. The bundled `.doc` template **defines named IEEE paragraph styles** (IEEE
   Title, IEEE Abstract, IEEE Heading 1/2, IEEE Text, IEEE List, IEEE Reference,
   etc.) plus the US Letter page setup and margins. Filling those styles
   automatically produces a correctly-formatted document — no need to re-derive
   fonts, sizes, or spacing.
2. Word's `ExportAsFixedFormat` produces a PDF with the fonts actually used in
   the document embedded, satisfying the dvcon.org "embed all fonts" rule.

If Word is unavailable on a future machine, fall back to the `docx` skill's
docx-js + LibreOffice path (requires installing LibreOffice), or open the
generated `.docx` in Word/GDocs and export manually.

## The helper scripts

Two interchangeable scripts are shipped. They take the same arguments (the bash
version uses `--flag` style) and produce the same output.

`scripts/convert_md_to_docx.ps1` — the PowerShell implementation. It:

1. Parses the markdown into a list of `(style, text)` tuples (see mapping below).
2. Opens the bundled template via Word COM.
3. Clears the body (keeping the style + section definitions).
4. Re-emits each parsed paragraph using `Selection`-based typing, applying the
   named IEEE style and alignment per paragraph.
5. Saves the `.docx` (`wdFormatXMLDocument` = 16).
6. Optionally exports a `.pdf` via `ExportAsFixedFormat`.

`scripts/convert_md_to_docx.sh` — the bash twin. On Windows (Git Bash / MSYS /
Cygwin) it auto-detects `pwsh`/`powershell.exe`, converts paths to Windows form
with `cygpath -w`, and delegates to the `.ps1` so the output is byte-for-byte
the same. On macOS / Linux it falls back to a `pandoc` + `libreoffice` path
(`pandoc` builds the `.docx`, `soffice --convert-to pdf` exports the PDF).

### Invocation

PowerShell (Windows native):

```powershell
powershell -ExecutionPolicy Bypass -File "<skill_dir>/scripts/convert_md_to_docx.ps1" `
  -Markdown C:\papers\mine.md `
  -Docx     C:\papers\mine.docx `
  -Pdf      C:\papers\mine.pdf        # optional; omit to produce .docx only
  # -Template C:\path\to\other.doc    # optional; defaults to the bundled template
```

Bash (Windows Git Bash, macOS, Linux):

```bash
"<skill_dir>/scripts/convert_md_to_docx.sh" \
  --markdown /path/to/paper.md \
  --docx     /path/to/paper.docx \
  --pdf      /path/to/paper.pdf      # optional; omit to produce .docx only
  # --template /path/to/other.doc    # optional; defaults to the bundled template
```

All paths should be absolute. Both scripts remove any pre-existing output files
before writing, so re-runs are safe.

### Requirements

- **PowerShell path** (`convert_md_to_docx.ps1`, or the `.sh` on Windows):
  - **MS Word installed** (drives Word via COM; verified Word 16.0 on this host).
  - PowerShell (Windows PowerShell 5+ or PowerShell 7).
- **Bash path on macOS / Linux** (`convert_md_to_docx.sh`): `pandoc` and
  `libreoffice` (`soffice`) on PATH. Note: `pandoc`'s `--reference-doc` needs a
  `.docx` template; the bundled template is a legacy `.doc`, so on non-Windows
  the bash wrapper builds a plain `.docx` without the IEEE styles unless you
  pass a `.docx` template via `--template`. For full template styling, run on
  Windows (either script — the `.sh` delegates to the `.ps1`).
- The bundled template at `references/dvcon_abstract_template.doc` (shipped with
  the skill). Override with `-Template` / `--template` if you have a newer one.

## IEEE named styles in the template

These are the named paragraph styles the template defines (captured by querying
the template's `Styles` collection via COM). Target these names exactly.

| Style name | Default look | Used for |
|------------|--------------|----------|
| `IEEE Title` | 25pt, centered, Times New Roman | The paper title (first `# H1`) |
| `IEEE Abstract` | 9pt, bold, justified | The abstract (first `>` blockquote block) |
| `IEEE Heading 1` | 10pt, centered | Top-level sections (`## H2`) — Roman numerals |
| `IEEE Heading 2` | 10pt, italic, left | Subsections (`### H3`) — capital letters |
| `IEEE Text` | 10pt, justified, Times New Roman | Body paragraphs |
| `IEEE List` | 10pt, justified | Bullet/numbered list items |
| `IEEE Reference` | (template-defined) | `[n] ...` reference entries |
| `IEEE Caption` | (template-defined) | Figure/table captions |
| `IEEE Table Number` | 8pt, centered | `TABLE N` line |
| `IEEE Table Title` | 8pt, centered | Table title line |
| `IEEE Author` | (template-defined) | Author names — **NOT emitted** (double-blind) |
| `IEEE Affiliation` | (template-defined) | Affiliations — **NOT emitted** (double-blind) |
| `IEEE Equation` | (template-defined) | Display equations |

The script does NOT emit `IEEE Author` / `IEEE Affiliation` — the abstract is
double-blind. For the full-paper stage, see the caveat in `SKILL.md`.

## Markdown → IEEE style mapping

The parser honors these rules:

| Markdown construct | Mapped to | Notes |
|--------------------|-----------|-------|
| First `# H1` | `IEEE Title` | Only the **first** H1 becomes the title. Subsequent H1s fall back to `IEEE Heading 1`. |
| Subsequent `# H1` | `IEEE Heading 1` | |
| `## H2` | `IEEE Heading 1` | Roman-numeral section. |
| `### H3` | `IEEE Heading 2` | Lettered subsection. |
| `>` blockquote (first contiguous block) | `IEEE Abstract` | Multi-line blockquotes are joined with spaces into one abstract paragraph. |
| `## Authors` / `## Affiliations` / `## Author Information` | **DROPPED** | Double-blind compliance. The drop persists until the next `##` heading. |
| `- `, `* `, `+ ` bullets | `IEEE List` | Each bullet = its own paragraph. |
| `1. ` numbered items | `IEEE List` | Each item = its own paragraph (number kept). |
| ` ``` ` fenced code block | `IEEE Text` (monospace) | Preserved verbatim with line breaks; font switched to Consolas. Good for ASCII diagrams. |
| `[n] ...` reference lines | `IEEE Reference` | A line beginning with `[<digits>]`. |
| Plain body paragraph | `IEEE Text` | Consecutive non-blank lines are **joined with a single space** (CommonMark soft-wrap). |
| Blank line | paragraph break | Ends the current body/abstract paragraph. Does NOT exit the Authors drop. |

### Example input → output

Input (excerpt):

```markdown
# A Coverage-Driven UVM Methodology for RISC-V Vector Verification

> This extended abstract proposes a coverage-driven verification methodology
> targeting the RISC-V vector extension.

## Introduction

Modern RISC-V vector implementations present unique verification challenges due
to the combinatorial space of `vsetvli` configurations.

## Authors

- Jane Doe, Example Corp
```

Output paragraphs (style | text):

```
IEEE Title     | A Coverage-Driven UVM Methodology for RISC-V Vector Verification
IEEE Abstract  | This extended abstract proposes a coverage-driven verification methodology targeting the RISC-V vector extension.
IEEE Heading 1 | Introduction
IEEE Text      | Modern RISC-V vector implementations present unique verification challenges due to the combinatorial space of `vsetvli` configurations.
(Authors section dropped — Jane Doe does NOT appear in the output)
```

Note the two wrapping body lines became ONE `IEEE Text` paragraph, and the
`## Authors` block was removed entirely.

## Verifying the output before submission

After running the script:

1. **Word count.** Open the `.docx` (or count words in the markdown body,
   excluding the reference list and any code blocks). For the abstract stage the
   body must be **600–1200 words**. For the full paper, **6–8 pages**.
2. **Double-blind check (abstract stage).** The converter drops `## Authors`
   sections, but the body prose may still self-identify. Grep the markdown for
   company names, "we at ...", author first names, GitHub handles, or
   acknowledgements — and warn the user to scrub them.
3. **PDF integrity.** Open the `.pdf`; confirm it is US Letter, fonts are
   embedded (Word's `ExportAsFixedFormat` embeds used fonts), no page numbers,
   no security settings, and file size ≤ 5 MB.
4. **Visual spot-check** against `references/dvcon_abstract_template.pdf` to
   confirm the title/heading/body styling matches.

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `Word COM` error / "read-only" on save | Another Word instance holds the file, or MS Word is not installed. The script removes pre-existing outputs before writing; close any open Word windows holding the target. |
| `$PSScriptRoot` empty / template not found | The script falls back to `$MyInvocation.MyCommand.Path`. If that also fails, pass `-Template <absolute path>` explicitly. |
| Every input line becomes its own paragraph | Older script bug; the current version joins soft-wrapped body lines. Re-pull the script if edited. |
| ASCII diagram collapsed to one line | Fenced code blocks (```` ``` ````) are preserved verbatim — wrap your diagram in a code fence, not as plain text. |
| Author names leaked into abstract PDF | The drop list is `Authors`/`Affiliations`/`Author Information` (exact match on the heading text). Rename the section OR scrub the body prose. |
| Backticks render literally (`vsetvli`) | Intentional — the template has no inline-code style. For a cleaner look, the user can find/replace backticks in Word before export. |
| PDF missing fonts | Word's `ExportAsFixedFormat` embeds used fonts by default; if a font is missing on the system it falls back. Ensure Times New Roman is installed (it ships with Windows/Word). |
| Want A4 instead of US Letter | Edit the template's page setup in Word once, save, and reuse. DVCon **requires US Letter** — do not change this for actual submissions. |
