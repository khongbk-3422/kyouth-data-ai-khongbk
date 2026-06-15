from pathlib import Path


def load_sql(filename: str) -> str:
    """Load SQL query from queries/{filename}.sql file."""
    query_path = Path(__file__).resolve().parent.parent / "queries" / f"{filename}.sql"
    return query_path.read_text(encoding="utf-8").strip()
