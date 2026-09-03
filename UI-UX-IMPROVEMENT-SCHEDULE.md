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

### Hours 4-24 of Day 1 — TODO (220 backlog slots, see Hour 24 below)

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
