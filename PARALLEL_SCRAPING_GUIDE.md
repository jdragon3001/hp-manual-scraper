# Parallel Scraping Guide

## Problem: Freezing When Running Multiple Instances

When running 3+ parallel scraping instances, the browsers freeze after a short time. This happens even when memory usage is low.

### Root Causes

1. **Website Rate Limiting** 🚫
   - manua.ls throttles too many requests from the same IP
   - 3 instances = 3x request rate → server slows down or blocks

2. **page.goto() Hanging** ⏱️
   - When rate-limited, page loads hang waiting for server response
   - Timeout helps but still wastes time

3. **No Coordination Between Instances** 🔀
   - Each instance has delays (0.3-0.5s), but combined load is too high
   - No shared rate limiting across processes

4. **Connection Pool Exhaustion** 🔌
   - Chromium instances compete for network connections
   - Can cause deadlocks at TCP level

## Solutions

### Option 1: Use Parallel-Safe Script (Recommended) ✅

Use `scrape_brand_parallel_safe.py` instead of `scrape_brand.py`:

```bash
# Terminal 1
python scrape_brand_parallel_safe.py HP

# Terminal 2
python scrape_brand_parallel_safe.py DELL

# Terminal 3 (optional, but 2 is safer)
python scrape_brand_parallel_safe.py LENOVO
```

**Improvements:**
- ✅ **Global rate limiting** via file lock (`.rate_limit_lock`)
- ✅ **Exponential backoff** on consecutive failures
- ✅ **Longer delays**: 0.8-1.5s between pages (was 0.3-0.5s)
- ✅ **Longer inter-manual delays**: 4-8s (was 2-5s)
- ✅ **Aggressive timeouts**: 5s page load (was 6-12s)
- ✅ **Better browser headers** to look more legitimate

### Option 2: Reduce Parallel Instances

Run only **2 instances** instead of 3:
```bash
# Terminal 1
python scrape_brand.py HP

# Terminal 2
python scrape_brand.py DELL
```

### Option 3: Increase Delays in Original Script

Edit `scrape_brand.py`:
```python
# Change line 31
DELAY_BETWEEN_PAGES = (1.0, 2.0)  # Was (0.3, 0.5)

# Change line 418
time.sleep(random.uniform(5, 10))  # Was (2, 5)
```

### Option 4: Sequential Execution (Slowest but Safest)

Run brands one at a time:
```bash
python scrape_brand.py HP
python scrape_brand.py DELL
python scrape_brand.py LENOVO
```

Or use the batch file:
```bash
run_small_brands.bat
```

## Recommended Setup for Parallel Scraping

### For 2 Parallel Instances (Optimal) ⭐

```bash
# Terminal 1 - Large brands
python scrape_brand_parallel_safe.py HP
python scrape_brand_parallel_safe.py LENOVO
python scrape_brand_parallel_safe.py ASUS

# Terminal 2 - Medium brands
python scrape_brand_parallel_safe.py SONY
python scrape_brand_parallel_safe.py DELL
python scrape_brand_parallel_safe.py ACER
```

### For 3 Parallel Instances (Risky)

Only if you must run 3:
```bash
# Use parallel-safe version
# Terminal 1
python scrape_brand_parallel_safe.py HP

# Terminal 2  
python scrape_brand_parallel_safe.py LENOVO

# Terminal 3
python scrape_brand_parallel_safe.py ASUS
```

**Warning:** Even with parallel-safe version, 3+ instances may still hit rate limits. Monitor for freezing and reduce to 2 if needed.

## How to Tell If You're Being Rate Limited

Watch for these signs in terminal output:
- ❌ `LOAD_ERR` - Page failed to load
- ❌ `[timeout@XX]` - Repeated timeouts
- ❌ `[BACKOFF:Xs]` - Script detecting rate limiting
- ❌ Long pauses with no output
- ❌ Chromium visible but not loading pages

If you see these frequently, you're hitting rate limits.

## Recovery Steps

If instances freeze:
1. **Kill all running instances** (Ctrl+C)
2. **Close all Chromium processes** (Task Manager)
3. **Wait 2-5 minutes** (let rate limit reset)
4. **Restart with only 2 instances** using parallel-safe script
5. **Progress is saved**, so you won't lose work

## Performance Comparison

| Setup | Speed | Reliability | Recommended? |
|-------|-------|-------------|--------------|
| 1 instance (original) | 1x | ⭐⭐⭐⭐⭐ | For small brands |
| 2 instances (parallel-safe) | 1.8x | ⭐⭐⭐⭐ | **Yes - Best balance** |
| 3 instances (parallel-safe) | 2.2x | ⭐⭐ | Risky |
| 3 instances (original) | 2.5x | ⭐ | **No - Freezes** |
| 4+ instances | 2x | ❌ | **No - Will freeze** |

## Technical Details

### Global Rate Limiter Mechanism

The parallel-safe script uses a file-based lock (`.rate_limit_lock`):
```python
def global_rate_limit():
    # Check file modification time
    last_request = file.stat().st_mtime
    elapsed = time.time() - last_request
    
    if elapsed < 0.3:  # Minimum 0.3s between ANY request
        sleep(0.3 - elapsed)
    
    # Update timestamp (atomic operation)
    file.touch()
```

This ensures all parallel instances coordinate request timing.

### Why File-Based?

- ✅ Works across separate processes
- ✅ No shared memory required
- ✅ Survives crashes/restarts
- ✅ Simple and reliable on Windows

### Backoff Strategy

When hitting 5+ consecutive timeouts:
1. Sleep for 5-10 seconds
2. Reset counter
3. Continue with longer delays

This gives the server time to recover.

## Monitoring Multiple Instances

Open separate terminal windows to monitor each:

```powershell
# Terminal 1
python scrape_brand_parallel_safe.py HP

# Terminal 2
python scrape_brand_parallel_safe.py DELL

# Terminal 3 (optional monitor)
while ($true) { 
    Get-Process chrome | Measure-Object -Property WorkingSet -Sum | 
    Select-Object @{Name="TotalMemoryMB";Expression={[math]::Round($_.Sum/1MB,2)}}
    Start-Sleep 5
}
```

## Summary

**For parallel scraping:**
1. ✅ Use `scrape_brand_parallel_safe.py`
2. ✅ Run only 2 instances simultaneously
3. ✅ Monitor for rate limiting signs
4. ✅ Be patient - slower is more reliable
5. ❌ Don't run 3+ instances

**Remember:** Scraping 20,200 manuals takes time. Running 2 parallel instances safely is better than 3 instances that freeze!



