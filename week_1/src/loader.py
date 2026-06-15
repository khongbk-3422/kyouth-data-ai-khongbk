import hashlib
import json
import logging
import sqlite3
from pathlib import Path

from src.utils import load_sql

logger = logging.getLogger(__name__)


def _calculate_content_hash(job_title: str, company: str, description: str) -> str:
    hash_input = f"{job_title}|{company}|{description}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def load_all_jsons(input_dir: str, output_dir: str):
    print("🥇 Gold: Starting database loading...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    db_path = Path(output_dir) / "jobs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = load_sql("create_jobs_table")
    cursor.execute(query)
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
            
            content_hash = _calculate_content_hash(
                data["job_title"],
                data["company"],
                data["description"]
            )
                
            query = load_sql("insert_job_record")
            cursor.execute(query, (data["source_id"], data["job_title"], data["company"], data["description"], content_hash))
            
            if cursor.rowcount > 0:
                logger.info(f"Inserted: {filename}")
                inserted_count += 1
            else:
                logger.warning(f"Skipped (duplicate): {filename}")
                skipped_count += 1
                
        except Exception as e:
            logger.error(f"Failed to load: {filename} | Reason: {e}")
            skipped_count += 1

    conn.commit()
    conn.close()

    print("\n📊 Gold Summary:")
    print(f"Total: {total_count} | Inserted: {inserted_count} | Skipped: {skipped_count}")