"""
Rebuild manual_urls_cache.json using Playwright to:
1. Detect redirects (brand doesn't have laptops/desktops)
2. Handle pagination
3. Extract all manual URLs accurately

Usage: python rebuild_cache_browser.py
"""
from playwright.sync_api import sync_playwright
import json
import time
import random
import re

BASE_URL = "https://www.manua.ls"
OUTPUT_FILE = "manual_urls_cache.json"
BACKUP_FILE = "manual_urls_cache_backup.json"

# All brands from your list
ALL_BRANDS = [
    "HP", "LENOVO", "ASUS", "SONY", "DELL", "ACER", "MSI", "SAMSUNG",
    "TOSHIBA", "APPLE", "PANASONIC", "FUJITSU", "GOOGLE", "GETAC",
    "LG", "PACKARD-BELL", "GATEWAY", "COMPAQ", "CLEVO", "MEDION",
    "ALIENWARE", "MICROSOFT", "RAZER", "IBM", "NEC", "ECS", "HONOR",
    "HUAWEI", "ADVANTECH", "INTEL", "AORUS", "FUJITSU-SIEMENS", "THOMSON",
    "VIZIO", "TECHBITE", "SYSTEM76", "SHUTTLE", "KOGAN", "IGEL", "ELO",
    "MAXDATA", "HAIER", "XIAOMI", "AIRIS", "BEKO", "DURABOOK", "TARGA",
    "JYSK", "VIEWSONIC", "WYSE", "VXL", "MPMAN", "XPG", "LOCKNCHARGE",
    "MICROTECH", "TREKSTOR", "PROMETHEAN", "GIADA", "FAYTECH", "FOXCONN",
    "ATARI", "BENQ", "ROLAND", "WOOOD", "HUMANSCALE", "FLYBOOK", "SCHNEIDER",
    "HTC", "NEXOC", "RAZOR", "XPLORE", "TCL", "VULCAN", "ZEBRA", "HYUNDAI",
    "ODYS", "BELINEA", "COBY", "KIANO", "CORE-INNOVATIONS", "HERCULES",
    "ARCHOS", "EMATIC", "VISUAL-LAND", "CRAIG", "EVGA", "DYNABOOK",
    "GENERAL-DYNAMICS-ITRONIX", "CTL", "PRIXTON", "PYLE", "SEAGATE",
    "DELL-WYSE", "ARCTIC-COOLING", "CYBERNET", "NCOMPUTING", "AXIS",
    "CORSAIR", "OPTOMA", "BEMATECH", "ADVANCE", "INFOCUS", "PHILIPS",
    "AAEON", "MOXA", "VTECH", "TRIPP-LITE", "KRAMER", "PRODVX", "NCS"
]

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def get_brand_manuals(page, brand, category):
    """
    Get all manuals for a brand/category using Playwright.
    Detects redirects and handles pagination.
    
    Returns: (manuals_list, redirect_detected)
    """
    brand_lower = brand.lower().replace('_', '-')
    url = f"{BASE_URL}/{category}/{brand_lower}"
    
    try:
        # Navigate and check for redirect
        response = page.goto(url, wait_until='domcontentloaded', timeout=15000)
        time.sleep(0.5)
        
        # Check if we got redirected
        current_url = page.url
        if current_url != url:
            # Redirected - brand doesn't have this category
            return [], True
        
        # Check if page says "no manuals"
        try:
            body_text = page.evaluate('() => document.body.innerText.toLowerCase()')
            if 'no manuals found' in body_text or 'page not found' in body_text:
                return [], True
        except:
            pass
        
        manuals = []
        manual_urls_seen = set()  # Track unique URLs
        page_num = 1
        max_pages = 100  # Higher limit for brands with many manuals
        pages_without_new_manuals = 0
        
        # Paginate through all pages
        while page_num <= max_pages:
            # Extract manual links from current page
            manual_links = page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/manual"]'));
                return links.map(link => ({
                    href: link.getAttribute('href'),
                    text: link.textContent.trim()
                }));
            }''')
            
            new_manuals_this_page = 0
            for link_data in manual_links:
                href = link_data['href']
                if not href or href.count('/') < 3:
                    continue
                
                # Build full URL
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                
                # Skip if we've seen this URL before
                if full_url in manual_urls_seen:
                    continue
                
                # Extract brand and model from URL
                parts = href.strip('/').split('/')
                if len(parts) >= 3 and parts[-1] == 'manual':
                    url_brand = parts[0].upper()
                    model = parts[1].replace('-', ' ').title()
                    
                    manual = {
                        'url': full_url,
                        'brand': url_brand,
                        'model': model
                    }
                    
                    manuals.append(manual)
                    manual_urls_seen.add(full_url)
                    new_manuals_this_page += 1
            
            # If we got no NEW manuals on this page, increment counter
            if new_manuals_this_page == 0:
                pages_without_new_manuals += 1
                # If 5 pages in a row with no new manuals, we're done
                # (site has duplicate manuals across pages, so need higher threshold)
                if pages_without_new_manuals >= 5:
                    break
            else:
                pages_without_new_manuals = 0
            
            # Print progress for large brands
            if page_num > 1 and page_num % 5 == 0:
                print(f".", end="", flush=True)
            
            # Navigate to next page
            page_num += 1
            next_url = f"{url}?p={page_num}"
            
            try:
                page.goto(next_url, wait_until='domcontentloaded', timeout=10000)
                    
                # Check if redirected back to page 1 (no more pages)
                if '?p=' not in page.url:
                    break
                
                time.sleep(0.3)
            except Exception as e:
                # Timeout or error means no more pages
                break
        
        return manuals, False
        
    except Exception as e:
        print(f"\n  ERROR: {str(e)[:60]}")
        return [], False

def rebuild_cache():
    """Rebuild cache using browser-based approach"""
    print("=" * 60)
    print("REBUILDING CACHE WITH PLAYWRIGHT (REDIRECT DETECTION)")
    print("=" * 60)
    
    # Backup existing cache
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            old_cache = json.load(f)
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(old_cache, f, indent=2)
        print(f"✓ Backed up existing cache to {BACKUP_FILE}\n")
    except:
        print("No existing cache to backup\n")
    
    print(f"Processing {len(ALL_BRANDS)} brands...\n")
    
    all_manuals = {
        'laptops': [],
        'desktops': []
    }
    
    stats = {
        'brands_processed': 0,
        'laptop_manuals': 0,
        'desktop_manuals': 0,
        'laptop_redirects': 0,
        'desktop_redirects': 0,
        'errors': 0
    }
    
    start_time = time.time()
    
    with sync_playwright() as p:
        for i, brand in enumerate(ALL_BRANDS, 1):
            # RESTART BROWSER FOR EVERY BRAND
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            print(f"[{i}/{len(ALL_BRANDS)}] {brand:25s} ", end="", flush=True)
            
            brand_start = time.time()
            
            # Get laptops
            laptops, laptop_redirect = get_brand_manuals(page, brand, 'laptops')
            if laptop_redirect:
                print("L:REDIRECT ", end="", flush=True)
                stats['laptop_redirects'] += 1
            else:
                print(f"L:{len(laptops):2d} ", end="", flush=True)
                all_manuals['laptops'].extend(laptops)
                stats['laptop_manuals'] += len(laptops)
            
            time.sleep(random.uniform(0.3, 0.7))
            
            # Get desktops
            desktops, desktop_redirect = get_brand_manuals(page, brand, 'desktops')
            if desktop_redirect:
                print("D:REDIRECT ", end="", flush=True)
                stats['desktop_redirects'] += 1
            else:
                print(f"D:{len(desktops):2d} ", end="", flush=True)
                all_manuals['desktops'].extend(desktops)
                stats['desktop_manuals'] += len(desktops)
            
            brand_time = time.time() - brand_start
            stats['brands_processed'] += 1
            
            print(f"({brand_time:.1f}s)")
            
            # Close browser after this brand
            browser.close()
            
            # Save progress every 10 brands
            if i % 10 == 0:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_manuals, f, indent=2)
                elapsed = time.time() - start_time
                rate = i / elapsed * 60
                print(f"  → Progress saved: {stats['laptop_manuals']} laptops, {stats['desktop_manuals']} desktops | {rate:.1f} brands/min\n")
            
            time.sleep(random.uniform(0.5, 1.0))
    
    # Final save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_manuals, f, indent=2)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("CACHE REBUILD COMPLETE")
    print("=" * 60)
    print(f"Brands processed: {stats['brands_processed']}")
    print(f"Laptop manuals: {stats['laptop_manuals']:,}")
    print(f"Desktop manuals: {stats['desktop_manuals']:,}")
    print(f"Total manuals: {stats['laptop_manuals'] + stats['desktop_manuals']:,}")
    print(f"Laptop redirects: {stats['laptop_redirects']}")
    print(f"Desktop redirects: {stats['desktop_redirects']}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {stats['brands_processed']/(elapsed/60):.1f} brands/min")
    print("=" * 60)

if __name__ == "__main__":
    rebuild_cache()

