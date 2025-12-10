# Real Issue Found - December 9, 2025

## TL;DR

**The problem wasn't slow pages or bot detection.**  
**The T30Ii manual doesn't exist on the website anymore!**

The URL `https://www.manua.ls/ecs/t30ii/manual` **redirects to** `https://www.manua.ls/ecs` (brand page).

## How I Found It

1. **Speed test showed**: Text extraction was getting 0 characters
2. **Browser test showed**: `.viewer-page` selector didn't exist
3. **Manual navigation showed**: URL redirected from manual → brand page
4. **Comparison test showed**: G320 manual works fine, T30Ii redirects

## The Real Problem

Some manuals in your `manual_urls_cache.json` **were removed from the website**:
- ✅ G320 manual: Still exists, loads normally
- ❌ T30Ii manual: Removed, redirects to brand page

When the scraper tried to extract T30Ii:
1. Navigate to manual URL
2. Site redirects to brand page  
3. Wait for `.viewer-page` selector (never appears - no manual!)
4. Timeout after 3 seconds
5. Return 0 characters
6. Mark as EMPTY, queue for retry
7. Retry fails the same way
8. Loop forever on removed manuals

## The Fix

Added **redirect detection** to `scrape_brand.py`:

```python
response = page.goto(manual_url, wait_until='domcontentloaded', timeout=10000)

# Check if URL redirected (manual doesn't exist)
if page.url != manual_url and not page.url.startswith(manual_url):
    print(f"REDIRECT (manual removed) ", end="", flush=True)
    return None, 0, 0, False  # Don't retry, it's gone
```

And updated the handling:

```python
if not needs_restart and last_page == 0:
    # Manual was redirected - mark as done to skip it
    progress["done"].append(url)
    print(f"✗ SKIPPED (manual removed from site) ({elapsed:.1f}s)", flush=True)
```

## Test Results

```bash
Testing: https://www.manua.ls/ecs/g320/manual
  ✓ NO REDIRECT - Would extract this manual

Testing: https://www.manua.ls/ecs/t30ii/manual
  ✓ REDIRECT DETECTED - Would skip this manual
```

## Why This Explains Everything

- **"Slow" pages**: Not slow - just waiting for content that never loads
- **Timeouts**: Waiting for `.viewer-page` that doesn't exist
- **Empty extraction**: No manual = no content
- **Retry loops**: Retrying removed manuals forever

## What Happens Now

When you run the scraper:
- Working manuals: Extract normally ✅
- Removed manuals: Detect redirect, skip automatically ✅
- No more hanging on removed manuals
- No more empty retry loops

## Run It

```bash
conda activate manual-scraper
python scrape_brand.py ECS
```

You should now see:
- `✓` for successful extractions
- `✗ SKIPPED (manual removed from site)` for redirected manuals
- Much faster overall (not waiting on removed manuals)

## Bottom Line

**Jack, you were right** - it's a super simple site with no bot protection. The issue was removed manuals in the cache, not anything we were doing wrong. The fix is simple and tested. Should work great now!

---

**Status**: Fixed and tested ✅  
**Files Changed**: `scrape_brand.py`, `PROBLEM_LOG.txt`  
**Test Files**: `test_redirect_detection.py`, `check_page_structure.py`

