import sqlite3
import json
import time
import requests
import re
from typing import Dict, List
from pydantic import BaseModel, ConfigDict
from google import genai
from google.genai import types
from .rate_limiter import get_model_limits


# --- MODELS ---
class IndividualGapResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    gaps: List[str]
    demand_statistics: dict[str, int]


class MultiResumeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: List[IndividualGapResult]


# --- HELPERS ---
def parse_skills(skill_text: str) -> List[str]:
    text = (
        skill_text.lower()
        .replace("a/b testing", "ab_testing_placeholder")
        .replace("ci/cd", "cicd_placeholder")
    )
    raw_skills = re.split(r"[,/]", text)
    cleaned = {
        s.strip()
        .replace("ab_testing_placeholder", "a/b testing")
        .replace("cicd_placeholder", "ci/cd")
        for s in raw_skills
        if s.strip()
    }
    return list(cleaned)


# --- CORE ENGINE ---
def find_skill_gaps(
    resumes_dict: Dict[str, str], db_url: str, model_name: str
) -> MultiResumeAnalysis:
    batch_size, cooldown = get_model_limits(model_name)
    resume_items = list(resumes_dict.items())
    chunks = [
        dict(resume_items[i : i + max(1, batch_size)])
        for i in range(0, len(resume_items), max(1, batch_size))
    ]

    # 1. Fetch & Prepare DB data
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL")
    db_skills_pool = [
        skill for row in cursor.fetchall() for skill in parse_skills(row[0])
    ]
    conn.close()

    # Calculate global demand statistics for ALL jobs
    skill_demand = {skill: db_skills_pool.count(skill) for skill in set(db_skills_pool)}
    db_unique_skills = set(skill_demand.keys())

    all_results = []
    for chunk in chunks:
        # 1. PREPARE THE PROMPT
        prompt = f"""
        Extract hard technical skills from these resumes.
        Return ONLY valid JSON where the keys are filenames and values are lists of technical skills.
        Example: {{"resume1.pdf": ["Python", "SQL"], "resume2.txt": ["Java"]}}
        Resumes: {json.dumps(chunk)}
        """

        # 2. MODEL SELECTION (GEMINI vs OLLAMA)
        if model_name.startswith("ollama-"):
            # OLLAMA LOGIC
            response = requests.post(
                "http://host.docker.internal:11434/api/generate",
                json={
                    "model": model_name.replace("ollama-", ""),
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            raw_data = json.loads(response.json()["response"])
        else:
            # GEMINI LOGIC
            client = genai.Client()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            raw_data = json.loads(response.text)

        # 3. CALCULATE GAPS IN PYTHON
        for filename, skills_list in raw_data.items():
            resume_parsed = set()
            for s in skills_list:
                resume_parsed.update(parse_skills(s))

            gap_set = db_unique_skills - resume_parsed
            sorted_gaps = sorted(list(gap_set))

            # Match skills back to DB demand
            gap_stats = {skill: skill_demand[skill] for skill in sorted_gaps}

            all_results.append(
                IndividualGapResult(
                    filename=filename,
                    gaps=sorted_gaps,
                    demand_statistics=dict(
                        sorted(gap_stats.items(), key=lambda x: x[1], reverse=True)
                    ),
                )
            )

        if len(chunks) > 1:
            time.sleep(cooldown)

    return MultiResumeAnalysis(results=all_results)
