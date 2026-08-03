# CONCEPT-BRIEF.md — Template

> This template is the **handoff contract** between `site/intake.html` and the
> `full-album-release-package` skill. The agent reads `intake-data/<slug>.json`
> and writes `<album-slug>/CONCEPT-BRIEF.md` in the format below.
> The build skill then reads `CONCEPT-BRIEF.md` and starts generating.

> **Schema version:** v2.2 (`intake-data/schema.json`)
> **Brief template version:** v2.2 (this file)
> **Bumped:** 2026-08-03 — added M09_sonicDNA + R15-R19 + E22-E25 sections (V2-DRAFT additions + Twenty-Two retro lessons)

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
**Schema version locked:** v2.2

---

# 🔒 M09 — Sonic DNA Lock (read-only after approval)

> **CRITICAL:** This block is frozen at brief approval. The build skill MUST
> hold against these values on every regen. Any change requires explicit
> user re-approval (the `scripts/check-sonic-drift.py` guard).

| Field | Locked value | Source |
|---|---|---|
| **Genre flag** | [e.g. "hard rock"] | derived from M03 |
| **Vocals flag** | [e.g. "Axl Rose-style raw high tenor, ..."] | derived from M05 |
| **Mood flag** | [e.g. "aggressive, swaggering, explosive"] | derived from R12 |
| **Instruments flag** | [e.g. "dual electric guitars through Marshall stacks, ..."] | derived from R12 |
| **References flag** | [e.g. "Guns N' Roses Appetite for Destruction, Skid Row Slave to the Grind, ..."] | derived from M04 |
| **Tempo profile** | [e.g. "120-155 BPM, mid-to-fast"] | derived from M07 |
| **Locked at** | [ISO 8601 UTC timestamp] | approval time |
| **Locked by** | [user name] | approval action |

**Why this exists (Twenty-Two lesson, 2026-08-03):** the previous build locked
M03_genre = "90s grunge with FF melodic hooks" + M05_vocal = "Velvet Revolver-style
(Scott Weiland)", but a re-gen silently switched to hard rock + Axl Rose vocals.
The schema and the artifact DRIFTED without anyone noticing. This lock makes
that drift visible: every regen must pass `scripts/check-sonic-drift.py`.

---

# Tracklist placeholder ([N] tracks)

| # | Title | Theme | Mood | BPM (target) | Key (target) |
|---|-------|-------|------|--------------|--------------|
| 01 | [title] | [theme] | [mood] | [bpm] | [key] |
| ... |
| [N] | [title] | [theme] | [mood] | [bpm] | [key] |

---

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

---

# Production style

- **Approach:** [stripped | full-band | electronic | cinematic | hybrid]
- **Vocal approach:** [solo | duet | choir | spoken-word | instrumental]
- **Vocal character:** [free-text voice description]
- **Distribution intent:** [just-for-me | routenote-free | full-dsp | physical-and-dsp]

---

# Mastering & delivery

- **Loudness target (R15):** [spotify -14 LUFS | apple-music -16 LUFS | youtube -14 LUFS | broadcast -23 LUFS | cd-master -9 to -6 LUFS | vinyl-master | custom]
- **Sequence pacing (R16):** [continuous-flow | short-pause (1-2s) | standard-pause (3-4s) | long-pause (5-10s)]
- **Explicit rating (R17):** [clean | explicit-tagged | parental-advisory]
- **Co-writer / producer credits (R18):** [solo | co-producer | co-lyricist | feature-vocalist | full-band-credits]
- **Sample / cover usage (R19):** [original-only | samples-cleared | samples-pending | covers-included]

---

# Lyrical source

[user-writes | agent-writes | co-write]

---

# Emotional arc

[one paragraph — shape of the listening experience across the tracklist]

---

# Non-music influences

- [books, films, places, seasons that shaped the sound]

---

# Creative extras

- **Cover art direction:** [palette, photo vs illustration, typography mood]
- **Physical anchor:** [the ONE thing the listener should remember]
- **Press / rollout scope:** [music-only | music-press | music-press-social | everything]
- **Music videos:** [0 | 1-2 | 3-5]
- **Deadlines / pressure:** [ISO date or "no deadline"]
- **Album timeline (E22):** [milestones — lyrics done by X, music by Y, artwork by Z, release by W]
- **Recording session persona (E23):** [first-person-singular | first-person-plural | second-person | third-person-omniscient | third-person-limited | character-voice | varies]
- **Target audience (E24):** [who this album is for]
- **Physical release (E25):** [none | cd | vinyl-lp | vinyl-7in | cassette | usb-mini | merch-bundle | limited-edition-print]

---

# 📋 Topic status (audit trail)

The 26 topics from `intake-data/schema.json` v2.2, mapped to mandatory/recommended/extra tiers:

## 🟥 Mandatory (9 — all required, M09 is the new sonic-DNA lock)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| M·01 | Album concept | [user-answered / agent-default] | |
| M·02 | Project scope | [user-answered / agent-default] | |
| M·03 | Genre direction | [user-answered / agent-default] | |
| M·04 | Reference artists | [user-answered / agent-default] | |
| M·05 | Vocal approach | [user-answered / agent-default] | |
| M·06 | Language | [user-answered / agent-default] | |
| M·07 | Runtime per track | [user-answered / agent-default] | |
| M·08 | Artist identity | [user-answered / agent-default] | (bandName + artistName + creditLine) |
| **M·09** | **Sonic DNA lock** | **[user-approved / agent-locked]** | **Frozen at approval — read-only** |

## 🟧 Recommended (10 — default applied if skipped)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| R·09 | Album title | [user-answered / agent-default / deferred] | |
| R·10 | Tracklist placeholder | [user-answered / agent-default / deferred] | |
| R·11 | Visual motif | [user-answered / agent-default / deferred] | |
| R·12 | Production style | [user-answered / agent-default / deferred] | |
| R·13 | Lyrical source | [user-answered / agent-default / deferred] | |
| R·14 | Distribution intent | [user-answered / agent-default / deferred] | |
| R·15 | Mastering loudness target | [user-answered / agent-default] | spotify -14 LUFS default |
| R·16 | Sequence pacing | [user-answered / agent-default] | standard-pause default |
| R·17 | Explicit rating | [user-answered / agent-default] | clean default |
| R·18 | Co-writer credits | [user-answered / agent-default] | solo default |
| R·19 | Sample / cover usage | [user-answered / agent-default] | original-only default |

## 🟩 Extra (7 — opt-in)

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| E·15 | Emotional arc | [user-answered / agent-default / deferred] | |
| E·16 | Non-music influences | [user-answered / agent-default / deferred] | |
| E·17 | Cover art direction | [user-answered / agent-default / deferred] | |
| E·18 | Physical anchor | [user-answered / agent-default / deferred] | |
| E·19 | Press / rollout scope | [user-answered / agent-default / deferred] | hidden when R14=just-for-me |
| E·20 | Music videos | [user-answered / agent-default / deferred] | hidden when R14=just-for-me |
| E·21 | Deadlines / pressure | [user-answered / agent-default / deferred] | |
| E·22 | Album timeline | [user-answered / agent-default / deferred] | NEW v2.2 |
| E·23 | Session persona | [user-answered / agent-default] | NEW v2.2; shown when R13=agent-writes or co-write |
| E·24 | Target audience | [user-answered / agent-default / deferred] | NEW v2.2 |
| E·25 | Physical release | [user-answered / agent-default] | NEW v2.2; shown when R14=physical-and-dsp |

> **Note:** v2.2 has 26 answer fields total. E22-E25 are new; E19 + E20 + E25 have
> conditional visibility rules (hidden when R14=just-for-me or R14=routenote-free).
> E23 is shown when R13 in {agent-writes, co-write}.

---

# 🛡 Generation manifest contract

For every track, the build skill MUST write `music/<slug>.generation-manifest.json`
immediately after `mmx music generate` returns successfully. The manifest captures:

- Exact prompt body (chars)
- All `--vocals / --genre / --mood / --instruments / --bpm / --key / --references` flags
- Lyrics source path + char count
- Output file md5 + duration + bitrate + sample-rate + channels
- Model version (`music-3.0`)
- Schema version this manifest was generated against (e.g. `v2.2`)
- Reference to the locked M09_sonicDNA (if present)

**Before any regen:** the build skill MUST run `scripts/check-sonic-drift.py`
against the proposed prompt + flags. If drift is detected, the build halts
unless the user explicitly approves the change with `--allow-drift-fields`.

See `scripts/generation-manifest.py` and `scripts/check-sonic-drift.py` for
the canonical implementations.

---

# Sign-off

This brief was generated from `intake-data/<slug>.json` on `<YYYY-MM-DD HH:MM UTC>`.

When the user approves the brief in chat ("approve brief <slug>"), the agent starts
`full-album-release-package` from Layer 1 (Artist brand). State tracking lives in
`.meta/state.json`.

**Approval also locks M09_sonicDNA. From that point on, the build skill
holds against the sonic DNA on every regen.**

---

# Notes for the build skill (do not edit by hand)

- **Layer 1 (Artist brand)** writes a 5-sentence artist profile before any generation.
- **Layer 2 (Tracklist + lyrics)** halts at the STEP 1.5 checkpoint for user approval
  of all lyrics BEFORE any music is generated.
- **Layer 3 (Music tracks)** halts at the STEP 1.7 checkpoint for user approval of all
  composed prompts BEFORE any music API call. **Plus, must pass
  `scripts/check-sonic-drift.py` before the API call.**
- **Layer 3.5 (Generation manifest)** runs `scripts/generation-manifest.py` immediately
  after each successful `mmx music generate`. Required, not optional.
- **Layers 5–10** are auto-generated once the user approves Layer 4 (the artwork).
- **Layers 11–12** are deterministic scripts and run without checkpoints.
- **Media quality gate (Twenty-Two retro lesson, 2026-08-03):** all visual assets
  (cover, posters, merch, storyboards) must be real AI-generated via
  `mmx image generate` or `mmx video generate`. PIL/Pillow placeholder art is
  explicitly rejected — the user pushed back hard when the first pass shipped
  PIL-drawn covers/posters/merch as "real assets."