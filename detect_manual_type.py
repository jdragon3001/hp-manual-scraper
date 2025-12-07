"""
Detect which rendering method a manual uses on manua.ls:
1. HTML text rendering (extractable) - div elements with class 't m*'
2. Image rendering (requires OCR) - webp background images

This explains why the comprehensive evaluation failed - the test manual uses images.
"""
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import re

def detect_manual_rendering_type(manual_url: str):
    """
    Detect whether a manual uses text HTML or image-based rendering
    
    Returns dict with:
    - rendering_type: 'html_text' or 'image'
    - text_elements_count: number of text elements found
    - image_urls: list of background image URLs
    - sample_text: sample extracted text (if any)
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {manual_url}")
    print('='*80)
    
    result = {
        'url': manual_url,
        'rendering_type': None,
        'text_elements_count': 0,
        'image_urls': [],
        'sample_text': ''
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Capture image requests
        image_urls = []
        def handle_request(request):
            if 'viewer' in request.url and '.webp' in request.url:
                image_urls.append(request.url)
        
        page.on('request', handle_request)
        
        page.goto(manual_url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)  # Wait for dynamic content
        
        result['image_urls'] = image_urls
        
        # Check for HTML text elements
        text_elements = page.query_selector_all('.pf div[class*="t m"], .pf div[class*=" t "]')
        result['text_elements_count'] = len(text_elements)
        
        # Try to get text
        viewer_text = page.evaluate('''() => {
            const viewer = document.querySelector('.viewer-page');
            if (!viewer) return '';
            const texts = [];
            viewer.querySelectorAll('div').forEach(el => {
                if (el.className && (el.className.includes('t m') || el.className.match(/\\bt\\b/))) {
                    const text = el.innerText;
                    if (text && text.trim().length > 2) {
                        texts.push(text.trim());
                    }
                }
            });
            return texts.join(' ');
        }''')
        
        result['sample_text'] = viewer_text[:500] if viewer_text else ''
        
        # Determine rendering type
        if len(text_elements) > 10 and len(viewer_text) > 100:
            result['rendering_type'] = 'html_text'
        elif image_urls:
            result['rendering_type'] = 'image'
        else:
            result['rendering_type'] = 'unknown'
        
        # Get page structure info
        page_structure = page.evaluate('''() => {
            const pf = document.querySelector('.pf');
            if (!pf) return 'No .pf element found';
            
            const children = Array.from(pf.children).map(c => ({
                tag: c.tagName,
                class: c.className,
                childCount: c.children.length
            }));
            return children;
        }''')
        
        print(f"\n📊 Analysis Results:")
        print(f"   Rendering Type: {result['rendering_type'].upper()}")
        print(f"   Text Elements Found: {result['text_elements_count']}")
        print(f"   Background Images: {len(result['image_urls'])}")
        if result['image_urls']:
            print(f"   Sample Image URL: {result['image_urls'][0]}")
        print(f"   Extracted Text Length: {len(result['sample_text'])} chars")
        if result['sample_text']:
            print(f"   Sample Text: {result['sample_text'][:200]}...")
        
        print(f"\n📁 Page Structure:")
        for item in page_structure[:10] if isinstance(page_structure, list) else [page_structure]:
            print(f"   {item}")
        
        browser.close()
    
    return result


def test_multiple_manuals():
    """Test detection on multiple manuals to see patterns"""
    
    test_urls = [
        # Image-based (from your test)
        "https://www.manua.ls/asus/vivobook-16/manual",
        # HP manuals (likely HTML text since existing scraper works)
        "https://www.manua.ls/hp/14/manual",
        "https://www.manua.ls/hp/elitebook-840-g5/manual",
        # Dell
        "https://www.manua.ls/dell/optiplex-7050/manual",
        # Acer
        "https://www.manua.ls/acer/aspire-5/manual",
    ]
    
    results = []
    for url in test_urls:
        try:
            result = detect_manual_rendering_type(url)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error with {url}: {e}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    html_text_count = sum(1 for r in results if r['rendering_type'] == 'html_text')
    image_count = sum(1 for r in results if r['rendering_type'] == 'image')
    
    print(f"\n📊 Results:")
    print(f"   HTML Text Rendering: {html_text_count}")
    print(f"   Image Rendering: {image_count}")
    
    print("\n📋 Details:")
    for r in results:
        status = "✅" if r['rendering_type'] == 'html_text' else "🖼️"
        print(f"   {status} {r['url'].split('/')[-2]}: {r['rendering_type']}")
    
    if image_count > 0:
        print("\n⚠️  Some manuals use IMAGE rendering (webp background images)")
        print("   These require OCR to extract text. Options:")
        print("   1. Use Tesseract OCR on downloaded images")
        print("   2. Use a cloud OCR service (Google Vision, AWS Textract)")
        print("   3. Skip image-based manuals")
    
    return results


if __name__ == "__main__":
    # Test single manual first
    result = detect_manual_rendering_type("https://www.manua.ls/asus/vivobook-16/manual")
    
    print("\n" + "="*80)
    print("TESTING KNOWN WORKING MANUAL (HP 14)")
    print("="*80)
    result2 = detect_manual_rendering_type("https://www.manua.ls/hp/14/manual")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if result['rendering_type'] == 'image' and result2['rendering_type'] == 'html_text':
        print("\n✅ Confirmed: Different manuals use different rendering methods!")
        print("   - ASUS Vivobook 16: IMAGE rendering (webp) - requires OCR")
        print("   - HP 14: HTML TEXT rendering - existing scraper works")
        print("\n📝 Solution:")
        print("   1. Detect rendering type before scraping")
        print("   2. Use existing text_extractor for HTML text manuals")
        print("   3. Use OCR (Tesseract) for image-based manuals")

