# DVCon U.S. Copyright Form Reference

Source of truth for filling the Accellera/DVCon **Copyright Permission
Agreement** plus the **Speaker Consent Form** that share the same PDF. The
blank form is bundled at `references/dvcon-copyright-form-2027.pdf` (captured
from
`https://confcats-siteplex.s3.amazonaws.com/dvconus/images/dvcon-copyright-form-2027.pdf`,
linked as "Download the PDF Copyright Form" on
`https://dvcon.org/submission-instructions/call-for-extended-abstracts`).

Re-download if DVCon ships a new year. Field **geometry** is stable; the year
in the headings and the virtual-platform end date will change.

The helper is `scripts/fill_copyright_form.py`. It needs **PyMuPDF** (`fitz`).
From the repo root:

```bash
uv run --project backend python \
  plugins/dvcon-papers/skills/dvcon-submit/scripts/fill_copyright_form.py \
  --title "Paper Title" \
  --author "Jane Doe" --author "John Smith" \
  --company "Example Corp" \
  --presenter "Jane Doe" \
  --paper-id "12345" \
  --date 2026-09-07 \
  --authorized-signer "Jane Doe, Engineer" \
  --speaker-consent \
  --output submissions/dvcon-us-2027/copyright.pdf
```

## What DVCon asks authors to fill

From the dvcon.org instructions (re-verify each year):

- Fill in the **TITLE** of the paper.
- Fill in **ALL author names**.
- Input Title, Author, and **Paper ID** directly in Acrobat **before**
  printing.
- **SIGN** the form.
- Upload a scanned PDF via the Oxford Abstracts **Upload File** link on the
  submission page, together with the final manuscript.
- Deadline for DVCon U.S. 2027: **December 23, 2026, 23:59 (GMT -0700)**.
  Without the form the paper cannot be included in the proceedings.

The 2027 PDF has **no dedicated Paper ID widget**. The filler appends
`(Paper ID: …)` to the title field when `--paper-id` is given.

## AcroForm field map (2027)

Acrobat PDFMaker left several widgets misnamed. Match on **field name** as
below, never on the leftover sentence fragment as if it were prose.

### Page 1 — Copyright Permission Agreement

| Visible label | Acrobat field name | Type | Filler action |
|---------------|--------------------|------|----------------|
| `(company name)` in the license sentence | `materials on its websites httpswwwdvconorg and wwwaccelleraorg and select external sites such as industry` | Text | `--company` |
| Title of Document: | `Title of Document 1` | Text | `--title`, with optional `(Paper ID: …)` suffix |
| Author's Name(s): | `Title of Document 2` | Text | `--author` / `--authors` (the widget rect sits on the author line; the field name is wrong) |
| Author Signature | `Author Signature` | Signature | left blank unless `--author-signature <image>` |
| Date Form Signed | `Date Form Signed` | Signature (mislabeled) | stamped as `YYYY-MM-DD` from `--date` (the widget is too narrow for a long date) |
| Employer Authorized Signature | `Employer Authorized Signature If work was performed during service to employer` | Signature | left blank unless `--employer-signature <image>` |
| Authorized Signer's Name and Title | `Authorized Signers Name and Title` | Signature (mislabeled) | stamped as text from `--authorized-signer` |

### Page 2 — PART B (U.S. Government) + Speaker Consent

**PART B** applies only to U.S. Government employees whose work is not subject
to copyright. The filler **does not** complete PART B. If the user is in that
situation, stop and tell them to fill PART B themselves (and typically skip
the company-copyright grant on page 1).

| Visible label | Acrobat field name | Type | Filler action |
|---------------|--------------------|------|----------------|
| Authorized Signature (PART B) | `Authorized Signature` | Signature | never filled |
| Date Form Signed (PART B) | `Date Form Signed_2` | Signature | never filled |
| Presenter Name: | `Presenter Name` | Text | `--presenter` (defaults to the first `--author`) |
| Title of Presentation: | `Title of Presentation` | Text | `--title` without the Paper ID suffix |
| The license shall be valid until revoked | `The license shall be valid until revoked` | CheckBox (on-state `On`) | `--speaker-consent` only after the user confirms |
| Signature: | `Signature` | Signature | left blank unless `--speaker-signature <image>` |
| Date: | `Date` | Text | `--date` |

## Signatures

The filler **never forges a handwritten signature**. Options:

1. Fill the typed fields, leave signature widgets blank, and ask the user to
   open the PDF in Acrobat (or print, wet-sign, scan) before upload.
2. If the user supplies a PNG/JPG of an already-written signature, pass
   `--author-signature` and/or `--speaker-signature` (and
   `--employer-signature` when the employer must countersign).

Do not check `--speaker-consent` unless the user has actually agreed that
DVCon may record the talk and post it on the virtual platform until the date
printed on the form (April 4, 2027 for DVCon U.S. 2027).

## JSON payload (optional)

`--json payload.json` accepts:

```json
{
  "title": "An AI Interface to 17 Years of DVCon",
  "authors": ["Jane Doe", "John Smith"],
  "company": "Example Corp",
  "presenter": "Jane Doe",
  "paper_id": "12345",
  "date": "2026-09-07",
  "authorized_signer": "Jane Doe, Engineer",
  "speaker_consent": true,
  "output": "submissions/dvcon-us-2027/copyright.pdf"
}
```

CLI flags override JSON keys. `--author` can be repeated; `--authors` is a
single comma-separated string.

## Upload

After the user has signed, upload through Oxford Abstracts with
`playwright-cli` the same way as the paper PDF: click `label.fu-hover` on the
copyright **Upload File** control, then `playwright-cli upload` the **absolute**
path. Reach the full-paper stage from the user's submission dashboard — do not
use the abstract-stage "Submit Now" link. Re-snapshot; the control label may
differ from "Extended Abstract - Upload".
