"""
Threaded scraper - runs multiple browser instances using threads
Works better on Windows than multiprocessing
"""
import os
import json
import time
import re
import random
import requests
import psutil
import threading
from bs4 import BeautifulSoup
from pathlib import Path
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

# Configuration
BASE_URL = "https://www.manua.ls"
LAPTOP_URL = f"{BASE_URL}/computers-and-accessories/laptops"
DESKTOP_URL = f"{BASE_URL}/computers-and-accessories/desktops"
OUTPUT_DIR = Path("downloads")
PROGRESS_FILE = "playwright_progress.json"
URL_CACHE_FILE = "manual_urls_cache.json"

# Parallel settings - adjust based on RAM
NUM_WORKERS = 3  # 3 parallel browsers
DELAY_BETWEEN_PAGES = (0.1, 0.3)  # Random delay between pages

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

# Thread-safe progress
progress_lock = threading.Lock()

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"laptops": [], "desktops": []}

def save_progress_safe(category, url):
    with progress_lock:
        progress = load_progress()
        if category not in progress:
            progress[category] = []
        if url not in progress[category]:
            progress[category].append(url)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def worker_scrape(worker_id, work_queue, results_queue, stop_event):
    """
    Worker thread - maintains its own browser and processes manuals from queue
    """
    print(f"  [Worker {worker_id}] Starting browser...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        manuals_processed = 0
        
        while not stop_event.is_set():
            try:
                # Get next manual (non-blocking with timeout)
                manual = work_queue.get(timeout=1)
            except:
                # Queue empty or timeout, check if we should stop
                if work_queue.empty():
                    break
                continue
            
            manual_url = manual['url']
            brand = manual['brand']
            model = manual['model']
            category = manual['category']
            
            output_dir = OUTPUT_DIR / category / brand
            output_dir.mkdir(parents=True, exist_ok=True)
            
            start_time = time.time()
            
            try:
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
                        time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))
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
                
                elapsed = time.time() - start_time
                
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
                    
                    save_progress_safe(category, manual_url)
                    results_queue.put((True, worker_id, brand, model, len(content), total_pages, elapsed))
                else:
                    save_progress_safe(category, manual_url)
                    results_queue.put((False, worker_id, brand, model, 0, total_pages, elapsed, "Empty"))
                    
            except Exception as e:
                save_progress_safe(category, manual_url)
                results_queue.put((False, worker_id, brand, model, 0, 0, time.time() - start_time, str(e)[:30]))
            
            manuals_processed += 1
            work_queue.task_done()
            
            # Restart browser every 50 manuals to prevent memory buildup
            if manuals_processed % 50 == 0:
                browser.close()
                time.sleep(1)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
        
        browser.close()
        print(f"  [Worker {worker_id}] Done ({manuals_processed} manuals)")

def run_threaded_scraper():
    print("=" * 60)
    print(f"THREADED SCRAPER ({NUM_WORKERS} workers)")
    print("=" * 60)
    
    # Load progress
    progress = load_progress()
    
    # Load URL cache
    cached = load_url_cache()
    if not cached:
        print("ERROR: No URL cache found. Run the regular scraper first to build cache.")
        return
    
    print("Using cached URL list")
    
    # Build work queue
    work_queue = Queue()
    total_to_process = 0
    
    for category_name, manuals in cached.items():
        done_urls = set(progress.get(category_name, []))
        for manual in manuals:
            if manual['url'] not in done_urls:
                manual['category'] = category_name
                work_queue.put(manual)
                total_to_process += 1
    
    print(f"\nTotal manuals to process: {total_to_process}")
    print(f"Starting {NUM_WORKERS} worker threads...\n")
    
    # Results queue for main thread to collect
    results_queue = Queue()
    stop_event = threading.Event()
    
    # Start workers
    workers = []
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=worker_scrape, args=(i+1, work_queue, results_queue, stop_event))
        t.start()
        workers.append(t)
        time.sleep(2)  # Stagger browser launches
    
    # Collect results
    stats = {"success": 0, "failed": 0, "total_chars": 0, "total_pages": 0}
    completed = 0
    start_time = time.time()
    
    try:
        while completed < total_to_process:
            try:
                result = results_queue.get(timeout=5)
                completed += 1
                
                if result[0]:  # Success
                    _, worker_id, brand, model, chars, pages, elapsed = result
                    stats["success"] += 1
                    stats["total_chars"] += chars
                    stats["total_pages"] += pages
                    print(f"[{completed}/{total_to_process}] W{worker_id} ✓ {brand} {model} ({chars:,}ch, {pages}pg, {elapsed:.1f}s)")
                else:  # Failed
                    _, worker_id, brand, model, _, pages, elapsed, error = result
                    stats["failed"] += 1
                    print(f"[{completed}/{total_to_process}] W{worker_id} ✗ {brand} {model} - {error}")
                
                # Progress update every 25
                if completed % 25 == 0:
                    elapsed_total = time.time() - start_time
                    rate = completed / elapsed_total * 60
                    mem = psutil.virtual_memory().percent
                    eta_min = (total_to_process - completed) / (rate if rate > 0 else 1)
                    print(f"\n  [Stats: {stats['success']} OK, {stats['failed']} fail | {rate:.1f}/min | ETA: {eta_min:.0f}min | {mem:.0f}% RAM]\n")
                    
            except:
                # Check if workers are still alive
                if all(not t.is_alive() for t in workers):
                    break
                continue
                
    except KeyboardInterrupt:
        print("\n\nStopping workers...")
        stop_event.set()
    
    # Wait for workers to finish
    for t in workers:
        t.join(timeout=10)
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total pages: {stats['total_pages']:,}")
    print(f"Total characters: {stats['total_chars']:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    if elapsed > 0:
        print(f"Rate: {completed / elapsed * 60:.1f} manuals/minute")
    print("=" * 60)

if __name__ == "__main__":
    run_threaded_scraper()

