"""
Robust Manual Extractor with Fallbacks

Strategy:
1. Try text extraction (existing method)
2. If text is too short (<100 chars per page avg), download page images as backup
3. Optionally run OCR on images if Tesseract is available

This ensures we always get SOMETHING from every manual.
"""
from playwright.sync_api import sync_playwright
import requests
from pathlib import Path
import time
import re
from typing import Optional, Tuple
import config
from src.utils import setup_logging, sanitize_filename

logger = setup_logging(__name__)

# Check if Tesseract is available
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image
    from io import BytesIO
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    logger.info("Tesseract OCR is available for fallback")
except:
    logger.info("Tesseract OCR not available - will save images as fallback")


def extract_page_text(page, page_num: int) -> str:
    """Extract text from current page using innerText with proper wait"""
    try:
        page.wait_for_selector('.viewer-page', timeout=15000)
        time.sleep(3)  # Critical: wait for JS rendering to complete
        
        text = page.eval_on_selector('.viewer-page', '(element) => element.innerText')
        return text.strip() if text else ""
    except:
        return ""


def get_page_image_url(page) -> Optional[str]:
    """Extract the background image URL from the current page"""
    try:
        image_url = page.evaluate('''() => {
            const bi = document.querySelector('.bi');
            if (!bi) return null;
            const style = bi.getAttribute('style') || '';
            const match = style.match(/url\\(['"']?([^'"')]+)['"']?\\)/);
            return match ? match[1] : null;
        }''')
        
        if image_url and image_url.startswith('/'):
            image_url = 'https://www.manua.ls' + image_url
        
        return image_url
    except:
        return None


def download_image(image_url: str, referer: str) -> Optional[bytes]:
    """Download an image and return bytes"""
    try:
        headers = {
            'User-Agent': config.HEADERS['User-Agent'],
            'Referer': referer,
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return None


def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on image bytes if Tesseract is available"""
    if not TESSERACT_AVAILABLE:
        return ""
    
    try:
        from PIL import Image
        from io import BytesIO
        import pytesseract
        
        image = Image.open(BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        text = pytesseract.image_to_string(image, lang='eng', config='--psm 6 --oem 3')
        return text.strip()
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return ""


def extract_manual_robust(manual_url: str, save_images_on_fail: bool = True) -> Tuple[str, list]:
    """
    Extract manual with fallbacks
    
    Returns:
        Tuple of (text_content, list_of_image_paths)
    """
    logger.info(f"Robust extraction: {manual_url}")
    
    output = []
    image_paths = []
    pages_with_text = 0
    total_text_chars = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent=config.HEADERS['User-Agent']
        )
        page = context.new_page()
        
        # Load manual
        page.goto(manual_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(2)
        
        # Get title
        title = ""
        try:
            title = page.inner_text('h1')
            output.append("=" * 80)
            output.append(title.upper())
            output.append("=" * 80)
            output.append("")
        except:
            pass
        
        # Get subtitle/info
        try:
            subtitle = page.inner_text('.manual__subtitle')
            output.append(subtitle)
            output.append("-" * 80)
            output.append("")
        except:
            pass
        
        # Get description
        try:
            description = page.inner_text('.manual__description')
            output.append("DESCRIPTION:")
            output.append(description)
            output.append("")
            output.append("-" * 80)
            output.append("")
        except:
            pass
        
        # Get TOC
        try:
            toc_items = page.query_selector_all('.toc__container a')
            if toc_items:
                output.append("TABLE OF CONTENTS:")
                output.append("")
                for item in toc_items:
                    page_num = item.get_attribute('data-page') or ''
                    text = item.inner_text()
                    if text:
                        output.append(f"  Page {page_num:>3}: {text}")
                output.append("")
                output.append("-" * 80)
                output.append("")
        except:
            pass
        
        # Get total pages
        total_pages = 1
        try:
            page_indicator = page.inner_text('.btn')
            match = re.search(r'/\s*(\d+)', page_indicator)
            if match:
                total_pages = int(match.group(1))
        except:
            pass
        
        logger.info(f"Extracting {total_pages} pages...")
        output.append("MANUAL CONTENT:")
        output.append("")
        
        # First pass: Try text extraction
        page_texts = {}
        page_images = {}
        
        for page_num in range(1, total_pages + 1):
            if page_num == 1:
                page_url = manual_url
            else:
                page_url = f"{manual_url}?p={page_num}"
            
            try:
                page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
                time.sleep(1)
                
                # Try text extraction
                text = extract_page_text(page, page_num)
                
                if text and len(text) > 5:
                    page_texts[page_num] = text
                    total_text_chars += len(text)
                    pages_with_text += 1
                else:
                    # Get image URL for fallback
                    img_url = get_page_image_url(page)
                    if img_url:
                        page_images[page_num] = img_url
                
            except Exception as e:
                logger.warning(f"Error on page {page_num}: {e}")
            
            # Progress logging
            if page_num % 10 == 0:
                logger.info(f"  Progress: {page_num}/{total_pages} pages")
        
        browser.close()
    
    # Analyze results
    avg_chars_per_page = total_text_chars / max(pages_with_text, 1)
    text_extraction_success = avg_chars_per_page > 50 and pages_with_text > total_pages * 0.5
    
    logger.info(f"Text extraction: {pages_with_text}/{total_pages} pages, {total_text_chars} chars total, {avg_chars_per_page:.0f} avg/page")
    
    # Build output with text
    for page_num in sorted(page_texts.keys()):
        output.append(f"\n{'='*80}")
        output.append(f"PAGE {page_num}")
        output.append('='*80)
        output.append(page_texts[page_num])
    
    # Handle fallback for pages without text
    if page_images and (not text_extraction_success or save_images_on_fail):
        logger.info(f"Downloading {len(page_images)} page images as fallback...")
        
        for page_num, img_url in page_images.items():
            img_bytes = download_image(img_url, manual_url)
            
            if img_bytes:
                # Try OCR if available
                if TESSERACT_AVAILABLE:
                    ocr_text = ocr_image_bytes(img_bytes)
                    if ocr_text and len(ocr_text) > 10:
                        output.append(f"\n{'='*80}")
                        output.append(f"PAGE {page_num} (OCR)")
                        output.append('='*80)
                        output.append(ocr_text)
                        continue
                
                # Save image path for reference
                image_paths.append({
                    'page': page_num,
                    'url': img_url,
                    'bytes': img_bytes
                })
    
    # Add specs section
    output.append("")
    output.append("-" * 80)
    output.append("")
    
    full_text = '\n'.join(output)
    full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)
    
    return full_text, image_paths


def save_manual_robust(manual_info: dict, category: str, format: str = 'txt') -> bool:
    """
    Extract and save manual with fallbacks
    
    Args:
        manual_info: Dictionary with manual information
        category: 'laptops' or 'desktops'
        format: 'txt' or 'md'
    
    Returns:
        True if successful
    """
    if not manual_info or not manual_info.get('url'):
        logger.warning(f"No URL for manual")
        return False
    
    # Determine output directory
    base_dir = config.LAPTOP_DIR if category == 'laptops' else config.DESKTOP_DIR
    brand = manual_info.get('brand', 'Unknown')
    brand_folder = sanitize_filename(brand)
    output_dir = base_dir / brand_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    model = manual_info.get('model', 'Unknown')
    pages = manual_info.get('pages', '')
    
    if pages:
        filename = f"{brand}_{model}_{pages}pages.{format}"
    else:
        filename = f"{brand}_{model}.{format}"
    
    filename = sanitize_filename(filename)
    output_path = output_dir / filename
    
    # Check if already exists
    if output_path.exists():
        logger.info(f"File already exists: {output_path.name}")
        return True
    
    # Extract with robust method
    logger.info(f"Robust extraction: {output_path.name}")
    text_content, image_paths = extract_manual_robust(manual_info['url'])
    
    if not text_content or len(text_content) < 100:
        logger.error(f"Failed to extract content from {manual_info['url']}")
        return False
    
    # Save text file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"Saved: {output_path.name} ({len(text_content)} chars)")
        
        # Save images as backup if extraction was poor
        if image_paths:
            images_dir = output_dir / f"{sanitize_filename(model)}_images"
            images_dir.mkdir(exist_ok=True)
            
            for img_info in image_paths:
                img_path = images_dir / f"page_{img_info['page']:03d}.webp"
                with open(img_path, 'wb') as f:
                    f.write(img_info['bytes'])
            
            logger.info(f"Saved {len(image_paths)} backup images to {images_dir.name}/")
        
        time.sleep(config.REQUEST_DELAY)
        return True
        
    except Exception as e:
        logger.error(f"Error saving {output_path}: {e}")
        return False


if __name__ == "__main__":
    # Test the robust extractor
    print("="*80)
    print("ROBUST EXTRACTOR TEST")
    print("="*80)
    
    # Test on a manual
    test_url = "https://www.manua.ls/hp/14/manual"
    
    print(f"\nTesting: {test_url}")
    print("-"*80)
    
    text, images = extract_manual_robust(test_url)
    
    print(f"\n{'='*80}")
    print("RESULTS")
    print('='*80)
    print(f"Text length: {len(text)} chars")
    print(f"Backup images: {len(images)}")
    
    # Show sample
    print(f"\n{'='*80}")
    print("TEXT SAMPLE (first 2000 chars)")
    print('='*80)
    print(text[:2000])
    
    # Save test output
    with open('robust_test_output.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"\nSaved to: robust_test_output.txt")

