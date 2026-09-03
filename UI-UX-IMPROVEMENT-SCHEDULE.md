# album-studio · UI/UX Improvement Schedule (Omarchy-Inspired)

> **Goal**: 10+ UI/UX improvements inspired by Omarchy OS design language, with focus on animations + interactivity.
> **Mode**: 100% autonomous, hourly research + iteration cycle.

## Omarchy Design Cues Applied

| Cue | Description | Application |
|---|---|---|
| **Live theme preview** | Filterable carousel of theme previews | Theme switcher in studio footer |
| **Event-driven (no polling)** | Signals, not setInterval | Reactive state via CustomEvent |
| **Filterable command palette** | `super+space` opens app search | Command palette in studio |
| **Animated backgrounds** | Deliberate beat, uncorrelated periods | Cassette wall drift animation |
| **Theme semantic color system** | Normalized color names (bg/fg/accent) | CSS variables + 4 themes |
| **Fluid glass / blur** | Semi-transparent + backdrop-filter | Modal/drawer glass effect |
| **Visual progress for every action** | OSD-style ephemeral feedback | Toast system with progress |
| **Integrated corner controls** | Rounded/sharp toggle | Album card corner radius |
| **Display text-size knob** | One knob, one motion | Theme/font size selector |

## Schedule (Hourly Iterations)

| Hour | Focus | Deliverable | Status |
|---|---|---|---|
| 1 | Theme switcher (4 themes: Tokyo Night, Catppuccin, Gruvbox, Mixtape 85) with live preview | `site/theme-switcher.js` + 4 CSS theme files | done |
| 2 | Cassette wall drift animation + magnetic hover on cards | `site/library.js` animation + CSS | done |
| 3 | Command palette (`super+k`) — search albums, sessions, tracks, decisions | `site/command-palette.js` + global handler | done |
| 4 | Glass-morphism on modals/drawers + smooth slide-in/out | CSS update for `.album-cover` etc | done |
| 5 | Audio waveform visualization (Canvas-based, real-time) | `site/waveform.js` + canvas element | done |
| 6 | Hover micro-interactions (lift, glow, transform) on all cards | CSS :hover transitions | done |
| 7 | Toast system with progress bar (replaces the existing toast) | `site/toast.js` upgrade | done |
| 8 | Page transitions (fade/slide) + skeleton loaders | CSS + JS | done |
| 9 | Keyboard shortcuts overlay (`?` opens help) + accessibility | `site/shortcuts.js` | done |
| 10 | Animated build pipeline (cells light up sequentially on invoke) | `site/studio.js` update | done |

Each iteration: 1) research, 2) implement, 3) verify in Chrome, 4) commit, 5) run e2e.

## Cross-cutting concerns

- Every change MUST pass `python e2e/run_all.py` (159 verifications)
- Every change MUST pass the JS lint guard (no `$(...).forEach`)
- Aesthetic must align with Omarchy's "beautiful + productive" principle
- Dark-mode first (Omarchy defaults to Tokyo Night; album-studio's current Mixtape 85 dark is similar)
- Animations capped at 60fps with `prefers-reduced-motion` respected
