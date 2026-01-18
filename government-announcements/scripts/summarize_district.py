import argparse
import sqlite3
import os
import sys
from pathlib import Path

# Add parent path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.scrapers.utils.intelligence import IntelligenceEngine

DB_PATH = Path("data/darshi_sources.db")

def main():
    parser = argparse.ArgumentParser(description="Summarize district announcements using Gemini")
    parser.add_argument("district", help="District name or slug (e.g. 'bokaro', 'pune')")
    parser.add_argument("--model", default="gemini-1.5-flash", help="Gemini model to use")
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print("Database not found!")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    print(f"Searching for PDFs for '{args.district}'...")
    
    # query paths and metadata
    # source_id usually like 'dist-xx-name-coll'
    query_term = f"%{args.district}%"
    cursor.execute("SELECT title, local_path, start_date, end_date FROM announcements WHERE source_id LIKE ? AND local_path IS NOT NULL", (query_term,))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"No downloaded PDFs found for district '{args.district}'.")
        print("Try running the scraper first: python3 sources/scrapers/core_engine.py --priority high")
        return

    pdf_paths = []
    metadata_context = "### Document Metadata & Validity Periods:\n"
    
    found_count = 0
    for r in rows:
        title, path, start, end = r
        if os.path.exists(path):
            pdf_paths.append(path)
            filename = os.path.basename(path)
            validity = "Unknown"
            if start and end:
                validity = f"{start} to {end}"
            elif start:
                validity = f"Starts {start}"
            
            metadata_context += f"- **File**: {filename}\n  **Title**: {title}\n  **Validity**: {validity}\n\n"
            found_count += 1
    
    print(f"Found {found_count} valid PDF files locally.")
    
    if not pdf_paths:
        return
        
    print("Initializing Intelligence Engine...")
    engine = IntelligenceEngine(model_name=args.model)
    
    # Construct Context-Aware Prompt
    prompt = f"""
    You are a civic intelligence analyst for the district of {args.district.title()}.
    
    I have uploaded {len(pdf_paths)} government announcements.
    
    {metadata_context}
    
    **INSTRUCTIONS:**
    1. Analyze the content of each document in the context of its metadata.
    2. **CRITICAL**: Use the 'Validity' dates to determine if an announcement is UPCOMING, ACTIVE, or EXPIRED (Current Date: {os.getenv('CURRENT_DATE', 'Assume Today')}).
    3. Group findings by category (e.g., Elections, Infrastructure, Health).
    4. Highlight ACTIONABLE items for citizens.
    5. If a document is a form (e.g., Form A), explain what it is for based on the parent announcement title.
    """
    
    print("Requesting Analysis...")
    summary = engine.summarize_pdfs(pdf_paths, prompt=prompt)
    
    print("\n" + "="*50)
    print(f"CIVIC INTELLIGENCE REPORT: {args.district.upper()}")
    print("="*50 + "\n")
    print(summary)
    print("\n" + "="*50)

if __name__ == "__main__":
    main()
