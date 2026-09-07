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

# --- Inline markdown -> character-formatted runs ----------------------------
# Paragraph text still carries inline markers (**bold**, *italic*, `code`,
# [text](url)). Typing it verbatim would leave the markers visible in the PDF,
# so each paragraph is split into runs that Word can format individually.
# Backslash escapes (\* \_ \` \[ \] \\) are mapped to private-use characters
# during matching and restored as literals afterwards.
$script:inlineEscapes = [ordered]@{
  '\\' = [char]0xE000
  '\*' = [char]0xE001
  '\_' = [char]0xE002
  '\`' = [char]0xE003
  '\[' = [char]0xE004
  '\]' = [char]0xE005
}

# Alternation order matters: *** before ** before *, so the longest marker wins
# (a lazy `\*\*.+?\*\*` would otherwise chew ***both*** and leave a stray *).
# The _italic_ form requires non-word boundaries so identifiers and DOIs
# (e.g. 2024.findings-acl_137) are not mangled.
$script:inlinePattern = '(?<code>`[^`]+`)' +
  '|(?<bolditalic>\*\*\*.+?\*\*\*)' +
  '|(?<bolditalicu>___.+?___)' +
  '|(?<bold>\*\*.+?\*\*)' +
  '|(?<boldu>__.+?__)' +
  '|(?<italic>\*[^*]+?\*)' +
  '|(?<italicu>(?<!\w)_[^_]+?_(?!\w))' +
  '|(?<link>\[(?<ltext>[^\]]*)\]\((?<lurl>[^)]*)\))'

function New-Run([string]$Text, [bool]$Bold, [bool]$Italic, [bool]$Mono) {
  [pscustomobject]@{ Text = $Text; Bold = $Bold; Italic = $Italic; Mono = $Mono }
}

function Get-InlineRuns {
  param([string]$Text, [bool]$Bold = $false, [bool]$Italic = $false, [int]$Depth = 0)
  $runs = New-Object System.Collections.Generic.List[object]
  if ($Depth -gt 4) {
    $runs.Add((New-Run $Text $Bold $Italic $false))
    return , $runs
  }
  $pos = 0
  foreach ($m in [regex]::Matches($Text, $script:inlinePattern)) {
    if ($m.Index -lt $pos) { continue }
    if ($m.Index -gt $pos) {
      $runs.Add((New-Run $Text.Substring($pos, $m.Index - $pos) $Bold $Italic $false))
    }
    $v = $m.Value
    if ($m.Groups['code'].Success) {
      $runs.Add((New-Run $v.Substring(1, $v.Length - 2) $Bold $Italic $true))
    }
    elseif ($m.Groups['bolditalic'].Success -or $m.Groups['bolditalicu'].Success) {
      foreach ($r in (Get-InlineRuns -Text $v.Substring(3, $v.Length - 6) -Bold $true -Italic $true -Depth ($Depth + 1))) {
        $runs.Add($r)
      }
    }
    elseif ($m.Groups['bold'].Success -or $m.Groups['boldu'].Success) {
      foreach ($r in (Get-InlineRuns -Text $v.Substring(2, $v.Length - 4) -Bold $true -Italic $Italic -Depth ($Depth + 1))) {
        $runs.Add($r)
      }
    }
    elseif ($m.Groups['italic'].Success -or $m.Groups['italicu'].Success) {
      foreach ($r in (Get-InlineRuns -Text $v.Substring(1, $v.Length - 2) -Bold $Bold -Italic $true -Depth ($Depth + 1))) {
        $runs.Add($r)
      }
    }
    elseif ($m.Groups['link'].Success) {
      $ltext = $m.Groups['ltext'].Value
      $lurl = $m.Groups['lurl'].Value
      $shown = if ($ltext -ne '') { $ltext } else { $lurl }
      # Keep the URL visible when the label does not already contain it —
      # a printed paper has no clickable affordance.
      if ($lurl -match '^\s*https?://' -and $shown -notlike "*$lurl*") {
        $shown = "$shown ($lurl)"
      }
      foreach ($r in (Get-InlineRuns -Text $shown -Bold $Bold -Italic $Italic -Depth ($Depth + 1))) {
        $runs.Add($r)
      }
    }
    $pos = $m.Index + $m.Length
  }
  if ($pos -lt $Text.Length) {
    $runs.Add((New-Run $Text.Substring($pos) $Bold $Italic $false))
  }
  return , $runs
}

# Drop manual character formatting so the paragraph style governs again.
# Older Word builds can refuse Font.Reset on a collapsed selection, hence the
# explicit fallback.
function Reset-Font($Selection) {
  try { $Selection.Font.Reset() }
  catch {
    try {
      $Selection.Font.Bold = 0
      $Selection.Font.Italic = 0
      $Selection.Font.Name = 'Times New Roman'
    } catch {}
  }
}

function Split-InlineMarkdown([string]$Text) {
  $protected = $Text
  foreach ($k in $script:inlineEscapes.Keys) {
    $protected = $protected.Replace($k, [string]$script:inlineEscapes[$k])
  }
  $out = New-Object System.Collections.Generic.List[object]
  foreach ($run in (Get-InlineRuns -Text $protected)) {
    $t = $run.Text
    foreach ($k in $script:inlineEscapes.Keys) {
      $t = $t.Replace([string]$script:inlineEscapes[$k], $k.Substring(1))
    }
    if ($t -ne '') { $out.Add((New-Run $t $run.Bold $run.Italic $run.Mono)) }
  }
  if ($out.Count -eq 0) { $out.Add((New-Run '' $false $false $false)) }
  return , $out
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
    # Character formatting is applied per run and reset between runs, so a
    # style that is itself bold/italic (e.g. IEEE Abstract) keeps its own look:
    # Reset() drops manual formatting and lets the paragraph style govern, and
    # bold/italic are only ever turned ON, never forced off.
    if ($para.Mono) {
      # Fenced code is verbatim: inline markers inside a code block are literal.
      Reset-Font $sel
      try { $sel.Font.Name = 'Consolas'; $sel.Font.NameFarEast = 'Consolas' } catch {}
      $sel.TypeText($para.Text)
    } else {
      foreach ($run in (Split-InlineMarkdown $para.Text)) {
        if ($run.Text -eq '') { continue }
        Reset-Font $sel
        if ($run.Mono) { try { $sel.Font.Name = 'Consolas' } catch {} }
        if ($run.Bold) { try { $sel.Font.Bold = 1 } catch {} }
        if ($run.Italic) { try { $sel.Font.Italic = 1 } catch {} }
        $sel.TypeText($run.Text)
      }
    }
    # Keep formatting from leaking into the next paragraph.
    Reset-Font $sel
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
