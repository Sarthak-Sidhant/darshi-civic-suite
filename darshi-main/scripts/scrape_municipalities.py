
import os
import requests
import asyncio
from bs4 import BeautifulSoup
from app.services.postgres_service import get_db_connection
import re

# Wikipedia URL for Municipal Corporations in India
# Provided by user or derived from context
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_municipal_corporations_in_India"

async def scrape_municipalities():
    print(f"Fetching {WIKI_URL}...")
    try:
        response = requests.get(WIKI_URL)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Failed to fetch Wikipedia page: {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # The page generally has a table for each state or one large table.
    # Looking at the user snippet, it seems there are multiple tables or headers for states.
    # We will try to find all 'table.wikitable'
    
    tables = soup.find_all('table', {'class': 'wikitable'})
    print(f"Found {len(tables)} tables.")
    
    municipalities = []
    
    for table in tables:
        # Check headers to see if this is a relevant table
        headers = [th.text.strip() for th in table.find_all('th')]
        
        # Heuristic: Valid table should have columns like 'Corporation Name', 'City', 'District'
        if not any('Corporation Name' in h for h in headers) and not any('City' in h for h in headers):
            continue
            
        # Parse rows
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            # Skip header row inside tbody if any
            if not cols or (cols[0].name == 'th' and 'Corporation' in cols[1].text): 
                continue
                
            # Attempt to extract data. Structure varies but usually:
            # S/N | Corporation Name | City | District | Area | Population | ... | Website
            
            # We need to map indexes dynamically if possible, or use standard offset
            # Most tables seem to follow: S/N, Name, City, District...
            
            try:
                # Naive extraction based on typical wikipedia list format
                # Skipping S/N (index 0)
                
                # Check if row is purely headers (sometimes th used in first col)
                clean_cols = [c.text.strip() for c in cols]
                if len(clean_cols) < 4:
                    continue
                    
                corp_name = clean_cols[1]
                city = clean_cols[2]
                district = clean_cols[3]
                
                # Clean up names (remove reference brackets [1], etc.)
                corp_name = re.sub(r'\[.*?\]', '', corp_name).strip()
                city = re.sub(r'\[.*?\]', '', city).strip()
                district = re.sub(r'\[.*?\]', '', district).strip()
                
                # Try to get Population (often index 5 or similar)
                # Look for numeric-ish column
                population = None
                for i in range(4, len(clean_cols)):
                    val = clean_cols[i].replace(',', '')
                    if val.isdigit():
                        population = int(val)
                        break
                
                # Try to find Website (often last column or contains http)
                website = None
                links = row.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if 'http' in href and 'wikipedia' not in href and 'archive.org' not in href:
                         website = href
                         break
                
                if not website and len(clean_cols) > 0:
                     last_col_text = clean_cols[-1]
                     if 'http' in last_col_text:
                         website = last_col_text
                
                # Generate a slug ID
                muni_id = corp_name.lower().replace(' ', '_').replace('.', '').replace('-', '_')
                
                municipalities.append({
                    "id": muni_id[:50], # Truncate if too long
                    "name": corp_name,
                    "city": city,
                    "district": district,
                    "population": population,
                    "website": website,
                    "state": "Unknown" # Need to extract state from preceding H2 header or similar
                })
                
            except Exception as e:
                print(f"Skipping row due to error: {e}")
                continue

    # Post-process to find states
    # This is tricky with simple soup iteration. 
    # Alternative strategy: iterate through H2 headers and next_siblings until next header.
    
    municipalities_with_state = []
    
    content_div = soup.find('div', {'class': 'mw-parser-output'})
    if content_div:
        current_state = "Unknown"
        for child in content_div.children:
            if child.name == 'div' and 'mw-heading' in child.get('class', []):
                 h2 = child.find('h2')
                 if h2:
                    current_state = h2.text.strip().replace('[edit]', '')
            elif child.name == 'h2': # Fallback for older wiki HTML
                 current_state = child.text.strip().replace('[edit]', '')
            elif child.name == 'table' and 'wikitable' in child.get('class', []):
                # Process table knowing current_state
                table = child
                # ... reuse parsing logic ...
                # (For brevity in this one-off script, I'll copy-paste the logic or refactor)
                rows = table.find_all('tr')
                headers = [th.text.strip() for th in table.find_all('th')]
                
                # Verify it's a data table
                if not any('Corporation' in h or 'Name' in h for h in headers):
                    continue

                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    clean_cols = [c.text.strip() for c in cols]
                    if len(clean_cols) < 3: continue
                    
                    # Heuristic to skip header row that matches our check
                    if 'Corporation' in clean_cols[1]: continue

                    try:
                        corp_name = re.sub(r'\[.*?\]', '', clean_cols[1]).strip()
                        city = re.sub(r'\[.*?\]', '', clean_cols[2]).strip()
                        district = re.sub(r'\[.*?\]', '', clean_cols[3]).strip()
                        
                        population = None
                        for col in cols:
                            txt = col.text.replace(',', '').strip()
                            if txt.isdigit() and len(txt) > 4: # population usually > 10000
                                population = int(txt)
                                break
                        
                        # Website hunt
                        website = None
                        for col in cols:
                            a = col.find('a', href=True)
                            if a:
                                href = a['href']
                                if href.startswith('http') and 'wikipedia.org' not in href:
                                    website = href
                                    break
                        
                        m_id = f"{city.lower().replace(' ', '_')}_mc"
                        
                        municipalities_with_state.append({
                            "id": m_id,
                            "name": corp_name,
                            "city_name": city,
                            "district": district,
                            "state": current_state,
                            "population": population,
                            "website": website
                        })
                    except Exception as e:
                        pass

    print(f"Scraped {len(municipalities_with_state)} municipalities.")
    
    # DB Update
    conn = await get_db_connection()
    try:
        for m in municipalities_with_state:
            print(f"Upserting {m['name']} ({m['state']})...")
            # We use 'name' or 'id' constraint.
            # Since IDs are generated, we might conflict. 
            # Safer to use ON CONFLICT DO UPDATE on name/state if unique, 
            # but schema logic uses ID.
            # We'll try to insert, if ID exists, we skip (or update).
            
            await conn.execute("""
                INSERT INTO municipalities (id, name, state, district, population, website)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    state = EXCLUDED.state,
                    district = EXCLUDED.district,
                    population = EXCLUDED.population,
                    website = EXCLUDED.website
            """, m['id'], m['name'], m['state'], m['district'], m['population'], m['website'])
            
            # Also create corresponding 'cities' entry if missing?
            # Creating city implies we need lat/lng. We don't have it here.
            # So we will just store municipality data.
            
    finally:
        await conn.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_municipalities())
