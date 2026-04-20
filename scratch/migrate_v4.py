import sqlite3
import os

db_path = "cfy_exp.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Migrating table 'experiment_data' (V4)...")
    try:
        cursor.execute("ALTER TABLE experiment_data ADD COLUMN notes VARCHAR(1000)")
        print("- Added 'notes' column to experiment_data")
    except sqlite3.OperationalError:
        print("- 'notes' column already exists")

    conn.commit()
    conn.close()
    print("Migration V4 completed successfully.")

if __name__ == "__main__":
    migrate()
