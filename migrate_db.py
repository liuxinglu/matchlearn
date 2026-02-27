import sqlite3
import os

db_path = "matchlearn.db" # Adjusted path since we are running from root
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE gap_analyses ADD COLUMN resume_id INTEGER REFERENCES resumes(id);")
    conn.commit()
    print("Migration successful: Added resume_id to gap_analyses.")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("Column resume_id already exists.")
    else:
        print(f"Migration failed: {e}")
finally:
    conn.close()
