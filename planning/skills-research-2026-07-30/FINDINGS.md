# sonic-studio Skills Research — FINDINGS

**Date:** 2026-07-30
**Method:** Verified package availability via pip/npm + cross-referenced with documentation.
**Status:** This FINDINGS.md is the primary deliverable. The original delegated subagent timed out after collecting raw data; I wrote this directly.

---

## 1. Music / Audio

### 1.1 mutagen (Python ID3v2.4 metadata embedder)

**What it does:** Read + write ID3v2.3/v2.4 tags, Vorbis comments, MP4/M4A atoms, FLAC tags. Supports USLT (lyrics), APIC (cover art), all standard frames.

**Why for sonic-studio:** Every mastered track needs metadata (artist, album, track#, title, year, genre, lyrics, cover) for DSP submission. Currently we have the recipe validated (`audio-quality-2026-07-30/test_mutagen.py`).

**Install:**
```bash
/c/Users/lion_/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install mutagen
# Installed 2026-07-30: mutagen-1.48.1
```

**Recommendation:** ✅ **Install** — already done. Wire into `finalize-album.py` (Day 5 of v3.2 plan).

### 1.2 lyrics-transcriber (PyPI)

**What it does:** Auto-generate word-level-timestamped LRC + ASS karaoke files from audio, using Whisper + Genius/Spotify lyrics. https://pypi.org/project/lyrics-transcriber/

**Why for sonic-studio:** `lyrics-quality-2026-07-30/score_lyrics.py` reads lyrics text. If we want to score `lyrics_optimizer=true` outputs automatically, we need to transcribe the audio first. `lyrics-transcriber` does this end-to-end.

**Install:** `pip install lyrics-transcriber` (needs `openai-whisper` + a Genius API key)

**Recommendation:** ⏸ **Defer** — install when lyrics-quality automation becomes a real need (probably L4 build phase, not L1).

### 1.3 ffmpeg-python (Python wrapper)

**What it does:** Subprocess wrapper around ffmpeg. Same capabilities, more pythonic API. https://github.com/kkroening/ffmpeg-python

**Why for sonic-studio:** Cleaner integration than raw subprocess for our audio pipeline (loudnorm two-pass, acrossfade, spectrogram).

**Install:** `pip install ffmpeg-python`

**Recommendation:** ⚠️ **Skip** — we already use `subprocess.run([...])` cleanly. Adding a wrapper just for ergonomics isn't worth the dep.

### 1.4 pydub

**What it does:** High-level audio manipulation (cut, splice, fade, normalize). Wraps ffmpeg or avconv. https://github.com/jiaaro/pydub

**Why for sonic-studio:** Could simplify the gapless-stitching logic for L5.

**Recommendation:** ⚠️ **Skip** — ffmpeg's `acrossfade` does exactly what we need; pydub would be an extra layer without value.

### 1.5 librosa (audio analysis)

**What it does:** BPM detection, key detection, tempo, beat tracking, onsets, MFCC, chroma. https://librosa.org/

**Why for sonic-studio:** Could auto-detect BPM/key from generated audio (instead of trusting the model's `--bpm` param). Useful for the studio's "audio quality" panel.

**Install:** `pip install librosa` (50+ MB deps including scipy, numpy, soundfile, audioread)

**Recommendation:** ⚠️ **Defer** — ffmpeg's `aspectralstats` covers spectral centroid + flatness (which is what we use most). BPM/key detection would be nice but isn't in the critical path. Install only if a future layer needs it.

### 1.6 spotipy (Spotify Web API)

**What it does:** Read-only access to Spotify catalog (search artists/albums/tracks, get metadata, ISRC, etc.). https://github.com/spotipy-dev/spotipy

**Why for sonic-studio:** After distribution, validate that our tracks are actually on Spotify with correct metadata. Also useful for finding reference tracks (M04) — search for "Foo Fighters deep cut" and pull ISRC.

**Install:** `pip install spotipy` (needs Spotify app credentials)

**Recommendation:** ✅ **Install** — for Day 10+ (Library / dashboard phase) and for post-distribution validation.

---

## 2. Album packaging / Cassette-mesh

### 2.1 No canonical "cassette tape SVG renderer" library exists

I searched: github `cassette-tape`, npm `cassette-sticker`, npm `cassette-svg`, npm `cassette-mockup`. Nothing open-source and substantive.

What exists: Vecteezy + Freepik sell commercial SVG cassette templates. Adobe Illustrator files for cassette J-cards circulate. But no programmatic renderer.

**Recommendation:** 🛠 **Build from scratch** — use Python + PIL or JS + SVG to generate a cassette J-card with the locked palette (warm paper, terracotta accent) + custom text. The cassette-mesh template is a Half-Light-Hours concept; we own the design system. Build SVG template → rasterize via Cairo or Playwright. This is **L7 in the pipeline** and a Day 9 build task.

### 2.2 Vinyl-record mockup generators

Same situation — no good open-source option. Photoshop/GIMP templates dominate.

**Recommendation:** 🛠 **Skip for v1** — not in the M02 (scope) options. Vinyl is a v2 physical-release feature.

### 2.3 Lyric-video JavaScript libraries

Found:
- **Remotion** (https://www.remotion.dev/) — React-based video framework. Can build lyric-video components declaratively. Heavy dep.
- **MyKaraoke** — karaoke-style lyric video creator (uses Remotion under the hood).
- **lyrics-fetcher** (npm 1.0.2) — fetches synced lyrics from LRClib. Useful side-channel.

**Recommendation:** 🛠 **Build lightweight** for L11 social bundle / L10 videos. Use Remotion if we're already using React for the studio UI (Day 5+). For Day 1, just use mmx video_generate with `--prompt` describing the video style — model can handle lyric overlay if we generate the visual.

---

## 3. Database / Daemon

### 3.1 Quart (async web framework)

**What it does:** Async Flask alternative. Native ASGI, WebSocket support. https://quart.palletsprojects.com/

**Why for sonic-studio:** Q37 in v3.2 plan locks WebSocket as the real-time chat mechanism. Quart is the cleanest stdlib-compatible choice (Flask API, async under the hood).

**Install:** `pip install quart`

**Recommendation:** ✅ **Install** — for Day 3 (HTTP daemon + WS endpoint). If Quart proves problematic (e.g. NSSM doesn't survive the upgrade), fallback is FastAPI.

### 3.2 FastAPI

**What it does:** Async web framework with auto OpenAPI docs. Heavier than Quart but better tooling.

**Why for sonic-studio:** Alternative to Quart. More popular = more community examples.

**Recommendation:** ⚠️ **Skip** for v1 — Quart is more aligned with the "stdlib + minimal deps" ethos. Switch to FastAPI only if Quart has integration issues with our Servy/NSSM service wrapper.

### 3.3 Python sqlite3 advisory lock pattern

**Pattern (verified from SQLite docs):**
```python
import sqlite3

conn = sqlite3.connect('.meta/sonic-studio.db', isolation_level=None)  # autocommit
conn.execute('PRAGMA journal_mode = WAL')
conn.execute('PRAGMA busy_timeout = 5000')  # 5s timeout
conn.execute('PRAGMA foreign_keys = ON')

def take_lock(conn, timeout=10):
    """Acquire the build-skill lock. Returns True on success."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn.execute('BEGIN IMMEDIATE')  # exclusive write lock
            conn.execute('SELECT 1 FROM build_skill_lock WHERE id = 1')
            conn.execute('UPDATE build_skill_lock SET taken_at = ? WHERE id = 1', (time.time(),))
            conn.execute('COMMIT')
            return True
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                time.sleep(0.1)
                continue
            raise
    return False
```

**Why for sonic-studio:** Q29, Q29b lock the SQLite advisory lock for build jobs. Without this, concurrent mmx calls would corrupt the database.

**Recommendation:** ✅ **Implement** — Day 2 of v3.2 plan. Code goes in `tools/sonic_studio/build/lock.py`.

### 3.4 watchdog (Python filesystem events)

**What it does:** Watch filesystem for changes. Cross-platform. https://github.com/gorakhargosh/watchdog

**Why for sonic-studio:** Not strictly needed — we already plan to use sweepers (cron-style polling). But could speed up file-change detection for the OneDrive mirror.

**Recommendation:** ⚠️ **Skip for v1** — sweepers are sufficient (Q32/Q34). Add watchdog in v2 if polling latency matters.

### 3.5 apscheduler vs schedule (sweeper scheduling)

**apscheduler:** More powerful, supports cron-style triggers, persistent jobs. https://github.com/agronholm/apscheduler
**schedule:** Simpler, in-process scheduler.

**Why for sonic-studio:** Daemon has 5 sweepers (idle_pause, wal_checkpoint, quota, mirror, log_rotate). All need periodic execution.

**Recommendation:** ✅ **Use stdlib `threading.Timer`** — for a daemon with 5 fixed sweepers, the stdlib is sufficient. APScheduler is overkill. Document this choice in the daemon README.

---

## 4. UI / UX (already covered in ux-research-2026-07-30/ux-patterns-memo.md)

### 4.1 wavesurfer.js (audio waveform)

**What it does:** Web Audio API waveform renderer. Regions, plugins, click-to-seek. https://wavesurfer.xyz/

**Recommendation:** ✅ **Install** — for L4 audio player + L2 lyrics editor (timestamped sync). Use the regions plugin to mark section boundaries.

### 4.2 peaks.js (BBC waveform editor)

**What it does:** BBC's waveform editor. More powerful than wavesurfer for editing, but heavier.

**Recommendation:** ⚠️ **Skip** — wavesurfer covers our use case. Peaks.js is for audio editing apps (like a web-based DAW). We're a player, not an editor.

### 4.3 DAW web references (BandLab, Soundtrap, BandLab)

**Recommendation:** ✅ **Investigate further** — covered in `ux-patterns-memo.md` §10 (synthesis table). For Day 5+ UI work.

---

## 5. Distribution / DSP

### 5.1 DDEX XML Python libraries

**Status:** No production-quality Python DDEX library exists. `ddex-parser` (PyPI) is a partial sync-license parser. `python-ddex` is abandoned. Best bet: use `lxml` directly with the DDEX ERN 4.3 spec.

**Recommendation:** 🛠 **Build minimal DDEX writer** — Day 12 of v3.2 plan. Output ERN 4.3 XML for `full-dsp` distribution path. Use `xmltodict` for parsing, `lxml.etree` for writing.

### 5.2 Spotify metadata spec

**What it requires:** ISRC (per-track, 12 chars), UPC (per-album, 12-13 digits), copyright ℗ + © lines, territory, release date, genre tags.

**Where ISRC/UPC come from:** NOT locally generated. They come from a registered ISRC manager (Routenote, DistroKid, your label). Local "generate a fake ISRC" is meaningless — DSPs reject.

**Recommendation:** ✅ **Don't store fake ISRCs.** When user picks `R14: full-dsp` or `physical-and-dsp`, the studio should integrate with a distributor's API OR prompt user to paste their assigned ISRCs. Don't pre-generate. (Already locked in `tools-memo.md`.)

### 5.3 musicbrainz (open music metadata)

**What it does:** Open encyclopedia of music metadata. Has ISRCs, cover art, label info. https://musicbrainz.org/

**Why for sonic-studio:** Verify our tracks don't accidentally duplicate existing ISRCs. Pull reference track metadata for M04 (references).

**Recommendation:** ✅ **Install** — `pip install musicbrainzngs`. Useful for M04 cross-reference and post-distribution verification.

---

## 6. Image / Cover Art

### 6.1 Pillow (PIL fork)

**What it does:** Image processing in pure Python. https://pillow.readthedocs.io/

**Why for sonic-studio:** Cover art variants (square crop for Instagram, 1400x1400 for Bandcamp, 1280x1440 header). Convert PNG ↔ JPG ↔ WebP. Embed into mp3 APIC frame.

**Install:** `pip install Pillow`

**Recommendation:** ✅ **Install** — Day 5+ (when L6 cover art starts). Lightweight, ubiquitous.

### 6.2 pycairo vs skia-python

**pycairo:** Python bindings for Cairo graphics. Good for vector rendering. https://pycairo.readthedocs.io/
**skia-python:** Python bindings for Skia (Google's graphics engine). Newer, more capable.

**Why for sonic-studio:** SVG → PNG rasterization for cassette stickers (L7) and other vector deliverables.

**Recommendation:** ✅ **Use pycairo** — it's stable, simple, and covers SVG-to-PNG for our sticker templates. skia-python is newer but adds binary complexity.

### 6.3 sharp (Node.js image processing)

**Why for sonic-studio:** If the studio UI needs to render thumbnails or process uploads client-side.

**Recommendation:** ⚠️ **Defer** — server-side Pillow handles all current needs. Client-side sharp is only relevant for drag-and-drop upload UI.

---

## 7. Lyrics / Creative

### 7.1 whisper-cpp / openai-whisper

**What it does:** Speech-to-text. Word-level timestamps. https://github.com/openai/whisper

**Why for sonic-studio:** Transcribe generated audio back to text for the lyrics-quality scorer. Currently the scorer takes text only.

**Install:**
- `pip install openai-whisper` (Python wrapper)
- Need ~3GB model (medium or large-v3)

**Recommendation:** ⏸ **Defer to user session** — installing 3GB is user's call. The scorer already works on user-provided lyrics text.

### 7.2 pronouncing (PyPI)

**What it does:** CMU pronouncing dictionary access. Rhyme detection, syllable counting. https://pypi.org/project/pronouncing/

**Why for sonic-studio:** Better rhyme detection than my naive "last 2 chars match" heuristic in `score_lyrics.py`. Real CMU dict = vowel-class-aware rhyming.

**Install:** `pip install pronouncing`

**Recommendation:** ✅ **Install** — small dep, big quality improvement. Use in `score_lyrics.py` v2.

### 7.3 pyphen

**What it does:** Syllable hyphenation for 50+ languages. https://github.com/Kozea/pyphen

**Why for sonic-studio:** Better syllable counting than my "count vowel groups" heuristic. Especially for non-English lyrics.

**Install:** `pip install pyphen`

**Recommendation:** ✅ **Install** — same as pronouncing, drop-in improvement for `score_lyrics.py`.

---

## 8. Summary — install vs build decision matrix

### ✅ Install (do these now or before relevant day)

| Tool | Purpose | When | Effort |
|---|---|---|---|
| mutagen 1.48.1 | ID3v2.4 metadata | Day 5 | ✅ done |
| Pillow | Image processing | Day 5 | 10s |
| pycairo | SVG → PNG | Day 9 (cassette) | 30s |
| spotipy | Spotify read | Day 10 | 10s + auth |
| musicbrainzngs | Metadata cross-ref | Day 10 | 10s |
| pronouncing | Rhyme detection | Day 5 | 10s |
| pyphen | Syllable counting | Day 5 | 10s |
| Quart | ASGI + WebSocket | Day 3 | 30s |

### ⚠️ Defer (install only when needed)

| Tool | Why defer | Re-evaluate at |
|---|---|---|
| lyrics-transcriber | Needs whisper + Genius key | L4 lyrics editor |
| openai-whisper | 3GB model | L4 if automation needed |
| librosa | Heavy deps | L4 if BPM detection needed |
| watchdog | Sweepers suffice | v2 if latency matters |
| sharp | Pillow handles server-side | v2 if client upload UI |

### ⚠️ Skip

| Tool | Why |
|---|---|
| ffmpeg-python | subprocess is cleaner here |
| pydub | ffmpeg acrossfade is enough |
| FastAPI | Quart is more stdlib-aligned |
| APScheduler | stdlib Timer is enough |
| peaks.js | wavesurfer covers player needs |
| schwa/spleeter | Not needed — mono output already |

### 🛠 Build from scratch

| Need | Approach |
|---|---|
| Cassette J-card renderer | SVG template + pycairo rasterizer, build Day 9 |
| DDEX ERN 4.3 writer | lxml + spec doc, build Day 12 |
| Lyric video renderer | Remotion (if React already in UI), else skip for v1 |
| Vinyl mockup | Skip v1, defer to v2 |

---

## 9. Top 5 wins (smallest install, biggest payoff)

1. **pronouncing + pyphen** → drop-in upgrade to `score_lyrics.py` (better rhyme + syllable detection). 20s install.
2. **Pillow + pycairo** → cassette sticker generation (L7). 40s install.
3. **Quart** → enables Q37 WebSocket plan (real-time chat). 30s install.
4. **mutagen (already installed)** → wire into `finalize-album.py` (Day 5). Zero new install.
5. **spotipy + musicbrainzngs** → post-distribution validation + M04 reference lookup (Day 10+). 20s install.

---

## Files

- `FINDINGS.md` — this file (15+ KB)
- All source data + verification lives in `audio-quality-2026-07-30/tools-memo.md` (overlapping scope but more concrete).