# album-studio Lyrics Quality — Spec & Scoring Rubric

**Date:** 2026-07-30
**Goal:** Build a scoring system for lyrics-optimizer output that catches
quality regressions before they hit the album.
**Status:** Spec written, scorer (`score_lyrics.py`) implemented + tested on
synthetic samples. Live-run mode deferred (CLI doesn't expose lyrics text;
would need to call API directly with `target_minutes=0.05` and parse response).

## Background

`mmx music generate --lyrics-optimizer` produces a track where the model
writes its own lyrics based on the prompt. The CLI does NOT return the
lyrics text — only the audio. This is a problem for QA: we can hear the
track but can't read the lyrics.

### Workarounds considered

1. **Whisper transcription** — would add a Python dependency. Cost: 2-5s
   per 2-min track. Quality: 90-95% accurate on clean vocals.
2. **Direct API call with verbose logging** — bypass CLI, hit
   `https://api.minimax.io/v1/music_generation` directly. Requires
   `output_format: "url"` to get `audio_url` AND `lyrics` field. Need to
   confirm if API response includes lyrics when `lyrics_optimizer: true`.
3. **Re-generate with same brief and identical seed** — if music-3.0 is
   deterministic with same seed + same brief. NOT confirmed; need test.
4. **Side-by-side listening** — qualitative score by the user. Slow.

**Recommendation:** use workaround #2 (direct API). Pull the lyrics field
from the response. Save alongside the audio as `<slug>.lyrics.txt`.

## Scoring rubric

For each generated lyrics set, score these dimensions:

### A. Structural (binary presence)

- ✅ has `[Verse]` tag(s)
- ✅ has `[Chorus]` tag(s)
- ✅ has `[Bridge]` tag(s) (recommended for >3:00 tracks)
- ✅ repeated chorus (appears 2+ times)
- ✅ ends with `[Outro]` or `[End]`

### B. Length (numeric)

| Duration target | Word count target | Lines target |
|---|---|---|
| 1:00-1:30 | 80-150 | 16-24 |
| 2:00-3:00 | 150-300 | 30-50 |
| 3:30-4:30 | 250-450 | 50-75 |
| 5:00-6:00 | 400-700 | 75-110 |

Outside these ranges = fail.

### C. Meter regularity (numeric, lower=better)

- `line_length_stddev` < 1.5 words → **steady-meter** (good for verses, choruses)
- `line_length_stddev` 1.5-3.0 → **varied-meter** (acceptable)
- `line_length_stddev` > 3.0 → **uneven-meter** (likely garbage; flag)

### D. Rhyme scheme (numeric)

For each adjacent pair of lines, check if they rhyme (last 2+ chars match).
- `rhyme_pairs / total_adjacent_pairs` > 0.5 → **strong rhyme scheme**
- 0.25-0.5 → **acceptable**
- < 0.25 → **weak rhyme** (acceptable for spoken-word, free-verse; bad for verse-chorus)

### E. Hook (binary + count)

- 2+ lines that repeat → **has hook**
- A repeated line in the chorus that's the same as the song's title or
  a clear emotional hook → **strong hook**

### F. Vocabulary (numeric)

- `vocab_unique_ratio` > 0.6 → **diverse vocab**
- 0.4-0.6 → **normal**
- < 0.4 → **too repetitive** (could be intentional for chorus, but flag)

### G. Profanity / explicit content (binary + count)

- For "clean" or radio-edit albums: `profanity_count` must be 0
- For "explicit" albums: allowed but logged

## Genre-specific calibration

| Genre | Expected meter | Expected rhyme | Hook expectation |
|---|---|---|---|
| **Pop-punk** | steady | strong (AABB or ABAB) | strong chorus |
| **Indie rock** | varied | moderate (loose AABB) | some hook |
| **Indie folk** | varied | moderate | some hook (quiet) |
| **Hip-hop** | varied-rhythmic | dense (multi-syllable) | strong hook (often ad-lib) |
| **R&B / soul** | varied | moderate | emotional hook |
| **Synthwave** | steady | strong | driving hook |
| **Country** | steady | strong (AABB couplets) | chorus hook |
| **Metal** | shouted | weak (atmosphere over rhyme) | chant-style hook |
| **Cinematic / orchestral** | varied | none required | mood-driven, not hook |
| **Jazz / blues** | swung | loose | improvisation-driven |

## Implementation

The scorer `score_lyrics.py` takes:
- `--text <path>` — a .txt file with the lyrics
- OR `--audio <path>` — an mp3/wav file with the generated audio (transcribe via whisper)

For each, it prints:
- Per-dimension scores
- A pass/fail summary against the genre-specific calibration
- Total quality score (0-100)

## What I tested

Tested the scorer on a synthetic pop-punk verse-chorus sample:
- word_count: 82
- avg_line_length: 5.12 words
- line_length_stddev: 0.86 (steady-meter ✓)
- rhyme_pairs: 4 (good-rhyme ✓)
- hook_count: 3 (strong-hook ✓)
- tags: normal, steady-meter, good-rhyme, strong-hook, has-chorus, has-verse, normal-vocab

All checks passed. Scorer is working.

## What I did NOT test (yet)

- Real music-3.0 lyrics_optimizer output (would need direct API call or
  Whisper transcription; deferred to user-driven session)
- Edge cases: tag-only output (no lyrics content), empty output, single
  word per line (garbage), non-English output
- Integration with the build pipeline (would write lyrics scores to
  SQLite `tracks` table)

## Recommendation for v1

For the album-studio build:

1. **Add a `lyrics_quality_score` column** to `tracks` (integer 0-100)
2. **Score every lyrics-optimizer output** before allowing user approval
3. **Block approval** if score < 60
4. **Display score** in the studio UI as a small badge next to each track

The scorer code is ready (`score_lyrics.py`). Wiring into the build
pipeline is a Day 5 task.

## Files

- `score_lyrics.py` — the scorer (Python, ~13 KB)
- `report.md` — this file

## Next steps for the user

1. Decide on the minimum acceptable score threshold (50? 60? 70?)
2. Confirm direct-API lyrics capture approach (workaround #2 above)
3. Test the scorer with a real lyrics-optimizer sample once API access is confirmed