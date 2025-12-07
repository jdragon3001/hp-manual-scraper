"""
Scrape a single brand - run multiple instances in separate terminals for parallelism
Usage: python scrape_brand.py HP
       python scrape_brand.py DELL

Features:
- Chunked extraction (handles memory mid-manual)
- Retry queue for failed manuals
- Memory-based browser restart at 1.5GB
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

# Configuration
OUTPUT_DIR = Path("downloads")
PROGRESS_DIR = Path("progress")
PARTIAL_DIR = Path("partial_content")  # Store partial extractions
URL_CACHE_FILE = "manual_urls_cache.json"

# Page management  
PAGES_PER_CHUNK = 25          # Check every N pages
PAGES_BEFORE_RESTART = 50     # Restart browser more frequently (was 100)
MAX_SECONDS_PER_PAGE = 3      # If a page takes longer than this, something's wrong
DELAY_BETWEEN_PAGES = (0.3, 0.5)

# Retry settings
MAX_RETRIES = 3

def get_progress_file(brand):
    PROGRESS_DIR.mkdir(exist_ok=True)
    return PROGRESS_DIR / f"{brand.upper()}_progress.json"

def load_progress(brand):
    pfile = get_progress_file(brand)
    if pfile.exists():
        with open(pfile, 'r') as f:
            return json.load(f)
    return {"done": [], "partial": {}}  # partial stores {url: last_page_extracted}

def save_progress(brand, progress):
    pfile = get_progress_file(brand)
    with open(pfile, 'w') as f:
        json.dump(progress, f)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def get_partial_file(brand, url):
    """Get path to partial content file for a manual"""
    PARTIAL_DIR.mkdir(exist_ok=True)
    url_hash = str(hash(url) % 100000)  # Simple hash for filename
    return PARTIAL_DIR / f"{brand}_{url_hash}.txt"

def save_partial_content(brand, url, content):
    """Append content to partial file"""
    pfile = get_partial_file(brand, url)
    with open(pfile, 'a', encoding='utf-8') as f:
        f.write(content + "\n\n")

def load_partial_content(brand, url):
    """Load any existing partial content"""
    pfile = get_partial_file(brand, url)
    if pfile.exists():
        with open(pfile, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def clear_partial_content(brand, url):
    """Delete partial content file when done"""
    pfile = get_partial_file(brand, url)
    if pfile.exists():
        pfile.unlink()

class BrowserManager:
    """Manages browser lifecycle and tracks memory"""
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.pages_since_restart = 0
    
    def launch(self, playwright):
        """Launch browser"""
        self.browser = playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = self.context.new_page()
        self.pages_since_restart = 0
        return self.page
    
    def increment_pages(self, count=1):
        """Track pages extracted"""
        self.pages_since_restart += count
    
    def needs_restart(self):
        """Check if we should restart based on pages extracted"""
        return self.pages_since_restart >= PAGES_BEFORE_RESTART
    
    def close(self):
        """Close browser"""
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
    Extract pages from a manual with page-count based restart.
    Returns: (content, total_pages, last_page_extracted, needs_restart)
    """
    page = browser_mgr.page
    try:
        try:
            page.goto(manual_url, wait_until='domcontentloaded', timeout=12000)
        except Exception as e:
            print(f"LOAD_ERR ", end="", flush=True)
            return None, 0, 0, True
        
        time.sleep(0.3)
        
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
            page_start_time = time.time()
            
            # Show progress every 10 pages
            if page_num % 10 == 0:
                print(f"p{page_num} ", end="", flush=True)
            
            # Check every PAGES_PER_CHUNK pages if we should restart
            if page_num % PAGES_PER_CHUNK == 0:
                browser_mgr.increment_pages(PAGES_PER_CHUNK)
                if browser_mgr.needs_restart():
                    print(f"[50pg] ", end="", flush=True)
                    needs_restart = True
                    break
            
            try:
                page_url = f"{manual_url}?p={page_num}"
                
                # Aggressive timeout - if page doesn't load in 6s, skip it
                try:
                    page.goto(page_url, wait_until='domcontentloaded', timeout=6000)
                except:
                    consecutive_fails += 1
                    if consecutive_fails >= 3:
                        print(f"[timeout@{page_num}] ", end="", flush=True)
                        needs_restart = True
                        break
                    continue
                
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
                
                # Check if this page took too long (browser might be getting sluggish)
                page_time = time.time() - page_start_time
                if page_time > MAX_SECONDS_PER_PAGE * 2:
                    print(f"[slow:{page_time:.1f}s] ", end="", flush=True)
                
                if consecutive_fails >= 5:
                    print("[5fails] ", end="", flush=True)
                    needs_restart = True
                    break
                    
            except Exception as e:
                print(f"[err] ", end="", flush=True)
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    print(f"[3errs@{page_num}] ", end="", flush=True)
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
    print(f"SCRAPING: {brand_upper}", flush=True)
    print(f"=" * 50, flush=True)
    
    # Load data
    progress = load_progress(brand_upper)
    done_urls = set(progress.get("done", []))
    partial = progress.get("partial", {})
    cached = load_url_cache()
    
    if not cached:
        print("ERROR: No URL cache. Run full_scraper_playwright.py first to build cache.")
        return
    
    # Find manuals for this brand
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
    print(f"First manual: {manuals[0]['model']}", flush=True)
    print(f"URL: {manuals[0]['url']}\n", flush=True)
    
    stats = {"success": 0, "failed": 0, "retried": 0, "chars": 0}
    retry_queue = []  # [(manual, retry_count)]
    start_time = time.time()
    
    with sync_playwright() as p:
        browser_mgr = BrowserManager()
        browser_mgr.launch(p)
        
        i = 0
        while i < len(manuals) or retry_queue:
            # Process retry queue first if we have items and just restarted browser
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
                    
                    # Check if we have partial progress
                    start_page = partial.get(retry_manual['url'], 1)
                    
                    content, total_pages, last_page, needs_restart = extract_manual_chunked(
                        browser_mgr, retry_manual['url'], start_page
                    )
                    
                    # Save chunk if we got content
                    if content:
                        save_partial_content(brand_upper, retry_manual['url'], content)
                    
                    # Load full content
                    full_retry_content = load_partial_content(brand_upper, retry_manual['url'])
                    
                    if full_retry_content and len(full_retry_content) > 100:
                        # Save file
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
                        time.sleep(1)
                        browser_mgr.launch(p)
                    
                    save_progress(brand_upper, progress)
                    time.sleep(random.uniform(1, 2))
                
                retry_queue = new_retry_queue
                continue
            
            # Get next manual
            if i >= len(manuals):
                break
            
            manual = manuals[i]
            i += 1
            
            url = manual['url']
            model = manual['model']
            category = manual['category']
            
            print(f"[{i}/{len(manuals)}] {model}... ", end="", flush=True)
            manual_start = time.time()
            
            # Check if we have partial progress for this manual
            start_page = partial.get(url, 1)
            current_page = start_page
            total_pages = 0
            
            # Load any existing partial content from previous sessions
            existing_content = load_partial_content(brand_upper, url)
            if existing_content:
                print(f"[has partial] ", end="", flush=True)
            
            # Chunked extraction loop
            while True:
                content, total_pages, last_page, needs_restart = extract_manual_chunked(
                    browser_mgr, url, current_page
                )
                
                if content:
                    # Save this chunk to partial file immediately
                    save_partial_content(brand_upper, url, content)
                
                if needs_restart and last_page < total_pages and last_page > current_page - 1:
                    # Save progress marker
                    partial[url] = last_page + 1
                    progress["partial"] = partial
                    save_progress(brand_upper, progress)
                    
                    print(f"\n  [Chunk saved: pages {current_page}-{last_page}/{total_pages}, restarting...]", flush=True)
                    browser_mgr.close()
                    time.sleep(1)
                    browser_mgr.launch(p)
                    current_page = last_page + 1
                    print(f"  [Continuing {model}...] ", end="", flush=True)
                else:
                    # Done with this manual (either complete or failed)
                    break
            
            elapsed = time.time() - manual_start
            
            # Combine existing partial + any new content
            full_content = load_partial_content(brand_upper, url)
            if not full_content or len(full_content.strip()) < 100:
                full_content = None
            
            if full_content and len(full_content) > 100:
                # Save file
                save_manual_file(manual, full_content, total_pages, brand_upper)
                
                # Clean up partial files
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
            
            # Update progress
            progress["partial"] = partial
            save_progress(brand_upper, progress)
            
            # Check if browser needs restart after this manual
            browser_mgr.increment_pages(total_pages if total_pages > 0 else 10)
            if browser_mgr.needs_restart():
                print(f"\n  [Restarting browser after {browser_mgr.pages_since_restart} pages]\n", flush=True)
                browser_mgr.close()
                time.sleep(1)
                browser_mgr.launch(p)
            
            # Random delay between manuals (longer to avoid rate limiting)
            time.sleep(random.uniform(2, 5))
            
            # Stats every 25 manuals
            if i % 25 == 0:
                elapsed_total = time.time() - start_time
                rate = i / elapsed_total * 60
                print(f"\n  [Stats: {stats['success']} OK, {stats['failed']} fail, {len(retry_queue)} queued | {rate:.1f}/min]\n", flush=True)
        
        browser_mgr.close()
    
    # Final stats
    elapsed = time.time() - start_time
    print(f"\n{'=' * 50}", flush=True)
    print(f"DONE: {brand_upper}", flush=True)
    print(f"Success: {stats['success']} ({stats['retried']} from retries)", flush=True)
    print(f"Failed: {stats['failed']}", flush=True)
    print(f"Total chars: {stats['chars']:,}", flush=True)
    print(f"Time: {elapsed/60:.1f} minutes", flush=True)
    print(f"{'=' * 50}", flush=True)

def save_manual_file(manual, content, total_pages, brand):
    """Save manual content to file"""
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
        print("Usage: python scrape_brand.py BRAND_NAME")
        print("Example: python scrape_brand.py HP")
        print("\nAvailable brands with most manuals:")
        print("  HP (4099), LENOVO (2651), ASUS (2449), SONY (2403)")
        print("  DELL (2047), ACER (1736), MSI (949), SAMSUNG (730)")
        sys.exit(1)
    
    brand = sys.argv[1]
    scrape_brand(brand)
