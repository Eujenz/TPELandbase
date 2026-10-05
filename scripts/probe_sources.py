import hashlib
import json
import os
import ssl
import sys
import urllib.request
import zipfile
import io

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def probe_url(url, desc, max_bytes=4096):
    print(f"=== Probing: {desc} ===")
    print(f"URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
            status = resp.status
            headers = dict(resp.headers)
            content_type = headers.get("Content-Type", "")
            content_length = headers.get("Content-Length", "unknown")
            last_modified = headers.get("Last-Modified", "")
            data = resp.read()
            sha256 = hashlib.sha256(data).hexdigest()
            print(f"Status: {status}")
            print(f"Content-Type: {content_type}")
            print(f"Content-Length: {content_length} (Actual read: {len(data)})")
            print(f"Last-Modified: {last_modified}")
            print(f"SHA256: {sha256}")
            return {
                "status": status,
                "headers": headers,
                "data": data,
                "sha256": sha256
            }
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("Testing data sources...")
