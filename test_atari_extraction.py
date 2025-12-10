"""
Test what we actually extract from ATARI manual pages
"""
from playwright.sync_api import sync_playwright
import time

url = "https://www.manua.ls/atari/520st/manual"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Test first few pages
    for page_num in [1, 2, 3]:
        page_url = f"{url}?p={page_num}"
        print(f"\n{'='*60}")
        print(f"Page {page_num}: {page_url}")
        print('='*60)
        
        page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
        time.sleep(1)
        
        try:
            # Try the same extraction method as scraper
            page.wait_for_selector('.viewer-page', timeout=3000)
            print("✓ Found .viewer-page selector")
            
            text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
            print(f"✓ Extracted text length: {len(text) if text else 0} chars")
            print(f"✓ Stripped length: {len(text.strip()) if text else 0} chars")
            
            if text:
                print(f"\nFirst 200 chars:")
                print(text[:200])
                print(f"\n...more text..." if len(text) > 200 else "")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    browser.close()

print("\n" + "="*60)
print("Test complete")

