import json
import os
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

catalog_file = "scripts/taipei_full_catalog.json"

if not os.path.exists(catalog_file):
    print("Downloading full Taipei dataset catalog...")
    url = "https://data.taipei/api/frontstage/tpeod/dataset.download?format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        raw = r.read()
        with open(catalog_file, "wb") as f:
            f.write(raw)
    print(f"Downloaded catalog: {len(raw)} bytes.")

with open(catalog_file, "r", encoding="utf-8") as f:
    catalog = json.load(f)

print(f"Total datasets in catalog: {len(catalog)}")

keywords = [
    "使用分區", "8公尺", "道路寬度", "道路", "地段圖", "地籍", "段籍", "都市更新", "雙子星", "C1", "D1", "捷運局"
]

matches = {kw: [] for kw in keywords}

for ds in catalog:
    title = ds.get("title", "")
    desc = ds.get("description", "")
    full_text = f"{title} {desc}"
    ds_id = ds.get("id")
    for kw in keywords:
        if kw in full_text:
            matches[kw].append({
                "id": ds_id,
                "title": title,
                "org": ds.get("organization", {}).get("title") if isinstance(ds.get("organization"), dict) else ds.get("organization")
            })

for kw, items in matches.items():
    print(f"\n=== Keyword: {kw} ({len(items)} matches) ===")
    for item in items[:6]:
        print(f"  [{item['id']}] {item['title']} ({item['org']})")

with open("scripts/matched_taipei_datasets.json", "w", encoding="utf-8") as f:
    json.dump(matches, f, ensure_ascii=False, indent=2)

print("\nSaved matches to scripts/matched_taipei_datasets.json")
