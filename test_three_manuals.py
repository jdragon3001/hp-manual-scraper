"""
Test extraction on HP, MSI, and Lenovo manuals
Output to test_extraction folder
"""
from playwright.sync_api import sync_playwright
import time
import re
from pathlib import Path

OUTPUT_DIR = Path("test_extraction")
OUTPUT_DIR.mkdir(exist_ok=True)

# Test URLs - using specific manuals (5 pages each for quick test)
TEST_MANUALS = [
    {
        "name": "HP_EliteBook_840_G5",
        "url": "https://www.manua.ls/hp/elitebook-840-g5/manual",
        "max_pages": 5
    },
    {
        "name": "MSI_Stealth_16",
        "url": "https://www.manua.ls/msi/stealth-16-mercedes-amg/manual",
        "max_pages": 5
    },
    {
        "name": "Lenovo_ThinkPad_E16",
        "url": "https://www.manua.ls/lenovo/thinkpad-e16-gen-1/manual",
        "max_pages": 5
    }
]


def extract_manual(url: str, max_pages: int = 20) -> dict:
    """Extract manual with proper timing"""
    result = {
        "title": "",
        "total_pages": 0,
        "pages_extracted": 0,
        "total_chars": 0,
        "content": []
    }
    
    with sync_playwright() as p:
        # Use visible browser - less likely to be blocked
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Load manual
        print(f"  Loading page...")
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)  # Wait for JS to render
        
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
        
        pages_to_extract = min(max_pages, result["total_pages"]) if result["total_pages"] > 0 else max_pages
        print(f"  Title: {result['title']}")
        print(f"  Total pages: {result['total_pages']}, extracting first {pages_to_extract}")
        
        # Extract pages
        for page_num in range(1, pages_to_extract + 1):
            page_url = url if page_num == 1 else f"{url}?p={page_num}"
            
            try:
                page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
                time.sleep(3)  # Critical wait for JS rendering
                
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
                    status = "✓" if len(text) > 50 else "~"
                    print(f"    Page {page_num:2d}: {len(text):4d} chars {status}")
                else:
                    print(f"    Page {page_num:2d}: EMPTY")
                    
            except Exception as e:
                print(f"    Page {page_num:2d}: ERROR - {str(e)[:50]}")
        
        browser.close()
    
    return result


def format_output(result: dict) -> str:
    """Format result as text file"""
    lines = []
    lines.append("=" * 80)
    lines.append(result.get("title", "MANUAL").upper())
    lines.append("=" * 80)
    lines.append("")
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


def main():
    print("=" * 80)
    print("TESTING EXTRACTION ON 3 MANUALS")
    print("=" * 80)
    
    results = []
    
    for manual in TEST_MANUALS:
        print(f"\n{'='*60}")
        print(f"EXTRACTING: {manual['name']}")
        print(f"URL: {manual['url']}")
        print("=" * 60)
        
        try:
            result = extract_manual(manual['url'], manual['max_pages'])
            result["name"] = manual["name"]
            results.append(result)
            
            # Save to file
            output_path = OUTPUT_DIR / f"{manual['name']}_test.txt"
            output_text = format_output(result)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_text)
            
            print(f"\n  ✅ Saved to: {output_path}")
            print(f"  Stats: {result['pages_extracted']}/{result['total_pages']} pages, {result['total_chars']} chars")
            
            # Wait between manuals to avoid rate limiting
            print(f"  Waiting 5 seconds before next manual...")
            time.sleep(5)
            
        except Exception as e:
            print(f"\n  ❌ FAILED: {e}")
            results.append({"name": manual["name"], "error": str(e)})
            time.sleep(5)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['name']}: FAILED - {r['error'][:50]}")
        else:
            avg_chars = r['total_chars'] / max(r['pages_extracted'], 1)
            quality = "GOOD" if avg_chars > 100 else "POOR" if avg_chars > 20 else "BAD"
            print(f"  {'✅' if quality == 'GOOD' else '⚠️'} {r['name']}: {r['pages_extracted']} pages, {r['total_chars']} chars ({avg_chars:.0f} avg) [{quality}]")
    
    print("\n" + "=" * 80)
    print(f"Output saved to: {OUTPUT_DIR.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    main()

