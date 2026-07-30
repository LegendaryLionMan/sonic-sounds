# album-studio Questionnaire Walkthrough — 2026-07-29

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
4. **For each candidate:** generate clip, save to `~/OneDrive/Hermes/Agents/planning/album-studio/auditions/`, log the `trace_id`, `actual_duration_ms`, `actual_size_bytes` to the walkthrough doc for traceability.
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
| M08 | ⏳ pending | artist identity (we are here) |

---

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
