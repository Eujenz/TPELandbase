import json
import os
import re
import ssl
import sys
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_page_info(ds_id, label):
    url = f"https://data.taipei/dataset/detail?id={ds_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            html = r.read().decode("utf-8", errors="replace")
            title_m = re.search(r"<title>(.*?)</title>", html)
            title = title_m.group(1).strip() if title_m else "Unknown"
            
            # Find all resource URLs or JSON state embedded in the page
            resource_urls = re.findall(r'https?://[^\s"\'<>]+', html)
            filtered_resources = []
            for u in set(resource_urls):
                u_lower = u.lower()
                if any(x in u_lower for x in [".zip", ".shp", ".geojson", ".kml", ".csv", "/resource/", "/download/", "scope=resourceaquire"]):
                    filtered_resources.append(u)
                    
            return {
                "dataset_id": ds_id,
                "label": label,
                "page_url": url,
                "title": title,
                "resources": filtered_resources
            }
    except Exception as e:
        return {"dataset_id": ds_id, "label": label, "error": str(e)}

if __name__ == "__main__":
    targets = [
        ("3bab0a01-7936-4218-8cb5-f74dfcb43dda", "Taipei Zoning"),
        ("ee2e4015-8844-48fb-aa57-31209909b0fc", "Taipei Roads > 8m"),
        ("4f3d2280-1ebc-4bba-8ebf-66953403732b", "Taipei Cadastral Sections (地籍地段圖)")
    ]
    results = [get_page_info(tid, lbl) for tid, lbl in targets]
    with open("scripts/data_taipei_details.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Inspected {len(results)} datasets from data.taipei.")
