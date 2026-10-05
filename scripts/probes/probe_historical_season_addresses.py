"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 下載並探測 109S4 (實價登錄2.0前) 之歷史季度檔案，檢驗歷史檔案中的門牌遮蔽規則
"""

import urllib.request
import ssl
import zipfile
import io
import pandas as pd
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://plvr.land.moi.gov.tw/DownloadHistory?type=season&fileName=109S4"
print(f"Downloading historical season 109S4 from {url}...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
output = []

try:
    with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
        raw_zip = r.read()
        output.append(f"Downloaded 109S4 size: {len(raw_zip)} bytes")
        
        with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
            # Check Taipei main buy/sell
            filename = "a_lvr_land_a.csv"
            if filename in z.namelist():
                df = pd.read_csv(z.open(filename), encoding="utf-8", skiprows=[1], low_memory=False)
                output.append(f"Total 109S4 Taipei transactions: {len(df)}")
                
                # Check column name
                addr_col = "土地位置建物門牌" if "土地位置建物門牌" in df.columns else "土地區段位置建物區段門牌"
                output.append(f"Address column name: {addr_col}")
                
                addrs = df[addr_col].dropna().astype(str)
                ranges = addrs[addrs.str.contains(r'[０-９0-9]+[～~至\-][０-９0-9]+號')]
                exacts = addrs[~addrs.str.contains(r'[～~至\-]') & addrs.str.contains(r'[０-９0-9]+號')]
                output.append(f"NUMBER_RANGE count: {len(ranges)} ({len(ranges)/len(addrs)*100:.1f}%)")
                output.append(f"EXACT count: {len(exacts)} ({len(exacts)/len(addrs)*100:.1f}%)")
                
                output.append("\nSample NUMBER_RANGE from 109S4:")
                for s in ranges.head(10):
                    output.append(f"  {s}")
                    
                output.append("\nSample EXACT from 109S4:")
                for s in exacts.head(10):
                    output.append(f"  {s}")
except Exception as e:
    output.append(f"Error: {e}")

with open("scripts/probes/historical_109s4_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved report to scripts/probes/historical_109s4_report.txt")
