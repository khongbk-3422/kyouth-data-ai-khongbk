# K-Youth Data AI Pipeline

## Project Description

This project is a small end-to-end data pipeline for job listings built around the Medallion Architecture. It ingests raw JobStreet `.mhtml` files into a Bronze layer of HTML files, transforms them into cleaned Silver JSON records, loads those records into a SQLite Gold layer, and provides a simple profiler command for database inspection.

The goal is to practice the same core ideas used in real data platforms: keeping raw source data, cleaning and validating records before load, enforcing a basic schema, and making the pipeline safe to rerun without creating duplicates.

## Setup Instructions

### Prerequisites

- Python `3.14` or newer
- `uv` recommended for dependency management and running commands
- A terminal in the repository root

### Install Dependencies

From the repository root, run:

```bash
uv sync
```

If you prefer `pip`, install the project dependencies from `pyproject.toml` instead.

### Environment Setup

This project does not require API keys or other environment variables.

### Project Layout

- `week_1/data/0_source/` contains the raw `.mhtml` input files
- `week_1/data/1_bronze/` stores extracted HTML files
- `week_1/data/2_silver/` stores cleaned JSON files
- `week_1/data/3_gold/` stores the SQLite database `jobs.db`

## Usage

Run the pipeline from the `week_1` folder because the CLI uses local relative imports:

```bash
cd week_1
```

### Ingest Bronze Data

```bash
uv run python main.py ingest
```

This reads `data/0_source/*.mhtml` and writes raw HTML files into `data/1_bronze/`.

### Process Silver Data

```bash
uv run python main.py process
```

This reads HTML from `data/1_bronze/`, cleans and validates the records, and writes JSON files into `data/2_silver/`.

### Load Gold Data

```bash
uv run python main.py load
```

This loads the Silver JSON files into `data/3_gold/jobs.db` using SQLite and avoids duplicate inserts with `INSERT OR IGNORE`.

### Run Profile Check

```bash
uv run python main.py profile
```

This runs the data profiler against the Gold database.

### Run All Steps

```bash
uv run python main.py all
```

This runs the complete pipeline: ingest → process → load → profile.

### Expected Outputs

- Bronze: raw `.html` files in `week_1/data/1_bronze/`
- Silver: cleaned `.json` files in `week_1/data/2_silver/`
- Gold: SQLite database at `week_1/data/3_gold/jobs.db`

## Technical Reflections

### Day 1: The Extractor (Medallion & Lakehouses)

Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?

- **Answer**: Keeping the raw HTML in the Bronze layer preserves the original source of truth. If the parser changes, a field is extracted incorrectly, or the business rules evolve later, the pipeline can be replayed from the same raw data without needing to re-download anything. It also makes debugging much easier because you can compare the transformed record against the exact source page that produced it.

### Day 2: Treatment Plant (ETL vs ELT & Scale)

Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?

- **Answer**: Cloud systems often prefer ELT because raw data is cheap to store and flexible to reuse. Teams can load first, then apply different transformations later for analytics, machine learning, or reporting without repeatedly re-ingesting the source. Sequential processing is simple, but it becomes slow and fragile at scale because one bad file can block the entire run and one worker must do all the work. Distributed tools such as Spark split the workload across many workers so large datasets can be transformed faster and more reliably.

### Day 3: The Blueprint & The Vault (Storage & Contracts)

What should happen if an important field like `job_title` disappears? Why fail early instead of silently inserting `nulls` into DB? How does `INSERT OR IGNORE` help prevent duplicate records?

- **Answer**: If a required field like `job_title` is missing, the record should fail validation instead of being inserted with a null or empty value. Failing early protects downstream dashboards and analytics from corrupted rows that are hard to detect later. The pipeline should stop at the contract boundary, report the issue, and keep the invalid record out of the warehouse. `INSERT OR IGNORE` makes the load idempotent by preventing duplicate rows when the same JSON file is loaded again.

### Day 4: The QA Inspector & Orchestrator (Orchestration & DAGs)

What happens if `processor.py` crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?

- **Answer**: If `processor.py` crashes halfway through, the pipeline can be left in a partial state where some outputs exist and others do not. Manual retries require a person to notice the failure, rerun the correct step, and make sure the earlier outputs are still valid. Orchestration tools such as Airflow are more reliable because they model dependencies explicitly, retry failed steps automatically, keep run history, and make the pipeline observable and schedulable.

## Notes

- The CLI currently supports `ingest`, `process`, `load`, `profile`, and `all`.
- The Gold layer uses SQLite with `source_id` as the primary key.
- The Silver layer is designed to be idempotent by skipping existing output files.
