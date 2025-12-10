"""
Test that redirect detection works
"""
from playwright.sync_api import sync_playwright

urls_to_test = [
    ("https://www.manua.ls/ecs/g320/manual", "Should work - manual exists"),
    ("https://www.manua.ls/ecs/t30ii/manual", "Should detect redirect - manual removed")
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for url, description in urls_to_test:
        print(f"\nTesting: {url}")
        print(f"Expected: {description}")
        
        response = page.goto(url, wait_until='domcontentloaded', timeout=10000)
        
        print(f"  Request URL: {url}")
        print(f"  Final URL:   {page.url}")
        print(f"  Redirected:  {page.url != url}")
        
        if page.url != url:
            print(f"  ✓ REDIRECT DETECTED - Would skip this manual")
        else:
            print(f"  ✓ NO REDIRECT - Would extract this manual")
    
    browser.close()

