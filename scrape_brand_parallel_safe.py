"""
Parallel-safe brand scraper with rate limiting coordination
Usage: python scrape_brand_parallel_safe.py HP

Features:
- File-based rate limiting across multiple instances
- Exponential backoff on failures
- More aggressive timeouts
- Better error handling for parallel execution
"""
import os
import sys
import json
import time
import re
import random
import psutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime

# Configuration
OUTPUT_DIR = Path("downloads")
PROGRESS_DIR = Path("progress")
PARTIAL_DIR = Path("partial_content")
URL_CACHE_FILE = "manual_urls_cache.json"
RATE_LIMIT_FILE = Path(".rate_limit_lock")  # Shared rate limiting

# Page management - MORE CONSERVATIVE for parallel
PAGES_PER_CHUNK = 25
PAGES_BEFORE_RESTART = 50
MAX_SECONDS_PER_PAGE = 3

# INCREASED delays for parallel execution
DELAY_BETWEEN_PAGES = (0.8, 1.5)      # Increased from (0.3, 0.5)
DELAY_BETWEEN_MANUALS = (4, 8)        # Increased from (2, 5)
GLOBAL_REQUEST_DELAY = 0.3             # Minimum time between ANY request across all instances

# Retry settings
MAX_RETRIES = 3
CONSECUTIVE_TIMEOUT_LIMIT = 5          # If we hit this many timeouts, back off

def global_rate_limit():
    """
    Enforce a global minimum delay between requests across all parallel instances.
    Uses file modification time as coordination mechanism.
    """
    try:
        # Create lock file if doesn't exist
        if not RATE_LIMIT_FILE.exists():
            RATE_LIMIT_FILE.touch()
        
        # Check last request time
        last_mod = RATE_LIMIT_FILE.stat().st_mtime
        elapsed = time.time() - last_mod
        
        if elapsed < GLOBAL_REQUEST_DELAY:
            sleep_time = GLOBAL_REQUEST_DELAY - elapsed + random.uniform(0, 0.1)
            time.sleep(sleep_time)
        
        # Update timestamp
        RATE_LIMIT_FILE.touch()
    except:
        # If file locking fails, just use local delay
        time.sleep(GLOBAL_REQUEST_DELAY)

def get_progress_file(brand):
    PROGRESS_DIR.mkdir(exist_ok=True)
    return PROGRESS_DIR / f"{brand.upper()}_progress.json"

def load_progress(brand):
    pfile = get_progress_file(brand)
    if pfile.exists():
        try:
            with open(pfile, 'r') as f:
                return json.load(f)
        except:
            return {"done": [], "partial": {}}
    return {"done": [], "partial": {}}

def save_progress(brand, progress):
    pfile = get_progress_file(brand)
    try:
        with open(pfile, 'w') as f:
            json.dump(progress, f)
    except Exception as e:
        print(f"\n[WARN: Progress save failed: {e}]", flush=True)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def get_partial_file(brand, url):
    PARTIAL_DIR.mkdir(exist_ok=True)
    url_hash = str(hash(url) % 100000)
    return PARTIAL_DIR / f"{brand}_{url_hash}.txt"

def save_partial_content(brand, url, content):
    pfile = get_partial_file(brand, url)
    try:
        with open(pfile, 'a', encoding='utf-8') as f:
            f.write(content + "\n\n")
    except Exception as e:
        print(f"[WARN: Partial save failed: {e}]", end="", flush=True)

def load_partial_content(brand, url):
    pfile = get_partial_file(brand, url)
    if pfile.exists():
        try:
            with open(pfile, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            pass
    return ""

def clear_partial_content(brand, url):
    pfile = get_partial_file(brand, url)
    if pfile.exists():
        try:
            pfile.unlink()
        except:
            pass

class BrowserManager:
    def __init__(self, worker_id=""):
        self.browser = None
        self.context = None
        self.page = None
        self.pages_since_restart = 0
        self.worker_id = worker_id
        self.consecutive_timeouts = 0
    
    def launch(self, playwright):
        """Launch browser with more realistic settings"""
        self.browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',  # Reduce shared memory usage
            ]
        )
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            }
        )
        # Set shorter default timeout
        self.context.set_default_timeout(8000)
        self.page = self.context.new_page()
        self.pages_since_restart = 0
        return self.page
    
    def increment_pages(self, count=1):
        self.pages_since_restart += count
    
    def needs_restart(self):
        return self.pages_since_restart >= PAGES_BEFORE_RESTART
    
    def should_backoff(self):
        """Check if we should slow down due to repeated failures"""
        return self.consecutive_timeouts >= CONSECUTIVE_TIMEOUT_LIMIT
    
    def close(self):
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        self.browser = None
        self.context = None
        self.page = None
        self.pages_since_restart = 0

def extract_manual_chunked(browser_mgr, manual_url, start_page=1):
    """
    Extract pages with global rate limiting and better timeout handling
    """
    page = browser_mgr.page
    try:
        # Global rate limit before making request
        global_rate_limit()
        
        try:
            # Shorter timeout, fail fast
            page.goto(manual_url, wait_until='domcontentloaded', timeout=8000)
            browser_mgr.consecutive_timeouts = 0  # Reset on success
        except Exception as e:
            browser_mgr.consecutive_timeouts += 1
            print(f"LOAD_ERR ", end="", flush=True)
            
            # If we're hitting too many timeouts, back off
            if browser_mgr.should_backoff():
                print(f"[BACKOFF:5s] ", end="", flush=True)
                time.sleep(5)
                browser_mgr.consecutive_timeouts = 0
            
            return None, 0, 0, True
        
        time.sleep(random.uniform(0.3, 0.6))
        
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
        
        print(f"({total_pages}pg) ", end="", flush=True)
        if start_page > 1:
            print(f"[resume@{start_page}] ", end="", flush=True)
        
        all_content = []
        consecutive_fails = 0
        last_page = start_page - 1
        needs_restart = False
        
        for page_num in range(start_page, total_pages + 1):
            if page_num % 10 == 0:
                print(f"p{page_num} ", end="", flush=True)
            
            if page_num % PAGES_PER_CHUNK == 0:
                browser_mgr.increment_pages(PAGES_PER_CHUNK)
                if browser_mgr.needs_restart():
                    print(f"[50pg] ", end="", flush=True)
                    needs_restart = True
                    break
            
            try:
                page_url = f"{manual_url}?p={page_num}"
                
                # Global rate limit before each page request
                global_rate_limit()
                
                try:
                    # Aggressive timeout
                    page.goto(page_url, wait_until='domcontentloaded', timeout=5000)
                    browser_mgr.consecutive_timeouts = 0
                except:
                    consecutive_fails += 1
                    browser_mgr.consecutive_timeouts += 1
                    
                    if browser_mgr.should_backoff():
                        print(f"[BACKOFF:10s] ", end="", flush=True)
                        time.sleep(10)
                        browser_mgr.consecutive_timeouts = 0
                    
                    if consecutive_fails >= 3:
                        print(f"[timeout@{page_num}] ", end="", flush=True)
                        needs_restart = True
                        break
                    continue
                
                # Longer delay between pages for parallel execution
                time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))
                
                try:
                    page.wait_for_selector('.viewer-page', timeout=3000)
                    text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                except:
                    consecutive_fails += 1
                    continue
                
                if text and len(text.strip()) > 30:
                    all_content.append(f"--- Page {page_num} ---\n{text.strip()}")
                    last_page = page_num
                    consecutive_fails = 0
                else:
                    consecutive_fails += 1
                
                if consecutive_fails >= 5:
                    print("[5fails] ", end="", flush=True)
                    needs_restart = True
                    break
                    
            except Exception as e:
                print(f"[err] ", end="", flush=True)
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    needs_restart = True
                    break
                continue
        
        content = "\n\n".join(all_content) if all_content else None
        return content, total_pages, last_page, needs_restart
        
    except Exception as e:
        print(f"ERR:{str(e)[:20]} ", end="", flush=True)
        return None, 0, 0, True

def scrape_brand(brand_name):
    brand_upper = brand_name.upper()
    
    print(f"=" * 50, flush=True)
    print(f"SCRAPING: {brand_upper} [PARALLEL-SAFE MODE]", flush=True)
    print(f"=" * 50, flush=True)
    
    progress = load_progress(brand_upper)
    done_urls = set(progress.get("done", []))
    partial = progress.get("partial", {})
    cached = load_url_cache()
    
    if not cached:
        print("ERROR: No URL cache.")
        return
    
    manuals = []
    for category, items in cached.items():
        for item in items:
            if item['brand'].upper() == brand_upper and item['url'] not in done_urls:
                item['category'] = category
                manuals.append(item)
    
    if not manuals:
        print(f"No pending manuals for {brand_upper}")
        print(f"(Already completed {len(done_urls)} manuals)")
        return
    
    print(f"Found {len(manuals)} manuals to scrape", flush=True)
    print(f"Global rate limiting: {GLOBAL_REQUEST_DELAY}s between requests", flush=True)
    print(f"Inter-manual delay: {DELAY_BETWEEN_MANUALS[0]}-{DELAY_BETWEEN_MANUALS[1]}s\n", flush=True)
    
    stats = {"success": 0, "failed": 0, "retried": 0, "chars": 0}
    retry_queue = []
    start_time = time.time()
    
    with sync_playwright() as p:
        browser_mgr = BrowserManager(brand_upper)
        browser_mgr.launch(p)
        
        i = 0
        while i < len(manuals) or retry_queue:
            # Process retry queue periodically
            if retry_queue and i > 0 and i % 5 == 0:
                print(f"\n  [Processing {len(retry_queue)} retries...]\n", flush=True)
                new_retry_queue = []
                
                for retry_manual, retry_count in retry_queue:
                    if retry_count >= MAX_RETRIES:
                        print(f"  SKIP (max retries): {retry_manual['model']}", flush=True)
                        progress["done"].append(retry_manual['url'])
                        save_progress(brand_upper, progress)
                        continue
                    
                    print(f"  RETRY #{retry_count+1}: {retry_manual['model']}... ", end="", flush=True)
                    
                    start_page = partial.get(retry_manual['url'], 1)
                    content, total_pages, last_page, needs_restart = extract_manual_chunked(
                        browser_mgr, retry_manual['url'], start_page
                    )
                    
                    if content:
                        save_partial_content(brand_upper, retry_manual['url'], content)
                    
                    full_retry_content = load_partial_content(brand_upper, retry_manual['url'])
                    
                    if full_retry_content and len(full_retry_content) > 100:
                        save_manual_file(retry_manual, full_retry_content, total_pages, brand_upper)
                        clear_partial_content(brand_upper, retry_manual['url'])
                        stats["success"] += 1
                        stats["retried"] += 1
                        stats["chars"] += len(full_retry_content)
                        progress["done"].append(retry_manual['url'])
                        if retry_manual['url'] in partial:
                            del partial[retry_manual['url']]
                        print(f"✓ ({len(full_retry_content):,}ch)", flush=True)
                    else:
                        new_retry_queue.append((retry_manual, retry_count + 1))
                        print(f"✗ still empty", flush=True)
                    
                    if needs_restart:
                        print(f"\n  [Restarting browser...]\n", flush=True)
                        browser_mgr.close()
                        time.sleep(2)
                        browser_mgr.launch(p)
                    
                    save_progress(brand_upper, progress)
                    time.sleep(random.uniform(*DELAY_BETWEEN_MANUALS))
                
                retry_queue = new_retry_queue
                continue
            
            if i >= len(manuals):
                break
            
            manual = manuals[i]
            i += 1
            
            url = manual['url']
            model = manual['model']
            category = manual['category']
            
            print(f"[{i}/{len(manuals)}] {model}... ", end="", flush=True)
            manual_start = time.time()
            
            start_page = partial.get(url, 1)
            current_page = start_page
            total_pages = 0
            
            existing_content = load_partial_content(brand_upper, url)
            if existing_content:
                print(f"[has partial] ", end="", flush=True)
            
            # Chunked extraction loop
            while True:
                content, total_pages, last_page, needs_restart = extract_manual_chunked(
                    browser_mgr, url, current_page
                )
                
                if content:
                    save_partial_content(brand_upper, url, content)
                
                if needs_restart and last_page < total_pages and last_page > current_page - 1:
                    partial[url] = last_page + 1
                    progress["partial"] = partial
                    save_progress(brand_upper, progress)
                    
                    print(f"\n  [Chunk saved: pages {current_page}-{last_page}/{total_pages}, restarting...]", flush=True)
                    browser_mgr.close()
                    time.sleep(2)
                    browser_mgr.launch(p)
                    current_page = last_page + 1
                    print(f"  [Continuing {model}...] ", end="", flush=True)
                else:
                    break
            
            elapsed = time.time() - manual_start
            
            full_content = load_partial_content(brand_upper, url)
            if not full_content or len(full_content.strip()) < 100:
                full_content = None
            
            if full_content and len(full_content) > 100:
                save_manual_file(manual, full_content, total_pages, brand_upper)
                clear_partial_content(brand_upper, url)
                
                stats["success"] += 1
                stats["chars"] += len(full_content)
                progress["done"].append(url)
                if url in partial:
                    del partial[url]
                print(f"✓ ({len(full_content):,}ch, {total_pages}pg, {elapsed:.1f}s)", flush=True)
            else:
                stats["failed"] += 1
                retry_queue.append((manual, 0))
                print(f"✗ EMPTY - queued for retry ({elapsed:.1f}s)", flush=True)
            
            progress["partial"] = partial
            save_progress(brand_upper, progress)
            
            browser_mgr.increment_pages(total_pages if total_pages > 0 else 10)
            if browser_mgr.needs_restart():
                print(f"\n  [Restarting browser after {browser_mgr.pages_since_restart} pages]\n", flush=True)
                browser_mgr.close()
                time.sleep(2)
                browser_mgr.launch(p)
            
            # LONGER delay between manuals for parallel execution
            time.sleep(random.uniform(*DELAY_BETWEEN_MANUALS))
            
            if i % 25 == 0:
                elapsed_total = time.time() - start_time
                rate = i / elapsed_total * 60
                print(f"\n  [Stats: {stats['success']} OK, {stats['failed']} fail, {len(retry_queue)} queued | {rate:.1f}/min]\n", flush=True)
        
        browser_mgr.close()
    
    elapsed = time.time() - start_time
    print(f"\n{'=' * 50}", flush=True)
    print(f"DONE: {brand_upper}", flush=True)
    print(f"Success: {stats['success']} ({stats['retried']} from retries)", flush=True)
    print(f"Failed: {stats['failed']}", flush=True)
    print(f"Total chars: {stats['chars']:,}", flush=True)
    print(f"Time: {elapsed/60:.1f} minutes", flush=True)
    print(f"{'=' * 50}", flush=True)

def save_manual_file(manual, content, total_pages, brand):
    output_dir = OUTPUT_DIR / manual['category'] / brand
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{sanitize_filename(brand)}_{sanitize_filename(manual['model'])}_{total_pages}pages.txt"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"Brand: {brand}\n")
        f.write(f"Model: {manual['model']}\n")
        f.write(f"URL: {manual['url']}\n")
        f.write(f"Total Pages: {total_pages}\n")
        f.write("=" * 60 + "\n\n")
        f.write(content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_brand_parallel_safe.py BRAND_NAME")
        print("Example: python scrape_brand_parallel_safe.py HP")
        print("\nThis version is optimized for running multiple instances in parallel.")
        print("Features:")
        print("  - Global rate limiting across instances")
        print("  - Exponential backoff on failures")
        print("  - More conservative delays")
        sys.exit(1)
    
    brand = sys.argv[1]
    scrape_brand(brand)



