"""Check if actual PDF files are available for download"""
import requests
from bs4 import BeautifulSoup
import config

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

response = requests.get(test_url, headers=config.HEADERS, timeout=config.TIMEOUT)
soup = BeautifulSoup(response.content, 'lxml')

output = []
output.append("Searching for PDF download links...\n")

# Method 1: Look for download buttons/links
download_links = soup.find_all('a', href=True)
pdf_links = []
for link in download_links:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if 'pdf' in href.lower() or 'download' in text.lower() or 'pdf' in text.lower():
        pdf_links.append((href, text))
        
output.append(f"Found {len(pdf_links)} potential PDF links:")
for href, text in pdf_links[:10]:
    output.append(f"  {href} - '{text}'")

# Method 2: Check for data attributes or hidden fields with PDF URLs
output.append("\n\nSearching for PDF URLs in script tags...")
scripts = soup.find_all('script')
pdf_in_scripts = []
for script in scripts:
    if script.string and 'pdf' in script.string.lower():
        pdf_in_scripts.append(script.string[:200])
output.append(f"Found {len(pdf_in_scripts)} scripts mentioning 'pdf'")
for script_text in pdf_in_scripts[:3]:
    output.append(f"  {script_text}...")

# Method 3: Look in page source for any PDF URLs
output.append("\n\nSearching raw HTML for PDF URLs...")
import re
pdf_urls = re.findall(r'https?://[^\s<>"]+?\.pdf', response.text, re.IGNORECASE)
output.append(f"Found {len(pdf_urls)} PDF URLs in source:")
for url in list(set(pdf_urls))[:10]:
    output.append(f"  {url}")

# Method 4: Check for manual download endpoint
output.append("\n\nChecking common download endpoints...")
possible_pdf_urls = [
    f"https://www.manua.ls/download/asus/vivobook-16",
    f"https://www.manua.ls/asus/vivobook-16/download",
    f"https://www.manua.ls/asus/vivobook-16/manual.pdf",
    f"https://www.manua.ls/api/manual/asus/vivobook-16/pdf",
]
for url in possible_pdf_urls:
    try:
        r = requests.head(url, headers=config.HEADERS, timeout=5, allow_redirects=True)
        output.append(f"  {url} - Status: {r.status_code}, Content-Type: {r.headers.get('content-type', 'N/A')}")
    except Exception as e:
        output.append(f"  {url} - Error: {str(e)[:50]}")

# Save to file
with open('pdf_download_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Analysis complete! Check 'pdf_download_analysis.txt'")

