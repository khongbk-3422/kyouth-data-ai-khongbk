import sqlite3
from pathlib import Path

from src.sql import load_sql

def run_data_profile(db_path: str):
    """
    Connects to the database and generates data metrics to audit data quality.
    """
    db_file = Path(db_path)
    
    # Program Idempotency Check: Don't crash if database doesn't exist
    if not db_file.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # 1. Total records count
        cursor.execute(load_sql("queries/count_jobs.sql"))
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

        # 2. Count missing or NULL entries across core dimensions
        cursor.execute(load_sql("queries/count_missing_values.sql"))
        missing_title, missing_company, missing_desc = cursor.fetchone()
        
        # Guard against None responses from an empty table aggregate evaluation
        missing_title = missing_title or 0
        missing_company = missing_company or 0
        missing_desc = missing_desc or 0

        # 3. Calculate average length of job description string fields
        cursor.execute(load_sql("queries/avg_description_length.sql"))
        avg_desc_len = int(round(cursor.fetchone()[0] or 0))

        # 4. Extract shortest description with its contextual identification metrics
        cursor.execute(load_sql("queries/shortest_description.sql"))
        short_id, short_title, short_len = cursor.fetchone()

        # 5. Extract longest description with its contextual identification metrics
        cursor.execute(load_sql("queries/longest_description.sql"))
        long_id, long_title, long_len = cursor.fetchone()

        # Print metrics report exactly matching the requested format specifications
        print("--- 🔍 DATA QUALITY REPORT ---")
        print(f"📈 Total Records: {total_records}")
        print(f"❓ Missing Values -> job_title: {missing_title}, company: {missing_company}, description: {missing_desc}")
        print(f"📝 Avg Description Length: {avg_desc_len} chars")
        print(f"⚠️ Shortest Description: {short_len} chars")
        print(f"   ↳ source_id: {short_id} | job_title: {short_title}")
        print(f"🚨 Longest Description: {long_len} chars")
        print(f"   ↳ source_id: {long_id} | job_title: {long_title}")

    except sqlite3.OperationalError as e:
        # Gracefully handle situations where table structure doesn't exist inside db file
        print(f"❌ Table validation failure: {str(e)}")
    finally:
        conn.close()
