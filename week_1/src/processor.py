import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError

# 1. Enforce Data Contract via Pydantic
class JobListing(BaseModel):
    source_id: str = Field(min_length=1)
    job_title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    description: str = Field(min_length=1)

def clean_text(element) -> str:
    """Helper to strip tags, trim whitespace, and avoid fused words."""
    if not element:
        return ""
    # Using space as separator prevents "<span>Hello</span><span>World</span>" -> "HelloWorld"
    text = element.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def clean_string(value: str) -> str:
    if not value:
        return ""
    return " ".join(str(value).split())


def extract_job_header_lines(soup: BeautifulSoup) -> list[str]:
    page = soup.find(attrs={"data-automation": "jobDetailsPage"})
    if not page:
        return []

    lines = []
    for line in page.get_text("\n", strip=True).splitlines():
        cleaned = clean_string(line)
        if cleaned:
            lines.append(cleaned)
    return lines


def looks_like_job_title(line: str) -> bool:
    if not line:
        return False

    lowered = line.lower()
    title_keywords = (
        " engineer",
        "engineer",
        " developer",
        "developer",
        " analyst",
        "analyst",
        " specialist",
        "specialist",
        " associate",
        "associate",
        " programmer",
        "programmer",
        " scientist",
        "scientist",
        " tester",
        "tester",
        " architect",
        "architect",
        " administrator",
        "administrator",
        " manager",
        "manager",
        " support",
        "support",
        " consultant",
        "consultant",
        " automation",
        "automation",
        " platform",
        "platform",
        " product",
        "product",
        " solution",
        "solution",
        " executive",
        "executive",
        " officer",
        "officer",
        " designer",
        "designer",
        " developer",
        "developer",
        " devops",
        "devops",
    )

    return any(keyword in lowered for keyword in title_keywords)


def extract_title(soup: BeautifulSoup) -> str:
    title_tag = soup.find(attrs={"data-automation": "job-detail-title"})
    if title_tag:
        title_text = clean_string(title_tag.get_text(separator=" ", strip=True))
        if title_text:
            return title_text

    for meta_tag in soup.find_all("meta"):
        if meta_tag.get("property") in {"og:title", "twitter:title"} and meta_tag.get("content"):
            title_text = re.sub(
                r"\s*-\s*Jobstreet\s*$",
                "",
                clean_string(meta_tag.get("content")),
                flags=re.I,
            )
            title_text = re.sub(r"\s+Job\s+in\s+.+$", "", title_text, flags=re.I)
            return clean_string(title_text)

    if soup.title and soup.title.get_text(strip=True):
        title_text = re.sub(r"\s*-\s*Jobstreet\s*$", "", clean_string(soup.title.get_text(" ", strip=True)), flags=re.I)
        title_text = re.sub(r"\s+Job\s+in\s+.+$", "", title_text, flags=re.I)
        return clean_string(title_text)

    return ""


def extract_company(soup: BeautifulSoup, title: str) -> str:
    company_profile = soup.find(attrs={"data-automation": "company-profile"})
    if company_profile:
        profile_text = clean_string(company_profile.get_text(separator=" ", strip=True))
        match = re.match(r"^(.+?)\s+\d+(?:\.\d+)?\b", profile_text)
        if match:
            return clean_string(match.group(1))

    company_tag = soup.find(attrs={"data-automation": "advertiser-name"})
    if company_tag:
        company = clean_string(company_tag.get_text(separator=" ", strip=True))
        if company:
            return company

    header_lines = extract_job_header_lines(soup)
    skip_exact = {
        "View all jobs",
        "Quick apply",
        "Apply",
        "Save",
        "Add expected salary to your profile for insights",
        "Full time",
    }

    for line in header_lines:
        if line == title:
            continue
        if line in skip_exact:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", line):
            continue
        if line.lower().endswith("reviews"):
            continue
        if line.startswith("(") and line.endswith(")"):
            continue
        if line.lower().startswith("posted "):
            continue
        if line.lower().startswith("job detail"):
            continue
        return line

    meta_desc = soup.find("meta", property="og:description")
    if meta_desc and meta_desc.get("content"):
        description = clean_string(meta_desc.get("content"))
        match = re.match(r"^([A-Z][A-Za-z0-9&'().,\-/+ ]{1,80}?)\s+is\s+", description)
        if match:
            return clean_string(match.group(1))

    return ""

def process_all_html(input_dir: str, output_dir: str):
    print("🥈 Silver: Starting data processing...")
    
    # Ensure Silver directory exists (Idempotency)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print("\n📊 Silver Summary:\nTotal: 0 | Processed: 0 | Skipped: 0")
        return

    # Sort files to ensure strict execution tracking order
    html_files = sorted([f for f in input_path.iterdir() if f.suffix.lower() == '.html'])
    
    total_count = len(html_files)
    processed_count = 0
    skipped_count = 0

    if total_count == 0:
        print("\n📊 Silver Summary:\nTotal: 0 | Processed: 0 | Skipped: 0")
        return

    for file_path in html_files:
        filename = file_path.name
        output_file_path = Path(output_dir) / f"{file_path.stem}.json"
        try:
            if output_file_path.exists():
                print(f"⚠️ Skipping existing: {filename}")
                skipped_count += 1
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            # --- FIELD EXTRACTION ---
            
            # Extract source_id from <meta property="og:url" content="...">
            source_id = ""
            meta_url = soup.find('meta', property='og:url')
            if meta_url and meta_url.get('content'):
                # Split trailing slashes and grab the last URI block segment
                url_path = meta_url['content'].rstrip('/')
                source_id = url_path.split('/')[-1]

            # Extract job title and company with fallbacks for pages that omit the primary markers
            raw_title = extract_title(soup)
            raw_company = extract_company(soup, raw_title)

            # Extract description from meta property="og:description"
            raw_description = ""
            meta_desc = soup.find('meta', property='og:description')
            if meta_desc and meta_desc.get('content'):
                raw_description = meta_desc.get('content')
            
            # Text Cleaning Process
            cleaned_title = clean_string(raw_title)
            cleaned_company = clean_string(raw_company)
            cleaned_description = clean_string(raw_description)

            # --- VALIDATION LAYER ---
            # Instantiate data dictionary payload
            data_payload = {
                "source_id": source_id,
                "job_title": cleaned_title,
                "company": cleaned_company,
                "description": cleaned_description
            }

            # Enforce validation schemas with Pydantic
            listing = JobListing(**data_payload)
            
            # --- IDEMPOTENT WRITE LAYER ---
            # Write structured dictionary output to disk using strict UTF-8
            with open(output_file_path, 'w', encoding='utf-8') as out_f:
                json.dump(listing.model_dump(), out_f, ensure_ascii=False, indent=2)
                
            print(f"✅ Processed: {filename}")
            processed_count += 1

        except ValidationError as val_err:
            # Capture missing fields specifically for output alerts formatting
            errors = val_err.errors()
            missing_field = errors[0]['loc'][0] if errors else "data"
            print(f"⚠️ Missing {missing_field} in: {filename}")
            skipped_count += 1
        except Exception:
            print(f"⚠️ Error processing {filename}")
            skipped_count += 1

    # End summary log report block output
    print("\n📊 Silver Summary:")
    print(f"Total: {total_count} | Processed: {processed_count} | Skipped: {skipped_count}")
