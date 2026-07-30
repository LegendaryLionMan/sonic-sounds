# album-studio

> An HTML front door for the music-album-planning-questionnaire and
> full-album-release-package skills. Plan an album, track the 12-layer
> build pipeline, hand off cleanly to the agent.

**Project type:** evolving the existing album-creation skill stack with a
project workspace (intake form + dashboard), not a standalone app.

---

## What's in this project

```
album-studio/
├── README.md                      ← this file
├── DESIGN.md                      ← visual identity tokens (palette, type, motif)
├── site/
│   ├── intake.html                ← 21-topic intake form (the front door)
│   └── dashboard.html             ← 12-layer pipeline status board
├── intake-data/
│   ├── schema.json                ← JSON Schema for the exported brief
│   └── <slug>.json                ← per-album exported briefs (one per project)
├── concept-briefs/
│   └── <slug>/CONCEPT-BRIEF.md    ← the handoff to full-album-release-package
├── music/
│   └── <slug>/{lyrics,music,...}  ← output of full-album-release-package
└── .meta/
    ├── state.json                 ← dashboard reads this (12 layers, statuses)
    └── sections-3-and-4.md        ← intake + dashboard UX specs (planning archive)
```

---

## How to use it

### 1. Start a new album — open the intake form

Open `site/intake.html` in a browser (double-click or `start site\intake.html` on Windows).

The form is the **21-topic questionnaire** from the existing
`music-album-planning-questionnaire` skill. Fill the 8 mandatory topics first;
the export button stays disabled until all 8 are filled.

When you click **Generate CONCEPT-BRIEF**, the form downloads a JSON file
like `intake-data/<album-slug>.json`.

### 2. Hand the brief to the agent

In a chat with Penelope (me), drop the JSON file path:

> "Approve brief `intake-data/maren-sol-half-light-hours.json`"

I read the JSON, write `concept-briefs/<slug>/CONCEPT-BRIEF.md` from the
template, and start `full-album-release-package` Layer 1 (Artist brand).

### 3. Watch the pipeline — open the dashboard

Open `site/dashboard.html` in a browser. The page reads `.meta/state.json`
every 30 seconds and renders the 12 layers with their current status.

The page also shows the **next action** (what you need to do right now to
keep the pipeline moving).

### 4. Per-layer checkpoints

The build pipeline has two explicit approval gates:

- **STEP 1.5** — Lyrics review (after Layer 2 writes 10 `.md` lyrics files,
  before Layer 3 generates any audio)
- **STEP 1.7** — Prompt review (after Layer 3 composes 10 music prompts,
  before Layer 3 spends any music API quota)

Both gates halt the pipeline. The dashboard updates the relevant layer to
`blocked` and surfaces the next action.

---

## How the project relates to the existing skills

| This project | Existing skill |
|---|---|
| `site/intake.html` (the form) | `music-album-planning-questionnaire` (the conversation) |
| `intake-data/<slug>.json` (the export) | the questionnaire's output contract |
| `concept-briefs/<slug>/CONCEPT-BRIEF.md` | the questionnaire's brief format |
| `site/dashboard.html` (the status board) | `full-album-release-package` (the 12 layers) |
| `.meta/state.json` | the build skill's running state |
| `music/<slug>/{lyrics,music,...}` | the build skill's output |

The site is **not** a replacement for the agent — it's a **surface** that
makes the skill workflow visible and inspectable. The agent still does
all the heavy lifting.

---

## Visual identity

See `DESIGN.md` for the full token spec:

- Direction: editorial / zine (warm paper, big serif, indie-press)
- Palette: warm paper `#F4EFE6`, ink `#1B1714`, terracotta accent `#B8503A`
- Typography: Cormorant Garamond display / Lora body / JetBrains Mono mono
- Motif: the half-lit window from Half-Light Hours
- Single accent, no gradients, no rounded corners

Both `site/intake.html` and `site/dashboard.html` consume these tokens
via CSS custom properties at the top of each file.

---

## Mirrors

Per the user's standard mirror rule:

| Source | Mirror |
|---|---|
| `~/Documents/Projects/album-studio/` | `~/OneDrive/Hermes/Agents/planning/album-studio/` |

After every change, both copies must `md5sum` byte-match. (Mirror script
documented in `.meta/sections-3-and-4.md` planning archive.)

---

## What this project does NOT do

- Not a backend / API. Both pages are pure static HTML + inline CSS/JS.
- Not a real-time collaboration tool. Updates flow user → agent → state.json.
- Not a lyrics editor. The agent writes lyrics; the user reviews them.
- Not a music streaming service. The agent delivers MP3s; the user uploads
  to distributors.
- Not a distribution platform. The `album-distribution-launch` skill owns
  that (DistroKid / RouteNote / etc).

---

## License

Personal project. Not for redistribution.
