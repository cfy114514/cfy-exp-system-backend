import sqlite3
import os

db_path = "cfy_exp.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- 升级 users 表 ---
    print("Migrating table 'users'...")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN real_name VARCHAR(50)")
        print("- Added real_name")
    except sqlite3.OperationalError:
        print("- real_name already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255)")
        print("- Added avatar_path")
    except sqlite3.OperationalError:
        print("- avatar_path already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN department VARCHAR(100)")
        print("- Added department")
    except sqlite3.OperationalError:
        print("- department already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        print("- Added is_active")
    except sqlite3.OperationalError:
        print("- is_active already exists")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
        print("- Added created_at")
        # 为现有用户初始化创建时间
        cursor.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")
    except sqlite3.OperationalError:
        print("- created_at already exists")

    conn.commit()
    conn.close()
    print("Migration V3 completed successfully.")

if __name__ == "__main__":
    migrate()
