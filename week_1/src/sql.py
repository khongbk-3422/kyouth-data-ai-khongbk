from pathlib import Path

WEEK_DIR = Path(__file__).resolve().parent.parent


def load_sql(relative_path: str) -> str:
    """Read a SQL statement from a file relative to the week_1 root."""
    return (WEEK_DIR / relative_path).read_text(encoding="utf-8")
