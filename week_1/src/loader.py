import json
import sqlite3
from pathlib import Path

def load_all_jsons(input_dir: str, output_dir: str):
    print("🥇 Gold: Starting database loading...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    db_path = Path(output_dir) / "jobs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            source_id TEXT PRIMARY KEY,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT NOT NULL,
            tech_stack TEXT
        )
    """)
    conn.commit()

    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print("\n📊 Gold Summary:\nTotal: 0 | Inserted: 0 | Skipped: 0")
        conn.close()
        return

    json_files = sorted([f for f in input_path.iterdir() if f.suffix.lower() == '.json'])
    
    total_count = len(json_files)
    inserted_count = 0
    skipped_count = 0

    if total_count == 0:
        print("\n📊 Gold Summary:\nTotal: 0 | Inserted: 0 | Skipped: 0")
        conn.close()
        return

    for file_path in json_files:
        filename = file_path.name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Using INSERT OR IGNORE enforces warehouse idempotency. 
            # If source_id already exists, SQLite safely skips it without raising an error.
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
                VALUES (?, ?, ?, ?)
            """, (data["source_id"], data["job_title"], data["company"], data["description"]))
            
            # Check rowcount to determine if database changed or ignored the record
            if cursor.rowcount > 0:
                print(f"✅ Inserted: {filename}")
                inserted_count += 1
            else:
                print(f"⏭️ Skipped (duplicate): {filename}")
                skipped_count += 1
                
        except Exception:
            print(f"⚠️ Failed to load: {filename}")
            skipped_count += 1

    conn.commit()
    conn.close()

    print("\n📊 Gold Summary:")
    print(f"Total: {total_count} | Inserted: {inserted_count} | Skipped: {skipped_count}")