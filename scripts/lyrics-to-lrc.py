"""
lyrics-to-lrc.py — Convert sonic-studio lyrics/*.md files into LRC synced-lyrics files.

Usage:
    python scripts/lyrics-to-lrc.py --album-dir <path> [--use-mp3-duration]

Reads:
  <album-dir>/lyrics/*.md    (Markdown with [Section] tags + **Length:** header)
  <album-dir>/music/*.mp3    (optional, for true track duration via ffprobe)

Writes:
  <album-dir>/lyrics-lrc/*.lrc  (LRC format with [MM:SS.xx] timestamps)

The script reads each MP3's actual duration via ffprobe, so timestamps are
synced to the real track. Falls back to **Length:** field if ffprobe is missing.

Section start times are computed from a canonical template:
  Intro (6%) → Verse 1 (13%) → Pre-Chorus (5%) → Chorus (13%) →
  Verse 2 (13%) → Pre-Chorus (5%) → Chorus (13%) → Bridge (12%) →
  Chorus (13%) → Outro (7%)

Lines within each section are spaced evenly.

Format reference: LRC v1.0 standard (timestamps MM:SS.xx)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


# Canonical section template: (section_name, weight)
SECTION_TEMPLATE = [
    ("Intro", 0.06),
    ("Verse 1", 0.13),
    ("Pre-Chorus", 0.05),
    ("Chorus", 0.13),
    ("Verse 2", 0.13),
    ("Pre-Chorus", 0.05),
    ("Chorus", 0.13),
    ("Bridge", 0.12),
    ("Chorus", 0.13),
    ("Outro", 0.07),
]


def ffprobe_duration(mp3_path):
    """Get duration in seconds from an MP3 via ffprobe. Returns None on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def parse_lyrics_md(path):
    """Parse sonic-studio lyrics/*.md.

    Returns (meta_dict, sections_list) where sections_list is
    [(section_name, [line_text, ...]), ...].
    """
    text = path.read_text(encoding="utf-8")
    meta = {}
    sections = []
    current_section = None
    current_lines = []

    for line in text.splitlines():
        m = re.match(r"^\*\*(\w+):\*\*\s*(.+)$", line.strip())
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        if line.startswith("Production:"):
            meta["production"] = line.replace("Production:", "").strip()
            continue
        if line.startswith("# "):
            continue
        sm = re.match(r"^\[(\w[\w\s]*?)\]$", line.strip())
        if sm:
            if current_section:
                sections.append((current_section, current_lines))
            current_section = sm.group(1).strip()
            current_lines = []
        elif current_section and line.strip():
            current_lines.append(line.strip())

    if current_section:
        sections.append((current_section, current_lines))

    return meta, sections


def parse_length_to_seconds(s):
    """Parse 'M:SS' or 'MM:SS' or 'M:SS.ss' to seconds."""
    m = re.match(r"^(\d+):(\d+(?:\.\d+)?)$", s.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + float(m.group(2))


def fmt_time(t):
    """Format seconds to [MM:SS.xx]."""
    m = int(t // 60)
    s = t - m * 60
    return f"[{m:02d}:{s:05.2f}]"


def section_starts(duration_s):
    """Compute cumulative start times for each section in the template."""
    starts = {}
    cumulative = 0.0
    for name, weight in SECTION_TEMPLATE:
        starts[name] = cumulative
        cumulative += weight * duration_s
    return starts


def generate_lrc(track_slug, lyrics_path, out_path, artist, album, mp3_path=None):
    """Generate one LRC file. Returns (line_count, duration_s)."""
    meta, sections = parse_lyrics_md(lyrics_path)

    # Get duration: prefer MP3 real duration, then **Length:** field, then 3:30 default
    duration_s = None
    if mp3_path and mp3_path.exists():
        duration_s = ffprobe_duration(mp3_path)
    if duration_s is None and "length" in meta:
        duration_s = parse_length_to_seconds(meta["length"])
    if duration_s is None:
        duration_s = 3 * 60 + 30

    track_num, track_title = track_slug.split("-", 1)
    if track_slug == "05-twenty-two":
        title = "Twenty-Two"
    else:
        title = track_title.replace("-", " ").title()

    length_str = f"{int(duration_s // 60):02d}:{duration_s % 60:05.2f}"

    lines = []
    lines.append(f"[ar:{artist}]")
    lines.append(f"[al:{album}]")
    lines.append(f"[ti:{title}]")
    lines.append(f"[length:{length_str}]")
    lines.append("")

    starts = section_starts(duration_s)

    for section_name, section_lines in sections:
        ts = starts.get(section_name)
        if ts is None:
            continue

        lines.append(f"{fmt_time(ts)}[music: {section_name.lower()}]")

        # Get section duration from template
        section_dur = None
        for name, weight in SECTION_TEMPLATE:
            if name == section_name:
                section_dur = weight * duration_s
                break

        n = len(section_lines)
        if n > 0 and section_dur:
            for i, line in enumerate(section_lines):
                t = ts + (i + 0.5) * (section_dur / n)
                lines.append(f"{fmt_time(t)}{line}")

    lines.append("")
    lines.append("[tool:Hermes Agent lyrics-to-lrc.py]")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines), duration_s


def main():
    parser = argparse.ArgumentParser(description="Generate LRC synced-lyrics from .md files")
    parser.add_argument("--album-dir", required=True, help="Path to album folder containing lyrics/")
    parser.add_argument("--artist", default="Pyro Altar", help="Artist name")
    parser.add_argument("--album", default="Twenty-Two", help="Album name")
    parser.add_argument("--use-mp3-duration", action="store_true", default=True,
                        help="Use ffprobe to read actual MP3 duration (default: True)")
    args = parser.parse_args()

    album_dir = Path(args.album_dir)
    lyrics_dir = album_dir / "lyrics"
    music_dir = album_dir / "music"
    lrc_dir = album_dir / "lyrics-lrc"
    lrc_dir.mkdir(parents=True, exist_ok=True)

    if not lyrics_dir.exists():
        print(f"ERROR: {lyrics_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(lyrics_dir.glob("*.md"))
    if not md_files:
        print(f"ERROR: no .md files in {lyrics_dir}", file=sys.stderr)
        sys.exit(1)

    have_ffprobe = False
    if args.use_mp3_duration:
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
            have_ffprobe = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("WARNING: ffprobe not available, falling back to **Length:** field")

    print(f"Generating LRC files for {len(md_files)} tracks...")
    print(f"  ffprobe available: {have_ffprobe}")
    for md_path in md_files:
        slug = md_path.stem
        lrc_path = lrc_dir / f"{slug}.lrc"
        mp3_path = music_dir / f"{slug}.mp3" if have_ffprobe else None
        n, dur = generate_lrc(slug, md_path, lrc_path, args.artist, args.album, mp3_path)
        print(f"  ✅ {slug}.lrc: {n} lines ({dur}s)")

    print(f"\nDone. {len(md_files)} LRC files in {lrc_dir}/")


if __name__ == "__main__":
    main()
