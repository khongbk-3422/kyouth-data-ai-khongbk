import io
import os
import PyPDF2
import requests
from google import genai
import re
from .find_skill_gaps import find_skill_gaps
from fastapi import UploadFile

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
DB_PATH = os.path.abspath("src/week_2/jobs_d3_eval.db")


async def extract_file_text(files: list[UploadFile]) -> str:
    """Reads uploaded files and turns them into a single text string."""
    if not files:
        return ""

    file_context = "\n\n--- ATTACHED RESUMES ---\n"

    for file in files:
        content = await file.read()  # Read the file in memory
        file_context += f"\n[File: {file.filename}]\n"

        if file.filename.lower().endswith(".pdf"):
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        file_context += extracted + "\n"
            except Exception as e:
                file_context += f"(Error reading PDF: {str(e)})\n"

        else:
            try:
                file_context += content.decode("utf-8", errors="ignore") + "\n"
            except Exception as e:
                file_context += f"(Error reading text file: {str(e)})\n"

    return file_context


async def generate_chat_response(
    prompt: str, choice: str, files: list[UploadFile]
) -> str:
    # 1. Check for the skill gap trigger
    if re.search(r"find\s+skill(s)?\s+gap(s)?", prompt, re.IGNORECASE):
        # 1. Build a map of filename to extracted text
        resumes_map = {}
        for file in files:
            text = await extract_file_text([file])  # Extract individually
            resumes_map[file.filename] = text

        # 2. Pass the whole map to the analyzer
        analysis_data = find_skill_gaps(resumes_map, DB_PATH, choice)

        # 3. Format the JSON result into a clean chat bubble
        reply = "Skill Gap Report:\n"
        for item in analysis_data.results:
            reply += f"\n--- {item.filename} ---\n"
            reply += f"Gaps: {', '.join(item.gaps)}\n"
        return reply
    else:
        try:
            # 1. Grab all the text from the uploaded resumes
            file_text = await extract_file_text(files)

            # 2. Mash the user's prompt and the resume text together
            full_prompt = prompt + file_text

            # --- PATH 1: Cloud AI (Gemini) ---
            if choice.startswith("gemini"):
                client = genai.Client()
                response = client.models.generate_content(
                    model=choice,
                    contents=full_prompt,
                )
                return f"[{choice}] {response.text}"

            # --- PATH 2: Local AI (Ollama) ---
            elif choice.startswith("ollama-"):
                actual_model = choice.replace("ollama-", "", 1)
                payload = {
                    "model": actual_model,
                    "prompt": full_prompt,
                    "stream": False,
                }
                response = requests.post(OLLAMA_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                return f"[{actual_model}] {data.get('response', 'No response.')}"

            else:
                return "Error: Unknown model routing."

        except Exception as e:
            return f"System Error: {str(e)}"
