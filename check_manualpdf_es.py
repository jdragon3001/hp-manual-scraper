"""Check if manualpdf.es has better content access"""
import requests
from bs4 import BeautifulSoup
import config

# Try the Spanish version
test_url = "https://www.manualpdf.es/asus/vivobook-16/manual"

print("Checking manualpdf.es structure...\n")

response = requests.get(test_url, headers=config.HEADERS, timeout=30)
soup = BeautifulSoup(response.content, 'lxml')

output = []

# Check for downloadable PDF
output.append("1. Looking for download links...")
download_links = soup.find_all('a', href=True)
pdf_downloads = []
for link in download_links:
    href = link.get('href', '')
    text = link.get_text(strip=True).lower()
    if 'download' in text or 'descargar' in text or 'pdf' in href.lower():
        pdf_downloads.append((href, text))

output.append(f"   Found {len(pdf_downloads)} potential download links:")
for href, text in pdf_downloads[:10]:
    output.append(f"   - {href} ({text})")

# Check for PDF URLs in page
output.append("\n2. Searching for PDF URLs...")
import re
pdf_urls = re.findall(r'https?://[^\s<>"]+?\.pdf[^"]*', response.text, re.IGNORECASE)
output.append(f"   Found {len(set(pdf_urls))} unique PDF URLs:")
for url in list(set(pdf_urls))[:5]:
    output.append(f"   - {url}")

# Check page structure
output.append("\n3. Checking page structure...")
viewer_page = soup.find('div', class_='viewer-page')
if viewer_page:
    text_len = len(viewer_page.get_text())
    output.append(f"   viewer-page found: {text_len} chars")
else:
    output.append("   No viewer-page found")

# Check for iframe
output.append("\n4. Checking for iframes...")
iframes = soup.find_all('iframe')
output.append(f"   Found {len(iframes)} iframes:")
for iframe in iframes[:3]:
    src = iframe.get('src', 'N/A')
    output.append(f"   - {src}")

# Check for different structure
output.append("\n5. Comparing to manua.ls...")
output.append(f"   Title: {soup.find('h1').get_text() if soup.find('h1') else 'Not found'}")
output.append(f"   Has .pf divs: {len(soup.find_all('div', class_='pf'))}")
output.append(f"   Has viewer-page: {'Yes' if soup.find('div', class_='viewer-page') else 'No'}")

# Save to file
with open('manualpdf_es_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('\n'.join(output))
print("\nSaved to: manualpdf_es_analysis.txt")



