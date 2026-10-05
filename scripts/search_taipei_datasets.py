import json

with open("scripts/taipei_full_catalog.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

print(f"Total datasets in catalog: {len(catalog)}")

keywords = [
    "使用分區",
    "8公尺",
    "道路寬度",
    "道路",
    "地段圖",
    "地段代碼",
    "地籍",
    "段籍",
    "門牌位置",
    "都市更新",
    "雙子星",
    "C1",
    "D1",
    "捷運局"
]

results = {kw: [] for kw in keywords}

for item in catalog:
    ds_id = item.get("資料集id", "")
    title = item.get("資料集名稱", "")
    desc = item.get("資料集描述", "")
    org = item.get("資料集提供機關", "")
    url = item.get("資料存取網址", "")
    fmt = item.get("檔案格式", "")
    fields = item.get("主要欄位說明", "")
    
    full_str = f"{title} {desc} {fields}"
    for kw in keywords:
        if kw in full_str:
            results[kw].append({
                "id": ds_id,
                "title": title,
                "org": org,
                "format": fmt,
                "url": url,
                "fields": fields
            })

# Write findings to a clean JSON file
with open("scripts/taipei_catalog_matches.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Print summary
for kw, matches in results.items():
    print(f"\n=== Keyword '{kw}': {len(matches)} matches ===")
    for m in matches[:5]:
        print(f"  [{m['id']}] {m['title']} | {m['org']} | {m['format']}")
        if m['url']:
            print(f"    URL: {m['url'][:120]}")
