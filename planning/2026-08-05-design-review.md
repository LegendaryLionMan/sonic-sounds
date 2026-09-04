# Sonic Studio Design Review — 2026-08-05 (Session End)

## What got shipped today

### 8 commits, 3 design alternatives built, 31 AI assets generated (~7.5 MB), 9 Penpot pages

```
489277b Twenty-Two: Mixtape '85 design alternative informed by user references
14660c4 Twenty-Two: premium animations page + 4 CSS animation primitives
3b8eee1 Twenty-Two: premium cassette-mesh alternative with AI-generated photography
0c119ad Twenty-Two: doc — Penpot fix log update (full cleanup, 1 rect per page)
620a683 Twenty-Two: re-render 6 cassette-mesh PNGs at editorial zine dimensions
91ebf46 Twenty-Two: doc — Penpot fix log (cassette-mesh re-import via cache-buster)
35ab3ae Twenty-Two: rebuild 6 Penpot pages in cassette-mesh style (replaces Editorial Zine)
6e9c13e Twenty-Two: Penpot MCP bridge solved — 6 pages + 26 design tokens imported
```

## Three design alternatives on the table

### 1. Original cassette-mesh (dark, neon, the aurora-label cassette)
- **6 pages** in Penpot: 01 Design System, 02 Components, 03 Intake, 04 Dashboard, 05 Cover Exploration, 06 Motif Library
- **The vocabulary:** Major Mono Display + Inter + JetBrains Mono, magenta/cyan/amber/violet aurora palette, dark `#0a0a14` canvas, "the label is the aurora" footer

### 2. Premium cassette-mesh (cleaned up, 4 hero AI images inlined)
- **2 pages** in Penpot: Premium 01 Design System, Premium 04 Dashboard
- Same vocabulary as #1 but with REAL AI-generated cassette photography (4 cover variants, 6 motifs, 3 voice portraits, 1 hero cassette)
- The "premium" alternative — same chrome, real photos instead of CSS-only meshes

### 3. Mixtape '85 (new, from user references) ⭐ USER FAVORITE
- **1 page** in Penpot: Premium 01b — Mixtape 85
- **The vocabulary:** Bebas Neue + Inter + JetBrains Mono + Caveat, cream cassettes with color-banded labels (red/yellow/cyan/green), the cassette IS the hero, "the cassette is the chassis" footer
- 14 NEW AI assets informed by 6 user references (saved to assets/references/)

## Honest review — what's working, what's broken, what's missing

### What's WORKING (across all 3 alternatives)

✅ **Color-banded cassettes in Mixtape '85** — the 4 cover variants with saturated color bands on cream shells. This is exactly the user's vibe from the references.

✅ **Real hero cassette photography** — the 1920×1080 hero-mixtape85.jpg with aurora-gradient label on black velvet is editorial-grade.

✅ **Major Mono Display headline treatment** — "THE LABEL IS THE AURORA" in the cassette-mesh design is iconic.

✅ **12-layer pipeline grid with gradient state badges** — works in both cassette-mesh and premium variants.

✅ **Voice portraits are real photography** — Maren Sol, Joaquín, Ensemble as AI-generated singer portraits.

✅ **Saturated neon-vintage palette** — magenta/cyan/amber/violet on dark is genuinely beautiful.

### What's BROKEN (across all 3 alternatives)

❌ **No navigation between pages.** Each Penpot page exists in isolation. The user can't click from Design System → Dashboard → Cover Exploration. There's no top nav, no sidebar, no page-switching UI.

❌ **Animations page is a static screenshot.** The 4 CSS animation primitives are real and live (mesh drift, reel spin, typewriter, pulse glow), but I exported them as a static PNG. The user has to open `site/premium-cassette-animations.html` in Chrome to see them move. **Should have been an animated GIF or webm.**

❌ **All content is placeholder.** "Maren Sol / 12 tracks / 42:14 / 2026" — none of this is real. The user can see it's a shell.

❌ **Voice Auditions shows 3 voices but the dashboard plan locked 6.** The earlier overview said "6/6 ready" but I only show 3 cards in the dashboard. The voice portraits I generated are 3 (Marielle, Joaquín, Ensemble) — should have been 6.

❌ **No real cover selection interaction.** Cover Exploration (page 05) shows 4 cassettes in a row but there's no hover state, no "click to select" indication. Just static rectangles.

❌ **No real pipeline interaction.** Dashboard 12-layer grid has status badges but no "click to advance" or "regenerate" buttons. Pure visual.

❌ **Hero has too much empty space** on the left in cassette-mesh variants. The cassette only fills the right half; left half is mostly black.

❌ **Hero cassette image contains hallucinated text** (the AI-generated cassette labels have fake "HALF LIGHT HOURS / Society / etc." in the wrong font). On the editorial-grade look, this looks intentional but it's actually AI noise.

❌ **Mixtape '85 hero subtitle** has the AI-generated cassette text bleeding through into the page chrome (the AI wrote fake tracklist text that's rendered as part of the hero, mixed with my handwritten Caveat text).

### What's MISSING (next session priority list)

1. **Design-token documentation** in `DESIGN.md` needs to be updated with the Mixtape '85 palette additions (red `#e83a3a`, yellow `#f0c53c`, blue `#2962ff`, green `#4caf50`, etc.)

2. **Real navigation between Penpot pages** — at minimum, a top nav with links to all 9 pages. Should be a separate "00 Index" page in Penpot.

3. **OneDrive mirror of Penpot file** — the design lives only in the live Penpot instance. Should be backed up to `~/OneDrive/Hermes/Agents/planning/sonic-studio-design/`.

4. **Cover selection interaction** — the cover-exploration page should let the user click a cassette and have a "this becomes the album cover" feedback state. This requires actual interactive HTML, not just static PNGs.

5. **Animated GIF/webm export of the animations page** — the 4 animation primitives are real and live; capture them as motion for the user to see.

6. **6 voice portraits**, not 3 — generate Sabine, Ailani, Théo portraits to match the dashboard plan's "6/6 ready" voice wallet.

7. **Real content wiring** — connect the dashboard to the actual Half-Light Hours data in `~/OneDrive/Hermes/albums/half-light-hours/`. Right now it's all placeholder.

8. **Component library page (page 02)** — the current 02-Components page has a board (Penpot board) but no actual components. Should have buttons, cards, badges, status pills, voice cards, etc. as proper Penpot components, not just a placeholder board.

9. **Per-page hero variants** — every page should have its own hero treatment, not the same "the label is the aurora" everywhere.

10. **Dark mode toggle** — the cassette-mesh is dark, the Mixtape '85 is dark, but the user might want a light mode too.

## The user's actual feedback this session

| Message | What they meant |
|---|---|
| "its getting better! review all designs!!" | The Mixtape '85 direction is right. Now do a real review of what's working / broken / missing across all the artifacts I shipped today. |

## Next session concrete actions (priority order)

1. **[CRITICAL]** Update `DESIGN.md` with the Mixtape '85 design tokens
2. **[CRITICAL]** Generate 3 more voice portraits (Sabine, Ailani, Théo) to complete the 6-voice wallet
3. **[HIGH]** Render animations as animated GIF/webm so the user can see them move
4. **[HIGH]** Add a Penpot "00 Index" page with navigation links to all 9 design pages
5. **[MEDIUM]** Mirror the Penpot file to OneDrive for backup/offline access
6. **[MEDIUM]** Wire real Half-Light Hours data into the dashboard (replace placeholder text)
7. **[LOW]** Cover selection interaction (requires HTML, not just Penpot PNGs)
8. **[LOW]** Component library page (page 02) — populate with real Penpot components

## Files inventory (this session)

### Penpot pages (9 total, all confirmed via MCP bridge)
1. 01 — Design System (cassette-mesh, 6228 tall)
2. 02 — Components (cassette-mesh, 6178 tall)
3. 03 — Intake (cassette-mesh, 8026 tall)
4. 04 — Dashboard (cassette-mesh, 3082 tall)
5. 05 — Cover Exploration (cassette-mesh, 3082 tall)
6. 06 — Motif Library (cassette-mesh, 3610 tall)
7. Premium 01 — Design System (cassette-mesh premium, 6228 tall)
8. Premium 04 — Dashboard (cassette-mesh premium, 3082 tall)
9. Premium 01b — Mixtape 85 (Mixtape '85, 6228 tall) ⭐

### AI assets (31 total)
- 4 cassette-mesh covers (magenta-cyan / blue-violet / green-amber / warm-ember)
- 4 Mixtape '85 covers (red-tape / yellow-tape / cyan-tape / green-tape)
- 6 cassette-mesh motifs (Vancouver / Berlin / Lisbon / Brooklyn / Tokyo / Mexico City)
- 6 Mixtape '85 motifs (stacked / fanned / wall display / handheld / car / radio)
- 1 cassette-mesh hero (yellow cassette with aurora label)
- 1 Mixtape '85 hero (cream cassette with aurora label)
- 1 cassette-mesh dashboard bg (recording studio at 3 AM)
- 3 Mixtape '85 dashboard bgs (shelf / desk / boombox)
- 3 cassette-mesh voice portraits (Marielle / Joaquín / Ensemble)
- 2 promo mockups at exact editorial zine dimensions (2880×6228, 2880×3082)

### Standalone HTML pages
- `site/premium-cassette-animations.html` — 4 CSS animation primitives, hand-coded, Open Design was incomplete (BYOK auth failed)

### Project files
- `assets/references/` — 6 user references, kept for future iteration
- `PREMIUM-README.md` — describes the Mixtape '85 build
- `update_ov/scripts/ov-test-suite.py` — 33 tests, 3 byte-identical copies (independent work this session)

## What the user said is "getting better"

The user has approved the Mixtape '85 direction. Don't propose cassette-mesh alternatives unless the user explicitly says they want to revert. The aesthetic is locked to:
- Light cream cassettes with color-banded labels
- Real photography, vintage worn
- Dark background to make the colored labels POP
- Bebas Neue headlines + JetBrains Mono specs + Caveat handwritten notes
- "The cassette is the chassis" footer
- 80s/early-90s mixtape culture as the mood

## Final state summary

| Track | Status | File | Size |
|---|---|---|---|
| Cassette-mesh original | ✅ 6 Penpot pages | sonic-studio-design Penpot file | full |
| Cassette-mesh premium | ✅ 2 Penpot pages | Premium 01, Premium 04 | full |
| Mixtape '85 | ✅ 1 Penpot page | Premium 01b — Mixtape 85 | full |
| Animations | ⚠️ static screenshot | site/premium-cassette-animations.html | 10 KB |
| OV test suite | ✅ 33/33 pass | update_ov/scripts/ov-test-suite.py | 45 KB |
| OV auth fix | ✅ applied | .env OPENVIKING_API_KEY updated | — |
