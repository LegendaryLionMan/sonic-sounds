# DESIGN.md — album-studio

> The visual identity for the album-studio project: an HTML front door for
> the music-album-planning-questionnaire and full-album-release-package skills.
>
> Direction locked: **Editorial / zine** — warm paper, big serif, indie-press feel.
> Inherits from the Half-Light Hours / Maren Sol visual world.

---

## 1. Why this direction

Albums are narrative artifacts. The site that fronts the album-creation pipeline
should feel like **an editor's desk** — not a SaaS dashboard, not a form-builder.

References that informed this direction:
- **Half-Light Hours** album packaging (2026-06-25): warm paper, half-lit window motif
- **Sufjan Stevens / Carrie & Lowell** zine-era press kit
- **Bon Iver 22, A Million** minimal editorial typography
- **Editorial design system** (Open Design `od://design-systems/editorial`)

What it is NOT:
- Not a SaaS dashboard (no Tailwind-style card grids)
- Not a Spotify-clone (no green/black gradients)
- Not a music-tech VC landing page (no neon, no animated meshes)

---

## 2. Color palette

Derived from Half-Light Hours artwork, anchored in warm paper + ink.

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#F4EFE6` | Primary background — warm off-white |
| `--ink` | `#1B1714` | Primary text — near-black warm |
| `--ink-soft` | `#3D3530` | Secondary text |
| `--rule` | `#C9BFAE` | Hairlines, dividers, borders |
| `--accent` | `#B8503A` | One accent only — warm terracotta red (covers CTA, status critical, motif emphasis) |
| `--accent-soft` | `#D9846F` | Hover states, accent wash |
| `--highlight` | `#E8D9A8` | Pinned/highlighted content (mandatory-tier tags) |
| `--status-done` | `#4A6B47` | Status: done / approved (muted forest, not bright green) |
| `--status-active` | `#B8503A` | Status: in-progress (same as accent — intentional, in-progress is the signal) |
| `--status-blocked` | `#7A1F1F` | Status: blocked (deep oxblood) |

**Rule:** only ONE accent color in any single view. No gradients. No drop shadows on flat surfaces (only on raised cards).

---

## 3. Typography

Three families, all serif, all on the warm-paper background.

| Token | Family | Use |
|---|---|---|
| `--serif-display` | `"Cormorant Garamond", "EB Garamond", Georgia, serif` | Hero headings, section titles (weight 500, italic for "phase" indicators) |
| `--serif-body` | `"Lora", "Source Serif Pro", Georgia, serif` | Body copy, questions, lyrics excerpts (weight 400, line-height 1.7) |
| `--sans-mono` | `"JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace` | Metadata, filenames, status badges, the "NN" track numbers (weight 400, letter-spacing 0.02em) |

**Type scale (modular, ratio 1.333 — perfect fourth):**

| Token | rem | Use |
|---|---|---|
| `--fs-xs` | 0.75rem (12px) | Metadata, footnotes, mono labels |
| `--fs-sm` | 0.875rem (14px) | Secondary text, helper |
| `--fs-base` | 1.0625rem (17px) | Body — slightly larger than browser default for editorial feel |
| `--fs-md` | 1.25rem (20px) | Lead paragraphs |
| `--fs-lg` | 1.75rem (28px) | Sub-headings |
| `--fs-xl` | 2.75rem (44px) | Section titles |
| `--fs-2xl` | 4.25rem (68px) | Page hero |
| `--fs-3xl` | 6.5rem (104px) | Display — only on the intake hero and dashboard header |

**Rules:**
- Body text NEVER goes below `--fs-base`.
- Italic only for `--serif-display` (the editorial convention).
- ALL CAPS only on `--sans-mono` labels and metadata, with `letter-spacing: 0.08em`.
- No bold; we lean on weight + size contrast.

---

## 4. Layout grid

Editorial zines use a **12-column grid with an asymmetric content rail**. We mimic that:

```
┌─────────────────────────────────────────────────────┐
│ masthead (full bleed, hairline border-bottom)      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐ ┌─────────────────────────────────┐   │
│  │ col 1-4  │ │ col 5-12                        │   │
│  │ (meta)   │ │ (content)                       │   │
│  │          │ │                                 │   │
│  │ y-axis   │ │ x-axis reading flow             │   │
│  │ labels:  │ │                                 │   │
│  │ ────     │ │                                 │   │
│  │ ALBUM    │ │                                 │   │
│  │ STATUS   │ │                                 │   │
│  │ ────     │ │                                 │   │
│  │ LAYER 03 │ │                                 │   │
│  │ IN-REV   │ │                                 │   │
│  └──────────┘ └─────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

- **Page max width:** 1180px (sits comfortably inside 1440px desktop)
- **Page margin:** clamp(24px, 4vw, 64px) — paper-like edge breathing
- **Section gap:** 96px (loose, editorial)
- **Within-section gap:** 24px
- **Hairlines:** 1px `--rule`, never thicker

**Mobile breakpoint:** at <768px viewport, the left "meta column" collapses to top of section as a chip row.

---

## 5. Motif

The motif is a **half-lit window** — same one as Half-Light Hours.

Why keep the same motif across the studio and the album it produces:
- Consistency: the studio and the album feel like one artifact
- Recall: anyone who's seen Half-Light Hours recognizes the studio
- Proven: the motif already worked for a release, it's not invented for this site

**Motif usage on the site:**
- Subtle SVG corner mark in the masthead (a single 1px-line rectangle with a diagonal half-light gradient inside)
- A thin horizontal hairline with a small terracotta dot at the right edge — visual punctuation between sections
- A footer motif: the studio name in display serif, half-italicized

**What it is NOT:** not a watermark on every page, not a hero illustration. Subtle presence, not loud.

---

## 6. Components

Reusable building blocks. Same DNA across both pages.

### Card
- 1px `--rule` border, no border-radius (editorial zines don't round)
- `--paper` background (no white cards on warm paper — they feel wrong)
- 32px padding
- Optional: thin terracotta dot in top-right when status is "blocked" or "needs-review"

### Status badge
- `--sans-mono`, `--fs-xs`, ALL CAPS
- Three states:
  - `TODO` — `--ink-soft` text, `--rule` border
  - `IN-PROGRESS` — `--accent` text, `--accent` border
  - `DONE` — `--status-done` text, `--status-done` border
  - `BLOCKED` — `--status-blocked` text, `--status-blocked` border

### Question row (intake)
- Number on the left in `--sans-mono` (e.g. `M·03`)
- Tier tag (mandatory / recommended / extra) on the right
- Question text in `--serif-display`, italic
- Free-text input or select below, full-width within the content rail

### Layer card (dashboard)
- Layer number + name in `--serif-display`
- Status badge in top-right
- One-line summary in `--serif-body`
- Footer with: last-updated timestamp, "open layer →" link

### Hairline divider
- 1px `--rule`, with optional terracotta dot at right edge

---

## 7. Motion

Restraint. Editorial sites feel expensive because they don't move much.

- **Default:** static
- **On hover (links):** 1px underline shifts to terracotta, 120ms ease-out
- **On hover (cards):** border color shifts to `--accent`, no transform
- **On form submit:** the page fades in confirmation over 240ms ease-out
- **Never:** parallax, scroll-driven transforms, animated gradients

---

## 8. Accessibility

- Body text contrast ratio: `--ink` on `--paper` = 13.6:1 (AAA)
- All interactive elements: 2px solid `--accent` focus ring, offset 2px
- Skip-to-content link as first focusable element
- Form labels always associated with inputs (no placeholder-as-label)
- Status conveyed via text + icon (not color alone)

---

## 9. Files this DESIGN.md drives

| File | Token consumers |
|---|---|
| `site/intake.html` | All tokens (palette, type, layout, motif, components, motion) |
| `site/dashboard.html` | All tokens |
| `README.md` | References this file for visual rules |

---

## 10. What this DESIGN.md is NOT

- Not a Figma file (we ship code, not design specs in PDFs)
- Not a per-page wireframe (the layout grid covers structure)
- Not a content doc (the intake + dashboard UX specs live elsewhere)

