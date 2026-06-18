import sqlite3
import sys
import time
import re
import os
from typing import List, Dict, Tuple
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- PYDANTIC MODELS ---
class SkillGapResult(BaseModel):
    gaps: List[str]
    # Bonus: Return basic statistics (demand count)
    demand_statistics: Dict[str, int]
    # Bonus: Return tokens and time
    total_tokens: int
    time_ms: float

class ResumeExtraction(BaseModel):
    technical_skills: List[str]

# --- HELPER FUNCTIONS ---
def parse_skills(skill_text: str) -> List[str]:
    """
    Parses a string of skills deterministically.
    Rules: Lowercase, split by '/' and ',', EXCEPT for 'A/B testing' and 'CI/CD'.
    """
    if not skill_text:
        return []
    
    text = skill_text.lower()
    
    # Temporarily hide exceptions so they don't get split
    text = text.replace("a/b testing", "ab_testing_placeholder")
    text = text.replace("ci/cd", "cicd_placeholder")
    
    # Split by comma or slash using Regex
    raw_skills = re.split(r'[,/]', text)
    
    cleaned_skills = set() # Use set to remove immediate duplicates
    for s in raw_skills:
        s = s.strip()
        # Restore exceptions
        s = s.replace("ab_testing_placeholder", "a/b testing")
        s = s.replace("cicd_placeholder", "ci/cd")
        
        # Ignore empty strings
        if s:
            cleaned_skills.add(s)
            
    return list(cleaned_skills)

def is_jailbreak_attempt(text: str) -> bool:
    """Bonus: Basic Jailbreak/Prompt Injection detection."""
    suspicious = [
        "ignore previous instructions", "disregard", "bypass", 
        "system prompt", "you are now", "forget all", "developer mode"
    ]
    text_lower = text.lower()
    for phrase in suspicious:
        if phrase in text_lower:
            return True
    return False

# --- MAIN LOGIC ---
def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
    start_time = time.time()
    total_tokens = 0
    
    # --- Rate Limit & Batch Size Justification ---
    # Since we are processing ONE resume at a time in this function, batch size is inherently 1.
    # Retry wait is set to 5 seconds to back off if Google's API throws a 503 error.
    MAX_RETRIES = 3
    RETRY_WAIT = 5 
    
    try:
        # 1. Read Resume (and optimize tokens)
        with open(input_file_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
            
        # Time/Token Optimization: Truncate excessively long resumes (over 3000 chars)
        resume_text = resume_text[:3000]
        
        # Jailbreak Protection
        if is_jailbreak_attempt(resume_text):
            print("[SECURITY WARNING] Potential Prompt Injection detected. Sanitizing input...")
            # Sanitize by drastically strictly stripping the prompt context
            resume_text = "Extract technical skills only from this data: " + re.sub(r'[^a-zA-Z0-9.,/\s]', '', resume_text)

        # 2. Extract Skills from Resume via LLM
        client = genai.Client()
        
        # Enclose in XML tags to sandbox the resume data from the system instructions
        prompt = f"""
        Extract only the hard technical skills (programming languages, frameworks, cloud platforms, tools) from the following resume.
        Ignore soft skills like 'leadership', 'management', and ignore certifications.
        <resume>
        {resume_text}
        </resume>
        """
        
        resume_skills_raw = []
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                attempts += 1
                # Temperature 0 enforces maximum determinism in the LLM response
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ResumeExtraction,
                        temperature=0.0, 
                    ),
                )
                
                if response.usage_metadata:
                    total_tokens += response.usage_metadata.total_token_count
                else:
                    total_tokens += len(prompt.split()) * 4
                    
                import json
                result_dict = json.loads(response.text)
                resume_skills_raw = result_dict.get('technical_skills', [])
                break # Success
            except Exception as e:
                if attempts == MAX_RETRIES:
                    print(f"LLM Extraction failed after 3 attempts: {e}")
                time.sleep(RETRY_WAIT)

        # 3. Read Tagged DB (Time Optimization: Local SQL instead of sending DB to LLM)
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()

        # 4. Deterministic Parsing & Statistics
        db_skills_pool = []
        for row in rows:
            db_skills_pool.extend(parse_skills(row[0]))
            
        resume_parsed = set()
        for skill in resume_skills_raw:
            resume_parsed.update(parse_skills(skill))
            
        # Calculate Frequency/Demand of DB skills
        skill_demand = {}
        for skill in db_skills_pool:
            skill_demand[skill] = skill_demand.get(skill, 0) + 1
            
        # 5. Deterministic Gap Calculation (Pure Math/Set logic)
        db_unique_skills = set(skill_demand.keys())
        
        # Gap = Skills in DB minus Skills in Resume
        gap_set = db_unique_skills - resume_parsed
        
        # Sort alphabetically to ensure absolute deterministic output order
        sorted_gaps = sorted(list(gap_set))
        
        # Compile Stats strictly for the gap skills
        gap_stats = {skill: skill_demand[skill] for skill in sorted_gaps}
        
        # Sort stats by demand (highest first) for practical insights
        gap_stats = dict(sorted(gap_stats.items(), key=lambda item: item[1], reverse=True))

        elapsed_ms = (time.time() - start_time) * 1000

        # Construct Pydantic Response
        result = SkillGapResult(
            gaps=sorted_gaps,
            demand_statistics=gap_stats,
            total_tokens=total_tokens,
            time_ms=elapsed_ms
        )
        
        return result

    except Exception as e:
        # Ultimate fallback for graceful error handling
        print(f"Gracefully handled error: {e}")
        return SkillGapResult(gaps=[], demand_statistics={}, total_tokens=0, time_ms=0.0)

if __name__ == "__main__":
    db_path = "data/jobs.db"
    resume_path = "resources/resume_d3.txt"
    
    if not os.path.exists(db_path) or not os.path.exists(resume_path):
        print("Ensure jobs.db and resume.txt exist in the respective directories.")
        sys.exit(1)
        
    final_result = find_skill_gaps(resume_path, db_path)
    
    print(f"gaps={final_result.gaps} time={final_result.time_ms:.0f} tokens={final_result.total_tokens}")
    
    # Bonus Display
    print("\n--- BONUS: Top 5 Most In-Demand Missing Skills ---")
    top_5 = list(final_result.demand_statistics.items())[:5]
    for skill, count in top_5:
        print(f"Skill: {skill.ljust(20)} | Missing from resume, but required by {count} job(s)")