# sonic-studio — 24-Hour Autonomous Work Plan

**Started:** 2026-07-30 ~08:30 UTC (user away for 24h)
**Goal:** Make progress without blocking on the user, while M08+ questionnaire questions wait.
**User request:** "create a plan of things you can do by yourself... other validations, other checks, prepare 200 questions about other topics, find blind spots, also search for skills in marketplace and github that would be cool to have for the music creation tool and to build UI/UX and databases, think outside of the box in this planning phase."

---

## What I'm NOT doing (out of scope — waiting on user)

- Asking M08 (artist identity) — the open questionnaire question
- Asking R09-R14 or E15-E21 — also pending
- Building Day 1+ of the v3.2 plan — user hasn't said "start day 1"
- Modifying the locked v3.2 plan — that's what user reviews

## What I AM doing (5 categories)

### Category A — Deep validation of the music-generation pipeline (4-6h)

The matrix test gave us a yes/no pass map. Now go deeper:

1. **Audio quality heuristics on every matrix file** (32 files)
   - LUFS integrated loudness (EBU R128 standard)
   - True-peak dBTP (peaks vs. sample peaks — clipping risk)
   - Spectral centroid (brightness — is "grunge dirt" actually dirtier?)
   - Spectral flatness (noisiness — distinguishing distorted from clean)
   - Dynamic range (DR — pop-punk should be compressed, indie rock more dynamic)
   - Compare M01 vs G02: does the model actually deliver "dirtier" sound on grunge brief?

2. **Lyrics-generation quality test** (20-30 generations)
   - Score each on: syllable count per line (regularity), rhyme scheme adherence, hook potential, total word count
   - Compare pop-punk vs indie vs folk output — different patterns?
   - Identify which brief structures produce usable lyrics

3. **Quota-cost reality** — already have this from matrix
   - Music-3.0: ~80-200s CLI time per track, ~3-5% quota per track
   - 6-track EP: 18-30% quota
   - Validate the music-2.6-free tier is actually viable (longer, less quality, but no quota cost)

4. **Audition pipeline dry-run**
   - Build the audition script (generate 4 candidates sequentially, validate each, present)
   - Test it with the M08 candidates we already designed (A/B/C/D from §1.2 of walkthrough)
   - Verify the 60s wall doesn't bite on short clips

### Category B — Skills research (2-3h)

1. **Hermes skills marketplace** — search for existing skills that apply to sonic-studio
   - music/audio processing
   - lyrics/creative writing
   - album/cover art generation
   - database/daemon patterns
   - UI/UX templates
   - cassette/zine aesthetic references

2. **GitHub search** — find production-quality skills/repos for:
   - album-art generators
   - cassette-tape SVG renderers
   - ID3 metadata embedders (mutagen already proven in past sessions)
   - SQLite daemon patterns (FastAPI, Quart, http.server)
   - ffmpeg batch processing (album mastering)

3. **Open Design plugin packs** — visual designers for cassette stickers, cover art, zine layouts

4. **Document what's worth installing vs building from scratch**

### Category C — Blind spots in the questionnaire (2-3h)

The schema has 20 questions (M01-M08 + R09-R14 + E15-E21). Find gaps:

1. **What the schema doesn't ask but the user will need to know:**
   - Cover art visual direction (palette, motif, typography) — E17 covers this but may be too open
   - Artist photo / press shot
   - Social handles / website
   - Copyright preferences (P-line, C-line)
   - ISRC codes / UPC
   - Explicit content rating (lyrics NSFW? themes for minors?)
   - Producer credit / co-writer splits
   - Sample clearance (does the user need to worry about samples?)
   - Mastering target loudness (Spotify -14 LUFS, Apple -16 LUFS, etc.)
   - Release sequence (instant vs. pre-order vs. staggered)
   - Album-tier pricing (free / name-your-price / fixed)
   - Pre-save campaign mechanics
   - First-week strategy

2. **What the schema asks but the user might struggle with:**
   - M08 artist identity — needs more guidance (gender already binary-locked, but what about age range, persona, real or fictional?)
   - R11 motif — "motif" is vague; should be more specific
   - E16 influences — vs R09 references (potential overlap)
   - E17 cover art — could use a "mood board" mechanic

3. **Draft a v3 schema patch** with new recommended/extra questions, organized by category

### Category D — Tools & libraries investigation (2h)

1. **ffmpeg** — confirm capabilities for: loudnorm (LUFS normalization), silenceremove, acrossfade (gapless between tracks), volume normalization, EQ presets
2. **mutagen** — ID3v2.4 metadata embedding (already proven in past sessions, but document the exact recipe)
3. **Pillow** — image processing for cover art variants
4. **SoX / ffmpeg-python** — any advantages over raw ffmpeg for our pipeline?
5. **lyrics-to-lrc** timing sync — what's the canonical Python lib?
6. **HTTP server choice** — stdlib http.server vs Quart vs FastAPI for the daemon
7. **WebSocket library** — Quart vs FastAPI vs websockets for the studio's real-time chat (Q37)

### Category E — UI/UX research (1-2h)

1. **Look at existing album-creator UIs:**
   - Bandcamp (the indie-press reference)
   - Suno (the AI-music creation UX)
   - Udio (similar to Suno)
   - DistroKid (the release pipeline UX)
   - TuneCore
   - LANDR (mastering)
   - Spotify for Artists (release calendar)

2. **Identify UX patterns worth borrowing:**
   - Pipeline visualization (which step am I on, what's next?)
   - Audition interfaces (A/B comparison, keyboard shortcuts)
   - Lyrics editor (line-by-line, syllable counter, rhyme highlighting)
   - Audio player (waveform, scrub, A/B repeat)
   - Asset versioning (visual diff between v1/v2/v3)

3. **Write a UX-patterns memo** with links/screenshots of what to copy vs avoid

### Category F — Schema + skeleton drafts (1-2h)

The user may want to see actual schema and pipeline-deps.json drafts before Day 1:

1. **SQLite schema skeleton** — 13 tables per v3.2 plan, full DDL with comments
   - Write to `.meta/sonic-studio-schema-draft.sql` (NOT yet applied — for review)
2. **pipeline-deps.json skeleton** — 12-layer DAG with placeholder mmx_actions
   - Write to `.meta/pipeline-deps-draft.json` (NOT yet applied — for review)
3. **Both are draft-only — not applied. User reviews and applies.**

### Category G — Project housekeeping (1h)

1. **Verify git state** — `git status`, commit any orphan files worth keeping
2. **Mirror key docs to OneDrive** — `planning/`, `DESIGN.md`, `README.md` → `~/OneDrive/Hermes/Agents/planning/sonic-studio/`
3. **Run the state-path validator** on any new files written today

---

## Order of operations (24h)

**Hour 0-2:** Read everything (done already). Write this plan. Set up todos.

**Hour 2-6:** Category A — audio quality heuristics + lyrics quality test + audition dry-run. This is the highest-value work since it produces actionable data for the user.

**Hour 6-9:** Category B — skills research. Findings matter for build-time choices.

**Hour 9-13:** Category C — questionnaire blind spots + draft schema patch. This is the "think outside the box" work the user asked for.

**Hour 13-15:** Category D — tools investigation. Mostly confirmatory, but writes a memo for future sessions.

**Hour 15-17:** Category E — UI/UX research. Memo + screenshots.

**Hour 17-19:** Category F — schema + pipeline-deps drafts. Hands-on, but drafts only.

**Hour 19-20:** Category G — housekeeping. Mirror files, git status.

**Hour 20-21:** Write OVERNIGHT-24H-RESULTS.md. Summarize what was done, what's blocked on user, what's next.

**Hour 21-24:** Buffer for slow tasks, retries, anything that didn't fit earlier. Catch-up + final commit.

## What I'm explicitly NOT doing

- **Building the daemon.** That's Day 3, user hasn't approved Day 1.
- **Asking M08 via text message.** User said they're 24h away — no point.
- **Modifying v3.2 plan.** Locked. Anything I find goes into a separate doc.
- **Generating the album.** No brief is locked yet (M08 open).
- **Long-running tests that would burn quota.** The matrix was comprehensive; second rounds need approval.

## Stop conditions

- If I hit a quota budget concern: stop music-gen work, switch to non-quota work
- If I find something that contradicts the v3.2 plan: write it as a "v3.3 proposal" but don't act on it
- If something blocks: write it down + move to next category, don't stall

## Output documents at the end

1. `planning/OVERNIGHT-24H-RESULTS.md` — what I did, what I found, what to look at first
2. `planning/QUESTIONNAIRE-V2-DRAFT.md` — proposed new questions
3. `.meta/audio-quality-report.md` — the matrix's quality deep-dive
4. `.meta/lyrics-quality-report.md` — lyrics-generation scoring
5. `.meta/audition-pipeline/` — the audition script + dry-run results
6. `.meta/sonic-studio-schema-draft.sql` — schema skeleton
7. `.meta/pipeline-deps-draft.json` — pipeline DAG skeleton
8. `planning/ux-patterns-memo.md` — UX research findings
9. `planning/skills-research.md` — marketplace/github search findings
10. `planning/tools-memo.md` — ffmpeg/mutagen/etc. confirmed capabilities

All mirrored to `~/OneDrive/Hermes/Agents/planning/sonic-studio/` (mirror-on-write per memory rule).

---

**Status legend (per doc):**
- ✅ done
- ⏳ in progress
- ❌ blocked / not done
- 🟡 partial / needs review

Standing by to execute. Will report back when user returns.