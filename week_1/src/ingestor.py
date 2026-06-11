import os
import email
from email import policy
from pathlib import Path

def ingest_all_mhtml(input_dir: str, output_dir: str):
    print("🥉 Bronze: Starting data ingestion...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print("\nSource directory does not exist or is not a directory.")
        return

    mhtml_files = sorted([f for f in input_path.iterdir() if f.suffix.lower() == '.mhtml'])
    
    total_count = len(mhtml_files)
    extracted_count = 0
    failed_count = 0

    if total_count == 0:
        print("\nNo MHTML files found in the source directory.")
        return

    for file_path in mhtml_files:
        filename = file_path.name
        try:
            with open(file_path, 'rb') as f:
                # Parse the MHTML file as an email message
                msg = email.message_from_binary_file(f, policy=policy.default)
            
            html_content = None
            
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    html_content = part.get_content()
                    break
            
            if html_content:
                output_file_path = Path(output_dir) / f"{file_path.stem}.html"
                
                with open(output_file_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(html_content)
                
                print(f"✅ Extracted: {filename}"                )
                extracted_count += 1
            else:
                print(f"⚠️ No HTML content found in: {filename}")
                failed_count += 1
                
        except Exception as e:
            print(f"⚠️ Error processing {filename}: {e}")
            failed_count += 1

    print("\n📊 Bronze Summary:")
    print(f"Total: {total_count} | Extracted: {extracted_count} | Failed: {failed_count}")
