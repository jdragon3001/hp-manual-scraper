"""
Rebuild manual_urls_cache.json using brand-specific pages.
Instead of paginating through all laptops/desktops, this scrapes:
  - https://www.manua.ls/laptops/{brand}
  - https://www.manua.ls/desktops/{brand}

This is more reliable and ensures we get ALL manuals for each brand.

Usage: python rebuild_cache_by_brand.py
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random

BASE_URL = "https://www.manua.ls"
OUTPUT_FILE = "manual_urls_cache.json"
BACKUP_FILE = "manual_urls_cache_backup.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_all_brands_from_cache():
    """Extract all unique brands from existing cache"""
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        brands = set()
        for category, manuals in cache.items():
            for manual in manuals:
                brands.add(manual['brand'].upper())
        
        return sorted(list(brands))
    except:
        # If no cache, use a default list of major brands
        return [
            "HP", "LENOVO", "ASUS", "SONY", "DELL", "ACER", "MSI", "SAMSUNG",
            "TOSHIBA", "APPLE", "PANASONIC", "FUJITSU", "GOOGLE", "GETAC",
            "LG", "EMATIC", "PACKARD-BELL", "GATEWAY", "COMPAQ", "CLEVO",
            "MEDION", "ALIENWARE", "MICROSOFT", "RAZER", "IBM", "NEC"
        ]

def get_manuals_from_brand_page(session, brand, category):
    """
    Get all manuals for a brand from their category page.
    Args:
        brand: Brand name (will be lowercased for URL)
        category: 'laptops' or 'desktops'
    Returns:
        List of manual dictionaries
    """
    brand_lower = brand.lower().replace('_', '-')
    url = f"{BASE_URL}/{category}/{brand_lower}"
    
    try:
        response = session.get(url, timeout=30)
        
        # Check if page exists (404 or redirect means no manuals for this brand/category)
        if response.status_code == 404 or 'no manuals found' in response.text.lower():
            return []
        
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        manuals = []
        
        # Find all manual links on the brand page
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            
            # Look for manual links in format: /brand/model/manual
            if href and '/manual' in href and href.count('/') >= 3:
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                
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
                    
                    # Avoid duplicates
                    if manual not in manuals:
                        manuals.append(manual)
        
        return manuals
    
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching {url}: {str(e)[:50]}")
        return []
    except Exception as e:
        print(f"  Parse error for {url}: {str(e)[:50]}")
        return []

def rebuild_cache():
    """Rebuild the entire cache by scraping brand-specific pages"""
    print("=" * 60)
    print("REBUILDING MANUAL CACHE BY BRAND")
    print("=" * 60)
    
    # Backup existing cache
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            old_cache = json.load(f)
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(old_cache, f, indent=2)
        print(f"✓ Backed up existing cache to {BACKUP_FILE}")
    except:
        print("No existing cache to backup")
    
    # Get all brands
    brands = get_all_brands_from_cache()
    print(f"\nFound {len(brands)} brands to process")
    print(f"First 10: {', '.join(brands[:10])}")
    print()
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_manuals = {
        'laptops': [],
        'desktops': []
    }
    
    stats = {
        'brands_processed': 0,
        'laptop_manuals': 0,
        'desktop_manuals': 0,
        'errors': 0
    }
    
    start_time = time.time()
    
    for i, brand in enumerate(brands, 1):
        print(f"[{i}/{len(brands)}] {brand}...", end=" ", flush=True)
        
        brand_start = time.time()
        laptop_count = 0
        desktop_count = 0
        
        # Get laptops for this brand
        try:
            laptops = get_manuals_from_brand_page(session, brand, 'laptops')
            laptop_count = len(laptops)
            all_manuals['laptops'].extend(laptops)
            stats['laptop_manuals'] += laptop_count
        except Exception as e:
            print(f"\n  ERROR (laptops): {str(e)[:50]}")
            stats['errors'] += 1
        
        time.sleep(random.uniform(0.5, 1.0))  # Be polite
        
        # Get desktops for this brand
        try:
            desktops = get_manuals_from_brand_page(session, brand, 'desktops')
            desktop_count = len(desktops)
            all_manuals['desktops'].extend(desktops)
            stats['desktop_manuals'] += desktop_count
        except Exception as e:
            print(f"\n  ERROR (desktops): {str(e)[:50]}")
            stats['errors'] += 1
        
        brand_time = time.time() - brand_start
        stats['brands_processed'] += 1
        
        print(f"L:{laptop_count} D:{desktop_count} ({brand_time:.1f}s)")
        
        # Save progress every 10 brands
        if i % 10 == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_manuals, f, indent=2)
            elapsed = time.time() - start_time
            rate = i / elapsed * 60
            print(f"  [Saved progress: {stats['laptop_manuals']} laptops, {stats['desktop_manuals']} desktops | {rate:.1f} brands/min]\n")
        
        time.sleep(random.uniform(0.5, 1.0))  # Be polite
    
    # Final save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_manuals, f, indent=2)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("CACHE REBUILD COMPLETE")
    print("=" * 60)
    print(f"Brands processed: {stats['brands_processed']}")
    print(f"Total laptop manuals: {stats['laptop_manuals']:,}")
    print(f"Total desktop manuals: {stats['desktop_manuals']:,}")
    print(f"Total manuals: {stats['laptop_manuals'] + stats['desktop_manuals']:,}")
    print(f"Errors: {stats['errors']}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {stats['brands_processed']/(elapsed/60):.1f} brands/min")
    print("=" * 60)

if __name__ == "__main__":
    rebuild_cache()

