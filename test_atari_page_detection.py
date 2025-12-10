"""
Test page count detection for ATARI manual
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.manua.ls/atari/520st/manual"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"Testing: {url}\n")
    
    page.goto(url, wait_until='domcontentloaded', timeout=10000)
    time.sleep(2)
    
    # Method 1: From .btn element
    try:
        btn_text = page.inner_text('.btn')
        print(f"Button text: '{btn_text}'")
        
        import re
        match = re.search(r'(\d+)\s*page', btn_text, re.IGNORECASE)
        if match:
            print(f"✓ Method 1 (.btn with regex): {match.group(1)} pages")
        else:
            print(f"✗ Method 1 failed - no match in button text")
    except Exception as e:
        print(f"✗ Method 1 failed: {e}")
    
    # Method 2: Using JavaScript evaluation
    try:
        total_pages = page.evaluate('''() => {
            const text = document.querySelector('.btn')?.innerText || '';
            const match = text.match(/(\\d+)\\s*page/i);
            return match ? parseInt(match[1]) : 1;
        }''')
        print(f"✓ Method 2 (JS eval): {total_pages} pages")
    except Exception as e:
        print(f"✗ Method 2 failed: {e}")
    
    # Method 3: Check all possible selectors
    try:
        all_buttons = page.query_selector_all('button, .btn, a.btn')
        print(f"\nFound {len(all_buttons)} button-like elements:")
        for i, btn in enumerate(all_buttons[:10]):  # Show first 10
            try:
                text = btn.inner_text()
                if text.strip():
                    print(f"  Button {i}: '{text[:50]}'")
            except:
                pass
    except Exception as e:
        print(f"✗ Method 3 failed: {e}")
    
    # Method 4: Look at page structure
    try:
        page_info = page.evaluate('''() => {
            const pageInfo = document.querySelector('.page-info, .pagination, .page-number');
            return pageInfo ? pageInfo.innerText : 'Not found';
        }''')
        print(f"\nPage info element: {page_info}")
    except:
        pass
    
    # Wait a bit to see the page
    time.sleep(5)
    browser.close()

