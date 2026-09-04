# sonic-studio · Theme System

> World-class 6-theme design system, Mixtape '85 era (v3.5).
> Built around Omarchy's official themes + a bespoke sonic-studio Mixtape '85.

## 1. Architecture

### 1.1 Files

| File | Role |
|---|---|
| `site/themes.css` | All 6 themes as `:root[data-theme="..."]` blocks. Loads on every page before any other stylesheet. |
| `site/themes.js` | Sets `document.documentElement.dataset.theme` from localStorage. Listens for `theme:change` events. Provides a `Themes` API for the picker. |
| `site/theme-picker.js` | Renders the picker dropdown (mounted in the topbar). |
| `site/themes/DESIGN.md` | This file. |
| `site/themes/palettes.json` | Canonical 16-color + extra palette per theme, used as the source of truth and for documentation generation. |

### 1.2 CSS token shape

Every theme defines the same semantic tokens. There are **never** raw hex values in component code — only `var(--ink)`, `var(--accent)`, etc.

#### Surface tokens (backgrounds)
```
--bg              page background
--bg-soft         sidebar / drawer / cards-on-page
--bg-elevated     hover state on a card; header player backdrop
--bg-overlay      modal scrim
--surface         input field background
--surface-raised  popover background
```

#### Ink tokens (text)
```
--ink             primary text
--ink-soft        secondary text (labels, captions)
--ink-muted       tertiary text (timestamps, fine print)
--ink-faint       placeholder text
--ink-inverse     text on accent / accent-2 backgrounds
```

#### Accent tokens (interactive / brand)
```
--accent          primary accent (the "Mixtape yellow" in Mixtape '85)
--accent-2        secondary accent (the "Mixtape cyan")
--accent-3        tertiary accent (used sparingly: tag pills, role badges)
--accent-fg       foreground on accent backgrounds
--accent-soft     tinted background derived from --accent
```

#### State tokens
```
--success         green for OK/done
--warn            yellow for in-progress
--danger          red for blocked / errors
--info            blue for hints
--rule            hairlines
--rule-strong     more visible dividers
```

#### Type tokens
```
--display         display heading (Bebas Neue in Mixtape, Oswald elsewhere)
--sans            body sans (Inter)
--mono            monospace (JetBrains Mono)
--hand            handwriting (Caveat)
--font-scale      multiplicative scale factor (default 1)
```

#### Animation tokens
```
--t-quick         100ms — small interactions (hovers)
--t-base          200ms — buttons, focus rings
--t-slow          320ms — theme transitions, larger moves
--t-spring        cubic-bezier(0.18, 0.89, 0.32, 1.28) — pop, bounce
```

#### Album cover decoration
```
--cover-frame     outline around album cover thumbnails
--cover-fade      mask at top of long album lists
```

### 1.3 Theme switch flow

1. User opens the theme picker (top-right, in the topbar).
2. Sees 6 swatches: each row shows theme name + 3 dot swatches (bg, accent, accent-2) + a one-line description.
3. Hovers → live preview (CSS transition 320ms — `document.documentElement.dataset.theme` is set to the new value; transition only runs once on hover, **not** while the picker is open, so we don't burn CPU).
4. Clicks → committed to localStorage; the transition plays once.
5. Theme choice is also broadcast on `window` as an event so other components (e.g. the cassette artwork, the topbar pill) can react.

### 1.4 Persistence

```js
localStorage["sonic-studio:theme"] = {
  "v": 1,
  "theme": "mixtape85",
  "appliedAt": 1700000000000
}
```

`themes.js` reads on `DOMContentLoaded`, applies immediately to avoid flash. If the stored theme is unknown (corrupt or renamed), falls back to `mixtape85`.

### 1.5 Accessibility

- All themes meet WCAG AA contrast (4.5:1 for normal text, 3:1 for large text) verified via the `--ink` on `--bg` combination.
- Theme toggle respects `prefers-reduced-motion` — transitions become instant.
- Picker dropdown is keyboard-navigable (Tab, Enter, Escape, arrow keys).
- `aria-live="polite"` announcement when theme changes.

## 2. Themes

### 2.1 Mixtape '85 (the MAIN theme — built from the albums-page aesthetic)

**Identity.** Warm yellow + cyan on near-black. Cassette-era analog warmth. Display type is Bebas Neue, body is Inter.

```
--bg:           #0a0a0f   near-black
--bg-soft:      #14141a   sidebar
--bg-elevated:  #1a1a22   card hover
--ink:          #fafafa   white text
--ink-soft:     rgba(255,255,255,.7)
--ink-muted:    rgba(255,255,255,.4)
--accent:       #f0c53c   Mixtape yellow
--accent-2:     #2dd8f0   Mixtape cyan
--accent-3:     #f25cb0   hot pink (decoration)
--accent-fg:    #14141a   dark text on yellow
--success:      #4caf50
--warn:         #f0c53c
--danger:       #e83a3a
--info:         #2dd8f0
--rule:         rgba(255,255,255,.08)
--rule-strong:  rgba(255,255,255,.18)
```

### 2.2 Tokyo Night (Omarchy official)

**Identity.** Calm nocturnal deep-blue with soft pastel syntax. Inspired by Tokyo city lights at night.

**Source:** [omarchytheme.com/themes/tokyo-night](https://omarchytheme.com/themes/tokyo-night), confirmed.

```
--bg:           #1a1b26
--bg-soft:      #16161e
--bg-elevated:  #1f2335
--ink:          #c0caf5
--ink-soft:     #a9b1d6
--ink-muted:    #565f89
--accent:       #7aa2f7   blue
--accent-2:     #bb9af7   purple
--accent-3:     #7dcfff   sky
--accent-fg:    #1a1b26
--success:      #9ece6a
--warn:         #e0af68
--danger:       #f7768e
--info:         #7dcfff
--rule:         #292e42
--rule-strong:  #3b4261
```

### 2.3 Catppuccin Latte (Omarchy official, LIGHT)

**Identity.** Warm pastel light theme. Daytime, reading-friendly. Soft pinks, blues, greens.

**Source:** [catppuccin/palette](https://github.com/catppuccin/palette), confirmed full 26-color palette.

```
--bg:           #eff1f5   base
--bg-soft:      #e6e9ef   mantle
--bg-elevated:  #dce0e8   crust
--ink:          #4c4f69   text
--ink-soft:     #5c5f77   subtext1
--ink-muted:    #6c6f85   subtext0
--accent:       #1e66f5   blue
--accent-2:     #8839ef   mauve
--accent-3:     #fe640b   peach
--accent-fg:    #eff1f5
--success:      #40a02b   green
--warn:         #df8e1d   yellow
--danger:       #d20f39   red
--info:         #04a5e5   sky
--rule:         #ccd0da   surface0
--rule-strong:  #bcc0cc   surface1
```

### 2.4 Gruvbox Dark (Omarchy official)

**Identity.** Warm retro amber-on-warm-black. Cave-light, den-studio vibe.

**Source:** [omarchytheme.com/themes/gruvbox](https://omarchytheme.com/themes/gruvbox), confirmed.

```
--bg:           #282828   bg0
--bg-soft:      #1d2021   bg0_h
--bg-elevated:  #3c3836   bg1
--ink:          #ebdbb2   fg
--ink-soft:     #d4be98   fg2
--ink-muted:    #a89984   gray
--accent:       #fabd2f   yellow
--accent-2:     #83a598   blue (Gruvbox's "blue")
--accent-3:     #fb4934   bright red
--accent-fg:    #282828
--success:      #b8bb26   green
--warn:         #fabd2f
--danger:       #fb4934
--info:         #83a598
--rule:         #3c3836
--rule-strong:  #504945
```

### 2.5 Everforest (Omarchy official)

**Identity.** Forest greens, cream, warm rust. Acoustic, organic, outdoors.

**Source:** [omarchytheme.com/themes/everforest](https://omarchytheme.com/themes/everforest), confirmed.

```
--bg:           #2d353b
--bg-soft:      #232a2e
--bg-elevated:  #343f44
--ink:          #d3c6aa
--ink-soft:     #9da9a0
--ink-muted:    #7a8478
--accent:       #7fbbb3   sage teal
--accent-2:     #a7c080   leaf green
--accent-3:     #d699b6   mauve
--accent-fg:    #2d353b
--success:      #a7c080
--warn:         #dbbc7f
--danger:       #e67e80
--info:         #7fbbb3
--rule:         #3d484d
--rule-strong:  #475258
```

### 2.6 Kanagawa (Omarchy official)

**Identity.** Sumi-e ink painting meets wave-blue Japanese aesthetic. Sharp, ink-on-paper.

**Source:** [omarchytheme.com/themes/kanagawa](https://omarchytheme.com/themes/kanagawa), confirmed.

```
--bg:           #1f1f28
--bg-soft:      #16161d
--bg-elevated:  #2a2a37
--ink:          #dcd7ba   sumi-ink
--ink-soft:     #c8c093
--ink-muted:    #625e5a
--accent:       #7fb4ca   wave blue
--accent-2:     #b6927b   bocha (warm rust)
--accent-3:     #d27e99   sakura pink
--accent-fg:    #1f1f28
--success:      #87a987
--warn:         #e6c384
--danger:       #c34043
--info:         #7fb4ca
--rule:         #2a2a37
--rule-strong:  #363646
```

## 3. Theme Picker UX

```
┌─────────────────────────────────────────┐
│  ▾ theme                                │
├─────────────────────────────────────────┤
│  ●  Mixtape '85        [yellow] [cyan]  │ ← current
│  ○  Tokyo Night       [bg] [blue]       │
│  ○  Catppuccin Latte  [cream] [blue]    │
│  ○  Gruvbox           [warm] [yellow]   │
│  ○  Everforest        [forest] [sage]   │
│  ○  Kanagawa          [ink] [wave]      │
└─────────────────────────────────────────┘
```

- Open: click on the theme chip in the topbar (next to "⌘K").
- Switch: click anywhere on a row → 320ms transition plays.
- Keyboard: `Tab` to focus the chip, `Enter` or `Space` to open, `↑↓` to navigate rows, `Enter` to commit, `Escape` to close.
- Mouse hover does NOT preview (per design decision: too disorienting + wasted CPU). Click commits.

## 4. Component coverage

Every component must work in every theme. Validation: `tests/test_theme_coverage.py` checks that the following classes exist in `site/themes.css` with each theme variant:

- `.topbar`, `.pill`, `.cmd`, `.crumb`
- `.eyebrow`, `.h1`, `.h2`, `.p`
- `.card`, `.card:hover`, `.card-frame`
- `.btn-primary`, `.btn-ghost`, `.btn-danger`
- `.header-player` and all `.hp-*` children
- `.status-active`, `.status-paused`, `.status-done`, `.status-blocked`
- `.theme-switch` / theme picker itself

(Plus visual verification via `desktop_preview` on each theme — see `tools/theme-tour.py`.)
