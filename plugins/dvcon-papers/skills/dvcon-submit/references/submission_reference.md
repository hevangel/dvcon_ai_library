# DVCon U.S. Submission Reference

Source of truth for the Oxford Abstracts DVCon submission forms — primarily the
"Initial Stage - Extended Abstracts" form, with notes on how the later
full-paper stage differs. Field labels, roles, option lists, and dropdown
gotchas are captured here so the skill builds locators from facts, not guesses.

The form is driven with **`playwright-cli`** (a real-browser command-line tool),
not the ZCode in-app browser. `playwright-cli` supports `upload`, so the PDF
upload is fully automatable. See `SKILL.md` Workflow B for the command flow.

> These facts were captured from the live DVCon U.S. 2027 stage (event id 77379,
> Oxford Abstracts stage `81951`). The **form shape is stable across years**;
> only the stage id and the deadline change. Always re-derive the stage id from
> the dvcon.org "Submit Now" link, then `playwright-cli snapshot` the form and
> verify labels against this reference before filling.

## Discovery path

1. `https://dvcon.org/` → top nav **Submission Instructions** → **Call for
   Extended Abstracts** (direct URL:
   `https://dvcon.org/submission-instructions/call-for-extended-abstracts`).
2. On that page, the **Submit Now** button link target is the live Oxford
   Abstracts submitter URL:
   `https://app.oxfordabstracts.com/stages/<STAGE_ID>/submitter`.
3. After sign-in, Oxford Abstracts redirects to the new-submission form:
   `https://app.oxfordabstracts.com/stages/<STAGE_ID>/submissions/new?...`.
   The page header reads
   `Design & Verification Conference & Exhibition <YEAR>: Initial Stage - Extended Abstracts`
   and shows the deadline beneath it.

## Page header context (verify you are on the right form)

- Heading level 1: `Oxford Abstracts logo / DVCon US <YEAR>`
- Subheading: `Design & Verification Conference & Exhibition <YEAR>: Initial Stage - Extended Abstracts`
- `Deadline - Monday, 7th September, 2026` (for DVCon U.S. 2027)
- Intro paragraph mentions it is a **blind submission** and that names /
  affiliations must **not** be in the abstract.

## Form fields (in DOM order)

### 1. Title*  (rich-text editor)

- Label text: `Title*`
- Help text: `Enter the FULL TITLE of your submission. This will be used in the final program.`
- Counter: `0/50` (max **50 words**, NOT characters — verified live on the 2027
  stage: the 47-character, 9-word title "Mining 17 Years of DVCon Papers with
  RAG Agents" moved the counter to `9/50`). Do not needlessly truncate a title
  to 50 characters.
- Editor: contenteditable rich-text region with an italic / subscript /
  superscript / special-characters / clear-formatting toolbar. There is no
  Bold button in the Title editor (only Italic).
- Locating: target the editor's contenteditable body, not a `textbox` role.
  Build the locator from the snapshot after confirming the toolbar labels.

### 2. Short Description*  (rich-text editor)

- Label text: `Short Description*`
- Help text: `Please enter a short description of your paper (max 250 words). This will be used in the final program.`
- Counter: `0/250` (max **250 words**)
- Editor: contenteditable rich-text region with Italic / Bold / Subscript /
  Superscript / Special Characters / Unordered List / Ordered List /
  Clear-formatting toolbar. Fuller toolbar than Title.
- Locating: same contenteditable approach as Title.

### 3. Extended Abstract - Upload*

- Label text: `Extended Abstract - Upload*`
- Help text: `Upload your extended abstract for review here. Please refrain from including any author's name or affiliations in this submission. The abstract should be 600-1200 words or two pages. Please do not submit your full paper.`
- Button: `Choose File (.pdf, .doc, .docx, .txt only)`
- Accepted: `.pdf`, `.doc`, `.docx`, `.txt` (PDF preferred per dvcon.org)
- **Automatable with `playwright-cli upload`,** but the click target matters.
  The snapshot ref labelled `button "file_upload Choose File (...)"` actually
  resolves to the **hidden `<input type="file" class="sr-only">`**, and a
  `<label class="mdc-button ... fu-hover">` sits on top of it and intercepts
  pointer events. Clicking the ref therefore fails with
  `<label ...> intercepts pointer events` → timeout, and a following `upload`
  errors with `can only be used when there is related modal state present`.
  **Click the label instead**, then upload the **absolute** path:

  ```bash
  playwright-cli click "label.fu-hover"      # opens the file chooser modal
  playwright-cli upload "C:\path\to\abstract.pdf"
  ```

  A successful click reports `### Modal state - [File chooser]: can be handled
  by upload`. After the upload the widget re-renders to `Replace file ...` plus
  a `Remove` button, a `Download uploaded file` link, and a poster preview —
  re-`snapshot` and check for those rather than for a filename.
  (File upload is the key reason the skill uses `playwright-cli` instead of the
  ZCode in-app browser, which cannot do file uploads.)

### 4. Authors, Affiliations*

- Section header: `Authors, Affiliations*`
- Section help: `You MUST enter the names of ALL authors here - including yourself if you are an author - in the order in which you wish them to appear in the printed text. Names omitted here will NOT be printed in the author index or the final program.`
- Repeatable blocks. First block is pre-rendered. Use **"+ Add Another Author"**
  for additional authors and **"+ Add Another Affiliation"** for multi-affiliation
  authors. Re-snapshot after each add — inputs are async-rendered.

Per-author block fields:

| Field | Control | Required | Notes |
|-------|---------|----------|-------|
| First Name* | textbox `First Name*` | yes | |
| Last Name* | textbox `Last Name*` | yes | |
| Presenting* | checkbox | yes, for **exactly one** author | Sets who presents; only one author may have this checked |
| Email* | textbox `Email*` | yes | |
| Institution* | textbox/combobox `Institution*` (Affiliation 1) | yes | |
| City* | textbox/combobox `City*` (Affiliation 1) | yes | |
| Country* | dropdown combobox `Country*` (Affiliation 1) | yes | See "Country dropdowns" below |

Presenting-author rule: exactly one author must be the presenter. If the user
specifies more than one or none, ask before continuing.

### 5. Consent checkboxes

Three required checkboxes. All three must be checked. They are attestations —
only check after the user has actually confirmed each fact.

| Label | Text |
|-------|------|
| Permission to publish* | Check this box to give us permission to publish your submission on electronic media and in hardcopy if it is accepted for presentation |
| Author/Speaker approval* | I confirm that this submission has been approved by all authors |
| Author/Speaker will attend* | The presentation format will be either slides or a poster. I confirm that at least one of the listed authors will register in full to attend and present their paper in either format at the conference. Failure to attend the conference will result in the removal of your paper from the proceedings and a block on future submissions to DVCon. |

### 6. Country*  (presenter travel-from)

- Label text: `Country*`
- Help text: `The country the presenter will be traveling from to attend the conference. This may differ from your legal residency.`
- Dropdown. See "Country dropdowns" below for the USA / UAE gotcha.

### 7. Primary Topic*  (dropdown)

- Label text: `Primary Topic*`
- Help text: `Please choose the primary topic that best describe your submission.`
- Dropdown. The 14 topic options use **short labels**, not the long names on
  the dvcon.org homepage. See "Topic dropdown" below.

### 8. Secondary Topic  (optional dropdown)

- Label text: `Secondary Topic`
- Help text: `Please choose an optional secondary topic for your submission.`
- Same 14 options as Primary Topic. Optional.

### 9. Submit button

- Button text: `Submit`
- Drive with `playwright-cli click "<submit_ref>"`.
- Only click after explicit user confirmation (see SKILL.md Workflow B step B.6).
  Submission is a hard-to-reverse outward action.

## Full-paper stage differences

The above describes the **Initial Stage - Extended Abstracts** form. When the
user returns to submit the **full paper** after preliminary acceptance, the
Oxford Abstracts stage is different (a new stage id, reached from the user's
submission dashboard, not the abstract "Submit Now" link). Key differences:

- **Author info is included in the PDF.** The full paper is NOT double-blind, so
  do not apply the abstract converter's `## Authors` drop. See SKILL.md's
  "Full-paper conversion caveat".
- **Page limit is 6–8 pages**, not 600–1200 words.
- **A signed copyright form (PDF)** must also be uploaded before the final
  deadline, via the submission page's Upload File link. The form must be filled
  with the paper Title + all author names + paper ID, then signed.
- The form fields (Title, Short Description, Authors, Topics, consents) are
  largely the same; re-`snapshot` to confirm exact labels for the target stage,
  since the stage id and some field wording differ.

## Topic dropdown

The Primary/Secondary Topic dropdown uses these **14 short option labels**
exactly. Match these strings in `selectOption(...)`, not the long homepage
names:

| Dropdown label | dvcon.org homepage topic name |
|----------------|-------------------------------|
| `Analog` | Mixed-Signal and AMS Verification |
| `CDC/RDC` | Clocking, Timing, and CDC/RDC Verification |
| `Coverage` | Coverage Strategies and Optimization |
| `CPU Verification` | Processor and Custom Architecture Verification |
| `Formal/Assertions` | Formal and Assertion-based Verification |
| `FPGA Prototyping` | FPGA Prototyping for Verification Acceleration |
| `Functional Safety` | Functional Safety and Compliance |
| `Low-Power` | Low Power Design and Verification |
| `Modern Testbench Architecture` | Modern Testbench Architecture and Language Integration |
| `Regression/Integration` | Regression Management, CI/CD in Verification Workflows |
| `Requirements` | Requirements Traceability and Spec Linking |
| `Security` | Security Verification and Trust in Hardware |
| `System Emulation` | Emulation and System-Level Validation |
| `VIP` | Verification Intellectual Property |

The form also renders a **"Descriptions of topics"** section under the dropdowns
that maps short labels to long descriptions — useful if the user is unsure which
topic fits.

## Country dropdowns

The form has **two** country dropdowns and they use slightly different option
labels:

1. **Affiliation Country** (per affiliation, under each author). This dropdown
   uses these non-standard labels worth noting:
   - `USA` (not "United States")
   - `UAE` (not "United Arab Emirates")
   - `UK` is not present as a short form — use `United Kingdom`
   - `Korea, Republic of` (South Korea), `Korea, Democratic People's Republic of` (North)
   - `Russian Federation`, `Iran, Islamic Republic of`, `Syrian Arab Republic`,
     `Vietnam`, `Taiwan`
2. **Presenter Country** (single, top-level "Country*" field near the bottom).
   This dropdown uses more naturalized labels:
   - `United States` (not "USA")
   - `United Arab Emirates` (not "UAE")
   - `United Kingdom`
   - `Korea (South)`, `Korea (North)`
   - `Russia`, `Iran`, `Syria`, `Vietnam`, `Taiwan`

When calling `selectOption(...)`, use the label that matches the **specific**
dropdown you are targeting. If `selectOption("USA")` fails on the presenter
country, the presenter dropdown probably wants `United States`. Always verify
the exact option label via a fresh snapshot before selecting.

## Rich-text editor notes

The Title and Short Description are **contenteditable rich-text regions**, not
`<input>` or `<textarea>`. With `playwright-cli`:

- Run `playwright-cli snapshot` and read the element **ref** for the editor's
  contenteditable body (it is exposed as a region, not always a textbox role).
- Use `playwright-cli fill "<ref>" "<text>"` to set the whole value at once. If
  `fill` is rejected on the contenteditable, fall back to
  `playwright-cli click "<ref>"` then `playwright-cli type "<text>"` to enter
  text character-by-character. The Title counter (`0/50`) and Short Description
  counter (`0/250`) update as you type — use them to verify the value landed.
- The Title editor has no Bold button; the Short Description editor does. If you
  see a Bold button, you are in Short Description, not Title.

## After submit

On successful submission, Oxford Abstracts shows a confirmation and the
submission appears under the user's dashboard. Remind the user of the next DVCon
milestones (from the dvcon.org Important Dates for DVCon U.S. 2027; re-verify
the exact dates for the target year):

- Abstract submission deadline: **Sep 7, 2026**
- Abstract preliminary accept/reject notification: **Oct 1, 2026**
- Draft paper submission deadline: **Nov 1, 2026**
- Paper preliminary accept/reject notification: **Dec 1, 2026**
- Final paper + author registration + copyright form deadline: **Dec 23, 2026**
- Paper final accept/reject notification: **Jan 14, 2027**
- Final poster/slide/video deadline: **Feb 7, 2027**
- Conference: **March 1–4, 2027**, Santa Clara, CA

The copyright form (PDF) must be uploaded via the Upload File link on the
submission page **by Dec 23, 2026** — filled with Title + all author names +
paper ID, signed. Without it the paper cannot be included in the proceedings.
