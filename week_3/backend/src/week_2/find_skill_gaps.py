import sqlite3
import sys
import time
import re
import os
import json
from typing import List, Dict, Tuple
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_MODEL = "gemini-3-flash-preview"
# eval
DB_PATH = "resources_eval/jobs_d3_eval.db"
RESUME_PATH = "resources_eval/resume_d3_eval.txt"

# resources
# DB_PATH = "resources/jobs_d1.db"
# RESUME_PATH = "resources/resume_d1.txt"

class SkillGapResult(BaseModel):
    gaps: List[str]
    demand_statistics: Dict[str, int]
    total_tokens: int
    time_ms: float

class ResumeExtraction(BaseModel):
    technical_skills: List[str]

# --- HELPER FUNCTIONS ---
def parse_skills(skill_text: str) -> List[str]:
    if not skill_text:
        return []
    
    text = skill_text.lower()
    
    text = text.replace("a/b testing", "ab_testing_placeholder")
    text = text.replace("ci/cd", "cicd_placeholder")
    
    raw_skills = re.split(r'[,/]', text)
    
    cleaned_skills = set()
    for s in raw_skills:
        s = s.strip()
        s = s.replace("ab_testing_placeholder", "a/b testing")
        s = s.replace("cicd_placeholder", "ci/cd")
        
        if s:
            cleaned_skills.add(s)
            
    return list(cleaned_skills)

def is_jailbreak_attempt(text: str) -> bool:
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
    
    MAX_RETRIES = 3
    RETRY_WAIT = 5 
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
            
        resume_text = resume_text[:3000]
        
        if is_jailbreak_attempt(resume_text):
            print("[SECURITY WARNING] Potential Prompt Injection detected. Sanitizing input...")
            resume_text = "Extract technical skills only from this data: " + re.sub(r'[^a-zA-Z0-9.,/\s]', '', resume_text)

        client = genai.Client()
        
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
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
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
                    
                result_dict = json.loads(response.text)
                resume_skills_raw = result_dict.get('technical_skills', [])
                break # Success
            except Exception as e:
                if attempts == MAX_RETRIES:
                    print(f"LLM Extraction failed after 3 attempts: {e}")
                time.sleep(RETRY_WAIT)

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
            
        skill_demand = {}
        for skill in db_skills_pool:
            skill_demand[skill] = skill_demand.get(skill, 0) + 1
            
        db_unique_skills = set(skill_demand.keys())
        
        gap_set = db_unique_skills - resume_parsed
        
        sorted_gaps = sorted(list(gap_set))
        
        gap_stats = {skill: skill_demand[skill] for skill in sorted_gaps}
        
        gap_stats = dict(sorted(gap_stats.items(), key=lambda item: item[1], reverse=True))

        elapsed_ms = (time.time() - start_time) * 1000

        result = SkillGapResult(
            gaps=sorted_gaps,
            demand_statistics=gap_stats,
            total_tokens=total_tokens,
            time_ms=elapsed_ms
        )
        
        return result

    except Exception as e:
        print(f"Gracefully handled error: {e}")
        return SkillGapResult(gaps=[], demand_statistics={}, total_tokens=0, time_ms=0.0)

if __name__ == "__main__":
    db_path = DB_PATH
    resume_path = RESUME_PATH

    if not os.path.exists(db_path) or not os.path.exists(resume_path):
        print("Ensure jobs.db and resume.txt exist in the respective directories.")
        sys.exit(1)
        
    final_result = find_skill_gaps(resume_path, db_path)
    
    print(f"gaps={final_result.gaps} time={final_result.time_ms:.0f} tokens={final_result.total_tokens}")
    print("\n--- BONUS: Top 5 Most In-Demand Missing Skills ---")
    top_5 = list(final_result.demand_statistics.items())[:5]
    for skill, count in top_5:
        print(f"Skill: {skill.ljust(20)} | Missing from resume, but required by {count} job(s)")

    # 1. Get the directory where the resume is located
    directory = os.path.dirname(resume_path)
    
    # 2. Get the base name of the resume file
    base_name = os.path.splitext(os.path.basename(resume_path))[0]
    
    # 3. Create the new filename
    output_filename = f"{base_name}_result.json"
    
    # 4. Join the directory and the filename together
    output_path = os.path.join(directory, output_filename)

    # 5. Save the JSON exactly in that target directory
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_result.model_dump_json(indent=4))
        
    print(f"\nSuccessfully saved full gap analysis to: {output_path}")