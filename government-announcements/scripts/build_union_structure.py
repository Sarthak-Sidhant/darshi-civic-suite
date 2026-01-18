#!/usr/bin/env python3
"""
Builds the 01_union_of_india registry structure with all major central government sources.
Based on the official Indian government organizational hierarchy.
"""

import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_DIR = os.path.join(BASE_DIR, "sources", "registry")
UNION_DIR = os.path.join(REGISTRY_DIR, "01_union_of_india")

# Template for YAML output
def create_yaml(path, data):
    """Writes data to a YAML file with formatted sections."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("# === IDENTITY ===\n")
        f.write(f'id: "{data.get("id", "")}"\n')
        f.write(f'name: "{data.get("name", "")}"\n')
        f.write(f'type: "{data.get("type", "")}"\n')
        f.write(f'jurisdiction_level: "{data.get("jurisdiction_level", "national")}"\n')
        f.write("\n")
        
        f.write("# === HIERARCHY ===\n")
        f.write(f'parent: "{data.get("parent", "union_of_india")}"\n')
        if data.get("reporting_to"):
            f.write(f'reporting_to: "{data.get("reporting_to")}"\n')
        f.write("\n")
        
        f.write("# === SCRAPING CONFIG ===\n")
        f.write(f'url: "{data.get("url", "")}"\n')
        f.write(f'scraper_type: "{data.get("scraper_type", "unknown")}"\n')
        f.write('status: "pending"\n')
        f.write('last_scraped: null\n')
        f.write(f'priority: "{data.get("priority", "medium")}"\n')


# === SOURCE DEFINITIONS ===

APEX_EXECUTIVE = [
    {"id": "union-apex-president", "name": "President's Secretariat", "slug": "president_secretariat", 
     "url": "https://presidentofindia.nic.in", "type": "apex_executive", "priority": "high",
     "reporting_to": "President of India"},
    {"id": "union-apex-pmo", "name": "Prime Minister's Office", "slug": "pmo",
     "url": "https://www.pmindia.gov.in", "type": "apex_executive", "priority": "high",
     "reporting_to": "Prime Minister"},
    {"id": "union-apex-cabinet", "name": "Cabinet Secretariat", "slug": "cabinet_secretariat",
     "url": "https://cabsec.gov.in", "type": "apex_executive", "priority": "high",
     "reporting_to": "Cabinet Secretary"},
    {"id": "union-apex-vp", "name": "Vice President's Secretariat", "slug": "vice_president",
     "url": "https://vicepresidentofindia.nic.in", "type": "apex_executive", "priority": "medium",
     "reporting_to": "Vice President of India"},
]

LEGISLATIVE = [
    {"id": "union-leg-loksabha", "name": "Lok Sabha (House of the People)", "slug": "loksabha",
     "url": "https://loksabha.nic.in", "type": "legislative", "priority": "high"},
    {"id": "union-leg-rajyasabha", "name": "Rajya Sabha (Council of States)", "slug": "rajyasabha",
     "url": "https://rajyasabha.nic.in", "type": "legislative", "priority": "high"},
    {"id": "union-leg-gazette", "name": "The Gazette of India", "slug": "gazette_of_india",
     "url": "https://egazette.gov.in", "type": "legislative", "priority": "high"},
]

JUDICIARY = [
    {"id": "union-jud-sc", "name": "Supreme Court of India", "slug": "supreme_court",
     "url": "https://main.sci.gov.in", "type": "judiciary", "priority": "high"},
    {"id": "union-jud-ngt", "name": "National Green Tribunal", "slug": "ngt",
     "url": "https://greentribunal.gov.in", "type": "judiciary", "priority": "medium"},
    {"id": "union-jud-nclat", "name": "National Company Law Appellate Tribunal", "slug": "nclat",
     "url": "https://nclat.nic.in", "type": "judiciary", "priority": "medium"},
]

CONSTITUTIONAL_BODIES = [
    {"id": "union-const-eci", "name": "Election Commission of India", "slug": "eci",
     "url": "https://eci.gov.in", "type": "constitutional_body", "priority": "high"},
    {"id": "union-const-cag", "name": "Comptroller and Auditor General", "slug": "cag",
     "url": "https://cag.gov.in", "type": "constitutional_body", "priority": "high"},
    {"id": "union-const-upsc", "name": "Union Public Service Commission", "slug": "upsc",
     "url": "https://www.upsc.gov.in", "type": "constitutional_body", "priority": "high"},
    {"id": "union-const-nhrc", "name": "National Human Rights Commission", "slug": "nhrc",
     "url": "https://nhrc.nic.in", "type": "constitutional_body", "priority": "medium"},
    {"id": "union-const-cic", "name": "Central Information Commission", "slug": "cic",
     "url": "https://cic.gov.in", "type": "constitutional_body", "priority": "medium"},
]

# Major Ministries (citizen-facing, high priority)
MINISTRIES = [
    # Critical Citizen-Facing
    {"id": "union-min-mha", "name": "Ministry of Home Affairs", "slug": "mha",
     "url": "https://www.mha.gov.in", "priority": "high"},
    {"id": "union-min-mohfw", "name": "Ministry of Health and Family Welfare", "slug": "mohfw",
     "url": "https://www.mohfw.gov.in", "priority": "high"},
    {"id": "union-min-moe", "name": "Ministry of Education", "slug": "moe",
     "url": "https://www.education.gov.in", "priority": "high"},
    {"id": "union-min-morth", "name": "Ministry of Road Transport and Highways", "slug": "morth",
     "url": "https://morth.nic.in", "priority": "high"},
    {"id": "union-min-mohua", "name": "Ministry of Housing and Urban Affairs", "slug": "mohua",
     "url": "https://mohua.gov.in", "priority": "high"},
    {"id": "union-min-mof", "name": "Ministry of Finance", "slug": "mof",
     "url": "https://finmin.nic.in", "priority": "high"},
    {"id": "union-min-molaw", "name": "Ministry of Law and Justice", "slug": "molaw",
     "url": "https://lawmin.gov.in", "priority": "high"},
    
    # Important
    {"id": "union-min-mod", "name": "Ministry of Defence", "slug": "mod",
     "url": "https://mod.gov.in", "priority": "medium"},
    {"id": "union-min-mea", "name": "Ministry of External Affairs", "slug": "mea",
     "url": "https://www.mea.gov.in", "priority": "medium"},
    {"id": "union-min-moagri", "name": "Ministry of Agriculture and Farmers Welfare", "slug": "moagri",
     "url": "https://agricoop.nic.in", "priority": "medium"},
    {"id": "union-min-moenv", "name": "Ministry of Environment, Forest and Climate Change", "slug": "moenv",
     "url": "https://moef.gov.in", "priority": "medium"},
    {"id": "union-min-moci", "name": "Ministry of Commerce and Industry", "slug": "moci",
     "url": "https://commerce.gov.in", "priority": "medium"},
    {"id": "union-min-mole", "name": "Ministry of Labour and Employment", "slug": "mole",
     "url": "https://labour.gov.in", "priority": "medium"},
    {"id": "union-min-morail", "name": "Ministry of Railways", "slug": "morail",
     "url": "https://indianrailways.gov.in", "priority": "medium"},
    {"id": "union-min-mopng", "name": "Ministry of Petroleum and Natural Gas", "slug": "mopng",
     "url": "https://mopng.gov.in", "priority": "medium"},
    {"id": "union-min-mopower", "name": "Ministry of Power", "slug": "mopower",
     "url": "https://powermin.gov.in", "priority": "medium"},
    {"id": "union-min-mowr", "name": "Ministry of Jal Shakti (Water Resources)", "slug": "mowr",
     "url": "https://jalshakti-dowr.gov.in", "priority": "medium"},
    {"id": "union-min-moca", "name": "Ministry of Civil Aviation", "slug": "moca",
     "url": "https://www.civilaviation.gov.in", "priority": "medium"},
    {"id": "union-min-mosj", "name": "Ministry of Social Justice and Empowerment", "slug": "mosj",
     "url": "https://socialjustice.gov.in", "priority": "medium"},
    {"id": "union-min-mota", "name": "Ministry of Tribal Affairs", "slug": "mota",
     "url": "https://tribal.nic.in", "priority": "medium"},
    {"id": "union-min-mowcd", "name": "Ministry of Women and Child Development", "slug": "mowcd",
     "url": "https://wcd.nic.in", "priority": "medium"},
    {"id": "union-min-mocf", "name": "Ministry of Consumer Affairs, Food and Public Distribution", "slug": "mocf",
     "url": "https://consumeraffairs.nic.in", "priority": "high"},
    {"id": "union-min-meity", "name": "Ministry of Electronics and IT", "slug": "meity",
     "url": "https://www.meity.gov.in", "priority": "medium"},
    {"id": "union-min-mospi", "name": "Ministry of Statistics and Programme Implementation", "slug": "mospi",
     "url": "https://mospi.gov.in", "priority": "low"},
]

STRATEGIC_DEPARTMENTS = [
    {"id": "union-strat-isro", "name": "Indian Space Research Organisation (ISRO)", "slug": "isro",
     "url": "https://www.isro.gov.in", "type": "strategic_department", "priority": "medium",
     "reporting_to": "Department of Space, PMO"},
    {"id": "union-strat-dae", "name": "Department of Atomic Energy", "slug": "dae",
     "url": "https://dae.gov.in", "type": "strategic_department", "priority": "low",
     "reporting_to": "PMO"},
    {"id": "union-strat-drdo", "name": "Defence Research and Development Organisation", "slug": "drdo",
     "url": "https://www.drdo.gov.in", "type": "strategic_department", "priority": "low",
     "reporting_to": "Ministry of Defence"},
    {"id": "union-strat-uidai", "name": "Unique Identification Authority of India (UIDAI)", "slug": "uidai",
     "url": "https://uidai.gov.in", "type": "strategic_department", "priority": "high",
     "reporting_to": "Ministry of Electronics and IT"},
]


def build_union_structure():
    """Generate the complete 01_union_of_india registry structure."""
    
    print("Building Union of India registry structure...")
    
    # Create directories
    categories = [
        ("apex_executive", APEX_EXECUTIVE),
        ("legislative", LEGISLATIVE),
        ("judiciary", JUDICIARY),
        ("constitutional_bodies", CONSTITUTIONAL_BODIES),
        ("ministries", MINISTRIES),
        ("strategic_departments", STRATEGIC_DEPARTMENTS),
    ]
    
    total_created = 0
    
    for category_name, sources in categories:
        category_dir = os.path.join(UNION_DIR, category_name)
        os.makedirs(category_dir, exist_ok=True)
        
        for source in sources:
            filename = f"{source['slug']}.yaml"
            filepath = os.path.join(category_dir, filename)
            
            data = {
                "id": source["id"],
                "name": source["name"],
                "type": source.get("type", "ministry"),
                "jurisdiction_level": "national",
                "parent": "union_of_india",
                "reporting_to": source.get("reporting_to", ""),
                "url": source.get("url", ""),
                "scraper_type": "s3waas" if ".gov.in" in source.get("url", "") else "unknown",
                "priority": source.get("priority", "medium"),
            }
            
            create_yaml(filepath, data)
            total_created += 1
            print(f"  Created: {category_name}/{filename}")
    
    print(f"\n✓ Created {total_created} source YAML files in 01_union_of_india/")


if __name__ == "__main__":
    build_union_structure()
