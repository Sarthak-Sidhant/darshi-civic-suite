#!/usr/bin/env python3
"""
Populates registry YAMLs with URLs discovered from IGOD scraping.
Matches district names from YAMLs to IGOD data and updates configs in-place.
"""

import os
import json
import glob
import yaml
import re
from difflib import get_close_matches

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_DIR = os.path.join(BASE_DIR, "sources", "registry")
IGOD_DATA = os.path.join(BASE_DIR, "data", "igod_urls.json")

def normalize(text):
    """Normalize text for matching (lowercase, remove common suffixes)."""
    if not text: return ""
    text = text.lower().strip()
    text = re.sub(r' district| collectorate| administration', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def update_yaml(path, url, scraper_type="s3waas"):
    """Update URL and scraper config in YAML file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        url_updated = False
        metadata_injected = False
        has_scraper_type = False
        has_status = False
        
        # First pass: check what exists
        for line in lines:
            if line.strip().startswith('scraper_type:'): has_scraper_type = True
            if line.strip().startswith('status:'): has_status = True

        for line in lines:
            if line.strip().startswith('url:') and '""' in line and url:
                new_lines.append(f'url: "{url}"\n')
                url_updated = True
            elif line.strip().startswith('scraper_type:') and "unknown" in line:
                new_lines.append(f'scraper_type: "{scraper_type}"\n')
            else:
                new_lines.append(line)
        
        # Inject missing fields at the end of SCRAPING CONFIG section
        if not has_scraper_type:
             # Find insertion point: usually after url or sections_to_watch
             # Simple heuristic: insert before sections_to_watch or at end
             insert_idx = -1
             for i, line in enumerate(new_lines):
                 if "sections_to_watch:" in line:
                     insert_idx = i
                     break
             
             fields_to_add = [
                 f'scraper_type: "{scraper_type}"\n',
                 'status: "active"\n',
                 'last_scraped: null\n',
                 'priority: "medium"\n'
             ]
             
             if insert_idx != -1:
                 # Insert before sections
                 new_lines[insert_idx:insert_idx] = fields_to_add
             else:
                 new_lines.extend(fields_to_add)
                 
             metadata_injected = True
        
        if url_updated or metadata_injected:
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
            
    except Exception as e:
        print(f"Error updating {path}: {e}")
        
    return False

def main():
    if not os.path.exists(IGOD_DATA):
        print(f"Error: {IGOD_DATA} not found. Run fetch_urls.py first.")
        return

    print("Loading IGOD data...")
    with open(IGOD_DATA, 'r', encoding='utf-8') as f:
        igod_links = json.load(f)
    
    # Pre-process IGOD keys for faster lookup
    igod_lookup = {normalize(k): v for k, v in igod_links.items()}
    
    print(f"Loaded {len(igod_lookup)} URLs from IGOD.")
    
    # Walk Registry
    yaml_files = glob.glob(os.path.join(REGISTRY_DIR, "**", "*.yaml"), recursive=True)
    updated_count = 0
    
    print(f"Scanning {len(yaml_files)} registry files...")
    
    for ypath in yaml_files:
        filename = os.path.basename(ypath)
        
        # We primarily target district collectorates for now
        if filename != "collectorate.yaml":
            continue
            
        # Get district name from path
        # Path: .../districts/{district_slug}/collectorate.yaml
        district_slug = os.path.basename(os.path.dirname(ypath))
        district_name_norm = normalize(district_slug.replace('_', ' '))
        
        # Try match
        matched_url = igod_lookup.get(district_name_norm)
        
        # If no exact match, try fuzzy
        if not matched_url:
            # simple alias check
            # e.g. "kanpur nagar" vs "kanpur"
            for key in igod_lookup:
                if district_name_norm in key or key in district_name_norm:
                     # Very simple containment check
                     if abs(len(key) - len(district_name_norm)) < 5:
                         matched_url = igod_lookup[key]
                         break
        
        if matched_url:
            if update_yaml(ypath, matched_url):
                updated_count += 1
                print(f"  ✓ Updated {district_slug}: {matched_url}")
        else:
            # print(f"  ✗ No match for {district_slug}")
            pass
            
    print(f"\nTotal Updated: {updated_count} files.")

if __name__ == "__main__":
    main()
