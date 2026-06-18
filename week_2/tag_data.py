import sqlite3
import sys
import time
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables (GOOGLE_API_KEY)
load_dotenv()

def tag_data(db_url: str):
    """
    Reads job descriptions from a SQLite database, extracts tech stacks using Gemini,
    and updates the database in batches.
    """
    start_time = time.time()
    total_tokens = 0
    
    # --- Rate Limit Formulas & Justification ---
    # Max Gemini Free RPM = 15. 
    # Safe Target = 1 request every 5 seconds.
    BATCH_SIZE = 5  
    INTER_BATCH_DELAY = 5 
    MAX_RETRIES = 3
    RETRY_WAIT = 5 # Wait time if a 503 Server Error occurs
    
    try:
        # 1. Connect to Database
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        
        # Ensure the tech_stack column exists (failsafe)
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN tech_stack TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        # Fetch rows that need tagging
        # Note: Adjust 'id' and 'description' if your column names differ
        cursor.execute("SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''")
        rows = cursor.fetchall()
        
        if not rows:
            print("No data to tag")
            elapsed = (time.time() - start_time) * 1000
            print(f"Total tokens used: {total_tokens}, took {elapsed:.3f}ms")
            return total_tokens, elapsed
            
        # Initialize Gemini Client
        client = genai.Client()
        
        # 2. Batch Processing
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            
            # --- Bonus: Token & Time Optimization ---
            # Truncating descriptions to 1000 chars removes redundant corporate fluff, 
            # significantly reducing input tokens while keeping core technical keywords.
            prompt_data = {str(row[0]): row[1][:1000] for row in batch} 
            
            prompt = (
                "Extract technical stacks from the following job descriptions. "
                "Return strictly a JSON object where keys are the job IDs and values "
                "are comma-separated strings of the tech stack.\n"
                f"{json.dumps(prompt_data)}"
            )
            
            success = False
            attempts = 0
            
            while not success and attempts < MAX_RETRIES:
                try:
                    attempts += 1
                    
                    # Call Gemini, enforcing JSON output to prevent text-parsing errors
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    
                    # Accumulate token usage (Bonus)
                    if response.usage_metadata:
                        total_tokens += response.usage_metadata.total_token_count
                    else:
                        # Fallback calculation if metadata is missing (Assume 1 word = 1.3 tokens roughly, 
                        # or assignment fallback of 4 tokens per word)
                        total_tokens += len(prompt.split()) * 4
                        
                    # Parse the JSON response
                    extracted_tags = json.loads(response.text)
                    
                    # 3. Update Database using Batch Execution
                    update_payload = []
                    for job_id, tech_stack in extracted_tags.items():
                        update_payload.append((tech_stack, str(job_id)))
                        # Log to standard output as required
                        print(f"Analyzed Job {job_id}: {tech_stack}")
                        
                    cursor.executemany("UPDATE jobs SET tech_stack = ? WHERE source_id = ?", update_payload)
                    conn.commit()
                    success = True
                    
                    # Pause to respect the 15 RPM rate limit
                    time.sleep(INTER_BATCH_DELAY)
                    
                except Exception as e:
                    # Gracefully handle 503s or parsing errors
                    if attempts == MAX_RETRIES:
                        print(f"[Batch {i//BATCH_SIZE}] Failed after {MAX_RETRIES} attempts. Error: {str(e)[:100]}...")
                    else:
                        time.sleep(RETRY_WAIT)
                        
        conn.close()
        
        # Final Time and Token calculation
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"Total tokens used: {total_tokens}, took {elapsed_ms:.3f}ms")
        
        return total_tokens, elapsed_ms
        
    except Exception as e:
        # Ultimate fallback to ensure NO stack traces or crashes ever reach the terminal
        print(f"A critical error occurred, but was handled gracefully: {e}")
        return 0, 0.0

if __name__ == "__main__":
    # Point this to your actual database file
    db_path = "data/jobs.db" 
    
    # Ensure the file exists before running
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found. Please ensure it is in the same directory.")
    else:
        tag_data(db_path)