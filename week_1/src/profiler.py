import logging
import re
import sqlite3
from pathlib import Path

from src.utils import load_sql

logger = logging.getLogger(__name__)


def _calculate_quality(job_title: str, company: str, description: str) -> str:
    if not job_title or not company or not description:
        return "LOW"
    
    if len(description) < 100:
        return "LOW"
    
    special_char_count = len(re.findall(r'[!#@$%^&*()+=\[\]{};:\'",<>?/\\|`~]', description))
    total_chars = len(description)
    if special_char_count / total_chars > 0.1:
        return "LOW"
    
    return "HIGH"

def run_data_profile(db_path: str):
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        query = load_sql("create_jobs_quarantine_table")
        cursor.execute(query)
        
        query = load_sql("label_jobs_quality")
        cursor.execute(query)
        records = cursor.fetchall()
        for source_id, job_title, company, description in records:
            quality = _calculate_quality(job_title, company, description)
            query = load_sql("update_job_quality")
            cursor.execute(query, (quality, source_id))
        conn.commit()
        
        query = load_sql("move_low_quality_to_quarantine")
        cursor.execute(query)
        query = load_sql("delete_low_quality_jobs")
        cursor.execute(query)
        conn.commit()
        logger.info("Quality labeling and quarantine complete")
        
        query = load_sql("count_total_jobs")
        cursor.execute(query)
        total_records = cursor.fetchone()[0]

        if total_records == 0:
            print("--- 🔍 DATA QUALITY REPORT ---")
            print("📈 Total Records: 0")
            print("❓ Missing Values -> job_title: 0, company: 0, description: 0")
            print("📝 Avg Description Length: 0 chars")
            print("⚠️ Shortest Description: 0 chars\n   ↳ source_id: N/A | job_title: N/A")
            print("🚨 Longest Description: 0 chars\n   ↳ source_id: N/A | job_title: N/A")
            conn.close()
            return

        query = load_sql("count_missing_values_jobs")
        cursor.execute(query)
        missing_title, missing_company, missing_desc = cursor.fetchone()
        
        missing_title = missing_title or 0
        missing_company = missing_company or 0
        missing_desc = missing_desc or 0

        query = load_sql("average_description_length_jobs")
        cursor.execute(query)
        avg_desc_len = int(round(cursor.fetchone()[0] or 0))

        query = load_sql("shortest_description_job")
        cursor.execute(query)
        short_id, short_title, short_len = cursor.fetchone()

        query = load_sql("longest_description_job")
        cursor.execute(query)
        long_id, long_title, long_len = cursor.fetchone()

        print("--- 🔍 DATA QUALITY REPORT ---")
        print(f"📈 Total Records: {total_records}")
        print(f"❓ Missing Values -> job_title: {missing_title}, company: {missing_company}, description: {missing_desc}")
        print(f"📝 Avg Description Length: {avg_desc_len} chars")
        print(f"⚠️ Shortest Description: {short_len} chars")
        print(f"   ↳ source_id: {short_id} | job_title: {short_title}")
        print(f"🚨 Longest Description: {long_len} chars")
        print(f"   ↳ source_id: {long_id} | job_title: {long_title}")
        
        query = load_sql("count_quarantine_records")
        cursor.execute(query)
        quarantine_count = cursor.fetchone()[0]
        
        if quarantine_count > 0:
            print("\n--- ⚠️ QUARANTINED RECORDS (LOW QUALITY) ---")
            print(f"🚫 Total LOW Quality: {quarantine_count}")
            
            query = load_sql("count_missing_values_quarantine")
            cursor.execute(query)
            q_missing_title, q_missing_company, q_missing_desc = cursor.fetchone()
            q_missing_title = q_missing_title or 0
            q_missing_company = q_missing_company or 0
            q_missing_desc = q_missing_desc or 0
            
            print(f"❓ Missing Values -> job_title: {q_missing_title}, company: {q_missing_company}, description: {q_missing_desc}")
            
            query = load_sql("average_description_length_quarantine")
            cursor.execute(query)
            q_avg_desc_len = int(round(cursor.fetchone()[0] or 0))
            print(f"📝 Avg Description Length: {q_avg_desc_len} chars")

    except sqlite3.OperationalError as e:
        logger.error(f"Table validation failure: {str(e)}")
    finally:
        conn.close()
