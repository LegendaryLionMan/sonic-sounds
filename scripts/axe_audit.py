"""scripts/axe-audit - run axe-core accessibility checks against the live site.

Per 2026-09-06 user feedback (full visual inspection): the current
visual_inspect.py found 21 input_no_label issues and other a11y
problems. This script runs axe-core (the de-facto a11y standard) via
Playwright to give deeper a11y feedback than our basic checks.

Requirements:
    pip install axe-core-python playwright
    # Or include axe-core as a static JS file in your test

Usage:
    python scripts/axe-audit.py                     # audit all pages
    python scripts/axe-audit.py --page intake.html
    python scripts/axe-audit.py --page library.html --json

Output: a summary of violations grouped by impact (critical/serious/
moderate/minor), plus the raw issue data for triage.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALL_PAGES = ["albums.html", "studio.html", "intake.html", "library.html",
             "dashboard.html", "album.html", "index.html"]
AXE_SOURCE = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"


def run_audit(base: str, pages: list[str]) -> dict:
    """Run axe-core against each page. Returns aggregated violations."""
    from playwright.sync_api import sync_playwright
    results = {"pages": {}, "summary": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        page = browser.contexts[0].pages[0]
        for path in pages:
            page.goto(f"{base}/site/{path}?v=axe",
                      wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            # Inject axe-core
            page.add_script_tag(url=AXE_SOURCE)
            page.wait_for_function("typeof window.axe !== 'undefined'", timeout=10000)
            # Run axe
            raw = page.evaluate("""
                () => window.axe.run(document, {
                    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'best-practice'] }
                }).then(r => JSON.stringify(r.violations))
            """)
            try:
                violations = json.loads(raw) if raw else []
            except Exception as e:
                violations = [{"id": "axe_load_failed", "impact": "critical",
                              "description": f"axe-core failed: {e}",
                              "nodes": []}]
            summary = {
                "critical": sum(1 for v in violations if v.get("impact") == "critical"),
                "serious": sum(1 for v in violations if v.get("impact") == "serious"),
                "moderate": sum(1 for v in violations if v.get("impact") == "moderate"),
                "minor": sum(1 for v in violations if v.get("impact") == "minor"),
                "total": len(violations),
                "violations": [
                    {
                        "id": v.get("id"),
                        "impact": v.get("impact"),
                        "help": v.get("help"),
                        "helpUrl": v.get("helpUrl"),
                        "description": (v.get("description") or "")[:200],
                        "node_count": len(v.get("nodes", [])),
                    }
                    for v in violations
                ],
            }
            results["pages"][path] = summary
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in results["pages"].values():
        for k in counts:
            counts[k] += v.get(k, 0)
    results["summary"] = counts
    return results


def main() -> int:
    p = argparse.ArgumentParser(description="axe-core a11y audit")
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--page", action="append", help="specific page (repeatable)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    args = p.parse_args()
    pages = args.page or ALL_PAGES
    try:
        results = run_audit(args.base, pages)
    except Exception as e:
        print(f"audit failed: {e}")
        return 1
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    print("\n=== axe-core accessibility audit ===")
    s = results["summary"]
    print(f"  TOTAL: {sum(s.values())} violation(s) across {len(pages)} page(s)")
    print(f"  critical: {s['critical']}")
    print(f"  serious:  {s['serious']}")
    print(f"  moderate: {s['moderate']}")
    print(f"  minor:    {s['minor']}")
    for path, v in results["pages"].items():
        if v["total"] > 0:
            print(f"\n  {path}: {v['total']} violation(s)")
            for viol in v["violations"][:5]:
                print(f"    - [{viol['impact']}] {viol['id']}: {viol['description'][:80]}")
                print(f"      {viol['helpUrl']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
