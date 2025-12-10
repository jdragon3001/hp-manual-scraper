"""
Scrape a single brand with OCR fallback for image-based manuals
Usage: python scrape_brand_with_ocr.py ATARI

Features:
- Text extraction for HTML-based manuals
- OCR fallback for image-based manuals (like ATARI)
- Chunked extraction with memory management
- Retry queue for failed manuals
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
import requests
from PIL import Image
from io import BytesIO
import pytesseract

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuration
OUTPUT_DIR = Path("downloads")
PROGRESS_DIR = Path("progress")
PARTIAL_DIR = Path("partial_content")
URL_CACHE_FILE = "manual_urls_cache.json"

# Page management  
PAGES_PER_CHUNK = 25
PAGES_BEFORE_RESTART = 50
MAX_SECONDS_PER_PAGE = 5
DELAY_BETWEEN_PAGES = (0.3, 0.6)
PAGE_LOAD_TIMEOUT = 8000

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
    return {"done": [], "partial": {}}

def save_progress(brand, progress):
    pfile = get_progress_file(brand)
    with open(pfile, 'w') as f:
        json.dump(progress, f, indent=2)

def load_url_cache():
    if Path(URL_CACHE_FILE).exists():
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_partial_filename(brand, url):
    url_hash = abs(hash(url))
    return PARTIAL_DIR / f"{brand}_{url_hash}.txt"

def save_partial_content(brand, url, content):
    PARTIAL_DIR.mkdir(exist_ok=True)
    pfile = get_partial_filename(brand, url)
    with open(pfile, 'a', encoding='utf-8') as f:
        f.write(content + "\n\n")

def load_partial_content(brand, url):
    pfile = get_partial_filename(brand, url)
    if pfile.exists():
        with open(pfile, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def clear_partial_content(brand, url):
    pfile = get_partial_filename(brand, url)
    if pfile.exists():
        pfile.unlink()

def save_manual_file(manual, content, total_pages, brand):
    category = manual['category']
    model = manual['model']
    
    # Clean model name for filename
    safe_model = re.sub(r'[<>:"/\\|?*]', '_', model)
    safe_brand = re.sub(r'[<>:"/\\|?*]', '_', brand)
    
    output_path = OUTPUT_DIR / category / safe_brand
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{safe_brand}_{safe_model}_{total_pages}pages.txt"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

class BrowserManager:
    def __init__(self):
        self.browser = None
        self.page = None
        self.pages_processed = 0
        self.process = psutil.Process()
        
    def launch(self, playwright):
        self.browser = playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.pages_processed = 0
        
    def close(self):
        if self.browser:
            self.browser.close()
        self.browser = None
        self.page = None
        
    def increment_pages(self, count):
        self.pages_processed += count
        
    def needs_restart(self):
        return self.pages_processed >= PAGES_BEFORE_RESTART

def extract_text_from_page(page, page_url):
    """Try to extract text using standard method"""
    try:
        page.goto(page_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
        time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))
        
        text = None
        try:
            page.wait_for_selector('.viewer-page', timeout=3000)
            page.set_default_timeout(3000)
            text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
        except:
            try:
                page.set_default_timeout(3000)
                text = page.evaluate('() => document.body.innerText')
            except:
                pass
        
        if text and len(text.strip()) > 30:
            return text.strip(), 'text'
        return None, None
    except Exception as e:
        return None, None

def extract_image_url_from_page(page):
    """Extract background image URL from page"""
    try:
        image_url = page.evaluate('''() => {
            const bi = document.querySelector('.bi');
            if (!bi) return null;
            const style = window.getComputedStyle(bi);
            const bgImage = style.backgroundImage;
            if (!bgImage || bgImage === 'none') return null;
            const match = bgImage.match(/url\\(["']?([^"')]+)["']?\\)/);
            return match ? match[1] : null;
        }''')
        return image_url
    except:
        return None

def ocr_from_image_url(image_url):
    """Download image and extract text using OCR"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
        
        # Convert to PIL Image
        img = Image.open(BytesIO(response.content))
        
        # Perform OCR
        text = pytesseract.image_to_string(img, config='--psm 1 --oem 3')
        
        if text and len(text.strip()) > 30:
            return text.strip()
        return None
    except Exception as e:
        print(f"[OCR_ERR:{str(e)[:20]}] ", end="", flush=True)
        return None

def extract_manual_with_ocr_fallback(browser_mgr, manual_url, start_page=1):
    """
    Extract manual pages with automatic OCR fallback for image-based manuals
    """
    try:
        page = browser_mgr.page
        
        # Get total pages
        page.goto(manual_url, wait_until='domcontentloaded', timeout=10000)
        time.sleep(1)
        
        total_pages = 1
        try:
            # Try multiple methods to detect page count
            total_pages = page.evaluate('''() => {
                // Method 1: Look for "X pages" in the page
                const pageText = document.body.innerText;
                let match = pageText.match(/(\\d+)\\s*pages?/i);
                if (match) return parseInt(match[1]);
                
                // Method 2: Look for "X / Y" format in navigation
                match = pageText.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                if (match) return parseInt(match[2]);
                
                // Method 3: Look in title
                const title = document.title;
                match = title.match(/\\((\\d+)\\s*pages?\\)/i);
                if (match) return parseInt(match[1]);
                
                return 1;
            }''')
            
            if total_pages == 1:
                # Fallback: try getting from page title directly
                title = page.title()
                import re
                match = re.search(r'\((\d+)\s*pages?\)', title, re.IGNORECASE)
                if match:
                    total_pages = int(match.group(1))
        except Exception as e:
            print(f"[page_detect_err:{str(e)[:20]}] ", end="", flush=True)
            pass
        
        print(f"({total_pages}pg) ", end="", flush=True)
        if start_page > 1:
            print(f"[resume@{start_page}] ", end="", flush=True)
        
        all_content = []
        consecutive_fails = 0
        last_page = start_page - 1
        needs_restart = False
        use_ocr = False  # Will be set to True if we detect image-based manual
        
        for page_num in range(start_page, total_pages + 1):
            page_start_time = time.time()
            
            # Show progress every 10 pages
            if page_num % 10 == 0:
                print(f"p{page_num} ", end="", flush=True)
            
            # Check every PAGES_PER_CHUNK pages if we should restart
            if page_num % PAGES_PER_CHUNK == 0:
                browser_mgr.increment_pages(PAGES_PER_CHUNK)
                if browser_mgr.needs_restart():
                    print(f"[{page_num}pg] ", end="", flush=True)
                    needs_restart = True
                    break
            
            try:
                page_url = f"{manual_url}?p={page_num}"
                
                # Try text extraction first (unless we already know it's OCR-based)
                if not use_ocr:
                    text, method = extract_text_from_page(page, page_url)
                    
                    if text:
                        all_content.append(f"--- Page {page_num} ---\n{text}")
                        last_page = page_num
                        consecutive_fails = 0
                        continue
                    
                    # If first 3 pages are empty, switch to OCR mode
                    if page_num <= 3:
                        consecutive_fails += 1
                        if consecutive_fails >= 3:
                            print(f"[→OCR] ", end="", flush=True)
                            use_ocr = True
                            consecutive_fails = 0
                            # Retry this page with OCR
                            page_num -= 1
                            continue
                
                # Try OCR extraction
                if use_ocr:
                    page.goto(page_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
                    time.sleep(0.5)
                    
                    image_url = extract_image_url_from_page(page)
                    if image_url:
                        if page_num % 10 == 1:  # Show OCR indicator occasionally
                            print(f"[OCR] ", end="", flush=True)
                        
                        text = ocr_from_image_url(image_url)
                        if text:
                            all_content.append(f"--- Page {page_num} ---\n{text}")
                            last_page = page_num
                            consecutive_fails = 0
                        else:
                            consecutive_fails += 1
                    else:
                        consecutive_fails += 1
                
                # Check for too many failures
                if consecutive_fails >= 5:
                    print(f"[5fails@{page_num}] ", end="", flush=True)
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
        extraction_method = "OCR" if use_ocr else "TEXT"
        return content, total_pages, last_page, needs_restart, extraction_method
        
    except Exception as e:
        print(f"ERR:{str(e)[:20]} ", end="", flush=True)
        return None, 0, 0, True, "ERROR"

def scrape_brand(brand_name):
    brand_upper = brand_name.upper()
    
    print(f"=" * 50, flush=True)
    print(f"SCRAPING: {brand_upper} (with OCR fallback)", flush=True)
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
    
    stats = {"success": 0, "failed": 0, "retried": 0, "chars": 0, "ocr_count": 0, "text_count": 0}
    retry_queue = []
    start_time = time.time()
    
    with sync_playwright() as p:
        browser_mgr = BrowserManager()
        browser_mgr.launch(p)
        
        i = 0
        while i < len(manuals) or retry_queue:
            # Process retry queue
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
                    content, total_pages, last_page, needs_restart, method = extract_manual_with_ocr_fallback(
                        browser_mgr, retry_manual['url'], start_page
                    )
                    
                    if content:
                        save_partial_content(brand_upper, retry_manual['url'], content)
                    
                    if content and len(content) > 100:
                        full_content = load_partial_content(brand_upper, retry_manual['url'])
                        save_manual_file(retry_manual, full_content, total_pages, brand_upper)
                        clear_partial_content(brand_upper, retry_manual['url'])
                        progress["done"].append(retry_manual['url'])
                        if retry_manual['url'] in partial:
                            del partial[retry_manual['url']]
                        stats["success"] += 1
                        stats["retried"] += 1
                        if method == "OCR":
                            stats["ocr_count"] += 1
                        else:
                            stats["text_count"] += 1
                        print(f"✓ [{method}]", flush=True)
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
            
            start_page = partial.get(url, 1)
            current_page = start_page
            total_pages = 0
            extraction_method = "TEXT"
            
            existing_content = load_partial_content(brand_upper, url)
            if existing_content:
                print(f"[has partial] ", end="", flush=True)
            
            # Chunked extraction loop
            while True:
                content, total_pages, last_page, needs_restart, method = extract_manual_with_ocr_fallback(
                    browser_mgr, url, current_page
                )
                
                extraction_method = method
                
                if content:
                    save_partial_content(brand_upper, url, content)
                
                if needs_restart and last_page < total_pages and last_page > current_page - 1:
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
                    break
            
            elapsed = time.time() - manual_start
            
            # Combine all content
            full_content = load_partial_content(brand_upper, url)
            if not full_content or len(full_content.strip()) < 100:
                full_content = None
            
            if full_content and len(full_content) > 100:
                save_manual_file(manual, full_content, total_pages, brand_upper)
                clear_partial_content(brand_upper, url)
                
                stats["success"] += 1
                stats["chars"] += len(full_content)
                if extraction_method == "OCR":
                    stats["ocr_count"] += 1
                else:
                    stats["text_count"] += 1
                print(f"✓ [{extraction_method}] ({elapsed:.1f}s)", flush=True)
                progress["done"].append(url)
                if url in partial:
                    del partial[url]
            else:
                print(f"✗ EMPTY - queued for retry ({elapsed:.1f}s)", flush=True)
                retry_queue.append((manual, 0))
            
            progress["partial"] = partial
            save_progress(brand_upper, progress)
            
            if needs_restart:
                print(f"\n  [Restarting browser after {browser_mgr.pages_processed} pages]\n", flush=True)
                browser_mgr.close()
                time.sleep(1)
                browser_mgr.launch(p)
            
            time.sleep(random.uniform(0.5, 1))
        
        browser_mgr.close()
    
    elapsed_minutes = (time.time() - start_time) / 60
    
    print(f"\n{'='*50}", flush=True)
    print(f"DONE: {brand_upper}", flush=True)
    print(f"Success: {stats['success']} ({stats['retried']} from retries)", flush=True)
    print(f"  - Text extraction: {stats['text_count']}", flush=True)
    print(f"  - OCR extraction: {stats['ocr_count']}", flush=True)
    print(f"Failed: {stats['failed']}", flush=True)
    print(f"Total chars: {stats['chars']:,}", flush=True)
    print(f"Time: {elapsed_minutes:.1f} minutes", flush=True)
    print(f"{'='*50}", flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_brand_with_ocr.py <BRAND>")
        print("Example: python scrape_brand_with_ocr.py ATARI")
        sys.exit(1)
    
    brand = sys.argv[1]
    scrape_brand(brand)

