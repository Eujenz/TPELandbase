"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 解析 DownloadSeason_ajax_list 中的選項與測試實際歷史季度下載
"""

import re
import urllib.request
import ssl
import hashlib

with open('scripts/probes/download_season_ajax_list.html', 'r', encoding='utf-8') as f:
    text = f.read()

options = re.findall(r'<option[^>]*value=["\']([^"\']+)["\'][^>]*>(.*?)</option>', text)
print(f"Total season options found: {len(options)}")
for val, lbl in options[:12]:
    print(f"  Val: '{val}' -> Label: '{lbl.strip()}'")

# Test downloading a historical season: 112S4 or 113S1
if options:
    test_val = options[1][0] if len(options) > 1 else options[0][0]
    test_url = f"https://plvr.land.moi.gov.tw/DownloadHistory?type=season&fileName={test_val}"
    print(f"\nTesting historical season download URL: {test_url}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            data = r.read(1024 * 1024) # read first 1MB
            print(f"Status: {r.status}")
            print(f"Content-Type: {r.headers.get('Content-Type')}")
            print(f"Read bytes: {len(data)}, Content-Length: {r.headers.get('Content-Length')}")
            print(f"First 100 bytes: {data[:100]}")
    except Exception as e:
        print("Download error:", e)
