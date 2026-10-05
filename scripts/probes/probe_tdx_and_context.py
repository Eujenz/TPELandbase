"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 檢測 TDX 憑證狀態、官方交通圖資來源 (捷運站出入口、公車站、臺鐵/高鐵) 與 NLSC 官方底圖
"""

import os
import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

output = []

# 1. Check TDX Credentials
tdx_id = os.environ.get("TDX_CLIENT_ID")
tdx_secret = os.environ.get("TDX_CLIENT_SECRET")

output.append("=== 1. TDX Credentials Check ===")
if tdx_id and tdx_secret:
    output.append("TDX credentials FOUND in environment variables.")
    # Test token acquisition
    token_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    data = f"grant_type=client_credentials&client_id={tdx_id}&client_secret={tdx_secret}".encode("utf-8")
    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            token_json = json.loads(r.read().decode("utf-8"))
            output.append(f"TDX Auth SUCCESS! Status: {r.status}, Token received.")
    except Exception as e:
        output.append(f"TDX Auth ERROR: {e}")
else:
    output.append("TDX credentials NOT found in environment. Marking TDX as UNVERIFIED.")

# 2. Check data.taipei MRT Exits dataset
output.append("\n=== 2. data.taipei MRT Stations / Exits ===")
# Search data.taipei catalog for MRT exits
mrt_ds_id = "64dda883-fa49-4322-a9b0-bb96e1a49ec3" # Known MRT exits ID on data.taipei
url_mrt = f"https://data.taipei/dataset/detail?id={mrt_ds_id}"
try:
    req = urllib.request.Request(url_mrt, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        output.append(f"MRT Exits Dataset Page accessible. Status: {r.status}")
except Exception as e:
    output.append(f"MRT Exits page check note: {e}")

# 3. Check NLSC WMTS capabilities
output.append("\n=== 3. NLSC Official Basemap Check ===")
emap_url = "https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/15/14493/27655" # Sample tile
try:
    req = urllib.request.Request(emap_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        output.append(f"NLSC EMAP WMTS tile fetch SUCCESS! Status: {r.status}, Content-Type: {r.headers.get('Content-Type')}")
except Exception as e:
    output.append(f"NLSC EMAP WMTS tile fetch note: {e}")

with open("scripts/probes/tdx_context_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved report to scripts/probes/tdx_context_report.txt")
