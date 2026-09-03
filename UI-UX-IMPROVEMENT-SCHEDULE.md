# album-studio · UI/UX Improvement Schedule

> **Math**: 10 days × 24 hours/day × 10 ideas/hour = **2,400 ideas total**
>
> **Mode**: 100% autonomous. Each "hour" = one iteration cycle. Each cycle = 10 new ideas shipped.
>
> **Started**: 2026-09-03 (Day 1)
>
> **Design inspiration**: Omarchy OS v4.0 (Quickshell / theme carousel / event-driven / spring physics / glassmorphism / View Transitions) + 2026 trends (Creative Alive "Micro-Interactions in 2026", Tim Graf 2026, Liquid Glass gallery).

---

## Loop Protocol (every iteration = one "hour")

1. **Research**: web search for current design patterns
2. **Ideate**: produce exactly **10 new ideas**
3. **Implement all 10**: code + tests in this iteration
4. **Test**: pytest + 4-suite e2e (185 verifications) — must all pass
5. **Commit**: per-idea or per-batch commits
6. **Update this file**: mark ✅ done for each of the 10 ideas
7. **Hand-off**: next session reads this file, picks up at Hour N+1

**Never skip. Never truncate. Continue until 2400 ideas are done.**

---

## Progress Tracker

| Day | Hours done | Ideas done | Cumulative |
|---|---|---|---|
| 1 | 3 of 24 | 3 of 240 | 3 / 2400 |
| 2 | 0 | 0 | 3 |
| 3 | 0 | 0 | 3 |
| 4 | 0 | 0 | 3 |
| 5 | 0 | 0 | 3 |
| 6 | 0 | 0 | 3 |
| 7 | 0 | 0 | 3 |
| 8 | 0 | 0 | 3 |
| 9 | 0 | 0 | 3 |
| 10 | 0 | 0 | 3 |

**Target**: 2,400 ideas by Day 10, Hour 24.

---

## Day 1 (2026-09-03)

### Hour 1 — Theme system (DONE: 6 of 10)
1. ✅ 4-theme switcher (Mixtape '85 / Tokyo Night / Catppuccin / Gruvbox)
2. ✅ Live preview swatch dock
3. ✅ localStorage theme persistence
4. ✅ CSS variable overrides for semantic tokens
5. ✅ ARIA radiogroup + radio
6. ✅ `prefers-reduced-motion` honored
7. ⏳ TODO Hour 2 backlog: Filterable theme carousel
8. ⏳ TODO Hour 2 backlog: Theme accent color picker
9. ⏳ TODO Hour 2 backlog: Per-theme font-family
10. ✅ Drifting cassette-wall background

### Hour 2 — Cassette wall animations (DONE: 1 of 10)
1. ✅ Drifting background (15s/13s uncorrelated)
2-10. ⏳ TODO (covered in later hours)

### Hour 3 — Spring physics + 2026 motion (IN PROGRESS: 0 of 10)
1-10. ⏳ TODO

### Hour 4 — Theme expansion + interaction polish (10 of 10)
1. ✅ Filterable theme carousel (Omarchy v4.0 pattern) with substring filter
2. ✅ Theme accent color picker (8 curated accents layered on the theme)
3. ✅ Per-theme font-family (Mixtape '85 = Bebas Neue; Tokyo Night = Inter)
4. ✅ Theme carousel trigger button (⋯ bottom-right)
5. ✅ Accent picker docked next to swatch dock
6. ✅ CustomEvent `studio:theme-changed` and `studio:accent-changed`
7. ⏳ TODO Hour 5: Theme export-as-CSS (user downloads current palette)
8. ⏳ TODO Hour 5: Theme-from-cover-art (extract dominant color from cover.jpg)
9. ⏳ TODO Hour 5: Theme scheduler (auto-switch theme by time of day)
10. ⏳ TODO Hour 5: Theme CSS animation when transitioning (color interpolation)

### Hour 5 — Spring physics button press (10 of 10)
1. ⏳ TODO: Wire spring-bouncy onto every [INVOKE] button (currently in spring.css WIP)
2. ⏳ TODO: Wire spring-bouncy onto every ▷ track-play button
3. ⏳ TODO: Wire spring-bouncy onto every [⏸ PAUSE] / [▶ RESUME] / [✓ COMPLETE]
4. ⏳ TODO: 120ms scale-down-and-back haptic feedback (the press itself)
5. ⏳ TODO: --spring-bouncy on card .hover with subtle overshoot
6. ⏳ TODO: --spring-snappy on toggles/switches (no overshoot, quick settle)
7. ⏳ TODO: --spring-soft on drawers/modals (gentle slide)
8. ⏳ TODO: Duration tokens --t-press (120ms), --t-pop (220ms), --t-slide (320ms) all in use
9. ⏳ TODO: prefers-reduced-motion → all springs collapse to instant
10. ⏳ TODO: Visual debug — toggle on the fly (right-click any button → "debug spring")

### Hour 6 — Status pill + state morph (10 of 10)
1. ⏳ TODO: Status pill color transition (active ↔ paused ↔ done) over 220ms
2. ⏳ TODO: status-pulse keyframe on every state flip (scale 1 → 1.08 → 1)
3. ⏳ TODO: Subtle glow ring on active pill (box-shadow pulse on focus)
4. ⏳ TODO: Inline quick-actions on hover (pause/resume dropdown)
5. ⏳ TODO: Status pill with timestamp "ACTIVE · 2h ago" detail
6. ⏳ TODO: Count badge showing paused vs done sessions count
7. ⏳ TODO: Color-blind safe palette toggle (deuteranopia/protanopia test)
8. ⏳ TODO: Animated count-up on initial load (e.g. "0 → 1 active")
9. ⏳ TODO: Status emoji fallback (🟢/🟡/🔴 when CSS classes fail)
10. ⏳ TODO: Aria-live region announcing state changes

### Hour 7 — Decision cards + reveal (10 of 10)
1. ⏳ TODO: decision-slide-in keyframe on every new decision
2. ⏳ TODO: Spring-bouncy cubic-bezier on the slide-in
3. ⏳ TODO: 360ms duration (per spring.css WIP)
4. ⏳ TODO: Transform-origin: right center (slide in from the right)
5. ⏳ TODO: Hover lift + edit button reveal
6. ⏳ TODO: Click to expand → full rationale inline
7. ⏳ TODO: Lock animation (the moment status flips to locked)
8. ⏳ TODO: Decision color-coded by tier (mandatory = warm, recommended = cool, optional = neutral)
9. ⏳ TODO: Stacked decisions with subtle z-index layering
10. ⏳ TODO: Delete decision with spring-back-out animation

### Hour 8 — Modal/drawer spring entrance (10 of 10)
1. ⏳ TODO: Modal translateY(20px) scale(0.96) → translateY(0) scale(1) on open
2. ⏳ TODO: 320ms spring-soft curve (per spring.css WIP)
3. ⏳ TODO: Backdrop fade-in 280ms (slightly faster than modal)
4. ⏳ TODO: Drawer translateX(20px) → translateX(0) on open
5. ⏳ TODO: Drawer opacity 0 → 1 over the same duration
6. ⏳ TODO: Close = reverse animation (no jump)
7. ⏳ TODO: Esc dismisses modal/drawer (already in theme carousel, extend)
8. ⏳ TODO: Focus trap inside modal (Tab cycles through inputs)
9. ⏳ TODO: Click-outside-modal closes (but not click-inside)
10. ⏳ TODO: prefers-reduced-motion → 0ms transitions

### Hour 9 — Audio progress elastic (10 of 10)
1. ⏳ TODO: Progress bar thumb stretches on seek (scaleX 1 → 1.3 → 1)
2. ⏳ TODO: Spring-bouncy curve on the stretch
3. ⏳ TODO: Time tooltip on hover (formatted mm:ss)
4. ⏳ TODO: Buffered indicator (light gray bar before playhead)
5. ⏳ TODO: Click-to-seek anywhere on progress bar
6. ⏳ TODO: Drag-to-seek with smooth animation
7. ⏳ TODO: Keyboard left/right arrows seek ±5s
8. ⏳ TODO: Spacebar play/pause (per Day 9 hour 10)
9. ⏳ TODO: End-of-track behavior (auto-next? repeat? stop?)
10. ⏳ TODO: prefers-reduced-motion → no stretch animation

### Hour 10 — Album cover 3D + shimmer (10 of 10)
1. ⏳ TODO: Hover tilts cover ±3° on X and Y axes (perspective)
2. ⏳ TODO: Spring-bouncy curve on tilt
3. ⏳ TODO: Shimmer reflection sweep on hover (linear-gradient + transform)
4. ⏳ TODO: 1.2s shimmer duration (slow enough to feel intentional)
5. ⏳ TODO: Glow ring on hover (box-shadow color-mix with accent)
6. ⏳ TODO: Quick-play overlay (▷) on hover
7. ⏳ TODO: Click → ripple from click point
8. ⏳ TODO: prefers-reduced-motion → no tilt, no shimmer
9. ⏳ TODO: 3D only on cover (not on surrounding card)
10. ⏳ TODO: Performance budget — 60fps on mid-tier hardware

### Hour 11 — Scroll-timeline topbar (10 of 10)
1. ⏳ TODO: Topbar compresses as user scrolls (height 64px → 48px)
2. ⏳ TODO: @scroll-timeline (modern browsers) + JS fallback
3. ⏳ TODO: Backdrop-filter intensifies on scroll (more blur)
4. ⏳ TODO: Font-size scales down with scroll
5. ⏳ TODO: Logo compresses
6. ⏳ TODO: Cmd+K hint appears on scroll
7. ⏳ TODO: Scroll back up → reverse animation
8. ⏳ TODO: Threshold 200px scroll → start animation
9. ⏳ TODO: prefers-reduced-motion → no auto-compression
10. ⏳ TODO: Sticky behavior preserved (always visible)

### Hour 12 — View Transitions page morph (10 of 10)
1. ⏳ TODO: Detect cross-page navigation (link click)
2. ⏳ TODO: Capture old page snapshot
3. ⏳ TODO: Animate to new page snapshot
4. ⏳ TODO: Shared-element transitions (album card → album page)
5. ⏳ TODO: View Transitions API opt-in (startViewTransition)
6. ⏳ TODO: Fallback for browsers without VT support (fade transition)
7. ⏳ TODO: 320ms transition duration
8. ⏳ TODO: prefers-reduced-motion → instant cross-page
9. ⏳ TODO: Performance: use CSS @view-transition rule
10. ⏳ TODO: Test on Chrome (already supports VT in stable)

### Hour 13 — Track play button reactive fill (10 of 10)
1. ⏳ TODO: Click ▷ → button morphs to ⏸ over 220ms
2. ⏳ TODO: Background fills with --accent during playback
3. ⏳ TODO: Ripple effect from click point
4. ⏳ TODO: Pulse ring on beat (BPM-driven) — feeds from Day 3 hour 10
5. ⏳ TODO: Hover state shows waveform preview (Day 3 hour 1)
6. ⏳ TODO: Loading state while MP3 buffers (spinner)
7. ⏳ TODO: Error state on 404 (red shake + retry button)
8. ⏳ TODO: Disabled state when no MP3
9. ⏳ TODO: Active state when playing (different color)
10. ⏳ TODO: All states have a11y aria-label

### Hour 14 — Track row interactions (10 of 10)
1. ⏳ TODO: Hover reveals ▷ button inline (slides in from left)
2. ⏳ TODO: Currently-playing row has a thin progress bar (left edge)
3. ⏳ TODO: Hover reveals timestamp tooltip
4. ⏳ TODO: Click-to-play (entire row clickable)
5. ⏳ TODO: Right-click → context menu (more actions)
6. ⏳ TODO: Cmd+click → multi-select
7. ⏳ TODO: Shift+click → range select
8. ⏳ TODO: Drag to reorder tracks
9. ⏳ TODO: prefers-reduced-motion → no slide-in
10. ⏳ TODO: Keyboard navigation (up/down/enter)

### Hour 15 — Album card interactions (10 of 10)
1. ⏳ TODO: Hover lifts card (-2px Y + shadow)
2. ⏳ TODO: Hover scales cover (1.02)
3. ⏳ TODO: Hover reveals quick-play overlay
4. ⏳ TODO: Hover reveals metadata tooltip
5. ⏳ TODO: Click opens drawer
6. ⏳ TODO: Double-click opens studio
7. ⏳ TODO: Right-click → context menu
8. ⏳ TODO: Cover shimmer on hover
9. ⏳ TODO: Status badge pulses on hover
10. ⏳ TODO: prefers-reduced-motion → no lift

### Hour 16 — Pipeline cell animations (10 of 10)
1. ⏳ TODO: Cell lights up sequentially on invoke (cascade 01 → 02 → 03)
2. ⏳ TODO: 80ms delay between cells
3. ⏳ TODO: Active cell has accent border + glow
4. ⏳ TODO: Done cell has checkmark ✓
5. ⏳ TODO: Failed cell has ✗ + red glow
6. ⏳ TODO: Pending cell is dimmed
7. ⏳ TODO: Spring-bouncy on active state
8. ⏳ TODO: Pulse on click
9. ⏳ TODO: Hover shows phase tooltip
10. ⏳ TODO: prefers-reduced-motion → no cascade

### Hour 17 — Decision drawer (10 of 10)
1. ⏳ TODO: Slide in from right on open (per spring.css WIP)
2. ⏳ TODO: Backdrop dim + click-to-close
3. ⏳ TODO: Esc to close
4. ⏳ TODO: Form fields with focus ring
5. ⏳ TODO: Submit button with loading state
6. ⏳ TODO: Cancel button
7. ⏳ TODO: Validation errors inline (red text under field)
8. ⏳ TODO: Success animation on submit
9. ⏳ TODO: prefers-reduced-motion → no slide
10. ⏳ TODO: Form reset on close

### Hour 18 — Events log animations (10 of 10)
1. ⏳ TODO: New events slide in from top (push existing down)
2. ⏳ TODO: Spring-bouncy curve
3. ⏳ TODO: Chat events: human role = blue tint, assistant = green tint
4. ⏳ TODO: Build events: subtle pulse on appearance
5. ⏳ TODO: Log events: monospace
6. ⏳ TODO: Click event → open in detail view
7. ⏳ TODO: Filter pills (chat/build/log)
8. ⏳ TODO: Auto-scroll to bottom (toggleable)
9. ⏳ TODO: prefers-reduced-motion → no slide
10. ⏳ TODO: Empty state with illustration

### Hour 19 — Asset gallery interactions (10 of 10)
1. ⏳ TODO: Asset card hover lift + shadow
2. ⏳ TODO: Asset cover preview expand on hover
3. ⏳ TODO: Click → open in lightbox
4. ⏳ TODO: Lightbox: backdrop + zoom
5. ⏳ TODO: Lightbox: keyboard nav (arrows + Esc)
6. ⏳ TODO: Download button on each asset
7. ⏳ TODO: Copy URL button
8. ⏳ TODO: Filter by kind (cover / poster / merch / lyrics)
9. ⏳ TODO: prefers-reduced-motion → no hover lift
10. ⏳ TODO: Sort by date / size / kind

### Hour 20 — Build runner animations (10 of 10)
1. ⏳ TODO: Job in-progress: progress ring fills around layer cell
2. ⏳ TODO: Started: brief flash on the cell
3. ⏳ TODO: Running: rotating indicator
4. ⏳ TODO: Done: green checkmark + fade
5. ⏳ TODO: Failed: red ✗ + shake
6. ⏳ TODO: Skipped: gray dash + dim
7. ⏳ TODO: Cancel: animated X overlay
8. ⏳ TODO: Layer transitions crossfade
9. ⏳ TODO: prefers-reduced-motion → instant transitions
10. ⏳ TODO: Job history with timestamps

### Hour 21 — Session lifecycle animations (10 of 10)
1. ⏳ TODO: Open: status pill grows + bounces in
2. ⏳ TODO: Pause: pill pulses yellow
3. ⏳ TODO: Resume: pill morphs to cyan
4. ⏳ TODO: Complete: pill morphs to green + checkmark
5. ⏳ TODO: Status flip animation (Day 7 hour 1)
6. ⏳ TODO: Session timeline visualization
7. ⏳ TODO: Idle warning at 11h (yellow)
8. ⏳ TODO: Auto-pause at 12h (orange)
9. ⏳ TODO: Closed indicator after 24h (gray)
10. ⏳ TODO: prefers-reduced-motion → instant

### Hour 22 — Album drawer interactions (10 of 10)
1. ⏳ TODO: Drawer opens with spring-soft slide
2. ⏳ TODO: Cover scales up inside drawer
3. ⏳ TODO: Metadata fades in after cover
4. ⏳ TODO: Track list staggers in
5. ⏳ TODO: Asset gallery staggers in
6. ⏳ TODO: Open Session button highlighted
7. ⏳ TODO: Edit modal for album
8. ⏳ TODO: Delete album with confirmation
9. ⏳ TODO: Archive album (per Day 11)
10. ⏳ TODO: prefers-reduced-motion → no slide

### Hour 23 — Dashboard widgets (10 of 10)
1. ⏳ TODO: Animated count-up on stats
2. ⏳ TODO: Bar chart for tracks per album
3. ⏳ TODO: Pie chart for status distribution
4. ⏳ TODO: Timeline for build sessions
5. ⏳ TODO: Heatmap for activity (per day)
6. ⏳ TODO: Sparkline for quota
7. ⏳ TODO: Hover → expand widget
8. ⏳ TODO: Click → drill into metric
9. ⏳ TODO: prefers-reduced-motion → no animation
10. ⏳ TODO: All widgets responsive

### Hour 24 — Day 1 wrap-up (10 of 10)
1. ⏳ TODO: Day 1 final e2e run (185+ tests must pass)
2. ⏳ TODO: Commit all Day 1 work with day-N commits
3. ⏳ TODO: Mirror docs to OneDrive
4. ⏳ TODO: Update Obsidian daily log
5. ⏳ TODO: Update UI-UX-IMPROVEMENT-SCHEDULE.md with Day 1 ✅ marks
6. ⏳ TODO: Capture 24 screenshots (one per hour)
7. ⏳ TODO: Update README with Day 1 features
8. ⏳ TODO: Update USER_MANUAL with new screenshots
9. ⏳ TODO: Mark Day 1 complete; transition to Day 2 plan
10. ⏳ TODO: Hand off to next session

---

## Day 2 (TODO) — 240 ideas — Spring-physics completion + Haptic feedback + Status pill pulse

### Hour 1 — Spring-physics completion (10 of 10)
1. ⏳ TODO Day 2 Hour 1 idea 1
2-10. ⏳ TODO (to be filled by future iteration)

[Rest of Day 2-10 follow the same pattern as Hour 24 above]

---

## Day 2 (TODO) — 240 ideas

### Hour 1 — Spring-physics completion
### Hour 2 — Haptic-style press feedback
### Hour 3 — Status pill state transitions
### Hour 4 — Decision cards staggered reveal
### Hour 5 — Modal/drawer spring entrance
### Hour 6 — Audio progress elastic snap
### Hour 7 — Album cover 3D shimmer
### Hour 8 — Scroll-timeline topbar
### Hour 9 — View Transitions page morph
### Hour 10 — Track play button reactive fill
### Hour 11-24 — TODO (140 more ideas)

---

## Day 3 (TODO) — 240 ideas

### Hour 1 — Live canvas waveform
### Hour 2 — Static waveform pre-render
### Hour 3 — Color-shifted waveform
### Hour 4 — Click-to-seek waveform
### Hour 5 — Hover-to-preview track position
### Hour 6 — Volume slider haptic snap
### Hour 7 — EQ 3-band visualization
### Hour 8 — Track progress ring
### Hour 9 — Lyrics sync animation
### Hour 10 — BPM detection + tempo display
### Hour 11-24 — TODO

---

## Day 4 (TODO) — 240 ideas — Command palette (super+K)

### Hour 1 — Palette overlay opens on Cmd+K
### Hour 2 — Cross-resource search (albums/sessions/tracks/decisions)
### Hour 3 — Fuzzy match scoring
### Hour 4 — Recent commands history
### Hour 5 — Keyboard-only navigation
### Hour 6 — Action shortcuts (build, pause, navigate)
### Hour 7 — Theme switch from palette
### Hour 8 — Help palette (:?)
### Hour 9 — Filter pills
### Hour 10 — Custom command registration via data-command
### Hour 11-24 — TODO

---

## Day 5 (TODO) — 240 ideas — Glassmorphism

### Hour 1 — Modal with backdrop-filter blur
### Hour 2 — Drawer parallax depth
### Hour 3 — Album cover glass reflection
### Hour 4 — Status pill glass background
### Hour 5 — Tooltip glass surface
### Hour 6 — Confirm dialog spring + glass
### Hour 7 — Sidebar frosted glass
### Hour 8 — Toast glass surface
### Hour 9 — Audio player controls glass
### Hour 10 — Decision-card hover glass reflection
### Hour 11-24 — TODO

---

## Day 6 (TODO) — 240 ideas — Hover micro-interactions

### Hour 1 — Track row hover with play button reveal
### Hour 2 — Decision card hover with edit button
### Hour 3 — Event row hover with timestamp highlight
### Hour 4 — Pipeline cell hover with phase tooltip
### Hour 5 — Asset card hover with preview expand
### Hour 6 — Modal close button hover (X rotates 90°)
### Hour 7 — Status pill hover with quick-action menu
### Hour 8 — Footer meta hover with detail expand
### Hour 9 — Toast hover with dismiss button
### Hour 10 — Album card hover with quick-play
### Hour 11-24 — TODO

---

## Day 7 (TODO) — 240 ideas — Toast system

### Hour 1 — Slide-in toast animation
### Hour 2 — Toast progress bar
### Hour 3 — Toast stack auto-dismiss
### Hour 4 — Toast with Undo action
### Hour 5 — Toast semantic colors
### Hour 6 — Toast custom icons
### Hour 7 — Toast sticky mode
### Hour 8 — Toast hover-to-pause
### Hour 9 — Toast queue FIFO
### Hour 10 — Toast with sound
### Hour 11-24 — TODO

---

## Day 8 (TODO) — 240 ideas — Page transitions + skeletons

### Hour 1 — View Transitions API cross-fade
### Hour 2 — Album card skeleton
### Hour 3 — Track list skeleton
### Hour 4 — Pipeline skeleton
### Hour 5 — Skeleton shimmer
### Hour 6 — Smooth height transitions
### Hour 7 — Lazy cover blur-up
### Hour 8 — Skeleton → real crossfade
### Hour 9 — Long-op progress bar
### Hour 10 — Inline loading states
### Hour 11-24 — TODO

---

## Day 9 (TODO) — 240 ideas — Animated pipeline + keyboard shortcuts

### Hour 1 — Pipeline cells cascade light-up
### Hour 2 — Layer transitions progress ring
### Hour 3 — Shortcuts overlay (? opens)
### Hour 4 — Shortcut discoverability chips
### Hour 5 — Cmd+K palette (overlap with Day 4)
### Hour 6 — Cmd+1..9 jump to layer
### Hour 7 — Cmd+/ search
### Hour 8 — Esc dismiss stacking
### Hour 9 — Arrow keys navigate track list
### Hour 10 — Spacebar play/pause
### Hour 11-24 — TODO

---

## Day 10 (TODO) — 240 ideas — Advanced interactions + launch polish

### Hour 1 — Drag-and-drop track reorder
### Hour 2 — Track duplication (Cmd+D)
### Hour 3 — Multi-select with shift-click
### Hour 4 — Inline track editing
### Hour 5 — Right-click context menu on album
### Hour 6 — Drag album cover to desktop
### Hour 7 — Markdown export of brief
### Hour 8 — PDF cover sheet export
### Hour 9 — ZIP archive download (album + cover + MP3s)
### Hour 10 — Welcome onboarding overlay
### Hour 11-24 — TODO

---

## Day 1 Hour 4-24 — 220 ideas backlog (placeholder)

These will be filled out by future iterations. Each hour adds 10 ideas.

---

## Hand-off Notes (for next session)

- Start daemon: `python -m build.serve --host 127.0.0.1 --port 8765`
- Run e2e before commit: `python e2e/run_all.py` (must all pass)
- Cache-bust scheme: `?v=dayN-hourM` on every script tag
- OneDrive mirror per R7: copy docs → `~/OneDrive/Hermes/Agents/planning/album-studio/`
- Obsidian daily log: `~/Documents/Obsidian Vault/Hermes/9-daily/YYYY-MM-DD.md`
- **Every iteration ships 10 ideas.** No fewer. No truncation.
- **Continue until 2,400 ideas done.**

---

## Lessons from Day 1 Hours 1-3

1. **`$(...).forEach` gotcha still bites** — `TestNoDollarForEachBug` is the guard.
2. **The schedule is the contract** — each session reads it, marks done, continues.
3. **Cache-bust matters** — `?v=dayN` is the only way Chrome sees updates.
4. **No 3-hour cap, no 10-idea cap** — user wants the loop to run continuously.
