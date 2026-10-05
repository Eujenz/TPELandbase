"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 探查 MOI 歷季實價登錄下載管道 (plvr.land.moi.gov.tw 與 data.gov.tw 歷次發布)
"""

import urllib.request
import ssl
import json
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Inspect what DownloadSeason returned
url = "https://plvr.land.moi.gov.tw/DownloadSeason?season=113S2&type=lvr_landcsv.zip"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        content = r.read().decode("utf-8", errors="replace")
        print("=== DownloadSeason response ===")
        print(content)
except Exception as e:
    print("DownloadSeason error:", e)

# 2. Check DownloadOpenData page html to see the actual download form / parameters for historical seasons
url_page = "https://plvr.land.moi.gov.tw/DownloadOpenData"
req_page = urllib.request.Request(url_page, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req_page, timeout=15, context=ctx) as r:
        html = r.read().decode("utf-8", errors="replace")
        with open("scripts/probes/download_open_data_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\nSaved download_open_data_page.html, size:", len(html))
        
        # Search for season options or download URLs in html
        seasons = re.findall(r'value=[\"\'](\d+[S|s]\d+)[\"\']', html)
        print("Found seasons:", seasons[:15])
        
        forms = re.findall(r'<form[^>]*action=[\"\']([^\"\']+)[\"\'][^>]*>', html)
        print("Found form actions:", forms)
except Exception as e:
    print("DownloadOpenData page error:", e)
