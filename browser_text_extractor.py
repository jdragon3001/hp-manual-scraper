"""
Browser-based text extractor - extracts text directly from the embedded viewer

Based on browser investigation:
- The viewer renders PDF pages in a .viewer-page container
- Text elements have class patterns like 't m0', 't m1', etc.
- HP manuals have actual readable text; ASUS uses custom font encoding
"""
from playwright.sync_api import sync_playwright
import time
import re
from pathlib import Path


def extract_viewer_text(page) -> str:
    """Extract text from the current viewer page"""
    # Wait for viewer to load
    try:
        page.wait_for_selector('.viewer-page', timeout=10000)
        time.sleep(1)  # Wait for content to render
    except:
        return ""
    
    # Try multiple extraction methods
    
    # Method 1: Get all text from elements with 't' class
    text = page.evaluate('''() => {
        const texts = [];
        // Get all elements with class containing 't '
        document.querySelectorAll('.pf [class*="t "], .pf .t').forEach(el => {
            const text = el.textContent || el.innerText;
            if (text && text.trim()) {
                texts.push(text.trim());
            }
        });
        return texts.join(' ');
    }''')
    
    if text and len(text) > 10:
        return text
    
    # Method 2: Get innerText of the whole viewer-page
    text = page.evaluate('''() => {
        const viewer = document.querySelector('.viewer-page');
        return viewer ? viewer.innerText : '';
    }''')
    
    return text.strip() if text else ""


def extract_manual(manual_url: str, max_pages: int = None) -> dict:
    """Extract all pages from a manual"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING: {manual_url}")
    print('='*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 1024}
        )
        page = context.new_page()
        
        # Load manual
        page.goto(manual_url, wait_until='networkidle', timeout=60000)
        time.sleep(2)
        
        # Get title
        title = ""
        try:
            title = page.inner_text('h1')
            print(f"Title: {title}")
        except:
            pass
        
        # Get total pages
        total_pages = 1
        try:
            btn_text = page.inner_text('.btn')
            match = re.search(r'/\s*(\d+)', btn_text)
            if match:
                total_pages = int(match.group(1))
                print(f"Total Pages: {total_pages}")
        except:
            pass
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        # Extract each page
        pages_text = []
        print(f"\nExtracting {total_pages} pages...")
        
        for page_num in range(1, total_pages + 1):
            print(f"  Page {page_num}/{total_pages}...", end=' ', flush=True)
            
            # Navigate to page
            if page_num == 1:
                page_url = manual_url
            else:
                page_url = f"{manual_url}?p={page_num}"
            
            try:
                page.goto(page_url, wait_until='networkidle', timeout=30000)
                time.sleep(1)
                
                text = extract_viewer_text(page)
                
                if text:
                    pages_text.append({
                        'page': page_num,
                        'text': text
                    })
                    print(f"✅ ({len(text)} chars)")
                else:
                    print("⚠️ No text")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        browser.close()
    
    return {
        'title': title,
        'total_pages': total_pages,
        'pages': pages_text
    }


def test_manual(manual_url: str, pages: int = 5):
    """Test extraction on a manual"""
    result = extract_manual(manual_url, max_pages=pages)
    
    print(f"\n{'='*80}")
    print("EXTRACTED TEXT PREVIEW")
    print('='*80)
    
    total_chars = 0
    for p in result['pages']:
        total_chars += len(p['text'])
        print(f"\n--- PAGE {p['page']} ---")
        print(p['text'][:500])
        if len(p['text']) > 500:
            print("...")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: {len(result['pages'])} pages, {total_chars} total characters")
    print('='*80)
    
    return result


if __name__ == "__main__":
    # Test HP manual (known to work)
    print("\n" + "="*80)
    print("TEST 1: HP 14 Manual (should have readable text)")
    print("="*80)
    hp_result = test_manual("https://www.manua.ls/hp/14/manual", pages=3)
    
    # Test ASUS manual (problematic)
    print("\n" + "="*80)
    print("TEST 2: ASUS VivoBook 16 Manual (may have encoded text)")
    print("="*80)
    asus_result = test_manual("https://www.manua.ls/asus/vivobook-16/manual", pages=3)
    
    # Compare results
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    
    hp_chars = sum(len(p['text']) for p in hp_result['pages'])
    asus_chars = sum(len(p['text']) for p in asus_result['pages'])
    
    print(f"HP 14: {hp_chars} characters extracted from {len(hp_result['pages'])} pages")
    print(f"ASUS VivoBook 16: {asus_chars} characters extracted from {len(asus_result['pages'])} pages")
    
    if hp_chars > 100 and asus_chars < 100:
        print("\n⚠️ Confirmed: HP works but ASUS uses a different rendering method")
    elif hp_chars > 100 and asus_chars > 100:
        print("\n✅ Both manuals have extractable text!")

