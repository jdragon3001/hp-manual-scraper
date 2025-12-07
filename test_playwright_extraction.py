"""Test the new Playwright-based text extraction on a single manual"""
from src.playwright_text_extractor import extract_manual_text_playwright
import sys

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

print("=" * 80)
print("Testing Playwright-based text extraction")
print("=" * 80)
print(f"\nExtracting from: {test_url}")
print("This will take a couple of minutes as it loads all pages...\n")

text = extract_manual_text_playwright(test_url)

if text:
    print(f"\n✓ SUCCESS! Extracted {len(text)} characters")
    print(f"\nFirst 1000 characters:\n{'-' * 80}")
    print(text[:1000])
    print(f"{'-' * 80}\n")
    
    # Save to test file
    with open('test_extraction_output.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Full output saved to: test_extraction_output.txt")
    
    # Check quality indicators
    print("\n" + "=" * 80)
    print("QUALITY CHECK:")
    print("=" * 80)
    words = text.split()
    print(f"  Total words: {len(words)}")
    print(f"  Contains 'PAGE': {' PAGE ' in text}")
    print(f"  Contains 'SPECIFICATIONS': {'SPECIFICATIONS' in text}")
    print(f"  Contains 'FAQ': {'FAQ' in text or 'QUESTION' in text}")
    
    # Check for gibberish indicators
    lines = text.split('\n')
    very_short_lines = [l for l in lines if len(l.strip()) > 0 and len(l.strip()) < 3]
    print(f"  Very short lines (< 3 chars): {len(very_short_lines)} / {len([l for l in lines if l.strip()])}")
    
    if len(words) > 100 and len(very_short_lines) < 50:
        print("\n✓ Quality looks GOOD!")
    else:
        print("\n⚠ Quality might be poor")
else:
    print("✗ FAILED to extract text")
    sys.exit(1)



