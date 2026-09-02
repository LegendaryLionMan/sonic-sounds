"""db/albums.py — CRUD for artists, albums, tracks, assets (per Q23, Q24 v3.2 §Day 2).

Per Q23: 4 of the 13 tables are the core content schema
  (artists, albums, tracks, assets). These are what the build pipeline
  writes to.

Per Q24: ~150 lines of DDL; ~250 lines for db.py. This file is part of the
db.py layer (the rest is connection.py, migrations.py, sessions.py).

Per Q25: SQLite is at .meta/album-studio.db.

Per Q26: WAL mode + PRAGMAs applied via db.connection.

Per Q27: album.status is a derived value via SQLite trigger (already in
db/schema.sql).

Functions:
- Artists: list_artists, get_artist, create_artist, update_artist, delete_artist
- Albums: list_albums, get_album, create_album, update_album, archive_album
- Tracks: list_tracks, get_track, create_track, update_track, delete_track
- Assets: list_assets, get_asset, create_asset, update_asset, delete_asset

All return either a dict (sqlite3.Row) or list of dicts. All writes happen
inside a transaction (implicit via autocommit on the connection; explicit
commit() where needed).
"""
import sqlite3
from pathlib import Path
from typing import Optional, Union

from db.connection import open_db, DEFAULT_DB_PATH

# ===== ARTISTS =====

def _rows_to_dicts(rows) -> list[dict]:
    """Convert sqlite3.Row iterable to list of dicts."""
    return [dict(r) for r in rows]


def list_artists(db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List all artists, ordered by name."""
    conn = open_db(db_path)
    rows = conn.execute("SELECT * FROM artists ORDER BY name").fetchall()
    return _rows_to_dicts(rows)


def get_artist(artist_id: str,
              db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a single artist by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM artists WHERE id = ?", (artist_id,)
    ).fetchone()
    return dict(row) if row else None


def create_artist(artist_id: str, name: str, *,
                  persona: str = None,
                  hometown_city: str = None,
                  hometown_region: str = None,
                  hometown_country: str = None,
                  formed_year: int = None,
                  is_fictional: bool = False,
                  is_default: bool = False,
                  db_path: Optional[Union[str, Path]] = None) -> dict:
    """Create a new artist. Returns the created row.

    Raises sqlite3.IntegrityError if id is duplicate.
    """
    conn = open_db(db_path)
    conn.execute("""
        INSERT INTO artists (id, name, persona, hometown_city, hometown_region,
                             hometown_country, formed_year, is_fictional, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (artist_id, name, persona, hometown_city, hometown_region,
          hometown_country, formed_year, int(is_fictional), int(is_default)))
    conn.commit()
    return get_artist(artist_id, db_path)


def update_artist(artist_id: str, *,
                  name: str = None,
                  persona: str = None,
                  hometown_city: str = None,
                  hometown_region: str = None,
                  hometown_country: str = None,
                  formed_year: int = None,
                  is_fictional: bool = None,
                  is_default: bool = None,
                  db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Update an existing artist. Only provided fields are updated."""
    conn = open_db(db_path)
    fields = []
    values = []
    if name is not None:
        fields.append("name = ?"); values.append(name)
    if persona is not None:
        fields.append("persona = ?"); values.append(persona)
    if hometown_city is not None:
        fields.append("hometown_city = ?"); values.append(hometown_city)
    if hometown_region is not None:
        fields.append("hometown_region = ?"); values.append(hometown_region)
    if hometown_country is not None:
        fields.append("hometown_country = ?"); values.append(hometown_country)
    if formed_year is not None:
        fields.append("formed_year = ?"); values.append(formed_year)
    if is_fictional is not None:
        fields.append("is_fictional = ?"); values.append(int(is_fictional))
    if is_default is not None:
        fields.append("is_default = ?"); values.append(int(is_default))
    if not fields:
        return get_artist(artist_id, db_path)
    fields.append("updated_at = datetime('now')")
    values.append(artist_id)
    conn.execute(
        f"UPDATE artists SET {', '.join(fields)} WHERE id = ?", values
    )
    conn.commit()
    return get_artist(artist_id, db_path)


def delete_artist(artist_id: str,
                 db_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete an artist. Returns True if deleted, False if not found."""
    conn = open_db(db_path)
    cur = conn.execute("DELETE FROM artists WHERE id = ?", (artist_id,))
    conn.commit()
    return cur.rowcount > 0


# ===== ALBUMS =====

def list_albums(db_path: Optional[Union[str, Path]] = None,
                status: str = None) -> list[dict]:
    """List all albums, optionally filtered by status.

    Per the plan §7 Day 4 CLI: 'list albums' shows (artist, title, status, last activity).
    """
    conn = open_db(db_path)
    if status:
        rows = conn.execute(
            "SELECT * FROM albums WHERE status = ? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM albums ORDER BY created_at DESC"
        ).fetchall()
    return _rows_to_dicts(rows)


def get_album(album_id: str,
             db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch an album by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM albums WHERE id = ?", (album_id,)
    ).fetchone()
    return dict(row) if row else None


def create_album(album_id: str, title: str, primary_artist_id: str, *,
                status: str = "active",
                release_date: str = None,
                runtime_min: int = None,
                cover_path: str = None,
                cassette_sticker_path: str = None,
                isrc: str = None,
                m09_sonic_dna: str = None,
                db_path: Optional[Union[str, Path]] = None) -> dict:
    """Create a new album. Returns the created row."""
    conn = open_db(db_path)
    conn.execute("""
        INSERT INTO albums (id, title, primary_artist_id, status, release_date,
                            runtime_min, cover_path, cassette_sticker_path, isrc,
                            m09_sonic_dna)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (album_id, title, primary_artist_id, status, release_date,
          runtime_min, cover_path, cassette_sticker_path, isrc, m09_sonic_dna))
    conn.commit()
    return get_album(album_id, db_path)


def update_album(album_id: str, **kwargs) -> Optional[dict]:
    """Update an album. Only provided fields are updated."""
    db_path = kwargs.pop("db_path", None)
    conn = open_db(db_path)
    fields = []
    values = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if key not in ("title", "status", "release_date", "runtime_min",
                       "cover_path", "cassette_sticker_path", "isrc",
                       "m09_sonic_dna", "primary_artist_id"):
            continue
        fields.append(f"{key} = ?")
        values.append(value)
    if not fields:
        return get_album(album_id, db_path=db_path)
    fields.append("updated_at = datetime('now')")
    values.append(album_id)
    conn.execute(f"UPDATE albums SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_album(album_id, db_path=db_path)


def archive_album(album_id: str,
                 db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Archive an album (status='archived')."""
    return update_album(album_id, status="archived", db_path=db_path)


# ===== TRACKS =====

def list_tracks(album_id: str,
               db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List all tracks for an album, ordered by track_num."""
    conn = open_db(db_path)
    rows = conn.execute(
        "SELECT * FROM tracks WHERE album_id = ? ORDER BY track_num",
        (album_id,)
    ).fetchall()
    return _rows_to_dicts(rows)


def list_tracks_count(album_id: str,
                    db_path: Optional[Union[str, Path]] = None) -> int:
    """Count the number of tracks in an album. Used by the library.js
    cassette wall to render "N tracks" without loading all rows.
    """
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM tracks WHERE album_id = ?",
        (album_id,),
    ).fetchone()
    return int(row["n"]) if row else 0


def get_track(track_id: str,
             db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a track by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM tracks WHERE id = ?", (track_id,)
    ).fetchone()
    return dict(row) if row else None


def create_track(album_id: str, track_num: int, title: str, *,
                duration_sec: int = None,
                isrc: str = None,
                lyrics_path: str = None,
                lrc_path: str = None,
                mp3_path: str = None,
                cover_path: str = None,
                mood: str = None,
                status: str = "todo",
                db_path: Optional[Union[str, Path]] = None) -> dict:
    """Create a new track. The track_id is auto-generated as <album_id>:<track_num>."""
    track_id = f"{album_id}:{track_num:02d}"
    conn = open_db(db_path)
    conn.execute("""
        INSERT INTO tracks (id, album_id, track_num, title, duration_sec, isrc,
                            lyrics_path, lrc_path, mp3_path, mood, cover_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (track_id, album_id, track_num, title, duration_sec, isrc,
          lyrics_path, lrc_path, mp3_path, mood, cover_path, status))
    conn.commit()
    return get_track(track_id, db_path)


def update_track(track_id: str, **kwargs) -> Optional[dict]:
    """Update a track. Only provided fields are updated."""
    db_path = kwargs.pop("db_path", None)
    conn = open_db(db_path)
    fields = []
    values = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if key not in ("title", "duration_sec", "isrc", "lyrics_path", "lrc_path",
                       "mp3_path", "mood", "cover_path", "status"):
            continue
        fields.append(f"{key} = ?")
        values.append(value)
    if not fields:
        return get_track(track_id, db_path=db_path)
    fields.append("updated_at = datetime('now')")
    values.append(track_id)
    conn.execute(f"UPDATE tracks SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_track(track_id, db_path=db_path)


def delete_track(track_id: str,
                db_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete a track. Returns True if deleted."""
    conn = open_db(db_path)
    cur = conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
    conn.commit()
    return cur.rowcount > 0


# ===== ASSETS =====

def list_assets(album_id: str,
               kind: str = None,
               db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """List all assets for an album, optionally filtered by kind."""
    conn = open_db(db_path)
    if kind:
        rows = conn.execute(
            "SELECT * FROM assets WHERE album_id = ? AND kind = ? ORDER BY id",
            (album_id, kind)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM assets WHERE album_id = ? ORDER BY id",
            (album_id,)
        ).fetchall()
    return _rows_to_dicts(rows)


def get_asset(asset_id: str,
             db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Fetch a single asset by ID."""
    conn = open_db(db_path)
    row = conn.execute(
        "SELECT * FROM assets WHERE id = ?", (asset_id,)
    ).fetchone()
    return dict(row) if row else None


def create_asset(asset_id: str, album_id: str, kind: str, path: str, *,
                mime: str = None,
                width: int = None,
                height: int = None,
                size_bytes: int = None,
                sha256: str = None,
                db_path: Optional[Union[str, Path]] = None) -> dict:
    """Create a new asset. Returns the created row."""
    conn = open_db(db_path)
    conn.execute("""
        INSERT INTO assets (id, album_id, kind, path, mime, width, height,
                            size_bytes, sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (asset_id, album_id, kind, path, mime, width, height, size_bytes, sha256))
    conn.commit()
    return get_asset(asset_id, db_path)


def update_asset(asset_id: str, **kwargs) -> Optional[dict]:
    """Update an asset. Only provided fields are updated."""
    db_path = kwargs.pop("db_path", None)
    conn = open_db(db_path)
    fields = []
    values = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if key not in ("kind", "path", "mime", "width", "height", "size_bytes", "sha256"):
            continue
        fields.append(f"{key} = ?")
        values.append(value)
    if not fields:
        return get_asset(asset_id, db_path=db_path)
    values.append(asset_id)
    conn.execute(f"UPDATE assets SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return get_asset(asset_id, db_path=db_path)


def delete_asset(asset_id: str,
                db_path: Optional[Union[str, Path]] = None) -> bool:
    """Delete an asset. Returns True if deleted."""
    conn = open_db(db_path)
    cur = conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    return cur.rowcount > 0
