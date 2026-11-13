"""Check each address in urls.csv once: status, final address, page title, access.

Writes .work/checked.json. Addresses already checked are skipped unless --recheck.
Reads at most 400 KB of each page and keeps only its title: no article text is stored.
"""

import csv
import html
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).parent
WORK = HERE / ".work"
OUT = WORK / "checked.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 url-check"

SIGNIN_HOSTS = {"x.com", "twitter.com", "linkedin.com", "reddit.com", "tiktok.com", "instagram.com", "facebook.com", "threads.net", "threads.com"}
PAYWALL_HOSTS = {"nytimes.com", "ft.com", "wsj.com", "economist.com", "nejm.org", "thelancet.com"}
LANG_BY_TLD = {".de": "de", ".jp": "ja", ".ar": "es", ".cl": "es", ".fr": "fr", ".es": "es", ".it": "it"}


def bare_host(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.8"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(400_000).decode("utf-8", "replace")
            status, final = response.status, response.geturl()
    except urllib.error.HTTPError as error:
        return {"status": error.code, "final": url, "title": "", "lang": "", "paywall": False}
    except (OSError, ValueError) as error:  # timeout, DNS, TLS, malformed address
        return {"status": f"error: {type(error).__name__}", "final": url, "title": "", "lang": "", "paywall": False}
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.DOTALL | re.IGNORECASE)
    lang = re.search(r"<html[^>]*\blang=[\"']?([a-zA-Z-]+)", body)
    squashed = body.replace(" ", "")
    return {
        "status": status,
        "final": final,
        "title": html.unescape(re.sub(r"\s+", " ", title.group(1)).strip())[:140] if title else "",
        "lang": lang.group(1).lower()[:2] if lang else "",
        "paywall": '"isAccessibleForFree":false' in squashed or '"isAccessibleForFree":"False"' in squashed,
    }


def describe(url, found, expected):
    host = bare_host(url)
    status = found["status"]
    if any(host == h or host.endswith("." + h) for h in SIGNIN_HOSTS):
        access = "sign-in wall likely"
    elif found["paywall"] or host in PAYWALL_HOSTS or "paywall" in expected:
        access = "paywall"
    elif status in (401, 403, 429):
        access = "blocks bots"
    elif not isinstance(status, int) or status >= 400:
        access = "unreachable"
    else:
        access = "open"
    lang = found["lang"] or next((v for k, v in LANG_BY_TLD.items() if host.endswith(k)), "en")
    redirect = found["final"] if found["final"].rstrip("/") != url.rstrip("/") else ""
    return {"http_status": status, "access": access, "language": lang, "redirects_to": redirect,
            "page_title": found["title"], "link_checked": datetime.now(UTC).date().isoformat()}


def main():
    WORK.mkdir(exist_ok=True)
    recheck = "--recheck" in sys.argv
    rows = list(csv.DictReader((HERE / "urls.csv").open()))
    checked = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [r for r in rows if recheck or r["url"] not in checked]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for row, found in zip(todo, pool.map(lambda r: fetch(r["url"]), todo)):
            checked[row["url"]] = describe(row["url"], found, row["expected_answer"])
    OUT.write_text(json.dumps(checked, indent=1, ensure_ascii=False))
    print(f"checked {len(todo)} address(es); {len(checked)} on record")


main()
