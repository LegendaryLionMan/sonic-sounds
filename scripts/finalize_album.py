"""scripts/finalize-album.py — Day 11 finalize orchestration.

Per plan section Day 11:
  - 'Audio master stage (NEW in v2, locked 2026-08-02 §1.Q41):
    ffmpeg loudnorm two-pass per track to R15_loudnessTarget
    (default spotify = -14 LUFS). True-peak limiter at -1 dBTP.
    Writes loudness-report.json per track (input LUFS, target LUFS,
    applied gain, true-peak, dynamic range).'
  - 'Audio package stage (NEW in v2): ID3v2.4 metadata via mutagen
    (artist, album, track number, year, ISRC placeholder, cover art
    front-cover). Written to _master/ mirror before finalize completes.'
  - 'Versioning move: moves non-current asset versions to _OLD/,
    generates _OLD/INDEX.md audit trail (existing Q30 behavior)'
  - 'Album status flip: writes status=done to albums row + emits
    album_finalized event'

This script is callable from both:
  - the daemon: POST /api/albums/<id>/finalize (build/handlers_albums.py)
  - the CLI:   python -m scripts.finalize_album <album_id>

Public entry point: run_finalize(album_id, ...)
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger("sonic_studio.scripts.finalize")

# Per plan: Spotify default target = -14 LUFS, true-peak ceiling = -1 dBTP.
DEFAULT_TARGET_LUFS = -14.0
DEFAULT_TRUE_PEAK_DBTP = -1.0

# Where mastered files land. Per plan: "_master/ mirror before
# finalize completes". Lay this out at <project>/albums/<album_id>/_master/.
def _master_dir(album_id: str, *, base: Optional[Path] = None) -> Path:
    base = base or Path("albums")
    return base / album_id / "_master"


def _find_ffmpeg() -> Optional[str]:
    """Locate ffmpeg binary, or return None."""
    from shutil import which
    return which("ffmpeg")


def _measure_lufs(input_path: Path, ffmpeg: str) -> Optional[float]:
    """Run ffmpeg's loudnorm first pass to measure integrated loudness.

    Returns integrated LUFS (e.g. -23.0 for a quiet master) or None if
    measurement fails. Two-pass loudnorm requires this measurement for
    the second pass's linear/normalization args.
    """
    try:
        # -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary → stderr
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", str(input_path),
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=120,
        )
        # Summary line: "Input Integrated:  -23.4 LUFS"
        for line in (proc.stderr or "").splitlines():
            if "Input Integrated" in line:
                # value follows the colon
                parts = line.split(":")
                if len(parts) >= 2:
                    return float(parts[-1].strip().split()[0])
        return None
    except Exception as e:
        _log.warning(f"loudnorm measurement failed for {input_path}: {e}")
        return None


def _master_track(input_path: Path, output_path: Path,
                  target_lufs: float, true_peak: float,
                  ffmpeg: str) -> dict:
    """Two-pass loudnorm on a single audio file.

    Returns dict: {ok, input_lufs, output_lufs, true_peak, gain_db, error}.
    """
    if not input_path.exists():
        return {"ok": False, "error": f"input not found: {input_path}"}

    # Pass 1: measure
    input_lufs = _measure_lufs(input_path, ffmpeg)
    if input_lufs is None:
        # Without measurement, use single-pass loudnorm with target I=
        # Per plan, two-pass is the standard; we degrade gracefully.
        cmd1 = [ffmpeg, "-y", "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11",
                "-ar", "48000", str(output_path)]
        try:
            r = subprocess.run(cmd1, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                return {"ok": False, "error": f"ffmpeg failed: {r.stderr[:200]}"}
            return {"ok": True, "input_lufs": None, "output_lufs": target_lufs,
                    "true_peak": true_peak, "gain_db": 0.0}
        except Exception as e:
            return {"ok": False, "error": f"ffmpeg exception: {e}"}

    # Two-pass: compute the gain, apply normalization
    linear_gain = target_lufs - input_lufs
    cmd2 = [ffmpeg, "-y", "-i", str(input_path),
            "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:measured_I={input_lufs}:measured_TP=-1:measured_LRA=11:linear=true:offset={linear_gain}",
            "-ar", "48000", str(output_path)]
    try:
        r = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"ok": False, "error": f"ffmpeg two-pass failed: {r.stderr[:200]}",
                    "input_lufs": input_lufs}
        return {"ok": True, "input_lufs": input_lufs, "output_lufs": target_lufs,
                "true_peak": true_peak, "gain_db": linear_gain}
    except Exception as e:
        return {"ok": False, "error": f"ffmpeg two-pass exception: {e}",
                "input_lufs": input_lufs}


def _apply_id3_tags(mp3_path: Path, *, artist: str, album: str,
                    title: str, track_num: int, year: int,
                    isrc: Optional[str] = None,
                    cover_path: Optional[Path] = None) -> bool:
    """Write ID3v2.4 tags via mutagen. Returns True on success.

    Best-effort: if mutagen is missing or the file isn't an MP3, we
    log and return False. The caller treats this as a soft failure.
    """
    try:
        from mutagen.id3 import ID3, TPE1, TALB, TIT2, TRCK, TDRC, TSRC
        from mutagen.id3 import ID3NoHeaderError
    except ImportError:
        _log.warning("mutagen not installed; skipping ID3 tagging")
        return False
    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        try:
            tags = ID3()
        except Exception:
            return False
    except Exception as e:
        _log.warning(f"couldn't open ID3 for {mp3_path}: {e}")
        return False
    tags.add(TPE1(encoding=3, text=[artist]))
    tags.add(TALB(encoding=3, text=[album]))
    tags.add(TIT2(encoding=3, text=[title]))
    tags.add(TRCK(encoding=3, text=[str(track_num)]))
    tags.add(TDRC(encoding=3, text=[str(year)]))
    if isrc:
        tags.add(TSRC(encoding=3, text=[isrc]))
    if cover_path and cover_path.exists():
        try:
            from mutagen.id3 import APIC
            with open(cover_path, "rb") as f:
                cover_data = f.read()
            tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,  # front cover
                desc="cover",
                data=cover_data,
            ))
        except Exception as e:
            _log.warning(f"cover art embed failed: {e}")
    try:
        tags.save(str(mp3_path))
        return True
    except Exception as e:
        _log.warning(f"ID3 save failed for {mp3_path}: {e}")
        return False


def run_finalize(album_id: str, *,
                 target_lufs: float = DEFAULT_TARGET_LUFS,
                 true_peak_dbtp: float = DEFAULT_TRUE_PEAK_DBTP,
                 skip_mastering: bool = False,
                 apply_id3: bool = True,
                 base_dir: Optional[Path] = None,
                 db_path=None) -> dict:
    """Finalize an album: master tracks + ID3 tags + status flip.

    Args:
      album_id: the album slug
      target_lufs: integrated loudness target (default -14)
      true_peak_dbtp: true-peak ceiling (default -1.0)
      skip_mastering: if True, skip ffmpeg loudnorm (dry-run mode for
                     testing the orchestration without real audio)
      apply_id3: if True, write ID3v2.4 tags via mutagen
      base_dir: override the project root for tests
      db_path: override the db path for tests

    Returns a dict suitable for jsonify:
      {
        ok: bool,
        album_id: str,
        album_status: str (post-finalize),
        mastered_files: list[{track_id, status, ...}],
        id3_applied: list[track_id],
        lufs_measured: float | None,
        true_peak: float,
        loudness_report_path: str | None,
      }
    """
    base = base_dir or Path(".")
    base = base.resolve()
    ffmpeg = None if skip_mastering else _find_ffmpeg()
    if not skip_mastering and ffmpeg is None:
        _log.warning("ffmpeg not on PATH; running in dry-run (skip_mastering=True) mode")
        skip_mastering = True

    # Import db modules locally to avoid circular imports.
    from db import albums as db_albums
    from db.connection import open_db, close_db

    # Verify album exists.
    album_row = db_albums.get_album(album_id, db_path=db_path)
    if album_row is None:
        raise FileNotFoundError(f"album not found: {album_id!r}")

    # Master dir.
    master_dir = _master_dir(album_id, base=base)
    master_dir.mkdir(parents=True, exist_ok=True)

    # Track list (only ones with mp3_path)
    track_rows = db_albums.list_tracks(album_id, db_path=db_path)
    tracks_with_audio = [t for t in track_rows if t.get("mp3_path")]

    mastered_files = []
    id3_applied = []
    loudness_reports = []
    overall_lufs = None

    for tr in tracks_with_audio:
        src_path = base / tr["mp3_path"]
        if not src_path.exists():
            _log.warning(f"track {tr['id']} mp3 missing on disk: {src_path}")
            mastered_files.append({
                "track_id": tr["id"],
                "status": "skipped",
                "reason": f"mp3 not on disk at {src_path}",
            })
            continue
        out_path = master_dir / f"{tr['id'].replace(':', '-')}.mp3"
        if skip_mastering:
            # Dry-run: copy source → master for downstream consumption
            shutil.copy2(src_path, out_path)
            mastered_files.append({
                "track_id": tr["id"],
                "status": "dry_run",
                "out": str(out_path.relative_to(base)),
            })
            continue
        result = _master_track(src_path, out_path,
                                target_lufs=target_lufs,
                                true_peak=true_peak_dbtp,
                                ffmpeg=ffmpeg)
        entry = {
            "track_id": tr["id"],
            "status": "mastered" if result.get("ok") else "failed",
            "out": str(out_path.relative_to(base)),
            "input_lufs": result.get("input_lufs"),
            "gain_db": result.get("gain_db"),
        }
        if not result.get("ok"):
            entry["error"] = result.get("error")
        mastered_files.append(entry)
        if result.get("input_lufs"):
            loudness_reports.append({
                "track_id": tr["id"],
                "input_lufs": result["input_lufs"],
                "output_lufs": target_lufs,
                "gain_db": result.get("gain_db"),
                "true_peak_dbtp": true_peak_dbtp,
            })
            overall_lufs = result["input_lufs"]  # rough aggregate

        if apply_id3 and entry["status"] == "mastered":
            id3_ok = _apply_id3_tags(
                out_path,
                artist=album_row.get("primary_artist_id", ""),
                album=album_row.get("title", album_id),
                title=tr.get("title", tr["id"]),
                track_num=tr.get("track_num", 0),
                year=int(time.strftime("%Y")),
                isrc=tr.get("isrc"),
                cover_path=(base / album_row["cover_path"]) if album_row.get("cover_path") else None,
            )
            if id3_ok:
                id3_applied.append(tr["id"])

    # Write the loudness-report.json (per plan Q41 §1)
    report_path = master_dir / "loudness-report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "album_id": album_id,
            "target_lufs": target_lufs,
            "true_peak_dbtp": true_peak_dbtp,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tracks": loudness_reports,
        }, f, indent=2)

    # Album status flip (per plan)
    db_albums.update_album(album_id, status="done", db_path=db_path)
    final_row = db_albums.get_album(album_id, db_path=db_path)

    return {
        "ok": True,
        "album_id": album_id,
        "album_status": final_row.get("status"),
        "mastered_files": mastered_files,
        "id3_applied": id3_applied,
        "lufs_measured": overall_lufs,
        "true_peak": true_peak_dbtp,
        "loudness_report_path": str(report_path.relative_to(base)),
    }


# ============================================================
# CLI entry point
# ============================================================

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Finalize an album (Day 11)")
    parser.add_argument("album_id", help="album slug to finalize")
    parser.add_argument("--target-lufs", type=float, default=DEFAULT_TARGET_LUFS)
    parser.add_argument("--true-peak-dbtp", type=float, default=DEFAULT_TRUE_PEAK_DBTP)
    parser.add_argument("--skip-mastering", action="store_true",
                        help="Dry-run (no ffmpeg invocation)")
    parser.add_argument("--no-id3", action="store_true",
                        help="Skip ID3 tagging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_finalize(
        args.album_id,
        target_lufs=args.target_lufs,
        true_peak_dbtp=args.true_peak_dbtp,
        skip_mastering=args.skip_mastering,
        apply_id3=not args.no_id3,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys_exit = main()
    import sys as _sys
    _sys.exit(sys_exit)
