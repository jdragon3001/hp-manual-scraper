"""Investigate manualpdf.es connection"""
import requests
from bs4 import BeautifulSoup
import config

test_manual = "https://www.manua.ls/asus/vivobook-16/manual"

print("=" * 80)
print("Investigating manualpdf.es connection")
print("=" * 80)

# Step 1: Check if manua.ls redirects to manualpdf.es
print("\n1. Checking for redirects...")
response = requests.get(test_manual, headers=config.HEADERS, allow_redirects=True)
print(f"   Final URL: {response.url}")
print(f"   Redirect history: {[r.url for r in response.history]}")

# Step 2: Check HTML for any manualpdf.es references
print("\n2. Searching HTML for manualpdf.es references...")
soup = BeautifulSoup(response.content, 'lxml')
manualpdf_links = soup.find_all(href=lambda x: x and 'manualpdf.es' in x if x else False)
print(f"   Found {len(manualpdf_links)} links to manualpdf.es")
for link in manualpdf_links[:5]:
    print(f"   - {link.get('href')}")

# Step 3: Search in scripts for manualpdf.es
print("\n3. Checking JavaScript for manualpdf.es...")
scripts = soup.find_all('script')
manualpdf_in_js = []
for script in scripts:
    if script.string and 'manualpdf.es' in script.string:
        manualpdf_in_js.append(script.string[:300])
print(f"   Found in {len(manualpdf_in_js)} scripts")
for js in manualpdf_in_js[:2]:
    print(f"   {js}...")

# Step 4: Try direct manualpdf.es URL patterns
print("\n4. Testing direct manualpdf.es URLs...")
test_urls = [
    "https://manualpdf.es/asus/vivobook-16/manual",
    "https://manualpdf.es/asus/vivobook-16",
    "https://www.manualpdf.es/asus/vivobook-16/manual",
]
for url in test_urls:
    try:
        r = requests.head(url, headers=config.HEADERS, timeout=5, allow_redirects=True)
        print(f"   {url}")
        print(f"     Status: {r.status_code}, Final URL: {r.url}")
    except Exception as e:
        print(f"   {url} - Error: {str(e)[:50]}")

# Step 5: Check raw text for manualpdf.es
print("\n5. Searching entire page source...")
if 'manualpdf.es' in response.text:
    print("   ✓ Found 'manualpdf.es' in page source!")
    # Find context
    import re
    matches = re.finditer(r'.{0,100}manualpdf\.es.{0,100}', response.text)
    print("   Contexts:")
    for i, match in enumerate(list(matches)[:3], 1):
        print(f"   {i}. ...{match.group()}...")
else:
    print("   ✗ Not found in page source")



