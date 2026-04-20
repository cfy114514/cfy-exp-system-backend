import sqlite3
import os

db_path = "cfy_exp.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 尝试添加 site_photos_paths
        cursor.execute("ALTER TABLE experiment_data ADD COLUMN site_photos_paths JSON")
        print("Successfully added column: site_photos_paths")
    except sqlite3.OperationalError as e:
        print(f"Column site_photos_paths error: {e}")

    try:
        # 尝试添加 report_pdf_path
        cursor.execute("ALTER TABLE experiment_data ADD COLUMN report_pdf_path VARCHAR(255)")
        print("Successfully added column: report_pdf_path")
    except sqlite3.OperationalError as e:
        print(f"Column report_pdf_path error: {e}")

    try:
        # 顺便检查是否缺失 project_id 和 operator_id (之前的升级)
        cursor.execute("ALTER TABLE experiment_data ADD COLUMN project_id INTEGER")
        print("Successfully added column: project_id")
    except sqlite3.OperationalError as e:
        print(f"Column project_id error: {e}")

    try:
        cursor.execute("ALTER TABLE experiment_data ADD COLUMN operator_id INTEGER")
        print("Successfully added column: operator_id")
    except sqlite3.OperationalError as e:
        print(f"Column operator_id error: {e}")

    conn.commit()
    conn.close()
    print("Database sync complete.")
