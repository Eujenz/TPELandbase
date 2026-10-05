import re

with open('scripts/taipei_detail_sample.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("File length:", len(text))

# Check for API paths
apis = set(re.findall(r'(/api/[a-zA-Z0-9_\-\./]+)', text))
print("\nUnique API paths:")
for a in sorted(apis):
    print(" ", a)

# Check for resource URLs or data download
urls = set(re.findall(r'https?://[^\s"\'<>]+', text))
print("\nResource/Download URLs:")
for u in sorted(urls):
    if any(k in u.lower() for k in ['resource', 'download', 'blob', 'file', 'cdn', 'api']):
        print(" ", u)

# Check for inline script data
for m in re.finditer(r'<script id="([^"]+)"[^>]*>(.*?)</script>', text, re.DOTALL):
    print("Found script id:", m.group(1), "Length:", len(m.group(2)))

# Check for Nuxt / Next / Redux / Svelte state
for keyword in ['__NEXT_DATA__', '__NUXT__', '__INITIAL_STATE__', 'window.__']:
    if keyword in text:
        print("Found keyword:", keyword)
