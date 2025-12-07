"""Test script to inspect the actual page content structure"""
import requests
from bs4 import BeautifulSoup
import config

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

response = requests.get(test_url, headers=config.HEADERS, timeout=config.TIMEOUT)
soup = BeautifulSoup(response.content, 'lxml')

output = []

# Find the actual page div
page_div = soup.find('div', class_='page-1')
if page_div:
    output.append("Found page-1 div!")
    output.append(f"Classes: {page_div.get('class')}")
    output.append(f"\nDirect children count: {len(list(page_div.children))}")
    
    # Get all text from this div
    all_text = page_div.get_text(separator=' ', strip=True)
    output.append(f"\nTotal text length: {len(all_text)} chars")
    output.append(f"\nFirst 1000 chars:\n{all_text[:1000]}")
    
    # Look for text divs within
    text_divs = page_div.find_all('div', class_=lambda x: x and any('t' in cls for cls in x) if x else False)
    output.append(f"\n\nFound {len(text_divs)} divs with 't' in class")
    output.append("\nFirst 30 text divs:")
    for i, div in enumerate(text_divs[:30], 1):
        classes = ' '.join(div.get('class', []))
        text = div.get_text()
        # Get position styles if any
        style = div.get('style', '')
        output.append(f"  {i}. classes='{classes}' text='{text}' style='{style[:50]}'")
else:
    output.append("page-1 div not found!")
    
    # Try alternative - look for all divs with 'pf' class
    pf_divs = soup.find_all('div', class_='pf')
    output.append(f"\nFound {len(pf_divs)} divs with class 'pf'")

# Save to file
with open('page_structure_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Analysis complete! Check 'page_structure_analysis.txt'")



