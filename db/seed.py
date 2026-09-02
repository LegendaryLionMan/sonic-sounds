"""db/seed.py — Maren Sol seed (per Phase 0.A + Day 2 of PLAN-2026-07-28-v3.2).

Walks the album canonical at `~/OneDrive/Hermes/albums/Half-Light-Hours/` and
inserts:
  - 1 artist (Maren Sol)
  - 1 album (Half-Light Hours)
  - 10 tracks (Dusk Index through Dawn Index Reprise)
  - ~30 assets (cover art + posters + cassette sticker + music videos + lyrics)

Then marks all 12 pipeline stages as 'done' for the seeded album (it's the
worked example — every other album will start at layer 01).

Usage:
  python -m db.seed [--db PATH]

If --db is omitted, defaults to `.meta/album-studio.db` (per plan §Day 2).
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

# Album canonical path (per R10 + structure-policy skill)
ALBUM_CANONICAL = Path("C:/Users/lion_/OneDrive/Hermes/albums/Half-Light-Hours")
DEFAULT_DB = Path(".meta/album-studio.db")
# Schema source: absolute path resolved at import time so it works
# regardless of the current working directory (e.g. service-mode daemon).
SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

# Locked M-lock values (per META-DECISIONS-2026-08-02 + M01-M09 schema examples)
MAREN_SOL_ARTIST = {
    "id": "maren-sol",
    "name": "Maren Sol",
    "persona": "indie folk artist, late-20s, dream-folk vocalist, breathy delivery",
    "hometown_city": "Vancouver",
    "hometown_region": "British Columbia",
    "hometown_country": "Canada",
    "formed_year": 2018,
    "is_fictional": 0,
    "is_default": 1,
}

HALF_LIGHT_HOURS_ALBUM = {
    "id": "half-light-hours",
    "title": "Half-Light Hours",
    "primary_artist_id": "maren-sol",
    "status": "active",
    "release_date": "2026-09-21",
    "runtime_min": 40,
    "cover_path": "cover-art/album-cover-front-square.jpg",
    "cassette_sticker_path": "merch/cassette-sticker-mixtape85.png",
    "isrc": "USS1Z2500001",
    "m09_sonic_dna": json.dumps({
        "genre": "dream-folk",
        "vocals": "Maren Sol, breathy mezzo-soprano, close-mic, intimate",
        "mood": "nostalgic, tender, half-lit windows, late autumn",
        "instruments": "acoustic guitar, light piano, brushed drums, fingerpicked strings",
        "references": "Maren Sol, Sufjan Stevens, Adrianne Lenker, Big Thief",
        "tempoProfile": "70-95 BPM, slow-to-mid",
        "lockedAt": "2026-08-05T00:00:00Z"
    }),
    "locked_at": "2026-08-05T00:00:00Z",
}

# 10 tracks (per tag-manifest.json)
# Title, duration in seconds, mood descriptor, ISRC suffix
TRACKS = [
    ("01", "Dusk Index", 204, "Intimate fingerpicked opener"),
    ("02", "Lease on a Vanishing", 252, "Hushed → swelling strings"),
    ("03", "Half-Light Hours", 278, "Atmospheric piano"),
    ("04", "You, in Static", 198, "Lo-fi bedroom"),
    ("05", "The Cartographer", 236, "Anthemic, handclaps"),
    ("06", "Borrowed Coats", 242, "Autumnal folk"),
    ("07", "Maps for the Disappearing", 264, "Anthemic harmonies"),
    ("08", "Silver Bay", 188, "Stripped piano ballad"),
    ("09", "What the Window Knew", 286, "Electronic-textured"),
    ("10", "Dawn Index (Reprise)", 216, "Gentle closer"),
]


def _mime_for_image(path: Path) -> str:
    """Return the MIME type for an image file based on its extension.

    Centralized so all asset-discover code paths produce consistent MIMEs.
    """
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "application/octet-stream"


def _mime_for_video(path: Path) -> str:
    """Return the MIME type for a video file based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".mov":
        return "video/quicktime"
    if suffix == ".webm":
        return "video/webm"
    return "application/octet-stream"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file. Returns '0' * 64 for missing files."""
    if not path.exists():
        return "0" * 64
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lyrics(track_id: str) -> str:
    """Read lyrics for a track. Returns empty string if missing."""
    md_path = ALBUM_CANONICAL / "lyrics" / f"{track_id}-{slugify(TRACKS_BY_ID[track_id])}.md"
    if not md_path.exists():
        return ""
    try:
        return md_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def slugify(title: str) -> str:
    """Convert 'Dusk Index' → 'dusk-index' for filename matching."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# Build a quick title-lookup
TRACKS_BY_ID = {tid: title for tid, title, _, _ in TRACKS}


def discover_assets(album_id: str) -> list[dict]:
    """Walk album-canonical/ and produce asset records for everything in
    cover-art/, posters/, merch/, music/, videos/, lyrics/.

    Each asset gets a stable id like "<album>:<kind>:<stem>".
    """
    assets = []

    # Cover art (jpg/png in cover-art/)
    for f in sorted((ALBUM_CANONICAL / "cover-art").glob("*")):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            kind = "cover" if "front" in f.stem else "artwork"
            assets.append({
                "id": f"{album_id}:cover:{f.stem}",
                "album_id": album_id,
                "kind": kind,
                "path": f"cover-art/{f.name}",
                "mime": _mime_for_image(f),
                "width": None,  # could detect with PIL but out of scope
                "height": None,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_file(f),
            })

    # Posters
    for f in sorted((ALBUM_CANONICAL / "posters").glob("*")):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            assets.append({
                "id": f"{album_id}:poster:{f.stem}",
                "album_id": album_id,
                "kind": "poster",
                "path": f"posters/{f.name}",
                # Use the actual extension to pick the MIME type. Hardcoding
                # image/jpeg for everything was a known bug; PNG and WebP
                # would be mislabeled.
                "mime": _mime_for_image(f),
                "width": None,
                "height": None,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_file(f),
            })

    # Merch (cassette sticker)
    for f in sorted((ALBUM_CANONICAL / "merch").glob("*")):
        if f.is_file() and f.suffix.lower() in (".jpg", ".png", ".webp"):
            kind = "cassette" if "cassette" in f.stem else "merch"
            assets.append({
                "id": f"{album_id}:{kind}:{f.stem}",
                "album_id": album_id,
                "kind": kind,
                "path": f"merch/{f.name}",
                "mime": _mime_for_image(f),
                "width": None,
                "height": None,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_file(f),
            })

    # Videos
    for f in sorted((ALBUM_CANONICAL / "videos").glob("*")):
        if f.is_file() and f.suffix.lower() in (".mp4", ".mov", ".webm"):
            assets.append({
                "id": f"{album_id}:video:{f.stem}",
                "album_id": album_id,
                "kind": "video",
                "path": f"videos/{f.name}",
                "mime": _mime_for_video(f),
                "width": None,
                "height": None,
                "size_bytes": f.stat().st_size,
                "sha256": sha256_file(f),
            })

    return assets


def read_album_cover(album_id: str) -> str | None:
    """Return the path to the primary album cover, or None."""
    cover_dir = ALBUM_CANONICAL / "cover-art"
    if not cover_dir.exists():
        return None
    for f in cover_dir.glob("album-cover-front-square*"):
        return f"cover-art/{f.name}"
    return None


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply the schema.sql to a fresh database."""
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    conn.executescript(sql)


def seed_half_light_hours(db_path: Path = DEFAULT_DB) -> dict:
    """Run the full seed migration. Returns a summary dict."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not ALBUM_CANONICAL.exists():
        raise FileNotFoundError(
            f"Album canonical not found at {ALBUM_CANONICAL}. "
            f"Per R10, this is the required source for the seed."
        )

    if db_path.exists():
        # Don't overwrite an existing db
        print(f"Database already exists at {db_path}. Use --force to overwrite.")
        return {"skipped": True, "reason": "db exists"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        # Apply schema
        init_schema(conn)

        # 1. Insert artist
        conn.execute("""
            INSERT INTO artists (id, name, persona, hometown_city, hometown_region,
                                 hometown_country, formed_year, is_fictional, is_default)
            VALUES (:id, :name, :persona, :hometown_city, :hometown_region,
                    :hometown_country, :formed_year, :is_fictional, :is_default)
        """, MAREN_SOL_ARTIST)
        print(f"  ✓ Inserted artist: {MAREN_SOL_ARTIST['name']}")

        # 2. Insert album
        cover = read_album_cover(HALF_LIGHT_HOURS_ALBUM["id"])
        if cover:
            HALF_LIGHT_HOURS_ALBUM["cover_path"] = cover
        conn.execute("""
            INSERT INTO albums (id, title, primary_artist_id, status, release_date,
                                runtime_min, cover_path, cassette_sticker_path, isrc,
                                m09_sonic_dna, locked_at)
            VALUES (:id, :title, :primary_artist_id, :status, :release_date,
                    :runtime_min, :cover_path, :cassette_sticker_path, :isrc,
                    :m09_sonic_dna, :locked_at)
        """, HALF_LIGHT_HOURS_ALBUM)
        print(f"  ✓ Inserted album: {HALF_LIGHT_HOURS_ALBUM['title']}")

        # 3. Insert tracks
        album_id = HALF_LIGHT_HOURS_ALBUM["id"]
        for tid, title, duration, mood in TRACKS:
            track_id = f"{album_id}:{tid}"
            # ISRC format: 2 country + 3 registrant + 2 year + 5 designation.
            # The seed registrant code is "S1Z25" (placeholder for Maren Sol's
            # label) and year is 2025. Each track gets a unique 5-digit
            # designation starting at 00001.
            track_num_int = int(tid)
            isrc = f"USS1Z25{track_num_int:05d}"
            slug = slugify(title)
            mp3 = ALBUM_CANONICAL / "music" / f"{tid}-{slug}.mp3"
            lyrics_md = ALBUM_CANONICAL / "lyrics" / f"{tid}-{slug}.md"
            lrc = ALBUM_CANONICAL / "lyrics-lrc" / f"{tid}-{slug}.lrc"
            conn.execute("""
                INSERT INTO tracks (id, album_id, track_num, title, duration_sec, isrc,
                                    lyrics_path, lrc_path, mp3_path, mood, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track_id, album_id, int(tid), title, duration, isrc,
                f"lyrics/{tid}-{slug}.md" if lyrics_md.exists() else None,
                f"lyrics-lrc/{tid}-{slug}.lrc" if lrc.exists() else None,
                f"music/{tid}-{slug}.mp3" if mp3.exists() else None,
                mood,
                "tagged" if mp3.exists() else "todo",
            ))
        print(f"  ✓ Inserted {len(TRACKS)} tracks")

        # 4. Insert assets
        assets = discover_assets(album_id)
        for a in assets:
            conn.execute("""
                INSERT INTO assets (id, album_id, kind, path, mime, width, height, size_bytes, sha256)
                VALUES (:id, :album_id, :kind, :path, :mime, :width, :height, :size_bytes, :sha256)
            """, a)
        print(f"  ✓ Inserted {len(assets)} assets")

        # 5. Mark all 12 pipeline stages as done
        # (per the plan: "Mark all 12 pipeline stages as 'done' for the
        # seeded album (it's the worked example)")
        from db.pipeline import LAYER_ORDER
        for layer_id in LAYER_ORDER:
            approved_at = "2026-08-05T00:00:00Z" if layer_id in {
                "02_lyrics_drafts", "03_lyrics_finalize", "06_cover_art",
                "09_metadata_isrc", "11_press_kit", "12_finalize"
            } else None
            conn.execute("""
                INSERT INTO build_jobs (album_id, layer_id, status, approved_at,
                                         started_at, completed_at)
                VALUES (?, ?, 'done', ?, ?, ?)
            """, (
                album_id, layer_id, approved_at,
                "2026-08-01T00:00:00Z", "2026-08-04T00:00:00Z"
            ))
        print(f"  ✓ Marked {len(LAYER_ORDER)} pipeline stages as 'done'")

        # 6. Insert an album_briefs row with the locked M-decisions
        brief_json = json.dumps({
            "concept": "Half-Light Hours is a memory-journal album — 10 vignettes from the half-lit windows of late autumn.",
            "locked_decisions": {
                "M01_concept": "memory-journal, half-lit windows, late autumn",
                "M02_scope": "album, 10 tracks, ~37 min",
                "M03_genre": "dream-folk, atmospheric, intimate",
                "M04_references": ["Maren Sol (artist's own work)", "Sufjan Stevens", "Adrianne Lenker"],
                "M05_vocal": "solo, breathy mezzo-soprano, close-mic",
                "M06_language": "english only",
                "M07_runtime": "3:00-4:00 per track",
                "M08_artistName": "Maren Sol",
                "M08_bandName": None,
                "M08_creditLine": None,
            },
            "sonic_dna": json.loads(HALF_LIGHT_HOURS_ALBUM["m09_sonic_dna"]),
        }, indent=2)
        conn.execute("""
            INSERT INTO album_briefs (album_id, brief_json, sonic_dna_json)
            VALUES (?, ?, ?)
        """, (album_id, brief_json, HALF_LIGHT_HOURS_ALBUM["m09_sonic_dna"]))
        print(f"  ✓ Inserted album_briefs with locked M-decisions")

        # 7. Record the seed in audit_log
        conn.execute("""
            INSERT INTO audit_log (actor, action, target, payload_json)
            VALUES ('daemon', 'seed.half-light-hours', ?, ?)
        """, (album_id, json.dumps({"tracks": len(TRACKS), "assets": len(assets)})))
        print(f"  ✓ Wrote audit_log entry")

        conn.commit()
        print(f"\n  ✓ Seeded {db_path}")

        return {
            "skipped": False,
            "artist": 1,
            "album": 1,
            "tracks": len(TRACKS),
            "assets": len(assets),
            "layers_marked_done": len(LAYER_ORDER),
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Maren Sol seed (Phase 0.A)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"Path to SQLite db (default: {DEFAULT_DB})")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing db (DESTRUCTIVE)")
    args = parser.parse_args()

    if args.force and args.db.exists():
        # Remove the main db file plus any WAL/SHM sidecar files. Without
        # removing WAL/SHM, the next open() may read a stale WAL and either
        # fail with "database disk image is malformed" or silently leak
        # transactions from the old database.
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(args.db) + suffix)
            if p.exists():
                p.unlink()
                print(f"  ! Force-deleted {p}")

    if not ALBUM_CANONICAL.exists():
        print(f"ERROR: Album canonical not found at {ALBUM_CANONICAL}")
        print(f"       Per R10, this is the required source for the seed.")
        sys.exit(1)

    print(f"=== Phase 0.A: Maren Sol seed ===")
    print(f"  Album canonical: {ALBUM_CANONICAL}")
    print(f"  DB: {args.db}")
    print(f"  Schema: {SCHEMA_FILE}")
    print()

    result = seed_half_light_hours(args.db)
    print(f"\n  Summary: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
