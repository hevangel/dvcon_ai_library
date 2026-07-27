<#
.SYNOPSIS
  Convert a DVCon paper written in Markdown into a .docx (and optionally .pdf)
  that matches the IEEE-style DVCon abstract template, by filling the
  template's named IEEE styles via Word COM.

.DESCRIPTION
  The DVCon U.S. abstract template (references/dvcon_abstract_template.doc)
  is a single-column, single-spaced IEEE-style Word template. It defines a set
  of named paragraph styles (IEEE Title, IEEE Abstract, IEEE Heading 1/2,
  IEEE Text, IEEE List, IEEE Reference, IEEE Caption, IEEE Table Number,
  IEEE Table Title, IEEE Author, IEEE Affiliation, IEEE Equation). This script
  opens the template, clears the body, and re-emits the markdown content using
  those named styles so the output inherits the correct fonts, sizes, spacing,
  margins, and paper size automatically.

  Markdown mapping:
    # H1 / first heading     -> IEEE Title (only the FIRST H1 becomes the title)
    > abstract blockquote    -> IEEE Abstract (the first contiguous blockquote)
    ## H2                    -> IEEE Heading 1 (Roman-numeral section)
    ### H3                   -> IEEE Heading 2 (lettered subsection)
    - / * list items         -> IEEE List
    ```code blocks```        -> IEEE Text (monospace via inline style tweak)
    [n] reference lines      -> IEEE Reference (a paragraph starting with "[" )
    plain paragraphs         -> IEEE Text
    blank lines              -> paragraph break

  Double-blind rule: DVCon abstracts must NOT contain author names or
  affiliations. This script does NOT emit IEEE Author / IEEE Affiliation
  paragraphs. If the markdown contains an "## Authors" section it is skipped
  from the abstract output.

.PARAMETER Markdown
  Absolute path to the input .md file.

.PARAMETER Docx
  Absolute path to the output .docx file (will be created/overwritten).

.PARAMETER Pdf
  Optional: also export a .pdf to this path. Uses Word's ExportAsFixedFormat.

.PARAMETER Template
  Optional: override the template .doc path. Defaults to the skill's bundled
  references/dvcon_abstract_template.doc.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File convert_md_to_docx.ps1 `
    -Markdown C:\papers\mine.md `
    -Docx C:\papers\mine.docx `
    -Pdf C:\papers\mine.pdf
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Markdown,
  [Parameter(Mandatory = $true)][string]$Docx,
  [string]$Pdf,
  [string]$Template
)

$ErrorActionPreference = 'Stop'

# Default template path: <this script's dir>/../references/dvcon_abstract_template.doc
if (-not $Template) {
  $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  if (-not $scriptDir) { $scriptDir = $PSScriptRoot }
  if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
  $Template = Join-Path $scriptDir '..\references\dvcon_abstract_template.doc'
}

foreach ($p in @($Markdown, $Template)) {
  if (-not (Test-Path -LiteralPath $p)) { throw "Input not found: $p" }
}
$Markdown = (Resolve-Path -LiteralPath $Markdown).Path
$Template = (Resolve-Path -LiteralPath $Template).Path
$outDir = Split-Path -Parent $Docx
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
# Remove any pre-existing output so Word can write fresh (avoid read-only / lock errors).
foreach ($out in @($Docx, $Pdf)) {
  if ($out -and (Test-Path -LiteralPath $out)) {
    Remove-Item -LiteralPath $out -Force -ErrorAction SilentlyContinue
  }
}

# --- Parse markdown into a list of (style, text) tuples ---------------------
# Markdown rules we honor:
#   * A blank line ends a paragraph. Consecutive non-blank body lines are JOINED
#     with a single space (standard CommonMark soft-wrapping).
#   * The FIRST `# H1` becomes the IEEE Title.
#   * A contiguous blockquote (`> ...`) block becomes the IEEE Abstract.
#   * `## Authors` / `## Affiliations` / `## Author Information` sections are
#     DROPPED entirely (double-blind). The drop persists until the next `##`
#     heading that is not itself an author heading.
#   * A fenced ``` block is kept verbatim (newlines preserved) and rendered as
#     IEEE Text with a monospace font tweak, so ASCII diagrams survive.
#   * `[n] ...` reference lines become IEEE Reference paragraphs.
$lines = Get-Content -LiteralPath $Markdown -Encoding UTF8
$paras = New-Object System.Collections.Generic.List[object]
$inCode = $false
$codeBuf = New-Object System.Collections.Generic.List[string]
$skipAuthors = $false       # true while inside an Authors/Affiliations section
$bodyBuf = New-Object System.Collections.Generic.List[string]
$absBuf = New-Object System.Collections.Generic.List[string]

function Flush-Body {
  if ($script:bodyBuf.Count -gt 0) {
    $joined = ($script:bodyBuf -join ' ')
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Text'; Text = $joined; Mono = $false })
    $script:bodyBuf.Clear()
  }
}
function Flush-Abs {
  if ($script:absBuf.Count -gt 0) {
    $joined = ($script:absBuf -join ' ')
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Abstract'; Text = $joined; Mono = $false })
    $script:absBuf.Clear()
  }
}
function Flush-Code {
  if ($script:codeBuf.Count -gt 0) {
    $joined = ($script:codeBuf -join "`r`n")
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Text'; Text = $joined; Mono = $true })
    $script:codeBuf.Clear()
  }
}
function Flush-All { Flush-Body; Flush-Abs; Flush-Code }

for ($i = 0; $i -lt $lines.Count; $i++) {
  $line = $lines[$i]
  $trim = "$line".TrimEnd()
  $trimmed = "$line".Trim()

  # Fenced code block toggling (highest priority, even inside author-skip)
  if ($trimmed -match '^```') {
    if ($inCode) { Flush-Code; $inCode = $false } else { Flush-All; $inCode = $true }
    continue
  }
  if ($inCode) { $script:codeBuf.Add($line); continue }

  # Headings flush any in-progress paragraph/abstract.
  if ($trimmed -match '^###\s+(.*)$') {
    Flush-All
    if ($skipAuthors) { continue }
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Heading 2'; Text = $Matches[1].Trim(); Mono = $false })
    continue
  }
  if ($trimmed -match '^##\s+(.*)$') {
    Flush-All
    $h = $Matches[1].Trim()
    if ($h -match '^(Authors?|Affiliations?|Author Information)$') {
      # Enter author-skip mode: drop this heading and everything until the next H2.
      $script:skipAuthors = $true
      continue
    }
    # Any other H2 exits author-skip mode and is emitted normally.
    $script:skipAuthors = $false
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Heading 1'; Text = $h; Mono = $false })
    continue
  }
  if ($trimmed -match '^#\s+(.*)$') {
    Flush-All
    if ($skipAuthors) { continue }
    $titleUsed = $false
    foreach ($existing in $script:paras) { if ($existing.Style -eq 'IEEE Title') { $titleUsed = $true; break } }
    $sty = if ($titleUsed) { 'IEEE Heading 1' } else { 'IEEE Title' }
    $script:paras.Add([pscustomobject]@{ Style = $sty; Text = $Matches[1].Trim(); Mono = $false })
    continue
  }

  # Blank line = paragraph separator
  if ($trimmed -eq '') {
    Flush-Body
    Flush-Abs
    # Do NOT exit skipAuthors on blank lines — only a new H2 exits it.
    continue
  }

  # While inside an author/affiliation section, drop everything.
  if ($skipAuthors) { continue }

  # Reference paragraph: a line beginning with [n] / [N]
  if ($trimmed -match '^\[\s*\d+\s*\]') {
    Flush-Body
    Flush-Abs
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE Reference'; Text = $trimmed; Mono = $false })
    continue
  }
  # Blockquote -> accumulate into the abstract buffer
  if ($trimmed -match '^>\s?(.*)$') {
    Flush-Body
    $absText = $Matches[1].Trim()
    if ($absText -ne '') { $script:absBuf.Add($absText) }
    continue
  }
  # Anything else that looks like a blockquote continuation flushes the abstract.
  # List items each become their own IEEE List paragraph.
  if ($trimmed -match '^[-*+]\s+(.*)$') {
    Flush-Body
    Flush-Abs
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE List'; Text = $Matches[1].Trim(); Mono = $false })
    continue
  }
  if ($trimmed -match '^\d+\.\s+(.*)$') {
    Flush-Body
    Flush-Abs
    $script:paras.Add([pscustomobject]@{ Style = 'IEEE List'; Text = $trimmed; Mono = $false })
    continue
  }
  # Default: accumulate body text (soft-wrapped lines join into one paragraph)
  Flush-Abs
  $script:bodyBuf.Add($trimmed)
}
Flush-All

if ($paras.Count -eq 0) { throw "No content parsed from $Markdown" }

# --- Drive Word COM ---------------------------------------------------------
# Strategy: open the template (which carries the IEEE named styles + page setup),
# clear the body, then append each parsed paragraph at the end of the document
# using Selection-based typing so the named style is applied to each paragraph
# as it is created. Selection-based insertion is the most COM-robust way to add
# styled paragraphs without fragile Range arithmetic.
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0  # wdAlertsNone
try {
  $doc = $word.Documents.Open($Template, $false, $false)

  # Clear the body but keep style + section definitions. Select All -> Delete.
  $sel = $word.Selection
  $sel.WholeStory()
  $sel.Delete() | Out-Null
  # After delete there is one empty paragraph left; set a neutral base style.
  try { $sel.Style = $doc.Styles.Item('IEEE Text') } catch {}

  $alignMap = @{
    'IEEE Title'     = 1  # center
    'IEEE Abstract'  = 3  # justify
    'IEEE Heading 1' = 1  # center
    'IEEE Heading 2' = 0  # left
  }

  $idx = 0
  foreach ($para in $paras) {
    $idx++
    if ($idx -gt 1) {
      # Start a new paragraph. Move to end of doc first so we always append.
      $sel.EndKey(6) | Out-Null   # wdStory = 6
      $sel.InsertParagraphAfter()
      $sel.EndKey(6) | Out-Null
    }
    # Set the style for the (current) paragraph before typing.
    try { $sel.Style = $doc.Styles.Item($para.Style) } catch { $sel.Style = $doc.Styles.Item('IEEE Text') }
    $sel.TypeText($para.Text)
    if ($para.Mono) {
      try { $sel.Font.Name = 'Consolas'; $sel.Font.NameFarEast = 'Consolas' } catch {}
    } else {
      # Restore the template's body font (Times New Roman) after a mono block.
      try { $sel.Font.Name = 'Times New Roman' } catch {}
    }
    # Set alignment for this paragraph now that text is typed.
    if ($alignMap.ContainsKey($para.Style)) {
      $sel.ParagraphFormat.Alignment = $alignMap[$para.Style]
    } else {
      $sel.ParagraphFormat.Alignment = 3  # justify for body/list/reference
    }
  }

  # Save as .docx (wdFormatXMLDocument = 16)
  $doc.SaveAs2($Docx, 16) | Out-Null

  # Optional PDF export. ExportAsFixedFormat is Word's native PDF writer and
  # embeds the fonts actually used in the document.
  if ($Pdf) {
    # wdExportFormatPDF=17, OpenAfterExport=$false,
    # OptimizeFor=wdExportOptimizeForPrint=0, Range=wdExportAllDocument=0,
    # From=0, To=0, Item=wdExportDocumentContent=0, IncludeDocProps=$true,
    # KeepIRM=$true, CreateBookmarks=wdExportCreateHeadingBookmarks=1,
    # DocStructureTags=$true, BitmapMissingFonts=$true, UseISO19005_1=$false
    $doc.ExportAsFixedFormat($Pdf, 17, $false, 0, 0, 0, 0, 7, $true, $true, 1, $true) | Out-Null
  }

  $doc.Close($false)
}
finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}

if ($Pdf) {
  if (Test-Path -LiteralPath $Pdf) {
    $bytes = (Get-Item -LiteralPath $Pdf).Length
    Write-Host "WROTE $Docx and $Pdf ($bytes bytes)"
  } else {
    throw "PDF export did not produce $Pdf"
  }
} else {
  Write-Host "WROTE $Docx"
}
