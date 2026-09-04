# sonic-studio Tools Memo — Validated Capabilities
**Date:** 2026-07-30
**Purpose:** Document which tools are confirmed-available on this host for the sonic-studio pipeline, and the canonical recipes for each.

---

## ffmpeg (already installed system-wide)

**Version confirmed:** Lavf62.12.102, Lavc62.28.102 (from ffmpeg stderr)

### Validated filters

#### `loudnorm` (two-pass) — industry-standard EBU R128 normalization

**Recipe:**
```bash
# Pass 1: measure
ffmpeg -hide_banner -i input.mp3 -af "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=summary" -f null - 2>&1 | tee measure.txt

# Pass 2: apply (with measured values from pass 1)
ffmpeg -hide_banner -i input.mp3 \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11:measured_I=-14.1:measured_TP=0.1:measured_LRA=6.5:measured_thresh=-24.2:offset=-0.7:linear=true" \
  -c:a libmp3lame -b:a 256k output.mp3
```

**Verified end-to-end:** C01 mastered to -14.0 LUFS, -1.0 dBTP, 4.4 LU LRA. **43x realtime on this host.**

**Use case in sonic-studio:** `finalize-album.py` runs loudnorm two-pass per track, with target configurable by `R15 mastering_target` (Spotify -14, Apple -16, YouTube -14, broadcast -23, etc.).

#### `ebur128` (one-pass) — measurement only

**Recipe:**
```bash
ffmpeg -hide_banner -i input.mp3 -af "ebur128=peak=true" -f null - 2>&1 | tail -25
```

Output: integrated loudness (LUFS), loudness range (LU), true peak (dBFS), LRA low/high.

**Speed:** 0.3s per 2-min track on this host.

**Use case:** real-time validation in the studio's "audio quality" panel + post-master verification.

#### `aspectralstats` — spectral centroid + flatness

**Recipe:**
```bash
ffmpeg -hide_banner -i input.mp3 \
  -af "aspectralstats=measure=mean+centroid+flatness,ametadata=print:key=lavfi.aspectralstats.1.centroid" \
  -f null - 2>&1
```

Output: spectral centroid (Hz), spectral flatness (0-1), spectral mean (power).

**Use case:** verify that "grunge" briefs actually produce dirtier sound (centroid > 2000 Hz, flatness > 0.10).

#### `astats` — RMS / peak / crest / flat factor

**Recipe:**
```bash
ffmpeg -hide_banner -i input.mp3 -af "astats=metadata=1:reset=0" -f null - 2>&1
```

Output: RMS level (dB), Peak level (dB), Flat factor (dB), Crest factor (linear), Dynamic range (dB), Entropy, Zero crossings.

**Use case:** quality dashboard per track.

#### `acrossfade` — gapless track stitching

**Recipe (verified):**
```bash
ffmpeg -i track1.mp3 -i track2.mp3 \
  -filter_complex "[0:a]atrim=0:30,asetpts=PTS-STARTPTS[first]; \
                   [1:a]atrim=0:30,asetpts=PTS-STARTPTS[second]; \
                   [first][second]acrossfade=d=2:c1=tri:c2=tri[out]" \
  -map "[out]" -c:a libmp3lame -b:a 192k output.mp3
```

Verified: 30s + 30s - 2s overlap = 58s output. Crossfades work.

**Use case:** L5 mastering can optionally apply gapless crossfade between adjacent tracks (for `R16 = continuous-flow` mode).

#### `showspectrumpic` — spectrogram PNG generation

**Recipe:**
```bash
ffmpeg -i input.mp3 -lavfi showspectrumpic=s=1280x480 -update 1 -frames:v 1 spectrum.png
```

Verified: produces 1280x480 PNG. C01 spectrogram shows full frequency range (0-20kHz), cymbal hash, vocal harmonics, distinct verse/chorus structure.

**Use case:** album art embedded in CONCEPT-BRIEF.md; visual track comparison.

---

## mutagen (Python ID3v2.4) — installed 2026-07-30

**Install:**
```bash
/c/Users/lion_/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install mutagen
# Installed: mutagen-1.48.1
```

### Canonical recipe for sonic-studio ID3 embedding

```python
from mutagen.id3 import ID3, ID3NoHeaderError, TPE1, TALB, TIT2, TRCK, TCON, TDRC, USLT, APIC

audio = ID3(file_path)  # raises ID3NoHeaderError if no ID3 tag
audio.add(TPE1(encoding=3, text="Artist Name"))
audio.add(TALB(encoding=3, text="Album Title"))
audio.add(TIT2(encoding=3, text="Track Title"))
audio.add(TRCK(encoding=3, text="01/10"))
audio.add(TCON(encoding=3, text="Indie Rock"))
audio.add(TDRC(encoding=3, text="2026"))  # ID3v2.4
audio.add(USLT(encoding=3, lang="eng", desc="", text="[Verse 1]\n..."))  # unsynced lyrics
# For cover art:
# audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="cover", data=open("cover.jpg","rb").read()))
audio.save()
```

**Verified:** All 7 fields write + read back. Persists through ffmpeg re-encoding. Encoding=3 = UTF-8 (correct for non-ASCII titles).

**Use case in sonic-studio:** `finalize-album.py` embeds artist, album, track#, title, year, genre, lyrics (USLT), cover (APIC) into every mastered mp3.

---

## AIGC watermark

Music-3.0 already embeds an AIGC watermark (TXXX:aigc frame) by default. Verified:
```
TXXX:aigc: {"aigc": {"Label": "1", "ContentProducer": "HUABABSpeech7E01", "ProduceID": "06b9a7b2f7dd073dfb7bc23f6be48d94"}}
```

This is required by China AIGC regulations (the model is MiniMax). Cannot be removed via standard tools. The `--aigc-watermark=false` flag on mmx doesn't exist (it's always on).

**Implication for distribution:** all tracks carry this watermark. For DSPs that filter AI-generated content, this is an honest signal. For casual listeners, it's invisible. Don't try to strip it.

---

## Whisper (for lyrics transcription)

**Status:** Not yet installed on this host. **Defer to user session** — installing whisper locally requires ~3 GB model download.

**Use case:** lyrics-quality scorer reads generated audio → transcribes lyrics → scores. Currently the scorer takes text input only; integrating whisper would let it score `lyrics_optimizer=true` outputs automatically.

**Recommendation:** install when the audition pipeline (M08) needs it. `pip install openai-whisper` + download `medium` or `large-v3` model.

---

## Pillow / PIL (image processing)

**Status:** Not yet tested on this host. Available via pip (`pip install Pillow`).

**Use case:** cover art variants (square crop for Instagram, 1400x1400 for Bandcamp, 1280x1440 header), aspect-ratio resizing, format conversion (PNG ↔ JPG ↔ WebP).

**Recommendation:** install when L6 (Cover art) starts generating candidates.

---

## scipy / numpy / matplotlib

**Status:** Already in many Python installs. Verify with `python -c "import scipy; print(scipy.__version__)"`.

**Use case:** audio analysis if we move beyond ffmpeg filters. librosa depends on these.

---

## Tool decision matrix

| Tool | Installed? | Tested? | Use case | Day | Install effort |
|---|---|---|---|---|---|
| ffmpeg | yes | yes | audio mastering, gapless, spectrograms | Day 5 | (system) |
| mutagen | yes (venv) | yes | ID3v2.4 metadata | Day 5 | 5s |
| Pillow | no | no | cover art variants | Day 5 | 10s |
| whisper | no | no | lyrics transcription | Day 5 (when needed) | 3-5 min + 3GB |
| scipy/numpy | TBD | no | spectral analysis fallback | optional | (often present) |
| librosa | no | no | BPM/key detection from audio | Day 4 | 30s + deps |
| spotipy | no | no | Spotify metadata read | Day 10+ | 10s + auth |

## What I did NOT install (and why)

- **librosa** — 50MB+ dependency tree. ffmpeg's `aspectralstats` covers the spectral analysis we need. Defer to Day 4 if user wants BPM/key detection.
- **whisper** — 3GB model. Defer to actual lyrics-quality automation need.
- **DDEX libraries** — no production-quality Python DDEX library exists. Will likely build minimal DDEX ERN 4.3 writer as a Day 12 task.
- **ISRC/UPC generators** — these need to come from a registered ISRC manager (Routenote, DistroKid) not generated locally. Local generation is meaningless.

## Files

- `audio-quality-2026-07-30/test_crossfade.py` — verified crossfade recipe
- `audio-quality-2026-07-30/test_mutagen.py` — verified ID3 embedding recipe
- `audio-quality-2026-07-30/C01-mastered.mp3` — verified mastered output
- `music-test-2026-07-29/test-crossfade.mp3` — verified gapless test output