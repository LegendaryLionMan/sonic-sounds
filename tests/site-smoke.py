r"""
sonic-studio site smoke test
Tests both intake.html and dashboard.html at desktop viewport (1440x900)
Captures screenshots to sonic-studio-smoke-*.png
"""
from playwright.sync_api import sync_playwright
import sys, os, json, time

BASE = "http://127.0.0.1:8765/site"
SHOTS_DIR = r"C:\Users\lion_\AppData\Local\Temp"

errors = []
results = []

def check(name, ok, detail=""):
    icon = "OK" if ok else "FAIL"
    line = f"  [{icon}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    results.append((name, ok, detail))
    if not ok:
        errors.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    console_msgs = []
    page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda e: console_msgs.append(f"pageerror: {e}"))

    # ============================================================
    # 1) intake.html
    # ============================================================
    print("\n=== intake.html ===")
    page.goto(f"{BASE}/intake.html", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(800)

    # Check title
    title = page.title()
    check("title rendered", "sonic-studio" in title, title)

    # Count question cards
    qs = page.locator("article.question").count()
    check("21 question cards", qs == 21, f"found {qs}")

    # Count tier bands
    bands = page.locator(".tier-band").count()
    check("3 tier bands", bands == 3, f"found {bands}")

    # Mandatory tier count
    m_qs = page.locator("article.question[data-tier='M']").count()
    check("8 mandatory questions", m_qs == 8, f"found {m_qs}")

    r_qs = page.locator("article.question[data-tier='R']").count()
    check("6 recommended questions", r_qs == 6, f"found {r_qs}")

    e_qs = page.locator("article.question[data-tier='E']").count()
    check("7 extra questions", e_qs == 7, f"found {e_qs}")

    # Tracklist grid: 12 rows
    tracks = page.locator(".tracklist-rows input").count()
    check("12 tracklist inputs (6 title + 6 theme = no, 12 title + 12 theme = 24)", tracks == 24, f"found {tracks}")

    # Generate button initially disabled
    btn = page.locator("#generateBtn")
    check("generate button initially disabled", btn.is_disabled(), "")

    # Check the saved-label
    saved = page.locator("#savedLabel .text").inner_text()
    check("saved label visible", "READY" in saved or "TYPING" in saved, saved)

    # Fill all 8 mandatory fields
    page.fill("textarea[name='M01_concept']", "An album about the half-light hour — that 30-minute window between dusk and full dark when the world feels liminal.")
    page.select_option("select[name='M02_scope']", "album")
    page.fill("input[name='M03_genre']", "dream-folk")
    page.fill("input[name='M04_ref1']", "Grouper")
    page.fill("input[name='M04_ref2']", "Adrianne Lenker")
    page.fill("input[name='M04_ref3']", "Aldous Harding")
    page.select_option("select[name='M05_approach']", "solo")
    page.fill("input[name='M05_character']", "low, breathy, close-mic'd")
    page.fill("input[name='M06_languages']", "English")
    page.select_option("select[name='M07_runtime']", "standard")
    page.fill("input[name='M08_artist']", "Maren Sol")

    page.wait_for_timeout(1500)  # let debounce + gate update fire

    # Mandatory resolved should be 8/8
    resolved_text = page.locator("#mandatoryResolved").inner_text()
    check("mandatory resolved 8/8 after fill", resolved_text.strip() == "resolved 8 of 8", resolved_text.strip())

    # Generate button now enabled
    check("generate button enabled after 8/8", not btn.is_disabled(), "")

    # Capture screenshot
    shot = os.path.join(SHOTS_DIR, "sonic-studio-smoke-intake-filled.png")
    page.screenshot(path=shot, full_page=True)
    print(f"  Screenshot: {shot}")

    # Click generate and verify a download happens
    with page.expect_download(timeout=10000) as dl_info:
        btn.click()
    dl = dl_info.value
    save_path = os.path.join(SHOTS_DIR, "sonic-studio-smoke-download.json")
    dl.save_as(save_path)
    check("download fired", os.path.exists(save_path), save_path)

    # Validate the downloaded JSON against the schema
    with open(save_path) as f:
        exported = json.load(f)
    check("exported has schemaVersion 1.0", exported.get("schemaVersion") == "1.0", str(exported.get("schemaVersion")))
    check("exported has albumSlug matching pattern", bool(exported.get("albumSlug")) and "-" in exported.get("albumSlug",""), exported.get("albumSlug"))
    check("exported has all 8 mandatory answer keys", all(k in exported.get("answers",{}) for k in ["M01_concept","M02_scope","M03_genre","M04_references","M05_vocal","M06_language","M07_runtime","M08_artist"]))
    check("exported M02_scope is album", exported["answers"]["M02_scope"]["value"] == "album")
    check("exported M04 has 3 references", len(exported["answers"]["M04_references"]["artists"]) == 3)
    check("exported M06 languages is ['English']", exported["answers"]["M06_language"]["languages"] == ["English"])

    # Verify confirmation card appeared
    confirm = page.locator("#confirmationCard")
    is_shown = "is-shown" in (confirm.get_attribute("class") or "")
    check("confirmation card shown after export", is_shown, "")

    # Console errors check - dashboard tries multiple fallback paths, so 404s on
    # candidate state.json paths are EXPECTED (not actual errors)
    page.wait_for_timeout(300)
    bad_console = [m for m in console_msgs if m.startswith("error") or m.startswith("pageerror")]
    # Filter expected 404s from the candidate-path probes
    bad_console = [m for m in bad_console if "Failed to load resource" not in m]
    check("no JS console errors during intake flow", len(bad_console) == 0, f"{len(bad_console)} errors: {bad_console[:3]}")

    # ============================================================
    # 2) dashboard.html with state.json present
    # ============================================================
    print("\n=== dashboard.html ===")
    console_msgs.clear()
    page.goto(f"{BASE}/dashboard.html?album=half-light-hours", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(800)

    # Title should mention the album
    title = page.locator("#dashTitle").inner_text()
    check("title mentions album", "Half-Light" in title or "half-light" in title.lower(), title)

    # Subtitle should have artist · genre · scope
    subtitle = page.locator("#dashSubtitle").inner_text()
    check("subtitle has artist · genre · scope",
          "Maren Sol" in subtitle and "dream-folk" in subtitle and "album" in subtitle,
          subtitle)

    # 12 layer cards
    cards = page.locator(".layer-card").count()
    check("12 layer cards", cards == 12, f"found {cards}")

    # Verify the statuses we set in state.json
    done_cards = page.locator(".layer-card[data-status='done']").count()
    in_prog_cards = page.locator(".layer-card[data-status='in-progress']").count()
    todo_cards = page.locator(".layer-card[data-status='todo']").count()
    blocked_cards = page.locator(".layer-card[data-status='blocked']").count()
    check("1 done card (artist brand)", done_cards == 1, f"found {done_cards}")
    check("1 in-progress card (tracklist)", in_prog_cards == 1, f"found {in_prog_cards}")
    check("1 blocked card (ID3 metadata)", blocked_cards == 1, f"found {blocked_cards}")

    # Next action block visible
    next_action = page.locator(".next-action h3")
    check("next action block visible", next_action.count() == 1, "")

    # Progress bar segments
    segs = page.locator(".progress-bar .seg").count()
    check("progress bar 12 segments", segs == 12, f"found {segs}")

    # Capture screenshot
    shot = os.path.join(SHOTS_DIR, "sonic-studio-smoke-dashboard.png")
    page.screenshot(path=shot, full_page=True)
    print(f"  Screenshot: {shot}")

    # Console errors - 404s on candidate state.json paths are EXPECTED (fallback probes)
    page.wait_for_timeout(300)
    bad_console = [m for m in console_msgs if m.startswith("error") or m.startswith("pageerror")]
    bad_console = [m for m in bad_console if "Failed to load resource" not in m]
    check("no JS console errors on dashboard", len(bad_console) == 0, f"{len(bad_console)} errors: {bad_console[:3]}")

    # ============================================================
    # 3) dashboard.html with no state.json (empty state)
    # ============================================================
    print("\n=== dashboard.html (empty state) ===")
    console_msgs.clear()
    # Use a non-existent slug to force the empty state path
    page.goto(f"{BASE}/dashboard.html?album=does-not-exist", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(800)
    empty = page.locator(".empty-state")
    check("empty state shown when state.json missing", empty.count() == 1, "")
    cta = page.locator(".empty-state .button")
    check("empty state CTA points to intake.html", cta.count() == 1 and "intake" in cta.get_attribute("href"), cta.get_attribute("href"))

    page.wait_for_timeout(300)
    bad_console = [m for m in console_msgs if m.startswith("error") or m.startswith("pageerror")]
    bad_console = [m for m in bad_console if "Failed to load resource" not in m]
    check("no JS console errors on empty dashboard", len(bad_console) == 0, f"{len(bad_console)} errors: {bad_console[:3]}")

    # ============================================================
    # 4) Mobile viewport test (collapses dashboard grid)
    # ============================================================
    print("\n=== dashboard.html (mobile 600px) ===")
    ctx2 = browser.new_context(viewport={"width": 600, "height": 900})
    page2 = ctx2.new_page()
    page2.goto(f"{BASE}/dashboard.html?album=half-light-hours", wait_until="networkidle", timeout=15000)
    page2.wait_for_timeout(800)
    shot = os.path.join(SHOTS_DIR, "sonic-studio-smoke-dashboard-mobile.png")
    page2.screenshot(path=shot, full_page=True)
    print(f"  Screenshot: {shot}")
    ctx2.close()

    # Mobile intake
    ctx3 = browser.new_context(viewport={"width": 600, "height": 900})
    page3 = ctx3.new_page()
    page3.goto(f"{BASE}/intake.html", wait_until="networkidle", timeout=15000)
    page3.wait_for_timeout(800)
    shot = os.path.join(SHOTS_DIR, "sonic-studio-smoke-intake-mobile.png")
    page3.screenshot(path=shot, full_page=True)
    print(f"  Screenshot: {shot}")
    ctx3.close()

    browser.close()

# ============================================================
# Final report
# ============================================================
print()
print("=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
failed = len(errors)
total = len(results)
print(f"PASSED: {passed}/{total}")
if failed:
    print(f"FAILED: {errors}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)