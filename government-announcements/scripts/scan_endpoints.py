import sys
print("STARTING SCRIPT...", flush=True)

try:
    import os
    import glob
    import yaml
    import requests
    import urllib3
    from concurrent.futures import ThreadPoolExecutor

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    REGISTRY_DIR = os.path.join(BASE_DIR, "sources", "registry")
    print(f"REGISTRY_DIR: {REGISTRY_DIR}", flush=True)

    def load_urls():
        urls = []
        pattern = os.path.join(REGISTRY_DIR, "**", "*.yaml")
        files = glob.glob(pattern, recursive=True)
        print(f"Found {len(files)} YAML files.", flush=True)
        for yaml_path in files:
            if os.path.basename(yaml_path).startswith('_'):
                continue
            try:
                with open(yaml_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and config.get('url'):
                        urls.append({
                            'id': config.get('id'),
                            'name': config.get('name'),
                            'url': config.get('url').rstrip('/')
                        })
            except Exception:
                pass
        return urls

    def check_site(site):
        base_url = site['url']
        targets = [
            ("/documents/", False),
            ("/en/documents/", True),
            ("/notice_category/announcement/", False),
            ("/en/notice_category/announcement/", True),
            ("/notice_category/notices/", False),
            ("/en/notice_category/notices/", True)
        ]
        
        results = {
            'documents': {'status': 'MISSING', 'url': None},
            'announcement': {'status': 'MISSING', 'url': None},
            'notices': {'status': 'MISSING', 'url': None}
        }
        
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        for path, is_en in targets:
            category = 'documents' if 'documents' in path else 'announcement' if 'announcement' in path else 'notices'
            if results[category]['status'] == 'FOUND':
                continue
                
            full_url = base_url.rstrip('/') + path
            try:
                resp = session.get(full_url, verify=False, timeout=5, allow_redirects=True)
                is_valid = False
                if resp.status_code == 200:
                    if resp.url.rstrip('/') == base_url.rstrip('/'):
                        pass
                    elif "page-not-found" in resp.url or "Page Not Found" in resp.text:
                        pass
                    else:
                        is_valid = True
                
                if is_valid:
                    results[category] = {
                        'status': 'FOUND', 
                        'url': full_url,
                        'requires_en': is_en
                    }
            except Exception:
                pass
                
        return site, results

    def main():
        sites = load_urls()
        print(f"Scanning {len(sites)} sites...", flush=True)
        
        stats = {
            'documents': {'found': 0, 'en_needed': 0},
            'announcement': {'found': 0, 'en_needed': 0},
            'notices': {'found': 0, 'en_needed': 0}
        }
        
        # Open CSV (unbuffered)
        with open("idor_scan_results.csv", "w", buffering=1) as csv_log:
            csv_log.write("id,name,documents_url,announcement_url,notices_url\n")
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                for site, res in executor.map(check_site, sites):
                    doc_url = res['documents']['url'] or ""
                    ann_url = res['announcement']['url'] or ""
                    not_url = res['notices']['url'] or ""
                    csv_log.write(f"{site['id']},{site['name']},{doc_url},{ann_url},{not_url}\n")
                    
                    if res['documents']['status'] == 'FOUND':
                        stats['documents']['found'] += 1
                        if res['documents']['requires_en']: stats['documents']['en_needed'] += 1
                    
                    if res['announcement']['status'] == 'FOUND':
                        stats['announcement']['found'] += 1
                        if res['announcement']['requires_en']: stats['announcement']['en_needed'] += 1

                    if res['notices']['status'] == 'FOUND':
                        stats['notices']['found'] += 1
                        if res['notices']['requires_en']: stats['notices']['en_needed'] += 1

        print("\n=== IDOR/Endpoint Scale Report ===", flush=True)
        total = len(sites)
        for cat in ['documents', 'announcement', 'notices']:
            found = stats[cat]['found']
            en = stats[cat]['en_needed']
            print(f"Endpoint: /{cat}/")
            print(f"  - Accessible: {found}/{total} ({found/total*100:.1f}%)")
            print(f"  - Required /en/: {en} ({en/found*100 if found else 0:.1f}% of accessible)")
            print()
            
except Exception as e:
    print(f"CRITICAL ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    main()
