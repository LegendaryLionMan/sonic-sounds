# DESIGN.md — sonic-studio

> The visual identity for the sonic-studio project: an HTML front door for the music-album-planning-questionnaire and the full-album-release-package skills.
>
> Direction locked: **Mixtape '85** — light cream cassette shells with color-banded labels, real photography, vintage worn, dark background to make the colored labels POP.
>
> Two design alternatives also exist (cassette-mesh aurora, premium cassette-mesh) but Mixtape '85 is the locked direction as of 2026-08-05.

---

## 1. Visual brief — Mixtape '85

The aesthetic is **80s / early-90s home-recorded mixtape culture**. Informed by the user's 6 reference images (saved to `assets/references/`):

- **Light cream / white plastic cassette shells** (not dark, not CGI)
- **Saturated color-banded labels** (red `#e83a3a`, yellow `#f0c53c`, cyan `#2dd8f0`, green `#4caf50`, blue `#2962ff`, magenta `#f25cb0`, orange `#ff7b00`) as full-bleed panels
- **Hand-applied sticker aesthetic** — small mono track numbers, handwritten titles
- **Visible wear, scratches, dust, fingerprints** — vintage patina, not pristine
- **Cassette IS the chassis** — the artifact itself is the visual, not chrome around it
- **Dark background** (`#0a0a0f`) so the colored labels POP

References that informed this direction:
- Indie record store photography (Dylan / Stones / Springsteen wall of tapes)
- 80s mixtape culture (handwritten tracklists, color-banded labels)
- FWRK Studios `MOCKUP` cassette PSD template (red+yellow flag stripe, light grey shell)
- A24 film photography (chiaroscuro, 35mm grain)

What it is NOT:
- Not Editorial Zine (no serif on warm paper)
- Not dark-on-dark cassette-mesh (no neon space aesthetic)
- Not a SaaS dashboard (no card grids)

---

## 2. Color palette

### Primary (token + use)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0a0a0f` | Primary canvas — near-black, makes colored labels POP |
| `--bg-soft` | `#14141a` | Card backgrounds, topbar |
| `--bg-card` | `#ffffff` | Cassette shell base (NOT a card — the SHELL is cream) |
| `--shell` | `#f5f1e8` | Cassette cream shell color |
| `--shell-shadow` | `#d4cfb8` | Cassette shell shadow / yellowing |
| `--ink` | `#fafafa` | Primary text on dark |
| `--ink-soft` | `rgba(255,255,255,.7)` | Secondary text |
| `--ink-muted` | `rgba(255,255,255,.4)` | Metadata, timestamps |
| `--ink-dark` | `#0a0a0f` | Text on cream cassette labels |

### Color bands (the cassette label palette)

| Token | Hex | Real cassette brand analogue |
|---|---|---|
| `--red` | `#e83a3a` | Maxell, TDK SA |
| `--yellow` | `#f0c53c` | TDK D, Philips |
| `--cyan` | `#2dd8f0` | Sony, BASF Chrome |
| `--blue` | `#2962ff` | Sony HF, JVC |
| `--green` | `#4caf50` | TDK AD, Realistic |
| `--magenta` | `#f25cb0` | Memorex, hard-to-find |
| `--violet` | `#b94af5` | Memorex, rare |
| `--amber` | `#ff7b00` | BASF, ferric oxide |
| `--pink` | `#ff5b8a` | Memorex pastels |

**Rule:** color bands are full-bleed cassette labels. Use one band per cassette. Side A and Side B can have different bands.

### Status colors (used in pipeline grid)

| Token | Hex | Use |
|---|---|---|
| `--status-done` | `#4caf50` (green) | Layer complete |
| `--status-active` | `#2dd8f0` (cyan) | Layer in progress |
| `--status-blocked` | `#e83a3a` (red) | Layer blocked |

### Aurora (the label drift — kept from cassette-mesh for the hero cassette)

| Token | Hex | Use |
|---|---|---|
| `--aurora-magenta` | `#f25cb0` | Label gradient top |
| `--aurora-cyan` | `#2dd8f0` | Label gradient middle |
| `--aurora-amber` | `#ff7b00` | Label gradient bottom |

---

## 3. Typography

### Four families

| Token | Family | Use |
|---|---|---|
| `--display` | `"Bebas Neue", "Oswald", sans-serif` | Hero headlines, cassette titles (weight 400, uppercase, letter-spacing 0.04em) |
| `--sans` | `"Inter", system-ui, sans-serif` | Body copy, descriptions, UI chrome |
| `--mono` | `"JetBrains Mono", "SF Mono", monospace` | Timestamps, cassette specs (C-90, 192KHZ), metadata, eyebrows |
| `--hand` | `"Caveat", "Kalam", cursive` | Handwritten tracklist notes, vocal descriptions |

**Why Bebas Neue:** heavy condensed sans = 80s/90s editorial + record-store aesthetic. Major Mono Display ships as the fallback for the "cassette-mesh" alternative but is replaced here.

**Why Caveat:** the handwritten layer is the mixtape authenticity. Real cassettes had tracklists written by hand. Caveat captures that.

### Type scale (modular, ratio 1.333)

| Token | Size | Use |
|---|---|---|
| `--fs-xs` | 12px | Mono eyebrows, metadata |
| `--fs-sm` | 14px | Body small |
| `--fs-base` | 15px | Body default |
| `--fs-md` | 18px | Lead paragraphs |
| `--fs-lg` | 24px | Section headings |
| `--fs-xl` | 36px | Section titles |
| `--fs-2xl` | 56px | Page hero (display) |
| `--fs-3xl` | 84px | Hero spectacle (display) |

### Type rules

- All headlines in `--display` are UPPERCASE with letter-spacing 0.04em
- Eyebrows always mono, ALL CAPS, letter-spacing 0.22em, 11px
- Mono specs (C-90, 192KHZ, 24BIT) live in `--fs-xs` with letter-spacing 0.14em
- Handwritten notes in `--hand` are italic by default
- Body text ratio: 6:1 minimum contrast on dark

---

## 4. Layout grid

### Page structure

```
┌─────────────────────────────────────────────────────┐
│ topbar (full bleed, backdrop-blur)                  │
│ sonic-studio · /mixtape '85 · ⌘K         [SIDE A · C-90]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  hero (96px padding)                                │
│  ┌──────────┐ ┌─────────────────────────────────┐   │
│  │ col 1-3  │ │ col 4-12 (hero cassette)         │   │
│  │ (eyebrow,│ │                                 │   │
│  │  lede,   │ │                                 │   │
│  │  CTAs)   │ │                                 │   │
│  └──────────┘ └─────────────────────────────────┘   │
│                                                     │
├─────────────────────────────────────────────────────┤
│ section (96px gap)                                  │
│  /section-name · eyebrow                            │
│  SECTION HEADLINE (display, uppercase)              │
│  ─── section underline (4px gradient) ───           │
│  [content grid]                                     │
├─────────────────────────────────────────────────────┤
│ footer (mono, 11px, /SONIC-STUDIO · TEMPLATE 14B)  │
└─────────────────────────────────────────────────────┘
```

### Numbers

- **Page max width:** 2880px (Penpot source-of-truth; live HTML at 1440px)
- **Page margin:** 64px (chassis), 48px (mobile)
- **Section gap:** 56px
- **Within-section gap:** 24px
- **Card padding:** 32px
- **Cassette-card aspect ratio:** 1:1 (square covers)
- **Hero cassette aspect ratio:** 16:9 (widescreen hero)

### Responsive

- **Mobile <768px:** topbar collapses to icon-only; hero stacks vertically; grid columns 1
- **Tablet 768-1440px:** 4-col grid; hero cassette 60% width
- **Desktop >1440px:** 6-col grid; hero cassette 60% width, lede 40%

**The hero is ALWAYS 60/40 split — cassette dominant, lede supportive.** Never the other way around.

---

## 5. Components

### Cassette cover (the primary content unit)

```
┌─────────────────────┐
│ ▣ A · CHOSEN         │  ← tag (top-left, 10px mono, opaque pill)
│                     │
│    [real photo]     │  ← full-bleed cassette photograph
│                     │
│                     │
│ 01 · HALF-LIGHT HRS │  ← bottom band, display caps, color-band label
└─────────────────────┘
```

- Aspect ratio 1:1
- Image: real AI-generated cassette photograph
- Tag: top-left, pill-shaped, `rgba(0,0,0,.7)` background, `padding: 6px 12px`
- Color band: bottom 0, full-width, `padding: 16px`, `font-family: var(--display)`, `font-size: 18px`, letter-spacing 0.08em, uppercase
- Color band bg: token from cassette label palette (--red / --yellow / etc.)
- Color band text: black on light bands (yellow/cyan), white on dark bands (red/blue/violet)

### Topbar

```
sonic-studio / mixtape '85 · design system    [▷ SIDE A · C-90]    [▷ PRESS PLAY] [⌘K]
```

- Full bleed, `padding: 16px 22px`
- Background: `rgba(0,0,0,.4)` with `backdrop-filter: blur(20px)`
- Left: crumb (mono, 13px)
- Center: status pill (mono, 11px, ALL CAPS, with dot indicator)
- Right: action buttons (mono, 12px, glass-pill)

### Cassette label band (the primary accent)

Each variant uses one color band as its identity. The cover gallery shows 4 covers, each with a different band. The user picks one. The chosen band becomes the album's identity color.

### Pipeline cell (12-layer)

- Default: `rgba(255,255,255,.02)` background, 1px `var(--rule)` border
- Done: linear-gradient(135deg, `rgba(255,123,0,.15)`, `rgba(242,92,176,.15)`), border `rgba(255,123,0,.4)`, label `var(--amber)`
- Active: linear-gradient(135deg, `rgba(45,216,240,.18)`, `rgba(185,74,245,.18)`), border `rgba(45,216,240,.45)`, label `var(--cyan)`
- Blocked: `rgba(255,255,255,.05)`, border `var(--rule-strong)`, label `var(--ink-soft)`

### Voice card

- 3-column grid: portrait (96px circular) | info | play button
- Portrait: full-bleed real photo, 96px circle
- Name: `var(--display)`, 18px, uppercase
- Description: `var(--hand)`, 16px, italic
- Play button: 48px circle, `rgba(255,255,255,.04)` background, `▷` glyph

### Album card

- Top: aspect-ratio 1:1 cover image
- Bottom: 3-line metadata (number mono, title display, meta mono)

### Status pill

- `display: inline-flex; gap: 8px; align-items: center;`
- Padding `8px 14px`, border-radius `999px`
- Mono 11px, ALL CAPS, letter-spacing 0.14em
- Yellow tint (`rgba(240,197,60,.08)` border, `rgba(240,197,60,.3)` background)
- Color: `var(--yellow)`
- With dot indicator (6px circle, `box-shadow: 0 0 8px var(--yellow)`)

---

## 6. Motif

The cassette itself is the motif. Specifically:

- The **cassette tape** (real object, color-banded label) is the only repeated visual element
- The **wall of tapes** (multiple cassettes arranged together) is the visual for "many albums"
- The **stacked tapes** is the visual for "this studio's history"
- The **handheld cassette** is the visual for "personal connection"

**What it is NOT:** not a half-lit window (that was editorial zine), not a neon aurora (that was cassette-mesh), not a hand-drawn cassette icon (too generic).

---

## 7. Motion

Restraint. Cassettes are physical objects, not animated ones.

- **Default:** static
- **Hero cassette:** subtle 3s rotate via `animation: hero-float 3s ease-in-out infinite` (rotate -2deg → 2deg)
- **Color band:** subtle 4s hue drift via `filter: hue-rotate()` (alternate direction)
- **On hover (cards):** scale 1 → 1.02, 200ms ease-out
- **On hover (buttons):** translate-y 0 → 2px, 180ms ease-out

**The 4 CSS animation primitives** are documented separately at `site/premium-cassette-animations.html` and rendered as animated GIFs in `assets/premium-animations/`:
1. Mesh drift (12s linear hue-rotate)
2. Reel spin (4s linear rotate)
3. Typewriter (4s steps(16) typing)
4. Pulse glow (2s ease-in-out box-shadow)

---

## 8. Accessibility

- Body text: `--ink` on `--bg` = 16.5:1 (AAA)
- Cassette label bands: tested per WCAG AA on each band color
- Cassette tag pills: tested contrast on dark
- All interactive elements: 2px solid `var(--yellow)` focus ring, offset 2px
- Skip-to-content link as first focusable element
- Cassette labels: alway image + alt text, alt text uses the album title
- Status conveyed via text + icon (not color alone)

---

## 9. Files this DESIGN.md drives

| File | Token consumers |
|---|---|
| `assets/premium-mixtape85-design-system.png` | All tokens (palette, type, layout, components) |
| `site/premium-cassette-animations.html` | All tokens + animation primitives |
| `assets/premium-animations/01-mesh-drift.gif` | Mesh drift primitive |
| `assets/premium-animations/02-reel-spin.gif` | Reel spin primitive |
| `assets/premium-animations/03-typewriter.gif` | Typewriter primitive |
| `assets/premium-animations/04-pulse-glow.gif` | Pulse glow primitive |
| `assets/premium-mockup-01-design-system.png` | Premium cassette-mesh variant |
| `assets/premium-mockup-04-dashboard.png` | Premium cassette-mesh variant |
| `references/ref-01..06` | 6 user reference images |
| `README.md` | References this file for visual rules |

---

## 10. Legacy designs (kept for reference, NOT active)

These designs exist in Penpot but are NOT the active direction:

- **Original cassette-mesh (6 pages):** 01 Design System, 02 Components, 03 Intake, 04 Dashboard, 05 Cover Exploration, 06 Motif Library. Aurora-mesh on dark, Major Mono Display headlines. Locked as a **secondary alternative** in case the user wants to revert.
- **Premium cassette-mesh (2 pages):** Premium 01 Design System, Premium 04 Dashboard. Same vocabulary as cassette-mesh but with real AI-generated photography. Locked as a tertiary alternative.
- **Editorial Zine (frozen 2026-07-28):** cream paper, serif typography, draftable layouts. GONE — the user explicitly rejected it on 2026-08-05.

**Active direction: Mixtape '85. Do not resurrect unless the user explicitly asks.**

---

## 11. What this DESIGN.md is NOT

- Not a Figma file (we ship code, not design specs in PDFs)
- Not a per-page wireframe (the layout grid covers structure)
- Not a content doc (the intake + dashboard UX specs live elsewhere)
- Not an "everything is editable" doc — the locked colors and type scale are locked
