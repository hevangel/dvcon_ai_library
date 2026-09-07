---
name: dvcon-submit
description: Submit papers to the DVCon (Design & Verification Conference) U.S. call for papers via the Oxford Abstracts portal — both the extended-abstract stage and the later full-paper stage — by driving a real browser with the playwright-cli command-line tool. Also converts a DVCon paper written in Markdown into a properly-styled, DVCon/IEEE-template-compliant .docx and .pdf using MS Word, and fills the Accellera/DVCon copyright + speaker-consent PDF. Use whenever the user wants to submit an extended abstract or full paper to DVCon, fill out the DVCon submission form, fill the DVCon copyright form, upload a paper to Oxford Abstracts, enter authors/affiliations/topics into the DVCon submission system, or convert a markdown paper to the DVCon Word template / PDF — even if they don't explicitly say "Oxford Abstracts", "playwright-cli", "copyright form", or "Word template".
---

# DVCon Submit

This skill does three things for DVCon U.S. paper submissions:

1. **Convert** a paper written in Markdown into a `.docx` (and optionally `.pdf`)
   that matches the IEEE-style DVCon abstract template, via MS Word COM. The
   output uses the template's named IEEE styles so it inherits the right fonts,
   sizes, margins, and US Letter paper size automatically.
2. **Fill** the Accellera/DVCon **copyright permission + speaker-consent** PDF
   (title, all author names, company, paper ID, dates). Signature widgets stay
   blank unless the user supplies a signature image — the skill never forges a
   handwritten signature.
3. **Submit** the resulting PDF (or the user's existing PDF) to the DVCon U.S.
   call for papers on **Oxford Abstracts**, by driving a real browser with the
   **`playwright-cli`** command-line tool — including the file upload, which the
   ZCode in-app browser cannot do but `playwright-cli upload` can.

It handles both stages of the DVCon lifecycle:

- **Extended Abstracts** (the initial submission, double-blind, 600–1200 words)
- **Full Paper** (the later stage, after preliminary acceptance, 6–8 pages,
  author info included)

## When to use

Trigger this skill when the user wants to:

- submit an extended abstract **or** a full paper to DVCon (U.S.)
- fill out the DVCon submission form on Oxford Abstracts
- upload a paper PDF to the DVCon / Oxford Abstracts submission system
- enter authors, affiliations, or topics into the DVCon submission form
- convert a markdown paper to the DVCon Word template / PDF
- fill the DVCon / Accellera copyright form (and speaker-consent page)
- prepare a DVCon abstract or full paper for submission

Do **not** trigger this for tutorials/workshops or panel submissions — those are
separate Oxford Abstracts stages with different forms.

## Three tools, two stages

| Task | Stage | Tool |
|------|-------|------|
| Convert markdown → `.docx` + `.pdf` (template-styled) | either | `scripts/convert_md_to_docx.ps1` (PowerShell, MS Word COM) or `scripts/convert_md_to_docx.sh` (bash twin; delegates to the `.ps1` on Windows, else `fill_ieee_docx.py` + LibreOffice) |
| Fill the copyright + speaker-consent PDF | full paper | `scripts/fill_copyright_form.py` (PyMuPDF; bundled `references/dvcon-copyright-form-2027.pdf`) |
| Drive the submission form (fill fields, upload PDF, click Submit) | either | `playwright-cli` (real browser) |

The conversion is optional — if the user already has a compliant PDF, skip
straight to submission. Copyright filling is for the **full-paper** stage (and
can be prepared earlier). The submission is optional too — if the user only
wants a PDF, stop after conversion / copyright fill.

## Prerequisites

### For conversion (markdown → PDF)

- **MS Word must be installed** (the script drives Word via COM). Verified
  available as Word 16.0 on this machine. No LibreOffice/pandoc needed.
- The DVCon template is bundled at
  `references/dvcon_abstract_template.doc` (Word `.doc`, OLE2). A read-only PDF
  rendering of the same template is at `references/dvcon_abstract_template.pdf`
  for visual reference. Re-download the latest from the dvcon.org instructions
  page if the conference updates it.

### For submission (driving Oxford Abstracts)

- **`playwright-cli`** must be installed and on PATH
  (`playwright-cli --version` should print a version; verified v0.1.14 here).
  It provides `open --headed`, `goto`, `snapshot`, `fill`, `select`, `check`,
  `click`, and crucially `upload` — so the abstract PDF upload is automatable,
  unlike the ZCode in-app browser.
- **The user must be signed in to Oxford Abstracts.** Launch
  `playwright-cli open --headed --persistent` so the browser is visible and the
  profile persists; if the sign-in page appears, ask the user to log in
  (email/password, Google, or LinkedIn) in that visible window, then continue.
  Never enter credentials yourself.
- The user must have a finished, compliant paper PDF.
- **Copyright form** (full-paper stage): PyMuPDF, already a backend
  dependency. Run the filler with `uv run --project backend python …`. The
  blank form is bundled; re-download from dvcon.org if the conference year
  changes.

## Collect the submission payload first

Before touching the browser or the converter, confirm you have every required
field. If anything is missing or ambiguous, ask — do not guess author names,
emails, affiliations, or topics.

| Field | Required | Notes |
|-------|----------|-------|
| `title` | yes | Full title, ≤ 50 characters. Used in the final program. |
| `short_description` | yes | Plain text, ≤ 250 words. Used in the final program. |
| `paper_pdf_path` | yes | Local PDF. Abstract stage: 600–1200 words, double-blind. Full-paper stage: 6–8 pages, with author info. |
| `authors[]` | yes (≥1) | Each: `first_name`, `last_name`, `email`, `is_presenting` (exactly **one** presenter), and ≥1 `affiliation` (`institution`, `city`, `country`). Order = printed order. **Author info goes in the FORM, not the abstract PDF.** Required in the form for both stages; in the PDF only for the full-paper stage. |
| `presenter_country` | yes | Country the presenter travels from (may differ from residency). |
| `primary_topic` | yes | One of the 14 topics (see `references/submission_reference.md`). |
| `secondary_topic` | optional | One of the same 14 topics. |
| `consents` | yes (all 3) | Publish permission, all-authors-approved, will-attend-and-present. |
| `company` | full-paper copyright | Employer / copyright holder named in the license sentence. |
| `paper_id` | full-paper copyright | Oxford Abstracts paper id. The 2027 PDF has no Paper ID widget; the filler appends it to the title. |
| `copyright_date` | full-paper copyright | Date the form is signed. |
| `authorized_signer` | full-paper copyright | Employer authorized signer's name and title, when work was done for an employer. |
| `speaker_consent` | full-paper copyright | User must confirm DVCon may record and post the talk on the virtual platform. |

### Stage-specific PDF rules

**Extended Abstract stage** (double-blind):

- 600–1200 words (~2 pages, excluding diagrams/figures/tables). NOT the full paper.
- **US Letter (8.5″ × 11″)**, embed all fonts, avoid Type 3 fonts.
- **No page numbers.** No security/encryption settings on the PDF.
- **Adobe PDF (.pdf)** preferred; max **5.0 MB**.
- **No author names or affiliations anywhere in the PDF.**

**Full Paper stage** (after preliminary acceptance):

- 6–8 pages.
- Same US Letter / font-embedding / no-security rules.
- **Author names and affiliations ARE included** in the full paper.
- A signed **copyright form** (PDF) must also be uploaded by the final deadline.
  Fill it with Workflow B (title + all author names + paper ID + company), then
  the user signs (Acrobat or wet-ink). Upload via the submission page's
  Upload File control.

## Workflow A — Convert markdown to the DVCon template PDF

Read `references/conversion_reference.md` for the full markdown-to-style mapping,
the list of IEEE named styles the template defines, and troubleshooting. The
reference is the source of truth for the conversion.

Two interchangeable helper scripts are provided — pick the one matching your
shell. Both take the same arguments (the bash version uses `--flag` style):

**PowerShell** (Windows native; drives MS Word via COM):

```powershell
powershell -ExecutionPolicy Bypass -File "<skill_dir>/scripts/convert_md_to_docx.ps1" `
  -Markdown C:\papers\mine.md `
  -Docx     C:\papers\mine.docx `
  -Pdf      C:\papers\mine.pdf
```

**Bash** (Git Bash / macOS / Linux). On Windows it auto-detects PowerShell and
delegates to the `.ps1` so the output is identical; on other platforms it
converts the bundled `.doc` to `.docx` with LibreOffice, then
`fill_ieee_docx.py` fills the IEEE named styles (same mapping as the `.ps1`,
including inline runs). pandoc is not used:

```bash
"<skill_dir>/scripts/convert_md_to_docx.sh" \
  --markdown /path/to/paper.md \
  --docx     /path/to/paper.docx \
  --pdf      /path/to/paper.pdf
```

Drop the `-Pdf` / `--pdf` argument to produce only the `.docx`. The script:

- opens the bundled template (carrying the IEEE styles + US Letter page setup),
- clears the body,
- re-emits the markdown using the template's named styles
  (`# H1`→IEEE Title, `>`blockquote→IEEE Abstract, `## H2`→IEEE Heading 1,
  `### H3`→IEEE Heading 2, lists→IEEE List, `[n]` lines→IEEE Reference,
  body→IEEE Text, fenced code→IEEE Text monospace),
- converts inline markers to real character formatting
  (`**bold**`, `*italic*`, `` `code` ``→Consolas, `[label](url)`), so no
  asterisks or backticks leak into the PDF,
- **drops any `## Authors` / `## Affiliations` / `## Author Information`
  section** so the abstract PDF stays double-blind compliant,
- saves the `.docx` and exports the `.pdf` with embedded fonts.

After conversion, **verify the output** before submitting:

1. Word-count the body (Title + Abstract + sections, excluding the reference
   list and figures): must be 600–1200 for the abstract stage.
2. Confirm the PDF opens, is US Letter, and contains no author names (the
   converter drops the Authors section, but the user's prose may still mention
   affiliations — grep the markdown for "we", company names, etc., and warn).
3. Confirm file size ≤ 5 MB.

### Full-paper conversion caveat

The converter drops `## Authors` / `## Affiliations` / `## Author Information`
sections by default (correct for the double-blind abstract). For the **full
paper**, author info must be retained. Two options:

- Rename the author heading to something NOT in the drop list before converting
  (e.g. `## Authors and Affiliations`), then convert.
- Or convert without the author section, then open the `.docx` in Word and add
  the author block manually before exporting the PDF.

## Workflow B — Fill the copyright + speaker-consent PDF

Read `references/copyright_reference.md` for the AcroForm field map. Several
Acrobat field names on the 2027 PDF do **not** match the visible labels
(Author's Name(s) is stored as `Title of Document 2`; Date Form Signed is a
Signature widget). The script maps those; do not fill by guessing names from a
snapshot of the PDF.

Required before running: `title`, every author name in printed order,
`company` (the license names the copyright holder), and the Oxford Abstracts
`paper_id` once the user has it. Ask if any of those are missing. Also ask:

- the signature date (default today only after confirming)
- presenter name (defaults to the first author)
- authorized signer name + title, if the work was done for an employer
- whether to check the speaker-consent box (virtual-platform recording license)
- whether the user has a signature PNG/JPG, or will sign in Acrobat / on paper

Do **not** complete PART B (U.S. Government employees). If the user says they
are a U.S. Government employee whose work is not subject to copyright, stop
and tell them to fill PART B themselves.

```bash
uv run --project backend python \
  "<skill_dir>/scripts/fill_copyright_form.py" \
  --title     "An AI Interface to 17 Years of DVCon" \
  --author    "Jane Doe" \
  --author    "John Smith" \
  --company   "Example Corp" \
  --presenter "Jane Doe" \
  --paper-id  "12345" \
  --date      2026-09-07 \
  --authorized-signer "Jane Doe, Engineer" \
  --speaker-consent \
  --output    C:\papers\copyright.pdf
```

Pass `--author-signature` / `--speaker-signature` / `--employer-signature` only
when the user provides an image of an already-written signature. Otherwise
leave those widgets blank and tell the user to sign before upload.

After filling, read the JSON summary back to the user (title, authors, company,
paper ID suffix, date, consent checkbox, unsigned=true/false). Then:

1. If `unsigned` is true, wait for the user to sign.
2. Upload the signed PDF on the full-paper Oxford Abstracts page with
   `playwright-cli click "label.fu-hover"` then
   `playwright-cli upload "<absolute signed pdf>"` (same Choose File gotcha as
   the paper upload). Re-snapshot first — the control is **Upload File**, not
   the abstract-stage "Extended Abstract - Upload".

## Workflow C — Submit to Oxford Abstracts via playwright-cli

Read `references/submission_reference.md` for exact field labels, the 14 topic
dropdown options, the two country-dropdown label variants, and the rich-text
editor gotchas. The reference is the source of truth for the form.

### C.1 Open a persistent, visible browser

```bash
playwright-cli open --headed --persistent
```

`--headed` lets the user see (and log into) the window. `--persistent` keeps the
profile so login survives across runs. If the user already has a session open,
`playwright-cli list` shows it; otherwise `open` creates one.

### C.2 Discover the submitter URL and navigate

Discover the current portal URL rather than guessing the stage id — it changes
every year (DVCon U.S. 2027 = stage `81951`):

```bash
playwright-cli goto "https://dvcon.org/submission-instructions/call-for-extended-abstracts"
playwright-cli snapshot
```

From the snapshot, find the **Submit Now** link
(`https://app.oxfordabstracts.com/stages/<ID>/submitter`) and `goto` it. If the
sign-in page appears, ask the user to log in in the visible window, then
`snapshot` again. After login the portal lands on the new-submission form.

### C.3 Take a snapshot to get element refs

```bash
playwright-cli snapshot
```

`playwright-cli` commands take a **target** argument that is either an exact
element **ref** from the most recent snapshot, or a unique CSS selector. Always
`snapshot` before acting, and re-snapshot after any action that re-renders the
page (e.g., clicking "+ Add Another Author"). Stale refs cause failures.

### C.4 Fill the fields

Use the refs from the snapshot. Field order and the exact labels are in
`references/submission_reference.md`; the short summary:

```bash
# Rich-text editors (Title, Short Description): fill the contenteditable region
playwright-cli fill "<title_ref>"           "My DVCon Paper Title"
playwright-cli fill "<short_desc_ref>"      "A short description of my paper..."

# Repeatable Authors block: fill First/Last/Email, check Presenting for ONE author,
# fill Affiliation (Institution/City), select Country from the dropdown
playwright-cli fill  "<first_name_ref>"     "Jane"
playwright-cli fill  "<last_name_ref>"      "Doe"
playwright-cli fill  "<email_ref>"          "jane@example.com"
playwright-cli check "<presenting_ref>"
playwright-cli fill  "<institution_ref>"    "Example Corp"
playwright-cli fill  "<city_ref>"           "San Jose"
playwright-cli select "<affiliation_country_ref>" "USA"      # NOTE: "USA" here
playwright-cli click  "<add_another_author_ref>"
playwright-cli snapshot    # re-snapshot: the new block has fresh refs

# Three consent checkboxes
playwright-cli check "<publish_perm_ref>"
playwright-cli check "<all_authors_approved_ref>"
playwright-cli check "<will_attend_ref>"

# Presenter travel-from country — NOTE: "United States" here, NOT "USA"
playwright-cli select "<presenter_country_ref>" "United States"

# Topics (short labels: Formal/Assertions, Coverage, CDC/RDC, ...)
playwright-cli select "<primary_topic_ref>"   "Formal/Assertions"
playwright-cli select "<secondary_topic_ref>" "Coverage"
```

The two country dropdowns use **different option labels** — see the reference.

### C.5 Upload the PDF (playwright-cli CAN do this)

```bash
playwright-cli click  "label.fu-hover"        # NOT the "Choose File" snapshot ref
playwright-cli upload "C:\papers\mine.pdf"
```

`upload` feeds absolute file paths to the page's file chooser, but it only works
while a file-chooser **modal state** is open. Do not click the snapshot ref
labelled `button "file_upload Choose File (...)"` — that ref resolves to the
hidden `<input type="file" class="sr-only">`, and the visible
`<label class="... fu-hover">` on top of it intercepts pointer events, so the
click times out and `upload` then fails with `can only be used when there is
related modal state present`. Click the **label** instead; a good click reports
`### Modal state - [File chooser]: can be handled by upload`. After uploading,
re-snapshot and confirm the widget now shows `Replace file ...`, a `Remove`
button, and a `Download uploaded file` link.

### C.6 Final review and submit

Read back every field value to the user for sign-off (title, short description,
all authors + affiliations, topics, country, the three consents, and
confirmation that the PDF is attached). Then ask explicitly whether to click
**Submit**.

Only after the user confirms, click Submit:

```bash
playwright-cli click "<submit_ref>"
```

If the form surfaces validation errors, re-snapshot, report the exact errors,
fix them, and re-review. Never click Submit without explicit user confirmation —
submission is a hard-to-reverse outward action.

### C.7 Full-paper stage differences

When the user returns to submit the **full paper** after preliminary acceptance:

- The Oxford Abstracts stage is different (a new stage id); navigate from the
  user's submission dashboard rather than the abstract "Submit Now" link.
- The full paper **includes** author info — do NOT apply the double-blind drop.
  See "Full-paper conversion caveat" under Workflow A.
- A signed copyright form PDF must also be uploaded before the final deadline.
  Produce it with Workflow B; do not upload a blank or unsigned form.
- The page limit is 6–8 pages, not 600–1200 words.

## Safety rules

- **Never click Submit without explicit user confirmation.**
- **Never enter the user's credentials.** Hand login to the user via the headed
  window.
- **Never invent author names, emails, affiliations, topics, or copyright
  company / paper ID.** If the payload is incomplete, ask.
- **Never forge a handwritten signature** on the copyright form. Leave the
  signature widgets blank or stamp only an image the user supplied.
- **Do not check speaker consent** on the copyright PDF unless the user has
  confirmed the virtual-platform recording license.
- **Do not fill PART B** of the copyright PDF (U.S. Government employees).
- **Abstract stage is double-blind.** The markdown converter drops `## Authors`
  sections automatically; also warn if the body prose mentions specific
  companies or uses "we [at Company]" phrasing that could de-anonymize.
- **Full-paper stage is NOT blind** — author info belongs in the PDF.
- The three consent checkboxes are legal attestations (all authors approved;
  someone will attend and present). Do not check them unless the user has
  actually confirmed those facts.
- Each `goto` URL must come from the dvcon.org page, the Oxford Abstracts UI, or
  the user's submission dashboard — never a guess. Stage ids change yearly.
- `playwright-cli` drives a real browser that the user can see; describe actions
  in plain terms ("opening the form", "filling the title"), not internal CLI
  jargon.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `convert_md_to_docx.ps1` / `.sh`: "Word COM" error / "read-only" | Ensure MS Word is installed and not held open elsewhere; both scripts remove pre-existing output files before writing |
| `convert_md_to_docx.sh` on macOS/Linux: "python3 not found" / "LibreOffice not found" | The bash wrapper's non-Windows branch needs Python 3 (stdlib) and `libreoffice` (`soffice`); it does **not** use pandoc. On Windows it auto-delegates to the `.ps1` instead |
| Conversion emits every line as its own paragraph | Fixed in current script — soft-wrapped body lines are joined; re-run if you edited the script |
| `**bold**` / `*italic*` markers appear in the PDF | Fixed in current script — paragraphs are split into character runs; see `references/conversion_reference.md` |
| Output `.docx` "not updated" | It is; `submissions/**/*.docx` is gitignored so it never shows in `git status`. Close any Word window holding a stale copy and check the file timestamp. |
| Authors leaked into the abstract PDF | The converter drops `## Authors`/`## Affiliations`/`## Author Information`; check the body prose for self-identifying language |
| `playwright-cli` not found | Install/repair the global CLI; confirm with `playwright-cli --version` |
| Portal shows the sign-in page | `open --headed --persistent` and ask the user to log in; the profile persists for next time |
| A `fill`/`select` target is ambiguous | Re-`snapshot`; `playwright-cli` needs an exact ref or unique selector — tighten scope rather than guessing |
| `select "USA"` fails on the presenter country | The presenter dropdown uses `United States`; only the affiliation dropdown uses `USA`. See the reference. |
| `upload` says "can only be used when there is related modal state present" | The Choose File click did not open the chooser. Click `label.fu-hover`, not the `Choose File` snapshot ref (that ref is the hidden `input.sr-only`, and the label intercepts pointer events). Then `upload` the **absolute** path. |
| Title truncated unnecessarily | The `0/50` counter on Title counts **words**, not characters. A 47-character title reads `9/50`. |
| Validation error on Submit | Re-snapshot, report the exact message, fix, re-review with the user |
| `fill_copyright_form.py`: "PyMuPDF (fitz) is required" | Run via `uv run --project backend python …` from the repo root. |
| `fill_copyright_form.py`: author names landed on the title line | The 2027 form stores authors in the widget named `Title of Document 2`. Re-run the script rather than editing field names by hand. |
| Copyright PDF has no Paper ID box | Expected for 2027. Pass `--paper-id`; it is appended to the title. |
| Copyright PDF still shows SIGN placeholders | Signature widgets are blank on purpose. Sign in Acrobat, or pass `--author-signature` / `--speaker-signature`. |
| PART B (U.S. Government) left empty | Expected. Only U.S. Government employees complete that block, by hand. |
