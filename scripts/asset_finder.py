"""scripts/asset-finder - audit which assets are reachable + sized.

Per 2026-09-06 user feedback (full visual inspection): the new-album
modal on albums.html and the asset gallery have intermittent 404s.
This script audits every asset referenced by the HTML pages and
verifies its HTTP status + size + content-type.

Usage:
    python scripts/asset-finder.py                # all pages
    python scripts/asset-finder.py --page albums  # one page
    python scripts/asset-finder.py --json          # JSON report
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]


class AssetHarvester(HTMLParser):
    """Pull every <link href>, <img src>, <script src> URL from an HTML page."""
    def __init__(self):
        super().__init__()
        self.urls: set[str] = set()
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src", "srcset", "poster"):
            v = d.get(attr)
            if v and not v.startswith("data:") and not v.startswith("#"):
                self.urls.add(v)


def find_assets(base: str, page_path: str) -> dict:
    """Fetch HTML, extract asset URLs, check each one."""
    html = urllib.request.urlopen(f"{base}/site/{page_path}", timeout=10).read().decode("utf-8", errors="replace")
    harvester = AssetHarvester()
    harvester.feed(html)
    findings = {}
    for url in harvester.urls:
        # Resolve relative URLs
        if url.startswith(("http://", "https://")):
            full = url
        elif url.startswith("/"):
            full = base + url
        else:
            full = f"{base}/site/{url}"
        try:
            req = urllib.request.Request(full, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as r:
                findings[url] = {
                    "status": r.status,
                    "size": int(r.headers.get("Content-Length", 0)),
                    "type": r.headers.get("Content-Type", ""),
                }
        except urllib.error.HTTPError as e:
            findings[url] = {"status": e.code, "size": 0, "type": "", "error": "HTTPError"}
        except Exception as e:
            findings[url] = {"status": 0, "size": 0, "type": "",
                             "error": type(e).__name__}
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description="asset finder")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--page", action="append")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    pages = args.page or ALL_PAGES
    full_report = {}
    for path in pages:
        results = find_assets(args.base, path)
        full_report[path] = results
        broken = [(u, r) for u, r in results.items()
                  if r.get("status", 0) >= 400 or r.get("status", 0) == 0]
        ok = [(u, r) for u, r in results.items()
              if r.get("status", 0) < 400 and r.get("status", 0) > 0]
        if args.json:
            continue
        print(f"\n=== {path} ({len(results)} assets) ===")
        print(f"  ok: {len(ok)}, broken: {len(broken)}")
        for u, r in broken[:5]:
            print(f"    BROKEN  {r.get('status', '?')}  {u}")

    if args.json:
        print(json.dumps(full_report, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
