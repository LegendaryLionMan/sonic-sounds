# album-studio · UI/UX Improvement Schedule (Omarchy-Inspired)

> **Goal**: 10 UI/UX improvements per iteration, with a web-research + implement + test loop. Each iteration ships one batch of improvements and updates this file with what was researched, built, and what comes next.
>
> **Mode**: 100% autonomous. Run this loop hourly until all 10 hours are done.
>
> **Started**: 2026-09-03

---

## Loop Protocol (every iteration)

1. **Research**: web search for current design patterns / references
2. **Ideate**: produce 10 new ideas specific to album-studio
3. **Pick & Implement**: ship 1-3 of the ideas per iteration (scope-fit)
4. **Test**: pytest + e2e (4 suites, 185 verifications) — must all pass
5. **Commit**: incremental commits with `ui(<area>): hour N — <description>`
6. **Update this file**: mark the idea as ✅ done, add the new idea to the backlog
7. **Hand off** (end-of-iteration): next session picks up here

---

## Iteration 1 (hour 1) — Theme switcher [DONE]

**Research**: Omarchy v4.0 release notes — live theme preview, semantic color tokens, theme carousel UX; also Liquid Glass Design gallery patterns.

**10 ideas generated (hour 1)**:
1. ✅ **4-theme switcher** (Mixtape '85 / Tokyo Night / Catppuccin / Gruvbox) — done
2. ✅ Live preview swatch dock (gradient chips) — done
3. ✅ localStorage persistence — done
4. ✅ CSS variable overrides for semantic tokens — done
5. ✅ ARIA radiogroup + radio — done
6. ✅ `prefers-reduced-motion` — done
7. ⏳ Filterable theme carousel (Omarchy v4.0 feature) — backlog
8. ⏳ Theme color picker for accent — backlog
9. ⏳ Per-theme font-family — backlog
10. ⏳ Theme-from-wallpaper (extract palette from image) — backlog

---

## Iteration 2 (hour 2) — Cassette wall animations [DONE]

**Research**: Omarchy's deliberate-beat, uncorrelated-periods background; CSS animation patterns.

**10 ideas generated (hour 2)**:
1. ✅ **Drifting background** (radial gradients, 15s/13s uncorrelated) — done
2. ✅ **Magnetic hover tilt** (cursor → --tilt-x/y CSS vars, max 6°) — done
3. ✅ Vinyl shine ring on hover (conic gradient spin) — done
4. ✅ Card entrance stagger (80ms apart, 6 children) — done
5. ✅ Topbar entrance animation — done
6. ✅ `prefers-reduced-motion` — done
7. ⏳ Scroll-driven parallax on album cover — backlog
8. ⏳ Filter pills (active / paused / done) with stagger — backlog
9. ⏳ Track list reveal animation — backlog
10. ⏳ "Add new album" CTA with pulse animation — backlog

---

## Iteration 3 (hour 3) — Spring-physics + 2026 motion patterns [IN PROGRESS]

**Research** (web search "music player UI 2026 design patterns glassmorphism micro-interactions"):
- Creative Alive "Micro-Interactions in 2026": Spring physics on every tactile control. Haptic-style visual feedback. Scroll-linked timelines. Choreographed state transitions.
- Tim Graf 2026: Glassmorphism vs Neumorphism guide. Parallax depth.
- Liquid Glass gallery: Audio player cards with liquid-glass effects.

**10 ideas generated (hour 3)**:
1. 🚧 **Spring-physics button press** (cubic-bezier(.34, 1.56, .64, 1) for bouncy; CSS tokens --spring-bouncy/--spring-soft/--spring-snappy) — IN PROGRESS, file created
2. ⏳ Haptic 120ms scale-down-and-back on INVOKE/▷/PAUSE — backlog
3. ⏳ Status pill with state-transition color morph — backlog
4. ⏳ Decision cards with staggered reveal (elastic overshoot from right) — backlog
5. ⏳ Modal/drawer with spring-soft slide-in — backlog
6. ⏳ Audio progress bar with elastic snap — backlog
7. ⏳ Album cover 3D hover with shimmer reflection — backlog
8. ⏳ Scroll-linked parallax on topbar (`@scroll-timeline`) — backlog
9. ⏳ View Transitions API for page navigation (cross-page morph) — backlog
10. ⏳ Track play button with reactive fill animation — backlog

---

## Iteration 4 (hour 4) — Audio waveform visualization [TODO]

**Research plan**: Canvas-based waveform rendering. Web Audio API's `AnalyserNode` for real-time FFT. Dribbble references.

**10 ideas to generate** (placeholder):
1. ⏳ Live canvas waveform during MP3 playback
2. ⏳ Static waveform pre-render from MP3 header (no JS audio decode)
3. ⏳ Color-shifted waveform tied to accent
4. ⏳ Click-to-seek with waveform scrubbing
5. ⏳ Hover-to-preview track position
6. ⏳ Volume slider with haptic snap
7. ⏳ EQ visualization (3-band)
8. ⏳ Track progress ring (radial)
9. ⏳ Lyrics sync animation
10. ⏳ BPM detection + tempo display

---

## Iteration 5 (hour 5) — Command palette (super+K) [TODO]

**Research plan**: Omarchy v4.0 command palette (filterable, nested, JSONC-extensible). Raycast's UI.

**10 ideas to generate**:
1. ⏳ Command palette overlay (super+K)
2. ⏳ Search albums/sessions/tracks/decisions
3. ⏳ Fuzzy match scoring
4. ⏳ Recent commands history
5. ⏳ Keyboard-only navigation
6. ⏳ Action shortcuts (build → invoke, pause/resume)
7. ⏳ Theme switch from palette
8. ⏳ Help palette (?)
9. ⏳ Filter pills (albums only / sessions only)
10. ⏳ Custom command registration via data attr

---

## Iteration 6 (hour 6) — Glassmorphism modals + drawers [TODO]

**Research plan**: Liquid Glass gallery (backdrop-filter, layered depth).

**10 ideas to generate**:
1. ⏳ Modal with backdrop-filter blur
2. ⏳ Drawer with parallax depth
3. ⏳ Album cover with glass reflection overlay
4. ⏳ Status pill with glass background
5. ⏳ Tooltip with glass surface
6. ⏳ Confirm dialog with spring entrance
7. ⏳ Sidebar with frosted glass
8. ⏳ Toast with glass surface
9. ⏳ Audio player controls with glass
10. ⏳ Decision-card hover with glass reflection

---

## Iteration 7 (hour 7) — Hover micro-interactions on every card [TODO]

**Research plan**: Haptic-style visual feedback, scale-on-hover, ripple effects.

**10 ideas to generate**:
1. ⏳ Album card lift on hover (already have)
2. ⏳ Track row hover with play button reveal
3. ⏳ Decision card hover with edit button reveal
4. ⏳ Event row hover with timestamp highlight
5. ⏳ Pipeline cell hover with phase tooltip
6. ⏳ Asset card hover with preview expand
7. ⏳ Modal/drawer close button hover
8. ⏳ Status pill hover with quick-action menu
9. ⏳ Footer meta hover with detail expand
10. ⏳ Toast hover with dismiss button

---

## Iteration 8 (hour 8) — Toast system with progress bar [TODO]

**Research plan**: OSD-style ephemeral feedback. Animated progress.

**10 ideas to generate**:
1. ⏳ Replace static toast with animated slide-in
2. ⏳ Toast with progress bar (build_started → running → done)
3. ⏳ Toast stack with auto-dismiss
4. ⏳ Toast with action button (Undo)
5. ⏳ Toast with semantic colors (success/error/info)
6. ⏳ Toast with custom icon (per kind)
7. ⏳ Toast with sticky mode (until clicked)
8. ⏳ Toast with hover-to-pause
9. ⏳ Toast queue (FIFO)
10. ⏳ Toast with sound (optional toggle)

---

## Iteration 9 (hour 9) — Page transitions + skeleton loaders [TODO]

**Research plan**: View Transitions API. Skeleton loaders for perceived performance.

**10 ideas to generate**:
1. ⏳ Page cross-fade via View Transitions API
2. ⏳ Skeleton loader for album cards (during fetch)
3. ⏳ Skeleton loader for track list
4. ⏳ Skeleton loader for pipeline
5. ⏳ Skeleton shimmer animation
6. ⏳ Smooth height transitions on content load
7. ⏳ Lazy-render album covers with blur-up
8. ⏳ Skeleton → real-content crossfade
9. ⏳ Progress bar for long operations
10. ⏳ Inline loading states (button → spinner)

---

## Iteration 10 (hour 10) — Animated build pipeline + keyboard shortcuts [TODO]

**Research plan**: Sequential cell light-up animation. Keyboard shortcuts overlay (`?`).

**10 ideas to generate**:
1. ⏳ Pipeline cells light up sequentially on invoke
2. ⏳ Layer 01 → 02 → 03 → ... cascade animation
3. ⏳ Keyboard shortcuts overlay (`?` opens help)
4. ⏳ Shortcut discoverability (chip on hover)
5. ⏳ Cmd+K palette (already in iteration 5)
6. ⏳ Cmd+1..9 jump to pipeline layer
7. ⏳ Cmd+/ search
8. ⏳ Esc dismiss modals
9. ⏳ Arrow keys navigate track list
10. ⏳ Spacebar play/pause

---

## Status

| Hour | Status | Commits | Tests added |
|---|---|---|---|
| 1 | ✅ done | `1d98f21` | 27 |
| 2 | ✅ done | (pending) | 8 |
| 3 | 🚧 in progress | (pending) | TBD |
| 4-10 | ⏳ TODO | — | — |

**Current test count**: 404 pytest + 2 skipped; 185 e2e verifications across 4 suites (UX contract 122 + Day 13-14 surfaces 47 + Playwright 16 + JS lint).

---

## Hand-off Notes (for next session)

- Start daemon: `python -m build.serve --host 127.0.0.1 --port 8765` (default port)
- Theme switcher is the visual baseline. Pick a theme in the bottom-left dock.
- Every iteration runs `python e2e/run_all.py` before commit — must all pass.
- Cache-bust scheme: `?v=hourN` on every script tag in studio.html, albums.html, library.html, intake.html.
- Static assets go in `site/`; tests in `tests/`; e2e in `e2e/`; docs in `docs/`.
- OneDrive mirror per R7: README/USER_MANUAL/TECHNICAL → `~/OneDrive/Hermes/Agents/planning/album-studio/`.
- Obsidian daily log: `~/Documents/Obsidian Vault/Hermes/9-daily/YYYY-MM-DD.md`.
