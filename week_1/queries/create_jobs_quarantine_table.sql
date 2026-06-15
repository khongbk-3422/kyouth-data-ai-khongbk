CREATE TABLE IF NOT EXISTS jobs_quarantine (
    source_id TEXT PRIMARY KEY,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    description TEXT NOT NULL,
    tech_stack TEXT,
    content_hash TEXT,
    quality TEXT
)
