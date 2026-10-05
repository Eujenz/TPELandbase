import hashlib
import io
import json
import os
import ssl
import sys
import urllib.request
import zipfile
import geopandas as gpd

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_download(url, output_path, desc):
    print(f"\n==========================================")
    print(f"Testing: {desc}")
    print(f"URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=40, context=ctx) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            content_length = resp.headers.get("Content-Length", "")
            last_modified = resp.headers.get("Last-Modified", "")
            data = resp.read()
            sha256 = hashlib.sha256(data).hexdigest()
            print(f"HTTP Status: {status}")
            print(f"Content-Type: {content_type}")
            print(f"Content-Length: {len(data)} bytes")
            print(f"Last-Modified: {last_modified}")
            print(f"SHA256: {sha256}")
            
            with open(output_path, "wb") as f:
                f.write(data)
                
            return {
                "success": True,
                "status": status,
                "content_type": content_type,
                "length": len(data),
                "last_modified": last_modified,
                "sha256": sha256
            }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"success": False, "error": str(e)}

os.makedirs("data/raw/probes", exist_ok=True)

# 1. MOI LVR Land CSV
test_download(
    "https://plvr.land.moi.gov.tw/Download?type=zip&fileName=lvr_landcsv.zip",
    "data/raw/probes/lvr_landcsv.zip",
    "MOI LVR Land Batch (Current)"
)

# 2. Taipei Roads > 8m
test_download(
    "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=074a401d-45a2-4748-bf62-7d5372d53d45",
    "data/raw/probes/taipei_roads_8m.zip",
    "Taipei Roads > 8m (SHP ZIP)"
)

# 3. Taipei Cadastral Sections (數值地籍地段圖)
test_download(
    "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=86430589-4e8b-4e21-9d5f-08b0e5c2ce3f",
    "data/raw/probes/taipei_cadastral_sections.zip",
    "Taipei Cadastral Sections (SHP ZIP)"
)

# 4. Taipei Zoning
test_download(
    "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=0cb6e68a-87c1-4846-b766-bcde3ebe179c",
    "data/raw/probes/taipei_zoning_0cb6.zip",
    "Taipei Zoning Part 1 (SHP ZIP)"
)

# 5. Taipei Doorplate Locations (門牌位置數值資料)
test_download(
    "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=ce76ca0c-7f94-4935-ab47-1d2a41ca2abb",
    "data/raw/probes/taipei_doorplate.csv",
    "Taipei Doorplate Locations CSV"
)
