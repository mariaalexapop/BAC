#!/bin/bash
# Sync local SQLite database to Turso
# Usage: ./scripts/sync-to-turso.sh

set -e

DB_PATH="$(dirname "$0")/../../data/questions.db"
DUMP_FILE="/tmp/turso_sync_$$.sql"

echo "Exporting local database..."
/usr/bin/python3 << PYEOF
import sqlite3, os

db_path = os.path.expanduser("$DB_PATH")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

with open("$DUMP_FILE", "w", encoding="utf-8") as f:
    f.write("PRAGMA foreign_keys=OFF;\n\n")
    for table in ["tests", "questions"]:
        f.write(f'DROP TABLE IF EXISTS "{table}";\n')
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        row = cursor.fetchone()
        if row and row[0]:
            f.write(row[0] + ";\n\n")

    for table in ["tests", "questions"]:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        for row in rows:
            vals = []
            for v in row:
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            f.write(f'INSERT INTO "{table}" VALUES({",".join(vals)});\n')
        f.write("\n")

conn.close()
count = cursor.execute("SELECT COUNT(*) FROM questions").fetchone()[0] if False else len(rows)
print(f"Exported {count} questions")
PYEOF

echo "Uploading to Turso in batches..."
/usr/bin/python3 << PYEOF
import subprocess

with open("$DUMP_FILE", "r") as f:
    lines = f.readlines()

# First batch: schema (DROP + CREATE)
schema_lines = []
data_lines = []
for line in lines:
    if line.startswith("INSERT"):
        data_lines.append(line)
    else:
        schema_lines.append(line)

# Upload schema
with open("/tmp/turso_schema.sql", "w") as f:
    f.writelines(schema_lines)
result = subprocess.run(["turso", "db", "shell", "bac-bio"],
    stdin=open("/tmp/turso_schema.sql"), capture_output=True, text=True, timeout=30)
if result.returncode != 0:
    print(f"Schema failed: {result.stderr[:200]}")
    exit(1)
print("Schema uploaded")

# Upload data in batches
batch_size = 30
total = len(data_lines)
for i in range(0, total, batch_size):
    batch = data_lines[i:i+batch_size]
    chunk_path = f"/tmp/turso_batch_{i}.sql"
    with open(chunk_path, "w") as f:
        f.writelines(batch)
    result = subprocess.run(["turso", "db", "shell", "bac-bio"],
        stdin=open(chunk_path), capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"Batch {i} failed: {result.stderr[:200]}")
        exit(1)

print(f"Uploaded {total} rows to Turso")
PYEOF

rm -f "$DUMP_FILE" /tmp/turso_schema.sql /tmp/turso_batch_*.sql
echo "Sync complete!"
