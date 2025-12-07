"""
Full hybrid scraper - uses requests for listings, Playwright for extraction
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

# Configuration
BASE_URL = "https://www.manua.ls"
LAPTOP_URL = f"{BASE_URL}/computers-and-accessories/laptops"
DESKTOP_URL = f"{BASE_URL}/computers-and-accessories/desktops"
OUTPUT_DIR = Path("downloads")
PROGRESS_FILE = "playwright_progress.json"
URL_CACHE_FILE = "manual_urls_cache.json"
PAGES_PER_CHUNK = 50  # Check memory every N pages
MANUALS_BEFORE_RESTART = 100  # Fallback counter (memory-based is primary)
DELAY_BETWEEN_MANUALS = (2, 4)  # Delay between manuals
RATE_LIMIT_BACKOFF = 30  # Initial backoff when rate limited
MAX_BROWSER_MEMORY_MB = 1500  # 1.5GB - restart if exceeded (leaves headroom before crash)
MAX_SYSTEM_MEMORY_PCT = 85  # Also restart if system memory gets this high
MAX_PAGE_TIME = 10  # Max seconds per page before giving up

def get_browser_memory_mb():
    """Get memory usage of all chromium processes in MB"""
    total_mb = 0
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            if 'chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower():
                total_mb += proc.info['memory_info'].rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            pass
    return total_mb

def get_system_memory_percent():
    """Get system memory usage percentage"""
    return psutil.virtual_memory().percent

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"laptops": [], "desktops": []}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_url_cache(all_manuals):
    with open(URL_CACHE_FILE, 'w') as f:
        json.dump(all_manuals, f, indent=2)

def get_manual_links_from_page(session, url):
    """Get all manual links from a category page using requests"""
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
                    # Extract brand and model from URL
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
        print(f"    Error: {str(e)[:60]}")
        return []

def get_all_manual_urls(session, category_url, category_name, total_pages):
    """Get all manual URLs for a category"""
    print(f"Getting {category_name} manual URLs ({total_pages} pages)...")
    
    all_manuals = []
    
    for page in range(1, total_pages + 1):
        page_url = f"{category_url}?p={page}" if page > 1 else category_url
        
        if page % 10 == 0:
            print(f"  Page {page}/{total_pages}...")
        
        manuals = get_manual_links_from_page(session, page_url)
        all_manuals.extend(manuals)
        
        time.sleep(0.5)  # Be polite
    
    print(f"Found {len(all_manuals)} manuals for {category_name}")
    return all_manuals

def is_rate_limited(page):
    """Check if we're being rate limited by looking at page content"""
    try:
        body_text = page.evaluate('() => document.body.innerText.toLowerCase()')
        indicators = ['too many requests', 'rate limit', 'please wait', 'try again', 'blocked', 'captcha']
        return any(ind in body_text for ind in indicators)
    except:
        return False

def extract_manual_content(page, manual_url, start_page=1, max_pages=None, verbose=True):
    """
    Extract text content using Playwright - chunked extraction with memory monitoring.
    
    Returns: (content, total_pages, last_page_extracted, needs_restart)
    - content: extracted text
    - total_pages: total pages in manual
    - last_page_extracted: last page we successfully got (for resume)
    - needs_restart: True if memory is high and browser should restart
    """
    start_time = time.time()
    
    def log(msg):
        if verbose:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.1f}s] {msg}", end=" ", flush=True)
    
    try:
        log("loading")
        page.goto(manual_url, wait_until='domcontentloaded', timeout=10000)
        time.sleep(0.5 + random.random() * 0.3)
        
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
        
        end_page = total_pages if max_pages is None else min(start_page + max_pages - 1, total_pages)
        all_content = []
        last_page = start_page - 1
        needs_restart = False
        consecutive_failures = 0
        
        for page_num in range(start_page, end_page + 1):
            page_url = f"{manual_url}?p={page_num}"
            page_start = time.time()
            
            try:
                if page_num == start_page or page_num % 10 == 0:
                    log(f"p{page_num}/{total_pages}")
                else:
                    log(f"p{page_num}")
                
                page.goto(page_url, wait_until='domcontentloaded', timeout=8000)
                time.sleep(0.2 + random.random() * 0.2)
                page.wait_for_selector('.viewer-page', timeout=5000)
                
                text_content = page.eval_on_selector('.viewer-page', '(element) => element.innerText')
                
                if text_content and len(text_content.strip()) > 30:
                    all_content.append(f"--- Page {page_num} ---\n{text_content.strip()}")
                    last_page = page_num
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                
                # Check if this page took too long
                page_time = time.time() - page_start
                if page_time > MAX_PAGE_TIME:
                    log(f"slow({page_time:.1f}s)")
                
                # Check memory every PAGES_PER_CHUNK pages
                if page_num % PAGES_PER_CHUNK == 0:
                    browser_mem = get_browser_memory_mb()
                    sys_mem = get_system_memory_percent()
                    log(f"[mem:{browser_mem:.0f}MB/{sys_mem:.0f}%]")
                    if browser_mem > MAX_BROWSER_MEMORY_MB or sys_mem > MAX_SYSTEM_MEMORY_PCT:
                        log(f"HIGH-MEM!")
                        needs_restart = True
                        break
                
                # Too many consecutive failures = probably rate limited
                if consecutive_failures >= 5:
                    log("5-fails")
                    needs_restart = True
                    break
                    
            except Exception as e:
                log("x")
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    needs_restart = True
                    break
                continue
        
        content = "\n\n".join(all_content) if all_content else None
        return content, total_pages, last_page, needs_restart
        
    except Exception as e:
        log(f"ERR:{str(e)[:30]}")
        return None, 0, 0, True

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def run_full_scraper():
    progress = load_progress()
    
    print("=" * 60)
    print("FULL HYBRID SCRAPER")
    print("(requests for listings, Playwright for extraction)")
    print("=" * 60)
    
    # Create session for requests
    session = requests.Session()
    session.headers.update(HEADERS)
    
    categories = [
        ("laptops", LAPTOP_URL, 151),   # 15,193 manuals
        ("desktops", DESKTOP_URL, 51),  # 5,111 manuals
    ]
    
    # Phase 1: Get all manual URLs (use cache if available)
    cached = load_url_cache()
    if cached:
        print("Using cached URL list (delete manual_urls_cache.json to refresh)")
        all_manuals = cached
    else:
        all_manuals = {}
        for category_name, category_url, total_pages in categories:
            manuals = get_all_manual_urls(session, category_url, category_name, total_pages)
            all_manuals[category_name] = manuals
        save_url_cache(all_manuals)
        print("URL list cached for future runs")
    
    # Phase 2: Extract content using Playwright
    print("\n" + "=" * 60)
    print("EXTRACTING MANUAL CONTENT (FAST MODE)")
    print(f"(ALL pages, chunked by {PAGES_PER_CHUNK}, {DELAY_BETWEEN_MANUALS[0]}-{DELAY_BETWEEN_MANUALS[1]}s delay)")
    print("=" * 60)
    
    stats = {"success": 0, "failed": 0, "skipped": 0, "total_chars": 0}
    consecutive_empty = 0
    manuals_since_restart = 0
    current_backoff = RATE_LIMIT_BACKOFF
    failed_queue = []  # Track failed manuals for retry
    
    def create_browser(p):
        browser = p.chromium.launch(headless=True)  # Headless for speed
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        context.set_default_timeout(10000)  # 10s default timeout for all operations
        page = context.new_page()
        return browser, context, page
    
    with sync_playwright() as p:
        browser, context, page = create_browser(p)
        
        for category_name, manuals in all_manuals.items():
            print(f"\n{'='*60}")
            print(f"CATEGORY: {category_name.upper()} ({len(manuals)} manuals)")
            print(f"{'='*60}")
            
            for manual in manuals:
                manual_url = manual['url']
                brand = manual['brand']
                model = manual['model']
                
                # Skip if already done
                if manual_url in progress.get(category_name, []):
                    stats["skipped"] += 1
                    continue
                
                # Check memory and restart if needed
                manuals_since_restart += 1
                browser_mem = get_browser_memory_mb()
                sys_mem = get_system_memory_percent()
                
                if browser_mem > MAX_BROWSER_MEMORY_MB or sys_mem > MAX_SYSTEM_MEMORY_PCT or manuals_since_restart >= MANUALS_BEFORE_RESTART:
                    print(f"\n  [Browser restart: {browser_mem:.0f}MB browser, {sys_mem:.0f}% system]\n")
                    browser.close()
                    time.sleep(2)
                    browser, context, page = create_browser(p)
                    manuals_since_restart = 0
                
                # Smart rate limit detection after 3 empties
                if consecutive_empty >= 3:
                    if is_rate_limited(page):
                        print(f"\n  [RATE LIMITED - waiting {current_backoff}s, then retrying {len(failed_queue)} failed...]\n")
                        time.sleep(current_backoff)
                        current_backoff = min(current_backoff * 2, 180)  # Max 3 min
                    else:
                        print(f"\n  [3 empties - restarting browser, will retry {len(failed_queue)} failed...]\n")
                        time.sleep(5)
                    consecutive_empty = 0
                    browser.close()
                    time.sleep(2)
                    browser, context, page = create_browser(p)
                    manuals_since_restart = 0
                    
                    # Retry failed manuals after browser restart
                    if failed_queue:
                        print(f"  [Retrying {len(failed_queue)} failed manuals...]\n")
                        retry_list = failed_queue.copy()
                        failed_queue.clear()
                        
                        for retry_manual in retry_list:
                            r_url = retry_manual['url']
                            r_brand = retry_manual['brand']
                            r_model = retry_manual['model']
                            r_category = retry_manual['category']
                            
                            print(f"  RETRY: {r_brand} {r_model}...", end=" ", flush=True)
                            
                            try:
                                content, total_pages, last_page, _ = extract_manual_content(page, r_url)
                                
                                if content and len(content) > 100:
                                    r_output_dir = OUTPUT_DIR / r_category / r_brand
                                    r_output_dir.mkdir(parents=True, exist_ok=True)
                                    safe_brand = sanitize_filename(r_brand)
                                    safe_model = sanitize_filename(r_model)
                                    filename = f"{safe_brand}_{safe_model}_{total_pages}pages.txt"
                                    filepath = r_output_dir / filename
                                    
                                    with open(filepath, 'w', encoding='utf-8') as f:
                                        f.write(f"Brand: {r_brand}\n")
                                        f.write(f"Model: {r_model}\n")
                                        f.write(f"URL: {r_url}\n")
                                        f.write(f"Total Pages: {total_pages}\n")
                                        f.write("=" * 60 + "\n\n")
                                        f.write(content)
                                    
                                    stats["success"] += 1
                                    stats["failed"] -= 1
                                    stats["total_chars"] += len(content)
                                    current_backoff = RATE_LIMIT_BACKOFF
                                    print(f"OK ({len(content):,} chars)")
                                else:
                                    print("STILL EMPTY - skipping")
                                
                                time.sleep(random.uniform(2, 4))
                            except:
                                print("RETRY FAILED - skipping")
                        
                        print(f"  [Retry complete, continuing...]\n")
                
                # Create output directory
                output_dir = OUTPUT_DIR / category_name / brand
                output_dir.mkdir(parents=True, exist_ok=True)
                
                print(f"  {brand} {model}...", end=" ", flush=True)
                manual_start = time.time()
                
                try:
                    # Chunked extraction with memory monitoring
                    all_chunks = []
                    current_page = 1
                    total_pages = 0
                    extraction_complete = False
                    
                    while not extraction_complete:
                        content, total_pages, last_page, needs_restart = extract_manual_content(
                            page, manual_url, start_page=current_page
                        )
                        
                        if content:
                            all_chunks.append(content)
                        
                        # Check if we're done
                        if last_page >= total_pages:
                            extraction_complete = True
                        elif needs_restart:
                            # Memory high or failures - restart browser and continue
                            print(f"\n    [Chunk done: pages 1-{last_page}/{total_pages}, restarting browser...]", end=" ", flush=True)
                            browser.close()
                            time.sleep(2)
                            browser, context, page = create_browser(p)
                            manuals_since_restart = 0
                            current_page = last_page + 1
                            time.sleep(1)  # Brief pause before continuing
                        else:
                            extraction_complete = True
                    
                    elapsed = time.time() - manual_start
                    full_content = "\n\n".join(all_chunks) if all_chunks else None
                    
                    if full_content and len(full_content) > 100:
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
                            f.write(full_content)
                        
                        stats["success"] += 1
                        stats["total_chars"] += len(full_content)
                        consecutive_empty = 0
                        current_backoff = RATE_LIMIT_BACKOFF
                        print(f"OK ({len(full_content):,} chars, {total_pages}pg, {elapsed:.1f}s)")
                    else:
                        print(f"EMPTY ({elapsed:.1f}s)")
                        stats["failed"] += 1
                        consecutive_empty += 1
                        if len(failed_queue) < 10:
                            failed_queue.append({
                                'url': manual_url,
                                'brand': brand,
                                'model': model,
                                'category': category_name
                            })
                    
                    # Update progress
                    if category_name not in progress:
                        progress[category_name] = []
                    progress[category_name].append(manual_url)
                    save_progress(progress)
                    
                    # Varied random delay
                    if random.random() < 0.2:
                        delay = random.uniform(5, 8)
                    else:
                        delay = random.uniform(1.5, 4)
                    time.sleep(delay)
                    
                except Exception as e:
                    stats["failed"] += 1
                    consecutive_empty += 1
                    if len(failed_queue) < 10:
                        failed_queue.append({
                            'url': manual_url,
                            'brand': brand,
                            'model': model,
                            'category': category_name
                        })
                    print(f"ERROR: {str(e)[:40]}")
                    continue
                
                # Print stats periodically with memory info
                total = stats["success"] + stats["failed"]
                if total % 10 == 0 and total > 0:
                    rate = stats["success"] / total * 100
                    browser_mem = get_browser_memory_mb()
                    sys_mem = get_system_memory_percent()
                    print(f"\n  [Stats: {stats['success']} OK, {stats['failed']} fail ({rate:.0f}%) | Mem: {browser_mem:.0f}MB browser, {sys_mem:.0f}% system]\n")
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Total characters: {stats['total_chars']:,}")
    print("=" * 60)

if __name__ == "__main__":
    run_full_scraper()
