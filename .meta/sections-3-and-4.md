# Section 3 — Intake form UX spec

## 3.1 Goals

The intake form (`site/intake.html`) is the **front door** for someone starting a new album project. It must:

1. **Not feel like a form** — feel like the first chapter of an editor's interview
2. **Save progress automatically** — never lose work to a closed tab
3. **Export to JSON** — the agent reads JSON, not HTML form data
4. **Gate generation at the 8 mandatory topics** — same gate as `music-album-planning-questionnaire`

## 3.2 Three-tier grouping (matches the planning skill)

The 21 topics are grouped into 3 tiers that map 1:1 to the questionnaire skill:

| Tier | Badge color | Topics | What it means |
|---|---|---|---|
| **Mandatory (M)** | `--accent` border, ALL CAPS tag | 8 topics | Album cannot be generated without these. Form refuses to export until all 8 are filled. |
| **Recommended (R)** | `--ink-soft` border, ALL CAPS tag | 6 topics | Strongly suggested. Defaults applied if skipped (clearly marked as defaults). |
| **Extra (E)** | `--rule` border, ALL CAPS tag | 7 topics | Creative extras. Pure opt-in. |

The 21 topics, in their exact questionnaire order:

| # | Tier | Question prompt (form) |
|---|---|---|
| M·01 | Mandatory | What is this album *about*? (the emotional/narrative heart — not genre) |
| M·02 | Mandatory | What scope? (single / EP / album / double-feature / concept piece) |
| M·03 | Mandatory | What genre direction? (primary family at minimum) |
| M·04 | Mandatory | 1–3 reference artists whose sound you want to channel |
| M·05 | Mandatory | Vocal approach (solo / duet / choir / spoken word / instrumental + voice character) |
| M·06 | Mandatory | Language(s) for lyrics |
| M·07 | Mandatory | Runtime target per track (radio edit / standard / extended / immersive) |
| M·08 | Mandatory | Artist identity (stage name — new or existing persona) |
| R·09 | Recommended | Working album title (placeholder OK) |
| R·10 | Recommended | Tracklist placeholder (rough song titles or themes) |
| R·11 | Recommended | Visual motif (one recurring image — a window, a color, an object) |
| R·12 | Recommended | Production style (stripped / full band / electronic / cinematic / hybrid) |
| R·13 | Recommended | Lyrical source (you write / agent writes / co-write) |
| R·14 | Recommended | Distribution intent (just for me / RouteNote Free / full DSP / physical + DSP) |
| E·15 | Extra | Emotional arc across tracks (shape of the listening experience) |
| E·16 | Extra | Non-music influences (books, films, places, seasons that shaped the sound) |
| E·17 | Extra | Cover art direction (palette, photo vs illustration, typography mood) |
| E·18 | Extra | Physical anchor (the ONE thing the listener should remember) |
| E·19 | Extra | Press / rollout scope (music only / + press kit / + social / + everything) |
| E·20 | Extra | Music videos (0 / 1–2 / 3–5) |
| E·21 | Extra | Deadlines / pressure (when does this need to ship) |

## 3.3 Input shapes per topic

Each topic gets the input shape that fits the kind of answer:

| Topic | Input shape |
|---|---|
| M·01, R·11, R·13, R·15, R·18, E·16, E·17, E·18, E·21 | `<textarea>` (open text) |
| M·02, R·14, R·12, R·15, E·19, E·20 | `<select>` with curated options |
| M·03 | `<input type="text">` + datalist of genre suggestions |
| M·04 | `<input type="text">` × 3 (three slots for three artists) |
| M·05 | `<select>` (vocal approach) + `<textarea>` (voice character) |
| M·06 | `<input type="text">` + comma-separated language tags |
| M·07 | `<select>` (runtime target) |
| M·08 | `<input type="text">` (artist stage name) |
| R·09 | `<input type="text">` (album title) |
| R·10 | 12 numbered `<input type="text">` rows (song titles or themes) |
| E·21 | `<input type="date">` |

## 3.4 Auto-save behavior

- **Storage:** `localStorage` key `sonic-studio.intake.<slug>` where `<slug>` is derived from the artist name + today's date.
- **Frequency:** debounced 800ms after the last keystroke.
- **Visible feedback:** A small `--sans-mono` label below the form masthead shows `SAVED 09:24:35 UTC` and updates on each save.
- **On load:** the form auto-hydrates from the most recent `sonic-studio.intake.*` key in localStorage.
- **On export:** the form clears the localStorage key after successful JSON download (and writes `intake-data/<slug>.json` to disk via the agent).

## 3.5 Mandatory-gate behavior

The form tracks a `mandatoryResolved` counter that increments per filled mandatory question. The "Generate CONCEPT-BRIEF" button:

- **Disabled** when `mandatoryResolved < 8`. Visual: terracotta `--rule` border, `cursor: not-allowed`, tooltip explains the gap.
- **Enabled** when `mandatoryResolved === 8`. Visual: solid `--accent` border, hover state lifts to `--accent-soft`.

On click when enabled:
- The form composes a JSON object from all 21 fields.
- Triggers download as `intake-data/<slug>.json`.
- Shows a confirmation card in the page: "Brief exported. Open a chat with Penelope and say 'approve brief <slug>' to start the build pipeline."

## 3.6 Visual layout

```
┌──────────────────────────────────────────────────────────┐
│  sonic-studio                                             │  <- masthead
│  intake — 21 questions for the album you haven't made yet │
│                                                           │
│  ▌ SAVED 09:24:35 UTC                                    │
├──────────────────────────────────────────────────────────┤
│  MANDATORY · 8 (gate: all 8 to export)                   │  <- tier band
│  ── resolved 0 of 8 ─────────────────────────────────    │
│                                                           │
│  M·01 ──────  ALBUM CONCEPT                              │
│             What is this album about?                     │
│             [textarea, full width]                        │
│                                                           │
│  M·02 ──────  PROJECT SCOPE                              │
│             What scope?                                   │
│             [select: single / EP / album / ...]            │
│                                                           │
│  ... 19 more ...                                          │
│                                                           │
├──────────────────────────────────────────────────────────┤
│              [ Generate CONCEPT-BRIEF ]                  │  <- sticky footer
└──────────────────────────────────────────────────────────┘
```

The form is one long scrolling page. No multi-step wizard, no tabs. The questionnaire skill rejects multi-step because the conversation flow is meant to be top-to-bottom. The site honors that.

## 3.7 What the form does NOT do

- Not a multi-page wizard
- Not connected to a backend (the agent does the export-to-disk step in a chat, not the page)
- Not a save indicator on the server (localStorage is the truth until the user downloads the JSON)
- Not a "preview your brief" — the JSON download is the handoff

---

# Section 4 — Dashboard UX spec

## 4.1 Goals

The dashboard (`site/dashboard.html`) is the **status board** for an album as it moves through the 12-layer pipeline. It must:

1. **Read state from a JSON file** (`.meta/state.json`) without any server
2. **Show all 12 layers** with their current status in a single page
3. **Show the brief summary** (artist, album, scope, genre) at the top
4. **Surface the next-action** clearly — what the user should do right now

## 4.2 What state.json looks like

```json
{
  "schemaVersion": "1.0",
  "updatedAt": "2026-07-28T09:24:35Z",
  "album": {
    "slug": "half-light-hours",
    "artist": "Maren Sol",
    "title": "Half-Light Hours",
    "scope": "album",
    "genre": "dream-folk"
  },
  "layers": [
    { "id": 1,  "name": "Artist brand",       "status": "done",        "updatedAt": "..." },
    { "id": 2,  "name": "Tracklist + lyrics",  "status": "done",        "updatedAt": "..." },
    { "id": 3,  "name": "Music tracks",        "status": "done",        "updatedAt": "..." },
    { "id": 4,  "name": "Album cover + posters","status": "done",        "updatedAt": "..." },
    { "id": 5,  "name": "Spotify distribution","status": "todo",        "updatedAt": null },
    ...
  ],
  "nextAction": {
    "for": "user",
    "text": "Approve Spotify package (Layer 5)",
    "link": "music/half-light-hours/spotify/SPOTIFY-DISTRIBUTION-PACKAGE.md"
  }
}
```

## 4.3 Layer status states

A layer can be in one of four states, matching the existing `full-album-release-package` skill vocabulary:

| Status | Badge color | Meaning |
|---|---|---|
| `todo` | `--ink-soft` border, ink text | Not started |
| `in-progress` | `--accent` border, accent text | Agent is working on it |
| `blocked` | `--status-blocked` border, blocked text | User input required or external blocker |
| `done` | `--status-done` border, done text | Approved and complete |

## 4.4 The 12 layers (exact, in pipeline order)

| # | Name | Owner | Default artifact on disk |
|---|---|---|---|
| 1 | Artist brand | Agent (LLM) | `music/<slug>/README.md` |
| 2 | Tracklist + lyrics | Agent (with user checkpoint at STEP 1.5) | `music/<slug>/lyrics/*.md` |
| 3 | Music tracks | Agent (with user checkpoint at STEP 1.7) | `music/<slug>/music/*.mp3` |
| 4 | Album cover + posters | Agent | `music/<slug>/cover-art/*.jpg`, `posters/*.jpg` |
| 5 | Spotify / DistroKid package | Agent | `music/<slug>/spotify/SPOTIFY-DISTRIBUTION-PACKAGE.md` |
| 6 | EPK / Press kit | Agent | `music/<slug>/press/PRESS-KIT.md` |
| 7 | Social rollout (60-day) | Agent | `music/<slug>/social/SOCIAL-ROLLOUT-PLAN.md` |
| 8 | Tour + merch catalog | Agent | `music/<slug>/merch/TOUR-AND-MERCH.md` |
| 9 | Music video concepts + storyboards | Agent | `music/<slug>/videos/VIDEO-CONCEPTS.md` |
| 10 | Podcast / radio interview | Agent | `music/<slug>/press/podcast-interview.mp3` |
| 11 | ID3 metadata embedding | Agent (script) | `music/<slug>/music/tag-manifest.json` |
| 12 | LRC synced lyrics | Agent (script) | `music/<slug>/lyrics-lrc/*.lrc` |

## 4.5 Visual layout

```
┌──────────────────────────────────────────────────────────┐
│  sonic-studio                                             │
│  pipeline — Half-Light Hours · Maren Sol · dream-folk     │
│                                                           │
│  ▌ LAST UPDATE 2026-07-28 09:24 UTC                      │
├──────────────────────────────────────────────────────────┤
│  PROGRESS                                                 │
│  4 of 12 layers complete ──── ──── ──── ──── ────        │
│                                                           │
│  NEXT ACTION                                              │
│  → Approve Spotify package (Layer 5)                     │
│    open music/half-light-hours/spotify/...md              │
├──────────────────────────────────────────────────────────┤
│  LAYERS                                                   │
│                                                           │
│  ┌────────────────────────┐  ┌────────────────────────┐  │
│  │ 01 · artist brand      │  │ 02 · tracklist + lyrics│  │
│  │                        │  │                        │  │
│  │ ─ DONE ─               │  │ ─ DONE ─               │  │
│  │ updated 2026-06-25     │  │ updated 2026-06-25     │  │
│  │ open layer →           │  │ open layer →           │  │
│  └────────────────────────┘  └────────────────────────┘  │
│                                                           │
│  ┌────────────────────────┐  ┌────────────────────────┐  │
│  │ 03 · music tracks      │  │ 04 · cover + posters   │  │
│  │ ─ DONE ─               │  │ ─ DONE ─               │  │
│  └────────────────────────┘  └────────────────────────┘  │
│                                                           │
│  ┌────────────────────────┐  ┌────────────────────────┐  │
│  │ 05 · spotify package   │  │ 06 · press kit         │  │
│  │ ─ IN-PROGRESS ─        │  │ ─ TODO ─               │  │
│  └────────────────────────┘  └────────────────────────┘  │
│                                                           │
│  ... 6 more cards in a 2-column grid ...                  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

A 2-column grid for the 12 layer cards. On viewport <768px the grid collapses to 1 column.

## 4.6 How state.json gets written

The agent updates `state.json` whenever a layer's status changes. Two scenarios:

1. **User-driven:** in chat, user says "complete layer 5". Agent updates state.json.
2. **Agent-driven:** agent finishes a layer; the build skill updates state.json via a small helper script.

The dashboard page itself is **read-only on state.json**. It polls every 30 seconds and re-renders. No websockets, no service worker.

## 4.7 When state.json doesn't exist

The dashboard renders an "empty state" view:

> No active album yet. Open `site/intake.html` to start a new project, or drop an existing album into `music/<slug>/` and the dashboard will pick it up.

The empty state has a single CTA: **Open intake form** (links to `intake.html`).

## 4.8 What the dashboard does NOT do

- Not a real-time collaboration tool
- Not a commenting system
- Not a place to edit the brief or lyrics (use intake.html or the editor of choice for that)
- Not a notifications center (the agent's chat does that)

