"""
Comprehensive evaluation of manua.ls scraping options
Testing multiple approaches to find the fastest, highest-quality method
"""
from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import time
import re
import json

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

results = []

def log(message):
    print(message)
    results.append(message)

log("=" * 80)
log("COMPREHENSIVE MANUA.LS EVALUATION")
log("=" * 80)

with sync_playwright() as p:
    # Launch with optimized settings
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--no-sandbox',
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        java_script_enabled=True,
    )
    
    page = context.new_page()
    
    # Block unnecessary resources for speed
    def block_resources(route):
        if route.request.resource_type in ['image', 'stylesheet', 'font', 'media']:
            route.abort()
        else:
            route.continue_()
    
    # page.route("**/*", block_resources)  # Uncomment to test with blocking
    
    log("\n" + "=" * 80)
    log("TEST 1: Check for hidden PDF URLs in page source/scripts")
    log("=" * 80)
    
    page.goto(test_url, wait_until='networkidle', timeout=60000)
    time.sleep(3)
    
    # Get all script content
    scripts = page.query_selector_all('script')
    pdf_refs = []
    for script in scripts:
        try:
            content = script.inner_html()
            if 'pdf' in content.lower() or '.pdf' in content:
                # Look for URLs
                urls = re.findall(r'https?://[^\s<>"\']+\.pdf[^\s<>"\']*', content, re.IGNORECASE)
                pdf_refs.extend(urls)
                # Look for any interesting patterns
                if 'pdfUrl' in content or 'pdf_url' in content or 'documentUrl' in content:
                    pdf_refs.append("Found pdf reference in script!")
        except:
            pass
    
    log(f"PDF references found: {len(set(pdf_refs))}")
    for ref in list(set(pdf_refs))[:5]:
        log(f"  - {ref}")
    
    log("\n" + "=" * 80)
    log("TEST 2: Check for PDF.js or document rendering data")
    log("=" * 80)
    
    # Check for PDF.js
    pdfjs_check = page.evaluate('''() => {
        return {
            hasPDFJS: typeof pdfjsLib !== 'undefined',
            hasPDFDocument: typeof PDFDocument !== 'undefined',
            windowKeys: Object.keys(window).filter(k => k.toLowerCase().includes('pdf')).slice(0, 10)
        }
    }''')
    log(f"PDF.js present: {pdfjs_check['hasPDFJS']}")
    log(f"PDF-related window objects: {pdfjs_check['windowKeys']}")
    
    log("\n" + "=" * 80)
    log("TEST 3: Check __NUXT__ data for document info")
    log("=" * 80)
    
    nuxt_data = page.evaluate('''() => {
        if (window.__NUXT__) {
            return JSON.stringify(window.__NUXT__).substring(0, 2000);
        }
        return "No __NUXT__ found";
    }''')
    log(f"NUXT data preview: {nuxt_data[:500]}...")
    
    log("\n" + "=" * 80)
    log("TEST 4: Test Playwright PDF generation")
    log("=" * 80)
    
    start_time = time.time()
    try:
        # Generate PDF of current page
        pdf_bytes = page.pdf(
            format='A4',
            print_background=True,
            scale=1.0
        )
        pdf_time = time.time() - start_time
        log(f"PDF generated: {len(pdf_bytes)} bytes in {pdf_time:.2f}s")
        
        # Save test PDF
        with open('test_page1.pdf', 'wb') as f:
            f.write(pdf_bytes)
        log("Saved to test_page1.pdf - CHECK IF THIS IS READABLE!")
    except Exception as e:
        log(f"PDF generation failed: {e}")
    
    log("\n" + "=" * 80)
    log("TEST 5: Test in-page navigation speed")
    log("=" * 80)
    
    # Test navigating to page 2 via button click vs URL change
    start_time = time.time()
    
    # Method A: Full page navigation
    page.goto(f"{test_url}?p=2", wait_until='networkidle', timeout=30000)
    method_a_time = time.time() - start_time
    log(f"Method A (full navigation to ?p=2): {method_a_time:.2f}s")
    
    # Go back to page 1
    page.goto(test_url, wait_until='networkidle', timeout=30000)
    time.sleep(1)
    
    # Method B: Click next page button
    start_time = time.time()
    try:
        next_btn = page.query_selector('a[href*="?p=2"], button:has-text("Next"), .pagination a:nth-child(2)')
        if next_btn:
            next_btn.click()
            page.wait_for_load_state('networkidle')
            method_b_time = time.time() - start_time
            log(f"Method B (click navigation): {method_b_time:.2f}s")
        else:
            log("Method B: Could not find next button")
    except Exception as e:
        log(f"Method B error: {e}")
    
    log("\n" + "=" * 80)
    log("TEST 6: Extract rendered text quality check")
    log("=" * 80)
    
    page.goto(test_url, wait_until='networkidle', timeout=30000)
    time.sleep(2)
    
    # Method A: innerText on viewer
    viewer_text = page.evaluate('''() => {
        const viewer = document.querySelector('.viewer-page');
        return viewer ? viewer.innerText : '';
    }''')
    log(f"Viewer innerText length: {len(viewer_text)} chars")
    log(f"Preview: {viewer_text[:200]}")
    
    # Method B: Get text from pf div (page content)
    pf_text = page.evaluate('''() => {
        const pf = document.querySelector('.pf');
        return pf ? pf.innerText : '';
    }''')
    log(f"\nPF div innerText length: {len(pf_text)} chars")
    log(f"Preview: {pf_text[:200]}")
    
    # Method C: Get all text spans/divs from the page render
    all_text = page.evaluate('''() => {
        const texts = [];
        document.querySelectorAll('.pf div, .pf span').forEach(el => {
            const text = el.innerText || el.textContent;
            if (text && text.trim().length > 0) {
                texts.push(text.trim());
            }
        });
        return texts.join(' ');
    }''')
    log(f"\nAll text elements combined: {len(all_text)} chars")
    log(f"Preview: {all_text[:200]}")
    
    log("\n" + "=" * 80)
    log("TEST 7: Test parallel page extraction")
    log("=" * 80)
    
    # Create multiple pages in same context
    start_time = time.time()
    pages_data = []
    
    for i in range(1, 4):  # Test 3 pages
        new_page = context.new_page()
        new_page.goto(f"{test_url}?p={i}", wait_until='networkidle', timeout=30000)
        pages_data.append({
            'page': i,
            'url': f"{test_url}?p={i}"
        })
    
    multi_page_time = time.time() - start_time
    log(f"Loading 3 pages sequentially: {multi_page_time:.2f}s ({multi_page_time/3:.2f}s per page)")
    
    # Clean up extra pages
    for p in context.pages[1:]:
        p.close()
    
    log("\n" + "=" * 80)
    log("TEST 8: Check for data URLs or embedded content")
    log("=" * 80)
    
    page.goto(test_url, wait_until='networkidle', timeout=30000)
    
    # Look for any data attributes that might contain content
    data_attrs = page.evaluate('''() => {
        const results = [];
        document.querySelectorAll('[data-src], [data-url], [data-pdf], [data-document]').forEach(el => {
            results.push({
                tag: el.tagName,
                dataSrc: el.getAttribute('data-src'),
                dataUrl: el.getAttribute('data-url'),
                dataPdf: el.getAttribute('data-pdf'),
            });
        });
        return results;
    }''')
    log(f"Elements with data attributes: {len(data_attrs)}")
    for attr in data_attrs[:5]:
        log(f"  {attr}")
    
    browser.close()

log("\n" + "=" * 80)
log("EVALUATION COMPLETE")
log("=" * 80)

# Save results
with open('evaluation_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print("\nResults saved to evaluation_results.txt")
print("Check test_page1.pdf to see if PDF generation works!")


