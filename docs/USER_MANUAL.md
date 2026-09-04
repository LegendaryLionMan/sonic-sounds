# sonic-studio · User Manual

> Plan an album, walk it through the 12-layer build pipeline, ship a
> final release. This manual is the entry point for every new user.

**Album-studio v3.4 · Mixtape '85** · Last updated 2026-09-02

---

## 1. What is sonic-studio?

Album-studio is a workspace for end-to-end music album creation:

1. **Intake** — answer 26 questions that define the album's scope, music, lyrics, visual, distribution, technical.
2. **Brief** — those answers lock into a structured "concept brief" the agent uses to drive generation.
3. **Build** — the 12-layer pipeline (Brief → Lyrics Drafts → Lyrics Finalize → Vocal Recordings → Instrumental → Cover Art → Cassette Sticker → Mixdown → Mastering → Metadata/ISRC → Distribution → Finalize) executes layer-by-layer with click-to-invoke buttons.
4. **Release** — finalize produces a mastered release with loudness-report, ID3 tags, and a status flip from `active` → `done`.

### 1.1 How this fits with the music-album-planning-questionnaire skill

Album-studio is the **web UI** companion to the existing `music-album-planning-questionnaire` skill. The skill drives the **content** (what to ask, what reference bands to surface); sonic-studio drives the **state** (which questions are answered, which layers are running, which files are written).

When the user says "I want to make an album", the skill triggers first (the questionnaire), and once the brief is locked, the studio opens the workspace.

---

## 2. The UX flow

```mermaid
flowchart TD
    Start([User opens sonic-studio]) --> Pick[Pick or create album]

    Pick -->|Existing album| AlbumDetail[Album drawer opens]
    Pick -->|New album| Intake[26-question intake form]

    Intake --> M01toM09[Mandatory questions M01-M09]
    M01toM09 --> R09toR14[Recommended questions R09-R14]
    R09toR14 --> E15toE21[Optional questions E15-E21]
    E15toM09 --> BriefLock[Concept brief locks to album_briefs]
    BriefLock --> SessionOpen[First session auto-opens]

    AlbumDetail --> OpenSession[Click Open Session]
    OpenSession --> Studio[Studio page renders]

    SessionOpen --> Studio

    Studio --> Cover[Album cover image loads]
    Cover --> Pipeline[12-layer pipeline renders]
    Pipeline --> Tracks[10 track list with play buttons]
    Tracks --> Events[Live events log]
    Events --> Decisions[Locked decisions panel]
    Decisions --> Footer[Footer: daemon status, quota bars]

    Pipeline --> InvokeBtn{User clicks [INVOKE]}
    InvokeBtn -->|Layer 8 no-op| AudioMaster[Audio mastering job]
    InvokeBtn -->|Layer 3| Lyrics[Lyrics finalize job]
    InvokeBtn -->|Other layers| MmxCall[mmx music/image generation call]
    MmxCall --> RunEvents[build_started + build_succeeded events written]
    AudioMaster --> RunEvents
    Lyrics --> RunEvents
    RunEvents --> AlbumCover

    Tracks --> PlayBtn{User clicks ▷}
    PlayBtn --> AudioPlayer[Audio element loads MP3 from OneDrive]
    AudioPlayer --> AudioRange[HTTP Range request streams bytes 0-N]
    AudioRange --> Playing[Audio plays in browser]

    Studio --> Pause[Click PAUSE]
    Studio --> Resume[Click RESUME]
    Studio --> Complete[Click COMPLETE]
    Complete --> Done[Session status = done]
    Done --> Finalize{User clicks FINALIZE}
    Finalize --> MasterLoud[Two-pass ffmpeg loudnorm to -14 LUFS]
    MasterLoud --> WriteTags[ID3v2.4 tags via mutagen]
    WriteTags --> ReleaseReady[Mastered release in albums/<id>/_master/]
    ReleaseReady --> Reopen{Reopen?}
    Reopen -->|Yes| Studio
    Reopen -->|No| Done

    style Start fill:#1a1a1a,stroke:#666
    style BriefLock fill:#0d2818,stroke:#2dd4bf
    style Studio fill:#0d2818,stroke:#2dd4bf
    style Playing fill:#0d2818,stroke:#2dd4bf
    style ReleaseReady fill:#0d2818,stroke:#2dd4bf
    style Done fill:#1a1a1a,stroke:#666
```

The flow has three natural exits: **(a)** short albums that stop at Cover Art or Mixdown, **(b)** mid-length albums that publish via Distribution, **(c)** full release packages that go through Finalize.

---

## 3. The pages

### 3.1 Library — the cassette wall

`http://127.0.0.1:8765/site/library.html`

```
sonic-studio / library
[1 ALBUM · 10 TRACKS]                                    ⌘K
─────────────────────────────────────────────────────────────────
the cassette wall
Every album you've ever made. Click a cassette to drop it into the player.
/albums · 1
your collection
┌─────────────────────────────────┐
│  [ALBUM COVER ART]               │   ← cover from /api/albums/<id>/cover
│                                  │
├─────────────────────────────────┤
│ ACTIVE · 40 MIN · 10 TRACKS     │   ← eyebrow
│ Half-Light Hours                │
│ Album id: half-light-hours      │
│                                  │
│ [▷ Open]                         │   ← jumps to albums.html?album=...
└─────────────────────────────────┘
```

**What it does.** Every album ever created is a cassette card. Click a card to open it. Click `[▷ Open]` to jump to the album-detail page.

**Live data shown.** Cover art (from OneDrive canonical), album title, artist, status, runtime in minutes, track count.

### 3.2 Albums — the working surface

`http://127.0.0.1:8765/site/albums.html`

```
sonic-studio / albums
[1 ACTIVE]                                       [+ NEW ALBUM] [⌘K]
─────────────────────────────────────────────────────────────────
ALBUMS IN PROGRESS
Max 3 active sessions. 12h idle auto-pause. Every build layer tracked via the daemon.

ACTIVE SESSIONS: 1    ALBUMS: 1    DONE: 0

ACTIVE · LIVE SESSIONS
─────────────────────────────────────
  LAYER UNDEFINED ·                  ← layer derived from build events
  [⏸ PAUSE] [✓ COMPLETE] [STUDIO]
─────────────────────────────────────

LIBRARY · ALL ALBUMS
┌──────────┐ ┌──────────┐ ┌──────────┐
│ [cover]  │ │ [cover]  │ │ [cover]  │
│ Half...  │ │ Twenty..│ │ New...   │
│ ACTIVE   │ │ ACTIVE   │ │ ACTIVE   │
└──────────┘ └──────────┘ └──────────┘

DAEMON · 127.0.0.1:8765
1 SESSIONS TRACKED · 9 LAYERS · MIXTAPE '85
```

**What it does.** Two panes stacked: active sessions on top (with lifecycle buttons), the full library below. Click an album card → opens the album drawer (right side panel) with detail info.

### 3.3 Studio — the main working page

`http://127.0.0.1:8765/site/studio.html?session=<session_id>`

```
sonic-studio / studio
[Half-Light Hours · Brief · active]   ACTIVE   [← Albums] [⌘K]
─────────────────────────────────────────────────────────────────
/SESSION                                  /ALBUM-COVER · MIXTAPE '85
                                          COVER
HALF-LIGHT HOURS                          ┌───────────────┐
maren-sol                                 │ [cover art]    │ ← /api/albums/<id>/cover
                                          │               │
LAYER —  PHASE —                          │               │
RUNTIME —   LAST ACTIVITY 2h ago          │               │
                                          │               │
[⏸ PAUSE] [▶ RESUME] [✓ COMPLETE]        └───────────────┘
                                          Half-Light Hours · 40 MIN
SESSION: 88c03b60-...
ALBUM ID: half-light-hours
OPENED: 2026-09-02 16:42
─────────────────────────────────────────────────────────────────
/PIPELINE · 12-LAYER BUILD
THE BUILD
01 BRIEF               [INVOKE]
02 LYRICS DRAFTS       [INVOKE]
03 LYRICS FINALIZE      [INVOKE]
04 VOCAL RECORDINGS    [INVOKE]
05 INSTRUMENTAL        [INVOKE]
06 COVER ART           [INVOKE]
07 MIXDOWN             [INVOKE]
08 MASTERING           [INVOKE]
09 DISTRIBUTION        [INVOKE]
─────────────────────────────────────────────────────────────────
/TRACKS · THIS ALBUM
01 DUSK INDEX                3:24  [▷]
02 LEASE ON A VANISHING      4:12  [▷]
03 HALF-LIGHT HOURS          4:38  [▷]
04 YOU, IN STATIC            3:18  [▷]
05 THE CARTOGRAPHER          3:56  [▷]
06 BORROWED COATS            4:02  [▷]
07 MAPS FOR THE DISAPPEARING 4:24  [▷]
08 SILVER BAY                3:08  [▷]
09 WHAT THE WINDOW KNEW      4:46  [▷]
10 DAWN INDEX (REPRISE)      3:36  [▷]
─────────────────────────────────────────────────────────────────
/EVENTS · LIVE CHAT LOG                  /DECISIONS · LOCKED-IN CHOICES
DAEMON · 127.0.0.1:8765
```

**What it does.** This is where you spend most of your time. The studio has:
- A sidebar with session metadata and lifecycle buttons (Pause / Resume / Complete)
- An album cover image (loaded live from `/api/albums/<id>/cover`)
- A 9-layer build pipeline (visible because the studio shows the first 9 of 12 layers; the remaining 3 are admin/press-kit/finalize accessible via the [invoke] workflow)
- A track list with **audio play buttons** — click `[▷]` and the MP3 streams from OneDrive via HTTP Range
- An events panel that polls every 2 seconds for build events
- A decisions panel for locked concept-brief answers (M01–M09 mandatory)

**Layer 8 (Mastering)** is a no-op layer — clicking [INVOKE] writes a MANUAL.md describing what the human mastering step should be, no actual audio processing runs.

### 3.4 Intake — the front door

`http://127.0.0.1:8765/site/intake.html`

26 questions across three tiers:
- **M01–M09** (mandatory) — concept, scope, genre, references, vocal, language, runtime, artist, sonic-DNA
- **R09–R14** (recommended) — title, tracklist, motif, production, lyrical source, distribution
- **E15–E21** (optional) — arc, influences, cover-art, anchor, press-scope, music-videos, deadline

Submitting the form locks the brief into the database and auto-creates an album + first session.

---

## 4. Audio playback — how the music player works

The studio's `[▷]` button next to each track triggers:

```javascript
// site/studio.js — loadTrack()
el.src = `/api/audio/${encodeURIComponent(trackId)}`;
```

That endpoint (Day 10 + Day 11 fix in commit `443a036`):

1. Looks up the track in the `tracks` table to get `mp3_path` and `album_id`
2. Resolves the MP3 file from one of these candidates (in order):
   - `<project_root>/<mp3_path>`
   - `<project_root>/music/<basename>`
   - `~/OneDrive/Hermes/albums/<album_id>/<mp3_path>` ← canonical
   - `~/OneDrive/Hermes/albums/<album_id>/music/<basename>`
3. Streams with `send_file(..., conditional=True, mimetype="audio/mpeg")` — the `conditional=True` enables HTTP Range support, so the browser can scrub without re-downloading

The seed stores MP3 paths relative to the OneDrive canonical location (`~/OneDrive/Hermes/albums/<album_id>/music/`), so the canonical path always resolves in production.

**Cover art uses the same pattern** at `/api/albums/<id>/cover`.

---

## 5. The interactive user guide — onboarding walkthrough

When you first open the studio, you'll see a brief intro overlay that walks you through the four core actions:

```
┌─────────────────────────────────────────────────────────────────┐
│  Welcome to sonic-studio.                                       │
│  ━━━━━━━━━━━━━━━━━━━━━                                          │
│                                                                  │
│  This is the STUDIO. The album you're working on is at the      │
│  top. Each [INVOKE] button runs one pipeline layer.              │
│                                                                  │
│  Let's try the first one.                                        │
│  ▸ Click [INVOKE] on layer 01 (Brief)                            │
│                                                                  │
│                          [ SKIP ]   [ NEXT → ]                  │
└─────────────────────────────────────────────────────────────────┘
```

The guide walks you through 4 steps:

1. **Click [INVOKE] on layer 01** — runs the brief layer, you'll see the build event appear in the events panel below.
2. **Click the [▷] button next to track 01** — loads the audio player, plays "Dusk Index" (3:24).
3. **Click [⏸ PAUSE] in the sidebar** — flips session status to `paused`, you can resume later.
4. **Lock a decision** — go to `/api/decisions` (or use the drawer) and lock M01 with the album concept.

Each step has a **[ NEXT → ]** button. The overlay auto-dismisses when you complete the step.

### 5.1 How to enable the guide

The guide is opt-in per session. To show it:

```bash
# Open the studio with the guide enabled:
http://127.0.0.1:8765/site/studio.html?session=<id>&guide=on
```

Or click the **❓ Help** button in the studio footer. The guide remembers dismissal per-session in `localStorage` so it doesn't auto-popup every visit.

---

## 6. Common workflows

### 6.1 Open an existing album and listen to a track

1. Go to **Library** (`/site/library.html`) → click the cassette card
2. Click **[▷ Open]** → drops you into the **Albums** page
3. Click the album card → opens the drawer → click **[Open Session]** (or the drawer is right-click → "Open session")
4. The **Studio** opens with the album's session loaded
5. Click the **[▷]** button next to any track → MP3 streams in the audio player

### 6.2 Invoke a build layer

1. In the **Studio**, find the pipeline section (9 layers under "PIPELINE · 12-LAYER BUILD")
2. Click **[INVOKE]** on the layer you want to run
3. The button optimistically goes to "queued" (yellow), then "running…" (yellow pulse), then "✓ done" (green, disabled) on success
4. The events panel at the bottom shows `build_started` and `build_succeeded` events
5. The pipeline cell lights up as `active` (cyan border) for the new layer

### 6.3 Submit the intake for a new album

1. Go to the **Intake** page (`/site/intake.html`)
2. Answer M01–M09 (mandatory). For an album of 40 minutes / 10 tracks / dream-folk:
   - M01_concept: "a year of leaving, cities, a love, an old self"
   - M03_genre: "dream-folk"
   - M04_references: 3 reference bands
   - M05_vocal: "breathy mezzo-soprano, close-mic, intimate"
   - M07_runtime: "40"
   - M08_artist: "maren-sol"
   - M09_sonicDNA: a JSON block (genre, vocals, mood, instruments, references, tempoProfile)
3. Submit. The brief is locked to `album_briefs`. An album + first session are auto-created.
4. You're redirected to the studio for the new album.

### 6.4 Finalize + reopen

When all 9 layers in the studio have been invoked, click **[✓ COMPLETE]** to mark the session done. Then:

1. `POST /api/albums/<id>/finalize` — runs the mastering pipeline
2. The daemon's `build.runner.run_finalize()`:
   - Master with ffmpeg loudnorm two-pass (`target_lufs=-14` for Spotify, `true_peak_dbtp=-1`)
   - Write ID3v2.4 tags (artist, album, title, track #, year, ISRC, front-cover APIC) via mutagen
   - Write `loudness-report.json` to `<base>/<album>/_master/`
   - Flip album `status: active → done`
3. To reopen: `POST /api/albums/<id>/reopen` → flips back to `active`

---

## 7. The seed data — what `python -m db.seed` produces

The seed populates Maren Sol's "Half-Light Hours" as the canonical example:

| Layer | Title | Duration | ISRC |
|---|---|---|---|
| 01 | Dusk Index | 3:24 | USS1Z2500001 |
| 02 | Lease on a Vanishing | 4:12 | USS1Z2500002 |
| 03 | Half-Light Hours | 4:38 | USS1Z2500003 |
| 04 | You, in Static | 3:18 | USS1Z2500004 |
| 05 | The Cartographer | 3:56 | USS1Z2500005 |
| 06 | Borrowed Coats | 4:02 | USS1Z2500006 |
| 07 | Maps for the Disappearing | 4:24 | USS1Z2500007 |
| 08 | Silver Bay | 3:08 | USS1Z2500008 |
| 09 | What the Window Knew | 4:46 | USS1Z2500009 |
| 10 | Dawn Index (Reprise) | 3:36 | USS1Z2500010 |

Total runtime: 39m 24s (40 min planned).

### Seeded covers / artwork (16 assets total)

- 2 cover art front squares (1000px and 3000px)
- 2 cover art back squares (1000px and 3000px)
- 5 posters (16:9, 3:4, 9:16, 1:1, stage)
- 5 merch (tshirt, vinyl sleeve, tour routing)
- 10 lyrics markdown files
- 4 press files (DistroKid guide, EPK, podcast script, podcast mp3)
- 14 videos (5 concepts + 13 storyboard frames)

All assets live in the canonical location: `~/OneDrive/Hermes/albums/Half-Light-Hours/`.

---

## 7.5 Screenshots

Page captures live in [`docs/assets/screenshots/`](assets/screenshots/README.md) (mirrored to `~/OneDrive/Hermes/Agents/planning/sonic-studio/docs/assets/screenshots/` per R7). The naming convention is:

- `01-studio.png` — Maren Sol's session view
- `02-albums.png` — Album grid
- `03-library.png` — Cassette wall
- `04-intake.png` — Intake form
- `05-guide.png` — Interactive user guide overlay

To capture a fresh screenshot: open the relevant URL in Chrome, take a screenshot (Win+Shift+S, the Snipping Tool, or your favorite capture tool), and drop the PNG into this folder. The README.md in the folder documents the convention.

---

## 8. API quick reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Daemon health (6 subsystems) |
| GET | `/api/albums` | List albums (with `?status=` filter) |
| GET | `/api/albums/<id>` | Get one album |
| GET | `/api/albums/<id>/cover` | Stream cover art JPEG (with OneDrive fallback) |
| GET | `/api/albums/<id>/tracks` | List tracks |
| GET | `/api/albums/<id>/assets` | List assets |
| GET | `/api/albums/<id>/sessions` | List sessions for album |
| POST | `/api/albums` | Create album |
| PATCH | `/api/albums/<id>` | Update album |
| POST | `/api/albums/<id>/archive` | Soft-delete (status → archived) |
| POST | `/api/albums/<id>/finalize` | Master + tag + status flip |
| POST | `/api/albums/<id>/reopen` | status → active |
| GET | `/api/sessions` | List sessions |
| POST | `/api/sessions` | Open a session |
| POST | `/api/sessions/<id>/pause` | Pause |
| POST | `/api/sessions/<id>/resume` | Resume |
| POST | `/api/sessions/<id>/complete` | Complete |
| GET | `/api/sessions/<id>/events?since_id=N` | Events for session |
| GET | `/api/sessions/<id>/decisions` | Decisions for session |
| GET | `/api/events?album=<id>` | All events for an album (including global build events) |
| POST | `/api/events` | Append event |
| POST | `/api/decisions` | Create / lock a decision |
| PATCH | `/api/decisions/<id>` | Update answer (bumps locked_at) |
| POST | `/api/build/invoke` | Queue + run a build job |
| GET | `/api/build/jobs` | List jobs |
| GET | `/api/build/jobs/<id>` | Get one job |
| POST | `/api/build/jobs/<id>/cancel` | Cancel queued job |
| POST | `/api/intake/submit` | Submit intake form (FormData or JSON) |
| GET | `/api/intake/brief/<id>` | Get the brief for an album |
| GET | `/api/intake/briefs` | List all briefs |
| GET | `/api/audio/<track_id>` | Stream MP3 with Range support |

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| "Preview is not opening in Chrome" | The daemon isn't running. Start it: `python -m build.serve --host 127.0.0.1 --port 8765` |
| Audio doesn't play | Check that the daemon is running (`/api/health` returns ok). Check the browser console for `404` on `/api/audio/<track_id>`. If 404, the MP3 file may not exist on disk — verify the path under `~/OneDrive/Hermes/albums/<id>/music/` |
| Cover image is blank | Check that `cover_path` is set on the album row and the file exists. The endpoint falls back through 5 candidate paths |
| Pipeline doesn't update | The events panel polls every 2s. If it doesn't refresh, check the daemon log for events-related errors |
| "Tracks: ?" appears | Run the seed: `python -m db.seed --force`. The library.js uses `/api/albums?track_count` which is decorated server-side |

---

## 10. For developers

- **Backend:** `build/serve.py` (Quart + SQLite). All handlers in `build/handlers_*.py`.
- **Frontend:** `site/*.html` + `site/*.js` + `site/*.module.css` (vanilla JS, no framework).
- **Database:** SQLite at `<project_root>/.meta/sonic-studio.db` (or `SONIC_STUDIO_DB_PATH`).
- **Migrations:** `db/migrations/` (auto-applied at daemon startup).
- **Tests:** `tests/test_*.py` — 377 tests, run with `pytest tests/ build/`.
- **Plan:** `docs/decisions/` for ADRs.

See [TECHNICAL.md](TECHNICAL.md) for the architecture deep-dive.
