import json
from collections import Counter

# Load the cache file
with open('manual_urls_cache.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count by brand
laptop_brands = Counter(item['brand'] for item in data.get('laptops', []))
desktop_brands = Counter(item['brand'] for item in data.get('desktops', []))

print('LAPTOPS BY BRAND:')
print('=' * 50)
for brand, count in sorted(laptop_brands.items(), key=lambda x: x[1], reverse=True):
    print(f'{brand:20s}: {count:>7,}')

print(f'\n{"TOTAL LAPTOPS":20s}: {sum(laptop_brands.values()):>7,}')

print('\n\nDESKTOPS BY BRAND:')
print('=' * 50)
for brand, count in sorted(desktop_brands.items(), key=lambda x: x[1], reverse=True):
    print(f'{brand:20s}: {count:>7,}')

print(f'\n{"TOTAL DESKTOPS":20s}: {sum(desktop_brands.values()):>7,}')

print('\n\nALL BRANDS COMBINED:')
print('=' * 50)
all_brands = Counter()
all_brands.update(laptop_brands)
all_brands.update(desktop_brands)
for brand, count in sorted(all_brands.items(), key=lambda x: x[1], reverse=True):
    print(f'{brand:20s}: {count:>7,}')

print(f'\n{"GRAND TOTAL":20s}: {sum(all_brands.values()):>7,}')

