"""
OCR-based text extraction v2 - Captures actual image URLs from each page

The URL pattern varies - this version navigates to each page and captures
the actual background image URL.
"""
from playwright.sync_api import sync_playwright
import requests
from PIL import Image
from io import BytesIO
import pytesseract
import re
import time
from pathlib import Path
from typing import Optional

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def get_manual_info_and_page_images(manual_url: str, max_pages: int = None) -> dict:
    """
    Navigate to each page and capture the actual background image URLs
    """
    print(f"\n📋 Getting manual info and page images...")
    
    result = {
        'title': '',
        'total_pages': 0,
        'pages': []  # List of {page_num, image_url}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Load first page
        page.goto(manual_url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)
        
        # Get title
        try:
            result['title'] = page.inner_text('h1')
            print(f"   Title: {result['title']}")
        except:
            pass
        
        # Get total pages
        try:
            page_text = page.inner_text('.btn')
            match = re.search(r'/\s*(\d+)', page_text)
            if match:
                result['total_pages'] = int(match.group(1))
                print(f"   Total Pages: {result['total_pages']}")
        except:
            pass
        
        if max_pages:
            pages_to_extract = min(max_pages, result['total_pages'])
        else:
            pages_to_extract = result['total_pages']
        
        print(f"\n📄 Capturing image URLs for {pages_to_extract} pages...")
        
        for page_num in range(1, pages_to_extract + 1):
            print(f"   Page {page_num}/{pages_to_extract}...", end=' ', flush=True)
            
            # Navigate to page
            if page_num == 1:
                page_url = manual_url
            else:
                page_url = f"{manual_url}?p={page_num}"
            
            try:
                page.goto(page_url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(1000)
                
                # Extract the background image URL from the .bi element
                image_url = page.evaluate('''() => {
                    const bi = document.querySelector('.bi');
                    if (!bi) return null;
                    const style = bi.getAttribute('style') || '';
                    const match = style.match(/url\\(['"']?([^'"')]+)['"']?\\)/);
                    return match ? match[1] : null;
                }''')
                
                if image_url:
                    # Make absolute URL if needed
                    if image_url.startswith('/'):
                        image_url = 'https://www.manua.ls' + image_url
                    
                    result['pages'].append({
                        'page_num': page_num,
                        'image_url': image_url
                    })
                    print(f"✅ {image_url.split('/')[-1]}")
                else:
                    print("⚠️ No image found")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        browser.close()
    
    return result


def download_and_ocr_page(image_url: str, referer: str) -> str:
    """Download image and extract text with OCR"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer,
    }
    
    try:
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # OCR
        text = pytesseract.image_to_string(
            image,
            lang='eng',
            config='--psm 6 --oem 3'
        )
        
        return text.strip()
        
    except Exception as e:
        return f"[Error: {e}]"


def extract_manual_with_ocr_v2(manual_url: str, output_path: Optional[Path] = None, max_pages: int = None) -> str:
    """
    Extract all text from manual using OCR v2
    """
    print(f"\n{'='*80}")
    print("OCR EXTRACTION v2")
    print(f"Manual: {manual_url}")
    print('='*80)
    
    # Get page info and image URLs
    info = get_manual_info_and_page_images(manual_url, max_pages)
    
    if not info['pages']:
        print("❌ No page images found!")
        return ""
    
    # Build output
    output = []
    output.append("=" * 80)
    output.append(info.get('title', 'MANUAL').upper())
    output.append("=" * 80)
    output.append("")
    output.append(f"Source: {manual_url}")
    output.append(f"Extracted via OCR")
    output.append(f"Total Pages: {info['total_pages']}")
    output.append("")
    output.append("-" * 80)
    output.append("")
    
    print(f"\n🔍 Extracting text from {len(info['pages'])} pages...")
    
    for page_info in info['pages']:
        page_num = page_info['page_num']
        image_url = page_info['image_url']
        
        print(f"   Page {page_num}...", end=' ', flush=True)
        
        text = download_and_ocr_page(image_url, manual_url)
        
        if text and not text.startswith('[Error'):
            output.append(f"\n{'='*80}")
            output.append(f"PAGE {page_num}")
            output.append('='*80)
            output.append(text)
            print(f"✅ ({len(text)} chars)")
        else:
            print(f"⚠️ {text[:50] if text else 'No text'}")
        
        time.sleep(0.3)
    
    full_text = '\n'.join(output)
    
    # Save if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"\n✅ Saved to: {output_path}")
    
    print(f"\n📊 Total extracted: {len(full_text)} characters")
    
    return full_text


if __name__ == "__main__":
    test_url = "https://www.manua.ls/asus/vivobook-16/manual"
    output_file = Path("ocr_test_output_v2.txt")
    
    print("="*80)
    print("OCR MANUAL EXTRACTOR v2")
    print("="*80)
    
    # Test with first 10 pages
    text = extract_manual_with_ocr_v2(test_url, output_file, max_pages=10)
    
    if text:
        print("\n📝 Sample of extracted text:")
        print("-"*40)
        # Show first 1500 chars
        lines = text.split('\n')
        for line in lines[:50]:
            print(line)
        print("-"*40)

