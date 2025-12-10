"""
Simple speed test - measure actual page load times
Usage: python test_page_speed.py
"""
import time
from playwright.sync_api import sync_playwright

def test_speed():
    url = "https://www.manua.ls/ecs/t30ii/manual"
    
    print(f"Testing: {url}\n")
    
    with sync_playwright() as p:
        # Test current settings
        print("=" * 60)
        print("TEST 1: Current stealth settings")
        print("=" * 60)
        
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        for page_num in [1, 2, 3, 10, 20]:
            page_url = f"{url}?p={page_num}"
            
            start = time.time()
            page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
            load_time = time.time() - start
            
            time.sleep(0.3)
            
            extract_start = time.time()
            try:
                page.wait_for_selector('.viewer-page', timeout=3000)
                text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                text_len = len(text)
            except:
                text_len = 0
            extract_time = time.time() - extract_start
            
            total_time = time.time() - start
            
            print(f"Page {page_num:3d}: Load={load_time:.2f}s | Extract={extract_time:.2f}s | Total={total_time:.2f}s | Text={text_len} chars")
        
        browser.close()
        
        # Test simple settings
        print("\n" + "=" * 60)
        print("TEST 2: Minimal/simple settings")
        print("=" * 60)
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for page_num in [1, 2, 3, 10, 20]:
            page_url = f"{url}?p={page_num}"
            
            start = time.time()
            page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
            load_time = time.time() - start
            
            time.sleep(0.3)
            
            extract_start = time.time()
            try:
                page.wait_for_selector('.viewer-page', timeout=3000)
                text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                text_len = len(text)
            except:
                text_len = 0
            extract_time = time.time() - extract_start
            
            total_time = time.time() - start
            
            print(f"Page {page_num:3d}: Load={load_time:.2f}s | Extract={extract_time:.2f}s | Total={total_time:.2f}s | Text={text_len} chars")
        
        browser.close()
        
        # Test with no delays
        print("\n" + "=" * 60)
        print("TEST 3: No delays between operations")
        print("=" * 60)
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for page_num in [1, 2, 3, 10, 20]:
            page_url = f"{url}?p={page_num}"
            
            start = time.time()
            page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
            load_time = time.time() - start
            
            # NO SLEEP
            
            extract_start = time.time()
            try:
                text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                text_len = len(text)
            except:
                text_len = 0
            extract_time = time.time() - extract_start
            
            total_time = time.time() - start
            
            print(f"Page {page_num:3d}: Load={load_time:.2f}s | Extract={extract_time:.2f}s | Total={total_time:.2f}s | Text={text_len} chars")
        
        browser.close()

if __name__ == "__main__":
    test_speed()

