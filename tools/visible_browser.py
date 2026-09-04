"""tools/visible_browser.py - drive the persistent visible Chrome via raw CDP.

Why raw CDP instead of Playwright:
  Playwright's connect_over_cdp drops the connection after every command and
  re-attaches with every call. With our persistent Chrome (launched via Servy
  or manually), the second Playwright command fails with "Connection closed
  while reading from the driver" — known issue with chromium CDP reuse.

  Raw websockets keep one persistent connection: click, eval, screenshot all
  work reliably.

The user's Chrome window must be running first. To launch it:
  "C:/Users/lion_/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe" ^
    --remote-debugging-port=9333 ^
    --user-data-dir="C:/Users/lion_/AppData/Local/hermes/profiles/chrome-sonic-sounds" ^
    --window-name=sonic-sounds-verify ^
    --window-size=1280,820 --window-position=200,150 ^
    "http://127.0.0.1:8765/site/library.html"

Usage:
  python tools/visible_browser.py status              # CDP up?
  python tools/visible_browser.py nav <url>           # navigate (auto screenshot)
  python tools/visible_browser.py click <selector>    # click + screenshot
  python tools/visible_browser.py eval <js-expr>      # eval JS, return value
  python tools/visible_browser.py shot <outfile>      # screenshot to file
  python tools/visible_browser.py menu <page-stem>    # show how to reach menu on <page>
"""
from __future__ import annotations
import sys
import os
import json
import asyncio
import base64
import urllib.request
from pathlib import Path

import websockets

CDP_HTTP = "http://127.0.0.1:9333"
SHOT_DIR = Path(r"C:\Users\lion_\AppData\Local\Temp\sonic-sounds-smoke")
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def cdp_up() -> bool:
    try:
        urllib.request.urlopen(CDP_HTTP + "/json/version", timeout=2)
        return True
    except Exception:
        return False


def get_page_ws() -> str | None:
    targets = json.loads(urllib.request.urlopen(CDP_HTTP + "/json", timeout=3).read())
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    return None


def _safe_stem(selector: str) -> str:
    """Make a filename-safe stem out of a CSS selector."""
    keep = []
    for ch in selector:
        if ch.isalnum() or ch in "_-":
            keep.append(ch)
        elif ch in "[]=\"'":
            continue
        else:
            keep.append("_")
    return "".join(keep)[:40] or "x"


async def _cdp_session(fn):
    """Run fn(ws, call) where call(method, params) returns the result dict."""
    page_ws = get_page_ws()
    if not page_ws:
        raise RuntimeError("no page target on CDP")
    async with websockets.connect(page_ws, max_size=64 * 1024 * 1024, ping_interval=None) as ws:
        msg_id = [0]

        async def call(method, params=None):
            msg_id[0] += 1
            await ws.send(json.dumps({"id": msg_id[0], "method": method, "params": params or {}}))
            while True:
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("id") == msg_id[0]:
                    return data

        await fn(ws, call)


def run(fn):
    asyncio.run(_cdp_session(fn))


def cmd_status():
    if not cdp_up():
        print("CDP DOWN — chrome not running on port 9333")
        sys.exit(2)
    targets = json.loads(urllib.request.urlopen(CDP_HTTP + "/json", timeout=3).read())
    print(f"CDP UP — {len(targets)} target(s):")
    for t in targets[:5]:
        print(f"  {t.get('type'):12s} {t.get('url', '')[:90]}")


def cmd_nav(url):
    async def go(ws, call):
        await call("Page.enable")
        r = await call("Page.navigate", {"url": url})
        # Wait for load
        await asyncio.sleep(1.0)
        # Snapshot
        title = (await call("Runtime.evaluate", {
            "expression": "document.title", "returnByValue": True
        }))["result"]["result"]["value"]
        out = SHOT_DIR / f"nav-{Path(url).stem or 'page'}.png"
        shot = await call("Page.captureScreenshot", {"format": "png"})
        (SHOT_DIR / out.name).write_bytes(base64.b64decode(shot["result"]["data"]))
        print(json.dumps({"url": url, "title": title, "shot": str(out)}, indent=2))

    run(go)


def cmd_click(selector):
    async def go(ws, call):
        # Resolve selector to make sure element exists
        exists = await call("Runtime.evaluate", {
            "expression": f"!!document.querySelector({json.dumps(selector)})",
            "returnByValue": True,
        })
        present = exists.get("result", {}).get("result", {}).get("value")
        if not present:
            print(f"SELECTOR NOT FOUND: {selector}")
            sys.exit(3)

        # Scroll into view
        await call("Runtime.evaluate", {
            "expression": f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}})",
            "returnByValue": True,
        })
        await asyncio.sleep(0.2)

        # State before
        before = await call("Runtime.evaluate", {
            "expression": "JSON.stringify({drawer: document.getElementById('album-drawer')?.hidden, url: location.href})",
            "returnByValue": True,
        })
        before_v = json.loads(before["result"]["result"]["value"])

        # Click via JS
        await call("Runtime.evaluate", {
            "expression": f"document.querySelector({json.dumps(selector)}).click()",
            "returnByValue": True,
        })
        await asyncio.sleep(0.5)

        # State after
        after = await call("Runtime.evaluate", {
            "expression": "JSON.stringify({drawer: document.getElementById('album-drawer')?.hidden, drawerTitle: document.getElementById('drawer-album-title')?.textContent, drawerAlbumId: document.getElementById('drawer-album-id')?.textContent})",
            "returnByValue": True,
        })
        after_v = json.loads(after["result"]["result"]["value"])

        out = SHOT_DIR / f"click-{_safe_stem(selector)}.png"
        shot = await call("Page.captureScreenshot", {"format": "png"})
        out.write_bytes(base64.b64decode(shot["result"]["data"]))

        print(json.dumps({
            "selector": selector,
            "shot": str(out),
            "before": before_v,
            "after": after_v,
        }, indent=2))

    run(go)


def cmd_eval(expr):
    async def go(ws, call):
        r = await call("Runtime.evaluate", {
            "expression": expr, "returnByValue": True,
        })
        result = r.get("result", {}).get("result", {}).get("value")
        if result is None:
            err = r.get("result", {}).get("exceptionDetails")
            print(f"ERROR: {json.dumps(err, indent=2)[:500]}")
        else:
            if isinstance(result, str):
                print(result)
            else:
                print(json.dumps(result, indent=2, default=str))

    run(go)


def cmd_shot(outfile):
    async def go(ws, call):
        shot = await call("Page.captureScreenshot", {"format": "png"})
        Path(outfile).write_bytes(base64.b64decode(shot["result"]["data"]))
        size = Path(outfile).stat().st_size
        print(f"saved {outfile} ({size:,} bytes)")

    run(go)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    try:
        if cmd == "status":
            cmd_status()
        elif cmd == "nav" and args:
            cmd_nav(args[0])
        elif cmd == "click" and args:
            cmd_click(args[0])
        elif cmd == "eval" and args:
            cmd_eval(args[0])
        elif cmd == "shot" and args:
            cmd_shot(args[0])
        else:
            print(__doc__)
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(4)
