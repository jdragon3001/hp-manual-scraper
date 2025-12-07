"""Capture network requests to find the API endpoint that loads manual text"""
from playwright.sync_api import sync_playwright
import json

test_url = "https://www.manua.ls/asus/vivobook-16/manual"

print("=" * 80)
print("Capturing network requests while page loads...")
print("=" * 80)

captured_requests = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Show browser so you can see it
    context = browser.new_context()
    page = context.new_page()
    
    # Capture all network requests
    def handle_request(request):
        captured_requests.append({
            'url': request.url,
            'method': request.method,
            'resource_type': request.resource_type,
            'post_data': request.post_data if request.method == 'POST' else None
        })
    
    def handle_response(response):
        # Log responses with interesting content
        if any(keyword in response.url.lower() for keyword in ['api', 'json', 'text', 'content', 'manual', 'data', 'pdf']):
            try:
                content_type = response.headers.get('content-type', '')
                print(f"\n  Response: {response.url}")
                print(f"    Status: {response.status}")
                print(f"    Type: {content_type}")
                if 'json' in content_type:
                    print(f"    JSON response!")
            except:
                pass
    
    page.on('request', handle_request)
    page.on('response', handle_response)
    
    print(f"\nLoading: {test_url}\n")
    page.goto(test_url, wait_until='networkidle', timeout=60000)
    
    print("\n" + "=" * 80)
    print("Waiting 5 seconds for dynamic content to load...")
    print("=" * 80)
    page.wait_for_timeout(5000)
    
    browser.close()

# Analyze captured requests
print("\n" + "=" * 80)
print(f"Total requests captured: {len(captured_requests)}")
print("=" * 80)

# Filter interesting requests
interesting = []
for req in captured_requests:
    url = req['url'].lower()
    if any(keyword in url for keyword in ['api', 'json', 'text', 'content', 'manual', 'data', '/v1/', '/v2/', 'graphql']):
        interesting.append(req)

print(f"\nInteresting requests ({len(interesting)}):")
for req in interesting:
    print(f"\n  {req['method']} {req['resource_type']}")
    print(f"  {req['url']}")
    if req['post_data']:
        print(f"  POST data: {req['post_data'][:200]}")

# Save full log
with open('network_requests_log.json', 'w', encoding='utf-8') as f:
    json.dump(captured_requests, f, indent=2)

print(f"\n\nFull log saved to: network_requests_log.json")
print("=" * 80)



