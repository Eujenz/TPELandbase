import re

with open('scripts/listdownload.html', 'r', encoding='utf-8') as f:
    text = f.read()

urls = set(re.findall(r'https?://[^\s"\'<>]+', text))
print("Found URLs in listdownload:")
for u in sorted(urls):
    if any(k in u.lower() for k in ['.csv', '.json', 'download', 'resource', 'dataset', 'catalog']):
        print(" ", u)
