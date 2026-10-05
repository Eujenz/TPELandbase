import re
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://data.taipei/dataset/detail?id=3bab0a01-7936-4218-8cb5-f74dfcb43dda'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode('utf-8')

with open('scripts/taipei_detail_sample.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Saved taipei_detail_sample.html, len:', len(html))
