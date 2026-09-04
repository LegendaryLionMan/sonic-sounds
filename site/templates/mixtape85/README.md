# mixtape85 — sonic-studio v1 template (Q21 PATCH 2026-08-05)

**Status:** Locked as v1 template per Q21 patch (2026-08-05).

## History

- **Original Q21 (2026-07-29, v3.1 lock):** "v1 ships ONE template: cassette-mesh (prototype 14), refined to production quality. No second template in v1."
- **Patched Q21 (2026-08-05, v3.2 revision):** User uploaded 6 cassette reference images. Synthesized visual brief → Mixtape '85 direction. **Mixtape '85 supersedes cassette-mesh as the v1 template.** The cassette-mesh prototype is preserved in `site/prototypes/14-cassette-mesh/` as research material.

## Why the patch

The user's reference images (6 cassette photos from real collections — Maxell, TDK, JVC, Memorex, Philips) established a clear aesthetic direction:

- Light cream/white cassette shells (NOT dark)
- Saturated color-banded labels (red/yellow/cyan/green/orange/magenta)
- Hand-applied sticker aesthetic with visible wear
- 80s/early-90s home-recorded mixtape culture (NOT editorial zine)
- Bebas Neue + Inter + JetBrains Mono + Caveat typography

The original cassette-mesh direction (dark canvas, magenta-cyan-amber-violet aurora, Major Mono Display) didn't match. The user feedback was unambiguous: "this is so stupid" / "i want to change the album topic" — extended to the visual direction.

## What this template provides

- **Palette** (per DESIGN.md §2): 9 color tokens (--bg, --bg-soft, --shell, --ink, --ink-soft, --ink-muted, --red, --yellow, --cyan, --green, --blue, --magenta, --violet, --amber, --pink)
- **Typography** (per DESIGN.md §3): 4 families (Inter / JetBrains Mono / Bebas Neue / Caveat)
- **8 type sizes** (modular ratio 1.333)
- **6 spacing tokens** (8px → 96px)
- **9 components** (button, card, input, modal, badge, sticker, session-card, topbar, footer)
- **4 page shapes** (index, studio, library, albums)

## Files

| File | Purpose |
|---|---|
| `site/css/components.css` | Tokens + 9 components (single source of truth) |
| `site/css/ux-states.css` | 5 button states (default/disabled/loading/success/error/timeout) + ARIA helpers + toast system |
| `site/index.html` | Home page (hero + album seed card + footer) |
| `site/studio.html` | Studio shell (session header + pipeline panel) |
| `site/library.html` | Cassette wall (album cover collection) |
| `site/albums.html` | Active/queued/done session cards |
| `site/mixtape85/00-index.html` | Premium design system page (Penpot-equivalent) |
| `site/mixtape85/02-components.html` | Premium components page |
| `site/mixtape85/03-intake.html` | Premium intake page |
| `site/mixtape85/04-dashboard.html` | Premium dashboard page (with real Half-Light Hours data) |
| `site/mixtape85/05-cover-exploration.html` | Premium cover exploration (interactive) |
| `site/mixtape85/06-motif-library.html` | Premium motif library |

## Premium mockups (Penpot-importable)

- `assets/premium-mixtape85-00-index.png` (2880x8022)
- `assets/premium-mixtape85-02-components.png` (2880x6178)
- `assets/premium-mixtape85-03-intake.png` (2880x8026)
- `assets/premium-mixtape85-04-dashboard.png` (2880x3082)
- `assets/premium-mixtape85-05-cover-exploration.png` (2880x2414)
- `assets/premium-mixtape85-06-motif-library.png` (2880x3610)
- `assets/premium-mixtape85-design-system.png` (2880x6228) — the original demo design system

## Verification

- ✓ `python -m http.server 8765` → all 4 page shapes return 200
- ✓ `python -m unittest tests.test_pipeline` → 22/22 pass (1 skip waiting for Day 2)
- ✓ `assets/day1-index-render.png` — visual confirmation: tokens render correctly
- ✓ All 4 page shapes (intake, studio, library, albums) have working shell + footer

## Out of scope (per v3.2 plan)

- A second template — Q21 patch is v1 lock, not v2 expansion
- Production-quality audio (Day 11)
- Live daemon integration (Day 3) — current pages hit /site/index.html etc. which work as static shells
- Penpot integration (Day 12 e2e suite)

## References

- `DESIGN.md` — design tokens and component spec
- `planning/QUESTIONNAIRE-WALKTHROUGH-2026-07-29.md` — locked M01-M09, R09-R19 + E22-E25 values
- `assets/references/ref-01..06` — user's 6 cassette reference images (the visual brief)
- `PENPOT-CLEANUP-FINAL-2026-08-05.md` — the 7 Penpot pages
- `site/penpot-pages/` — the rendered mockups at Penpot dimensions
