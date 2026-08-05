# Premium Cassette-Mesh Alternative

## What this is

A **premium upgrade** of the cassette-mesh design system (template 14). Same
visual language (`/the label is the aurora`), same color palette, same three
typefaces — but with **real AI-generated photography** instead of CSS-only mockups.

## AI-generated assets (15 images, 3.5 MB)

| Asset | Size | Purpose |
|---|---|---|
| `cover-v1-magenta-cyan.jpg` | 1024×1024 | Album cover (magenta/cyan aurora) |
| `cover-v2-blue-violet.jpg` | 1024×1024 | Album cover (blue/violet aurora) |
| `cover-v3-green-amber.jpg` | 1024×1024 | Album cover (green/amber aurora) |
| `cover-v4-warm-ember.jpg` | 1024×1024 | Album cover (warm ember aurora) |
| `hero-cassette.jpg` | 1920×1080 | Hero cassette with aurora mesh label |
| `motif-v1-vancouver.jpg` | 1024×1024 | Half-light window, Vancouver |
| `motif-v2-berlin.jpg` | 1024×1024 | Half-light window, Berlin |
| `motif-v3-lisbon.jpg` | 1024×1024 | Half-light window, Lisbon |
| `motif-v4-brooklyn.jpg` | 1024×1024 | Half-light window, Brooklyn |
| `motif-v5-tokyo.jpg` | 1024×1024 | Half-light window, Tokyo |
| `motif-v6-mexico-city.jpg` | 1024×1024 | Half-light window, Mexico City |
| `voice-marielle.jpg` | 1024×1024 | Singer portrait (Marielle) |
| `voice-joaquin.jpg` | 1024×1024 | Singer portrait (Joaquín) |
| `voice-ensemble.jpg` | 1024×1024 | Singer portrait (Ensemble) |
| `dashboard-studio-bg.jpg` | 1920×1080 | Recording studio at 3 AM |

## Premium mockups

- `assets/premium-mockup-01-design-system.png` (2880×6228) — Design system with real cassette hero
- `assets/premium-mockup-04-dashboard.png` (2880×2680) — Dashboard with real album covers, voice portraits, pipeline grid
- `assets/premium-animations-preview.png` (2880×1800) — 4 CSS animation primitives (mesh drift, reel spin, typewriter, pulse glow)

## Files

- `site/premium-cassette-animations.html` — Standalone HTML with the 4 animation primitives
- `assets/premium-mockups/01-design-system-2880x6228.png` — exact-mockup for Penpot import
- `assets/premium-mockups/04-dashboard-2880x3082.png` — exact-mockup for Penpot import

## Design system

Identical to the cassette-mesh template 14:

| Token | Value |
|---|---|
| `color.bg` | `#0a0a14` |
| `color.ink` | `#fafafa` |
| `color.tape` | `#f0c53c` |
| `color.magenta` | `#f25cb0` |
| `color.cyan` | `#2dd8f0` |
| `color.amber` | `#f5c142` |
| `color.violet` | `#b94af5` |
| `font.display` | Major Mono Display |
| `font.sans` | Inter |
| `font.mono` | JetBrains Mono |

## Tone

Same cassette-mesh tone: warm 90s indie rock aesthetic, A24 film cinematography,
35mm film grain, the tape is the chassis, the aurora is the soul.

## How to view

```bash
# Open the design system mockup
xdg-open assets/premium-mockup-01-design-system.png

# Open the dashboard mockup
xdg-open assets/premium-mockup-04-dashboard.png

# Open the animations preview
firefox site/premium-cassette-animations.html

# Open the premium animations in browser
explorer.exe site/premium-cassette-animations.html
```

## Generated with

- **MiniMax image-01** (15 images, ~3.5 MB total)
- **HTML/CSS** for the premium mockups
- **Playwright** for screenshot capture
- **Open Design** (attempted but the BYOK setup was incomplete; rolled manual CSS animations instead)
