import html
import json
import re

import httpx


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}

with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
    response = client.get("https://ihavecpu.com/category/cpu")
    print(response.status_code, response.url, len(response.text))
    match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', response.text, re.S)
    data = json.loads(html.unescape(match.group(1))) if match else {}
    products = data.get("props", {}).get("pageProps", {}).get("product", {}).get("data", [])
    links = re.findall(r'href=["\']([^"\']*/product/(\d+)/[^"\']+)["\']', response.text, re.I)
    print("products", len(products), "links", len(links))
    print(json.dumps(products[:2], ensure_ascii=False, indent=2))
    print(json.dumps(links[:10], ensure_ascii=False, indent=2))
    detail = client.get("https://ihavecpu.com/product/24243/x")
    detail_match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', detail.text, re.S)
    detail_data = json.loads(html.unescape(detail_match.group(1))) if detail_match else {}
    detail_props = detail_data.get("props", {}).get("pageProps", {})
    print("detail", detail.status_code, len(detail.text), list(detail_props))
    print(json.dumps(detail_props.get("product"), ensure_ascii=False, indent=2)[:25000])
