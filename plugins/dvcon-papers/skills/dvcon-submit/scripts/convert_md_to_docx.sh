#!/usr/bin/env bash
# Convert a DVCon paper written in Markdown into a .docx (and optionally .pdf)
# that matches the IEEE-style DVCon abstract template.
#
# This is the bash twin of convert_md_to_docx.ps1. The .ps1 does the real work
# by driving MS Word via COM (Windows-only). On Windows this script delegates to
# the .ps1; on other platforms it falls back to a pandoc + LibreOffice path.
#
# Usage:
#   convert_md_to_docx.sh \
#       --markdown /path/to/paper.md \
#       --docx     /path/to/paper.docx \
#       [--pdf     /path/to/paper.pdf] \
#       [--template /path/to/template.doc]
#
#   --markdown  (required) input .md file
#   --docx      (required) output .docx path
#   --pdf       (optional) also export a .pdf to this path
#   --template  (optional) override the bundled template .doc
#
# Exit codes:
#   0  success
#   1  bad arguments / missing input
#   2  no usable conversion backend found
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TEMPLATE="$SCRIPT_DIR/../references/dvcon_abstract_template.doc"
PS1_SCRIPT="$SCRIPT_DIR/convert_md_to_docx.ps1"

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

    MAP="$(find_powershell)"
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

# --- Non-Windows path: pandoc + LibreOffice -------------------------------
#
# pandoc builds the .docx using the bundled template as a reference doc so the
# IEEE named styles are inherited, then LibreOffice exports the PDF. Neither is
# installed on the current Windows host, but this branch lets the script run on
# macOS / Linux boxes that have them.

need_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: '$1' not found on PATH." >&2
        echo "       On this platform the bash wrapper needs pandoc + libreoffice" >&2
        echo "       to build the .docx/.pdf (the .ps1 path is Windows-only)." >&2
        echo "       Install pandoc (https://pandoc.org) and libreoffice" >&2
        echo "       ('soffice' / 'libreoffice'), then re-run." >&2
        return 1
    fi
}

# pandoc can use a .docx as --reference-doc only if it is the .docx format; the
# bundled template is a legacy .doc. If the user passed a .docx template or has
# converted the bundled one, use it; otherwise warn and build a plain .docx.
build_docx_with_pandoc() {
    local tpl="$1"
    if [[ "$tpl" == *.docx ]]; then
        pandoc "$MARKDOWN" -o "$DOCX" --reference-doc="$tpl"
    else
        echo "Note: bundled template is a legacy .doc; pandoc needs .docx for" >&2
        echo "      --reference-doc. Building a plain .docx without the IEEE" >&2
        echo "      styles. For template-styled output on Windows, use the .ps1." >&2
        pandoc "$MARKDOWN" -o "$DOCX"
    fi
}

need_tool pandoc
build_docx_with_pandoc "$TEMPLATE"
echo "WROTE $DOCX"

if [[ -n "$PDF" ]]; then
    need_tool soffice 2>/dev/null || need_tool libreoffice
    SOFFICE="$(command -v soffice || command -v libreoffice)"
    # Run headless; output dir is the PDF's parent, then rename to the target.
    pdf_dir="$(dirname "$PDF")"
    "$SOFFICE" --headless --convert-to pdf --outdir "$pdf_dir" "$DOCX" >&2
    # soffice names the output <docx-basename>.pdf; rename if different.
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
fi
