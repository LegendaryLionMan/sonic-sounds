# album-studio / penpot-pages

Autonomous Penpot build-out — what was produced before the 8-hour deadline.

## What this folder contains

6 high-fidelity PNG mockups of the Penpot design pages, plus the HTML sources
that generated them. All built against the locked DESIGN.md spec.

| Page | HTML | PNG | What it shows |
|---|---|---|---|
| 01 — Design System | 01-design-system.html | 01-design-system.png | Color tokens, type ramp, spacing scale |
| 02 — Components | 02-components.html | 02-components.png | Card, Badge (4 states), Question Row, Layer Card, Hairline, Motif |
| 03 — Intake | 03-intake.html | 03-intake.png | Full 11-mandatory + 11-recommended intake form |
| 04 — Dashboard | 04-dashboard.html | 04-dashboard.png | 12-layer grid with status badges + progress bar |
| 05 — Cover Exploration | 05-cover-exploration.html | 05-cover-exploration.png | 4 cover variants for "22" (altar / bedroom / stage / burned) |
| 06 — Motif Library | 06-motif-library.html | 06-motif-library.png | Half-lit window motif in 3 sizes |

Total: 6 pages, ~1,200 KB of rendered PNG, ~85 KB of HTML source.

## Auto-importer (fires when the Penpot plugin connects)

When the browser plugin connects (`File → MCP Server → Connect`), the
auto-importer at `planning/penpot-importer.js` runs and:

1. Creates 26 design tokens (10 colors + 8 font sizes + 7 spacing + 1 border-radius)
2. Creates 6 pages with the exact names DESIGN.md expects
3. Imports each PNG into the right page as an image-fill rectangle

The importer is idempotent — running it again won't duplicate anything.

## Mirroring

All files are mirrored to:
- `~/OneDrive/Hermes/Agents/planning/album-studio/penpot-build/` (canonical)
- `~/Documents/Projects/album-studio/site/penpot-pages/` (project repo)

md5 matches verified.

## Browser plugin setup (if the auto-import hasn't fired)

The Penpot MCP needs a browser plugin running inside Penpot itself:

1. Open Penpot in your browser at http://127.0.0.1:9001/
2. Open a design file (any file — the MCP needs ONE file focused)
3. Go to **Plugins → Load from URL**
4. Paste `http://localhost:4400/manifest.json` (NOT 127.0.0.1, NOT https)
5. Run the plugin
6. Click **Connect to MCP server**
7. **Keep the plugin window open** — closing it disconnects the MCP

Both Local and Remote MCP modes require the browser plugin step.
The `No Penpot plugin instances are currently connected` error means
the plugin isn't open in the browser, NOT that the URL is wrong.

## Reference

- DESIGN.md — the visual spec (editorial / zine direction)
- planning/penpot-build-data.json — layer + question data
- planning/penpot-importer.js — the auto-importer script
- planning/PENPOT-SETUP-NOTES.md — the diagnostic journey (why the
  plugin needed to be loaded from a specific URL)
