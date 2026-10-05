import json
import ssl
import sys
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

keywords = [
    '都市計畫土地使用分區',
    '超過8公尺',
    '道路寬度',
    '數值地籍地段圖',
    '段籍圖',
    '都市更新',
    '雙子星',
    '捷運C1'
]

results_map = {}

for kw in keywords:
    try:
        url = f"https://data.taipei/api/v1/dataset/search?q={urllib.parse.quote(kw)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8'))
            items = data.get('result', {}).get('results', [])
            print(f"=== Keyword: {kw} (found {len(items)}) ===")
            for item in items[:4]:
                ds_id = item.get('id')
                title = item.get('title')
                org = item.get('organization', {}).get('title')
                print(f"  ID: {ds_id} | Title: {title} | Org: {org}")
                if ds_id not in results_map:
                    results_map[ds_id] = item
    except Exception as e:
        print(f"Error querying {kw}: {e}")

with open('scripts/taipei_search_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_map, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(results_map)} unique dataset details to scripts/taipei_search_results.json")
