import json
import re
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_dataset_page(ds_id):
    url = f"https://data.taipei/dataset/detail?id={ds_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15, context=ctx).read().decode("utf-8", errors="replace")
    
    # Extract title
    title_m = re.search(r'<title>(.*?)</title>', html)
    title = title_m.group(1).replace("臺北市資料大平臺 ｜ ", "").strip() if title_m else ""
    
    # Extract resource download links
    rids = re.findall(r'rid=([a-f0-9\-]+)', html)
    rids = list(dict.fromkeys(rids))
    
    # Extract resources info from nuxt or text
    # Look for format, name, description, etc.
    return {
        "dataset_id": ds_id,
        "title": title,
        "url": url,
        "rids": rids,
        "download_urls": [f"https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid={rid}" for rid in rids]
    }

if __name__ == "__main__":
    datasets = [
        ("3bab0a01-7936-4218-8cb5-f74dfcb43dda", "Taipei Zoning (臺北市都市計畫使用分區圖)"),
        ("ee2e4015-8844-48fb-aa57-31209909b0fc", "Taipei Roads > 8m (臺北市寬度超過8公尺道路GIS圖資)"),
        ("4f3d2280-1ebc-4bba-8ebf-66953403732b", "Taipei Cadastral Sections (臺北市數值地籍地段圖)")
    ]
    
    for ds_id, label in datasets:
        info = fetch_dataset_page(ds_id)
        print(f"\n=== {label} ===")
        print(f"Dataset ID: {info['dataset_id']}")
        print(f"Title: {info['title']}")
        print(f"RIDs: {info['rids']}")
        for dl in info['download_urls']:
            print(f"  Download: {dl}")
