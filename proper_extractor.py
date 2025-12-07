"""
Proper text extractor using Playwright
Waits for full page render and extracts all text from the viewer
"""
from playwright.sync_api import sync_playwright
import time
import re
from pathlib import Path


def extract_page_text(page, page_num: int) -> str:
    """Extract text from current viewer page with proper waiting"""
    try:
        # Wait for the viewer to be present
        page.wait_for_selector('.viewer-page', timeout=15000)
        
        # Wait for content to render (the .pf element contains page content)
        page.wait_for_selector('.pf', timeout=10000)
        
        # Give extra time for text elements to render
        time.sleep(2)
        
        # Extract text using multiple methods to get everything
        text = page.evaluate('''() => {
            const texts = [];
            
            // Method 1: Get all divs/spans with 't' in class name (text elements)
            document.querySelectorAll('.pf [class*=" t "], .pf [class^="t "], .pf .t').forEach(el => {
                const text = el.textContent;
                if (text && text.trim().length > 0) {
                    texts.push(text.trim());
                }
            });
            
            // Method 2: If no text found, try innerText of pf
            if (texts.length === 0) {
                const pf = document.querySelector('.pf');
                if (pf) {
                    const innerText = pf.innerText;
                    if (innerText && innerText.trim().length > 0) {
                        texts.push(innerText.trim());
                    }
                }
            }
            
            // Method 3: Try h1, h2, h3, p, span, div with actual text
            if (texts.length === 0) {
                document.querySelectorAll('.viewer-page h1, .viewer-page h2, .viewer-page h3, .viewer-page p, .viewer-page span, .viewer-page div').forEach(el => {
                    const text = el.textContent;
                    if (text && text.trim().length > 2 && !el.children.length) {
                        texts.push(text.trim());
                    }
                });
            }
            
            return texts.join('\\n');
        }''')
        
        return text if text else ""
        
    except Exception as e:
        print(f"    Error on page {page_num}: {e}")
        return ""


def extract_manual(manual_url: str, max_pages: int = None) -> dict:
    """Extract complete manual with proper waiting"""
    print(f"\n{'='*80}")
    print(f"EXTRACTING: {manual_url}")
    print('='*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Load manual
        print("Loading page...")
        page.goto(manual_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
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
        
        # Extract pages
        all_pages = []
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
                
                text = extract_page_text(page, page_num)
                
                if text and len(text) > 5:
                    all_pages.append({
                        'page': page_num,
                        'text': text
                    })
                    print(f"✅ ({len(text)} chars)")
                else:
                    print("⚠️ No text")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
        
        browser.close()
    
    return {
        'title': title,
        'total_pages': total_pages,
        'pages': all_pages
    }


def format_output(result: dict) -> str:
    """Format extracted content as text"""
    output = []
    output.append("=" * 80)
    output.append(result.get('title', 'MANUAL').upper())
    output.append("=" * 80)
    output.append("")
    
    for p in result['pages']:
        output.append(f"\n{'='*80}")
        output.append(f"PAGE {p['page']}")
        output.append('='*80)
        output.append(p['text'])
    
    return '\n'.join(output)


if __name__ == "__main__":
    # Test on HP manual
    print("\n" + "="*80)
    print("TEST: HP 14 Manual - First 5 pages")
    print("="*80)
    
    result = extract_manual("https://www.manua.ls/hp/14/manual", max_pages=5)
    
    print("\n" + "="*80)
    print("EXTRACTED CONTENT")
    print("="*80)
    
    total_chars = 0
    for p in result['pages']:
        total_chars += len(p['text'])
        print(f"\n--- PAGE {p['page']} ({len(p['text'])} chars) ---")
        print(p['text'][:800])
        if len(p['text']) > 800:
            print("...[truncated]...")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: {len(result['pages'])} pages, {total_chars} total characters")
    print('='*80)
    
    # Save test output
    if total_chars > 100:
        output_text = format_output(result)
        with open('proper_extraction_test.txt', 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"Saved to: proper_extraction_test.txt")

