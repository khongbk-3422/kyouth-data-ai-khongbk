import sys
import logging

from pathlib import Path # Figure out why use Path?
from src.ingestor import ingest_all_mhtml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s |%(levelname)s |%(message)s"
)
from src.processor import process_all_html
from src.loader import load_all_jsons
from src.profiler import run_data_profile

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "data/0_source"
BRONZE_DIR = BASE_DIR / "data/1_bronze"
SILVER_DIR = BASE_DIR / "data/2_silver"
GOLD_DIR = BASE_DIR / "data/3_gold"
DB_NAME = "jobs.db"

def run_profiler():
    db_path = GOLD_DIR/DB_NAME
    run_data_profile(db_path)

def run_gold():
    input_dir = SILVER_DIR
    output_dir = GOLD_DIR
    load_all_jsons(input_dir, output_dir)

def run_silver():
    input_dir = BRONZE_DIR
    output_dir = SILVER_DIR
    process_all_html(input_dir, output_dir)


def run_bronze():
    input_dir = SOURCE_DIR
    output_dir = BRONZE_DIR
    ingest_all_mhtml(input_dir, output_dir)


def prompt_for_command():
    print("Usage: python main.py [command]")
    print("Available commands:")
    print("  ingest        Extracts raw HTML files from source MHTML files.")
    print("  process       Cleans and structures HTML data into validated JSON profiles.")
    print("  load          Loads JSON profiles into a SQLite database with idempotency.")
    print("  profile       Generates a data quality report for the SQLite database.")
    print("  all          Runs the entire pipeline: ingest → process → load → profile")
    choice = input("Select a command : ").strip().lower()
    return choice

def main():
    if len(sys.argv) < 2:
        command = prompt_for_command()
    else:
        command = sys.argv[1].lower()
    
    match command:
        case "ingest":
            run_bronze()

        case "process":
            run_silver()
            
        case "load":
            run_gold()

        case "profile":
            run_profiler()

        case "all":
            run_bronze()
            run_silver()
            run_gold()
            run_profiler()
            
        case _:
            print(f"Unknown command: '{command}'")
            sys.exit(1)

if __name__ == "__main__":
    main()