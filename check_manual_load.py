"""
Check if manual content loads after waiting
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.manua.ls/ecs/t30ii/manual"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print(f"Loading: {url}\n")
    page.goto(url, wait_until='networkidle', timeout=30000)
    
    print("Waiting for content to load...")
    for i in range(10):
        print(f"  After {i} seconds:")
        print(f"    .viewer-page exists: {page.query_selector('.viewer-page') is not None}")
        
        # Check if there's an iframe
        iframes = page.query_selector_all('iframe')
        print(f"    iframes found: {len(iframes)}")
        
        # Check page URL (might redirect)
        print(f"    current URL: {page.url}")
        
        # Get body text length
        body_len = len(page.evaluate('() => document.body.innerText'))
        print(f"    body text: {body_len} chars")
        
        if i == 0:
            # Try clicking on manual if there's a button/link
            try:
                page.click('text="View"', timeout=2000)
                print("    Clicked 'View' button")
            except:
                pass
        
        time.sleep(1)
    
    print("\nPress Enter to close...")
    input()
    browser.close()

