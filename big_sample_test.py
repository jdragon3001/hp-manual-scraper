"""
Big Sample Test - Extract multiple manuals organized by category and brand
Output to: test_sample/laptops/{brand}/ and test_sample/desktops/{brand}/
"""
from playwright.sync_api import sync_playwright
import time
import re
from pathlib import Path

# Output directory
OUTPUT_DIR = Path("test_sample")

# Sample manuals to test - mix of brands and categories
TEST_MANUALS = {
    "laptops": {
        "HP": [
            "https://www.manua.ls/hp/elitebook-840-g5/manual",
            "https://www.manua.ls/hp/probook-450-g7/manual",
        ],
        "Lenovo": [
            "https://www.manua.ls/lenovo/thinkpad-e16-gen-1/manual",
            "https://www.manua.ls/lenovo/ideapad-3/manual",
        ],
        "Dell": [
            "https://www.manua.ls/dell/latitude-5520/manual",
            "https://www.manua.ls/dell/inspiron-15-3000/manual",
        ],
        "MSI": [
            "https://www.manua.ls/msi/stealth-16-mercedes-amg/manual",
        ],
        "Asus": [
            "https://www.manua.ls/asus/rog-strix-g15/manual",
        ],
    },
    "desktops": {
        "HP": [
            "https://www.manua.ls/hp/prodesk-400-g6/manual",
        ],
        "Dell": [
            "https://www.manua.ls/dell/optiplex-7080/manual",
        ],
        "Lenovo": [
            "https://www.manua.ls/lenovo/thinkcentre-m720q/manual",
        ],
    }
}

# How many pages to extract per manual (for testing)
MAX_PAGES = 10


def extract_manual(browser, url: str) -> dict:
    """Extract manual with proper timing"""
    result = {
        "title": "",
        "total_pages": 0,
        "pages_extracted": 0,
        "total_chars": 0,
        "content": []
    }
    
    context = browser.new_context(
        viewport={'width': 1400, 'height': 900},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    try:
        # Load manual
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        # Get title
        try:
            result["title"] = page.inner_text('h1')
        except:
            pass
        
        # Get total pages
        try:
            btn_text = page.inner_text('.btn')
            match = re.search(r'/\s*(\d+)', btn_text)
            if match:
                result["total_pages"] = int(match.group(1))
        except:
            pass
        
        pages_to_extract = min(MAX_PAGES, result["total_pages"]) if result["total_pages"] > 0 else MAX_PAGES
        
        # Extract pages
        for page_num in range(1, pages_to_extract + 1):
            page_url = url if page_num == 1 else f"{url}?p={page_num}"
            
            try:
                page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
                time.sleep(3)
                
                text = page.eval_on_selector('.viewer-page', '(el) => el.innerText')
                text = text.strip() if text else ""
                
                if text and len(text) > 5:
                    result["content"].append({
                        "page": page_num,
                        "text": text,
                        "chars": len(text)
                    })
                    result["total_chars"] += len(text)
                    result["pages_extracted"] += 1
                    
            except Exception as e:
                pass  # Skip failed pages silently
        
    finally:
        context.close()
    
    return result


def format_output(result: dict, url: str) -> str:
    """Format result as text file"""
    lines = []
    lines.append("=" * 80)
    lines.append(result.get("title", "MANUAL").upper())
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Source: {url}")
    lines.append(f"Total Pages: {result['total_pages']}")
    lines.append(f"Pages Extracted: {result['pages_extracted']}")
    lines.append(f"Total Characters: {result['total_chars']}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("")
    lines.append("MANUAL CONTENT:")
    lines.append("")
    
    for p in result["content"]:
        lines.append(f"\n{'='*80}")
        lines.append(f"PAGE {p['page']}")
        lines.append('='*80)
        lines.append(p["text"])
    
    return "\n".join(lines)


def get_filename_from_url(url: str) -> str:
    """Extract a filename from URL"""
    # URL like: https://www.manua.ls/hp/elitebook-840-g5/manual
    parts = url.rstrip('/').split('/')
    if len(parts) >= 2:
        brand = parts[-3].upper()
        model = parts[-2].replace('-', '_').title()
        return f"{brand}_{model}.txt"
    return "unknown.txt"


def main():
    print("=" * 80)
    print("BIG SAMPLE TEST - Multiple Brands & Categories")
    print("=" * 80)
    
    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    total_manuals = sum(len(urls) for brands in TEST_MANUALS.values() for urls in brands.values())
    print(f"\nWill extract {total_manuals} manuals ({MAX_PAGES} pages each)")
    print(f"Output to: {OUTPUT_DIR.absolute()}\n")
    
    results_summary = []
    manual_count = 0
    
    with sync_playwright() as p:
        # Use visible browser
        browser = p.chromium.launch(headless=False, slow_mo=50)
        
        for category, brands in TEST_MANUALS.items():
            print(f"\n{'='*60}")
            print(f"CATEGORY: {category.upper()}")
            print('='*60)
            
            for brand, urls in brands.items():
                # Create brand folder
                brand_dir = OUTPUT_DIR / category / brand
                brand_dir.mkdir(parents=True, exist_ok=True)
                
                for url in urls:
                    manual_count += 1
                    filename = get_filename_from_url(url)
                    output_path = brand_dir / filename
                    
                    print(f"\n[{manual_count}/{total_manuals}] {brand} - {filename}")
                    print(f"  URL: {url}")
                    
                    try:
                        result = extract_manual(browser, url)
                        
                        if result["pages_extracted"] > 0:
                            # Save to file
                            output_text = format_output(result, url)
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(output_text)
                            
                            avg_chars = result['total_chars'] / result['pages_extracted']
                            status = "✅ GOOD" if avg_chars > 100 else "⚠️ POOR"
                            print(f"  {status}: {result['pages_extracted']} pages, {result['total_chars']} chars")
                            print(f"  Saved: {output_path}")
                            
                            results_summary.append({
                                "category": category,
                                "brand": brand,
                                "file": filename,
                                "pages": result['pages_extracted'],
                                "chars": result['total_chars'],
                                "status": "GOOD" if avg_chars > 100 else "POOR"
                            })
                        else:
                            print(f"  ❌ FAILED: No content extracted")
                            results_summary.append({
                                "category": category,
                                "brand": brand,
                                "file": filename,
                                "pages": 0,
                                "chars": 0,
                                "status": "FAILED"
                            })
                        
                        # Small delay between manuals
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"  ❌ ERROR: {str(e)[:50]}")
                        results_summary.append({
                            "category": category,
                            "brand": brand,
                            "file": filename,
                            "pages": 0,
                            "chars": 0,
                            "status": "ERROR"
                        })
        
        browser.close()
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    good_count = sum(1 for r in results_summary if r["status"] == "GOOD")
    poor_count = sum(1 for r in results_summary if r["status"] == "POOR")
    failed_count = sum(1 for r in results_summary if r["status"] in ["FAILED", "ERROR"])
    
    print(f"\nResults: {good_count} GOOD, {poor_count} POOR, {failed_count} FAILED")
    print(f"\nBy Category:")
    
    for category in ["laptops", "desktops"]:
        cat_results = [r for r in results_summary if r["category"] == category]
        if cat_results:
            print(f"\n  {category.upper()}:")
            for r in cat_results:
                icon = "✅" if r["status"] == "GOOD" else "⚠️" if r["status"] == "POOR" else "❌"
                print(f"    {icon} {r['brand']}/{r['file']}: {r['pages']} pages, {r['chars']} chars")
    
    print(f"\n{'='*80}")
    print(f"Output saved to: {OUTPUT_DIR.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    main()

