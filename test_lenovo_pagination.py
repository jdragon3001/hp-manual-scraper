"""
Quick test to see what's happening with LENOVO pagination
"""
from playwright.sync_api import sync_playwright
import time

def test_lenovo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser
        page = browser.new_page()
        
        print("Testing LENOVO laptops pagination...")
        
        # Go to LENOVO laptops page 1
        page.goto("https://www.manua.ls/laptops/lenovo", wait_until='domcontentloaded')
        time.sleep(1)
        
        # Count manuals on page 1
        manual_count = page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/manual"]').length;
        }''')
        print(f"Page 1: {manual_count} manual links")
        
        # Try page 2
        print("\nNavigating to page 2...")
        response = page.goto("https://www.manua.ls/laptops/lenovo?p=2", wait_until='domcontentloaded')
        print(f"Response status: {response.status}")
        print(f"Final URL: {page.url}")
        time.sleep(1)
        
        manual_count_p2 = page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/manual"]').length;
        }''')
        print(f"Page 2: {manual_count_p2} manual links")
        
        # Try page 10
        print("\nNavigating to page 10...")
        response = page.goto("https://www.manua.ls/laptops/lenovo?p=10", wait_until='domcontentloaded')
        print(f"Response status: {response.status}")
        print(f"Final URL: {page.url}")
        time.sleep(1)
        
        manual_count_p10 = page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/manual"]').length;
        }''')
        print(f"Page 10: {manual_count_p10} manual links")
        
        # Try a very high page number
        print("\nNavigating to page 999...")
        response = page.goto("https://www.manua.ls/laptops/lenovo?p=999", wait_until='domcontentloaded')
        print(f"Response status: {response.status}")
        print(f"Final URL: {page.url}")
        
        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    test_lenovo()

