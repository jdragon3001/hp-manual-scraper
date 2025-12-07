"""
Parallel scraper - runs multiple browser instances to scrape different manuals simultaneously
"""
import os
import json
import time
import re
import random
import requests
import psutil
from bs4 import BeautifulSoup
from pathlib import Path
from playwright.sync_api import sync_playwright
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Configuration
BASE_URL = "https://www.manua.ls"
LAPTOP_URL = f"{BASE_URL}/computers-and-accessories/laptops"
DESKTOP_URL = f"{BASE_URL}/computers-and-accessories/desktops"
OUTPUT_DIR = Path("downloads")
PROGRESS_FILE = "playwright_progress.json"
URL_CACHE_FILE = "manual_urls_cache.json"

# Parallel settings
NUM_WORKERS = 3  # Number of parallel browsers (adjust based on your RAM)
PAGES_PER_CHUNK = 50
MAX_BROWSER_MEMORY_MB = 1200  # Lower per-worker since we have multiple
MAX_PAGE_TIME = 10

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Shared progress file lock
progress_lock = multiprocessing.Lock()

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"laptops": [], "desktops": []}

def save_progress(progress):
    with progress_lock:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)

def add_to_progress(category, url):
    """Thread-safe progress update"""
    with progress_lock:
        progress = load_progress()
        if category not in progress:
            progress[category] = []
        if url not in progress[category]:
            progress[category].append(url)
        save_progress(progress)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_url_cache(all_manuals):
    with open(URL_CACHE_FILE, 'w') as f:
        json.dump(all_manuals, f, indent=2)

def get_manual_links_from_page(session, url):
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        manual_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/manual' in href and href.count('/') >= 3:
                full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                if full_url not in manual_links:
                    parts = href.strip('/').split('/')
                    if len(parts) >= 3:
                        brand = parts[0].upper()
                        model = parts[1].replace('-', ' ').title()
                        manual_links.append({
                            'url': full_url,
                            'brand': brand,
                            'model': model
                        })
        return manual_links
    except Exception as e:
        return []

def get_all_manual_urls(session, category_url, category_name, total_pages):
    print(f"Getting {category_name} manual URLs ({total_pages} pages)...")
    all_manuals = []
    
    for page in range(1, total_pages + 1):
        page_url = f"{category_url}?p={page}" if page > 1 else category_url
        if page % 10 == 0:
            print(f"  Page {page}/{total_pages}...")
        manuals = get_manual_links_from_page(session, page_url)
        all_manuals.extend(manuals)
        time.sleep(0.3)
    
    print(f"Found {len(all_manuals)} manuals for {category_name}")
    return all_manuals

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def get_browser_memory_mb():
    total_mb = 0
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            if 'chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower():
                total_mb += proc.info['memory_info'].rss / (1024 * 1024)
        except:
            pass
    return total_mb

def extract_single_manual(manual_info):
    """
    Worker function - extracts a single manual using its own browser instance.
    Returns (success, manual_url, chars_extracted, error_msg)
    """
    manual_url = manual_info['url']
    brand = manual_info['brand']
    model = manual_info['model']
    category = manual_info['category']
    worker_id = manual_info.get('worker_id', 0)
    
    output_dir = OUTPUT_DIR / category / brand
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # Navigate to manual
            page.goto(manual_url, wait_until='domcontentloaded', timeout=15000)
            time.sleep(0.5)
            
            # Get total pages
            total_pages = 1
            try:
                total_pages = page.evaluate('''() => {
                    const text = document.body.innerText;
                    const match = text.match(/(\\d+)\\s*page/i);
                    return match ? parseInt(match[1]) : 1;
                }''')
            except:
                pass
            
            all_content = []
            consecutive_failures = 0
            
            for page_num in range(1, total_pages + 1):
                try:
                    page_url = f"{manual_url}?p={page_num}"
                    page.goto(page_url, wait_until='domcontentloaded', timeout=8000)
                    time.sleep(0.2)
                    page.wait_for_selector('.viewer-page', timeout=5000)
                    
                    text_content = page.eval_on_selector('.viewer-page', '(element) => element.innerText')
                    
                    if text_content and len(text_content.strip()) > 30:
                        all_content.append(f"--- Page {page_num} ---\n{text_content.strip()}")
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    
                    if consecutive_failures >= 5:
                        break
                        
                except:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        break
                    continue
            
            browser.close()
            
            if all_content:
                content = "\n\n".join(all_content)
                safe_brand = sanitize_filename(brand)
                safe_model = sanitize_filename(model)
                filename = f"{safe_brand}_{safe_model}_{total_pages}pages.txt"
                filepath = output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Brand: {brand}\n")
                    f.write(f"Model: {model}\n")
                    f.write(f"URL: {manual_url}\n")
                    f.write(f"Total Pages: {total_pages}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(content)
                
                add_to_progress(category, manual_url)
                return (True, manual_url, len(content), total_pages, None)
            else:
                add_to_progress(category, manual_url)  # Mark as done even if empty
                return (False, manual_url, 0, total_pages, "Empty content")
                
    except Exception as e:
        return (False, manual_url, 0, 0, str(e)[:50])

def run_parallel_scraper():
    print("=" * 60)
    print(f"PARALLEL SCRAPER ({NUM_WORKERS} workers)")
    print("=" * 60)
    
    # Load existing progress
    progress = load_progress()
    
    # Get manual URLs
    session = requests.Session()
    session.headers.update(HEADERS)
    
    categories = [
        ("laptops", LAPTOP_URL, 151),
        ("desktops", DESKTOP_URL, 51),
    ]
    
    cached = load_url_cache()
    if cached:
        print("Using cached URL list")
        all_manuals = cached
    else:
        all_manuals = {}
        for category_name, category_url, total_pages in categories:
            manuals = get_all_manual_urls(session, category_url, category_name, total_pages)
            all_manuals[category_name] = manuals
        save_url_cache(all_manuals)
    
    # Build work queue (skip already done)
    work_queue = []
    for category_name, manuals in all_manuals.items():
        done_urls = set(progress.get(category_name, []))
        for manual in manuals:
            if manual['url'] not in done_urls:
                manual['category'] = category_name
                work_queue.append(manual)
    
    print(f"\nTotal manuals to process: {len(work_queue)}")
    print(f"Starting {NUM_WORKERS} parallel workers...\n")
    
    stats = {"success": 0, "failed": 0, "total_chars": 0, "total_pages": 0}
    start_time = time.time()
    
    # Process in parallel
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all work
        futures = {executor.submit(extract_single_manual, manual): manual for manual in work_queue}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            manual = futures[future]
            
            try:
                success, url, chars, pages, error = future.result(timeout=300)  # 5 min timeout per manual
                
                if success:
                    stats["success"] += 1
                    stats["total_chars"] += chars
                    stats["total_pages"] += pages
                    print(f"[{completed}/{len(work_queue)}] ✓ {manual['brand']} {manual['model']} ({chars:,} chars, {pages}pg)")
                else:
                    stats["failed"] += 1
                    print(f"[{completed}/{len(work_queue)}] ✗ {manual['brand']} {manual['model']} - {error}")
                    
            except Exception as e:
                stats["failed"] += 1
                print(f"[{completed}/{len(work_queue)}] ✗ {manual['brand']} {manual['model']} - Worker error: {str(e)[:30]}")
            
            # Progress update every 10
            if completed % 10 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed * 60  # manuals per minute
                mem = psutil.virtual_memory().percent
                print(f"\n  [Progress: {stats['success']} OK, {stats['failed']} fail | {rate:.1f}/min | {mem:.0f}% RAM]\n")
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total pages: {stats['total_pages']:,}")
    print(f"Total characters: {stats['total_chars']:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {(stats['success'] + stats['failed']) / elapsed * 60:.1f} manuals/minute")
    print("=" * 60)

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows support
    run_parallel_scraper()

