#!/usr/bin/env python3
"""
Builds the 03_special_economic_zones registry structure with major SEZs.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_DIR = os.path.join(BASE_DIR, "sources", "registry")
SEZ_DIR = os.path.join(REGISTRY_DIR, "03_special_economic_zones")


def create_yaml(path, data):
    """Writes data to a YAML file with formatted sections."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("# === IDENTITY ===\n")
        f.write(f'id: "{data.get("id", "")}"\n')
        f.write(f'name: "{data.get("name", "")}"\n')
        f.write(f'type: "special_economic_zone"\n')
        f.write(f'jurisdiction_level: "sez"\n')
        f.write("\n")
        
        f.write("# === HIERARCHY ===\n")
        f.write(f'parent_state: "{data.get("parent_state", "")}"\n')
        f.write(f'parent_district: "{data.get("parent_district", "")}"\n')
        f.write('governing_body: "Ministry of Commerce and Industry"\n')
        f.write("\n")
        
        f.write("# === SCRAPING CONFIG ===\n")
        f.write(f'url: "{data.get("url", "")}"\n')
        f.write('scraper_type: "custom"\n')
        f.write('status: "pending"\n')
        f.write('last_scraped: null\n')
        f.write(f'priority: "{data.get("priority", "low")}"\n')


SEZS = [
    {"id": "sez-gift-city", "name": "GIFT City IFSC", "slug": "gift_city_ifsc",
     "url": "https://www.giftgujarat.in", "parent_state": "gujarat", 
     "parent_district": "gandhinagar", "priority": "high"},
    {"id": "sez-noida", "name": "Noida Special Economic Zone", "slug": "noida_sez",
     "url": "https://nsez.gov.in", "parent_state": "uttar_pradesh",
     "parent_district": "gautam_buddha_nagar", "priority": "medium"},
    {"id": "sez-cochin", "name": "Cochin Special Economic Zone", "slug": "cochin_sez",
     "url": "https://csez.gov.in", "parent_state": "kerala",
     "parent_district": "ernakulam", "priority": "medium"},
    {"id": "sez-kandla", "name": "Kandla Special Economic Zone", "slug": "kandla_sez",
     "url": "https://kasez.gov.in", "parent_state": "gujarat",
     "parent_district": "kutch", "priority": "medium"},
    {"id": "sez-santacruz", "name": "SEEPZ Special Economic Zone", "slug": "seepz_sez",
     "url": "https://www.seepz.gov.in", "parent_state": "maharashtra",
     "parent_district": "mumbai_suburban", "priority": "medium"},
    {"id": "sez-falta", "name": "Falta Special Economic Zone", "slug": "falta_sez",
     "url": "https://faltasez.gov.in", "parent_state": "west_bengal",
     "parent_district": "south_24_parganas", "priority": "low"},
    {"id": "sez-madras", "name": "Madras Export Processing Zone", "slug": "mepz",
     "url": "https://mepz.gov.in", "parent_state": "tamil_nadu",
     "parent_district": "kanchipuram", "priority": "medium"},
]


def build_sez_structure():
    """Generate the 03_special_economic_zones registry structure."""
    
    print("Building SEZ registry structure...")
    os.makedirs(SEZ_DIR, exist_ok=True)
    
    for sez in SEZS:
        filename = f"{sez['slug']}.yaml"
        filepath = os.path.join(SEZ_DIR, filename)
        create_yaml(filepath, sez)
        print(f"  Created: {filename}")
    
    print(f"\n✓ Created {len(SEZS)} SEZ YAML files in 03_special_economic_zones/")


if __name__ == "__main__":
    build_sez_structure()
