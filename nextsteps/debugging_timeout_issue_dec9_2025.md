# Debugging ECS Timeout Issue - December 9, 2025

## Problem Summary

The scraper was failing on ECS brand manuals with the following symptoms:
- **Manual**: ECS T30Ii (103 pages)
- **URL**: https://www.manua.ls/ecs/t30ii/manual
- **Issue**: Timeout at page 20, empty content extracted
- **Time**: Taking 74.2 seconds, then failing
- **Result**: Manual queued for retry but retries also fail

## Root Cause Analysis

### Identified Issues:
1. **Too Aggressive Timeouts**: 6-second page load timeout was too short
2. **Low Retry Threshold**: Only 3 consecutive failures before giving up
3. **Short Delays**: 0.3-0.5s between pages may trigger rate limiting
4. **No Fallback**: Only tried `.viewer-page` selector, no alternative extraction methods
5. **Limited Diagnostics**: No detailed logging to understand failure points

### Contributing Factors:
- Website may be rate limiting automated requests
- Some manuals may use different rendering (image-based vs HTML text)
- Network congestion or slow server responses
- Pages may take longer to fully render

## Solutions Implemented

### 1. Increased Timeouts
**File**: `scrape_brand.py`

**Changes**:
- ✅ Page load timeout: 6s → 15s (line ~180)
- ✅ Selector wait timeout: 3s → 5s (line ~193)
- ✅ Consecutive failure threshold: 3 → 5 (line ~183)

### 2. Better Rate Limiting Protection
**Changes**:
- ✅ Delay between pages: 0.3-0.5s → 0.5-1.0s (line ~31)
- ✅ Delay between manuals: 2-5s → 3-7s (line ~418)
- ✅ Added 2s wait before retrying failed pages (line ~190)

### 3. Fallback Extraction Method
**Changes**:
- ✅ Try `.viewer-page` selector first
- ✅ If that fails, try `document.body.innerText`
- ✅ Handles both HTML text and alternative rendering methods

### 4. Enhanced Diagnostics
**New Files**:
- ✅ Created `diagnose_manual.py` - detailed manual testing tool
- ✅ Added empty page logging `[E{page_num}]`
- ✅ Added timeout logging `[T{page_num}]`
- ✅ Added manual type checking function

### 5. Updated Documentation
**Files Updated**:
- ✅ `PROBLEM_LOG.txt` - documented issue and solutions
- ✅ `nextsteps/debugging_timeout_issue_dec9_2025.md` (this file)

## Testing Steps

### Step 1: Test the Failing Manual
Run diagnostic on the specific manual that was failing:

```bash
conda activate manual-scraper
python diagnose_manual.py https://www.manua.ls/ecs/t30ii/manual
```

**What to look for**:
- Does page 1 load successfully?
- Are `.viewer-page` selectors present?
- Can we extract text from pages 1-3?
- What's the actual load time for page 10?

### Step 2: Resume ECS Scraping
With the fixes applied, restart the ECS scraping:

```bash
conda activate manual-scraper
python scrape_brand.py ECS
```

**What to monitor**:
- Are timeouts less frequent?
- Is content being extracted successfully?
- Watch for `[T{n}]` (timeout) and `[E{n}]` (empty) markers
- Check if manuals complete or still fail

### Step 3: Check Progress
Monitor the progress file and output:

```bash
# Check progress
cat progress/ECS_progress.json

# Check if any files were created
ls downloads/*/ECS/

# Check partial content (mid-extraction saves)
ls partial_content/ECS_*
```

## Expected Outcomes

### If Fixes Work:
- ✅ Longer timeouts allow slow pages to load
- ✅ More retries before giving up
- ✅ Fallback extraction catches alternative rendering
- ✅ Slower pace avoids rate limiting
- ✅ ECS manuals complete successfully

### If Issues Persist:
This indicates a deeper problem:
1. **Image-based rendering**: Manual uses OCR-required rendering (see PROBLEM_LOG.txt)
2. **IP blocking**: Website blocking your IP after detecting automation
3. **Geographic restrictions**: Content may be region-locked
4. **Authentication needed**: Some manuals may require login

**Next debugging steps if issues persist**:
1. Check if manual uses image rendering: `python detect_manual_type.py https://www.manua.ls/ecs/t30ii/manual`
2. Try with VPN or different IP
3. Check website terms of service for scraping policies
4. Consider using residential proxies or rotating IPs

## Files Modified

1. `scrape_brand.py` - Core scraper with timeout and delay fixes
2. `diagnose_manual.py` - New diagnostic tool
3. `PROBLEM_LOG.txt` - Issue documentation
4. `nextsteps/debugging_timeout_issue_dec9_2025.md` - This summary

## Commands Reference

```bash
# Activate environment
conda activate manual-scraper

# Test specific manual
python diagnose_manual.py <URL>

# Resume scraping
python scrape_brand.py ECS

# Check progress
cat progress/ECS_progress.json

# View scraper output
ls downloads/*/ECS/
```

## Next Steps

1. ✅ Run diagnostic on failing manual
2. ⏳ Resume ECS scraping with fixes
3. ⏳ Monitor for successful completion
4. ⏳ If successful, consider applying to other brands
5. ⏳ If not, investigate manual rendering type

---

**Status**: Fixes implemented, ready for testing
**Priority**: High - blocking ECS brand completion
**Last Updated**: December 9, 2025

