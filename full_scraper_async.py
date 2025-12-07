"""
Async parallel scraper - uses Playwright's async API for TRUE parallelism
No threading/multiprocessing issues - this is how Playwright is designed to work
"""
import os
import json
import time
import re
import random
import asyncio
import aiofiles
import psutil
from pathlib import Path
from playwright.async_api import async_playwright

# Configuration
BASE_URL = "https://www.manua.ls"
OUTPUT_DIR = Path("downloads")
PROGRESS_FILE = "playwright_progress.json"
URL_CACHE_FILE = "manual_urls_cache.json"

# Parallel settings
NUM_BROWSERS = 3  # Number of parallel browser instances (3 is safer)
MAX_RETRIES = 2   # Retry failed manuals

# Timing
PAGE_TIMEOUT = 10000      # 10s per page load
SELECTOR_TIMEOUT = 5000   # 5s to find element
DELAY_BETWEEN_PAGES = 0.2 # Brief delay between pages

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"laptops": [], "desktops": []}

def save_progress_sync(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def load_url_cache():
    if os.path.exists(URL_CACHE_FILE):
        with open(URL_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

async def extract_manual_async(browser_id, context, manual, semaphore):
    """Extract a single manual using an async browser context"""
    async with semaphore:  # Limit concurrent extractions
        manual_url = manual['url']
        brand = manual['brand']
        model = manual['model']
        category = manual['category']
        
        output_dir = OUTPUT_DIR / category / brand
        output_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        page = None
        
        try:
            page = await context.new_page()
            
            # Navigate to manual
            await page.goto(manual_url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
            await asyncio.sleep(0.3)
            
            # Get total pages
            total_pages = 1
            try:
                total_pages = await page.evaluate('''() => {
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
                    await page.goto(page_url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
                    await asyncio.sleep(DELAY_BETWEEN_PAGES)
                    
                    await page.wait_for_selector('.viewer-page', timeout=SELECTOR_TIMEOUT)
                    text_content = await page.eval_on_selector('.viewer-page', '(element) => element.innerText')
                    
                    if text_content and len(text_content.strip()) > 30:
                        all_content.append(f"--- Page {page_num} ---\n{text_content.strip()}")
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                    
                    if consecutive_failures >= 5:
                        break
                        
                except Exception:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        break
                    continue
            
            await page.close()
            elapsed = time.time() - start_time
            
            if all_content:
                content = "\n\n".join(all_content)
                safe_brand = sanitize_filename(brand)
                safe_model = sanitize_filename(model)
                filename = f"{safe_brand}_{safe_model}_{total_pages}pages.txt"
                filepath = output_dir / filename
                
                async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                    await f.write(f"Brand: {brand}\n")
                    await f.write(f"Model: {model}\n")
                    await f.write(f"URL: {manual_url}\n")
                    await f.write(f"Total Pages: {total_pages}\n")
                    await f.write("=" * 60 + "\n\n")
                    await f.write(content)
                
                return {
                    'success': True,
                    'browser_id': browser_id,
                    'brand': brand,
                    'model': model,
                    'chars': len(content),
                    'pages': total_pages,
                    'elapsed': elapsed,
                    'url': manual_url,
                    'category': category
                }
            else:
                return {
                    'success': False,
                    'browser_id': browser_id,
                    'brand': brand,
                    'model': model,
                    'error': 'Empty',
                    'url': manual_url,
                    'category': category,
                    'elapsed': elapsed
                }
                
        except Exception as e:
            if page:
                try:
                    await page.close()
                except:
                    pass
            return {
                'success': False,
                'browser_id': browser_id,
                'brand': brand,
                'model': model,
                'error': str(e)[:40],
                'url': manual_url,
                'category': category,
                'elapsed': time.time() - start_time
            }

async def run_browser_worker(browser_id, playwright, work_queue, results, semaphore, stop_event):
    """Worker that maintains a browser and processes manuals from queue"""
    print(f"  [B{browser_id}] Launching browser...")
    
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    manuals_processed = 0
    consecutive_errors = 0
    
    while not stop_event.is_set():
        if work_queue.empty():
            break
            
        try:
            manual = work_queue.get_nowait()
        except:
            await asyncio.sleep(0.1)
            if work_queue.empty():
                break
            continue
        
        try:
            result = await extract_manual_async(browser_id, context, manual, semaphore)
            results.append(result)
            manuals_processed += 1
            
            if result['success']:
                consecutive_errors = 0
            else:
                consecutive_errors += 1
            
            # Only restart if we hit multiple errors in a row
            if consecutive_errors >= 5:
                print(f"  [B{browser_id}] Restarting after {consecutive_errors} errors...")
                try:
                    await browser.close()
                except:
                    pass
                await asyncio.sleep(1)
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                consecutive_errors = 0
                
        except Exception as e:
            # Browser crashed - restart it
            print(f"  [B{browser_id}] Browser error, restarting: {str(e)[:30]}")
            try:
                await browser.close()
            except:
                pass
            await asyncio.sleep(1)
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
    
    try:
        await browser.close()
    except:
        pass
    print(f"  [B{browser_id}] Done ({manuals_processed} manuals)")

async def main():
    print("=" * 60)
    print(f"ASYNC PARALLEL SCRAPER ({NUM_BROWSERS} browsers)")
    print("=" * 60)
    
    # Load progress and cache
    progress = load_progress()
    cached = load_url_cache()
    
    if not cached:
        print("ERROR: No URL cache found. Run regular scraper first.")
        return
    
    print("Using cached URL list")
    
    # Build work queue
    work_queue = asyncio.Queue()
    total_to_process = 0
    
    for category_name, manuals in cached.items():
        done_urls = set(progress.get(category_name, []))
        for manual in manuals:
            if manual['url'] not in done_urls:
                manual['category'] = category_name
                await work_queue.put(manual)
                total_to_process += 1
    
    print(f"\nTotal manuals to process: {total_to_process}")
    print(f"Launching {NUM_BROWSERS} browser workers...\n")
    
    results = []
    stop_event = asyncio.Event()
    semaphore = asyncio.Semaphore(NUM_BROWSERS)  # One extraction per browser at a time
    
    start_time = time.time()
    
    async with async_playwright() as playwright:
        # Create worker tasks with staggered starts
        workers = []
        for i in range(NUM_BROWSERS):
            task = asyncio.create_task(
                run_browser_worker(i+1, playwright, work_queue, results, semaphore, stop_event)
            )
            workers.append(task)
            await asyncio.sleep(2)  # Stagger browser launches
        
        # Monitor progress while workers run
        last_count = 0
        while not all(w.done() for w in workers):
            await asyncio.sleep(2)
            
            # Process new results
            while len(results) > last_count:
                r = results[last_count]
                last_count += 1
                
                # Update progress
                if r['category'] not in progress:
                    progress[r['category']] = []
                progress[r['category']].append(r['url'])
                
                # Print result
                if r['success']:
                    print(f"[{last_count}/{total_to_process}] B{r['browser_id']} ✓ {r['brand']} {r['model']} ({r['chars']:,}ch, {r['pages']}pg, {r['elapsed']:.1f}s)")
                else:
                    print(f"[{last_count}/{total_to_process}] B{r['browser_id']} ✗ {r['brand']} {r['model']} - {r.get('error', 'Unknown')}")
                
                # Save progress every 10
                if last_count % 10 == 0:
                    save_progress_sync(progress)
                    elapsed = time.time() - start_time
                    rate = last_count / elapsed * 60
                    mem = psutil.virtual_memory().percent
                    success_count = sum(1 for x in results if x['success'])
                    print(f"\n  [Stats: {success_count} OK | {rate:.1f}/min | {mem:.0f}% RAM]\n")
        
        # Wait for all workers to complete
        await asyncio.gather(*workers)
    
    # Final save
    save_progress_sync(progress)
    
    # Final stats
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    total_chars = sum(r.get('chars', 0) for r in results if r['success'])
    total_pages = sum(r.get('pages', 0) for r in results if r['success'])
    
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    print(f"Total pages: {total_pages:,}")
    print(f"Total characters: {total_chars:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Rate: {len(results) / elapsed * 60:.1f} manuals/minute")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

