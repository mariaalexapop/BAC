#!/bin/bash
# Sync local SQLite database to Turso
# Usage: ./scripts/sync-to-turso.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$SCRIPT_DIR/../../data/questions.db"

echo "Exporting local database..."
/usr/bin/python3 << PYEOF
import sqlite3, os, subprocess

db_path = "$DB_PATH"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schemas with proper quoting
schemas = {}
for table in ["tests", "questions"]:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
    row = cursor.fetchone()
    if row and row[0]:
        schemas[table] = row[0]

# Build schema SQL with proper quoting for Turso
schema_sql = ["PRAGMA foreign_keys=OFF;", ""]

# Use explicit CREATE TABLE statements with all columns quoted
schema_sql.append('DROP TABLE IF EXISTS "questions";')
schema_sql.append('DROP TABLE IF EXISTS "tests";')
schema_sql.append("")

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='tests'")
schema_sql.append(cursor.fetchone()[0] + ";")
schema_sql.append("")

# Rebuild questions schema with all columns properly quoted
cursor.execute("PRAGMA table_info(questions)")
cols = cursor.fetchall()
col_defs = []
for col in cols:
    cid, name, ctype, notnull, default_val, pk = col
    parts = [f'"{name}"', ctype or "TEXT"]
    if notnull:
        parts.append("NOT NULL")
    if default_val is not None:
        parts.append(f"DEFAULT {default_val}")
    if pk:
        parts.append("PRIMARY KEY")
    col_defs.append("    " + " ".join(parts))

col_defs.append('    CONSTRAINT "questions_test_id_fkey" FOREIGN KEY ("test_id") REFERENCES "tests" ("id") ON DELETE RESTRICT ON UPDATE CASCADE')
schema_sql.append('CREATE TABLE "questions" (')
schema_sql.append(",\n".join(col_defs))
schema_sql.append(");")
schema_sql.append("")

# Write schema
with open("/tmp/turso_schema.sql", "w") as f:
    f.write("\n".join(schema_sql))

# Upload schema
result = subprocess.run(["turso", "db", "shell", "bac-bio"],
    stdin=open("/tmp/turso_schema.sql"), capture_output=True, text=True, timeout=30)
if result.returncode != 0:
    print(f"Schema failed: {result.stderr[:300]}")
    exit(1)
print("Schema uploaded")

# Upload data in batches
for table in ["tests", "questions"]:
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    batch_size = 30
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        sql_lines = []
        for row in batch:
            vals = []
            for v in row:
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            sql_lines.append(f'INSERT INTO "{table}" VALUES({",".join(vals)});')
        chunk_path = f"/tmp/turso_batch_{table}_{i}.sql"
        with open(chunk_path, "w") as f:
            f.write("\n".join(sql_lines))
        result = subprocess.run(["turso", "db", "shell", "bac-bio"],
            stdin=open(chunk_path), capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Batch {table} {i} failed: {result.stderr[:200]}")
            exit(1)
    print(f"Uploaded {len(rows)} {table} rows")

# Cleanup
import glob
for f in glob.glob("/tmp/turso_batch_*.sql") + ["/tmp/turso_schema.sql"]:
    os.remove(f)

print("Sync complete!")
PYEOF
