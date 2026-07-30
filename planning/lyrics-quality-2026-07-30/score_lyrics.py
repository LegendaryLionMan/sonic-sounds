#!/usr/bin/env python3
"""
Lyrics quality scorer for music-3.0 lyrics_optimizer output.

Reads a folder of mp3 files with lyrics-optimizer-generated lyrics (we
can't read the actual lyrics from the mp3 since music-3.0 doesn't embed
lyrics in metadata), so instead we re-generate 20+ lyrics with varying
briefs and score the OUTPUT TEXT against genre-appropriate heuristics.

For each brief, the model is asked to write lyrics via lyrics_optimizer=true.
We save the lyrics text and score:

- word_count: total words
- lines: total lines (excluding tag lines)
- avg_line_length: average words per line
- line_length_variance: std dev of line lengths (low = steady meter)
- rhyme_pairs: count of pairs of consecutive lines ending in same sound
- hook_lines: lines that repeat (choruses etc)
- syllable_estimate: rough syllable count
- structure_tags: presence of [Verse]/[Chorus]/[Bridge]/[Outro] tags
- profanity: simple bad-words check (basic)
- unique_words_ratio: vocabulary diversity

Output: per-brief JSON + summary.

Usage:
  python score_lyrics.py <briefs-file.yaml> --output-dir <dir>

where briefs-file.yaml is:
  - id: L01
    label: pop-punk-grunge-energetic
    prompt: pop-punk with grunge dirt, garage band, raw and energetic
    genre: pop-punk
    mood: raw, energetic, rebellious
    vocals: raw male baritone with garage grit
    lyrics_optimizer: true
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Use the SAME newline-escape fix that worked for the music matrix.
def escape_for_subprocess(s: str) -> str:
    """Replace real newlines with literal \\n so Windows subprocess
    doesn't break the command line."""
    return s.replace("\n", "\\n")


def generate_lyrics_only(
    brief: dict,
    output_dir: Path,
    mmx_path: str,
) -> dict:
    """Generate a track with lyrics_optimizer and save the audio.
    The lyrics are returned in stdout metadata — we extract from
    the .meta files ffmpeg can extract.

    Since music-3.0 doesn't expose lyrics in metadata, we instead
    save the lyrics_optimizer-generated lyrics to a sidecar .lyrics.txt
    by ALSO calling mmx with --lyrics-optimizer and reading stdout.

    Actually: music-3.0 returns the audio (no lyrics text in stdout).
    So we have to generate twice if we want the lyrics — once with
    lyrics-optimizer=true to write a track, and once to capture the
    lyrics output via a different mechanism.

    Cleanest approach: extract lyrics from the audio by transcribing
    using whisper. But that adds a dependency.

    For this scorer, we'll do something simpler: just measure the
    AUDIO quality heuristics that imply the lyrics worked — track
    duration, spectral centroid for vocal range, etc. We'll do an
    INDIRECT quality check.

    For the direct text quality, we can use mmx's lyrics_optimizer
    in dry-run mode if it exists, or test with a known set of
    LLM-generated lyrics for the briefs.
    """
    pass


def score_lyrics_text(lyrics: str) -> dict:
    """Score a lyrics string on multiple dimensions."""
    lines_raw = [l for l in lyrics.split("\n") if l.strip()]
    # Filter out structure tags
    structure_tags = [l for l in lines_raw if re.match(r"^\s*\[[\w\s]+\]\s*$", l)]
    content_lines = [l for l in lines_raw if not re.match(r"^\s*\[[\w\s]+\]\s*$", l)]

    words = []
    for line in content_lines:
        words.extend(line.split())

    word_count = len(words)
    line_lengths = [len(line.split()) for line in content_lines]
    avg_line_length = sum(line_lengths) / max(1, len(line_lengths))
    if len(line_lengths) > 1:
        mean = sum(line_lengths) / len(line_lengths)
        variance = sum((x - mean) ** 2 for x in line_lengths) / len(line_lengths)
        stddev = variance ** 0.5
    else:
        stddev = 0.0

    # Rhyme detection — extract last word of each line, check for similar
    # endings. Use a simple heuristic: same last 2 chars (catches -ight,
    # -ain, -ound etc.) OR same phoneme class (vowel-C).
    last_words = [line.split()[-1].lower().strip(".,!?;:'\"") if line.split() else "" for line in content_lines]
    rhyme_pairs = 0
    for i in range(len(last_words) - 1):
        if last_words[i] and last_words[i + 1]:
            # Match if last 2+ chars match (rough)
            if len(last_words[i]) >= 2 and last_words[i][-2:] == last_words[i + 1][-2:]:
                rhyme_pairs += 1
            # Or vowel-consonant ending
            elif len(last_words[i]) >= 3 and len(last_words[i + 1]) >= 3:
                if (last_words[i][-3:-1] == last_words[i + 1][-3:-1] or
                    last_words[i][-3:] == last_words[i + 1][-3:]):
                    rhyme_pairs += 1

    # Hook detection: lines that appear more than once
    from collections import Counter
    line_counter = Counter(line.strip().lower() for line in content_lines)
    repeated_lines = [line for line, count in line_counter.items() if count >= 2]
    hook_count = len(repeated_lines)

    # Syllable estimate: rough English heuristic (1 per vowel cluster + 1 for
    # words ending in 'e' silent, etc.). Just use a simple heuristic: count
    # vowel groups per word.
    def syll_estimate(word):
        word = word.lower().strip(".,!?;:'\"()[]")
        if not word:
            return 0
        # Count vowel groups (a, e, i, o, u, y)
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for ch in word:
            is_vowel = ch in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        # Subtract 1 for silent 'e' at end
        if word.endswith("e") and count > 1:
            count -= 1
        return max(1, count)

    total_syllables = sum(syll_estimate(w) for w in words)

    # Vocabulary diversity
    unique_words = set(w.lower().strip(".,!?;:'\"()[]") for w in words)
    unique_ratio = len(unique_words) / max(1, word_count)

    # Profanity (basic list — extend as needed)
    bad_words = {"fuck", "shit", "bitch", "asshole", "dick", "cunt", "bastard"}
    profanity_count = sum(1 for w in words if w.lower().strip(".,!?;:'\"") in bad_words)

    return {
        "word_count": word_count,
        "lines_total": len(lines_raw),
        "lines_content": len(content_lines),
        "structure_tags": structure_tags,
        "avg_line_length_words": round(avg_line_length, 2),
        "line_length_stddev": round(stddev, 2),
        "rhyme_pairs": rhyme_pairs,
        "hook_count": hook_count,
        "total_syllables_estimate": total_syllables,
        "vocab_unique_ratio": round(unique_ratio, 3),
        "profanity_count": profanity_count,
    }


def classify_lyrics(score: dict) -> list[str]:
    """Tag with qualitative descriptors."""
    tags = []
    wc = score["word_count"]
    avg = score["avg_line_length_words"]
    stddev = score["line_length_stddev"]
    rhyme = score["rhyme_pairs"]
    hooks = score["hook_count"]

    # Length
    if wc < 30:
        tags.append("very-short")
    elif wc < 80:
        tags.append("short")
    elif wc < 200:
        tags.append("normal")
    else:
        tags.append("long")

    # Line meter regularity
    if stddev < 1.5:
        tags.append("steady-meter")
    elif stddev < 3:
        tags.append("varied-meter")
    else:
        tags.append("uneven-meter")

    # Rhyming
    if rhyme == 0:
        tags.append("no-rhyme")
    elif rhyme <= 2:
        tags.append("sparse-rhyme")
    elif rhyme <= 6:
        tags.append("good-rhyme")
    else:
        tags.append("dense-rhyme")

    # Hooks
    if hooks == 0:
        tags.append("no-hook")
    elif hooks <= 2:
        tags.append("some-hook")
    else:
        tags.append("strong-hook")

    # Structure
    tags_struct = [t for t in score["structure_tags"] if t]
    if any("Chorus" in s for s in tags_struct):
        tags.append("has-chorus")
    if any("Verse" in s for s in tags_struct):
        tags.append("has-verse")
    if any("Bridge" in s for s in tags_struct):
        tags.append("has-bridge")

    # Vocabulary
    if score["vocab_unique_ratio"] > 0.75:
        tags.append("diverse-vocab")
    elif score["vocab_unique_ratio"] > 0.5:
        tags.append("normal-vocab")
    else:
        tags.append("repetitive")

    # Profanity
    if score["profanity_count"] > 0:
        tags.append("explicit")

    return tags


# Pre-written test briefs with sample lyrics in various styles.
# Since we can't directly extract the model's lyrics_optimizer output
# from the audio (no metadata embed), we test the score logic on a
# curated set of representative lyrics and also on the OUTPUTS of
# mmx music generate --lyrics-optimizer when called with --output-format
# that exposes the text.

# Actually we CAN get the lyrics from CLI: --lyrics-optimizer returns
# a "lyrics" field in the JSON output if the CLI is verbose. Let me
# re-test:
TEST_BRIEFS = [
    {
        "id": "L01",
        "label": "pop-punk-grunge-energetic",
        "prompt": "pop-punk with grunge dirt, garage band, raw and energetic",
        "genre": "pop-punk",
        "mood": "raw, energetic, rebellious",
        "vocals": "raw male baritone with garage grit",
        "lyrics": None,  # use lyrics-optimizer
    },
    {
        "id": "L02",
        "label": "indie-folk-melancholic",
        "prompt": "indie folk, melancholic, fingerpicked acoustic, autumn evening",
        "genre": "indie-folk",
        "mood": "melancholic, introspective",
        "vocals": "warm female alto, breathy",
        "lyrics": None,
    },
    {
        "id": "L03",
        "label": "electronic-synth-wave",
        "prompt": "synthwave, retro 80s, neon city, driving beat, arpeggios",
        "genre": "electronic",
        "mood": "nostalgic, hopeful, mysterious",
        "vocals": "androgynous synth-pop vocal",
        "lyrics": None,
    },
    {
        "id": "L04",
        "label": "jazz-blues-noir",
        "prompt": "jazz blues noir, smoky bar, upright bass, muted trumpet",
        "genre": "jazz",
        "mood": "sultry, late-night",
        "vocals": "smoky female alto, world-weary",
        "lyrics": None,
    },
    {
        "id": "L05",
        "label": "hip-hop-east-coast",
        "prompt": "east coast hip-hop, boom bap, 90s, vinyl crackle",
        "genre": "hip-hop",
        "mood": "confident, streetwise",
        "vocals": "confident male baritone, rapid flow",
        "lyrics": None,
    },
    {
        "id": "L06",
        "label": "rnb-slow-jam",
        "prompt": "slow jam R&B, late night, smooth, Rhodes piano",
        "genre": "rnb",
        "mood": "intimate, sensual",
        "vocals": "smooth male tenor, falsetto",
        "lyrics": None,
    },
    {
        "id": "L07",
        "label": "metal-thrash",
        "prompt": "thrash metal, fast, aggressive, distorted guitars",
        "genre": "metal",
        "mood": "angry, relentless",
        "vocals": "shouted male tenor, gritty",
        "lyrics": None,
    },
    {
        "id": "L08",
        "label": "country-ballad",
        "prompt": "country ballad, storytelling, acoustic guitar, fiddle",
        "genre": "country",
        "mood": "wistful, longing",
        "vocals": "warm male baritone, southern drawl",
        "lyrics": None,
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, default=Path("."))
    ap.add_argument("--dry-run", action="store_true",
                    help="Score the scorer without running mmx")
    args = ap.parse_args()

    args.output_dir.mkdir(exist_ok=True, parents=True)

    if args.dry_run:
        # Just verify the scorer works on a known sample
        sample = """[Verse 1]
Walking down the empty street
Rain is falling on my feet
Searching for a sign of hope
Trying just to learn to cope

[Chorus]
Hold on, hold on
The night will soon be gone
Hold on, hold on
Until the break of dawn

[Verse 2]
City lights are starting to fade
Memories of choices made
Every shadow holds a voice
Telling me I have a choice

[Chorus]
Hold on, hold on
The night will soon be gone
Hold on, hold on
Until the break of dawn"""

        score = score_lyrics_text(sample)
        score["tags"] = classify_lyrics(score)
        print(json.dumps(score, indent=2))
        return

    print("Real-run mode not implemented yet — use --dry-run to test scorer")
    sys.exit(1)


if __name__ == "__main__":
    main()