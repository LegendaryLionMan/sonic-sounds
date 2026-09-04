# sonic-studio Questionnaire Walkthrough — 2026-07-29

**Source of truth:** Live walkthrough with the user. Each section locks a schema
field for `intake-data/concept-briefs/*.json` and may add per-song params.

**Status legend:** ✅ locked | ⏳ pending

---

## §1 — Decisions captured (verified from live mmx CLI + official docs)

### Q: What does MiniMax music_generation actually expose for vocal/artist control?

**Source of truth:** Verified against `mmx music generate --help` (live CLI on this
host, mmx 1.0.16) AND `https://platform.minimax.io/docs/llms-full.txt` (602KB
llms-friendly mirror of the music docs, downloaded 2026-07-29).

**Findings — what the API has:**

| Parameter | What it controls | Verified at |
|---|---|---|
| `model` | `music-3.0` / `music-2.6` / `music-cover` | CLI `--help` |
| `prompt` | Free-text style description (genre, mood, vocals, instruments, BPM, key, structure) — max 2000 chars combined | CLI `--help` + docs |
| `lyrics` | Lyrics with `[Verse]`/`[Chorus]`/`[Bridge]`/etc structure tags | CLI `--help` |
| `lyrics-optimizer` | Auto-generate lyrics from prompt | CLI `--help` |
| `lyrics-file` | Read lyrics from file | CLI `--help` |
| `is-instrumental` | Vocal-less track (music-3.0+) | Docs |
| `vocals` | Vocal **style** (e.g. "warm male baritone", "duet with harmonies") | CLI `--help` |
| `genre` | Genre (folk, pop, jazz, electronic) | CLI `--help` |
| `mood` | Mood/emotion | CLI `--help` |
| `instruments` | Instruments to feature | CLI `--help` |
| `tempo` / `bpm` | Tempo (free-text or exact) | CLI `--help` |
| `key` | Musical key | CLI `--help` |
| `avoid` | Elements to avoid | CLI `--help` |
| `use-case` | Use case context | CLI `--help` |
| `structure` | Song structure | CLI `--help` |
| `references` | Reference tracks/artists | CLI `--help` |
| `extra` | Additional fine-grained requirements | CLI `--help` |
| `audio_setting` | sample_rate/bitrate/format | CLI `--help` |
| `output_format` | `hex` or `url` (24h expiry) | CLI `--help` |
| `aigc_watermark` | Embed watermark | CLI `--help` |
| `stream` | Stream raw audio | CLI `--help` |

**Findings — what the API does NOT have (user explicitly asked about these):**

- ❌ **No curated voice catalog.** T2A (speech) has 73 `voice_id`s; music has only
  the `vocals` free-text field. There is no "pick from a list of named voices" for music.
- ❌ **No `language` parameter.** Language is implicit in the `lyrics` text — Spanish
  lyrics produce Spanish vocals, English lyrics produce English vocals.
- ❌ **No discrete `gender` / `age` / `pitch` knobs.** All conveyed via free-text in
  `vocals` (e.g. "young male tenor", "weathered alto", "bright soprano with vibrato").
- ❌ **No pre-made voice samples to audition.** The only way to "preview" a `vocals`
  string is to actually generate a sample clip and play it back.

---

### §1.1 — Decisions for Q08 Layer B (vocal/artist characteristics)

| # | Decision | Locked |
|---|---|---|
| §1.1.a | **Audition clips at intake** — generate 3-5 short sample clips per audition so the user picks the `vocals` text by ear | ✅ |
| §1.1.b | **Front-person audition (Option B)** — front person gets audition; backing members get text-only `vocals` chosen from named suggestions. Default: audition only the band's `isFrontPerson: true` member. | ✅ |
| §1.1.c | **Exception case: per-track front designation** — any non-front member can be promoted to "tracks front" on a per-song basis; on first such designation, they go through the audition flow once (3-5 clips) and the chosen `vocals` string is cached. Future songs reuse the cached text. | ✅ |
| §1.1.d | **All generation parameters captured per song** — every field above (`vocals`, `genre`, `mood`, `instruments`, `tempo`, `bpm`, `key`, `avoid`, `use-case`, `structure`, `references`, `extra`, `is-instrumental`, `lyrics-optimizer`, plus `lyrics`, `lyrics-file`, `prompt`, `model`) is recorded in the per-song `generation_params` block, alongside response metadata (`trace_id`, `actual_duration_ms`, `actual_size_bytes`, `audio_url`). | ✅ |
| §1.1.e | **`is-instrumental` is a per-song toggle** in the per-song params, used for intros, outros, interludes. | ✅ |
| §1.1.f | **Always ask front-person gender** as a binary choice — **male / female only**. No other gender options offered. (USER EXPLICIT MANDATE 2026-07-29: "ask male or female. i dont want other genders!") | ✅ |
| §1.1.g | **Audition clip length = ~20 seconds.** 3-5 candidates × 20s = 60-100s of generated audio per member audition. | ✅ |
| §1.1.h | **No duet auditions by default.** Only generate duet clips if the user explicitly asks for one during the audition flow. | ✅ |
| §1.1.i | **Front person gender = male.** (USER ANSWER 2026-07-29.) | ✅ |
| §1.1.j | **Audition generation = SEQUENTIAL, one at a time.** User validates each clip before the next is generated. **Never launch parallel audition requests.** Rationale (USER EXPLICIT MANDATE 2026-07-29): (a) the first call might fail, wasting subsequent quota; (b) parallel calls risk rate-limit hits. Workflow: generate clip 1 → user listens + validates → generate clip 2 → validate → ... until all candidates are auditioned. | ✅ |

### §1.3 — Critical music-generation facts (learned 2026-07-29 from re-investigation)

**Verified live + from past session artifacts in `~/OneDrive/Hermes/music/*.md`:**

1. **The CLI `mmx music generate` does NOT stream.** Non-streaming requests hit a 60-second wall (HTTP response-body idle timeout on this Windows host). The CLI gives `rc=6 Network request failed` at ~60s.
2. **The plugin's `mmx_music_generate` is a thin CLI wrapper** — it does NOT pass `stream=true` or `target_minutes`. So it inherits the same 60s wall.
3. **The `minimax-music-long-form` skill's v6 streaming recipe is documented but the plugin doesn't implement it.** Real-world path: CLI short clips only (≤2 min), or hit the 60s wall.
4. **Maren Sol's actual track durations were 0:22-2:21 (from the sidecar `.md` files in `~/OneDrive/Hermes/music/`)** — NOT the aspirational 3:24-4:38 in the README. The README was a plan, not the delivered result. The 10 tracks in `Half-Light-Hours/music/` are 5-7 MB mp3s, each ~2-4 minutes actual — but those came from a separate generation session, not from the inline-plugin-mirror sidecars. The actual delivery is a hybrid: short auditions + long-form tracks concatenated in some way (not via the plugin's documented path).
5. **`rc=6 Network request failed` = batched-call transport failure.** Documented in `minimax-music-long-form` SKILL.md. Fix: wait 15-30s and retry with **SAME parameters, no changes**. Do NOT drop `--lyrics` or change the prompt.
6. **`music-3.0` (default in current CLI) and `music-2.6` both 1033 in waves.** Auto-fallback to `music-2.0` is documented but not in the plugin.
7. **For 20-second auditions: the CLI short-clip path should work** because the request finishes before 60s. The earlier `rc=6` I hit was likely the transport failure pattern, not a parameter bug.
8. **Lyrics creation path:** Maren Sol used `lyrics_optimizer: true` (model writes the lyrics). For auditions, same approach: throwaway lyrics via the optimizer, then change later.

### §1.4 — Audition pipeline (corrected after re-investigation)

1. **Use CLI `mmx music generate`** with `music-2.6` (or `music-2.6-free` to save quota), `lyrics-optimizer`, **~20s target** by NOT adding structure hints (model picks short). Explicit `--output-format url` returns an `audio_url` we can download.
2. **If `rc=6` (Network request failed):** wait 15-30s, retry with **same parameters**. Do NOT change.
3. **If still failing after 2 retries:** fall back to `music-2.6-free` (RPM 3, may not be the same model path).
4. **For each candidate:** generate clip, save to `~/OneDrive/Hermes/Agents/planning/sonic-studio/auditions/`, log the `trace_id`, `actual_duration_ms`, `actual_size_bytes` to the walkthrough doc for traceability.
5. **Validate after each clip.** User says "next" or "reroll" or "this is the one".

### §1.2 — Audition candidates for front person (male, pop-punk + grunge dirt, raw/gritty)

4 candidate `vocals` strings, ~20s audition clip each. Range from cleanest to roughest so the user can pick the punk-edge they want.

| # | Candidate `vocals` text | Character |
|---|---|---|
| A | "raw male baritone with garage grit, slight rasp, punk edge, room noise preserved" | Mid-rough, the M05 default feel |
| B | "raspy male tenor with punk attitude, melodic sing-shout, audible breath, slight nasal" | Punchier, Blink-182-adjacent |
| C | "young male alto, breathy and melodic, clean punk delivery with slight edge on chorus" | Cleanest of the four — if you want more polish |
| D | "weathered male baritone, gritty punk vocal with attitude, distorted edges, lo-fi room tone" | Roughest, Velvet Revolver-adjacent |

**4 candidates × 20s = 80s of generated audio.** Quota spend: ~4 calls (well within budget).

**Audition prompt template (used for each candidate):**

```
prompt = "pop-punk with grunge dirt, garage band, raw and energetic, fast tempo, driving drums, distorted guitars, melodic bass"
vocals = "<candidate text>"
genre = "pop-punk"
mood = "raw, energetic, rebellious"
instruments = "distorted electric guitar, driving drums, melodic bass, no synthesizers"
tempo = "fast"
bpm = 165
structure = "verse-chorus-verse-chorus"
lyrics-optimizer = true   # generate throwaway lyrics so we don't need real song lyrics
```

**Why this template:** gives every candidate a consistent sonic frame so the only variable the user is judging is the `vocals` string itself. ~20s of throwaway pop-punk with consistent band = clean comparison.

---

## §2 — Open questions

| # | Status | Topic |
|---|---|---|
| M01 | ✅ locked | concept (fictional 90s garage band) |
| M02 | ✅ locked | scope (album, 7-12) |
| M03 | ✅ locked | genre (pop-punk with grunge dirt) |
| M04 | ✅ locked | references (Foo Fighters, Blink-182, VR) |
| M05 | ✅ locked | vocal (solo, raw & gritty) |
| M06 | ✅ locked | language (english) |
| M07 | ✅ locked | runtime (standard) |
| M08a | ✅ locked | band name field (`M08_bandName`) — OPTIONAL, only filled for band releases. Maren Sol pattern: leave blank. Pyro Altar pattern: fill with band name. (Shape B + r2 annotation, locked 2026-08-02) |
| M08b | ✅ locked | artist name field (`M08_artistName`) — REQUIRED, always filled. Solo artist name OR front person name OR same as M08_bandName. Pyro Altar: "Cole Sterling". (Shape B + r2 annotation, locked 2026-08-02) |
| M08c | ✅ locked | credit line field (`M08_creditLine`) — fully optional text. Pyro Altar: empty (no credit line needed). (Shape B, locked 2026-08-02) |
| M08 | ✅ locked | artist identity VALUES — Pyro Altar (band) + Cole Sterling (front singer), no credit line. Schema example `examples[0]` updated. **This is the "has band name" pattern** (inverse of Maren Sol's "no band name" pattern — both are valid r2 cases). |
| M01 | ✅ locked | album concept = **nostalgia / looking back** — late-teen / early-20s years (age 15–22), loose vignettes, central question 'where did the time go?' (tenderness, not bitterness). Built from three M01 sub-questions, all option A: (M01.1) timeframe = late teens / coming-of-age; (M01.2) central question = 'where did the time go?'; (M01.3) narrative scope = loose vignettes. Rethink signal 2026-08-02 ~20:30 UTC: 'i want to change the album topic, this is so stupid. grunge album about phisiotherapy??' — original physiotherapy concept discarded. Pyro Altar / Cole Sterling the consistent entity, but the album is now a look-back at the band-formation years, not a recovery arc. M02 (12 tracks, ~46 min) and M07 (3:00–3:30 per track) preserved as discipline constraints. M04 references (FF In Your Honor, Nirvana In Utero) and M05 vocal (Velvet Revolver / Weiland) still serve this concept. Schema example `examples[0].values` updated 2026-08-02. |
| M02 | ✅ locked | project scope = **album** — standard 12-track format, ~46 min target. Tracks loosely map to 6-month recovery (2 per month). Schema example `examples[0].values` updated 2026-08-02. |
| M03 | ✅ locked | genre direction = **`90s grunge with Foo Fighters melodic hooks`** — raw tone and weight of 90s grunge (Pearl Jam, Nirvana, AIC, STP, Soundgarden) with FF's sing-along chorus structure and melodic hooks. Schema example `examples[0].values` updated 2026-08-02. |
| M04 | ✅ locked | reference artists = **Foo Fighters** (`In Your Honor`, songs: "Razor", "Cold Day in the Sun") for melodic recovery + quiet-to-loud + introspective tone, **+ Nirvana** (`In Utero`, songs: "Pennyroyal Tea", "All Apologies") for rawness + grunge-pain + stripped emotional weight. Two-ref classical setup. User delegated to agent (option 1). Schema example `examples[0].values` updated 2026-08-02. |
| M05 | ✅ locked | vocal approach = **Velvet Revolver-style (Scott Weiland)** — high-register melodic-grit belt with dynamic range. Tenor register (higher than typical rock baritone). Verses intimate/controlled, choruses open up to soaring belt with grit. Dry studio + light plate reverb; doubled lead on choruses. **VR is the bridge between the FF melodic and Nirvana raw refs** (M04). User explicit pick (not delegated). Schema example `examples[0].values` updated 2026-08-02. |
| M06 | ✅ locked | languages = **English only (100%)** — primary `en`, additional `[]`, mix_strategy `monolingual`, per_track_override `false`. Standard for 90s grunge genre; matches all 3 M04 references (FF, Nirvana, VR — all American English-language rock bands). Keeps conceptual focus tight on recovery arc. User explicit pick (option 1). Schema example `examples[0].values` updated 2026-08-02. |
| M07 | ✅ locked | runtime target = **3:00–3:30 per track** (no over-5:00, no long-track allowance, no variable runtime). Album total ~39 min for 12 tracks (12 × ~3:15 avg). Tight, single-friendly, classic grunge shape — most In Utero tracks fit (Pennyroyal Tea 3:31, All Apologies 3:51 slightly over), many FF tracks fit (Cold Day in the Sun 3:45 just over). User explicit pick (tighter than the 3 options offered). **Note:** M02 set ~46 min target; M07's ~39 min album total is below that — accept the variance for runtime discipline. Schema example `examples[0].values` updated 2026-08-02. |
| R09 | ✅ locked | album title = **"Twenty-Two"** — single-age title, the upper bound of the era the album looks back at (15–22). Direct, no metaphor overhead, ages itself honestly. Re-derivation under v2 (nostalgia): the original 'Learning to Walk' (locked 2026-08-02 ~20:13 UTC) was a recovery/P.T. metaphor; under v2 nostalgia the title still works but the meaning shifted enough to warrant a re-pick. 'Twenty-Two' is the cleanest v2 title — FF has used single-age/era single-words as working titles (Dove, One by One, 01020225). Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:40 UTC. |

| R10 | ✅ locked | tracklist = **12 nostalgia vignettes** for 'Twenty-Two'. Each track a standalone memory fragment from age 15–22, no single arc. Order: chronological-feeling but loose (Track 1 = earliest memory, Track 12 = 'now' looking back). 6 hard-rocking tracks + 6 quieter/intimate tracks. Track titles: 1 Razor, 2 Summer of 19, 3 First Show, 4 Her Car, 5 Twenty-Two, 6 Basement, 7 Open Mic, 8 Mama, 9 Freeway, 10 The Dive, 11 Junior, 12 Standing Still. Track 5 'Twenty-Two' = title track at the emotional midpoint. Track 1 'Razor' = same name as FF In Your Honor reference (M04 anchor that opens the album). Closing track 'Standing Still' = a kind of resolution for the look-back. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:42 UTC. |
| R11 | ✅ locked | motif = **recurring 4-chord progression (G–C–D–Em)**, played differently each time it appears. Track 1 clean arpeggio (first guitar), Track 5 full-band power chords (the realization), Track 9 dirty 12-string (the van), Track 11 solo acoustic (addressing younger self), Track 12 full-band with strings (the resolution). The progression is the album's spine — recognizable as the same emotional core, but aged across the tracks. Re-derivation under v2: the v1 recovery concept had a literal walking motif; v2 needed a v2-scale motif. G–C–D–Em is the most basic open-G 4-chord shape (the kind a 15-year-old learns first), collapsing the distance between listener and memory. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:45 UTC. |
| R12 | ✅ locked | production = **hybrid** — full-band for the loud tracks (First Show, Freeway, The Dive, Open Mic, Standing Still), stripped for the quiet tracks (Razor, Her Car, Basement, Mama, Junior). Mirrors the 6-loud / 6-quiet split from M02 re-derivation. Matches FF In Your Honor reference (M04) — that album IS this hybrid shape. Matches M03 (grunge + FF melodic) — grunge lives on the loud tracks, FF melodic lives on the quiet ones. Genre-aware: 'cinematic' would add score-like orchestration the vignettes don't want; 'electronic' would fight the vintage tone; 'full-band' alone ignores the quiet half; 'stripped' alone ignores the loud half. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:46 UTC. |
| R13 | ✅ locked | lyrical source = **co-write** — the user provides the memoir (the 15–22 memories), the agent provides the lyric shape (meter, rhyme, structure, hook placement). NOT 'user-writes' because the user has not asked to write the lyrics themselves. NOT 'agent-writes' because the album is autobiographical in texture (M01) and the agent's job is to translate memories into lyric shape, not invent them. Workflow: at each track, user provides memory beat, agent drafts lyric, user reviews/accepts/edits. CLI: `--lyrics-optimizer` runs on the user-provided lyric text; agent can also pass `--lyrics-file` for the file. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:47 UTC. |
| R14 | ✅ locked | distribution = **just-for-me** (default). The album is a personal nostalgia project, the user is the listener, not a public audience. Upgrading to 'routenote-free' / 'full-dsp' is a future decision after the album exists. Default = the schema's default value. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:48 UTC. |
| R15 | ✅ locked | loudness target = **spotify** (-14 LUFS, true-peak -1 dB). Per the schema this is the streaming default. The album is 'just-for-me' (R14) so technically the loudness doesn't need to match any platform, but locking to -14 LUFS keeps the master stage honest (finalize-album.py reads this value) and means if the user upgrades distribution later, the album already meets the Spotify target. Default = the schema's default value. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:48 UTC. |
| R16 | ✅ locked | sequence pacing = **standard-pause** (3-4s between tracks, per the schema). The vignettes are loose but independent — each track a standalone memory fragment, so a small breath between tracks lets each memory settle. Continuous-flow (bleeds) would suggest the album is a single piece — wrong for vignettes. Short-pause too tight for the emotional weight. Long-pause feels like a compilation. Concept-pause would be excess for an album that's already 12 distinct vignettes. Standard-pause matches the M07 3:00-3:30 runtime envelope. Default = the schema's default value. Agent pick under user 'you decide the rest' directive. Schema example `examples[0].values` updated 2026-08-02 ~20:49 UTC. |
---



## §2.5 — v2.2 hardening (2026-08-03)

**Status:** ✅ v2.2 schema bump complete. The V2-DRAFT additions (R17-R19, E22-E25) and the Twenty-Two retro lessons (M09_sonicDNA + manifest + drift-guard) are now locked in. Future walks against this schema will see all 26 topics (9 mandatory + 10 recommended + 11 extra = 30 fields).

**What's new in v2.2 (vs v2.1):**

- **M09_sonicDNA** (NEW mandatory) — frozen-at-approval snapshot of the
  album's sonic direction. Captures the exact --vocals / --genre / --mood /
  --instruments / --references / --bpm / --key flags. The build skill holds
  against this on every regen via `scripts/check-sonic-drift.py`.
- **R17_explicitRating** (NEW recommended) — clean / explicit-tagged /
  parental-advisory. Affects DSP tagging.
- **R18_coWriter** (NEW recommended) — solo / co-producer / co-lyricist /
  feature-vocalist / full-band-credits. Affects royalty splits.
- **R19_sampleCover** (NEW recommended) — original-only / samples-cleared /
  samples-pending / covers-included. Affects clearance.
- **E22_timeline** (NEW extra) — milestone timeline (different from E21
  single deadline).
- **E23_sessionPersona** (NEW extra) — first-person-singular/plural/
  second/third-person/character-voice/varied. Shown when R13 in
  {agent-writes, co-write}.
- **E24_audience** (NEW extra) — who the album is for.
- **E25_physicalRelease** (NEW extra) — cd / vinyl-lp / vinyl-7in / cassette
  / usb-mini / merch-bundle / limited-edition-print. Shown when R14 in
  {physical-and-dsp, physical-only}.
- **E15-E21** — placeholder stubs filled with proper prompts/descriptions
  (was `{"$ref": "#/$defs/answerText"}` with no content).

**The twenty-two-was-an-exercise retro** lives at
`planning/2026-08-03/twenty-two-as-exercise-retro.md`. Read that doc to
understand WHY these fields exist and what failure modes they prevent.

## §3 — Standing context

User direction: "we never did [the questionnaire walkthrough]" — so we are
running through M01-M08 properly, one question per turn (batched when natural).

User direction: "develop another UI template before we even start" — Phase 0.T
in v3.2 plan, scope pending §3 clarification in v3.2 walkthrough.

User direction (recap-test reflex, 2026-07-29): literal quote first, then context.

---

## §4 — Workflow rules (locked 2026-07-29)

1. **No auto-proceed.** Even when the next question seems obvious, wait for explicit user answer.
2. **One question per turn** by default — batched when they make sense together.
3. **Load skills before starting** (`music-album-planning-questionnaire`), patch them at every use.
4. **Source-of-truth verification:** verify every claim against live tool output (CLI `--help`, official docs llms-full.txt, schema files) before stating it as fact.


---

## §5 — Phase 0.Q completion status (verified 2026-08-05)

Per PLAN-2026-07-28-v3.2 §Phase 0.Q (BEFORE Day 3):

- **Mandatory (M01–M09):** all locked. Schema v2.2 reflects these as `x-tier: Mandatory`.
- **Recommended, build-driving (R09–R16):** all locked. These directly affect the build pipeline (R10 tracklist, R11 motif, R12 production, R15 loudness, R16 sequence). Schema v2.2 reflects.
- **Recommended, non-blocking (R17, R18, R19):** defined in schema v2.2 with sensible defaults (clean / solo / original-only). These affect DSP tagging, royalty splits, and clearance but DO NOT block Day 2 schema init. Walked by `defaults` per Q45.
- **Extra (E22–E25):** defined in schema v2.2 with empty defaults. Affect timeline, persona, audience, and physical release format. DO NOT block.

**Decision:** Phase 0.Q is **DONE** at the v2.2 lock level. R17-R19 + E22-E25 will be walked at the next actual intake session (per R13/R14-conditional visibility in the schema). They are not blocking Day 2 schema init, Day 3 daemon, or Day 6 build runner.

**Status:** ✅ Phase 0.Q complete (v2.2 schema-level lock; full per-topic walk scheduled at next intake).

**Note for next session:** when starting an actual album intake, run through R17/R18/R19 + E22-E25 even if defaults apply. The walkthrough exists to surface decisions, not just to lock defaults.
