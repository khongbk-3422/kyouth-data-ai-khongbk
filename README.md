# AI Job Matching & Skill Gap Analyzer (Week 2)

## Project Overview
This project is an AI-powered data processing pipeline designed to bridge the gap between job market demands and applicant skills. It leverages both local Large Language Models (Ollama) and cloud-based models (Google Gemini) to intelligently parse job descriptions, extract core technical stacks, and deterministically calculate the specific skill gaps of a candidate based on their resume. 

---

## 🛠️ Setup Instructions

**Prerequisites:** Ensure you have the following installed on your local machine:
* **Python 3.10+**
* **`uv`** (Python package manager)
* **Ollama** (Desktop application running in the background)

**1. Sync the Python Environment:**
This project uses `uv` for lightning-fast dependency management. Inside the `week_2` directory, run this command to automatically create the virtual environment and install all required packages (`google-genai`, `ollama`, `pydantic`, `python-dotenv`):

    uv sync

**2. Configure Environment Variables:**
Create a `.env` file in the root of the `week_2` directory and add your Google AI Studio API key. *(Note: Do not commit this file to Git. Ensure it is in your `.gitignore`)*.

    GOOGLE_API_KEY="your_actual_api_key_here"

**3. Prepare Data Files:**
Ensure `jobs_d1.db` (the SQLite database) and `resume.txt` (the candidate's resume) are present in the `week_2` directory.

---

## 🚀 Execution Guide (Step-by-Step Usage)

All Python scripts must be executed using `uv run` to ensure they use the correct virtual environment.

### Phase 1: Verify Local Models (Part 1)
First, download the required local models into Ollama. Run these commands one by one:

    ollama pull llama3.1
    ollama pull phi3
    ollama pull deepseek-r1:1.5b

Verify they are correctly installed:

    ollama ls

### Phase 2: Test Model Routing (Part 3)
Test the `prompt_model.py` script to ensure it correctly routes prompts to both your local machine and the cloud.

**Test Local Model (Ollama):**

    uv run prompt_model.py llama3.1 "Tell me a short coding joke."

**Test Cloud Model (Gemini):**

    uv run prompt_model.py gemini-3.5-flash "What is the capital of Malaysia?"

*Expected Output:* The terminal will print `--- RESPONSE ---` followed by the AI's answer. If the Gemini Free Tier is overloaded, the script gracefully catches the error and prints `[Gemini Error] 503 UNAVAILABLE` instead of crashing.

### Phase 3: Test Data Tagging (Day 1-2)
Run the batch-processing script to extract technical skills from the database's job descriptions. 

    uv run tag_data.py

*Expected Output:* A live log of updated jobs, followed by execution metrics.

    Analyzed Job 91397216: sql, python, java, react
    ...
    Total tokens used: 15420, took 45032.12ms

### Phase 4: Test Skill Gap Analysis (Day 3-4)
Run the analyzer to deterministically calculate what skills the candidate is missing based on `resume.txt`.

    uv run find_skill_gaps.py

*Expected Output:* A strictly lowercase, alphabetical list of missing skills (`gaps=...`), followed by time/token tracking, and a bonus statistical breakdown of the most in-demand missing skills.

---

## 📖 API / Function Reference

### `prompt_model.py`
* **`prompt_model(model: str, prompt: str) -> str`**
  * **Purpose:** Smart router directing prompts to local Ollama or cloud Gemini based on the model string. Implements `try-except` blocks to prevent crashes during API rate-limiting.
  * **Inputs:** `model` (e.g., 'llama3.1', 'gemini-3.5-flash'), `prompt` (User query).
  * **Outputs:** LLM text response or gracefully formatted error string.

### `tag_data.py`
* **`tag_data(db_url: str) -> Tuple[int, float]`**
  * **Purpose:** Batch processes database rows (5 at a time) using Gemini with `response_mime_type="application/json"` to ensure strict JSON output. Truncates descriptions to 1000 characters to optimize tokens.
  * **Inputs:** `db_url` (Path to SQLite database).
  * **Outputs:** Tokens used (int) and execution time in ms (float).

### `find_skill_gaps.py`
* **`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**
  * **Purpose:** Extracts skills from a resume using a temperature=0.0 LLM call, sanitizes inputs for jailbreaks, and uses deterministic Python Set math to calculate the gap against the job database.
  * **Inputs:** `input_file_path` (Path to resume text), `db_url` (Path to SQLite database).
  * **Outputs:** Pydantic `SkillGapResult` containing sorted gaps, token/time metrics, and demand statistics.

---

## 📊 Data & Assumptions

* **Database Schema:** Assumes the SQLite table is named `jobs` with a Primary Key `source_id` (TEXT) and columns `description` (TEXT) and `tech_stack` (TEXT).
* **Data Flow:** Raw descriptions → Gemini JSON Extraction → SQL Update → Database → Python Set Math ← Gemini Resume Extraction.
* **Token Optimization Assumption:** Assumes the core technical requirements of a job are listed within the first 1,000 characters of a description.
* **Parsing Rules:** Assumes technical skills can be reliably delimited by commas (`,`) or slashes (`/`), with hardcoded exceptions preserving terms like `CI/CD` and `A/B testing`.

---

## 🧪 Testing

* **Rate Limit Resiliency:** Tested against Google's Free Tier 15 RPM limit. The scripts simulate server overload (HTTP 503) and successfully utilize an exponential backoff/retry loop without crashing.
* **Determinism Verification:** The `find_skill_gaps.py` script was tested with multiple consecutive runs. Because the gap logic relies on pure mathematical Set Operations (`set(A) - set(B)`) rather than LLM reasoning, the output is guaranteed to be 100% deterministic.
* **Jailbreak Safety:** The system was tested by injecting malicious prompts (e.g., "Ignore previous instructions") into `resume.txt`. The script successfully intercepts known attack vectors, strips conversational context, and forces a strict data-extraction schema.

---

## ⚠️ Limitations

* **API Bottlenecks:** Because the system relies heavily on free-tier cloud models, batch processing of large databases is bottlenecked by the 15 Requests Per Minute limit, artificially extending runtime.
* **Semantic Matching Constraints:** The current skill gap logic relies on exact lowercase string matching. Therefore, "ReactJS", "React.js", and "React" are treated as distinct skills. Slight inaccuracies may occur due to missing semantic grouping.
* **Loss of Deep Context:** To optimize token usage, heavily verbose job descriptions are truncated. If a recruiter placed mandatory technical requirements at the very bottom of a 5,000-character description, the system would miss them.

---

## 🧠 Architecture Reflection

### Design Choices
The system is built on **Separation of Concerns**. LLMs are utilized strictly as *Data Extractors* (pulling skills from text), while traditional programming (Python Sets and SQL) handles the *Logic* (calculating the gaps). This prevents LLM hallucinations and ensures mathematical determinism. Error handling was prioritized globally; the system fails gracefully with clean terminal outputs rather than dumping stack traces.

### Trade-offs
I prioritized **Reliability and Cost-Efficiency over Raw Speed**. In `tag_data.py`, deliberate 5-second delays (`time.sleep`) are injected between batch executions. While this extends the runtime, it guarantees adherence to Gemini's 15 RPM limits. Furthermore, I chose to truncate the job description inputs—trading a minor risk of losing deep-context data for a massive reduction in API token consumption.

### Improvements
Given more time, I would implement **Vector Embeddings for Semantic Search**. Relying on strict lowercase string matching means "ReactJS" and "React.js" are treated as distinct skills. By embedding the extracted skills and using Cosine Similarity, the system could identify that a candidate with "NodeJS" automatically satisfies a requirement for "Node.js".