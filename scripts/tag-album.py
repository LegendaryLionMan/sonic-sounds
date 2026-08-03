"""
tag-album.py — Embed ID3 tags + cover art into album MP3 files.

Usage:
    python scripts/tag-album.py --album-dir <path> [--cover <jpg>]

Reads:
  <album-dir>/music/*.mp3
  <album-dir>/cover-art/album-cover-front-square.jpg  (default cover, optional)
  <album-dir>/lyrics/*.md                            (used for track titles + lyrics)

Writes:
  Same MP3s in-place, with embedded:
    - ID3v2.3 tags: artist, album, title, track, albumartist, date, genre, comment
    - Cover art (front square, 3000x3000)
    - Lyrics prose (full lyrics text)

Requires:
    pip install mutagen Pillow
"""
import argparse
import re
import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TDRC, TCON, COMM, USLT, APIC, error
    HAVE_MUTAGEN = True
except ImportError:
    HAVE_MUTAGEN = False


def parse_lyrics_md(path):
    """Return (meta_dict, prose_text) — full body joined as a single string."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    body_lines = []
    for line in text.splitlines():
        m = re.match(r"^\*\*(\w+):\*\*\s*(.+)$", line.strip())
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        if line.startswith("# ") or line.startswith("Production:"):
            continue
        body_lines.append(line)
    return meta, "\n".join(body_lines).strip()


def slug_to_title(slug):
    """Convert '01-razor' or '05-twenty-two' to title."""
    if slug == "05-twenty-two":
        return "Twenty-Two"
    track_num, track_title = slug.split("-", 1)
    return track_title.replace("-", " ").title()


def tag_track(mp3_path, lyrics_path, artist, album, year, genre, cover_path=None):
    """Apply ID3 tags to one MP3. Returns list of tags written."""
    if not HAVE_MUTAGEN:
        return ["ERROR: mutagen not installed"]

    slug = mp3_path.stem
    track_num = int(slug.split("-")[0])
    title = slug_to_title(slug)

    # Load + create ID3
    try:
        audio = MP3(str(mp3_path), ID3=ID3)
    except Exception:
        audio = MP3(str(mp3_path))
        audio.add_tags()

    written = []

    # Basic tags
    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artist))
    audio.tags.add(TPE2(encoding=3, text=artist))
    audio.tags.add(TALB(encoding=3, text=album))
    audio.tags.add(TRCK(encoding=3, text=f"{track_num}/12"))
    audio.tags.add(TDRC(encoding=3, text=str(year)))
    audio.tags.add(TCON(encoding=3, text=genre))
    audio.tags.add(COMM(encoding=3, lang="eng", desc="Hermes Agent",
                       text="Pyro Altar — Twenty-Two (2026-08-03)"))
    written += ["TIT2", "TPE1", "TPE2", "TALB", "TRCK", "TDRC", "TCON", "COMM"]

    # Lyrics
    if lyrics_path and lyrics_path.exists():
        _, prose = parse_lyrics_md(lyrics_path)
        audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=prose))
        written.append("USLT")

    # Cover art
    if cover_path and cover_path.exists():
        with open(cover_path, "rb") as f:
            data = f.read()
        audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front",
                           data=data))
        written.append("APIC")

    audio.save()
    return written


def main():
    parser = argparse.ArgumentParser(description="Embed ID3 tags + cover + lyrics into album")
    parser.add_argument("--album-dir", required=True)
    parser.add_argument("--artist", default="Pyro Altar")
    parser.add_argument("--album", default="Twenty-Two")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--genre", default="Grunge")
    parser.add_argument("--cover", default=None,
                        help="Path to cover JPG (default: <album-dir>/cover-art/album-cover-front-square.jpg)")
    args = parser.parse_args()

    if not HAVE_MUTAGEN:
        print("ERROR: mutagen not installed. Run: pip install mutagen Pillow", file=sys.stderr)
        sys.exit(1)

    album_dir = Path(args.album_dir)
    music_dir = album_dir / "music"
    lyrics_dir = album_dir / "lyrics"

    if not music_dir.exists():
        print(f"ERROR: {music_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    if args.cover:
        cover_path = Path(args.cover)
    else:
        cover_path = album_dir / "cover-art" / "album-cover-front-square.jpg"
    if not cover_path.exists():
        print(f"WARNING: cover not found at {cover_path}, skipping cover art")
        cover_path = None

    mp3_files = sorted(music_dir.glob("*.mp3"))
    print(f"Tagging {len(mp3_files)} tracks...")
    for mp3_path in mp3_files:
        lyrics_path = lyrics_dir / f"{mp3_path.stem}.md"
        tags = tag_track(mp3_path, lyrics_path, args.artist, args.album,
                         args.year, args.genre, cover_path)
        print(f"  ✅ {mp3_path.name}: {len(tags)} tags written ({', '.join(tags[:4])}...)")

    print(f"\nDone. {len(mp3_files)} tracks tagged.")


if __name__ == "__main__":
    main()
