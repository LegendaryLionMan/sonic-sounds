# Sonic Studio

> **Plan an album. Walk it through the 12-layer build pipeline. Ship a final release.**
> _Sonic Studio_ is a local-first music-album design + production studio. Local SQLite, no cloud required, open-source.

A daemon-driven workspace for music-album creation. The user answers 26 questions in the intake form, the brief locks into the database, and the 12-layer build pipeline executes layer-by-layer via click-to-invoke buttons in the studio. Includes a persistent **header music player** (cassette visual, 6 themes, 15 keyboard shortcuts) that follows you across every page.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE) [![Code style: plain JS](https://img.shields.io/badge/frontend-plain_JS-yellow.svg)](./site)

---

## ✨ What's inside

| | |
|---|---|
| 🎛 **12-layer pipeline** | intake → brief → M1–M13 (music) → R14 (release) — every layer has a daemon endpoint, an `INVOKE` button, and an artifact manifest |
| 🎵 **Header music player** | 7-button transport, 15 keyboard shortcuts, A/B loop, sleep timer, repeat modes, seek-bar hover preview, 6 themes — sticks to the top of every page |
| 📜 **Intake form** | 26 questions across 6 categories (scope, music, lyrics, visual, distribution, technical) with reference-band research |
| 🎨 **6 themes** | Mixtape '85 (default), Tokyo Night, Catppuccin Latte, Gruvbox Dark, Everforest, Kanagawa — instant picker, persists across reload |
| 🗄 **Single-file SQLite** | WAL mode + 5 sweepers (idle-pause, WAL checkpoint, quota snapshot, OneDrive mirror, log rotate) keep it healthy |
| 📦 **No build step** | open `site/albums.html` in any browser; the daemon is optional for music playback |
| 🎤 **Album delivery** | ISRC codes, ID3v2.3 tags, 9 cover designs, 6 voice portraits, 4 animated GIFs |

---

## 🚀 Quick start (3 commands)

```bash
# 1. Install
python -m pip install -e .

# 2. Start the daemon
python -m build.serve --port 8765

# 3. Open in Chrome
open http://127.0.0.1:8765/site/albums.html
```

That's it. You'll see the **Mixtape '85** theme, a persistent header music player at the top, and the album list (with the seeded "Half-Light Hours" demo album).

### 30-second tour

1. Start the daemon: `python -m build.serve --port 8765`
2. Open in Chrome: <http://127.0.0.1:8765/site/albums.html>
3. See the seeded album: Maren Sol / "Half-Light Hours" — 10 tracks, dream-folk, 40 min
4. Click `[INVOKE]` on any of the 9 pipeline layers to run it
5. Click `[▷]` next to any track to play the MP3 (streams from OneDrive)

---

## 🎵 Header music player — at a glance

The header follows you across every page. It mounts automatically when any `site/*.html` loads.

### Transport row
`−15 ⏮ ▷ ⏭ +15 ↻ 🔀` — shuffle lives at the END (after repeat).

### Keyboard shortcuts (15 total)

| Key | Action |
|---|---|
| `Space` | Play / Pause |
| `← / →` | Previous / Next track |
| `, / .` | Skip ±15 seconds |
| `↑ / ↓` | Volume ±5% |
| `M` | Mute / Unmute |
| `R` | Repeat: off → all → one |
| `S` | Shuffle |
| `[ / ]` | A/B loop start / end |
| `+ / −` | Speed (0.5× → 2×) |
| `I` | Elapsed / Remaining time |
| `L` | Lyrics panel |
| `T` | Tracklist panel |
| `?` | Open this shortcut cheatsheet |
| `Esc` | Close any panel |

### Cassette visual
- 78×46 rectangle sticker image
- Spinning reels (animated via `@keyframes hp-spin` when playing)
- Idle pulse on the cassette when paused
- Neutral near-black background — **no blue tint**

### Themes
The 6 themes are defined in [`site/themes.css`](./site/themes.css) as `:root[data-theme="X"] {}` blocks and applied via the picker in every page's topbar. Theme choice persists in localStorage with no FOUC.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (any)                                                       │
│  ─────────                                                          │
│  site/albums.html   ← albums page (seeded)                         │
│  site/library.html   ← library page (track browser)                 │
│  site/studio.html    ← studio page (12-layer pipeline INVOKE grid)   │
│  site/intake.html    ← intake form (26 questions)                    │
│  site/dashboard.html ← dashboard (status overview)                  │
│                                                                       │
│  Each page auto-mounts the header-player.js (cassette, transport)    │
└──────────────────────────────────────────────────────────────────────┘
                              │  HTTP / JSON
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Python daemon (Quart ASGI on Hypercorn)                             │
│  ────────────────────────────────                                  │
│  build/serve.py            — Quart app, route registration           │
│  build/handlers_*.py       — JSON endpoints per layer               │
│  db/connection.py          — SQLite WAL + PRAGMAs                    │
│  db/migrations/             — versioned schema                        │
│  db/albums.py              — album CRUD + tracks                     │
│  cli.py                    — Invoke mmx for M1–M13 generation         │
│                                                                       │
│  5 sweepers run on idle-pause ticks:                                 │
│    • idle-pause    — pause playback when user idle                   │
│    • WAL checkpoint — periodic WAL flush                              │
│    • quota snapshot — write quota counter every 5 min                │
│    • OneDrive mirror — mirror artifacts to OneDrive                  │
│    • log rotate     — truncate daemon.log to 10 MB                   │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SQLite at .meta/sonic-studio.db  (override via SONIC_STUDIO_DB_PATH)│
│  Lock file at .meta/daemon.lock    (override via SONIC_STUDIO_LOCK_PATH)│
│  Log file at .meta/daemon.log     (override via SONIC_STUDIO_LOG_PATH) │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation

| Doc | For | Description |
|---|---|---|
| **[CATCH-UP.md](./CATCH-UP.md)** | 🤖 **LLM catch-up guide** | Full requirements + context + recent decisions to onboard a new LLM |
| **[CHANGELOG.md](./CHANGELOG.md)** | Everyone | Release history with breaking-change callouts |
| **[SECURITY.md](./SECURITY.md)** | Everyone | Vulnerability disclosure policy, secret-handling rules |
| **[docs/USER_MANUAL.md](./docs/USER_MANUAL.md)** | End users | How to use the UI: intake → studio → finalize → reopen, with mermaid UX flow + screenshots |
| **[docs/TECHNICAL.md](./docs/TECHNICAL.md)** | Developers | Architecture, db schema, HTTP layer, build runner, sweepers, frontend data flow, test pyramid |
| **[docs/STRUCTURE-POLICY.md](./docs/STRUCTURE-POLICY.md)** | All | Folder layout, R1–R7 rules, mirror discipline |
| **[DESIGN.md](./DESIGN.md)** | Designers | Mixtape '85 design system: palette, type, motion, components |

---

## 🛣️ Roadmap

### Done
- [x] 12-layer pipeline with INVOKE buttons (M1–M13 + R14)
- [x] Intake form with 26 questions across 6 categories
- [x] 6 themes (Mixtape '85, Tokyo Night, Catppuccin Latte, Gruvbox Dark, Everforest, Kanagawa)
- [x] Header music player with cassette visual + 15 keyboard shortcuts + 6 themes
- [x] SQLite WAL + 5 sweepers
- [x] OneDrive mirror (artifacts + screenshots)
- [x] Album delivery package (ISRC codes, ID3v2.3, 9 covers, 6 voice portraits, 4 GIFs)
- [x] Test pyramid: 385 pytest + 159 e2e verifications (Day-14 baseline)

### In progress
- [ ] Lyrics transcription pipeline (panel placeholder ready)
- [ ] Drag-to-reorder tracks
- [ ] Audio waveform visualization on the seek bar

### Future
- [ ] Export to DistroKid-friendly CSV
- [ ] Album detail page (tracklist + cover art + credits)
- [ ] Multi-user collaboration (Phase 3+)

---

## 🛠️ Development

### Run the test suite

```bash
python -m pytest              # 385 tests, ~10 seconds
python tests/test_e2e.py     # 159 e2e verifications (slower)
```

### Code style

- **Python**: `black` formatting, type hints where helpful, `from __future__ import annotations`
- **JavaScript**: ES modules + plain functions in IIFEs, no build step
- **CSS**: custom properties for theming, BEM-ish class names

### Contributing

See [CONTRIBUTING.md](./.github/CONTRIBUTING.md) (TODO) and [.github/PULL_REQUEST_TEMPLATE.md](./.github/PULL_REQUEST_TEMPLATE.md).

---

## 📜 License

MIT — see [LICENSE](./LICENSE).

## 🙏 Acknowledgements

- Music: [Maren Sol](https://github.com/LegendaryLionMan) — the seeded demo album is "Half-Light Hours" (dream-folk, 10 tracks, 40 min)
- Cassette sticker: hand-illustrated, included in `site/assets/cassette-yellow-tape.jpg`
- Theme palette research: 6 themes hand-curated from Omarchy OS, Catppuccin, Tokyo Night, Gruvbox, Everforest, Kanagawa
- Type: Bebas Neue + Inter + JetBrains Mono + Caveat (handwritten)
