#!/usr/bin/env bash
# Convert a DVCon paper written in Markdown into a .docx (and optionally .pdf)
# that matches the IEEE-style DVCon abstract template.
#
# This is the bash twin of convert_md_to_docx.ps1. Both scripts honor the same
# markdown -> IEEE style mapping, author-section drop, and inline-run splitting
# (**bold**, *italic*, `code`, [label](url)).
#
# On Windows this script delegates to the .ps1 (MS Word COM). On macOS / Linux
# it converts the bundled .doc template to .docx with LibreOffice, then
# fill_ieee_docx.py (stdlib) rewrites the body using the template's named IEEE
# styles — the same strategy as Word COM, without pandoc.
#
# Usage:
#   convert_md_to_docx.sh \
#       --markdown /path/to/paper.md \
#       --docx     /path/to/paper.docx \
#       [--pdf     /path/to/paper.pdf] \
#       [--template /path/to/template.doc]
#
# Exit codes:
#   0  success
#   1  bad arguments / missing input
#   2  no usable conversion backend found
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TEMPLATE="$SCRIPT_DIR/../references/dvcon_abstract_template.doc"
PS1_SCRIPT="$SCRIPT_DIR/convert_md_to_docx.ps1"
FILL_SCRIPT="$SCRIPT_DIR/fill_ieee_docx.py"

MARKDOWN=""
DOCX=""
PDF=""
TEMPLATE="$DEFAULT_TEMPLATE"

usage() {
    cat <<EOF
Usage: $0 --markdown <file.md> --docx <file.docx> [--pdf <file.pdf>] [--template <file.doc>]

  --markdown   (required) input markdown file
  --docx       (required) output .docx file
  --pdf        (optional) also export a .pdf to this path
  --template   (optional) override the bundled DVCon IEEE template .doc
  -h, --help   show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --markdown) MARKDOWN="$2"; shift 2 ;;
        --docx)     DOCX="$2";     shift 2 ;;
        --pdf)      PDF="$2";      shift 2 ;;
        --template) TEMPLATE="$2"; shift 2 ;;
        -h|--help)  usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$MARKDOWN" || -z "$DOCX" ]]; then
    echo "Error: --markdown and --docx are required." >&2
    usage >&2
    exit 1
fi
if [[ ! -f "$MARKDOWN" ]]; then
    echo "Error: markdown input not found: $MARKDOWN" >&2
    exit 1
fi
if [[ ! -f "$TEMPLATE" ]]; then
    echo "Error: template not found: $TEMPLATE" >&2
    exit 1
fi

# Ensure outputs' parent dirs exist and clear any pre-existing output files
# (mirrors the .ps1 behavior, avoids Word/soffice read-only / lock errors).
for out in "$DOCX" "$PDF"; do
    [[ -z "$out" ]] && continue
    mkdir -p "$(dirname "$out")"
    rm -f "$out"
done

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

# Detect Windows so we can delegate to the .ps1 (Word COM). Git Bash / MSYS /
# Cygwin expose cygpath; native Windows PowerShell is on PATH as powershell.exe.
is_windows() {
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*|*Windows*) return 0 ;;
        *) return 1 ;;
    esac
}

# Convert a POSIX path to a Windows path when running under Git Bash / Cygwin.
# Falls through unchanged on systems without cygpath.
to_native_path() {
    local p="$1"
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$p"
    else
        printf '%s' "$p"
    fi
}

find_powershell() {
    if command -v pwsh >/dev/null 2>&1; then       printf 'pwsh'
    elif command -v powershell.exe >/dev/null 2>&1; then printf 'powershell.exe'
    elif command -v powershell >/dev/null 2>&1; then printf 'powershell'
    else return 1
    fi
}

if is_windows; then
    # --- Windows path: delegate to the .ps1 (drives MS Word via COM) --------
    if [[ ! -f "$PS1_SCRIPT" ]]; then
        echo "Error: $PS1_SCRIPT not found next to this script." >&2
        exit 2
    fi
    if ! PWSH="$(find_powershell)"; then
        echo "Error: PowerShell not found on PATH; it ships with Windows." >&2
        exit 2
    fi

    # Hand Windows-native paths to the .ps1 so Word COM resolves them.
    args=( -ExecutionPolicy Bypass -NoProfile -File "$(to_native_path "$PS1_SCRIPT")" )
    args+=( -Markdown "$(to_native_path "$MARKDOWN")" )
    args+=( -Docx     "$(to_native_path "$DOCX")" )
    args+=( -Template "$(to_native_path "$TEMPLATE")" )
    if [[ -n "$PDF" ]]; then
        args+=( -Pdf "$(to_native_path "$PDF")" )
    fi

    "$PWSH" "${args[@]}"
    exit $?
fi

# --- Non-Windows path: LibreOffice template + fill_ieee_docx.py ------------
#
# Same mapping as the .ps1: parse markdown into IEEE-styled paragraphs (drop
# Authors sections, split inline runs), stamp them into a copy of the template
# that already carries the named styles + US Letter page setup, then optionally
# export PDF. LibreOffice is used only to (1) turn the bundled legacy .doc into
# a .docx the zip writer can edit, and (2) export PDF. pandoc is not used —
# it cannot target the template's IEEE style names.

need_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: '$1' not found on PATH." >&2
        echo "       On this platform the bash wrapper needs python3 + libreoffice" >&2
        echo "       (the .ps1 path is Windows-only)." >&2
        echo "       Install Python 3 and LibreOffice ('soffice' / 'libreoffice')," >&2
        echo "       then re-run." >&2
        return 1
    fi
}

find_python() {
    if command -v python3 >/dev/null 2>&1; then printf 'python3'
    elif command -v python >/dev/null 2>&1; then printf 'python'
    else return 1
    fi
}

find_soffice() {
    if command -v soffice >/dev/null 2>&1; then printf 'soffice'
    elif command -v libreoffice >/dev/null 2>&1; then printf 'libreoffice'
    else return 1
    fi
}

if [[ ! -f "$FILL_SCRIPT" ]]; then
    echo "Error: $FILL_SCRIPT not found next to this script." >&2
    exit 2
fi
if ! PYTHON="$(find_python)"; then
    echo "Error: python3 not found on PATH." >&2
    echo "       The non-Windows converter needs Python 3 (stdlib only)." >&2
    exit 2
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/dvcon-md2docx.XXXXXX")"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

# A .docx template already has the IEEE styles in OOXML form. A .doc must be
# converted first so fill_ieee_docx.py can rewrite word/document.xml.
TEMPLATE_DOCX=""
case "$TEMPLATE" in
    *.docx|*.DOCX)
        TEMPLATE_DOCX="$TEMPLATE"
        ;;
    *)
        if ! SOFFICE="$(find_soffice)"; then
            echo "Error: LibreOffice not found on PATH (needed to convert the" >&2
            echo "       bundled .doc template to .docx). Pass a .docx via" >&2
            echo "       --template to skip this step." >&2
            exit 2
        fi
        "$SOFFICE" --headless --convert-to docx --outdir "$WORKDIR" "$TEMPLATE" >&2
        converted="$WORKDIR/$(basename "${TEMPLATE%.*}").docx"
        if [[ ! -f "$converted" ]]; then
            # soffice sometimes keeps the original basename when converting .doc
            converted="$(find "$WORKDIR" -maxdepth 1 -name '*.docx' | head -n 1)"
        fi
        if [[ -z "$converted" || ! -f "$converted" ]]; then
            echo "Error: LibreOffice did not produce a .docx from $TEMPLATE" >&2
            exit 1
        fi
        TEMPLATE_DOCX="$converted"
        ;;
esac

"$PYTHON" "$FILL_SCRIPT" \
    --markdown "$MARKDOWN" \
    --template-docx "$TEMPLATE_DOCX" \
    --docx "$DOCX"

if [[ -z "$PDF" ]]; then
    echo "WROTE $DOCX"
    exit 0
fi

if ! SOFFICE="$(find_soffice)"; then
    echo "Error: LibreOffice not found on PATH (needed for PDF export)." >&2
    exit 2
fi
pdf_dir="$(dirname "$PDF")"
"$SOFFICE" --headless --convert-to pdf --outdir "$pdf_dir" "$DOCX" >&2
generated="$pdf_dir/$(basename "${DOCX%.docx}.pdf")"
if [[ "$generated" != "$PDF" ]]; then
    mv -f "$generated" "$PDF"
fi
if [[ ! -f "$PDF" ]]; then
    echo "Error: PDF export did not produce $PDF" >&2
    exit 1
fi
bytes=$(wc -c < "$PDF" | tr -d ' ')
echo "WROTE $DOCX and $PDF ($bytes bytes)"
