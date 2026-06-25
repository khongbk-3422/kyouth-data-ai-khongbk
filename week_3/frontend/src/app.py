import os
import sqlite3
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
DB_PATH = os.path.join(BASE_DIR, "jobs.db")

# Helper function to connect to SQLite
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Lets us access columns by name
    return conn

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="chat_page.html")

# NEW: Route for our Bonus Dashboard
@app.get("/dashboard")
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

# NEW: API to get Chart Data (Pie Chart & Bar Chart)
@app.get("/api/charts")
async def get_chart_data():
    conn = get_db()
    
    # Data for Pie Chart: High Quality vs Low Quality (Quarantine)
    high_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    low_jobs = conn.execute("SELECT COUNT(*) FROM jobs_quarantine").fetchone()[0]
    
    # Data for Bar Chart: Top 5 Companies by job count
    top_companies = conn.execute("""
        SELECT company, COUNT(*) as count 
        FROM jobs 
        GROUP BY company 
        ORDER BY count DESC 
        LIMIT 5
    """).fetchall()
    
    conn.close()
    
    return {
        "quality": {"labels": ["High Quality", "Low Quality (Quarantine)"], "data": [high_jobs, low_jobs]},
        "companies": {"labels": [row["company"] for row in top_companies], "data": [row["count"] for row in top_companies]}
    }

# NEW: API for the Database Search Bar
@app.get("/api/search")
async def search_jobs(q: str = ""):
    conn = get_db()
    query = "SELECT job_title, company FROM jobs WHERE job_title LIKE ? OR company LIKE ? LIMIT 10"
    results = conn.execute(query, (f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    
    return [{"title": row["job_title"], "company": row["company"]} for row in results]