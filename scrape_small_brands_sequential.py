"""
Sequential scraper for all brands with < 50 manuals
Runs one brand at a time, waiting for each to complete before starting the next.
This prevents race conditions and ensures clean execution.

Usage: python scrape_small_brands_sequential.py
"""
import subprocess
import sys
import time
from datetime import datetime

# All brands with < 50 manuals (90 brands, ~640 manuals total)
SMALL_BRANDS = [
    "ECS", "HONOR", "HUAWEI", "ADVANTECH", "INTEL", "IBM", "RAZER", "COMPAQ",
    "AORUS", "MICROSOFT", "FUJITSU-SIEMENS", "THOMSON", "VIZIO", "TECHBITE",
    "SYSTEM76", "SHUTTLE", "KOGAN", "NEC", "IGEL", "ELO", "MAXDATA", "HAIER",
    "XIAOMI", "AIRIS", "BEKO", "DURABOOK", "TARGA", "JYSK", "VIEWSONIC", "WYSE",
    "VXL", "MPMAN", "XPG", "LOCKNCHARGE", "MICROTECH", "TREKSTOR", "PROMETHEAN",
    "GIADA", "FAYTECH", "FOXCONN", "ATARI", "BENQ", "ROLAND", "WOOOD",
    "HUMANSCALE", "FLYBOOK", "SCHNEIDER", "HTC", "NEXOC", "RAZOR", "XPLORE",
    "TCL", "VULCAN", "ZEBRA", "HYUNDAI", "ODYS", "BELINEA", "COBY", "KIANO",
    "CORE-INNOVATIONS", "HERCULES", "ARCHOS", "EMATIC", "VISUAL-LAND", "CRAIG",
    "EVGA", "DYNABOOK", "GENERAL-DYNAMICS-ITRONIX", "CTL", "PRIXTON", "PYLE",
    "SEAGATE", "DELL-WYSE", "ARCTIC-COOLING", "CYBERNET", "NCOMPUTING", "AXIS",
    "CORSAIR", "OPTOMA", "BEMATECH", "ADVANCE", "INFOCUS", "PHILIPS", "AAEON",
    "MOXA", "VTECH", "TRIPP-LITE", "KRAMER", "PRODVX", "NCS"
]

def run_brand(brand_name, index, total):
    """Run scraper for a single brand and wait for completion"""
    print("\n" + "=" * 70)
    print(f"[{index}/{total}] Starting: {brand_name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Run the scraper and wait for it to complete
        result = subprocess.run(
            [sys.executable, "scrape_brand.py", brand_name],
            capture_output=False,  # Show output in real-time
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n✓ {brand_name} completed successfully in {elapsed/60:.1f} minutes")
            return True
        else:
            print(f"\n✗ {brand_name} failed with exit code {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print(f"\n\n⚠ Interrupted by user during {brand_name}")
        raise
    except Exception as e:
        print(f"\n✗ Error running {brand_name}: {e}")
        return False

def main():
    print("=" * 70)
    print("SEQUENTIAL SMALL BRANDS SCRAPER")
    print("=" * 70)
    print(f"Total brands to scrape: {len(SMALL_BRANDS)}")
    print(f"Brands with < 50 manuals each")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    stats = {
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    failed_brands = []
    start_time = time.time()
    
    try:
        for i, brand in enumerate(SMALL_BRANDS, 1):
            success = run_brand(brand, i, len(SMALL_BRANDS))
            
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
                failed_brands.append(brand)
            
            # Brief pause between brands
            if i < len(SMALL_BRANDS):
                print(f"\nWaiting 3 seconds before next brand...")
                time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("⚠ INTERRUPTED BY USER")
        print("=" * 70)
        stats["skipped"] = len(SMALL_BRANDS) - stats["success"] - stats["failed"]
    
    # Final summary
    total_time = time.time() - start_time
    print("\n\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total time: {total_time/3600:.2f} hours ({total_time/60:.1f} minutes)")
    print(f"Successful: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed_brands:
        print("\nFailed brands:")
        for brand in failed_brands:
            print(f"  - {brand}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()



