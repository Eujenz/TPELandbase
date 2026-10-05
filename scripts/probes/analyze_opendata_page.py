"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 分析 plvr.land.moi.gov.tw/DownloadOpenData 頁面中之歷史期別與下載表單
"""

import re

with open('scripts/probes/download_open_data_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

output = []

# Search for select inputs
for m in re.finditer(r'<select[^>]*name=["\']([^"\']+)["\'][^>]*>(.*?)</select>', text, re.DOTALL):
    s_name = m.group(1)
    output.append(f"Select name: {s_name}")
    options = re.findall(r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>(.*?)</option>', m.group(2))
    output.append(f"  Options count: {len(options)}")
    for val, label in options[:12]:
        output.append(f"    val: '{val}' -> label: '{label.strip()}'")

# Search for forms or AJAX / href calls
urls = re.findall(r'href=["\']([^"\']+)["\']', text)
output.append("\nHrefs in page:")
for u in set(urls):
    if any(k in u.lower() for k in ['download', 'zip', 'csv', 'season', 'history', 'api']):
        output.append(f"  {u}")

# Search for buttons and onclicks
onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', text)
output.append("\nOnclick handlers:")
for oc in list(set(onclicks))[:10]:
    output.append(f"  {oc}")

# Look for JavaScript functions
funcs = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*\{', text)
output.append("\nFunctions:")
for fn, args in funcs:
    output.append(f"  {fn}({args})")

with open('scripts/probes/page_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(output))

print("Saved analysis to scripts/probes/page_analysis.txt")
