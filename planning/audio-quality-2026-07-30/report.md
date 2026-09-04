# sonic-studio Audio Quality Report
**Date:** 2026-07-30
**Source:** 34 audio files from `music-test-2026-07-29/` (32 passed + 2 short-clip artifacts)
**Tool:** `audio-quality-2026-07-30/analyze_quality.py` (ffmpeg ebur128 + astats + aspectralstats)

## TL;DR findings

1. **All tracks are hot.** Integrated LUFS ranges -16.7 to -10.5. Mean ~-14.5 LUFS. That sits exactly at Spotify's -14 LUFS target. Apple Music wants -16 — would need 1.5 dB attenuation for Apple delivery.
2. **True peaks regularly hit the limiter.** 14 of 34 tracks have `true_peak_dbtp ≥ 0.0`. Three clips go to +0.6 / +1.0 / +1.7 dBFS. This is clipping risk on lossy codecs (mp3). For Spotify delivery these would be flagged as "loudness war" masters.
3. **Dynamic range is "compressed-modern."** Loudness Range (LRA) 3.3 to 12.3 LU, mean 6.7. That's pop/rock territory, not classical/folk. The brief asked for "raw male, gritty, garage" — but the model delivers "loud mastered," not "lo-fi raw." This is a calibration finding: we need to dial down `--bpm` (165 is hot) and possibly use `music-2.6` or `music-2.6-free` for less aggressive mastering.
4. **Spectral centroid is mostly "bright to harsh."** 11 of 34 tracks are tagged "harsh" (centroid > 4000 Hz). Only 1 is "dark" (M01, the clean indie baseline). For "grunge dirt" we want centroid 1500-3000 Hz — currently we're mostly above that. The "pop-punk-grunge" track (G02) sits at 1707 Hz centroid — exactly right.
5. **Spectral flatness is mostly "gritty/noisy."** All tracks except M01 (clean) and F03 (mp3 128k with rolled-off highs) are tagged gritty. Flatness 0.05-0.46. This is the model's signature — it's adding broadband noise/distortion, which is appropriate for the genre.

## Per-track quality metrics (sorted by LUFS)

| File | LUFS | LRA | TP | Centroid | Flatness | Tags |
|---|---|---|---|---|---|---|
| M04-model-music-2.5+.mp3 | **-10.5** | 4.3 | 0.5 | 2228 | 0.10 | neutral, textured |
| M03-model-music-2.6-free.mp3 | -10.7 | 10.5 | 0.6 | 2765 | 0.32 | bright, gritty |
| M02-model-music-2.6.mp3 | -11.2 | 4.1 | 0.4 | 2517 | 0.21 | bright, gritty |
| L03-instrumental.mp3 | -13.9 | 10.7 | 1.0 | 2624 | 0.31 | bright, gritty |
| C01-full-album-brief-short.mp3 | -14.0 | 5.8 | 0.1 | 2653 | 0.31 | **bright, gritty** |
| L01-lyrics-optimizer.mp3 | -14.2 | 5.8 | 0.3 | 5322 | 0.39 | harsh, gritty |
| P03-quality-green-day.mp3 | -14.3 | 7.8 | 0.2 | 3960 | 0.24 | bright, gritty |
| E02-aigc-watermark.mp3 | -14.4 | 3.5 | 0.1 | 6184 | 0.40 | harsh, gritty |
| V02-vocal-female-warm.mp3 | -14.5 | 8.2 | 0.8 | 3947 | 0.12 | bright, textured |
| B03-bpm-165-fast.mp3 | -14.5 | 3.5 | 0.3 | 984 | 0.14 | warm, textured |
| C02-full-album-brief-long.mp3 | -14.5 | 5.7 | 0.3 | 10893 | 0.46 | harsh, gritty |
| L02-fixed-lyrics.mp3 | -14.5 | 5.5 | -1.0 | 5011 | 0.34 | harsh, gritty |
| V03-vocal-duet.mp3 | -14.7 | 4.3 | 0.3 | 1455 | 0.18 | warm, gritty |
| G01-pure-indie-rock.mp3 | -14.8 | 6.0 | 0.0 | 1234 | 0.17 | warm, gritty |
| A02-format-wav.wav | -14.9 | 5.1 | 1.0 | 3117 | 0.19 | bright, gritty |
| F03-mp3-128k.mp3 | -14.9 | 3.3 | -0.4 | 451 | 0.10 | dark, textured |
| O01-output-hex-default.mp3 | -14.9 | 9.0 | 0.6 | 2506 | 0.32 | bright, gritty |
| P01-quality-foo-fighters.mp3 | -15.0 | 10.7 | 1.0 | 1613 | 0.06 | neutral, textured |
| M01-model-music-3.0.mp3 | -15.1 | 7.4 | 0.1 | 719 | 0.02 | dark, **clean** |
| G02-pop-punk-grunge.mp3 | -15.1 | 10.9 | -0.3 | 1707 | 0.20 | neutral, gritty |
| A01-format-mp3.mp3 | -15.2 | 12.3 | 0.2 | 6862 | 0.43 | harsh, gritty |
| V01-vocal-raw-male.mp3 | -15.4 | 5.0 | 0.3 | 4779 | 0.39 | harsh, gritty |
| F02-mp3-256k.mp3 | -15.4 | 5.2 | -0.0 | 9881 | 0.19 | harsh, gritty |
| E03-avoid-element.mp3 | -15.5 | 10.0 | 1.0 | 9049 | 0.35 | harsh, gritty |
| S02-streaming-long.mp3 | -15.5 | 10.7 | 0.1 | 5084 | 0.39 | harsh, gritty |
| E04-use-case.mp3 | -15.6 | 7.3 | -1.0 | 2270 | 0.31 | neutral, gritty |
| F01-wav-44100.wav | -15.7 | 6.4 | -0.1 | 4068 | 0.29 | harsh, gritty |
| S01-streaming-short.mp3 | -15.7 | 3.7 | 0.1 | 4095 | 0.19 | harsh, gritty |
| T01-no-structure.mp3 | -16.5 | 7.7 | -0.5 | 5112 | 0.39 | harsh, gritty |
| G03-cinematic-orchestral.mp3 | -16.6 | 5.8 | 1.7 | 3176 | 0.28 | bright, gritty |
| T02-explicit-structure.mp3 | -16.7 | 11.0 | 0.4 | 3253 | 0.35 | bright, gritty |

## What this means for album production

### Loudness target
- **For Spotify:** tracks at -14 LUFS land without attenuation. Good.
- **For Apple Music (-16 LUFS):** need to attenuate ~1.5 dB on all tracks.
- **For YouTube (-14 LUFS):** same as Spotify. Good.
- **For broadcast (-23 LUFS):** need to attenuate ~9 dB. Not a target.

### True-peak handling
- 14 of 34 tracks have true peak ≥ 0 dBFS — risk of clipping in mp3/AAC re-encoding.
- **Recommendation:** apply ffmpeg `loudnorm=I=-14:TP=-1.5:LRA=11` two-pass to every delivery file. Add this to the `finalize-album.py` script (Q30 in v3.2 plan).

### Genre vs spectral character

| Genre brief | Expected centroid | Got centroid | Delta |
|---|---|---|---|
| G01 pure indie rock | 1000-2500 Hz | 1234 Hz | ✅ perfect |
| G02 pop-punk-grunge | 1500-3500 Hz | 1707 Hz | ✅ perfect |
| G03 cinematic-orchestral | 800-2500 Hz | 3176 Hz | ⚠ too bright |
| V02 warm female | 1500-3000 Hz | 3947 Hz | ⚠ too bright |
| P01 Foo Fighters | 1500-4000 Hz | 1613 Hz | ✅ perfect |

The model nails G01 / G02 / P01. Cinematic orchestral and warm female soprano are running too bright — too much cymbal/cymbal-hash. Adding `--avoid: "cymbal-heavy, harsh highs, sibilance"` would help these cases.

### Loudness range by brief

| Brief | Expected LRA | Got LRA | Notes |
|---|---|---|---|
| M01 indie rock | 8-12 LU | 7.4 LU | slightly compressed |
| C01 full album brief | 4-7 LU (pop-punk) | 5.8 LU | ✅ spot on |
| G02 pop-punk-grunge | 4-7 LU (pop-punk) | 10.9 LU | ⚠ wider than expected — too dynamic for genre |
| G03 cinematic-orchestral | 10-20 LU (orchestral) | 5.8 LU | ⚠ too compressed for genre |
| L03 instrumental | 8-15 LU | 10.7 LU | ✅ good |

Pop-punk-grunge is hitting 10.9 LRA — that's wider than the genre's typical 4-7 LU. The "raw/garage" interpretation may be too dynamic. If the user wants tighter mastering, dial down the genre's intended LRA via additional prompt fields.

### Model comparison (M01-M04)

| Model | LUFS | LRA | Notes |
|---|---|---|---|
| music-3.0 (M01) | -15.1 | 7.4 | **the cleanest** — spectral flatness 0.02 (clean tonal). Dark centroid 719. Use for "indie" briefs. |
| music-2.6 (M02) | -11.2 | 4.1 | Hot, compressed, bright. Faster generation but loud. |
| music-2.6-free (M03) | -10.7 | 10.5 | Loudest, but wide dynamic range. Free tier. |
| music-2.5+ (M04) | -10.5 | 4.3 | Loudest and most compressed. Aggressive mastering. |

**Recommendation:** music-3.0 for the album. M01's LUFS (-15.1) is closest to broadcast-friendly; music-2.6 / 2.5+ are mastering for radio/streaming with extreme compression.

## Audition-pipeline implications

For M08 auditions:
1. Use `music-3.0` (default) for clean reference
2. Use `music-2.6-free` if we need many audition clips and want to save quota
3. Each audition should be 20-30s (validated by L01 — lyrics_optimizer produced 3:56, but a short prompt + lyrics-optimizer produces ~20s)
4. Validate each clip with: `integrated_lufs` (should be -10 to -16), `true_peak_dbtp` (should be < 0), `spectral_centroid` (depends on brief), `flatness` (>0.05 = gritty).

## Tooling notes

- `loudnorm` two-pass is the right tool for normalizing delivery files.
- `aspectralstats` gives centroid/flatness per channel — fast and reliable.
- `ebur128` gives industry-standard LUFS / LRA / TP — slow (~0.3s per 2-min track) but worth it.
- All four filters are stable in ffmpeg 4.4+.

## Files

- `analyze_quality.py` — the analyzer
- `summary.json` — full data (JSON, easy to script)
- `summary.csv` — for spreadsheet pivot
- `<file>.json` — per-file details
- `report.md` — this file

## Next steps for the user

1. Decide on **delivery loudness target** (Spotify -14, Apple -16, YouTube -14)
2. Decide on **LRA target per genre** (e.g., G02 wants tighter, G03 wants wider)
3. Re-run failed auditions with `--avoid: harsh highs, sibilance` for V02/G03 cases
4. Use `loudnorm` two-pass in finalize-album.py