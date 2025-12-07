"""
Test OCR quality and try different settings to improve text extraction
"""
from playwright.sync_api import sync_playwright
import requests
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import pytesseract
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_page_image_url(manual_url: str, page_num: int) -> str:
    """Get image URL for a specific page"""
    if page_num == 1:
        url = manual_url
    else:
        url = f"{manual_url}?p={page_num}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)
        
        image_url = page.evaluate('''() => {
            const bi = document.querySelector('.bi');
            if (!bi) return null;
            const style = bi.getAttribute('style') || '';
            const match = style.match(/url\\(['"']?([^'"')]+)['"']?\\)/);
            return match ? match[1] : null;
        }''')
        
        browser.close()
        
        if image_url and image_url.startswith('/'):
            image_url = 'https://www.manua.ls' + image_url
        
        return image_url


def download_image(image_url: str, referer: str) -> Image.Image:
    """Download image"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer,
    }
    response = requests.get(image_url, headers=headers, timeout=30)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def test_ocr_settings(image: Image.Image) -> dict:
    """Test different OCR settings on the same image"""
    results = {}
    
    # Convert to RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Original image info
    print(f"\n📊 Image Info:")
    print(f"   Size: {image.size}")
    print(f"   Mode: {image.mode}")
    
    # Save original for inspection
    image.save('test_page_original.png')
    print(f"   Saved: test_page_original.png")
    
    # Test 1: Default settings
    print("\n🔧 Test 1: Default settings (--psm 6)")
    text1 = pytesseract.image_to_string(image, lang='eng', config='--psm 6 --oem 3')
    results['default'] = text1
    print(f"   Chars: {len(text1)}")
    print(f"   Text: {text1[:200]}")
    
    # Test 2: Single block mode
    print("\n🔧 Test 2: Single block mode (--psm 4)")
    text2 = pytesseract.image_to_string(image, lang='eng', config='--psm 4 --oem 3')
    results['single_block'] = text2
    print(f"   Chars: {len(text2)}")
    print(f"   Text: {text2[:200]}")
    
    # Test 3: Sparse text mode
    print("\n🔧 Test 3: Sparse text (--psm 11)")
    text3 = pytesseract.image_to_string(image, lang='eng', config='--psm 11 --oem 3')
    results['sparse'] = text3
    print(f"   Chars: {len(text3)}")
    print(f"   Text: {text3[:200]}")
    
    # Test 4: Enhanced contrast
    print("\n🔧 Test 4: Enhanced contrast")
    enhancer = ImageEnhance.Contrast(image)
    enhanced = enhancer.enhance(2.0)
    enhanced.save('test_page_enhanced.png')
    text4 = pytesseract.image_to_string(enhanced, lang='eng', config='--psm 6 --oem 3')
    results['enhanced'] = text4
    print(f"   Chars: {len(text4)}")
    print(f"   Text: {text4[:200]}")
    
    # Test 5: Scaled up 2x
    print("\n🔧 Test 5: Scaled up 2x")
    scaled = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    scaled.save('test_page_scaled.png')
    text5 = pytesseract.image_to_string(scaled, lang='eng', config='--psm 6 --oem 3')
    results['scaled'] = text5
    print(f"   Chars: {len(text5)}")
    print(f"   Text: {text5[:200]}")
    
    # Test 6: Grayscale + sharpen
    print("\n🔧 Test 6: Grayscale + sharpen")
    gray = image.convert('L')
    sharp = gray.filter(ImageFilter.SHARPEN)
    sharp.save('test_page_sharp.png')
    text6 = pytesseract.image_to_string(sharp, lang='eng', config='--psm 6 --oem 3')
    results['sharp'] = text6
    print(f"   Chars: {len(text6)}")
    print(f"   Text: {text6[:200]}")
    
    # Best result
    best_key = max(results.keys(), key=lambda k: len(results[k]))
    print(f"\n✅ Best result: {best_key} ({len(results[best_key])} chars)")
    
    return results


if __name__ == "__main__":
    test_url = "https://www.manua.ls/asus/vivobook-16/manual"
    
    print("="*80)
    print("OCR QUALITY TEST")
    print("="*80)
    
    # Test on page 11 which should have actual text content
    print("\n📄 Testing on page 11 (should have text content)...")
    
    image_url = get_page_image_url(test_url, 11)
    print(f"   Image URL: {image_url}")
    
    image = download_image(image_url, test_url)
    results = test_ocr_settings(image)
    
    print("\n" + "="*80)
    print("FULL BEST RESULT:")
    print("="*80)
    best_key = max(results.keys(), key=lambda k: len(results[k]))
    print(results[best_key])

