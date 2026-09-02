"""e2e/test_browser_drive.py — browser-driven E2E verification of album-studio UI.

This test drives a real Chrome browser (via the browser-use harness
running locally on 127.0.0.1:9222) against a live album-studio daemon.
It exercises EVERY interactive element on /site/albums.html and
/site/studio.html, including:

  - Static element render checks (topbar, status pill, hero, grids, footer)
  - Modal flow: open → fill → submit → close
  - Drawer flow: click album card → drawer opens with full meta
  - Drawer → open-session → drawer closes
  - Studio deep link via ?session=<id>
  - Static studio elements (sidebar, pipeline, tracks, assets, events, decisions lists)
  - Derived state from API: layer/phase from build events, status from session
  - Lifecycle: pause → resume → complete with state-aware button disable
  - Track duration rendering (the duration_sec vs duration_ms bug check)
  - Session picker dropdown shows human album title

Requires:
  - Daemon running on http://127.0.0.1:8792 (default; change BASE)
  - Chrome with remote debugging enabled on 127.0.0.1:9222
    (one-time: chrome://inspect/#remote-debugging → Allow)

This script depends on the browser-use harness helpers (new_tab, js,
etc.) being in scope when it runs. Paste into a `browser_exec` call,
or modify for playwright if you prefer.

The companion test_ui_full_ux.py runs WITHOUT a browser and covers
the API + UX state-machine layer. Together they form a 5-layer test
pyramid:
  L1 (this):   full UX in real Chrome
  L2:          JS-driven rendering contract
  L3:          HTTP API contract (pytest tests/test_handlers_*)
  L4:          db layer (pytest tests/test_*.py)
  L5:          pure unit
"""
import sys
import time
import urllib.error
import urllib.request
import json

BASE = "http://127.0.0.1:8792"


def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# === Result tracking ===
results = []


def check(name, condition, detail=""):
    marks = "✅" if condition else "❌"
    results.append((name, bool(condition), detail))
    print(f"  {marks} {name}" + (f"  ({detail})" if detail and not condition else ""))


def section(title):
    print(f"\n{title}")


# ============================================================
# ALBUMS PAGE
# ============================================================
section("[1] Albums page — element render check")
new_tab(f"{BASE}/site/albums.html")
time.sleep(3)

for sel, what in [
    ("nav.topbar", "topbar"),
    ("#status-pill", "status pill"),
    ("#new-album-btn", "new album button"),
    ("header.hero h1", "hero h1"),
    ("#stat-active", "active stat"),
    ("#stat-albums", "albums stat"),
    ("#stat-done", "done stat"),
    ("#session-grid", "session grid"),
    ("#album-grid", "album grid"),
    ("footer.footer", "footer"),
    ("#new-album-modal", "modal container"),
    ("#album-drawer", "drawer container"),
]:
    check(f"albums: {what}", js(f"document.querySelector('{sel}') !== null"))

check("modal initially hidden", js("document.querySelector('#new-album-modal').hidden === true"))
check("drawer initially hidden", js("document.querySelector('#album-drawer').hidden === true"))


# ============================================================
# MODAL FLOW
# ============================================================
section("[2] Modal: open + fill + submit")
js("document.querySelector('#new-album-btn').click()")
time.sleep(1)
check("modal opens", js("document.querySelector('#new-album-modal').hidden === false"))

for sel, name in [("input[name=id]", "id"), ("input[name=title]", "title"),
                   ("input[name=primary_artist_id]", "artist"),
                   ("input[name=release_date]", "date"),
                   ("input[name=runtime_min]", "runtime")]:
    check(f"modal field: {name}", js(f"document.querySelector('{sel}') !== null"))

# Default value check
default_artist = js("document.querySelector('input[name=primary_artist_id]').value")
check("default artist = 'maren-sol'", default_artist == "maren-sol", f"got {default_artist!r}")

# Fill + submit
js("document.querySelector('input[name=id]').value = 'e2e-browser-test'")
js("document.querySelector('input[name=title]').value = 'E2E Browser Test'")
js("document.querySelector('#new-album-form').dispatchEvent(new Event('submit'))")
time.sleep(2)
check("modal closes after submit", js("document.querySelector('#new-album-modal').hidden === true"))

titles = js("Array.from(document.querySelectorAll('.album-card .album-title')).map(e => e.textContent)")
check("new album appears in grid", "E2E Browser Test" in titles, f"got {titles}")
album_count = js("document.querySelectorAll('.album-card').length")
check("album count >= 2 (seeded + new)", album_count >= 2, f"got {album_count}")


# ============================================================
# DRAWER FLOW
# ============================================================
section("[3] Drawer: click album → meta → open session")
js("Array.from(document.querySelectorAll('.album-card')).find(c => c.dataset.id === 'e2e-browser-test').click()")
time.sleep(1)
check("drawer opens", js("document.querySelector('#album-drawer').hidden === false"))
check("drawer title",
      js("document.querySelector('#drawer-album-title').textContent") == "E2E Browser Test")
check("drawer has >=4 meta items",
      js("document.querySelectorAll('#drawer-meta .meta-item').length") >= 4)

# Inspect drawer meta
meta = js("Array.from(document.querySelectorAll('#drawer-meta .meta-item')).map(m => m.querySelector('.mk').textContent + ': ' + m.querySelector('.mv').textContent)")
for m in meta:
    print(f"    {m}")

# Click open session
js("document.querySelector('#drawer-open-session-btn').click()")
time.sleep(2)
check("drawer closes after open-session",
      js("document.querySelector('#album-drawer').hidden === true"))

# Verify session via API
_, sessions = api("GET", "/api/sessions")
e2e_sessions = [s for s in (sessions or []) if s.get("album_id") == "e2e-browser-test"]
sid = e2e_sessions[0]["id"] if e2e_sessions else None
check("session created via drawer", sid is not None)
print(f"  → sid: {sid}")


# ============================================================
# SEED EVENTS + DECISIONS, NAVIGATE STUDIO
# ============================================================
section("[4] Seed events + decision")
api("POST", "/api/events", {"session_id": sid, "role": "user", "kind": "chat",
                             "content": "browser e2e chat", "album_id": "e2e-browser-test"})
api("POST", "/api/events", {"session_id": sid, "role": "assistant", "kind": "build",
                             "content": "build layer 3", "album_id": "e2e-browser-test",
                             "payload": {"layer": 3, "phase": "lyrics_finalize"}})
api("POST", "/api/decisions", {"code": "M01", "tier": "mandatory",
                                 "answer": "locked", "rationale": "browser e2e",
                                 "album_id": "e2e-browser-test", "session_id": sid})

# Navigate studio with deep link
new_tab(f"{BASE}/site/studio.html?session={sid}")
time.sleep(4)


# ============================================================
# STUDIO PAGE — STATIC ELEMENTS
# ============================================================
section("[5] Studio: element render")
for sel, what in [
    ("nav.topbar", "topbar"),
    ("#session-picker", "session picker"),
    ("#album-title", "title"),
    ("#album-artist", "artist"),
    ("#stat-layer", "layer stat"),
    ("#stat-phase", "phase stat"),
    ("#stat-runtime", "runtime stat"),
    ("#stat-idle", "idle stat"),
    ("#btn-pause", "pause button"),
    ("#btn-resume", "resume button"),
    ("#btn-complete", "complete button"),
    ("#back-btn", "back button"),
    ("#pipeline", "pipeline"),
    ("#track-list", "tracks section"),
    ("#asset-list", "assets section"),
    ("#event-list", "events section"),
    ("#decision-list", "decisions section"),
]:
    check(f"studio: {what}", js(f"document.querySelector('{sel}') !== null"))


# ============================================================
# STUDIO PAGE — DATA RENDERS
# ============================================================
section("[6] Studio: data renders correctly")
check("title = 'E2E Browser Test'",
      js("document.querySelector('#album-title').textContent") == "E2E Browser Test")
check("artist = 'maren-sol'",
      js("document.querySelector('#album-artist').textContent") == "maren-sol")
check("pipeline = 9 cells",
      js("document.querySelectorAll('.pipe-cell').length") == 9)
check("layer stat = '03' (derived from build event)",
      js("document.querySelector('#stat-layer').textContent") == "03")
active = js("Array.from(document.querySelectorAll('.pipe-cell.active')).map(c => c.querySelector('.pipe-cell-num').textContent)")
check("layer 03 active", "03" in active, f"active: {active}")
done = js("Array.from(document.querySelectorAll('.pipe-cell.done')).map(c => c.querySelector('.pipe-cell-num').textContent)")
check("layers 01, 02 done", all(x in done for x in ["01", "02"]), f"done: {done}")

# Newly-created albums have no tracks seeded — verify empty state
check("track-list shows empty state",
      js("document.querySelector('#track-list .empty-line') !== null"))

# Events + decisions render
check("event rows >= 2", js("document.querySelectorAll('.event-row').length") >= 2)
check("decision cards >= 1", js("document.querySelectorAll('.decision-card').length") >= 1)

# Session picker shows human album title (the slug bug check)
picker_text = js("document.querySelector('#session-picker').selectedOptions[0].textContent")
check("picker shows human title", "E2E Browser Test" in picker_text, f"got {picker_text!r}")
check("picker does NOT show slug", "e2e-browser-test" not in picker_text, f"got {picker_text!r}")

# Tier badge on decision card
tier = js("document.querySelector('.decision-card .d-tier').textContent")
check("decision tier badge = 'mandatory'", tier == "mandatory", f"got {tier!r}")


# ============================================================
# TRACK DURATION (the format bug check)
# ============================================================
section("[6b] Track duration rendering (on seeded album)")
# Open a session on the seeded album (which has 10 tracks)
_, sess_resp = api("POST", "/api/sessions", {"album_id": "half-light-hours"})
if isinstance(sess_resp, dict) and sess_resp.get("id"):
    seeded_sid = sess_resp["id"]
else:
    _, all_sess = api("GET", "/api/sessions")
    seeded_sid = next((s["id"] for s in all_sess if s.get("album_id") == "half-light-hours"), None)

if seeded_sid:
    new_tab(f"{BASE}/site/studio.html?session={seeded_sid}")
    time.sleep(3)
    track_rows = js("document.querySelectorAll('.track-row').length")
    check("track rows on seeded album = 10", track_rows == 10, f"got {track_rows}")
    sample_dur = js("document.querySelector('.track-row .t-meta').textContent")
    check("first track duration = '3:24'",
          sample_dur == "3:24", f"got {sample_dur!r}")
    track_title = js("document.querySelector('.track-row .t-title').textContent")
    print(f"  → first track: {track_title!r} {sample_dur!r}")
    all_meta = js("Array.from(document.querySelectorAll('.track-row .t-meta')).map(e => e.textContent)")
    check("all 10 track durations in m:ss format",
          all(":" in m for m in all_meta), f"got {all_meta}")
else:
    check("track duration format", False, "no seeded album session available")


# ============================================================
# STUDIO — LIFECYCLE STATE MACHINE
# ============================================================
section("[7] Lifecycle state machine")
new_tab(f"{BASE}/site/studio.html?session={sid}")
time.sleep(3)

check("status pill = 'active' initially",
      js("document.querySelector('#status-text').textContent") == "active")
check("pause enabled", not js("document.querySelector('#btn-pause').disabled"))
check("resume disabled (not paused)", js("document.querySelector('#btn-resume').disabled"))
check("complete enabled", not js("document.querySelector('#btn-complete').disabled"))

js("document.querySelector('#btn-pause').click()")
time.sleep(2)
check("status = 'paused' after click",
      js("document.querySelector('#status-text').textContent") == "paused")
check("pause disabled when paused", js("document.querySelector('#btn-pause').disabled"))
check("resume enabled when paused", not js("document.querySelector('#btn-resume').disabled"))

js("document.querySelector('#btn-resume').click()")
time.sleep(2)
check("status = 'active' after resume",
      js("document.querySelector('#status-text').textContent") == "active")

js("document.querySelector('#btn-complete').click()")
time.sleep(2)
check("status = 'done' after complete",
      js("document.querySelector('#status-text').textContent") == "done")
check("all 3 lifecycle buttons disabled after done",
      js("document.querySelector('#btn-pause').disabled") and
      js("document.querySelector('#btn-resume').disabled") and
      js("document.querySelector('#btn-complete').disabled"))

# API confirmation
_, sess_after = api("GET", f"/api/sessions/{sid}")
check("API confirms status=done", sess_after.get("status") == "done")


# ============================================================
# SUMMARY
# ============================================================
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n{'=' * 64}")
print(f"BROWSER E2E TOTAL: {passed}/{total} passed")
print(f"{'=' * 64}")
failed = [(n, d) for n, ok, d in results if not ok]
if failed:
    print("\nFAILURES:")
    for n, d in failed:
        print(f"  ❌ {n} — {d}")
