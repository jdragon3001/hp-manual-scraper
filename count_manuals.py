#!/usr/bin/env python3
"""Count manual files per brand."""

from pathlib import Path
import json

def count_manuals_by_brand():
    """Count the number of manual files in each brand folder."""
    base_path = Path("downloads/laptops")
    
    if not base_path.exists():
        print(f"Error: {base_path} does not exist")
        return {}
    
    brand_counts = {}
    
    # Get all brand directories
    for brand_dir in sorted(base_path.iterdir()):
        if brand_dir.is_dir():
            # Count all .txt files in this brand directory
            txt_files = list(brand_dir.rglob("*.txt"))
            brand_counts[brand_dir.name] = len(txt_files)
    
    return brand_counts

if __name__ == "__main__":
    counts = count_manuals_by_brand()
    
    # Print results
    print("\n=== Manual Count by Brand ===\n")
    total = 0
    for brand, count in counts.items():
        print(f"{brand:20s}: {count:3d} manuals")
        total += count
    
    print(f"\n{'TOTAL':20s}: {total:3d} manuals")
    
    # Save to markdown file
    with open("manual_counts.md", "w", encoding="utf-8") as f:
        f.write("# Manual Count by Brand\n\n")
        f.write("*Generated on December 8, 2025*\n\n")
        f.write("| Brand | Count |\n")
        f.write("|-------|-------|\n")
        
        for brand, count in counts.items():
            f.write(f"| {brand} | {count} |\n")
        
        f.write(f"| **TOTAL** | **{total}** |\n")
        
        f.write("\n## Details\n\n")
        f.write(f"- Total brands: {len(counts)}\n")
        f.write(f"- Total manuals: {total}\n")
        f.write(f"- Average manuals per brand: {total/len(counts):.1f}\n")
    
    print("\n✓ Results saved to manual_counts.md")





