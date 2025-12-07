"""
Font-based text decoder for manua.ls

The site encodes text using custom fonts with Unicode Private Use Area characters.
This script downloads the font files, extracts the character mapping, and decodes the text.

Prerequisites:
- pip install fonttools brotli
"""
from playwright.sync_api import sync_playwright
import requests
from fontTools.ttLib import TTFont
from io import BytesIO
import re
import json
from pathlib import Path


def download_font(url: str, referer: str) -> bytes:
    """Download a font file"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer,
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.content


def extract_font_mapping(font_data: bytes) -> dict:
    """
    Extract the character-to-glyph mapping from a font file.
    Returns a dict mapping Unicode codepoints to their actual characters.
    """
    font = TTFont(BytesIO(font_data))
    
    mapping = {}
    
    # Get the cmap (character map) table
    cmap = font.getBestCmap()
    
    if cmap:
        # The cmap maps Unicode codepoints to glyph names
        for codepoint, glyph_name in cmap.items():
            # Skip standard ASCII and common Unicode
            if codepoint < 0xE000:  # Private Use Area starts at 0xE000
                continue
            
            # Try to determine what character this glyph represents
            # The glyph name often contains hints like "uni0041" for 'A'
            if glyph_name.startswith('uni'):
                try:
                    actual_char = chr(int(glyph_name[3:], 16))
                    mapping[chr(codepoint)] = actual_char
                except:
                    pass
            elif len(glyph_name) == 1:
                mapping[chr(codepoint)] = glyph_name
            elif glyph_name in ['space', 'Space']:
                mapping[chr(codepoint)] = ' '
            elif glyph_name in ['period', 'Period']:
                mapping[chr(codepoint)] = '.'
            elif glyph_name in ['comma', 'Comma']:
                mapping[chr(codepoint)] = ','
            else:
                # Try to extract letter from glyph name
                match = re.match(r'^([A-Za-z])_', glyph_name)
                if match:
                    mapping[chr(codepoint)] = match.group(1)
    
    return mapping


def decode_text(encoded_text: str, mapping: dict) -> str:
    """Decode text using the font mapping"""
    decoded = []
    for char in encoded_text:
        if char in mapping:
            decoded.append(mapping[char])
        elif ord(char) < 0xE000:  # Normal character
            decoded.append(char)
        else:
            decoded.append(f'[{hex(ord(char))}]')  # Unknown
    return ''.join(decoded)


def get_page_text_with_fonts(manual_url: str, page_num: int = 1) -> dict:
    """
    Extract both the encoded text and font URLs from a manual page
    """
    if page_num == 1:
        url = manual_url
    else:
        url = f"{manual_url}?p={page_num}"
    
    result = {
        'encoded_texts': [],
        'font_urls': [],
        'decoded_text': ''
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture font requests
        def capture_font(request):
            if '.woff' in request.url:
                result['font_urls'].append(request.url)
        
        page.on('request', capture_font)
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)
        
        # Extract text elements
        texts = page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('.pf .t').forEach(el => {
                const text = el.textContent;
                if (text && text.trim()) {
                    results.push({
                        text: text,
                        className: el.className
                    });
                }
            });
            return results;
        }''')
        
        result['encoded_texts'] = texts
        browser.close()
    
    return result


def analyze_font_mapping(manual_url: str):
    """
    Analyze the font encoding used by a manual and try to decode it
    """
    print(f"\n{'='*80}")
    print("FONT ENCODING ANALYSIS")
    print(f"URL: {manual_url}")
    print('='*80)
    
    # Get page data
    print("\n📄 Extracting page data...")
    data = get_page_text_with_fonts(manual_url)
    
    print(f"\n📝 Found {len(data['encoded_texts'])} text elements")
    print(f"📁 Found {len(data['font_urls'])} font files")
    
    for url in data['font_urls']:
        print(f"   - {url}")
    
    # Show encoded text
    print("\n📜 Encoded text samples:")
    for item in data['encoded_texts'][:5]:
        text = item['text']
        hex_repr = ' '.join(f'{ord(c):04x}' for c in text[:20])
        print(f"   Raw: {repr(text[:50])}")
        print(f"   Hex: {hex_repr}")
        print()
    
    # Try to decode fonts
    print("\n🔤 Analyzing font mappings...")
    all_mappings = {}
    
    for font_url in data['font_urls']:
        print(f"\n   Downloading: {font_url.split('/')[-1]}")
        try:
            font_data = download_font(font_url, manual_url)
            mapping = extract_font_mapping(font_data)
            all_mappings.update(mapping)
            print(f"   Found {len(mapping)} character mappings")
            
            # Show some mappings
            for enc, dec in list(mapping.items())[:10]:
                print(f"      {repr(enc)} ({hex(ord(enc))}) -> {repr(dec)}")
        except Exception as e:
            print(f"   Error: {e}")
    
    # Try to decode the text
    if all_mappings:
        print("\n🔓 Attempting to decode text...")
        for item in data['encoded_texts'][:3]:
            encoded = item['text']
            decoded = decode_text(encoded, all_mappings)
            print(f"\n   Encoded: {repr(encoded[:50])}")
            print(f"   Decoded: {decoded[:50]}")
    
    return {
        'data': data,
        'mappings': all_mappings
    }


def try_alternative_decoding(manual_url: str):
    """
    Try an alternative approach - analyze glyph shapes or use OCR on rendered text
    """
    print("\n" + "="*80)
    print("ALTERNATIVE APPROACH: Render and OCR single characters")
    print("="*80)
    
    # This approach would render each unique character and use OCR to identify it
    # Skipping for now as it's complex
    print("\nThis would involve:")
    print("1. Render each unique PUA character to an image")
    print("2. Use OCR to identify the rendered character")
    print("3. Build a mapping table")
    print("\nFor now, recommend installing Tesseract and using ocr_extractor.py")


if __name__ == "__main__":
    test_url = "https://www.manua.ls/asus/vivobook-16/manual"
    
    print("="*80)
    print("FONT-BASED TEXT DECODER")
    print("="*80)
    
    # First, install required packages
    print("\n📦 Checking dependencies...")
    try:
        from fontTools.ttLib import TTFont
        print("   ✅ fonttools installed")
    except ImportError:
        print("   ❌ fonttools not installed")
        print("   Run: pip install fonttools brotli")
        exit(1)
    
    # Analyze the font encoding
    result = analyze_font_mapping(test_url)
    
    # Show conclusion
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    
    if result['mappings']:
        print("\n✅ Font mappings found! Text can potentially be decoded.")
        print(f"   Total mappings: {len(result['mappings'])}")
    else:
        print("\n⚠️  No useful font mappings extracted.")
        print("   The font uses custom glyph names that don't reveal the original characters.")
        print("\n   RECOMMENDED: Use OCR approach instead")
        print("   1. Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Run: python ocr_extractor.py")

