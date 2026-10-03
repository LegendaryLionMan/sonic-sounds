"""scripts/csp-builder - generate Content-Security-Policy for the site.

Per 2026-09-06 user feedback: the security suite (suite 3) checks
that the daemon sets security headers, but it doesn't help the
STATIC FILES (CSS, JS, HTML) have proper CSP meta tags. Inline
scripts, eval, and external font loads all need policy directives.

Usage:
    python scripts/csp-builder.py --inject        # write CSP meta tags
    python scripts/csp-builder.py --report       # show what would be set

Outputs the recommended CSP for a static frontend with:
- Inline scripts (for the IIFE modules)
- Google Fonts
- localhost API
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"

# Recommended CSP for the sonic-sounds static frontend.
# - script-src 'self' 'unsafe-inline': the IIFE modules use inline
#   scripts for state, and we don't want to nonce every one.
# - style-src 'self' 'unsafe-inline' https://fonts.googleapis.com:
#   some inline style="..." attrs in templates.
# - img-src 'self' data: blob: https://*.googleusercontent.com:
#   covers inline data URIs, blob URLs (cover fallback), and Google
#   user-content (for future OAuth avatars).
# - font-src 'self' https://fonts.gstatic.com: Google Fonts CDN.
# - connect-src 'self' ws://localhost:* http://127.0.0.1:*:
#   local daemon API and any future WebSocket.
# - frame-ancestors 'none': never allow our pages to be iframed.

CSP_DIRECTIVES = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: blob:",
    "font-src 'self' https://fonts.gstatic.com",
    "media-src 'self' blob:",
    "connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
]


def main() -> int:
    p = argparse.ArgumentParser(description="generate CSP")
    p.add_argument("--inject", action="store_true",
                   help="inject CSP meta tag into all site/*.html")
    p.add_argument("--report", action="store_true",
                   help="print the proposed CSP without injecting")
    args = p.parse_args()

    csp = "; ".join(CSP_DIRECTIVES)
    meta_tag = f'<meta http-equiv="Content-Security-Policy" content="{csp}">'

    if args.report or not args.inject:
        print(f"[csp] proposed policy:\n  {csp}\n")
    if args.report:
        return 0

    if args.inject:
        count = 0
        for f in SITE_DIR.glob("*.html"):
            content = f.read_text(encoding="utf-8")
            if "Content-Security-Policy" in content:
                continue  # already injected
            # Inject after <meta charset> line
            content = re.sub(
                r'(<meta\s+charset="utf-8"[^>]*>)',
                r'\1\n' + meta_tag,
                content,
                count=1,
            )
            f.write_text(content, encoding="utf-8")
            count += 1
        print(f"[csp] injected into {count} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
