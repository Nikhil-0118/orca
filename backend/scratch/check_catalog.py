import urllib.request
import re
import ssl
import json

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

s_url = 'https://www.mosdac.gov.in/catalog-app/main-57C767YM.js'
req_s = urllib.request.Request(s_url, headers={'User-Agent': 'Mozilla/5.0'})
js = urllib.request.urlopen(req_s, context=ssl_ctx, timeout=15).read().decode('utf-8', errors='ignore')

# Find URLs or endpoints
endpoints = re.findall(r'https?://[^\s"\'<>]+', js)
print('Endpoints with mosdac:', set(e for e in endpoints if 'mosdac' in e))
api_paths = re.findall(r'["\'](/[a-zA-Z0-9_./-]*api[a-zA-Z0-9_./-]*)["\']', js)
print('API paths:', set(api_paths))

# Search for EOS-06 or OCM
ocm_matches = re.findall(r'E06[A-Za-z0-9_]+', js)
print('E06 matches:', set(ocm_matches))

# Look for json endpoints or dataset lists
json_endpoints = re.findall(r'["\']([a-zA-Z0-9_./-]+\.json)["\']', js)
print('JSON endpoints:', set(json_endpoints))
