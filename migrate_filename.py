import sqlite3
import os

db_path = "matchlearn.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE resumes ADD COLUMN filename VARCHAR;")
    conn.commit()
    print("Migration successful: Added filename to resumes.")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("Column filename already exists.")
    else:
        print(f"Migration failed: {e}")
finally:
    conn.close()
