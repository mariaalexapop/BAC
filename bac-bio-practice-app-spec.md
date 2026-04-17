# Bacalaureat Biology Practice App — Build Specification

## 1. Goal

Build a web application that lets a single student practice for the Romanian Bacalaureat biology exam using an existing library of past practice tests and their official answer keys (*bareme*). The student picks which subject to drill — **Subiectul I**, **Subiectul II**, or **Subiectul III** — and the app serves randomised questions drawn from across all available tests. When an answer is wrong, the app shows the official correct answer from the barem plus an AI-generated explanation of the mistake, targeted at helping the student score as high as possible on the real exam.

The library of tests is fixed and provided up front. The user never uploads anything.

## 2. Scope (what's in, what's not)

**In scope**
- One-time ingestion pipeline that parses every test + barem pair into a structured question database
- Web app with subject picker, question player, and answer feedback
- Randomisation with anti-repetition (don't re-serve recently-seen questions)
- AI-generated explanations of wrong answers, grounded in the barem
- Single-user app — no accounts, no auth

**Out of scope**
- User-uploaded tests (the library is fixed)
- Multiplayer, leaderboards, social features
- Timed mock exams that mimic the real 3-hour sitting (can be a later addition)
- Mobile-native app (responsive web is enough)

## 3. Recommended Stack

| Layer | Choice | Why |
|---|---|---|
| Ingestion | Python 3.11 + `pdfplumber` (text PDFs) + `pytesseract` / `ocrmypdf` (scanned PDFs) + `python-docx` | Best ecosystem for messy PDF parsing; Romanian OCR works well with Tesseract's `ron` language pack |
| LLM calls | Anthropic Claude API (`claude-sonnet-4-5` or similar) for parsing assistance and for runtime explanations | Needed for the two hardest tasks: aligning questions to barem entries, and generating explanations |
| Database | SQLite (file: `data/questions.db`) | Zero setup, portable, plenty fast for a single-user app with a few thousand questions. Upgrade to Postgres only if this ever goes multi-user. |
| Web app | Next.js 14 (App Router) + TypeScript + Tailwind | One codebase for API routes and UI; easy local dev (`npm run dev`) and easy deploy (Vercel, or a single Docker container) |
| ORM | Prisma | Typed queries against SQLite, painless migrations |

If you'd rather keep it dead simple: **Flask + vanilla HTML** also works. The spec below is stack-agnostic past Section 5.

## 4. Source Material — What the Input Looks Like

The provided folder contains pairs of files. Pairing rules:

- A **test file** has `test` somewhere in the filename (e.g. `test_model_2023_var3.pdf`)
- Its matching **barem file** has `barem` in the filename and shares the same identifying stem (e.g. `barem_model_2023_var3.pdf`)
- Files may be PDF or DOCX. Some PDFs are text-based; some are scans and need OCR.
- Each test contains three sections labelled **Subiectul I**, **Subiectul II**, and **Subiectul III**, each worth 30 points (plus 10 points *din oficiu*).
- Subiectul I is typically short-answer / fill-in / true-false / matching. Subiectul II and III contain longer structured questions, often broken into sub-points (a, b, c, d).
- The barem gives the accepted answer(s) and point allocation for each sub-point.

The ingestion pipeline must handle all of these variants.

## 5. Data Model

Use these tables. Field names are illustrative — adjust to your ORM's conventions.

### `tests`
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | e.g. `model_2023_var3` (derived from filename stem) |
| `source_file` | text | Path to the test file |
| `barem_file` | text | Path to the barem file |
| `year` | int nullable | Parsed from filename if possible |
| `ingested_at` | datetime | |

### `questions`
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | e.g. `model_2023_var3__subI__A__1` |
| `test_id` | text FK | → `tests.id` |
| `subject` | enum | `I` \| `II` \| `III` |
| `part_label` | text nullable | e.g. `A`, `B` — some subjects have lettered parts |
| `number` | text | e.g. `1`, `2a`, `4d` — keep as text because of sub-letters |
| `prompt` | text | The full question text as presented to the student |
| `context` | text nullable | Any preamble shared with sibling questions (a reading passage, a diagram caption, etc.) |
| `question_type` | enum | `short_answer` \| `fill_blank` \| `true_false` \| `matching` \| `multi_part` \| `essay` |
| `points` | int | From the barem |
| `barem_answer` | text | The canonical correct answer, verbatim from the barem |
| `barem_notes` | text nullable | Any grading notes ("se acceptă orice formulare echivalentă", partial credit rules, etc.) |
| `image_refs` | json nullable | Array of paths to cropped images if the question references a figure |

### `attempts` (for anti-repetition + light stats)
| Field | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `question_id` | text FK | |
| `shown_at` | datetime | |
| `was_correct` | bool nullable | null if the user skipped |
| `user_answer` | text nullable | |

Single-user app, so no `user_id` is needed. If you ever add users, add it here.

## 6. Ingestion Pipeline

This is the hard part. Build it as a standalone CLI: `python ingest.py --source ./tests_folder`.

### 6.1 File discovery and pairing
1. Walk the source folder. For each file, classify as `test` or `barem` by filename substring.
2. Build pairs by stripping `test`/`barem` from the stem and matching the remainder. Warn on unpaired files and skip them.

### 6.2 Text extraction
1. Try `pdfplumber` first. If the extracted text is empty or clearly garbage (e.g. < 100 characters for a multi-page file), fall back to OCR via `ocrmypdf` with `--language ron`.
2. For `.docx`, use `python-docx`.
3. Preserve page breaks and, where possible, the original layout — barem parsing relies on numbering staying intact.

### 6.3 Segmentation
Split each test into Subiectul I / II / III. These headers are reliable anchors in Romanian Bac papers. Within each subject, split into individual questions by their numbering (`1.`, `2.`, `A.`, etc.). Do the same for the barem.

### 6.4 Question ↔ barem alignment
This is where a generic regex-only approach will fail on you. Use this hybrid:
1. First pass: deterministic alignment by `(subject, part_label, number)` keys extracted from both documents.
2. Second pass: for any question where alignment is ambiguous or missing, send the question text + the full barem section for that subject to Claude with a prompt like: *"Given this question and this barem, return the exact barem entry that answers it, verbatim, as JSON."* This handles the cases where numbering drifts or the barem groups answers differently from the test.
3. Flag anything Claude can't confidently align into a `needs_review.json` file. Do not silently drop questions.

### 6.5 Question typing
Classify each question into one of the `question_type` enum values with a small rule set + Claude fallback. The type drives the UI (a true/false question should render as two buttons, not a text box).

### 6.6 Image handling
If a question references a figure ("în figura alăturată…"), extract the corresponding image region from the PDF page (pdfplumber can give you page images; crop by bounding box or just save the full page as a fallback) and store the path in `image_refs`. The web app will display it above the prompt.

### 6.7 Idempotency
Running the pipeline twice on the same folder should be a no-op. Key everything by `test_id` + question number.

## 7. Web App

### 7.1 Routes
- `GET /` — landing page with three big buttons: "Subiectul I", "Subiectul II", "Subiectul III", plus a small "practică mixtă" option that samples from all three.
- `GET /practice/[subject]` — the practice session UI.
- `POST /api/next-question` — body: `{ subject }`. Returns one randomised question (see §7.3 for the randomisation rules). Never returns the barem answer.
- `POST /api/submit-answer` — body: `{ question_id, user_answer }`. Returns `{ is_correct, barem_answer, explanation, points }`.

### 7.2 Practice UI
- Shows the question prompt, any context/passage, and any image.
- Input field type depends on `question_type`:
  - `true_false` → two buttons
  - `short_answer` / `fill_blank` → single-line input
  - `multi_part` / `essay` → multi-line textarea with visible sub-part labels (a, b, c, d) so the student structures their answer the way the barem expects
  - `matching` → pairs of dropdowns, or a drag-and-drop if you're feeling fancy
- After submit: show a clear ✓ / ✗, the barem answer verbatim, and the AI explanation (see §7.4). Then a "Next question" button.
- Keyboard shortcut: Enter submits, Space goes to next question.

### 7.3 Randomisation with anti-repetition
When `/api/next-question` is called:
1. Get all questions in the requested subject.
2. Exclude questions shown in the last N attempts, where N = `min(50, total_questions * 0.3)`. This guarantees variety without starving the pool if it's small.
3. Weight the remaining questions so ones never attempted (or attempted least recently) are more likely to surface. A simple approach: sort by `(times_seen ASC, last_seen_at ASC NULLS FIRST)`, then pick uniformly from the top third.
4. Record the selection in `attempts` immediately, even before the user answers, so reloading the page won't re-serve the same question.

### 7.4 Correctness judging + explanation
Judging a free-text Romanian biology answer against a barem is not a string-equality problem. Use Claude for this too.

Prompt shape (send as a single API call on `/api/submit-answer`):

> You are grading a Romanian Bacalaureat biology answer. The student is preparing for a high-stakes exam and needs feedback that matches how the official barem awards points.
>
> **Question:** {prompt}
> **Official barem answer:** {barem_answer}
> **Barem grading notes:** {barem_notes}
> **Student's answer:** {user_answer}
>
> Return strict JSON: `{ "is_correct": bool, "points_awarded": number, "explanation": string }`.
>
> `is_correct` is true only if the student's answer would earn full points per the barem. Accept equivalent phrasings — the barem itself often says *"se acceptă orice formulare echivalentă"*. Reject answers that are close but miss a required element (e.g. the barem requires two examples and the student gave one).
>
> The explanation must be in Romanian, must reference the barem directly, and must tell the student specifically what was missing or wrong and how to phrase it correctly next time. Keep it under 120 words.

Parse the JSON response, store the attempt, return to the frontend. If Claude's response fails to parse, fall back to a strict string-similarity check and a generic "compară răspunsul tău cu baremul de mai jos" message — never block the user on a model failure.

### 7.5 Session state
The session is ephemeral — no login. A browser-local session ID (cookie) ties `attempts` rows together so anti-repetition works per-browser. Clearing cookies resets the pool.

## 8. Project Layout

```
bac-bio-practice/
  ingest/
    __init__.py
    pair_files.py
    extract_text.py
    segment.py
    align_barem.py
    classify.py
    extract_images.py
    cli.py                 # entrypoint: python -m ingest.cli
  data/
    source/                # the provided test + barem files go here
    images/                # extracted figure crops
    questions.db           # SQLite file
    needs_review.json      # alignment failures for manual fixup
  web/
    app/
      page.tsx             # landing page
      practice/[subject]/page.tsx
      api/next-question/route.ts
      api/submit-answer/route.ts
    lib/
      db.ts                # Prisma client
      claude.ts            # Anthropic SDK wrapper
      randomize.ts         # §7.3 logic
    prisma/schema.prisma
    package.json
  README.md
  .env.example             # ANTHROPIC_API_KEY=...
```

## 9. Environment & Secrets
- `ANTHROPIC_API_KEY` — required for both ingestion (alignment fallback) and runtime (grading + explanations).
- `DATABASE_URL` — points at `data/questions.db` by default.
- No other secrets.

## 10. Build Order (so the engineer isn't blocked)

1. **Stand up the schema and an empty web app first.** Seed it with 3–5 hand-written questions so the UI can be built end-to-end without waiting on ingestion.
2. **Build the practice UI and the submit/grade endpoint** against that seed data. Get the Claude-based grading working and tuned.
3. **Build the ingestion pipeline** and run it against the real library. Expect to iterate 2–3 times on the segmenter and the aligner — Bac papers have enough layout drift between years that you'll find edge cases.
4. **Triage `needs_review.json` manually** for any questions the aligner gave up on. For a library of a few dozen tests, this is usually 10–30 minutes of cleanup.
5. **Tune the randomiser** once there's real data — the anti-repetition thresholds in §7.3 are starting points, not final values.

## 11. Acceptance Criteria

The build is done when all of these are true:

- Running `python -m ingest.cli --source ./data/source` populates `questions.db` with every question from every test/barem pair, with barem answers attached. Unaligned questions land in `needs_review.json` rather than being silently lost.
- Visiting `/` and clicking "Subiectul I" starts a practice session that serves a question from Subiectul I of some test.
- Submitting a correct answer shows a green ✓ and the barem answer; submitting a wrong answer shows a red ✗, the barem answer verbatim, and a Romanian explanation that references the barem and tells the student what to fix.
- Starting a new session after finishing one does not re-serve the questions from the previous session first — variety is visibly higher than random-with-replacement.
- The app runs locally with `npm run dev` plus a running SQLite file, no other services required.

## 12. Topic Filtering

### 12.1 Schema
The `questions` table has a `topic` column (nullable) with values: `sistem_nervos`, `analizatori`, `sistem_endocrin`, `sistem_osos`, `sistem_muscular`, `sistem_digestiv`, `sistem_circulator`, `sistem_respirator`, `sistem_excretor`, `sistem_reproducator`, `genetica`, `ecologie_umana`, `alcatuirea_corpului`, `mixt` (for cross-chapter questions), `altele` (fallback).

### 12.2 Ingestion Pipeline
`ingest/classify.py` includes `classify_topic(question_text, context, barem_answer)` which uses keyword matching on Romanian biology terms (e.g. "neuron", "reflex", "encefal" -> sistem_nervos; "nefron", "urină", "rinichi" -> sistem_excretor; "ADN", "cromozom", "genă" -> genetica). Run `--reclassify-topics` to update topics for existing questions.

### 12.3 API
- `POST /api/next-question` accepts optional `topic` parameter. If specified, filters the question pool to that topic before anti-repetition. If pool < 5 questions, anti-repetition exclusion is skipped.
- `GET /api/topics?subject=<I|II|III|null>` returns available topics with counts: `[{ topic, label, count }]`. Topics with 0 questions for the selected subject are excluded.

### 12.4 UI
The practice page shows topic selector chips above the question area. "Toate capitolele" is selected by default. Each chip shows the question count. Changing topic resets the session counter and fetches a new question.

### 12.5 Acceptance Criteria
- Ingestion populates `topic` for all questions.
- Selecting Subiectul II + "Sistem nervos" returns only nervous system questions from Subject II.
- Topics with 0 questions for a subject don't appear in the selector.
- Anti-repetition works correctly with topic filter applied.
