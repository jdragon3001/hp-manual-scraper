"""
Diagnostic script to test a specific manual URL and understand extraction issues.
Usage: python diagnose_manual.py <URL>
Example: python diagnose_manual.py https://www.manua.ls/ecs/t30ii/manual
"""
import sys
import time
from playwright.sync_api import sync_playwright

def diagnose_manual(url):
    """Detailed diagnosis of a manual URL"""
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {url}")
    print(f"{'='*60}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False to see what's happening
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Test 1: Can we load the first page?
        print("Test 1: Loading main page...")
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=15000)
            print(f"  ✓ Status: {response.status}")
            print(f"  ✓ URL: {page.url}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            browser.close()
            return
        
        time.sleep(2)
        
        # Test 2: What selectors exist?
        print("\nTest 2: Checking page structure...")
        selectors = {
            '.viewer-page': 'HTML text rendering',
            '.viewer': 'Viewer container',
            'img[src*="/bg"]': 'Background image (OCR needed)',
            'img[src*=".webp"]': 'WebP image',
            '.t': 'Text elements'
        }
        
        for selector, description in selectors.items():
            exists = page.query_selector(selector) is not None
            status = "✓" if exists else "✗"
            print(f"  {status} {selector}: {description}")
        
        # Test 3: Get page count
        print("\nTest 3: Getting total pages...")
        try:
            total_pages = page.evaluate('''() => {
                const text = document.body.innerText;
                const match = text.match(/(\\d+)\\s*page/i);
                return match ? parseInt(match[1]) : 1;
            }''')
            print(f"  ✓ Total pages: {total_pages}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            total_pages = 1
        
        # Test 4: Try extracting first 3 pages
        print("\nTest 4: Extracting first 3 pages...")
        for page_num in [1, 2, 3]:
            try:
                page_url = f"{url}?p={page_num}"
                print(f"\n  Page {page_num}: {page_url}")
                
                response = page.goto(page_url, wait_until='domcontentloaded', timeout=15000)
                print(f"    Status: {response.status}")
                
                time.sleep(1)
                
                # Try .viewer-page selector
                text = None
                try:
                    page.wait_for_selector('.viewer-page', timeout=5000)
                    text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                    print(f"    ✓ Method 1 (.viewer-page): {len(text)} chars")
                except Exception as e:
                    print(f"    ✗ Method 1 failed: {str(e)[:50]}")
                
                # Try body.innerText
                if not text or len(text) < 30:
                    try:
                        text = page.evaluate('() => document.body.innerText')
                        print(f"    ✓ Method 2 (body): {len(text)} chars")
                    except Exception as e:
                        print(f"    ✗ Method 2 failed: {str(e)[:50]}")
                
                if text and len(text) > 30:
                    print(f"    ✓ EXTRACTED: {len(text)} chars")
                    print(f"    Preview: {text[:100]}...")
                else:
                    print(f"    ✗ FAILED: No text extracted")
                    
            except Exception as e:
                print(f"    ✗ Error loading page: {str(e)[:100]}")
        
        # Test 5: Network analysis
        print("\nTest 5: Network timing...")
        start = time.time()
        try:
            page.goto(f"{url}?p=10", wait_until='domcontentloaded', timeout=15000)
            elapsed = time.time() - start
            print(f"  ✓ Page 10 loaded in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ✗ Page 10 timed out after {elapsed:.2f}s: {str(e)[:50]}")
        
        print("\n" + "="*60)
        print("Diagnosis complete. Press Ctrl+C to close browser.")
        print("="*60)
        
        # Keep browser open for inspection
        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_manual.py <URL>")
        print("Example: python diagnose_manual.py https://www.manua.ls/ecs/t30ii/manual")
        sys.exit(1)
    
    url = sys.argv[1]
    diagnose_manual(url)

