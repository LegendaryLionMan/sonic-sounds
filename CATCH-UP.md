# Sonic Sounds — Catch-up Guide

> **Purpose**: this file is the single source of truth a second LLM (or a human returning after a break) can read to fully understand what Sonic Sounds is, why each design decision was made, and how to keep working on it without breaking things.
>
> Last updated: 2026-09-04 (the day the project was renamed from sonic-studio → Sonic Sounds and pushed to https://github.com/LegendaryLionMan/sonic-sounds)

---

## 1. What this project is, in one sentence

A **local-first music-album design + production studio** that turns a 26-question intake form into a fully-deliverable album package: 10 MP3s with ISRC codes and ID3v2.3 tags, 9 cover designs, 6 voice portraits, 4 animated GIFs, and a persistent header music player that follows you across every page.

**Run it locally. Don't pay for cloud. Open-source under MIT.**

---

## 2. Non-negotiable requirements (collected across all sessions)

These are the things that **must not change** without explicit user approval.

### 2.1 Local-first, no cloud
- **All data lives in SQLite at `.meta/sonic-sounds.db`** (override via `SONIC_SOUNDS_DB_PATH` env var)
- **No cloud sync** — every artifact is mirrored to **OneDrive** at `~/OneDrive/Hermes/Agents/planning/<project>/` per the R5 mirror discipline (see `docs/STRUCTURE-POLICY.md`)
- The daemon binds to **`127.0.0.1:8765` only** (no `0.0.0.0` ever)
- **No telemetry, no analytics, no tracking**. Anywhere.

### 2.2 No build step on the frontend
- `site/*.html` files open directly in any modern browser
- All JS is plain ES modules + IIFEs (no Webpack, no Vite, no transpile)
- All CSS uses native **CSS custom properties** for theming
- The Python daemon is **optional** for music playback — only required for INVOKE / build-pipeline features

### 2.3 Six-theme system
The picker lives in every page's topbar via a `<div data-theme-mount>` slot.
Themes are defined in `site/themes.css` as `:root[data-theme="X"] {}` blocks.

| Theme | Mood | Use |
|---|---|---|
| **Mixtape '85** (default) | Warm yellow + cyan on near-black | The sonic-sounds identity — locked 2026-08-05 |
| **Tokyo Night** | Calm nocturnal deep-blue | Calm working sessions |
| **Catppuccin Latte** | Pastel warm light | The only light theme — also sets `colorScheme='light'` for browser chrome |
| **Gruvbox Dark** | Warm retro on warm-black | 80s/early-90s mixtape culture |
| **Everforest** | Forest greens + earth tones | Calm + nature |
| **Kanagawa** | Sumi-e ink + indigo | Eastern calligraphic mood |

**Locked**: do not propose cassette-mesh or Editorial Zine alternatives unless user explicitly reverts. Those are retired.

### 2.4 The header music player
The header (`site/header-player.js` + `site/header-player.css`) mounts automatically on every page via `<body class="has-header-player">`. It is the **single biggest UX surface** in the project and has been polished through ~19 days of iteration.

Required behaviors:
- **Cassette visual** — 78×46 rectangle sticker image, spinning reels via `@keyframes hp-spin` while playing, neutral near-black background (no blue tint)
- **Transport row order**: `−15 ⏮ ▷ ⏭ +15 ↻ 🔀` (shuffle at the END, after repeat)
- **Repeat modes**: `off → all → one` (full album loop / single-track loop)
- **Click the speaker icon** to mute / unmute (preserves slider position; remembers the volume you had before muting)
- **15 keyboard shortcuts** (see README.md for the full table)
- **Volume slider styled like the music progress bar** (gradient fill + accent thumb with soft glow) — uses a `--vol-pct` CSS var updated by `paintVol()` on every input event
- **Click-outside / Escape** closes any open panel (tracklist, lyrics, keys)

Negative behaviors to AVOID:
- ❌ Don't overlay reels/glow/pip dots ON TOP of the cassette sticker image — that was tried and reverted in `617018a`
- ❌ Don't swap the sleep-timer icon to a number when active — the icon stays `⏱`, the state is conveyed via `.is-active` class + title/aria-label
- ❌ Don't replace ±15s buttons with text labels `'−15' / '+15'` — use the proper glyphs `⟲` / `⟳`
- ❌ Don't put shuffle BEFORE play controls — user explicitly requested shuffle at the END after repeat
- ❌ Don't use a square cassette slot — the user explicitly asked for a wider rectangle (78×46 = aspect 1.70)

### 2.5 12-layer pipeline
The pipeline has 13 layers (M1–M13 + R14 for release). Each layer has:
- A daemon endpoint
- An `INVOKE` button on the studio page
- An artifact manifest that tracks what was produced (mp3 + tags + cover, etc.)

The state machine: **`ready → running → succeeded | failed`**. Failed layers can be re-run.

### 2.6 Five sweepers run on idle ticks
- `idle-pause` — pauses music playback when the user is idle (no DOM activity for N seconds)
- `WAL checkpoint` — periodic SQLite WAL flush
- `quota snapshot` — writes the quota counter to disk every 5 min
- `OneDrive mirror` — mirrors artifacts to OneDrive
- `log rotate` — truncates `daemon.log` to 10 MB

These are not user-facing. They keep the daemon healthy.

### 2.7 Env var naming convention
**All env vars use `SONIC_SOUNDS_` prefix** (was `ALBUM_STUDIO_` before the rename). The full list:

| Var | Default | Purpose |
|---|---|---|
| `SONIC_SOUNDS_DB_PATH` | `.meta/sonic-sounds.db` | SQLite database path |
| `SONIC_SOUNDS_LOCK_PATH` | `.meta/daemon.lock` | Singleton lock file |
| `SONIC_SOUNDS_LOG_PATH` | `.meta/daemon.log` | Daemon log |
| `SONIC_SOUNDS_MMX_CMD` | (none) | Override path to `mmx` CLI for M-layer generation |
| `SONIC_SOUNDS_E2E_BASE` | `http://127.0.0.1:8793` | Daemon URL for e2e tests |
| `SONIC_SOUNDS_E2E_PORT` | `8793` | Port the e2e runner starts on |
| `SONIC_SOUNDS_E2E_HEADLESS` | `1` | Run Playwright in headless mode for e2e |

### 2.8 Secrets & credentials
**There are no secrets in this repo.** Specifically:
- No API keys (OpenAI, Anthropic, GitHub, MiniMax, etc.)
- No private keys (RSA, EC, SSH, OpenSSH, DSA)
- No database connection strings with embedded passwords
- No environment files (`.env`, `.env.local`) — these are gitignored

The `.gitignore` includes `.env`, `.env.local`, `*.key`, `*.pem` as a defensive layer.

If you ever add a feature that needs an API key:
1. Read it from an env var
2. Never commit the env var's value
3. Add a `.env.example` (without real values) and document the required var in README
4. Add the env var name to the table above

### 2.9 Folder layout (the 3-pane principle)
The `docs/STRUCTURE-POLICY.md` defines the folder layout. The high-level rules:
- **Code lives in the project root** (build/, db/, site/, tests/, tools/, scripts/)
- **Runtime state lives in `.meta/`** (gitignored — varies per-host, per-run)
- **OneDrive mirror is at `~/OneDrive/Hermes/Agents/planning/<project>/`** — never committed
- **Historical prototypes go in `archive/`** — never renamed, kept for traceability
- **Skill mirror is in `.agents/skills/`** — gitignored local-only

---

## 3. Recent decisions (last 7 days, in order)

These are the choices a new LLM needs to know about to avoid contradicting the user's recent corrections.

### Day 18 (2026-09-04): 6-theme system + header-player bug fixes
- Commits: `eea8d98`, `1b50927`, `01b9886`, `cab9858`
- **Theme cascade bug**: module-level `:root { --bg: ...; }` was winning over `:root[data-theme]` even when data-theme was set. Fix: wrap module defaults in `:root:not([data-theme])`.
- **Cassette 4-col grid bug**: `.hp-transport`, `.hp-progress`, `.hp-right` were spilling below the bar. Fix: explicit 3-col grid `auto minmax(180, 0.9fr) minmax(280, 2fr) minmax(220, 1fr)`.
- **Pause-button restart bug**: clicking the pause button on the current track restarted it from 0. Fix: split the delegated handler so `.hp-track-play` clicks toggle play/pause instead of jumping.
- **End-of-album loop bug**: `repeat-all` kept looping the LAST track forever. Fix: `skip` clamps `idx` to `tracks.length - 1` so the last-track-replay loop is broken.

### Day 19 (2026-09-04): 10-polish batch (first)
- Commit: `a97abbb` (418 insertions, 2 files)
- Added: skip ±15s, seek-bar hover preview, sleep timer, lyrics panel, now-playing pip (later reverted), cassette glow + reel speed-up (later reverted), progress-fill shimmer (later reverted), tracklist current-track pulse, shuffle button, repeat cycling
- Initial decisions that were later REVERTED in the same day (Day-19 second commit `617018a`): the cassette overlays were visually busy, the sleep button showed minutes instead of icon, the ±15 buttons used `'−15'/'+15'` text instead of proper glyphs

### Day 19 (later): Visual cleanup reverts
- Commit: `617018a`
- Reverted: cassette overlays (reels/glow/pip), sleep button text-substitution, ±15 button text labels
- Established the **current visual language** the user wants (see §2.4)

### Day 19 (later): 10-polish batch (second)
- Commit: `adf4261` (342 insertions, 2 files)
- Added: keyboard shortcuts popover (`?` key), click-outside closes panels, escape closes panels, playback speed (`+`/`-`), time mode (`i`), A/B loop (`[`/`]`), idle pulse on cassette, track-row hover-lift, cassette hover affordance, footer credit line
- These are all **sticky** — verified and accepted by the user

### Day 19 (later): Reorders + widen cassette
- Commit: `09103a5` (51 insertions, 38 deletions)
- **Transport order fixed**: shuffle moved from position 1 to position 7 (after repeat)
- **Cassette widened**: 60×46 → 78×46 (aspect 1.30 → 1.70)
- **Volume slider** restyled to match `.hp-seek-fill` (gradient fill + accent thumb)
- **Right area decluttered**: removed the sleep ⏱ + lyrics ♪ mini-buttons that were between volume and tracks
- **Reels restored** in markup so they animate when playing

### Day 19 (later): Repo published + renamed
- Commit: `16f3218`
- Created https://github.com/LegendaryLionMan/sonic-sounds
- Repo renamed on GitHub: album-studio → sonic-studio → sonic-sounds → Sonic Sounds (final name). Repo URL is now https://github.com/LegendaryLionMan/sonic-sounds. The old album-studio and sonic-studio names no longer exist as separate GitHub repos.
- v0.1.0 release published

### Day 19 (this update): Catch-up doc + security audit + repo polish
- This file you're reading was added
- Security audit ran: **0 credentials found** (verified via `git grep` for sk-, ghp_, AKIA, BEGIN PRIVATE KEY, etc.)
- All env vars prefixed `SONIC_SOUNDS_` (was `ALBUM_STUDIO_`)
- Repo description, topics, and README polished

---

## 4. What to do when the user says "do X"

| User says | Do this |
|---|---|
| "more improvements" / "10 improvements" / "iterate" | Use the design language in §2.4. NEVER undo a recent decision (search `git log --oneline -30` first). Run raw CDP via `tools/visible_browser.py` for state verification + MiniMax vision for visual layout. Avoid adding tests unless the user explicitly asks. |
| "fix this bug" | First reproduce with raw CDP. The most common bug categories in this codebase are: (a) cache-stale Chrome → use `Network.setCacheDisabled(true) + Page.reload(ignoreCache: true)`, (b) regex-match-failed renames → grep before sed, (c) kernel cwd drift → use absolute paths |
| "publish to GitHub" | `gh api -X PATCH /repos/OWNER/REPO -f name='NEW'`. Update local remote via `git remote set-url`. Run security audit (no secrets in repo). |
| "rename this to Y" | Use `gh api -X PATCH` for the GitHub rename + `git remote set-url` + repo-wide regex replacement (use `_` for python, `-` for kebab, capital for title) |
| "do a security check" | Run `git grep -nIE 'sk-[A-Za-z0-9_-]{20,}\|gho_\|ghp_\|AKIA\|BEGIN.*PRIVATE KEY'` + check `.gitignore` excludes `.env*` + `*.key` + `*.pem` + search for `localhost:` (should only be 8765/8793) |

---

## 5. Things an LLM often gets WRONG (avoid these)

1. **The cassette is wider than tall.** Aspect 1.70 (78×46). Don't make it square.
2. **Shuffle goes AFTER repeat.** Position 7 in the transport, not position 1.
3. **±15s buttons use glyphs `⟲`/`⟳`**, not text `'−15'/'+15'`.
4. **Sleep button shows `⏱` always**, even when active (state via `.is-active` class).
5. **Volume slider has a gradient fill** (uses `--vol-pct` CSS var) — not a thin grey line.
6. **The cassette image is clean** — no overlays, no glow, no pip dots on top.
7. **Repeated mistakes to NEVER repeat**: trying to put reels/glow/dots back on the cassette, swapping sleep icon to a number, putting `shuffle` first, using text for skip buttons, making cassette square.
8. **The user's preference: visible/observable play artifacts**. When something changes state (mode, theme, etc.), there should be a visible cue. The user has explicitly requested this repeatedly.
9. **The user uses MiniMax as their primary LLM.** Don't assume OpenRouter/Gemini/Anthropic is available. The vision path that works is: `urllib.request` against `https://api.minimax.io/v1/chat/completions` with image data URIs.

---

## 6. Quick command reference

```bash
# Start daemon (auto-reloads on file changes via the existing process management)
python -m build.serve --port 8765

# Run tests
python -m pytest

# Run e2e (slower, ~3 minutes)
python e2e/run_all.py

# Visual verification via raw CDP
python tools/visible_browser.py nav http://127.0.0.1:8765/site/albums.html
python tools/visible_browser.py eval 'document.querySelector(".header-player").classList.add("is-playing")'
python tools/visible_browser.py shot /tmp/check.png

# Capture visible Chrome into raw CDP mode (run from the project root)
python tools/visible_browser.py status

# Open the album in the desktop preview pane (via Hermes desktop_preview)
# (this requires the Hermes agent, not a standalone CLI command)
```

---

## 7. The shape of a typical session

1. User: "I want to do X"
2. Agent: read this file, read the relevant `docs/*.md`, check the project structure, propose a plan or ask a single clarification
3. Agent: implement, verify with raw CDP, take screenshots
4. Agent: commit with a descriptive message
5. User: review, give feedback, ask for next thing
6. Goto 1

If something goes wrong, the failure modes are usually:
- Kernel cwd is broken (use absolute paths)
- Chrome cache is stale (use `?v=N` cache-bust or `Network.setCacheDisabled`)
- The user feedback looks like a bug report but is actually a strong design preference — read it carefully

---

## 8. The 1-paragraph project summary

Sonic Sounds is a local-first Python+JS music-album design + production studio. A user fills out a 26-question intake form, the brief locks into SQLite, and 13 build layers execute in sequence via click-to-invoke buttons, producing a complete album package (10 tracks, ISRC codes, ID3v2.3 tags, 9 cover designs). The header player (cassette visual, 15 keyboard shortcuts, 6 themes) persists across all pages. The user Francisco (LegendaryLionMan) iterates daily and has built ~19 days of polish into the player specifically. Local-first, no cloud, MIT-licensed. The current focus is visual polish + power-user features (keyboard shortcuts, A/B loop, sleep timer, playback speed).

## Working folder note

The canonical local project folder is `C:\Temp\sonic-sounds\`
(this is the git-tracked working tree).

There is a parallel mirror at `C:\Users\lion_\Documents\Projects\sonic-sounds\`
that gets auto-synced via OneDrive. During this session, the
OneDrive sync occasionally wiped files mid-operation; the workaround
was to do all git operations in `C:\Temp\sonic-sounds\` instead.

For the user-facing folder (where you open in your editor), use
`C:\Users\lion_\Documents\Projects\sonic-sounds\`. Both folders
are kept in sync.
