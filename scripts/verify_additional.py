import hashlib
import json
import os
import ssl
import urllib.request
import zipfile
import geopandas as gpd

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Download Zoning Part 2
url_zoning2 = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=10196e7d-2460-4b8a-b1d2-84001d09d7a4"
print("Downloading Zoning Part 2...")
req = urllib.request.Request(url_zoning2, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
    data = r.read()
    with open("data/raw/probes/taipei_zoning_1019.zip", "wb") as f:
        f.write(data)
    print(f"Zoning Part 2 size: {len(data)}, sha256: {hashlib.sha256(data).hexdigest()}")

zf2 = zipfile.ZipFile("data/raw/probes/taipei_zoning_1019.zip")
print("Zoning Part 2 files:", zf2.namelist())

# 2. Test NLSC Open Cadastral WMS / WFS / API
# NLSC provides maps.nlsc.gov.tw
print("\nTesting NLSC cadastral services...")
nlsc_urls = [
    ("NLSC WMTS GetCapabilities", "https://wmts.nlsc.gov.tw/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"),
    ("NLSC Cadastral WMS (LAND)", "https://maps.nlsc.gov.tw/S_Maps/wms?SERVICE=WMS&REQUEST=GetCapabilities"),
    ("NLSC Open API (Parcel search)", "https://api.nlsc.gov.tw/other/TownVillagePointQuery/121.513/25.048/4326")
]

nlsc_results = {}
for name, u in nlsc_urls:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            body = r.read(1024)
            nlsc_results[name] = {
                "status": r.status,
                "type": r.headers.get("Content-Type"),
                "sample": body.decode("utf-8", errors="replace")[:200]
            }
            print(f"{name} -> Status: {r.status}, Content-Type: {r.headers.get('Content-Type')}")
    except Exception as e:
        print(f"{name} -> Error: {e}")
        nlsc_results[name] = {"error": str(e)}

# 3. Test TGOS Geocoding API
print("\nTesting TGOS API...")
tgos_key = os.environ.get("TGOS_APP_ID") or os.environ.get("TGOS_KEY")
print(f"TGOS Key in env: {'Found' if tgos_key else 'None'}")

# 4. Check C1/D1 Official Geometry / Anchor Point
# C1/D1: Taipei Main Station Special Zone C1/D1 (臺北車站特定專用區 C1/D1 基地)
# Let's inspect known land parcels and cadastral / planning info
# C1: 臺北市中正區公園段一小段 or 臺北市大同區河溝頭段?
# Let's check sections in Taipei around Taipei Main Station
