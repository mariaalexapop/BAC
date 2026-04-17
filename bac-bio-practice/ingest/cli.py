"""
CLI entrypoint for the BAC Biology ingestion pipeline.

Usage:
    cd /Users/alexandrapop/BAC/bac_webapp/bac-bio-practice
    source ../venv/bin/activate
    python -m ingest.cli --source ../Test_Bio_cu_bareme

Options:
    --source DIR     Path to directory containing test/barem PDFs
    --db PATH        Path to SQLite database (default: data/questions.db)
    --dry-run        Parse and report without writing to DB
    --verbose        Print detailed output
"""

import argparse
import json
import os
import sqlite3
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .pair_files import discover_pairs
from .extract_text import extract_text
from .segment import segment_test, segment_barem
from .align_barem import align
from .classify import classify_question, classify_topic


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS tests (
    id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    barem_file TEXT NOT NULL,
    year INTEGER,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES tests(id),
    subject TEXT NOT NULL CHECK(subject IN ('I', 'II', 'III')),
    part_label TEXT,
    number TEXT NOT NULL,
    prompt TEXT NOT NULL,
    context TEXT,
    question_type TEXT NOT NULL CHECK(question_type IN ('short_answer', 'fill_blank', 'true_false', 'matching', 'multi_part', 'essay')),
    points INTEGER NOT NULL DEFAULT 0,
    barem_answer TEXT NOT NULL DEFAULT '',
    barem_notes TEXT,
    image_refs TEXT,
    topic TEXT,
    FOREIGN KEY (test_id) REFERENCES tests(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL REFERENCES questions(id),
    session_id TEXT,
    shown_at TEXT NOT NULL DEFAULT (datetime('now')),
    was_correct INTEGER,
    user_answer TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Create the database and tables if they don't exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA)
    # Migrate: add topic column if missing
    cur = conn.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cur.fetchall()]
    if 'topic' not in columns:
        conn.execute("ALTER TABLE questions ADD COLUMN topic TEXT")
    conn.commit()
    return conn


def is_already_ingested(conn: sqlite3.Connection, test_id: str) -> bool:
    """Check if a test has already been ingested."""
    cur = conn.execute("SELECT 1 FROM tests WHERE id = ?", (test_id,))
    return cur.fetchone() is not None


def make_question_id(test_id: str, subject: str, part_label: str, number: str) -> str:
    """Generate a deterministic question ID."""
    raw = f"{test_id}|{subject}|{part_label or ''}|{number}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def ingest_pair(
    conn: sqlite3.Connection,
    pair: Dict,
    verbose: bool = False,
    dry_run: bool = False,
) -> Dict:
    """
    Process a single test/barem pair.

    Returns a stats dict: {'questions': N, 'unaligned': N, 'skipped': bool}
    """
    test_id = pair['test_id']

    if not dry_run and is_already_ingested(conn, test_id):
        if verbose:
            print(f"  [skip] Already ingested: {test_id}")
        return {'questions': 0, 'unaligned': 0, 'skipped': True}

    # Extract text
    try:
        test_text = extract_text(pair['test_file'])
    except Exception as e:
        print(f"  [error] Failed to extract test text: {e}", file=sys.stderr)
        return {'questions': 0, 'unaligned': 0, 'skipped': True, 'error': str(e)}

    try:
        barem_text = extract_text(pair['barem_file'])
    except Exception as e:
        print(f"  [error] Failed to extract barem text: {e}", file=sys.stderr)
        return {'questions': 0, 'unaligned': 0, 'skipped': True, 'error': str(e)}

    # Segment
    test_questions = segment_test(test_text)
    barem_entries = segment_barem(barem_text)

    if verbose:
        print(f"  Parsed {len(test_questions)} questions, {len(barem_entries)} barem entries")

    # Align
    aligned, unaligned = align(test_questions, barem_entries)

    # Classify type and topic
    for q in aligned:
        q['question_type'] = classify_question(q)
        q['topic'] = classify_topic(
            q.get('prompt', ''),
            q.get('context'),
            q.get('barem_answer'),
        )

    for q in unaligned:
        q['question_type'] = classify_question(q)
        q['topic'] = classify_topic(
            q.get('prompt', ''),
            q.get('context'),
            q.get('barem_answer'),
        )

    if dry_run:
        if verbose:
            print(f"  [dry-run] Would insert {len(aligned)} questions, {len(unaligned)} unaligned")
        return {
            'questions': len(aligned),
            'unaligned': len(unaligned),
            'skipped': False,
            'unaligned_items': unaligned,
        }

    # Insert into DB
    conn.execute(
        "INSERT INTO tests (id, source_file, barem_file, year, ingested_at) VALUES (?, ?, ?, ?, ?)",
        (
            test_id,
            os.path.basename(pair['test_file']),
            os.path.basename(pair['barem_file']),
            pair.get('year'),
            datetime.now().isoformat(),
        ),
    )

    for q in aligned:
        q_id = make_question_id(test_id, q['subject'], q.get('part_label'), q['number'])
        conn.execute(
            """INSERT OR IGNORE INTO questions
               (id, test_id, subject, part_label, number, prompt, context,
                question_type, points, barem_answer, barem_notes, image_refs, topic)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                q_id,
                test_id,
                q['subject'],
                q.get('part_label'),
                q['number'],
                q['prompt'],
                q.get('context'),
                q['question_type'],
                q.get('points', 0),
                q.get('barem_answer', ''),
                q.get('barem_notes'),
                None,  # image_refs - future use
                q.get('topic'),
            ),
        )

    conn.commit()

    return {
        'questions': len(aligned),
        'unaligned': len(unaligned),
        'skipped': False,
        'unaligned_items': unaligned,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ingest BAC Biology test PDFs into SQLite database."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to directory containing test/barem PDFs",
    )
    parser.add_argument(
        "--db",
        default="data/questions.db",
        help="Path to SQLite database (default: data/questions.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report without writing to DB",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    parser.add_argument(
        "--reclassify-topics",
        action="store_true",
        help="Re-classify topics for all existing questions (updates in place)",
    )

    args = parser.parse_args()

    # Resolve paths
    source_dir = os.path.abspath(args.source)
    db_path = os.path.abspath(args.db)
    data_dir = os.path.dirname(db_path)

    print(f"Source: {source_dir}")
    print(f"Database: {db_path}")

    # Discover pairs
    print("\n--- Discovering test/barem pairs ---")
    pairs = discover_pairs(source_dir)
    print(f"Found {len(pairs)} test/barem pairs.")

    if not pairs:
        print("No pairs found. Exiting.")
        sys.exit(1)

    # Init DB
    conn = None
    if not args.dry_run:
        conn = init_db(db_path)
        print(f"Database initialized at {db_path}")
    else:
        # Still create a temporary in-memory DB for structure validation
        conn = sqlite3.connect(":memory:")
        conn.executescript(DB_SCHEMA)

    # Reclassify topics for existing questions if requested
    if args.reclassify_topics and not args.dry_run:
        print("\n--- Reclassifying topics for existing questions ---")
        cur = conn.execute("SELECT id, prompt, context, barem_answer FROM questions")
        rows = cur.fetchall()
        updated = 0
        for row in rows:
            q_id, prompt, context, barem_answer = row
            topic = classify_topic(prompt or '', context, barem_answer)
            conn.execute("UPDATE questions SET topic = ? WHERE id = ?", (topic, q_id))
            updated += 1
        conn.commit()
        print(f"  Updated topics for {updated} questions.")

        # Print topic distribution
        cur = conn.execute("SELECT topic, COUNT(*) FROM questions GROUP BY topic ORDER BY COUNT(*) DESC")
        print("  Topic distribution:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1]}")

    # Process each pair
    print(f"\n--- Processing {len(pairs)} pairs ---")
    total_questions = 0
    total_unaligned = 0
    total_skipped = 0
    total_errors = 0
    all_unaligned: List[Dict] = []

    for i, pair in enumerate(pairs, 1):
        test_name = os.path.basename(pair['test_file'])
        if args.verbose:
            print(f"\n[{i}/{len(pairs)}] {test_name}")
        else:
            # Progress indicator
            if i % 10 == 0 or i == len(pairs):
                print(f"  Processed {i}/{len(pairs)}...", end='\r')

        try:
            stats = ingest_pair(conn, pair, verbose=args.verbose, dry_run=args.dry_run)
        except Exception as e:
            print(f"\n  [error] {test_name}: {e}", file=sys.stderr)
            total_errors += 1
            continue

        if stats.get('skipped'):
            total_skipped += 1
        else:
            total_questions += stats['questions']
            total_unaligned += stats['unaligned']
            if stats.get('unaligned_items'):
                for uq in stats['unaligned_items']:
                    uq['_source_file'] = test_name
                all_unaligned.extend(stats['unaligned_items'])

    print()  # Clear progress line

    # Write unaligned questions to needs_review.json
    review_path = os.path.join(data_dir, "needs_review.json")
    if all_unaligned:
        os.makedirs(data_dir, exist_ok=True)
        # Make JSON-serializable (strip non-serializable fields)
        serializable = []
        for uq in all_unaligned:
            serializable.append({
                'source_file': uq.get('_source_file', ''),
                'subject': uq.get('subject', ''),
                'part_label': uq.get('part_label', ''),
                'number': uq.get('number', ''),
                'prompt': uq.get('prompt', '')[:200],  # truncate for readability
                'question_type': uq.get('question_type', ''),
            })
        with open(review_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(serializable)} unaligned questions to {review_path}")

    # Summary
    print("\n--- Summary ---")
    print(f"  Pairs found:      {len(pairs)}")
    print(f"  Skipped (exists): {total_skipped}")
    print(f"  Errors:           {total_errors}")
    print(f"  Questions stored: {total_questions}")
    print(f"  Unaligned:        {total_unaligned}")

    if not args.dry_run and conn:
        # Print DB stats
        cur = conn.execute("SELECT COUNT(*) FROM tests")
        print(f"  Total tests in DB:     {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM questions")
        print(f"  Total questions in DB: {cur.fetchone()[0]}")
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
