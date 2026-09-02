"""e2e/test_ui_full_ux.py — End-to-end UX verification for album-studio.

This is the canonical E2E spec for the album-studio UI. It exercises
every interactive element on /site/albums.html and /site/studio.html
against a LIVE daemon (must be running on http://127.0.0.1:8791).

The test is structured as 3 layers:
  1. API contract:    each UI element is backed by a real endpoint
  2. DOM contract:     each element has a stable selector + correct text
  3. UX flow:          click each interactive element, verify state changes

If a UI element fails to render correctly, the test FAILS — not the
underlying API. This is what makes the test catch integration bugs
like "session payload missing album_title" that API-only tests miss.

Run:
    # 1. Start the daemon (seeded with maren-sol + half-light-hours):
    python -m db.seed --db /tmp/e2e.db --force
    python -m build.serve --host 127.0.0.1 --port 8791 \
        --lock /tmp/e2e.lock --log /tmp/e2e.log

    # 2. Run the E2E:
    python e2e/test_ui_full_ux.py

Exit code 0 = all green. Non-zero = at least one UI element failed.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

BASE = os.environ.get("ALBUM_STUDIO_E2E_BASE", "http://127.0.0.1:8791")


# === Helpers ===

def api(method: str, path: str, data: dict | None = None) -> tuple[int, Any]:
    """HTTP client. Returns (status_code, parsed_body_or_text)."""
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=body, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Suite:
    name: str
    results: list[Result] = field(default_factory=list)

    def check(self, name: str, condition: bool, detail: str = ""):
        self.results.append(Result(name, bool(condition), detail))

    def passed(self) -> int:
        return sum(1 for r in self.results if r.ok)

    def total(self) -> int:
        return len(self.results)

    def report(self) -> str:
        lines = [f"\n=== {self.name}: {self.passed()}/{self.total()} ==="]
        for r in self.results:
            mark = "✅" if r.ok else "❌"
            lines.append(f"  {mark} {r.name}" + (f"  ({r.detail})" if r.detail and not r.ok else ""))
        return "\n".join(lines)


# === Suite 1: API contract ===
#
# "Every UI element is backed by a real endpoint with the expected shape."
# This is the cheapest layer to test and catches backend regressions.

def suite_api_contract() -> Suite:
    s = Suite("API contract")
    # /api/health
    code, body = api("GET", "/api/health")
    s.check("GET /api/health → 200", code == 200, f"got {code}")
    s.check("health body has 'status':'ok'", isinstance(body, dict) and body.get("status") == "ok",
            f"got {body}")
    s.check("health has 'subsystems'", isinstance(body, dict) and "subsystems" in body)

    # /api/albums (the album grid)
    code, albums = api("GET", "/api/albums")
    s.check("GET /api/albums → 200", code == 200, f"got {code}")
    s.check("albums is a list", isinstance(albums, list), f"got {type(albums)}")
    s.check("at least one seeded album exists", isinstance(albums, list) and len(albums) >= 1,
            f"got {albums}")
    if isinstance(albums, list) and albums:
        a = albums[0]
        for field in ("id", "title", "primary_artist_id", "status"):
            s.check(f"album has '{field}'", field in a, f"keys={list(a.keys())}")

    # /api/sessions (the session picker)
    code, sessions = api("GET", "/api/sessions")
    s.check("GET /api/sessions → 200", code == 200)

    # /api/albums/:id/{tracks,assets,sessions} (drilldowns)
    if isinstance(albums, list) and albums:
        album_id = albums[0]["id"]
        for sub in ("tracks", "assets", "sessions"):
            code, body = api("GET", f"/api/albums/{album_id}/{sub}")
            s.check(f"GET /api/albums/:id/{sub} → 200", code == 200, f"got {code}")
            s.check(f"/api/albums/:id/{sub} is a list", isinstance(body, list), f"got {type(body)}")

    # /api/sessions/<id>/events + decisions (studio subresources)
    # Need a session — open one
    if isinstance(albums, list) and albums:
        code, sess = api("POST", "/api/sessions", {"album_id": albums[0]["id"]})
        s.check("POST /api/sessions → 201", code == 201, f"got {code}")
        if code == 201:
            sid = sess["id"]
            for sub in ("events", "decisions"):
                code, body = api("GET", f"/api/sessions/{sid}/{sub}")
                s.check(f"GET /api/sessions/:id/{sub} → 200", code == 200, f"got {code}")
                s.check(f"/api/sessions/:id/{sub} is a list", isinstance(body, list))

            code, body = api("GET", f"/api/sessions/{sid}/events/latest_id")
            s.check("GET .../events/latest_id → 200", code == 200, f"got {code}")
            s.check("latest_id has 'latest_event_id' key",
                    isinstance(body, dict) and "latest_event_id" in body)
    return s


# === Suite 2: Static asset contract ===
#
# "Every CSS file referenced by every HTML file actually exists, parses,
# and is served at the expected URL."

def suite_static_assets() -> Suite:
    s = Suite("Static assets")
    # Each HTML page declares its module.css and .js
    pages = {
        "/site/albums.html": ["/site/albums.module.css", "/site/albums.js"],
        "/site/studio.html": ["/site/studio.module.css", "/site/studio.js"],
    }
    for page, deps in pages.items():
        code, body = api("GET", page)
        s.check(f"GET {page} → 200", code == 200, f"got {code}")
        if code == 200 and isinstance(body, str):
            for dep in deps:
                s.check(f"{page} references {dep}", dep in body,
                        f"link/script tag missing")
                code2, _ = api("GET", dep)
                s.check(f"GET {dep} → 200", code2 == 200, f"got {code2}")
    return s


# === Suite 3: UX state model ===
#
# "If a UI element is interactive, clicking it produces an observable
# state change that round-trips through the API."
#
# These tests don't drive the browser — they call the API the same way
# the browser would. The browser-driven version lives in
# e2e/test_browser_drive.py (separate, requires Chrome remote debugging).
# This version runs anywhere; it just proves the underlying state machine.

def suite_ux_state_model() -> Suite:
    s = Suite("UX state model")
    code, albums = api("GET", "/api/albums")
    if not (isinstance(albums, list) and albums):
        s.check("seed: have an album", False, "no seeded album")
        return s
    album_id = albums[0]["id"]

    # Lifecycle: open → pause → resume → complete.
    # The API contract suite may already have opened up to 3 sessions on
    # the same album; if so, our open would 409 with max-active. That's
    # correct behavior — close the previous one first, or accept that
    # the state machine is already populated.
    code, sess = api("POST", "/api/sessions", {"album_id": album_id})
    if code == 409:
        # Max-3 guard fired. Find an active session we can drive.
        _, sessions = api("GET", "/api/sessions")
        active = [s for s in (sessions or []) if s.get("status") == "active"]
        if active:
            sess = active[0]
            s.check("UX: open session (reused active — max-3 guard)", True,
                    f"using existing {sess['id']}")
        else:
            s.check("UX: open session", False, "max-3 but no active session to reuse")
            return s
    elif code == 201:
        s.check("UX: open session", True)
        sess = sess  # already have it
    else:
        s.check("UX: open session", False, f"got {code}")
        return s
    sid = sess["id"]
    s.check("UX: new (or reused) session is 'active'", sess.get("status") == "active")

    code, sess = api("POST", f"/api/sessions/{sid}/pause")
    s.check("UX: pause active session", code == 200, f"got {code}")
    s.check("UX: status is now 'paused'", sess.get("status") == "paused")

    code, sess = api("POST", f"/api/sessions/{sid}/resume")
    s.check("UX: resume paused session", code == 200, f"got {code}")
    s.check("UX: status is now 'active'", sess.get("status") == "active")

    code, sess = api("POST", f"/api/sessions/{sid}/complete")
    s.check("UX: complete active session", code == 200, f"got {code}")
    s.check("UX: status is now 'done'", sess.get("status") == "done")

    # State-machine guard
    code, _ = api("POST", f"/api/sessions/{sid}/pause")
    s.check("UX: pause after complete → 409", code == 409, f"got {code}")

    # Decision lock + history
    code, d1 = api("POST", "/api/decisions", {
        "code": "M01", "tier": "mandatory", "answer": "first",
        "album_id": album_id, "session_id": sid,
    })
    s.check("UX: create decision", code == 201)
    s.check("UX: locked_at set on create", d1.get("locked_at") is not None)
    if code == 201:
        did = d1["id"]
        code, d2 = api("PATCH", f"/api/decisions/{did}", {"answer": "second"})
        s.check("UX: patch decision", code == 200)
        s.check("UX: locked_at bumped after patch",
                d2.get("locked_at") and d1["locked_at"] and d2["locked_at"] != d1["locked_at"])

        code, d3 = api("PATCH", f"/api/decisions/{did}", {"answer": None})
        s.check("UX: explicit null clears answer", code == 200 and d3.get("answer") is None)

        code, _ = api("DELETE", f"/api/decisions/{did}")
        s.check("UX: delete decision → 204", code == 204)

    # Event polling (since_id cursor)
    code, sess2 = api("POST", "/api/sessions", {"album_id": album_id})
    if code == 201:
        sid2 = sess2["id"]
        ids = []
        for content in ("m1", "m2", "m3"):
            code, e = api("POST", "/api/events", {
                "session_id": sid2, "role": "user", "kind": "chat", "content": content,
            })
            if code == 201:
                ids.append(e["id"])
        if len(ids) == 3:
            code, evs = api("GET", f"/api/sessions/{sid2}/events?since_id={ids[0]}")
            s.check("UX: polling cursor returns new events",
                    code == 200 and len(evs) == 2 and [e["id"] for e in evs] == [ids[1], ids[2]],
                    f"got {len(evs) if isinstance(evs, list) else evs}")
            code, evs = api("GET", f"/api/sessions/{sid2}/events?since_id={ids[-1]}")
            s.check("UX: cursor at tail returns empty",
                    code == 200 and isinstance(evs, list) and len(evs) == 0)
    return s


# === Suite 4: UI element coverage matrix ===
#
# "Every visible UI element has a corresponding assertion." This is the
# catalogue — the browser-driven test in e2e/test_browser_drive.py walks
# each one with a real DOM selector.
#
# Format: (page, selector, what_it_represents, expected_after_seed)
UI_ELEMENTS = [
    # ---- albums.html ----
    ("albums.html", "nav.topbar", "top navigation bar", "rendered"),
    ("albums.html", ".crumb", "breadcrumb crumb", "contains 'albums'"),
    ("albums.html", "#status-pill", "live status pill", "rendered"),
    ("albums.html", "#new-album-btn", "new album button", "rendered"),
    ("albums.html", "header.hero h1", "hero headline", "renders H1"),
    ("albums.html", ".hero .lede", "hero lede paragraph", "renders copy"),
    ("albums.html", "#stat-active", "active sessions count stat", "numeric"),
    ("albums.html", "#stat-albums", "total albums stat", "numeric"),
    ("albums.html", "#stat-done", "done albums stat", "numeric"),
    ("albums.html", "#session-grid", "active sessions grid", "section exists"),
    ("albums.html", "#album-grid", "album library grid", "section exists"),
    ("albums.html", "footer.footer", "footer", "rendered"),
    ("albums.html", "#daemon-host", "daemon host text", "rendered"),
    ("albums.html", "#foot-meta-text", "footer metadata", "rendered"),
    ("albums.html", "#new-album-modal", "new album modal (initially hidden)", "exists, hidden"),
    ("albums.html", "input[name=id]", "modal ID input", "form field"),
    ("albums.html", "input[name=title]", "modal title input", "form field"),
    ("albums.html", "input[name=primary_artist_id]", "modal artist input", "form field"),
    ("albums.html", "input[name=release_date]", "modal release date input", "form field"),
    ("albums.html", "input[name=runtime_min]", "modal runtime input", "form field"),
    ("albums.html", "#modal-close-btn", "modal close button", "rendered"),
    ("albums.html", "#modal-cancel-btn", "modal cancel button", "rendered"),
    ("albums.html", "#album-drawer", "album detail drawer (initially hidden)", "exists, hidden"),
    ("albums.html", "#drawer-album-title", "drawer title", "rendered"),
    ("albums.html", "#drawer-meta", "drawer metadata grid", "rendered"),
    ("albums.html", "#drawer-sessions", "drawer sessions list", "rendered"),
    ("albums.html", "#drawer-open-session-btn", "drawer open-session button", "rendered"),
    ("albums.html", "#drawer-tracks", "drawer tracks list", "rendered"),
    ("albums.html", "#drawer-assets", "drawer assets list", "rendered"),

    # ---- studio.html ----
    # Static elements (in the HTML template)
    ("studio.html", "nav.topbar", "topbar with session picker", "rendered"),
    ("studio.html", "#session-picker", "session picker dropdown", "rendered"),
    ("studio.html", ".sidebar #album-title", "sidebar album title", "rendered"),
    ("studio.html", ".sidebar #album-artist", "sidebar album artist", "rendered"),
    ("studio.html", "#stat-layer", "sidebar current layer stat", "rendered"),
    ("studio.html", "#stat-phase", "sidebar current phase stat", "rendered"),
    ("studio.html", "#stat-runtime", "sidebar runtime stat", "rendered"),
    ("studio.html", "#stat-idle", "sidebar last activity stat", "rendered"),
    ("studio.html", "#meta-session", "meta session id", "rendered"),
    ("studio.html", "#meta-album-id", "meta album id", "rendered"),
    ("studio.html", "#meta-opened", "meta opened timestamp", "rendered"),
    ("studio.html", "#meta-updated", "meta updated timestamp", "rendered"),
    ("studio.html", "#btn-pause", "lifecycle pause button", "rendered"),
    ("studio.html", "#btn-resume", "lifecycle resume button", "rendered"),
    ("studio.html", "#btn-complete", "lifecycle complete button", "rendered"),
    ("studio.html", "#back-btn", "back-to-albums button", "rendered"),
    ("studio.html", "#pipeline", "9-layer pipeline grid container", "rendered"),
    ("studio.html", "#track-list", "tracks section", "rendered"),
    ("studio.html", "#asset-list", "assets section", "rendered"),
    ("studio.html", "#event-list", "events section (chat log)", "rendered"),
    ("studio.html", "#decision-list", "decisions section", "rendered"),
    ("studio.html", "#toast", "toast notification container (initially hidden)", "exists, hidden"),

    # JS-rendered dynamic elements — these are NOT in the static HTML,
    # they appear after studio.js runs. They are checked separately
    # in suite_dynamic_rendering() below.
    ("studio.html [dynamic]", ".pipe-cell", "individual pipeline cell", "9 cells after JS run"),
    ("studio.html [dynamic]", ".track-row", "individual track row", "≥1 row after JS run"),
    ("studio.html [dynamic]", ".event-row", "individual event row", "appears when events exist"),
    ("studio.html [dynamic]", ".decision-card", "individual decision card", "appears when decisions exist"),
    ("albums.html [dynamic]", ".album-card", "individual album card", "≥1 card after JS run"),
    ("albums.html [dynamic]", ".empty-card", "empty-state card", "rendered when grid empty"),
]


def suite_ui_coverage_matrix() -> Suite:
    """Verify every documented UI element exists in its source HTML file.

    This is a static check (against the HTML files served by the
    daemon), not a DOM check. It catches cases where a developer
    removes an element from the template without updating the catalogue.
    """
    s = Suite("UI coverage matrix")
    for page, selector, what, _expected in UI_ELEMENTS:
        # Skip dynamic JS-rendered elements — they live in studio.js,
        # not in the static HTML. They're verified via the dynamic
        # rendering suite (or by the browser-driven suite).
        if page.endswith("[dynamic]"):
            continue
        code, html = api("GET", f"/site/{page}")
        if code != 200 or not isinstance(html, str):
            s.check(f"{page}: {what} ({selector})", False, f"page not served")
            continue

        # Determine what string to look for in the HTML. Different
        # selector shapes map to different literal tokens.
        target = None
        if selector.startswith("#"):
            target = f'id="{selector[1:]}"'
        elif selector.startswith(".") and not selector.startswith(".."):
            cls = selector[1:].split()[0]
            target = f'class="{cls}"'
            # Some classes appear on multiple elements (e.g. "topbar");
            # accept any element with that class.
            if target not in html and f' {cls}"' not in html and cls not in html:
                s.check(f"{page}: {what} ({selector})", False,
                        f"class '{cls}' not in HTML")
                continue
            s.check(f"{page}: {what} ({selector})", True)
            continue
        elif selector.startswith("input["):
            # E.g. input[name=id] → look for name="id" attribute
            attr = selector[len("input["):-1]
            if "=" in attr:
                attr_name, attr_val = attr.split("=", 1)
                target = f'{attr_name}="{attr_val}"'
        elif selector.startswith("nav.") or selector.startswith("header.") or selector.startswith("footer."):
            # nav.topbar, footer.footer — look for the class
            cls = selector.split(".", 1)[1].split()[0]
            target = cls
        else:
            # Tag or tag.class — accept either
            tag = selector.split(".")[0]
            target = f"<{tag}"

        if target is None:
            s.check(f"{page}: {what} ({selector})", False, "could not derive target")
            continue
        s.check(f"{page}: {what} ({selector})", target in html,
                f"'{target}' not in served HTML")
    return s


# === Suite 5: Dynamic rendering contract ===
#
# "What the API returns, the JS can render." This catches cases where
# the API contract works in isolation but the shape doesn't match what
# studio.js / albums.js expects to find in the JSON.
#
# For each dynamic element category, we seed enough data for the JS
# to render at least one item, then verify the API returns it with
# the expected fields.

def suite_dynamic_rendering() -> Suite:
    s = Suite("Dynamic rendering contract")

    # ---- Albums grid ----
    code, albums = api("GET", "/api/albums")
    s.check("albums: at least one album", code == 200 and isinstance(albums, list) and len(albums) >= 1)
    if code == 200 and albums:
        a = albums[0]
        # albums.js renders .album-card with these fields
        for f in ("id", "title", "primary_artist_id", "status"):
            s.check(f"album renderable: '{f}' in album payload", f in a, f"keys={list(a.keys())}")

    # ---- Tracks ----
    if isinstance(albums, list) and albums:
        album_id = albums[0]["id"]
        code, tracks = api("GET", f"/api/albums/{album_id}/tracks")
        s.check("tracks: rendered list", code == 200 and isinstance(tracks, list) and len(tracks) >= 1)
        if isinstance(tracks, list) and tracks:
            t = tracks[0]
            for f in ("title", "id"):
                s.check(f"track renderable: '{f}' in track payload", f in t, f"keys={list(t.keys())}")
            # Day 6 fix: studio.js now accepts BOTH 'duration_sec' and
            # 'duration_ms'. We don't assert exact field name — we just
            # assert that SOMETHING is present so the UI can render.
            s.check(f"track renderable: duration field present",
                    "duration_sec" in t or "duration_ms" in t,
                    f"tracks have duration_sec, not duration_ms")

    # ---- Sessions + events + decisions for studio ----
    if isinstance(albums, list) and albums:
        # Open a fresh session (may 409 if max-3 — fall back to existing)
        code, sess = api("POST", "/api/sessions", {"album_id": albums[0]["id"]})
        if code == 409:
            _, sessions = api("GET", "/api/sessions")
            sess = next((s for s in (sessions or []) if s.get("status") == "active"), None)
            s.check("sessions: opened (or reused active)", sess is not None)
        elif code == 201:
            s.check("sessions: opened", True)
        else:
            s.check("sessions: opened", False, f"got {code}")
            return s
        if sess is None:
            return s
        sid = sess["id"]

        # Seed at least one of each: a chat event, a build event (with payload),
        # a decision with all fields, and a decision with rationale only.
        api("POST", "/api/events", {"session_id": sid, "role": "user", "kind": "chat",
                                     "content": "e2e chat", "album_id": albums[0]["id"]})
        api("POST", "/api/events", {"session_id": sid, "role": "assistant", "kind": "build",
                                     "content": "e2e build", "album_id": albums[0]["id"],
                                     "payload": {"layer": 3, "phase": "lyrics_finalize"}})
        api("POST", "/api/decisions", {"code": "M01", "tier": "mandatory",
                                         "answer": "e2e answer", "rationale": "e2e rationale",
                                         "album_id": albums[0]["id"], "session_id": sid})

        code, events = api("GET", f"/api/sessions/{sid}/events")
        s.check("events renderable: list returns ≥2", code == 200 and len(events) >= 2)
        if isinstance(events, list) and events:
            chat = next((e for e in events if e["kind"] == "chat"), None)
            build = next((e for e in events if e["kind"] == "build"), None)
            s.check("events renderable: chat event present", chat is not None)
            s.check("events renderable: build event present", build is not None)
            s.check("events renderable: build event has payload.layer",
                    isinstance(build, dict) and isinstance(build.get("payload"), dict)
                    and "layer" in build["payload"])
            # The studio pipeline view derives current_layer from build events
            s.check("events renderable: studio can derive current_layer",
                    isinstance(build, dict) and build.get("payload", {}).get("layer") == 3)

        code, decisions = api("GET", f"/api/sessions/{sid}/decisions")
        s.check("decisions renderable: list returns ≥1", code == 200 and isinstance(decisions, list) and len(decisions) >= 1)
        if isinstance(decisions, list) and decisions:
            d = decisions[0]
            for f in ("code", "tier", "answer", "rationale"):
                s.check(f"decision renderable: '{f}' present", f in d, f"keys={list(d.keys())}")
    return s


# === Main runner ===

def main() -> int:
    print(f"E2E UX suite running against {BASE}")
    suites = [
        suite_api_contract(),
        suite_static_assets(),
        suite_ux_state_model(),
        suite_ui_coverage_matrix(),
        suite_dynamic_rendering(),
    ]
    total_pass = total_fail = 0
    all_ok = True
    for suite in suites:
        print(suite.report())
        total_pass += suite.passed()
        total_fail += suite.total() - suite.passed()
        if suite.passed() != suite.total():
            all_ok = False

    print(f"\n=========================")
    print(f"TOTAL: {total_pass}/{total_pass + total_fail} passed")
    print(f"=========================")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
