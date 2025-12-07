"""Test script to analyze manual HTML structure and improve text extraction"""
import requests
from bs4 import BeautifulSoup
import config

# Test on a known manual  
test_url = "https://www.manua.ls/asus/vivobook-16/manual"

output = []
output.append("Fetching manual page...\n")
response = requests.get(test_url, headers=config.HEADERS, timeout=config.TIMEOUT)
soup = BeautifulSoup(response.content, 'lxml')

output.append("=" * 80)
output.append("METHOD 1: Current approach - div with 't m' classes")
output.append("=" * 80)
viewer_page = soup.find('div', class_='viewer-page')
if viewer_page:
    text_elements = viewer_page.find_all('div', class_=lambda x: x and 't m' in x if x else False)
    output.append(f"Found {len(text_elements)} text elements\n")

output.append("=" * 80)
output.append("METHOD 2: Get all text from viewer-page with separator")
output.append("=" * 80)
if viewer_page:
    all_text = viewer_page.get_text(separator=' ', strip=True)
    output.append(f"Total length: {len(all_text)} chars")
    output.append(f"Preview:\n{all_text[:800]}\n")

output.append("=" * 80)
output.append("METHOD 3: Check for iframe or embedded PDF viewer")
output.append("=" * 80)
iframes = soup.find_all('iframe')
output.append(f"Found {len(iframes)} iframes")
for iframe in iframes:
    output.append(f"  src: {iframe.get('src')}")

output.append("\n" + "=" * 80)
output.append("METHOD 4: Check for canvas elements (PDF.js rendering)")
output.append("=" * 80)
canvases = soup.find_all('canvas')
output.append(f"Found {len(canvases)} canvas elements")

output.append("\n" + "=" * 80)
output.append("METHOD 5: Look for text layer divs")
output.append("=" * 80)
# PDF.js often uses textLayer class
text_layers = soup.find_all('div', class_=lambda x: x and 'textlayer' in str(x).lower() if x else False)
output.append(f"Found {len(text_layers)} textLayer divs")

output.append("\n" + "=" * 80)
output.append("METHOD 6: Check viewer page structure and classes")
output.append("=" * 80)
if viewer_page:
    output.append(f"Viewer page classes: {viewer_page.get('class')}")
    # Get first level children
    children = list(viewer_page.children)
    output.append(f"Direct children: {len([c for c in children if c.name])}")
    for child in [c for c in children if c.name][:5]:
        output.append(f"  Tag: {child.name}, Classes: {child.get('class')}, ID: {child.get('id')}")

# Save to file
with open('text_extraction_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Analysis complete! Check 'text_extraction_analysis.txt' for results")
