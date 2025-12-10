"""
Check what's actually on the page
"""
from playwright.sync_api import sync_playwright

url = "https://www.manua.ls/ecs/t30ii/manual"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Visible so you can see
    page = browser.new_page()
    
    print(f"Loading: {url}\n")
    page.goto(url, wait_until='domcontentloaded', timeout=10000)
    page.wait_for_timeout(2000)  # Wait 2 seconds
    
    # Check what selectors exist
    print("Checking selectors:")
    print(f"  .viewer-page exists: {page.query_selector('.viewer-page') is not None}")
    print(f"  .viewer exists: {page.query_selector('.viewer') is not None}")
    print(f"  #page-container exists: {page.query_selector('#page-container') is not None}")
    print(f"  .pf exists: {page.query_selector('.pf') is not None}")
    
    # Get all class names on page
    print("\nAll unique classes on page:")
    classes = page.evaluate('''() => {
        const elements = document.querySelectorAll('*');
        const classes = new Set();
        elements.forEach(el => {
            if (el.className && typeof el.className === 'string') {
                el.className.split(' ').forEach(c => {
                    if (c.trim()) classes.add(c.trim());
                });
            }
        });
        return Array.from(classes).sort().slice(0, 20);
    }''')
    print(classes)
    
    # Try to get text from body
    print("\nTrying to get text from body:")
    body_text = page.evaluate('() => document.body.innerText')
    print(f"Body text length: {len(body_text)}")
    print(f"First 200 chars: {body_text[:200]}")
    
    # Try to get text from main content areas
    print("\nTrying different selectors:")
    selectors = ['#page-container', '.pf', 'body', '#sidebar', '.viewer']
    for sel in selectors:
        try:
            elem = page.query_selector(sel)
            if elem:
                text = elem.inner_text()
                print(f"  {sel}: {len(text)} chars")
            else:
                print(f"  {sel}: NOT FOUND")
        except Exception as e:
            print(f"  {sel}: ERROR - {e}")
    
    print("\nBrowser will stay open. Press Enter to close...")
    input()
    browser.close()

