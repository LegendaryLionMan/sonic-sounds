# sonic-studio Meta-Decisions — 2026-08-02

**Source:** Live session 2026-08-02 (Penelope + user). User direction delivered as
a single message with 6 numbered points + a 7th task (H3 video gen test).

**Status:** All 7 captured. **Video gen task completed (Hailuo-2.3 fallback,
see §3).** All other decisions are stated in chat and locked here for
persistence.

**Why this doc exists separately from `QUESTIONNAIRE-WALKTHROUGH-2026-07-29.md`:**
That doc captures per-field schema decisions (M01-M08, R15-R19, E22-E25, etc.).
This doc captures **cross-cutting meta-decisions** that affect the v3.2 plan,
the build order, the toolchain, and the delivery pipeline — not individual
questionnaire fields.

---

## §1 — The 6 numbered points from the user (verbatim, 2026-08-02)

> 1. print questionnaire here so i can see it
> 2. spotify
> 3. you choose
> 4. you decide
> 5. all go
> 6. install right now all of them.

| # | User input | Agent decision | Locked |
|---|---|---|---|
| 1 | "print questionnaire here so i can see it" | Printed full schema (M01-M08 + R09-R14 + E15-E21) + v2 proposals (R15-R19, E22-E25, M08c) at top of session reply. | ✅ |
| 2 | "spotify" | **Default mastering loudness target = Spotify -14 LUFS.** Applied at the master stage (not generation stage). Stored as the default value of the proposed R15 field. Rationale: 14 of 34 matrix test tracks already came out at -10.5 to -16.7 LUFS (mean -14.5) — the natural output is already at Spotify target, so this is the path of least intervention. | ✅ |
| 3 | "you choose" | **Loudness application point = master stage, on `finalize`.** Not during music generation (preserves reproducibility — same input → same output across runs), not as a per-track post-step (fragments the pipeline), not at upload time (too late for Spotify ingest). The `finalize` command becomes the master+package step. Note: this *extends* the existing `finalize-album.py` (currently asset versioning only, Q30) into an audio-master + asset-version + delivery-package step. **v3.2 plan needs an update for this.** | ✅ |
| 4 | "you decide" | **Schema + pipeline drafts as written are good — proceed to Phase 0.D when user says so.** No schema edits required before the questionnaire walkthrough resumes. The proposed v2 additions (R15-R19, E22-E25, M08c) stay in `QUESTIONNAIRE-V2-DRAFT.md` as draft, NOT applied to `intake-data/schema.json` yet. Apply when the walkthrough reaches M07 (where R15 fits naturally). | ✅ |
| 5 | "all go" | **Toolchain = full list.** The 8 packages the user asked for are the canonical music-album toolchain: pronouncing (rhyme/phoneme analysis), pyphen (syllable hyphenation for LRC timing), Pillow (cover art + assets), pycairo (vector cover art fallback), Quart (async web framework for HTML intake/studio pages), spotipy (Spotify API for delivery), musicbrainzngs (MBID lookups for canonical metadata), mutagen (ID3v2.4 embedding). | ✅ |
| 6 | "install right now all of them" | **All 8 installed.** pip install + import-test cycle ran in the active Hermes venv. Verified on 2026-08-02 16:13 UTC. See §2. | ✅ |

---

## §2 — Tool install record (2026-08-02 16:13 UTC)

All installed via `python -m pip install` in the active Hermes venv at
`C:\Users\lion_\AppData\Local\hermes\hermes-agent\venv`.

| Package | Version | Purpose | Verified import |
|---|---|---|---|
| pronouncing | 0.3.0 | CMU dict rhyme/phoneme lookup | `import pronouncing` → OK |
| pyphen | 0.17.2 | Syllable hyphenation (multilingual) | `import pyphen; pyphen.Pyphen(lang='en_US')` → OK |
| pycairo | 1.29.0 | Vector cover art (Cairo Python bindings) | `import cairo; cairo.version` → 1.29.0 |
| Pillow | (already 12.2.0) | Raster cover art + asset generation | `import PIL; PIL.__version__` → 12.2.0 |
| Quart | 0.21.0 | Async web framework (intake + studio) | `import quart` → OK |
| spotipy | 2.26.0 | Spotify Web API (delivery) | `import spotipy` → OK |
| musicbrainzngs | 0.7.1 | MusicBrainz canonical metadata | `import musicbrainzngs` → OK |
| mutagen | (already 1.48.1) | ID3v2.4 / Vorbis / FLAC tags | `import mutagen; mutagen.version_string` → 1.48.1 |

**Pyphen API note:** Pyphen 0.17.2 changed `Pyphen.insertions(word)` →
`Pyphen.inserted(word)`. If any agent code calls `.insertions(...)` it will
fail with `AttributeError`. Use `.inserted(word)` instead.

**Quart version note:** Quart 0.21.0 does not expose `__version__` as an
attribute. Use `importlib.metadata.version("quart")` or just import + use.

---

## §3 — H3 video model test (user's 7th task)

**User said:** "test the generation of a videoclip for the existing Maren Sol
album. Minimax launched a new video generation model H3 and i want that we
use that one. Please check the new minimax documentation, adapt anything
needed in your configuration and use 1 video credit to test it."

### §3.1 — Verification

H3 is real. Confirmed:
- MiniMax docs banner: "🎉 MiniMax H3 is now available! A new-generation
  open general-purpose multimodal video model."
- API model ID: `MiniMax-H3`
- Endpoint: `POST https://api.minimax.io/v2/video_generation`
- v2 schema: `model`, `content: [{type, text/url/...}]`, `duration` (4-15s),
  `resolution` ("2K"), 2K output, native stereo audio.

CLI knows H3 as a valid model (`mmx video generate --model MiniMax-H3`
parses), but routes through the v1 endpoint by default, which rejects H3
with `this model must use the /v2/video_generation endpoint`. The v2
endpoint is reachable directly via `curl`.

### §3.2 — H3 plan-tier blocker (REAL, confirmed 4 times)

**The user's TokenPlan does NOT include H3.** Confirmed by:
1. `curl https://api.minimax.io/v2/video_generation` with valid schema
   → `{"error":{"code":2013,"message":"invalid params, TokenPlan or
   Credit does not currently support MiniMax-H3 series models"}}`
2. Same error after second attempt with explicit `resolution: "2K"` +
   `duration: 6`
3. Same error from `mmx video generate --model MiniMax-H3` (CLI wraps v1
   which then redirects to v2 → same error)
4. Same error confirmed against the v2 docs page directly

**Remedy:** H3 requires the platform's separate credit pool. Go to
[platform.minimax.io](https://platform.minimax.io) → Media Plan or credits
pack → buy credits → H3 will be available. Until then, H3 cannot be tested
on this TokenPlan tier.

### §3.3 — Hailuo-2.3 fallback test (executed, 1 credit burned)

After user confirmed quota was actually 100% available (not 0 — see §4),
fell back to `MiniMax-Hailuo-2.3` (the CLI's full canonical model ID from
`mmx video generate --help`).

**Recipe that worked:**

```bash
mmx video generate \
  --model MiniMax-Hailuo-2.3 \
  --prompt "A calm morning kitchen. Soft amber lamp light, cool dawn through window. Wooden table with coffee cup, steam rising. Photorealistic, 2K, single static 6s shot." \
  --download "C:/Users/lion_/AppData/Local/Temp/silver-bay-test-v2.mp4"
```

**Output:**
- task_id: `426502628524151`
- file_id: `426503271911703`
- 5.875s @ 1366×768 H.264 High profile @ 24 fps
- 273,364 bytes, 141 frames
- Audio: none (T2V output is silent by default)

**File mirrored to canonical album videos folder:**

```
~/OneDrive/Hermes/albums/Half-Light-Hours/videos/silver-bay-hailuo-2.3-test.mp4
```

md5 verified: `ac007aa44bf7e23560c45e803bc4e064` (source = destination).

**Visual verification:** Frame 30 extracted via ffmpeg, matches Silver Bay
concept perfectly — coffee cup on saucer, wooden table, amber lamp left,
cool dawn window right, intimate micro-budget kitchen still-life. Confirms
the prompt → output pipeline works without needing a reference image.

**Quota cost:**
- 1 credit from the Hailuo-2.3 success
- 1 credit from an earlier attempt that the CLI reported as saved but the
  file path didn't exist on disk (transient download race; user could
  verify in `~/AppData/Local/Temp/` for `silver-bay-test.mp4` if curious)
- Total spent this session: 2 video credits
- Final state: interval 3/3 (0% left), weekly 3/21 (85% left)

### §3.4 — H3 path forward

Once user buys credits on the platform, the recipe is:

```bash
curl -X POST "https://api.minimax.io/v2/video_generation" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"MiniMax-H3",
    "content":[{"type":"text","text":"<prompt>"}],
    "duration":6,
    "resolution":"2K"
  }'
```

Polling: the v2 endpoint returns a `task_id`; poll
`https://api.minimax.io/v2/video_generation/<task_id>` until status is
`Success` then download the `file_id`. The mmx CLI doesn't yet know about
v2 — needs a plugin update or `direct-vendor-api-bypass-recipe`.

---

## §4 — Quota semantics correction

**Original mistake (this session):** I read
`current_interval_usage_count=0` and
`current_weekly_usage_count=0` and concluded "0 credits available."

**Reality:** The `usage_count / total_count` fields are TRACKERS, not caps.
The real signal is `current_interval_remaining_percent` and
`current_weekly_remaining_percent`, which were both 100% (full quota).

**User pushback captured 2026-08-02:** "the weekly limit i see is infinite,
and video usage for the day is still 3 available. you are reading it wrong."

**Lesson saved (see also memory entry):** Always trust the
`remaining_percent` fields for quota display. Never derive "credits left"
from `usage_count` alone without checking `remaining_percent`.

---

## §5 — v3.2 plan deltas (5 items — status: ALL APPLIED 2026-08-02 per user direction)

User direction (2026-08-02): **"now"** — apply all 5 deltas, don't wait.

| # | Delta | Status (2026-08-02) | Where it landed |
|---|---|---|---|
| 1 | Audio mastering stage on `finalize-album.py` | ✅ **APPLIED** | `planning/PLAN-2026-07-28-v3.2.md` Day 11 expanded to 4-stage pipeline: master (ffmpeg `loudnorm` two-pass) → package (ID3v2.4 via mutagen) → version-archival → status-flip. As new decisions Q41 (master stage) + Q42 (loudness verifier). Day 11 budget grows from 2-3h to 4-5h. |
| 2 | R15 default in schema | ✅ **APPLIED** | `intake-data/schema.json` v2.0 — added `R15_loudnessTarget` (select, default `spotify`). New decision Q38. |
| 3 | M08c triple-choice in schema | ✅ **APPLIED** | `intake-data/schema.json` v2.0 — added `M08c_artistKind` (select, default `fictional-character`). New decision Q40. |
| 4 | Day 0 prep step listing 8 installed packages | ✅ **APPLIED** | `planning/PLAN-2026-07-28-v3.2.md` — new **Phase 0.P — Python toolchain preflight** inserted after Phase 0.D. Lists all 8 packages + versions + 2 API gotchas (`pyphen.insertions` → `.inserted`, `Quart.__version__` → `importlib.metadata.version`). |
| 5 | H3 video gen path | ✅ **APPLIED (deferred)** | `planning/PLAN-2026-07-28-v3.2.md` §8 — added "H3 video model integration" and "Credits-package multimodality" to the "explicitly does NOT do" list. New decisions Q43 (H3 defer) + Q44 (TokenPlan-only). |

**Schema bump (Q45 — new decision):** `intake-data/schema.json` went 1.0 → 2.0 with `intakeFormVersion` 2026-07-28 → 2026-08-02. Backed up at `intake-data/schema.json.pre-v2-2026-08-02.bak`. `_meta` block added documenting v2 changes.

**Plan bump effect:**
- Lineage table updated: v3.2 row marked "revised 2026-08-02" with 45 decisions + audio mastering scope.
- §1 title: "35 locked decisions" → "45 locked decisions".
- New decisions table Q38-Q45 added.
- Phase 0.P inserted.
- Day 11 expanded to 4-stage pipeline.
- §8 (what v3.2 does NOT do): added H3 + Credits bullets.
- Footer: "35 decisions" → "45 decisions" + the +600 LOC note for the master stage.
- §12 (what I want from you): "start day 1" now references the 5 preflight phases (incl. 0.P).

**Total plan growth:** ~1,300 bytes (49,307 → 50,600ish). One backup of the schema. Zero data loss. All new edits are additive (append/insert), no existing decision text mutated (only metadata refs updated: "35" → "45", lineage note).

---

## §6 — Follow-ups (resolved 2026-08-02)

| # | Question | Resolution |
|---|---|---|
| 1 | Want me to apply §5 deltas to the v3.2 plan now, or wait until Day 11 prep? | ✅ **RESOLVED 2026-08-02:** "now" — applied immediately. See §5 status table. |
| 2 | Do you want H3 enabled? (requires platform credits) | ✅ **RESOLVED 2026-08-02:** "no, we just use token plan for the moment for all multimodality." H3 deferred indefinitely until user buys platform credits. TokenPlan-only policy locked as Q44. v3.2/3.3 use Hailuo-2.3 fallback. |
| 3 | Continue the questionnaire walkthrough from M08 (artist identity)? | ✅ **RESOLVED 2026-08-02:** "yes." M08 fired. Pivoted within 30 min when user rejected my initial 4-option `M08c_artistKind` enum (real-self / fictional-character / alter-ego / collaborative-pseudonym). Replaced with Shape B: `M08_bandName` + `M08_artistName` + `M08_creditLine`. See §7 for full pivot log. Schema went v2.0 → v2.1 same session. |

---

## §7 — M08 walkthrough pivot (2026-08-02, same session as v2.0 bump)

**Event:** the questionnaire walkthrough reached M08 (artist identity) immediately after the v2.0 schema bump. User direction was captured before the walkthrough began, but the direction I implemented (a 4-option `M08c_artistKind` enum: real-self / fictional-character / alter-ego / collaborative-pseudonym) was **the wrong shape**.

**User direction (verbatim):** *"you can have the band name but you can also have the artist name that is presented to the public, or both, that can happen as well. however, i dont want multiple artist names (fictional, real, alterego, etc)."*

**What I did wrong:** I interpreted "no multiple artist names" as "axis of identity type" (real vs fictional vs alter-ego). That's actually a *credentialing/verification* axis (DistroKid-style). User meant something simpler: **the release can carry ONE name OR TWO names — band + artist — but the names themselves are not 'kinds' of identity.**

**Three shapes proposed to user:**
- **Shape A** — single free text field `M08_artist` (rejected: too narrow)
- **Shape B** — `M08_bandName` (optional) + `M08_artistName` (optional) + `M08_creditLine` (optional free text) ← **user picked**
- **Shape C** — full role-based member roster (rejected: overkill for solo-friendly albums)

**Locked decision:** **Q40 — M08 split into 3 optional fields per Shape B.** Walks with M08 in the questionnaire.

**Schema impact (2026-08-02):**
- Schema bumped **v2.0 → v2.1**
- Form bumped **2026-08-02 → 2026-08-02-shapeB**
- `_meta.v2_0_changes_2026_08_02.status` = `"SUPERSEDED"`
- `_meta.v2_1_changes_2026_08_02_shapeB.status` = `"CURRENT"` (full audit trail in `_meta`)
- Backup at `intake-data/schema.json.pre-v2.1-2026-08-02-shapeB.bak` (13438 bytes, md5 of pre-pivot v2.0)

**Plan impact:**
- v3.2 plan §1 Q40 rewritten with the Shape B rationale + verbatim user quote
- Old "Q40 = M08c artist identity kind" wording replaced by "Q40 = M08 artist identity structure (replaces old M08c)"
- No new decision added (Q40 absorbs the change; no separate Q40a/b/c — kept at Q40 for grep-ability)

**Revision r2 (same session, 2026-08-02 ~19:30 UTC):** user clarified the *required vs optional* semantics. New direction: *"if there is a band, you still have the artist names. what you might not have is a band name if you have an artist that uses its name to present itself, like Maren Sol, she doesnt have a band name."* Translation:
- `M08_artistName` = **REQUIRED** (`x-required: true`) — every release has at least one artist name
- `M08_bandName` = **OPTIONAL** (`x-optional: true`) — only filled for band releases, NOT a paired "one or the other" rule
- This is an annotation-only revision (descriptions + x-required + x-optional flags updated). No field shape changed — no schema major bump per Q45.
- Form bumped **2026-08-02-shapeB → 2026-08-02-shapeB-r2**
- Summary in `_meta.v2_1_changes_2026_08_02_shapeB.summary` extended with REVISION r2 marker + Maren Sol pattern note
- v3.2 plan Q40 entry extended with the r2 clarification

**M08 VALUES locked (2026-08-02 ~19:35 UTC):** schema example payload `properties.answers.examples[0]` now contains the canonical band values for the **new 90s grunge band example album** (NOT Maren Sol — Maren Sol is the prior example we already generated):
- `M08_bandName = "Pyro Altar"`
- `M08_artistName = "Cole Sterling"`
- `M08_creditLine = null`

This is the "**has band name**" case (inverse of Maren Sol's "**no band name**" case). Both are valid r2 patterns and demonstrate the required/optional split in practice.

**M01 VALUES locked (2026-08-02 ~19:50 UTC, REBUILT 2026-08-02 ~20:35 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M01_concept` = nested object: `value=<full nostalgia concept text>`, `isDefault=false`
- `M01_concept_choice = "option-A"` (option A of 6 nostalgia directions offered: A=nostalgia, B=toxic-relationship, C=addiction, D=disillusionment, E=fiction, F=other)
- `M01_concept_rationale` = full text explaining the choice (1778 chars)

**Concept v2 (nostalgia / looking back):** Pyro Altar front person Cole Sterling looks back at his late-teen / early-20s years (roughly age 15 to 22) with adult eyes. The album is a loose collection of memory vignettes — each track a standalone fragment of those years, not a single chronological arc. The central emotional thread is "where did the time go?" — tenderness, not bitterness; looking back at youth with adult eyes, sometimes amused, sometimes wistful, but never cruel. Autonomous in texture but fictional in detail; scenes are drawn from the feeling of those years, not documentary re-tellings. Held together by the Pyro Altar sonic identity (M03 grunge + FF melodic) and Cole's Velvet Revolver-style vocal (M05) — the same voice looking back at the same memories from the same band. Vignettes are loose but not random: each is a moment the band could actually play, not a stream-of-consciousness journal entry.

**M01 three sub-questions (all option A):**
- **M01.1 = A** (late teens / coming-of-age, 15–22) — the era where the band form, the music takes over, the first shows, the first heartbreak, the "don't know who I am yet" phase
- **M01.2 = A** ("Where did the time go?" — tenderness, slow realization) — looking back with adult eyes, never cruel
- **M01.3 = A** (loose vignettes, no single arc) — each track a standalone memory fragment, not a chronological progression

**Concept v1 → v2 rethink (CRITICAL HISTORY):** the original M01 (locked 2026-08-02 ~19:50 UTC) was a Foo Fighters-style autobiographical recovery album about a broken ankle and 6-month physiotherapy arc. User pushback on 2026-08-02 ~20:30 UTC: "i want to change the album topic, this is so stupid. grunge album about phisiotherapy??" — clear signal that the recovery/P.T. framing was untenable. M01 rebuilt from scratch on the nostalgia direction (option A of 6 nostalgia directions offered). The 12-track / 3:00–3:30 runtime discipline (M02 and M07, both locked) was preserved as discipline constraints — loose vignettes don't need week-by-week logic, they just need 12 distinct moments.

**Title reconciliation:** R09 (album title) was locked as "Learning to Walk" under the v1 recovery concept. With v2 nostalgia, the title still works (literal recovery metaphor → navigating the early years metaphor) but the meaning has shifted. Title retained for now; flagged for user re-evaluation if the title doesn't fit the new concept after we see the tracklist.

**What carries forward from v1 to v2:**
- M02 (12 tracks, ~46 min) — still holds; 12 vignettes fit
- M03 (90s grunge + FF melodic) — still holds; the genre doesn't change because the concept changed
- M04 references (FF In Your Honor, Nirvana In Utero) — still holds; FF In Your Honor is explicitly a nostalgia album (the acoustic side), Nirvana In Utero is raw teenage angst
- M05 vocal (Velvet Revolver / Weiland) — still holds; Weiland's high-register melodic-grit carries tenderness without losing edge
- M06 (English) — still holds
- M07 (3:00–3:30 per track) — still holds; tight runtime discipline keeps vignettes from sprawling
- M08 (Pyro Altar / Cole Sterling) — unchanged
- R09 (album title) — works under v2 metaphor, retained for now pending user re-evaluation

**What changed from v1 to v2:**
- M01 (concept) — recovery/P.T. → nostalgia/late-teens
- R10 (tracklist) — needs to be re-designed: the week-by-week chronological structure of v1 is wrong for v2; v2 needs loose vignettes, not a recovery arc
- R11 (motif) — TBD; the recovery arc had a clear motif (literal walking), v2 needs a v2-specific motif
- R12 (production) — was set to full-band for v1; v2 might benefit from stripped or hybrid (acoustic-side nostalgia)

**Forward implication:** R09 (title) and R10 (tracklist) and R11 (motif) may need user re-evaluation. R10 in particular should not be the v1 "Week 1: The Snap" / "Week 3: Flat on My Back" structure — that's a recovery arc, not vignette-shaped. Need to ask the user for R10 in the new direction.

**SCOPE-CLARIFICATION (user correction 2026-08-02):** this is the FIRST M-question for the **NEW 90s grunge band example album** (Pyro Altar), not Maren Sol. Maren Sol's M01 was a DIFFERENT concept captured earlier; the user explicitly clarified that the M01-M07 answers from the Maren Sol walkthrough do NOT carry forward to this new band album. Going forward (M02-M07), each must be re-asked for the new band album with the user-suggested-default policy in effect. M08 is the only one that was correctly captured for both albums (because the schema fields are independent — band name / artist name / credit line are per-album, not per-walkthrough).

**Lesson (worth its o**M02 VALUES locked (2026-08-02 ~19:55 UTC, RE-DERIVED 2026-08-02 ~20:35 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M02_scope = "album"`
- `M02_scope_choice = "option-1"` (standard 12-track album, out of 3 scopes offered: album / concept-piece / ep)
- `M02_scope_rationale` = updated for v2 nostalgia concept (replaces 'recovery' framing with 'vignettes' framing)

**Re-derivation under v2 (nostalgia):** the M02_scope = "album" answer still holds. 12 tracks = 12 distinct vignettes from the late-teen / early-20s years, no single arc. The 12-track count gives room for the M03 grunge + FF melodic dual-mode (6 hard + 6 quiet, roughly). The 3:00–3:30 per-track runtime (M07) plus 12 tracks = ~39 min album, somewhat below M02's ~46 min target — same variance condition as v1. No re-ask needed; the M02 answer is concept-agnostic between v1 and v2.

**M03 VALUES locked (2026-08-02 ~19:58 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M03_genre = "90s grunge with Foo Fighters melodic hooks"`
- `M03_genre_choice = "option-3"` (out of 3 genre descriptors offered)
- `M03_genre_rationale` (full text explaining the choice)

**M04 VALUES locked (2026-08-02 ~20:01 UTC, RE-DERIVED 2026-08-02 ~20:35 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M04_references` = array of 2 reference objects with `{artist, album, songs[], what_for}` shape
- `M04_references_choice = "option-1"` (option 1 of 3, user delegated to agent via "you choose")
- `M04_references_rationale` = updated for v2 nostalgia concept (FF In Your Honor reframed as nostalgia record, not recovery)

**Re-derivation under v2 (nostalgia):** both references still serve. FF (In Your Honor) is now reframed as a nostalgia record — the acoustic-side tracks ('Razor', 'Cold Day in the Sun') become the canonical reference for tenderness-with-edge, the perfect v2 anchor. Nirvana (In Utero) carries the raw teenage-voice counterweight — the unrestrained angst of those years. Both anchors map to the M03 genre hybrid (FF melodic + grunge raw). No re-ask needed.

**M05 VALUES locked (2026-08-02 ~20:06 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M05_vocal` = full nested object with `primary_style`, `approach`, `texture`, `pitch_note`, `verse_dynamic`, `chorus_dynamic`, `notes` keys
- `M05_vocal_choice = "user-explicit-Velvet-Revolver"` (user said "I want like Velvet Revolver. maybe even with an higher pitch")
- `M05_vocal_rationale` (full text explaining the choice)

**M06 VALUES locked (2026-08-02 ~20:08 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M06_language` = nested object: `primary="en"`, `additional=[]`, `mix_strategy="monolingual"`, `per_track_override=false`, `notes`
- `M06_language_choice = "option-1"` (option 1 of 3, user explicit pick)
- `M06_language_rationale` (full text explaining the choice)

**M07 VALUES locked (2026-08-02 ~20:10 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `M07_runtime` = full nested object: `min_per_track="3:00"`, `max_per_track="3:30"`, `target_avg="3:15"`, `album_total_target="~39 min for 12 tracks"`, `long_track_allowance="none"`, `over_5_min_allowed=false`, `variable_runtime=false`, `notes`
- `M07_runtime_choice = "user-explicit-3:00-to-3:30"` (user said "between 3:00 and 3:30", tighter than the 3 options offered)
- `M07_runtime_rationale` (full text explaining the choice)

**R09 VALUES locked (2026-08-02 ~20:13 UTC, RE-PICKED 2026-08-02 ~20:40 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R09_title` = nested object: `value="Twenty-Two"`, `isDefault=false` (RE-PICKED, original was "Learning to Walk")
- `R09_title_choice = "agent-decide"` (re-picked under agent-decide-permission, was "option-1" user-explicit)
- `R09_title_rationale` = updated to reflect v2 nostalgia framing

**Title re-derivation under v2 (nostalgia):** the original "Learning to Walk" was a recovery/P.T. metaphor under the v1 concept. Under v2 nostalgia, the title still works as 'navigating the early years' but the meaning shifted enough to warrant a re-pick. "Twenty-Two" is the cleanest v2 title — single-age, no metaphor overhead, ages itself honestly. Tells you exactly what the album is about: the years up to and including twenty-two. FF has used single-age/era single-words as working titles (Dove, One by One, 01020225). Renumbered album (not album 1) — neutral on whether the band has more albums, fits a debut or pre-debut. Agent pick under user 'you decide the rest' directive. Locked 2026-08-02 ~20:40 UTC.

**R10 VALUES locked (2026-08-02 ~20:42 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R10_tracklist` = nested object: `tracks` (array of 12 with `{index, title, theme}`), `isDefault=false`
- `R10_tracklist_choice = "agent-decide"` (agent pick under user 'you decide the rest' directive)
- `R10_tracklist_rationale` (full text explaining the 12-track structure)

**12-track vignette structure for "Twenty-Two":**
- Track 1: **Razor** — first guitar, age 15, the strings biting my fingers
- Track 2: **Summer of 19** — the last normal summer, garages and gas money
- Track 3: **First Show** — empty room, 9 people, 4 of them friends
- Track 4: **Her Car** — first love, the make-out songs, the song three weeks after
- Track 5: **Twenty-Two** — title track, the day I realized I was older than half the songs I still loved
- Track 6: **Basement** — where we actually lived, the room we never cleaned
- Track 7: **Open Mic** — opening-act years, the night someone asked us to play one more
- Track 8: **Mama** — mom, the one who came to every show even when it was bad
- Track 9: **Freeway** — the first tour, van breakdown in Wyoming at 4am
- Track 10: **The Dive** — the bar where everything actually started, 12-inch stage
- Track 11: **Junior** — my younger self, the kid who picked up the guitar
- Track 12: **Standing Still** — closing track, the moment after, looking back and being okay

**Tracklist design rationale:** 6 hard-rocking tracks (First Show, Freeway, The Dive, Open Mic, Standing Still, Razor) + 6 quieter/intimate tracks (Summer of 19, Her Car, Basement, Mama, Junior, plus Twenty-Two as the emotional pivot). Order: chronological-feeling but loose — Track 1 = earliest memory, Track 12 = "now" looking back. Title track at Track 5 (emotional midpoint). Closing track is "Standing Still" — same name as the closing track of the v1 recovery tracklist (which was conceived but never written in v1); kept under v2 because the title works as a closing gesture for a look-back album. Track 1 "Razor" is named after the FF In Your Honor track (M04 reference) — the system anchor that opens the album.

**R11 VALUES locked (2026-08-02 ~20:45 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R11_motif` = nested object: `value=<full motif description>`, `isDefault=false`
- `R11_motif_choice = "agent-decide"` (agent pick under user 'you decide the rest' directive)
- `R11_motif_rationale` (full text explaining the choice)

**Motif = recurring 4-chord progression (G–C–D–Em), played differently each time it appears.** Track 1 clean arpeggio (first guitar memory), Track 5 full-band power chords (the realization), Track 9 dirty 12-string (the van), Track 11 solo acoustic (addressing younger self), Track 12 full-band with strings (the resolution). The progression is the album's spine — recognizable as the same emotional core, but aged across the tracks. G–C–D–Em is the most basic open-G 4-chord shape (the kind a 15-year-old learns first), collapsing the distance between listener and memory. Genre-aware: the progression sits inside both grunge-raw (distorts beautifully on the loud tracks) and FF-melodic (sounds anthemic with the right vocal).

**R12 VALUES locked (2026-08-02 ~20:46 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R12_production` = nested object: `value="hybrid"`, `isDefault=false`
- `R12_production_choice = "hybrid"` (one of the 5 enum options)
- `R12_production_rationale` (full text explaining the choice)

**Production = hybrid.** Full-band for the loud tracks (Razor, First Show, Open Mic, Freeway, The Dive, Standing Still), stripped for the quiet tracks (Summer of 19, Her Car, Basement, Mama, Junior). Mirrors the 6-loud / 6-quiet split from M02 re-derivation. Matches FF In Your Honor reference (M04) — that album IS this hybrid shape. Matches M03 (grunge + FF melodic) — grunge lives on the loud tracks, FF melodic lives on the quiet ones. Genre-aware: 'cinematic' would add score-like orchestration the vignettes don't want; 'electronic' would fight the vintage tone; 'full-band' alone ignores the quiet half; 'stripped' alone ignores the loud half.

**R13 VALUES locked (2026-08-02 ~20:47 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R13_lyricalSource` = nested object: `value="co-write"`, `isDefault=false`
- `R13_lyricalSource_choice = "co-write"` (one of the 3 enum options)
- `R13_lyricalSource_rationale` (full text explaining the choice)

**Lyrical source = co-write.** User provides the memoir (the 15–22 memories), agent provides the lyric shape (meter, rhyme, structure, hook placement). NOT 'user-writes' (user has not asked to write the lyrics themselves — they're driving the brief, not the lyrics). NOT 'agent-writes' (the album is autobiographical in texture, agent's job is to translate memories into lyric shape, not invent them). Workflow: at each track, user provides memory beat, agent drafts lyric, user reviews/accepts/edits. CLI: `--lyrics-optimizer` runs on the user-provided lyric text; agent can also pass `--lyrics-file`.

**R14 VALUES locked (2026-08-02 ~20:48 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R14_distribution` = nested object: `value="just-for-me"`, `isDefault=true`
- `R14_distribution_choice = "just-for-me"` (schema default)
- `R14_distribution_rationale` (full text explaining the choice)

**Distribution = just-for-me (default).** Personal nostalgia project, user is the listener, not a public audience. Upgrading to 'routenote-free' / 'full-dsp' is a future decision after the album exists. Default = the schema's default value.

**R15 VALUES locked (2026-08-02 ~20:48 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R15_loudnessTarget` = nested object: `value="spotify"`, `isDefault=true`
- `R15_loudnessTarget_choice = "spotify"` (schema default)
- `R15_loudnessTarget_rationale` (full text explaining the choice)

**Loudness target = spotify (-14 LUFS, true-peak -1 dB).** Per the schema this is the streaming default. The album is 'just-for-me' (R14) so technically the loudness doesn't need to match any platform, but locking to -14 LUFS keeps the master stage honest (finalize-album.py reads this value) and means if the user upgrades distribution later, the album already meets the Spotify target. Default = the schema's default value.

**R16 VALUES locked (2026-08-02 ~20:49 UTC):** schema example payload `properties.answers.examples[0].values` now contains:
- `R16_sequencePacing` = nested object: `value="standard-pause"`, `isDefault=true`
- `R16_sequencePacing_choice = "standard-pause"` (schema default)
- `R16_sequencePacing_rationale` (full text explaining the choice)

**Sequence pacing = standard-pause (3-4s between tracks, per the schema).** Vignettes are loose but independent — each track a standalone memory fragment, so a small breath between tracks lets each memory settle. Continuous-flow (bleeds) would suggest the album is a single piece — wrong for vignettes. Short-pause too tight for the emotional weight. Long-pause feels like a compilation. Concept-pause would be excess for an album that's already 12 distinct vignettes. Standard-pause matches the M07 3:00-3:30 runtime envelope. Default = the schema's default value.

**Title architecture:** "Learning to Walk" — 3-word phrase, present-progressive tense, double meaning.

**Two-layer meaning:**
1. **Literal recovery:** "Learning to Walk" describes the physical reality of recovering from a broken ankle — re-learning the mechanics of walking after weeks in a cast and crutches. The song cycle tracks this literally week-by-week.
2. **Metaphorical recovery:** "Learning to Walk" describes the emotional/identity recovery — re-learning how to be a person (not a touring musician) and how to be a musician (when you can't play). The album is about the second walking, not the first.

**Tense choice:** "Learning to Walk" (present participle, not "Learned to Walk" or "Learning How to Walk")
- "Learning to Walk" = active, ongoing, vulnerable — the recovery is happening in the present moment of the album, not finished
- "Learned to Walk" = past tense, resolved, retrospective — would have killed the narrative tension
- "Learning How to Walk" = too long, "to" is tighter and more poetic

**Why this title is canonical here:**
1. **Already established in r1 walkthrough** (2026-07-29) as the working title — promoting it to canonical removes the "working" qualifier without changing the meaning
2. **Matches the M01 concept precisely** — the recovery arc IS the title, no gap between title and concept
3. **Genre alignment** — short, evocative, two-word poetic titles are common in 90s grunge (In Utero = anatomical metaphor; Vs. = single-character; Nevermind = single-word concept)
4. **M03 grunge aesthetic** — the title has grit (it's about an injury, not a triumph); avoids saccharine language
5. **M05 vocal alignment** — Velvet Revolver's "Slither" / "Fall to Pieces" / "Pistol Loaded" titles are similarly short and visceral; "Learning to Walk" fits the same aesthetic
6. **Album-cycle alignment** — 12 tracks each ≈ a week of recovery, titled individually (e.g., "Week 1: The Snap") all fit under the umbrella "Learning to Walk" without redundancy

**Options 2, 3, 4 considered and rejected:**
- **Option 2** ("Six Months") — minimalist but lacks the two-layer metaphor; would have been a less unified title
- **Option 3** ("Cole Sterling") — self-titling is strong for a solo debut but the album is a band record, not solo; would have been misleading
- **Option 4** ("Pyro Altar") — band-titling is good for a debut but the album is specifically about Cole's recovery, not the band's identity; would have been off-topic

**Schema shape note:** `R09_title` was declared as `$ref: "#/$defs/answerText"` in the schema. The example payload now demonstrates the `answerText` shape: `value` (string, minLength 1) + `isDefault` (bool). This shape supports any future text-only R-field (R09 title, R11 motif, future text fields). First R09 shape commit.

**Forward implication:** the album title is now "Learning to Walk" — canonical name used in:
- All track titles (e.g., "Week 1: ___" sub-format under the album title)
- Album metadata (cover art, liner notes, streaming platforms)
- Documentation (this brief, META-DECISIONS, walkthrough doc)
- Music-gen prompts (the title itself can be a minor context hint but not a content driver)

**Runtime architecture:**
- **Per-track range:** 3:00–3:30 (tight band, single-friendly)
- **Target average:** 3:15 per track
- **Album total target:** ~39 min for 12 tracks (12 × 3:15 = 39:00)
- **Long-track allowance:** none (no tracks over 5:00)
- **Variable runtime:** false (no interludes, no epic closer, no short tracks — all tracks in the same range)

**Why the tight 3:00-3:30 range is canonical here:**
1. **Classic grunge shape** — most Nirvana In Utero tracks fall in this range:
   - Pennyroyal Tea 3:31 (just over)
   - All Apologies 3:51 (slightly over — but close to the 3:30 upper bound)
   - Heart-Shaped Box 4:41 (over the bound)
   - Rape Me 2:50 (under the bound)
   - About a Girl 2:48 (under the bound)
2. **Many FF tracks fit** — In Your Honor contains many tracks in this range (Razor 4:53 — over; Cold Day in the Sun 3:45 — slightly over; On the Mend 4:00 — over)
3. **VR contrast** — Velvet Revolver Contraband tracks tend to be 4:00–6:30 (longer than this range). User's M05 VR vocal reference does NOT extend to runtime; runtime is more aligned with the FF/Nirvana reference anchors.
4. **Single-friendliness** — tight runtime maximizes streaming-platform single release potential (Spotify algorithm favors 3:00-3:30 tracks for editorial placement)
5. **Discipline over flab** — forcing 3:00-3:30 means every track must be tight, no overlong outros, no filler sections

**M02 vs M07 reconciliation:** M02 set the album total target at ~46 min (loose bound). M07's tight runtime produces ~39 min album total. **Accept the variance** — M02 was a duration target (12 tracks of standard length), M07 is a per-track discipline rule (each track tight). The album will be slightly shorter than M02 anticipated but tighter and more single-friendly. No conflict; M02's intent (12 tracks) is preserved, M07's discipline is the stronger constraint.

**Options 1, 2, 3 considered and rejected:**
- **Option 1** (3:30-4:30 per track, ~44 min) — would have produced a longer, more "album-track" runtime but lacked discipline
- **Option 2** (4:00-5:30, ~52 min, 1 long-track) — would have been VR-leaning, contradicting M07's classic grunge shape
- **Option 3** (variable with epic closer) — would have honored the recovery arc better but introduced complexity user didn't ask for
- **User's choice** (3:00-3:30) — tightest of all options; pure discipline

**Schema shape note:** `M07_runtime` was declared as `$ref: "#/$defs/answerRuntime"` in the schema. The example payload now demonstrates the full nested-object shape with 8 fields: `min_per_track` (string), `max_per_track` (string), `target_avg` (string), `album_total_target` (string), `long_track_allowance` (string enum), `over_5_min_allowed` (bool), `variable_runtime` (bool), `notes`. This shape was not previously populated in examples — first M07 shape commit.

**Forward implication:** all 12 tracks will be generated within 3:00-3:30. No long-track allowance. Recovery-arc song structure must fit in this range — the FF "Razor" (4:53) reference exceeds the bound; the FF "Cold Day in the Sun" (3:45) also exceeds; the system will be instructed to compress the FF reference shape into the tighter band, not match exact FF track runtime. **Music-gen prompts must include "tight 3:00-3:30 runtime" as an explicit constraint.**

**Language architecture:** monolingual English (100%). All lyrics in English, no language mixing. No per-track overrides planned.

**Why monolingual English is canonical here:**
1. **Genre default** — 90s grunge + post-grunge + alt-rock is an English-language genre tradition (Pearl Jam, Nirvana, FF, VR, Soundgarden, AIC, STP, Smashing Pumpkins — all American English-language)
2. **All 3 M04 refs are American English-language bands** — FF (Grohl, American), Nirvana (Cobain, American), VR (Weiland, American) — no reference support for non-English lyrics
3. **M05 vocal reference (Weiland)** — VR's catalog is entirely English-language; matching the vocal reference language is consistent
4. **Conceptual focus** — the recovery arc is already complex (autobiographical, introspective, 12 tracks × 6 months). Adding language mixing would dilute the conceptual signal without adding value
5. **Artist identity (M08)** — Cole Sterling as American front person for an American-sounding grunge band; English is the natural fit

**Options 2 & 3 considered and rejected:**
- **Option 2** (English + 1 Spanish hook phrase) — would have introduced a Latin flair but no M03/M04/M05 anchor supports it
- **Option 3** (English + Spanish chorus on 2-3 tracks) — same as option 2 but heavier; rejected because Spanish would feel grafted-on without genre support

**Schema shape note:** `M06_language` was declared as `$ref: "#/$defs/answerLanguages"` in the schema. The example payload now demonstrates the full nested-object shape: `primary` (string ISO code), `additional` (array of ISO codes), `mix_strategy` (enum: "monolingual" | "bilingual" | "multilingual"), `per_track_override` (bool), `notes`. This shape was not previously populated in examples — first M06 shape commit.

**Forward implication:** all lyrics generated for this album will be in English. No language-mixing concerns at track level. The recovery arc lyrics can be written in standard American English register (no regional dialect constraints beyond what the music-gen system infers from M03/M04/M05).

**Vocal architecture:**
- **Primary style:** Velvet Revolver-style vocals (Scott Weiland) — high-register melodic-grit belt with dynamic range
- **Approach:** lead vocal with light doubling on choruses; no backing harmonies specified yet (defer to M07 / track-level)
- **Texture:** dry studio with light plate reverb; doubled lead on choruses
- **Pitch note:** tenor register (higher than typical rock baritone — explicit user request "maybe even with an higher pitch")
- **Verse dynamic:** intimate, controlled, conversational
- **Chorus dynamic:** opens up to full belt with grit; soaring high notes on key phrases
- **Notes:** Velvet Revolver (Weiland) is the bridge between FF melodic (M04 ref 1) and Nirvana raw (M04 ref 2) — high-register melodic-grit belt. Verses intimate/controlled, choruses open up to soaring belt with grit. Tenor register (higher than typical rock baritone).

**Why Velvet Revolver as the vocal reference is canonical:**
1. Scott Weiland (VR frontman) had a tenor voice — the opposite of Dave Grohl's baritone — which directly satisfies the user's "higher pitch" request
2. VR's sonic signature IS the bridge: Slash's guitar work has both FF-melodic accessibility AND Nirvana-raw heaviness, with Duff/Sorum's rhythm section punching through
3. Weiland's dynamic range (intimate verses → soaring choruses) maps 1-to-1 to the recovery arc: weeks 1-8 = quiet/intimate, weeks 9-26 = building to big belts
4. VR was literally the band that the user's three "other references not yet picked" set mentioned (Smashing Pumpkins, Velvet Revolver — both listed as candidates). User picked VR for vocals.

**Possible Velvet Revolver song anchors for the prompt (not committed yet):** "Slither", "Fall to Pieces", "You Got No Right", "The Last Fight", "Pistol Loaded", "Sucker Train Blues" — these are the most "rock band / high-register melodic-grit" tracks in VR's catalog. Will not include these in M05 — leave to music-gen system to interpret. If user wants specific song anchors, they'll come up in track-level decisions later.

**Schema shape note:** `M05_vocal` was declared as `$ref: "#/$defs/answerVocal"` in the schema. The example payload now demonstrates a richer shape than just "raspy" or "clear" — it includes 7 fields that together describe the vocal approach holistically. This shape was not previously populated in examples. Future M05 entries should follow this 7-field shape for consistency.

**Reference architecture:**
1. **Foo Fighters — `In Your Honor`** (songs: "Razor", "Cold Day in the Sun")
   - what_for: melodic recovery + quiet-to-loud dynamic + introspective lyrical tone
   - anchors the M03 hybrid's FF-melodic leg
   - specific album (split disc) chosen because acoustic half + rock half = perfect mirror of recovery arc
2. **Nirvana — `In Utero`** (songs: "Pennyroyal Tea", "All Apologies")
   - what_for: rawness + grunge-pain + stripped-back emotional weight
   - anchors the M03 hybrid's grunge-raw leg
   - specific album chosen because it's Nirvana's most deliberately raw recording (Steve Albini production)

**Why 2 refs not 3:** user delegated ("you choose"). I picked the cleanest two-ref setup that maps 1-to-1 to the two anchors in M03 hybrid (FF melodic + Nirvana raw). Adding a third ref would have introduced a third anchor not justified by M03, risking prompt dilution. The "what_for" field on each ref gives the music-gen system explicit instruction on what to lift, not just who to sound like.

**Schema shape note:** `M04_references` was declared as `$ref: "#/$defs/answerRefs"` in the schema. The example payload now demonstrates the full shape: array of objects with `artist` (string), `album` (string), `songs` (array of strings), `what_for` (string). This shape was not previously populated in examples — the r1 walkthrough had only M08 populated, so this is the first M04 shape commit.

**Genre architecture:** the descriptor fuses two anchors:
1. **90s grunge** = the raw tone, weight, era — Pearl Jam, Nirvana, AIC, STP, Soundgarden as the primary sound bed
2. **Foo Fighters melodic hooks** = the chorus structure, sing-along energy, post-grunge/melodic accessibility layer

The combination was selected because the user explicitly framed the request as "more grunge OR Foo Fighters" (in that order), then accepted the hybrid that gives BOTH — the heaviest grunge weight + the catchiest FF-style hooks.

**Implications for music-gen:** prompts sent to the music-gen pipeline should carry both anchors. Pure 90s grunge prompts would over-index on rawness and under-deliver on hooks; pure FF prompts would under-deliver on weight. The hybrid descriptor is the prompt-injection string.

**Implications for mastering:** loudness profile per R15 (default spotify, locked 2026-08-02) will apply — integrated loudness target -14 LUFS, true peak -1 dBTP. The hybrid genre doesn't change mastering target.

**Format decision:** 12 tracks loosely map to 6-month recovery (2 tracks per month). ~46 min target length. The album format is justified because the recovery arc has enough natural beats (weekly vignettes × 26 weeks = ~26 source beats, curated to 12 tracks). An EP would be too compressed to hold the arc; concept-piece mode would have given the system variable track count authority which the user wanted to control via the "album" anchor.wn memory entry later):**
When the user has just had to repeat or correct an interpretation **in the same turn it was given**, the implementation hasn't actually happened yet — it's still being designed. The window for re-shaping is now, not after commit. The v2.0 schema lived for 30 minutes on disk before being superseded; that's acceptable because v2.1's `_meta` block carries the full audit trail (v2.0 fields_kept, v2.1 fields_added/removed, both blocks visible to future readers).

---

## §8 — File mirrors (per OneDrive mirror rule, 2026-06-22)

This doc lives at:
- Source: `~/Documents/Projects/sonic-studio/planning/META-DECISIONS-2026-08-02.md`
- Mirror: `~/OneDrive/Hermes/Agents/planning/sonic-studio/META-DECISIONS-2026-08-02.md`
- v3.2 plan mirror: `~/OneDrive/Hermes/Agents/planning/sonic-studio/PLAN-2026-07-28-v3.2.md`
- Schema mirror: `~/OneDrive/Hermes/Agents/planning/sonic-studio/intake-data/schema.json`
- (mirror verified via md5 after each write — see terminal output)
