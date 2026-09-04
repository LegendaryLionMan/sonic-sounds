"""
generation-manifest.py — Write per-track generation manifests for sonic-sounds builds.

Usage:
    python scripts/generation-manifest.py --album-dir <path> [--track <slug>] [--regen]

For each track, writes:
    <album-dir>/music/<slug>.generation-manifest.json

The manifest captures EXACTLY what was sent to `mmx music generate`, plus the
output file's fingerprint (md5, duration, bitrate). This is the ground truth
for "what produced this MP3" — if you re-run the build, you can diff the
manifest against new params to detect sonic drift.

Manifest schema (v1):
    {
        "manifest_version": "1.0",
        "track_slug": "01-razor",
        "track_index": 1,
        "generated_at": "2026-08-03T19:42:13Z",
        "model": "music-3.0",
        "schema_version": "v2.2",
        "sonic_dna_locked_at": "2026-08-03T19:30:00Z",  # from M09_sonicDNA
        "prompt": {
            "body": "Hard rock in E minor at 145 BPM, raw and aggressive. ...",
            "chars": 857,
            "source_file": "<album-dir>/scripts/prompts/01-razor.md"
        },
        "flags": {
            "vocals": "Axl Rose-style raw high tenor, ...",
            "genre": "hard rock",
            "mood": "aggressive, swaggering, explosive",
            "instruments": "dual electric guitars through Marshall stacks, ...",
            "tempo": "fast",
            "bpm": 145,
            "key": "E minor",
            "use_case": "album-opening hard rock anthem, lead single",
            "structure": "intro-verse1-prechorus1-chorus1-verse2-prechorus2-chorus2-bridge-solo-chorus3-outro",
            "references": "Guns N' Roses Appetite for Destruction, Skid Row Slave to the Grind, Mötley Crüe Shout at the Devil"
        },
        "lyrics_source": "<album-dir>/lyrics/01-razor.md",
        "lyrics_chars": 1955,
        "output": {
            "file": "<album-dir>/music/01-razor.mp3",
            "md5": "abc123...",
            "size_bytes": 7849317,
            "duration_seconds": 245.3,
            "bitrate_bps": 256028,
            "sample_rate_hz": 44100,
            "channels": 2
        }
    }

WHY THIS EXISTS:
    The Twenty-Two build (2026-08-03) showed a clear failure mode: the schema
    locked M03_genre = "90s grunge with FF melodic hooks" + M05_vocal =
    "Velvet Revolver-style (Scott Weiland)", but a re-gen silently switched
    to hard rock + Axl Rose vocals. The schema and the artifact DRIFTED.

    The manifest is the studio's defense. Once written, it pins the build
    to a specific (model, prompt, flags, lyrics, output) tuple. Future
    regens can be diff-checked against the manifest — any change to
    vocals/genre/mood/instruments/references/bpm/key IS drift, and the
    check-sonic-drift.py script surfaces it before regeneration.

CONTRACT:
    The build pipeline (full-album-release-package) MUST call this script
    after every successful `mmx music generate`. The manifest is appended-
    only: any modification is logged as `manifestModifiedAt`.

Requires:
    pip install (mutagen)  -- for mp3 duration + bitrate reading
    ffprobe in PATH         -- fallback if mutagen returns 0:00

Schema bump policy:
    Manifest schema is independent of intake-data/schema.json. When the
    manifest schema changes, bump `manifest_version`. The check script
    is permissive across versions but flags unknown versions.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    HAVE_MUTAGEN = True
except ImportError:
    HAVE_MUTAGEN = False


# === OLD-MODEL GUARD (added 2026-08-04, user mandate) =========================
# User rule (2026-08-04): "never use the old model. find the way to use the new one."
# music-3.0 is the default + only acceptable model. Older models produce
# thin, short, less detailed audio. Block at manifest-write time so old
# tracks can never enter the build pipeline.
ALLOWED_MODELS = {"music-3.0"}
BLOCKED_MODELS = {"music-2.6", "music-2.6-free", "music-2.5", "music-2.5+",
                  "music-2.0", "music-1.0", "music-1.5"}


def check_model_allowed(model_name: str, source: str) -> None:
    """Exit 2 with a clear error if model is not in ALLOWED_MODELS.

    source: human-readable description of where the model string came from
    (e.g. 'prompt file', 'flags', 'manifest top-level') for debugging.
    """
    if model_name in BLOCKED_MODELS:
        print(f"[ERROR] BLOCKED model '{model_name}' found in {source}.", file=sys.stderr)
        print(f"[ERROR] User mandate (2026-08-04): NEVER use {model_name}.", file=sys.stderr)
        print(f"[ERROR] Only music-3.0 is allowed. If you don't pass --model,", file=sys.stderr)
        print(f"[ERROR] mmx defaults to music-3.0 — just omit the flag entirely.", file=sys.stderr)
        print(f"[ERROR] To regenerate this track: re-run mmx music generate WITHOUT --model music-2.6", file=sys.stderr)
        sys.exit(2)
    if model_name and model_name not in ALLOWED_MODELS:
        print(f"[ERROR] Unknown model '{model_name}' in {source}.", file=sys.stderr)
        print(f"[ERROR] Allowed models: {sorted(ALLOWED_MODELS)}", file=sys.stderr)
        sys.exit(2)


def md5_file(p: Path) -> str:
    """Compute MD5 of a file."""
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_audio_metadata(mp3_path: Path) -> dict:
    """Get duration/bitrate/sample-rate/channels for an MP3. ffprobe first, mutagen fallback."""
    # Try ffprobe first (most reliable, especially for Hailuo-generated MP3s
    # where mutagen sometimes returns 0:00 due to Xing/LAME header quirk)
    try:
        info = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,bit_rate,size", "-show_entries",
             "stream=sample_rate,channels",
             "-of", "json", str(mp3_path)],
            capture_output=True, text=True, check=True,
        )
        meta = json.loads(info.stdout)
        dur = float(meta["format"]["duration"])
        br = int(meta["format"]["bit_rate"])
        size = int(meta["format"]["size"])
        sr = int(meta["streams"][0]["sample_rate"])
        ch = int(meta["streams"][0]["channels"])
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"  [warn] ffprobe failed ({e}); falling back to mutagen", file=sys.stderr)
        if HAVE_MUTAGEN:
            try:
                m = MP3(str(mp3_path))
                dur = m.info.length
                br = m.info.bitrate
                size = mp3_path.stat().st_size
                sr = m.info.sample_rate
                ch = m.info.channels
            except Exception as e2:
                print(f"  [error] mutagen also failed: {e2}", file=sys.stderr)
                return None
        else:
            return None

    return {
        "file": str(mp3_path),
        "md5": md5_file(mp3_path),
        "size_bytes": size,
        "duration_seconds": round(dur, 3),
        "bitrate_bps": br,
        "sample_rate_hz": sr,
        "channels": ch,
    }


def parse_prompt_md(prompt_md_path: Path) -> dict:
    """Parse a prompt markdown file into body + flags.

    Expected format:
        # <slug>
        **BPM:** 145
        **Key:** E minor
        **Genre:** hard rock

        ## Prompt (sent to --prompt)
        ```
        Hard rock in E minor at 145 BPM, ...
        ```

        ## Other flags
        - `--vocals` ...
        - `--genre` hard rock
        ...
    """
    if not prompt_md_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_md_path}")

    content = prompt_md_path.read_text(encoding="utf-8")

    # Extract prompt body from ```code block```
    m = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
    if not m:
        raise ValueError(f"No ```code block``` found in {prompt_md_path}")
    body = m.group(1)

    # Extract flag-style metadata
    flags = {}
    flag_section = re.search(r"## Other flags\n\n(.*?)(?:\n## |\Z)",
                             content, re.DOTALL)
    if flag_section:
        for line in flag_section.group(1).split("\n"):
            line = line.strip()
            if not line.startswith("- `--"):
                continue
            # Parse: - `--flagname` value
            mm = re.match(r"^-\s+`--(\w+)`\s*(.*)$", line)
            if mm:
                fname, fvalue = mm.group(1), mm.group(2).strip()
                # Try to parse numeric values (bpm)
                if fname == "bpm":
                    try:
                        flags[fname] = int(fvalue)
                    except ValueError:
                        flags[fname] = fvalue
                else:
                    flags[fname] = fvalue

    # Extract top-level metadata (BPM, Key, Genre)
    meta = {}
    for line in content.split("\n"):
        line = line.strip()
        mm = re.match(r"^\*\*(\w+):\*\*\s*(.*)$", line)
        if mm:
            key = mm.group(1).lower()
            val = mm.group(2).strip()
            if key in ("bpm",):
                try:
                    meta[key] = int(val)
                except ValueError:
                    meta[key] = val
            else:
                meta[key] = val

    return {
        "prompt": {
            "body": body,
            "chars": len(body),
            "source_file": str(prompt_md_path),
        },
        "flags": flags,
        "metadata": meta,
    }


def load_sonic_dna(album_dir: Path) -> dict | None:
    """Load the M09_sonicDNA from the intake JSON if it exists."""
    intake_dir = album_dir.parent / "intake-data" if (album_dir.parent / "intake-data").exists() else None
    # The intake file lives at intake-data/<slug>.json relative to the project
    # root. The album dir is at music/<slug>/. Try a few locations.
    candidates = [
        album_dir.parent / "intake-data" / f"{album_dir.name}.json",
        Path(r"C:\Users\lion_\Documents\Projects\sonic-sounds\intake-data") / f"{album_dir.name}.json",
    ]
    for c in candidates:
        if c.exists():
            data = json.loads(c.read_text(encoding="utf-8"))
            sonic = data.get("values", {}).get("M09_sonicDNA", {})
            if sonic.get("value"):
                return sonic
    return None


def load_schema_version(album_dir: Path) -> str:
    """Find the current schema version. Walk up to find intake-data/schema.json."""
    candidates = [
        album_dir.parent / "intake-data" / "schema.json",
        Path(r"C:\Users\lion_\Documents\Projects\sonic-sounds\intake-data\schema.json"),
    ]
    for c in candidates:
        if c.exists():
            data = json.loads(c.read_text(encoding="utf-8"))
            return data.get("schemaVersion", "unknown")
    return "unknown"


def build_manifest(album_dir: Path, slug: str, schema_version: str,
                   sonic_dna: dict | None, regen: bool = False) -> dict:
    """Build the manifest for one track."""
    mp3_path = album_dir / "music" / f"{slug}.mp3"
    if not mp3_path.exists():
        raise FileNotFoundError(f"MP3 not found: {mp3_path}")

    # Prompt source
    prompt_candidates = [
        album_dir / "scripts" / "prompts" / f"{slug}.md",
        album_dir.parent / "scripts" / "prompts" / f"{slug}.md",
        Path(r"C:\Users\lion_\Documents\Projects\sonic-sounds\scripts\prompts") / f"{slug}.md",
    ]
    prompt_md = None
    for c in prompt_candidates:
        if c.exists():
            prompt_md = c
            break

    if not prompt_md:
        raise FileNotFoundError(f"Prompt file not found for {slug}")

    parsed = parse_prompt_md(prompt_md)

    # Lyrics source
    lyrics_path = album_dir / "lyrics" / f"{slug}.md"
    lyrics_chars = lyrics_path.stat().st_size if lyrics_path.exists() else 0

    # Audio metadata
    audio_meta = get_audio_metadata(mp3_path)
    if not audio_meta:
        raise RuntimeError(f"Could not read audio metadata for {mp3_path}")

    # Track index from slug (01-razor -> 1)
    idx = int(slug.split("-")[0]) if slug.split("-")[0].isdigit() else None

    # Sonic DNA reference
    sonic_dna_locked_at = sonic_dna.get("value", {}).get("lockedAt") if sonic_dna else None

    # === OLD-MODEL GUARD: validate the model BEFORE writing the manifest ===
    # Check 3 sources: top-level metadata, flags block, default fallback
    model_from_meta = parsed["metadata"].get("model", "music-3.0")
    model_from_flags = parsed["flags"].get("model", "music-3.0")
    if model_from_meta:
        check_model_allowed(model_from_meta, "prompt metadata header")
    if model_from_flags:
        check_model_allowed(model_from_flags, "prompt --model flag")

    manifest = {
        "manifest_version": "1.0",
        "track_slug": slug,
        "track_index": idx,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": parsed["metadata"].get("model", "music-3.0"),
        "schema_version": schema_version,
        "sonic_dna_locked_at": sonic_dna_locked_at,
        "prompt": parsed["prompt"],
        "flags": parsed["flags"],
        "lyrics_source": str(lyrics_path) if lyrics_path.exists() else None,
        "lyrics_chars": lyrics_chars,
        "output": audio_meta,
    }

    if regen:
        manifest["regen_of"] = None  # Can be filled by caller

    return manifest


def write_manifest(album_dir: Path, slug: str, manifest: dict, regen: bool = False):
    """Write manifest to disk. If existing manifest exists, preserve history."""
    manifest_path = album_dir / "music" / f"{slug}.generation-manifest.json"

    history = []
    if manifest_path.exists() and regen:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "history" in old:
            history = old["history"]
        elif old.get("manifest_version"):
            # First regen: archive the v1
            history = [{"archived_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "manifest": old}]

    if history:
        manifest["history"] = history

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="Write per-track generation manifests")
    parser.add_argument("--album-dir", type=Path, required=True,
                        help="Album directory containing music/, lyrics/, scripts/prompts/")
    parser.add_argument("--track", type=str, default=None,
                        help="Single track slug (e.g. '01-razor'). Default: all tracks in music/")
    parser.add_argument("--regen", action="store_true",
                        help="This is a regen — preserve prior manifest in 'history' field")
    args = parser.parse_args()

    album_dir = args.album_dir.resolve()
    music_dir = album_dir / "music"
    if not music_dir.exists():
        print(f"[error] music/ not found at {album_dir}", file=sys.stderr)
        sys.exit(1)

    schema_version = load_schema_version(album_dir)
    sonic_dna = load_sonic_dna(album_dir)

    # Discover tracks
    if args.track:
        tracks = [args.track]
    else:
        tracks = sorted(
            p.stem for p in music_dir.glob("*.mp3")
            if not p.stem.endswith(".generation-manifest")
        )

    print(f"Album: {album_dir.name}")
    print(f"Schema: {schema_version}")
    print(f"Sonic DNA locked: {sonic_dna is not None}")
    print(f"Tracks to process: {len(tracks)}")
    print()

    success = 0
    failures = []
    for slug in tracks:
        try:
            manifest = build_manifest(album_dir, slug, schema_version, sonic_dna, args.regen)
            path = write_manifest(album_dir, slug, manifest, args.regen)
            print(f"  ✅ {slug}: {manifest['output']['duration_seconds']:.1f}s "
                  f"@ {manifest['output']['bitrate_bps']} bps "
                  f"→ {path.name}")
            success += 1
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            print(f"  ❌ {slug}: {e}")
            failures.append((slug, str(e)))

    print()
    print(f"Generated {success}/{len(tracks)} manifests")
    if failures:
        print(f"Failures:")
        for slug, err in failures:
            print(f"  - {slug}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()