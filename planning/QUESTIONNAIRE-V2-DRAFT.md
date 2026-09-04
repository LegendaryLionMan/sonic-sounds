# sonic-studio Questionnaire v2 — Blind Spots & New Question Proposals

**Date:** 2026-07-30
**Author:** Penelope (autonomous 24h work)
**Status:** Draft for user review when they return
**Source:** Deep audit of `intake-data/schema.json` (current v1) + cross-reference
with `concept-briefs/TEMPLATE.md` + real-world album-release considerations

---

## How to read this

For each new question, I document:
- **Question ID**: where it slots (M, R, or E tier)
- **The gap**: what v1 doesn't ask but real-world album creation needs
- **Proposed prompt**: how to phrase it for the user
- **Type**: `text` / `select` / `multiselect` / `date`
- **Required**: yes/no within its tier
- **Default behavior**: what happens if user skips
- **Why it matters**: failure mode without the answer

---

## Section 1 — Gaps in current v1 (recommended new questions)

### R15: **Mastering loudness target**

- **Tier:** Recommended (move from M if too aggressive; user might just want "Spotify" defaulted)
- **Type:** select
- **Options:** `spotify` (-14 LUFS, default) | `apple-music` (-16 LUFS) | `youtube` (-14 LUFS) | `broadcast` (-23 LUFS) | `cd-master` (-9 to -12 LUFS) | `vinyl-master` (depends on format) | `custom`
- **Prompt:** *"Where will this album mostly be played? This sets the master loudness."*
- **Why it matters:** Currently every test track comes out at -14 LUFS (Spotify target). For Apple Music delivery, all 6 tracks would need 1.5 dB attenuation. Better to decide upfront and apply once.
- **Default:** Spotify (-14 LUFS) — applies via `loudnorm` two-pass on `finalize-album.py`.

### R16: **Album sequence & pacing**

- **Tier:** Recommended
- **Type:** select
- **Options:** `continuous-flow` (no silence between tracks) | `short-pause` (1-2s) | `standard-pause` (3-4s) | `long-pause` (5-10s, mixtape feel) | `concept-pause` (15s+, atmospheric / interludes)
- **Prompt:** *"How much silence between tracks? Affects gapless playback vs mixtape feel."*
- **Why it matters:** R10 (tracklist) doesn't specify inter-track gaps. This affects `finalize-album.py` (crossfade vs pause). For pop-punk: short-pause. For mixtapes: continuous-flow. For concept-pieces: long-pause.

### R17: **Explicit content rating**

- **Tier:** Recommended
- **Type:** select
- **Options:** `clean` (no profanity, radio-safe) | `explicit-tagged` (profanity allowed, marked) | `parental-advisory` (full profanity, marked)
- **Prompt:** *"Will this album have explicit lyrics? Affects radio playability + DSP tagging."*
- **Why it matters:** Affects Spotify/Apple Music metadata, YouTube content ID flags, distribution approval on some platforms. Currently the lyrics-optimizer can produce profanity without warning.

### R18: **Co-writer / producer credits**

- **Tier:** Recommended
- **Type:** multiselect
- **Options:** user-defined roles + names
- **Prompt:** *"Anyone else to credit? (e.g. co-producer, lyricist, feature vocalist). Default: just you."*
- **Why it matters:** Royalty splits + DSP metadata need to match real credits. Real-world albums often have 3-5 credited names. The build skill can write P-line / C-line from this.

### R19: **Sample/cover usage**

- **Tier:** Recommended
- **Type:** select
- **Options:** `original-only` (no samples, no covers) | `samples-cleared` (pre-cleared samples, docs attached) | `samples-pending` (samples used, clearance not yet obtained) | `cover-only` (one or more covers)
- **Prompt:** *"Does the album use any samples or covers? Affects clearance + DSP rules."*
- **Why it matters:** AI music from text prompts is generally "original" but user might want to add a beat from Splice or cover a public-domain folk song. Mis-tagging can lead to DMCA strikes.

### E22: **Album timeline / sequencing**

- **Tier:** Extra
- **Type:** text (free-form timeline)
- **Prompt:** *"Rough timeline — when do you want each milestone? E.g. lyrics done by Aug 15, music by Sep 1, artwork by Sep 15, release Oct 1. Or 'no deadline'."*
- **Why it matters:** Different from E21 (single deadline). A timeline lets the studio's session manager pace work and prompt the user at the right moments. Currently we only have a final-deadline date.

### E23: **Recording session persona**

- **Tier:** Extra
- **Type:** select
- **Options:** `first-person-singular` ("I") | `first-person-plural` ("we" — for bands) | `second-person` ("you") | `third-person-omniscient` | `third-person-limited` | `character-voice` (specific named character)
- **Prompt:** *"Whose story is this? Most albums have a consistent POV. Pick one or say 'varies'."*
- **Why it matters:** Affects lyrical generation. If user picks `character-voice`, the lyrics_optimizer prompt should include the character's name + backstory. Currently we'd just default to first-person without asking.

### E24: **Listener / target audience**

- **Tier:** Extra
- **Type:** text
- **Prompt:** *"Who is this album FOR? (e.g. 'people who feel stuck in a 9-5', 'people who just went through a breakup', 'myself in 5 years'). Or 'just for me' — that's a valid answer."*
- **Why it matters:** Affects press kit (E19), marketing copy, and even the lyrics_optimizer's register (intimate vs anthemic).

### E25: **Physical release intent**

- **Tier:** Extra
- **Type:** multiselect
- **Options:** `none` | `cd` | `vinyl-lp` | `vinyl-7in` | `cassette` | `usb-mini` | `merch-bundle` | `limited-edition-print`
- **Prompt:** *"Any physical format? Cassettes are surprisingly popular in indie scenes. CDs never went away. Vinyl is back."*
- **Why it matters:** Drives L7 (cassette sticker), L9 (merch assets), and asset generation. Currently R14 covers "physical-and-dsp" but doesn't decompose which physicals.

---

## Section 2 — Schema design improvements (not new questions)

### Fix: M08_artist is too open

**Current:** `M08_artist: answerText (free text)`
**Problem:** No guidance for what makes a complete answer. User could write "John" (first name) or "John Smith Band feat. Various Artists" — both valid, neither complete.

**Proposed:**
- Stay as free text (it's an artist's stage name)
- BUT add a `M08b_persona` extra field for: real name, age range, persona description
- AND add a `M08c_fictional` boolean (lock from previous walkthrough decision: M08 can be fictional)

**Prompt for M08c:** *"Is this artist a fictional persona or your real identity?"*
- `fictional-character` — like Gorillaz, Marilyn Manson, MF DOOM
- `real-self` — your real name
- `alter-ego` — a stage persona tied to you
- `collaborative-pseudonym` — multiple people under one name (BTS, The Residents)

### Fix: R11_motif is vague

**Current:** `R11_motif: answerText`
**Problem:** "motif" is a design term users won't know. The concept-brief template uses it but the prompt doesn't explain.

**Proposed:** Add helper text:
*"A 'motif' is one recurring image that appears throughout the album's design (and possibly in the lyrics). Examples: 'a half-lit window' (Half-Light Hours), 'a cracked phone screen', 'a single red balloon', 'a bus ticket stub'. Pick one image, not a list."*

### Fix: E17_coverArt is too open

**Current:** `E17_coverArt: answerText`
**Problem:** No structure for what's expected. User could write "good" or 1000 words.

**Proposed:** Split into:
- `E17a_palette` — required if cover art is non-trivial. "3-5 colors as hex codes (e.g. `#F4EFE6, #1B1714, #B8503A`)."
- `E17b_mood` — short text "what feeling should the cover evoke?"
- `E17c_composition` — text "where is the focal point? What fills the frame? Any typography?"

Or: keep as one text field but provide a placeholder example in the form.

### Fix: E16_influences overlaps R09_references

**Current:**
- R04: Reference artists (1-3 named)
- E16: Non-music influences (books, films, places)

**Problem:** Both ask "what inspired this?" — the user might list the same things twice.

**Proposed:** Make E16 explicitly NON-OVERLAPPING with R04. Add helper text:
*"Other than music references (covered in M04). What's a film, book, place, season, etc. that shaped this?"*

### Fix: M07_runtime per-track vs per-album

**Current:** `M07_runtime` is one of `radio-edit | standard | extended | immersive` — applied as the album's average.
**Problem:** But real albums have one or two signature longer tracks and the rest standard. M07 doesn't capture that variance.

**Proposed:** Either:
- Make M07 a `range` or `mix` (e.g. `mostly-standard, 1-2 extended`)
- Add an extra E26: `E26_runtimeMix: answerText` for "anything special about track durations?"

(This was already noted in the questionnaire walkthrough. Worth formalizing.)

---

## Section 3 — Validation rules (UX bulletproofing)

The schema's `enum` fields are good for forcing valid choices, but several text fields lack length limits:

| Field | Proposed min | Proposed max | Why |
|---|---|---|---|
| M01_concept | 20 chars | 1000 chars | Too short = insufficient brief; too long = off-topic |
| M03_genre | 5 chars | 200 chars | Same |
| M08_artist | 2 chars | 80 chars | Stage name realistic range |
| R09_title | 1 char | 80 chars | Album titles are short |
| R11_motif | 5 chars | 200 chars | One image, not a paragraph |
| E15_arc | 20 chars | 2000 chars | Emotional arc needs space |
| E16_influences | 5 chars | 1000 chars | |
| E17_coverArt | 10 chars | 1500 chars | |
| E18_anchor | 5 chars | 300 chars | "Physical anchor" should be one sentence |
| E24_listener | 5 chars | 500 chars | |

Also: add a `format: regex` for hex codes in E17_palette (if split into E17a).

---

## Section 4 — Conditional visibility

Some questions should only show based on prior answers. Examples:

| If user picks... | Then show... | Hide... |
|---|---|---|
| R14_distribution: `physical-and-dsp` | E25_physicalRelease | (none) |
| R14_distribution: `just-for-me` | (none) | E25, E19, E20 |
| R13_lyricalSource: `agent-writes` or `co-write` | E23_persona | (none) |
| R13_lyricalSource: `user-writes` | (none) | E23 (irrelevant) |
| R12_production: `cinematic` | (nothing extra — cinematic is the most "finished") | (none) |
| R12_production: `stripped` | R16_albumSequence (might want continuous) | (none) |
| M02_scope: `single` | (collapse R10 tracklist to 1) | (none) |
| M02_scope: `ep` | R10 tracklist = 3-6 | (none) |
| M02_scope: `album` | R10 tracklist = 7-12 | (none) |
| M02_scope: `concept-piece` or `double-feature` | R10 tracklist = arbitrary; E15_arc becomes more important | (none) |

This is UI-side logic, not schema. Schema should still allow any combination.

---

## Section 5 — What v1 gets RIGHT (don't change)

- 8 mandatory + 6 recommended + 7 extra = 21 questions is the right shape
- Tier system (mandatory/recommended/extra) is clear
- The 13 named `$defs` types are well-designed
- `albumSlug` regex is good (kebab-case, length limits)
- `submittedAt` ISO 8601 UTC is correct
- `schemaVersion` constant is forward-compatible

---

## Section 6 — Recommended rollout plan

When user returns, suggest this sequence:

1. **User reviews this doc.** Decides which questions to add.
2. **Update `schema.json`** with new fields (M08c, R15-R19, E22-E26, plus any other accepted).
3. **Add validation rules** (Section 3) — JSON schema's `minLength`/`maxLength`.
4. **Update `concept-briefs/TEMPLATE.md`** — add new sections.
5. **Update `intake.html`** (Day 9 of v3.2 plan) — render new questions with conditional visibility.
6. **Bump `intakeFormVersion`** to `2026-07-30` (or whatever date applies).

This is a **schema-only update** — no UI rebuild needed (the intake form will be built fresh on Day 9 anyway).

---

## Files for reference

- `intake-data/schema.json` — current v1 schema (20 questions)
- `concept-briefs/TEMPLATE.md` — current brief template
- `planning/PLAN-2026-07-28-v3.2.md` § 5 Day 9 — intake form build plan
- `planning/QUESTIONNAIRE-WALKTHROUGH-2026-07-29.md` — locked M01-M07 + M08 sub-decisions

---

**Next steps for the user (when they return):**

1. Read Section 1 (new questions) — keep / discard / modify each
2. Read Section 2 (schema improvements) — apply the fixes?
3. Decide on Section 3 validation rules
4. Approve Section 4 conditional visibility (or punt to Day 9)
5. I implement Sections 5-6 only after your sign-off