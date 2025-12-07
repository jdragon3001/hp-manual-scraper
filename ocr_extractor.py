"""
OCR-based text extraction for image-rendered manuals on manua.ls

Some manuals render pages as webp background images instead of HTML text.
This module downloads those images and uses OCR (Tesseract) to extract text.

Prerequisites:
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- pip install pytesseract pillow
"""
from playwright.sync_api import sync_playwright
import requests
from PIL import Image
from io import BytesIO
import pytesseract
import re
import time
from pathlib import Path
from typing import Optional, List, Tuple

# Configure Tesseract path (adjust for your system)
# Windows typical path:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def get_manual_info(manual_url: str) -> dict:
    """Get basic info about the manual (title, total pages, file_id)"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture the viewer URL to get file_id
        viewer_info = {}
        def capture_viewer_url(request):
            if '/viewer/' in request.url and '.webp' in request.url:
                # Extract info from URL like: /viewer/90/4036890/1/bg1.webp
                match = re.search(r'/viewer/(\d+)/(\d+)/(\d+)/bg\d+\.webp', request.url)
                if match:
                    viewer_info['quality'] = match.group(1)
                    viewer_info['file_id'] = match.group(2)
                    viewer_info['base_url'] = request.url.rsplit('/', 2)[0]
        
        page.on('request', capture_viewer_url)
        page.goto(manual_url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)
        
        # Get title
        title = ""
        try:
            title = page.inner_text('h1')
        except:
            pass
        
        # Get total pages from page indicator
        total_pages = 1
        try:
            page_text = page.inner_text('.btn')
            match = re.search(r'/\s*(\d+)', page_text)
            if match:
                total_pages = int(match.group(1))
        except:
            pass
        
        browser.close()
        
        return {
            'title': title,
            'total_pages': total_pages,
            **viewer_info
        }


def download_page_image(manual_url: str, page_num: int, file_id: str, quality: str = '90') -> Optional[Image.Image]:
    """
    Download the background image for a specific page
    
    URL pattern: https://www.manua.ls/viewer/{quality}/{file_id}/{page_num}/bg{page_num}.webp
    """
    image_url = f"https://www.manua.ls/viewer/{quality}/{file_id}/{page_num}/bg{page_num}.webp"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': manual_url,
    }
    
    try:
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        return image
        
    except Exception as e:
        print(f"  ❌ Failed to download page {page_num}: {e}")
        return None


def ocr_image(image: Image.Image, lang: str = 'eng') -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use Tesseract with optimized settings
        text = pytesseract.image_to_string(
            image,
            lang=lang,
            config='--psm 6 --oem 3'  # Assume uniform text block, use LSTM engine
        )
        
        return text.strip()
        
    except Exception as e:
        print(f"  ❌ OCR error: {e}")
        return ""


def extract_manual_with_ocr(manual_url: str, output_path: Optional[Path] = None) -> str:
    """
    Extract all text from an image-based manual using OCR
    
    Args:
        manual_url: URL of the manual page
        output_path: Optional path to save the extracted text
    
    Returns:
        Complete extracted text
    """
    print(f"\n{'='*80}")
    print(f"OCR EXTRACTION")
    print(f"Manual: {manual_url}")
    print('='*80)
    
    # Get manual info
    print("\n📋 Getting manual info...")
    info = get_manual_info(manual_url)
    
    print(f"   Title: {info.get('title', 'Unknown')}")
    print(f"   Total Pages: {info.get('total_pages', 'Unknown')}")
    print(f"   File ID: {info.get('file_id', 'Unknown')}")
    
    if not info.get('file_id'):
        print("❌ Could not determine file_id - manual may use HTML text rendering")
        return ""
    
    # Build output
    output = []
    output.append("=" * 80)
    output.append(info.get('title', 'MANUAL').upper())
    output.append("=" * 80)
    output.append("")
    output.append(f"Source: {manual_url}")
    output.append(f"Extracted via OCR")
    output.append("")
    output.append("-" * 80)
    output.append("")
    
    total_pages = info.get('total_pages', 1)
    file_id = info['file_id']
    quality = info.get('quality', '90')
    
    print(f"\n📄 Extracting {total_pages} pages...")
    
    for page_num in range(1, total_pages + 1):
        print(f"   Page {page_num}/{total_pages}...", end=' ', flush=True)
        
        # Download image
        image = download_page_image(manual_url, page_num, file_id, quality)
        
        if image:
            # OCR the image
            text = ocr_image(image)
            
            if text:
                output.append(f"\n{'='*80}")
                output.append(f"PAGE {page_num}")
                output.append('='*80)
                output.append(text)
                print(f"✅ ({len(text)} chars)")
            else:
                print("⚠️ No text found")
        else:
            print("❌ Download failed")
        
        # Small delay between pages
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


def check_tesseract_installed() -> bool:
    """Check if Tesseract is installed and accessible"""
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract not found: {e}")
        print("\n📝 To install Tesseract on Windows:")
        print("   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Run the installer")
        print("   3. Update the path in this script if needed")
        print(f"   4. Current path: {pytesseract.pytesseract.tesseract_cmd}")
        return False


if __name__ == "__main__":
    print("="*80)
    print("OCR MANUAL EXTRACTOR")
    print("="*80)
    
    # Check Tesseract installation
    print("\n🔍 Checking Tesseract installation...")
    if not check_tesseract_installed():
        print("\n⚠️  Install Tesseract before running OCR extraction")
        exit(1)
    
    # Test with the problematic manual
    test_url = "https://www.manua.ls/asus/vivobook-16/manual"
    output_file = Path("ocr_test_output.txt")
    
    print(f"\n🧪 Testing OCR extraction on image-based manual...")
    text = extract_manual_with_ocr(test_url, output_file)
    
    if text:
        print("\n📝 Sample of extracted text:")
        print("-"*40)
        # Show first 1000 chars
        print(text[:1000])
        print("-"*40)

