"""
Deep investigation of the page HTML structure to find any hidden text content
"""
from playwright.sync_api import sync_playwright
import json

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

print("="*80)
print("DEEP HTML INVESTIGATION")
print("="*80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto(test_url, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    
    # Get the full HTML of the viewer page
    print("\n1. Viewer page HTML structure:")
    viewer_html = page.evaluate('''() => {
        const viewer = document.querySelector('.viewer-page');
        if (!viewer) return 'No viewer found';
        return viewer.outerHTML.substring(0, 5000);
    }''')
    print(viewer_html)
    
    # Check for inline styles that might contain text positioning
    print("\n" + "="*80)
    print("2. Looking for hidden text or data attributes:")
    
    data_content = page.evaluate('''() => {
        const results = [];
        // Check all elements for data attributes
        document.querySelectorAll('[data-text], [data-content], [data-page-text]').forEach(el => {
            results.push({
                tag: el.tagName,
                dataText: el.getAttribute('data-text'),
                dataContent: el.getAttribute('data-content'),
            });
        });
        return results;
    }''')
    print(f"Elements with data-text/content: {len(data_content)}")
    for item in data_content[:10]:
        print(f"  {item}")
    
    # Check for text in computed styles or pseudo elements
    print("\n" + "="*80)
    print("3. All divs inside .pf with their content:")
    
    pf_content = page.evaluate('''() => {
        const pf = document.querySelector('.pf');
        if (!pf) return 'No .pf found';
        
        const divs = [];
        pf.querySelectorAll('*').forEach(el => {
            const text = el.textContent || '';
            const style = window.getComputedStyle(el);
            divs.push({
                tag: el.tagName,
                class: el.className,
                text: text.trim().substring(0, 100),
                position: style.position,
                backgroundImage: style.backgroundImage ? style.backgroundImage.substring(0, 100) : ''
            });
        });
        return divs;
    }''')
    
    print(f"Total elements in .pf: {len(pf_content) if isinstance(pf_content, list) else 0}")
    if isinstance(pf_content, list):
        for item in pf_content[:20]:
            if item.get('text') or item.get('backgroundImage'):
                print(f"  {item}")
    
    # Check if there's a separate text layer URL
    print("\n" + "="*80)
    print("4. Looking for text layer or JSON data:")
    
    json_data = page.evaluate('''() => {
        // Check for any global variables that might contain text
        const candidates = ['pageData', 'manualData', 'textContent', 'documentText', 'pageText'];
        const found = {};
        for (const name of candidates) {
            if (window[name]) {
                found[name] = JSON.stringify(window[name]).substring(0, 500);
            }
        }
        
        // Check for __NUXT__ state
        if (window.__NUXT__ && window.__NUXT__.state) {
            found['__NUXT__.state'] = JSON.stringify(window.__NUXT__.state).substring(0, 1000);
        }
        
        return found;
    }''')
    print(f"Global data found: {json.dumps(json_data, indent=2)}")
    
    # Check the actual style content in the page
    print("\n" + "="*80)
    print("5. Inline styles that might contain positioning data:")
    
    styles = page.query_selector_all('.pf style')
    for i, style in enumerate(styles[:3]):
        content = style.inner_html()
        print(f"\nStyle {i+1}:")
        print(content[:2000] if content else "Empty")
    
    browser.close()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("""
The manua.ls site uses two rendering methods:

1. HTML TEXT RENDERING (good):
   - Text is placed in div elements with CSS positioning
   - Class names like 't m0' contain actual text
   - The existing text_extractor.py handles these

2. IMAGE RENDERING (problematic):
   - Page is rendered as a webp background image
   - NO extractable text in HTML
   - The image URL is like: /viewer/90/{file_id}/{page}/bg{page}.webp
   - Requires OCR to extract text

SOLUTIONS:
A) Install Tesseract OCR and use ocr_extractor.py
B) Skip image-based manuals
C) Check if there's a PDF download link (some manuals have one)
D) Use a cloud OCR API (Google Vision, AWS Textract)
""")

