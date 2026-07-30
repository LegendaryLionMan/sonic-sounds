# CONCEPT-BRIEF.md — Template

> This template is the **handoff contract** between `site/intake.html` and the
> `full-album-release-package` skill. The agent reads `intake-data/<slug>.json`
> and writes `<album-slug>/CONCEPT-BRIEF.md` in the format below.
> The build skill then reads `CONCEPT-BRIEF.md` and starts generating.

---

# [ARTIST NAME] — Album Concept Brief

**Album title:** [Title]
**Artist:** [stage name]
**Genre:** [primary] / [secondary]
**Scope:** [single | EP | album | double-feature | concept-piece]
**Language:** [languages for lyrics]
**Runtime target:** [radio-edit | standard | extended | immersive]
**Visual motif:** [one recurring image — a window, a color, an object]
**Color palette:** [3-5 hex codes]
**Narrative arc:** [one sentence — what's the album ABOUT?]
**Comp artists:** [1-3 named]

# Tracklist placeholder ([N] tracks)

| # | Title | Theme | Mood | BPM (target) | Key (target) |
|---|-------|-------|------|--------------|--------------|
| 01 | [title] | [theme] | [mood] | [bpm] | [key] |
| ... |
| [N] | [title] | [theme] | [mood] | [bpm] | [key] |

# Visual identity

**Palette (3-5 hex):**
- `[hex]` — [name]
- `[hex]` — [name]
- `[hex]` — [name]

**Motif:** [one recurring visual element — e.g. "a single half-lit window"]

**Typography (display + body):**
- Display: [font family]
- Body: [font family]
- Mono (for metadata): [font family]

**Reference imagery:** [list of mood-board URLs, if any]

# Production style

- **Approach:** [stripped | full-band | electronic | cinematic | hybrid]
- **Vocal approach:** [solo | duet | choir | spoken-word | instrumental]
- **Vocal character:** [free-text voice description]
- **Distribution intent:** [just-for-me | routenote-free | full-dsp | physical-and-dsp]

# Lyrical source

[user-writes | agent-writes | co-write]

# Emotional arc

[one paragraph — shape of the listening experience across the tracklist]

# Non-music influences

- [books, films, places, seasons that shaped the sound]

# Creative extras

- **Cover art direction:** [palette, photo vs illustration, typography mood]
- **Physical anchor:** [the ONE thing the listener should remember]
- **Press / rollout scope:** [music-only | music-press | music-press-social | everything]
- **Music videos:** [0 | 1-2 | 3-5]
- **Deadlines / pressure:** [ISO date or "no deadline"]

# Topic status (audit trail)

The 21 topics from `site/intake.html`, mapped to mandatory/recommended/extra tiers:

## 🟥 Mandatory (8 — all required)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| M·01 | Album concept | [user-answered / agent-default] | |
| M·02 | Project scope | [user-answered / agent-default] | |
| M·03 | Genre direction | [user-answered / agent-default] | |
| M·04 | Reference artists | [user-answered / agent-default] | |
| M·05 | Vocal approach | [user-answered / agent-default] | |
| M·06 | Language | [user-answered / agent-default] | |
| M·07 | Runtime per track | [user-answered / agent-default] | |
| M·08 | Artist identity | [user-answered / agent-default] | |

## 🟧 Recommended (6 — default applied if skipped)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| R·09 | Album title | [user-answered / agent-default / deferred] | |
| R·10 | Tracklist placeholder | [user-answered / agent-default / deferred] | |
| R·11 | Visual motif | [user-answered / agent-default / deferred] | |
| R·12 | Production style | [user-answered / agent-default / deferred] | |
| R·13 | Lyrical source | [user-answered / agent-default / deferred] | |
| R·14 | Distribution intent | [user-answered / agent-default / deferred] | |

## 🟩 Extra (7 — opt-in)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| E·15 | Emotional arc | [user-answered / agent-default / deferred] | |
| E·16 | Non-music influences | [user-answered / agent-default / deferred] | |
| E·17 | Cover art direction | [user-answered / agent-default / deferred] | |
| E·18 | Physical anchor | [user-answered / agent-default / deferred] | |
| E·19 | Press / rollout scope | [user-answered / agent-default / deferred] | |
| E·20 | Music videos | [user-answered / agent-default / deferred] | |
| E·21 | Deadlines / pressure | [user-answered / agent-default / deferred] | |

---

# Sign-off

This brief was generated from `intake-data/<slug>.json` on `<YYYY-MM-DD HH:MM UTC>`.

When the user approves the brief in chat ("approve brief <slug>"), the agent starts
`full-album-release-package` from Layer 1 (Artist brand). State tracking lives in
`.meta/state.json`.

---

# Notes for the build skill (do not edit by hand)

- **Layer 1 (Artist brand)** writes a 5-sentence artist profile before any generation.
- **Layer 2 (Tracklist + lyrics)** halts at the STEP 1.5 checkpoint for user approval
  of all lyrics BEFORE any music is generated.
- **Layer 3 (Music tracks)** halts at the STEP 1.7 checkpoint for user approval of all
  composed prompts BEFORE any music API call.
- **Layers 5–10** are auto-generated once the user approves Layer 4 (the artwork).
- **Layers 11–12** are deterministic scripts and run without checkpoints.

