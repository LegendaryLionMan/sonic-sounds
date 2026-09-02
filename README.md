# album-studio

> **Plan an album. Walk it through the 12-layer build pipeline. Ship a final release.**
> Mixtape '85 era (v3.4) — replaces the cassette-mesh / Editorial Zine era retired 2026-08-05.

A daemon-driven workspace for music-album creation. The user answers 26 questions in the intake form, the brief locks into the database, and the 12-layer build pipeline executes layer-by-layer via click-to-invoke buttons in the studio.

---

## 🎵 The 30-second tour

1. **Start the daemon:** `python -m build.serve --port 8765`
2. **Open in Chrome:** http://127.0.0.1:8765/site/studio.html
3. **See the seeded album:** Maren Sol / "Half-Light Hours" — 10 tracks, dream-folk, 40 min
4. **Click `[INVOKE]`** on any of the 9 pipeline layers to run it
5. **Click `[▷]`** next to any track to play the MP3 (streams from OneDrive)

That's it. The daemon runs in the background; 5 sweepers (idle-pause, WAL checkpoint, quota snapshot, OneDrive mirror, log rotate) keep it healthy.

---

## 📚 Documentation

| Doc | For | Description |
|---|---|---|
| **[docs/USER_MANUAL.md](docs/USER_MANUAL.md)** | End users | How to use the UI: intake → studio → finalize → reopen, with mermaid UX flow + screenshots |
| **[docs/TECHNICAL.md](docs/TECHNICAL.md)** | Developers | Architecture, db schema, HTTP layer, build runner, sweepers, frontend data flow, test pyramid |
| **[docs/STRUCTURE-POLICY.md](docs/STRUCTURE-POLICY.md)** | All | Folder layout, R1-R7 rules, mirror discipline |

## ⚙️ Quick reference

```bash
# Setup
python -m db.seed --force             # populate Maren Sol / Half-Light Hours
python -m build.serve --port 8765    # start daemon (port 8765 = default)
python -m pytest tests/ build/ -q     # 377 tests

# E2E
python e2e/run_all.py                # 122/122 headless UX checks
python e2e/test_playwright_e2e.py    # 16/16 Playwright checks (needs Playwright installed)

# Operational
python -m scripts.verify_mirror       # md5 verify OneDrive ↔ albums/
python -m scripts.finalize_album <album_id> --skip-mastering   # dry-run finalize
```

---

## 🏗 The 12-layer pipeline

Per `pipeline-deps.json`:

```
01 brief                    [manual]   02 lyrics_drafts          [music.generate]
03 lyrics_finalize          [music.generate]   04 vocal_recordings    [music.generate]
05 instrumental            [music.generate]   06 cover_art           [image.generate]
07 cassette_sticker        [image.generate]   08 audio_mastering     [manual]
09 metadata_isrc           [manual]   10 distribution           [manual]
11 press_kit                [manual]   12 finalize               [manual]
```

The studio displays the first 9 layers. The remaining 3 are admin-only.

---

## 📊 Status

- **Tests:** 377 passing + 2 skipped (run with `pytest tests/ build/`)
- **E2E:** 122/122 headless UX + 16/16 Playwright = 138/138 distinct checks
- **Daemon subsystems:** 6/6 ok (audio, build_runner, db, http, static, sweepers)
- **Endpoints:** 30+ HTTP routes (albums, sessions, events, decisions, build, intake, audio, cover)
- **Sweepers:** 5 daemon threads (idle_pause, wal_checkpoint, quota, mirror, log_rotate)
- **Frontends:** 6 pages (index, intake, albums, library, studio, dashboard)
- **Canonical:** `~/OneDrive/Hermes/albums/Half-Light-Hours/` (per R10)

---

## 🔗 Related

- **Skill:** `music-album-planning-questionnaire` (drives the content; album-studio drives the state)
- **Skill:** `album-studio-day-ship-pattern` (the workflow this project follows)
- **Skill:** `album-studio-structure-policy` (folder layout rules)
- **Memory:** `~1000 lines of operational memory` (msys traps, hermes-venv contamination, bash double-backslash escaping, etc.)

---

**Plan v3.4** complete (Days 1-12 all shipped). See [docs/TECHNICAL.md §10](docs/TECHNICAL.md#10-day-by-day-commit-history) for the day-by-day commit history.
