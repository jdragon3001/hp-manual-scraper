"""
Quick test - what's happening with LENOVO desktops?
"""
from playwright.sync_api import sync_playwright
import time

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Testing LENOVO desktops...")
        
        # Go to LENOVO desktops
        response = page.goto("https://www.manua.ls/desktops/lenovo", wait_until='domcontentloaded', timeout=15000)
        print(f"Response status: {response.status if response else 'None'}")
        print(f"Final URL: {page.url}")
        time.sleep(2)
        
        # Check if redirected
        if page.url != "https://www.manua.ls/desktops/lenovo":
            print(f"REDIRECTED! Should detect this and skip.")
        else:
            print("No redirect - page exists")
            
            # Count manuals
            manual_count = page.evaluate('''() => {
                return document.querySelectorAll('a[href*="/manual"]').length;
            }''')
            print(f"Manual links found: {manual_count}")
        
        input("\nPress Enter to close...")
        browser.close()

if __name__ == "__main__":
    test()

