import sqlite3
import os

db_path = "cfy_exp.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(">>> 开始执行 v2 架构物理迁移...")

    # 1. 给 groups 表增加字段
    try:
        cursor.execute("ALTER TABLE groups ADD COLUMN manager_id INTEGER REFERENCES users(id)")
        print("Successfully added column: groups.manager_id")
    except sqlite3.OperationalError as e:
        print(f"Column groups.manager_id error: {e}")

    try:
        cursor.execute("ALTER TABLE groups ADD COLUMN group_type VARCHAR(20) DEFAULT 'public'")
        print("Successfully added column: groups.group_type")
    except sqlite3.OperationalError as e:
        print(f"Column groups.group_type error: {e}")

    # 2. 创建新表 group_members
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                group_id INTEGER NOT NULL REFERENCES groups(id),
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Successfully created table: group_members")
    except sqlite3.OperationalError as e:
        print(f"Table group_members error: {e}")

    # 3. 创建新表 group_applications
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                group_id INTEGER NOT NULL REFERENCES groups(id),
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Successfully created table: group_applications")
    except sqlite3.OperationalError as e:
        print(f"Table group_applications error: {e}")

    # 4. 数据转换：将旧的 'operator' 角色映射为 'student'
    try:
        cursor.execute("UPDATE users SET role = 'student' WHERE role = 'operator'")
        print(f"Successfully migrated roles: operator -> student (Rows affected: {cursor.rowcount})")
    except sqlite3.OperationalError as e:
        print(f"Role migration error: {e}")

    conn.commit()
    conn.close()
    print("✅ 2.0 架构物理迁移完成。")
