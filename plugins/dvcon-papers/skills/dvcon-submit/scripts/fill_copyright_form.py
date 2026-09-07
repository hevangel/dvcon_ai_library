#!/usr/bin/env python3
"""Fill the DVCon U.S. copyright + speaker-consent PDF.

The bundled 2027 form (references/dvcon-copyright-form-2027.pdf) is an
AcroForm. Several Acrobat field names do not match the visible labels —
see references/copyright_reference.md. This script fills the typed
fields, stamps dates / authorized-signer name onto widgets that were
incorrectly created as Signature fields, and optionally stamps a user-
supplied signature image.

It never invents a handwritten signature. Signature widgets stay blank
unless the caller passes an image file.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyMuPDF (fitz) is required. From the repo root run:\n"
        "  uv run --project backend python "
        "plugins/dvcon-papers/skills/dvcon-submit/scripts/fill_copyright_form.py ..."
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = (
    SCRIPT_DIR.parent / "references" / "dvcon-copyright-form-2027.pdf"
)

# Acrobat field names on the 2027 form. "Title of Document 2" is the
# Author's Name(s) widget — the label and the widget rect line up, the
# field name does not. The company widget's name is a leftover sentence
# fragment from PDFMaker.
FIELD_COMPANY = (
    "materials on its websites httpswwwdvconorg and wwwaccelleraorg "
    "and select external sites such as industry"
)
FIELD_TITLE = "Title of Document 1"
FIELD_AUTHORS = "Title of Document 2"
FIELD_PRESENTER = "Presenter Name"
FIELD_PRESENTATION_TITLE = "Title of Presentation"
FIELD_SPEAKER_DATE = "Date"
FIELD_SPEAKER_CONSENT = "The license shall be valid until revoked"

# These are Signature widgets on the 2027 form even though the visible
# labels are ordinary text. We stamp text into their rectangles.
OVERLAY_AUTHOR_DATE = "Date Form Signed"
OVERLAY_SIGNER_NAME = "Authorized Signers Name and Title"

SIG_AUTHOR = "Author Signature"
SIG_EMPLOYER = (
    "Employer Authorized Signature If work was performed during "
    "service to employer"
)
SIG_SPEAKER = "Signature"

TEXT_FONT = "helv"


def _format_long_date(value: datetime | date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _parse_date(value: str) -> str:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return _format_long_date(parsed)
        except ValueError:
            continue
    return raw


def _join_authors(authors: list[str]) -> str:
    cleaned = [a.strip() for a in authors if a and a.strip()]
    return ", ".join(cleaned)


def _title_with_paper_id(title: str, paper_id: str | None) -> str:
    title = title.strip()
    if paper_id:
        paper_id = paper_id.strip()
        if paper_id and paper_id.lower() not in title.lower():
            return f"{title}  (Paper ID: {paper_id})"
    return title


def _set_text_widget(widget, value: str, max_size: float = 11.0) -> None:
    text = value.strip()
    widget.field_value = text
    size = max_size
    width = max(widget.rect.width, 1.0)
    # Rough Helvetica width ~0.5em; shrink until it is likely to fit.
    while size > 6.0 and (len(text) * size * 0.5) > width:
        size -= 0.5
    widget.text_font = "Helv"
    widget.text_fontsize = size
    widget.update()


def _stamp_text(page, rect, text: str, fontsize: float = 10.0) -> None:
    if not text.strip():
        return
    value = text.strip()
    width = max(rect.width, 1.0)
    size = fontsize
    while size > 6.0 and (len(value) * size * 0.5) > width:
        size -= 0.5
    page.insert_textbox(
        rect,
        value,
        fontsize=size,
        fontname=TEXT_FONT,
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _stamp_image(page, rect, image_path: Path) -> None:
    if not image_path.is_file():
        raise FileNotFoundError(f"signature image not found: {image_path}")
    page.insert_image(rect, filename=str(image_path), keep_proportion=True)


def _find_widget(page, field_name: str):
    for widget in page.widgets() or []:
        if widget.field_name == field_name:
            return widget
    return None


def fill_copyright_form(
    template: Path,
    output: Path,
    *,
    title: str,
    authors: list[str],
    company: str,
    presenter: str | None = None,
    paper_id: str | None = None,
    date_signed: str | None = None,
    authorized_signer: str | None = None,
    speaker_consent: bool = False,
    author_signature: Path | None = None,
    speaker_signature: Path | None = None,
    employer_signature: Path | None = None,
) -> dict:
    """Fill the bundled copyright PDF and write `output`.

    Returns a dict of the values that were written, for verification.
    """
    if not template.is_file():
        raise FileNotFoundError(f"copyright template not found: {template}")

    author_line = _join_authors(authors)
    if not title.strip():
        raise ValueError("title is required")
    if not author_line:
        raise ValueError("at least one author is required")
    if not company.strip():
        raise ValueError("company is required (the license names the copyright holder)")

    presenter_name = (presenter or authors[0]).strip()
    iso_date = date.today().isoformat()
    if date_signed:
        raw = date_signed.strip()
        parsed_iso = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed_iso = datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                continue
        iso_date = parsed_iso or raw
    signed = _parse_date(date_signed or iso_date)
    full_title = _title_with_paper_id(title, paper_id)
    presentation_title = title.strip()

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    doc = fitz.open(template)
    if doc.page_count < 2:
        doc.close()
        raise ValueError(f"expected a 2-page copyright form, got {doc.page_count}")

    page0 = doc[0]
    page1 = doc[1]

    company_w = _find_widget(page0, FIELD_COMPANY)
    title_w = _find_widget(page0, FIELD_TITLE)
    authors_w = _find_widget(page0, FIELD_AUTHORS)
    if company_w is None or title_w is None or authors_w is None:
        doc.close()
        raise RuntimeError(
            "copyright template is missing expected text fields; "
            "re-download dvcon-copyright-form-2027.pdf"
        )

    _set_text_widget(company_w, company, max_size=9.0)
    _set_text_widget(title_w, full_title, max_size=11.0)
    _set_text_widget(authors_w, author_line, max_size=11.0)

    date_w = _find_widget(page0, OVERLAY_AUTHOR_DATE)
    if date_w is not None:
        _stamp_text(page0, date_w.rect, iso_date, fontsize=10.0)
    signer_w = _find_widget(page0, OVERLAY_SIGNER_NAME)
    if signer_w is not None and authorized_signer:
        _stamp_text(page0, signer_w.rect, authorized_signer, fontsize=10.0)

    if author_signature is not None:
        sig_w = _find_widget(page0, SIG_AUTHOR)
        if sig_w is None:
            doc.close()
            raise RuntimeError("Author Signature widget missing")
        _stamp_image(page0, sig_w.rect, author_signature)

    if employer_signature is not None:
        emp_w = _find_widget(page0, SIG_EMPLOYER)
        if emp_w is None:
            doc.close()
            raise RuntimeError("Employer Authorized Signature widget missing")
        _stamp_image(page0, emp_w.rect, employer_signature)

    presenter_w = _find_widget(page1, FIELD_PRESENTER)
    pres_title_w = _find_widget(page1, FIELD_PRESENTATION_TITLE)
    speaker_date_w = _find_widget(page1, FIELD_SPEAKER_DATE)
    consent_w = _find_widget(page1, FIELD_SPEAKER_CONSENT)
    if presenter_w is None or pres_title_w is None or speaker_date_w is None:
        doc.close()
        raise RuntimeError(
            "copyright template is missing speaker-consent text fields"
        )

    _set_text_widget(presenter_w, presenter_name, max_size=11.0)
    _set_text_widget(pres_title_w, presentation_title, max_size=11.0)
    _set_text_widget(speaker_date_w, signed, max_size=11.0)

    if speaker_consent:
        if consent_w is None:
            doc.close()
            raise RuntimeError("speaker-consent checkbox missing")
        consent_w.field_value = consent_w.on_state()
        consent_w.update()

    if speaker_signature is not None:
        sp_w = _find_widget(page1, SIG_SPEAKER)
        if sp_w is None:
            doc.close()
            raise RuntimeError("speaker Signature widget missing")
        _stamp_image(page1, sp_w.rect, speaker_signature)

    doc.save(output, deflate=True)
    doc.close()

    return {
        "output": str(output),
        "company": company.strip(),
        "title": full_title,
        "authors": author_line,
        "presenter": presenter_name,
        "presentation_title": presentation_title,
        "date": signed,
        "paper_id": (paper_id or "").strip() or None,
        "authorized_signer": (authorized_signer or "").strip() or None,
        "speaker_consent": bool(speaker_consent),
        "author_signature": bool(author_signature),
        "speaker_signature": bool(speaker_signature),
        "employer_signature": bool(employer_signature),
        "unsigned": not (author_signature or speaker_signature),
    }


def dump_fields(template: Path) -> None:
    doc = fitz.open(template)
    for index, page in enumerate(doc):
        print(f"page {index + 1}")
        for widget in page.widgets() or []:
            print(
                f"  {widget.field_type_string:10} "
                f"{widget.field_name!r} = {widget.field_value!r}"
            )
    doc.close()


def _self_test(template: Path) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "filled.pdf"
        result = fill_copyright_form(
            template,
            out,
            title="An AI Interface to 17 Years of DVCon",
            authors=["Jane Doe", "John Smith"],
            company="Example Corp",
            presenter="Jane Doe",
            paper_id="4242",
            date_signed="2026-09-07",
            authorized_signer="Jane Doe, Engineer",
            speaker_consent=True,
        )
        doc = fitz.open(out)
        page0 = {w.field_name: w.field_value for w in doc[0].widgets()}
        page1 = {w.field_name: w.field_value for w in doc[1].widgets()}
        text0 = doc[0].get_text()
        doc.close()

        assert page0[FIELD_COMPANY] == "Example Corp"
        assert "An AI Interface to 17 Years of DVCon" in page0[FIELD_TITLE]
        assert "Paper ID: 4242" in page0[FIELD_TITLE]
        assert page0[FIELD_AUTHORS] == "Jane Doe, John Smith"
        assert page1[FIELD_PRESENTER] == "Jane Doe"
        assert page1[FIELD_PRESENTATION_TITLE] == (
            "An AI Interface to 17 Years of DVCon"
        )
        assert page1[FIELD_SPEAKER_DATE] == "September 7, 2026"
        assert page1[FIELD_SPEAKER_CONSENT] == "On"
        assert "Jane Doe, Engineer" in text0
        assert "2026-09-07" in text0
        assert result["unsigned"] is True
    print("self-test ok")
    return 0


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--json file must contain an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fill the DVCon U.S. copyright + speaker-consent PDF."
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="blank copyright PDF (defaults to the bundled 2027 form)",
    )
    parser.add_argument("--output", "-o", type=Path, help="filled PDF path")
    parser.add_argument("--title", help="paper title")
    parser.add_argument(
        "--author",
        action="append",
        dest="author_list",
        default=[],
        help="author name (repeatable). Printed order follows flag order.",
    )
    parser.add_argument(
        "--authors",
        help="comma-separated author names (alternative to repeating --author)",
    )
    parser.add_argument("--company", help="copyright-holder / employer name")
    parser.add_argument("--presenter", help="speaker-consent presenter name")
    parser.add_argument(
        "--paper-id",
        help="Oxford Abstracts paper id; appended to the title "
        "(the 2027 form has no dedicated Paper ID field)",
    )
    parser.add_argument(
        "--date",
        help="signature date (YYYY-MM-DD, or a locale date). Default: today.",
    )
    parser.add_argument(
        "--authorized-signer",
        help="employer authorized signer's name and title (stamped as text)",
    )
    parser.add_argument(
        "--speaker-consent",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="check 'The license shall be valid until revoked' "
        "(only after the user confirms)",
    )
    parser.add_argument(
        "--author-signature",
        type=Path,
        help="optional PNG/JPG of the author's wet signature",
    )
    parser.add_argument(
        "--speaker-signature",
        type=Path,
        help="optional PNG/JPG of the speaker-consent signature",
    )
    parser.add_argument(
        "--employer-signature",
        type=Path,
        help="optional PNG/JPG of the employer authorized signature",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="optional JSON payload (keys: title, authors, company, "
        "presenter, paper_id, date, authorized_signer, speaker_consent, "
        "author_signature, speaker_signature, employer_signature)",
    )
    parser.add_argument(
        "--print-fields",
        action="store_true",
        help="dump template field names and exit",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="fill a temp copy of the bundled template and assert values",
    )
    args = parser.parse_args(argv)

    if args.print_fields:
        dump_fields(args.template)
        return 0
    if args.self_test:
        return _self_test(args.template)

    payload = _load_json(args.json) if args.json else {}
    title = args.title or payload.get("title")
    company = args.company or payload.get("company")
    presenter = args.presenter or payload.get("presenter")
    paper_id = args.paper_id or payload.get("paper_id")
    date_signed = args.date or payload.get("date")
    authorized_signer = args.authorized_signer or payload.get(
        "authorized_signer"
    )

    authors: list[str] = list(args.author_list)
    if args.authors:
        authors.extend(part.strip() for part in args.authors.split(","))
    if not authors:
        raw = payload.get("authors") or []
        if isinstance(raw, str):
            authors = [part.strip() for part in raw.split(",")]
        else:
            authors = [str(item).strip() for item in raw]

    if args.speaker_consent is not None:
        speaker_consent = args.speaker_consent
    elif "speaker_consent" in payload:
        speaker_consent = bool(payload.get("speaker_consent"))
    else:
        speaker_consent = False

    output = args.output or (
        Path(payload["output"]) if payload.get("output") else None
    )
    if not title or not company or not authors or output is None:
        parser.error(
            "--output, --title, --company, and at least one --author "
            "(or a --json file providing them) are required"
        )

    def _opt_path(cli_value, key):
        if cli_value is not None:
            return cli_value
        raw = payload.get(key)
        return Path(raw) if raw else None

    result = fill_copyright_form(
        args.template,
        output,
        title=title,
        authors=authors,
        company=company,
        presenter=presenter,
        paper_id=paper_id,
        date_signed=date_signed,
        authorized_signer=authorized_signer,
        speaker_consent=speaker_consent,
        author_signature=_opt_path(args.author_signature, "author_signature"),
        speaker_signature=_opt_path(
            args.speaker_signature, "speaker_signature"
        ),
        employer_signature=_opt_path(
            args.employer_signature, "employer_signature"
        ),
    )
    print(json.dumps(result, indent=2))
    if result["unsigned"]:
        print(
            "Note: signature widgets were left blank. Open the PDF in "
            "Acrobat (or print, wet-sign, and scan) before uploading.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
