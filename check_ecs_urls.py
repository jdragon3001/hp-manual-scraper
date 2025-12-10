import json

with open('manual_urls_cache.json') as f:
    data = json.load(f)

ecs_manuals = []
for category, manuals in data.items():
    for m in manuals:
        if m['brand'].upper() == 'ECS':
            ecs_manuals.append(m)

print(f"Total ECS manuals: {len(ecs_manuals)}\n")
print("First 10 ECS manuals:")
for m in ecs_manuals[:10]:
    print(f"  {m['model']}: {m['url']}")

