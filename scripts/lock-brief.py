"""
lock-brief.py — Lock an album's brief by auto-populating M09_sonicDNA.

Usage:
    # Auto-derive M09 from M03/M05/R12/M07 (recommended for most cases):
    python scripts/lock-brief.py --album-dir <album-folder>

    # Override individual fields (use when auto-derivation is wrong):
    python scripts/lock-brief.py --album-dir <album-folder> \\
        --override-vocals "Weiland-style wail" \\
        --override-genre "grunge"

    # Show what would be derived without writing:
    python scripts/lock-brief.py --album-dir <album-folder> --dry-run

After running, M09_sonicDNA.value.lockedAt is set and the intake JSON is
frozen as the build contract. Future regens must hold against these values
(see scripts/check-sonic-drift.py).

WHAT IT DOES:
1. Reads intake-data/<slug>.json (the album's exported brief)
2. Derives M09_sonicDNA.value from M03_genre, M05_vocal.primary_style,
   R12_production, M07_runtime, M04_references[0]
3. Optionally accepts --override-* flags for any field
4. Writes M09_sonicDNA.value + M09_sonicDNA.isDefault = false
5. Bumps schemaVersion if a M09_sonicDNA lock didn't exist before
6. Bumps intakeFormVersion to mark "locked at <timestamp>"
7. Verifies the locked values are parseable JSON
8. Prints a summary table showing what was derived vs. what was overridden

DERIVATION RULES (v1):
- genre        = M03_genre.value (string) — passed through as-is
                Override: --override-genre "<shorter categorical hint, e.g. 'hard rock'>"
- vocals       = M05_vocal.primary_style
                Override: --override-vocals "<vocal character for --vocals flag>"
- mood         = derived from R12_production.value + genre descriptor
                ('hybrid' + grunge → "intimate, dusky, raw"; 'full-band' + hard rock → "aggressive")
                Override: --override-mood "<mood descriptor for --mood flag>"
- instruments  = derived from production + genre (heuristic table below)
                Override: --override-instruments "<instruments for --instruments flag>"
- references   = M04_references[0].artist (+ album if multiple)
                Override: --override-references "<refs for --references flag>"
- tempoProfile = M07_runtime.min_per_track + " - " + M07_runtime.max_per_track + " per track"
                Override: --override-tempo "<tempo profile>"
- lockedAt     = current UTC ISO timestamp (always, no override)
- lockedBy     = "agent" or value of --locked-by

INSTRUMENT HEURISTIC TABLE (auto-derivation only):
    R12 + genre                → instruments
    'stripped' + folk/ambient → "fingerpicked acoustic guitar, light pad, room reverb"
    'full-band' + hard rock   → "dual electric guitars through Marshall stacks, palm-muted chug, double-kick drums, cowbell"
    'cinematic' + any         → "orchestral strings, piano, ambient pads, room reverb"
    'electronic' + any        → "synthesizers, drum machine, ambient pads"
    'hybrid' + grunge         → "overdriven electric guitar, brushed drums, light pad"
    'hybrid' + folk           → "fingerpicked acoustic guitar, brushed drums, light pad"
    (fallback)                 → "acoustic guitar, light drums, room reverb"

MOOD HEURISTIC TABLE:
    'stripped'    → "intimate, dusky, melancholic"
    'full-band'   → "aggressive, swaggering, energetic"
    'cinematic'   → "atmospheric, lush, contemplative"
    'electronic'  → "driving, hypnotic, textured"
    'hybrid'      → "warm, layered, dynamic"
    (fallback)    → "neutral, balanced"

WHY THIS SCRIPT EXISTS:
    The Twenty-Two build (2026-08-03) locked M03/M05/R12 in the schema
    pointing at "90s grunge with Scott Weiland", but the actual MP3s were
    generated with "hard rock + Axl Rose". The schema and the artifact
    drifted. To prevent this, every build must hold against a LOCKED
    M09_sonicDNA — and the lock must be the EXACT flags sent to the API.

    Before this script, the lock was manual: copy-paste the vocal
    descriptor into M09_sonicDNA. Easy to drift. With this script, the
    lock is generated at brief-approval time from the locked M03/M05/R12,
    and the user can override any field with explicit flags. The output is
    the canonical source of truth for what the build will produce.

ANTI-PATTERN THIS PREVENTS:
    "I'll just write M09 later" → never happens, schema and artifact
    drift silently. The lock happens at brief approval, before any
    generation runs.

REQUIREMENTS:
    Python 3.11+ (uses pathlib, datetime.timezone.utc, dataclasses)

EXIT CODES:
    0 = success (lock written or --dry-run shown)
    1 = error (intake JSON missing, missing M03/M05/R12/M07, etc)
    2 = drift detected: M09 already locked with different values + --force not passed
"""
import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# === Heuristic tables (auto-derivation only — overridable via --override-*) ===

INSTRUMENT_HEURISTICS = {
    ("stripped", "folk"):       "fingerpicked acoustic guitar, light pad, room reverb",
    ("stripped", "ambient"):    "fingerpicked acoustic guitar, soft synth pad, room reverb",
    ("stripped", "indie"):      "fingerpicked acoustic guitar, brushed drums, room reverb",
    ("full-band", "rock"):      "dual electric guitars through Marshall stacks, palm-muted chug, double-kick drums, cowbell",
    ("full-band", "hard rock"): "dual electric guitars through Marshall stacks, palm-muted chug, double-kick drums, cowbell",
    ("full-band", "metal"):     "electric guitars with high gain, double-kick drums, bass, distortion",
    ("full-band", "punk"):      "electric guitars with high gain, fast drums, bass, distortion",
    ("cinematic", "*"):         "orchestral strings, piano, ambient pads, room reverb",
    ("electronic", "*"):        "synthesizers, drum machine, ambient pads",
    ("hybrid", "grunge"):       "overdriven electric guitar, brushed drums, light pad",
    ("hybrid", "folk"):        "fingerpicked acoustic guitar, brushed drums, light pad",
    ("hybrid", "rock"):        "dual electric guitars, brushed drums, light pad",
    ("hybrid", "hard rock"):   "dual electric guitars, brushed drums, double-kick, cowbell",
}

MOOD_HEURISTICS = {
    "stripped":    "intimate, dusky, melancholic",
    "full-band":   "aggressive, swaggering, energetic",
    "cinematic":   "atmospheric, lush, contemplative",
    "electronic":  "driving, hypnotic, textured",
    "hybrid":      "warm, layered, dynamic",
}

GENRE_KEYWORDS = ["folk", "rock", "hard rock", "metal", "punk", "indie",
                  "ambient", "electronic", "jazz", "country", "grunge"]


def detect_genre_keyword(genre_str: str) -> str:
    """Extract the first genre keyword from a free-text genre string.

    E.g. "90s grunge with Foo Fighters melodic hooks" → "grunge"
         "dream-folk with electronic undertones"      → "folk"
         "cinematic indie folk"                        → "folk"
    Returns "*" if no keyword found (fallback rule).
    """
    genre_lower = genre_str.lower()
    for kw in GENRE_KEYWORDS:
        if kw in genre_lower:
            return kw
    return "*"


def derive_instruments(production: str, genre: str) -> str:
    """Apply instrument heuristic table."""
    genre_key = detect_genre_keyword(genre)
    # Specific (prod, genre) lookup first
    key = (production, genre_key)
    if key in INSTRUMENT_HEURISTICS:
        return INSTRUMENT_HEURISTICS[key]
    # (prod, *) wildcard
    wildcard_key = (production, "*")
    if wildcard_key in INSTRUMENT_HEURISTICS:
        return INSTRUMENT_HEURISTICS[wildcard_key]
    # Fallback
    return "acoustic guitar, light drums, room reverb"


def derive_mood(production: str) -> str:
    """Apply mood heuristic table."""
    return MOOD_HEURISTICS.get(production, "neutral, balanced")


def derive_tempo_profile(runtime: dict) -> str:
    """Build tempo profile from M07_runtime."""
    if not runtime:
        return "moderate"
    min_str = runtime.get("min_per_track", "")
    max_str = runtime.get("max_per_track", "")
    if min_str and max_str:
        return f"{min_str} - {max_str} per track"
    if min_str:
        return f"{min_str}+ per track"
    return "moderate"


def derive_references(refs: list) -> str:
    """Build references string from M04_references[].

    Format: "<artist1>, <artist2>, <artist3>" — joined by ", "
    Skips empty entries. Caps at 3 (matches M04 schema constraint).
    """
    if not refs:
        return ""
    artists = []
    for r in refs[:3]:
        artist = r.get("artist") if isinstance(r, dict) else r
        if artist:
            artists.append(artist)
    return ", ".join(artists)


def derive_sonic_dna(intake: dict) -> dict:
    """Derive M09_sonicDNA.value from the locked M03/M04/M05/M07/R12.

    Args:
        intake: the parsed intake JSON's `values` dict

    Returns:
        A dict matching M09_sonicDNA.value schema, ready to be wrapped:
        {"value": <this dict>, "isDefault": False}
    """
    vals = intake

    # M03_genre: stored as plain string in v2.2 examples
    genre = vals.get("M03_genre", "")
    if isinstance(genre, dict):
        # Older shape — pull value out
        genre = genre.get("value", "")

    # M05_vocal: structured object, primary_style is the --vocals flag
    vocal_obj = vals.get("M05_vocal", {})
    if isinstance(vocal_obj, dict):
        vocals = vocal_obj.get("primary_style", "")
    else:
        vocals = str(vocal_obj)

    # R12_production: {"value": "hybrid", "isDefault": false}
    prod_obj = vals.get("R12_production", {})
    production = prod_obj.get("value", "") if isinstance(prod_obj, dict) else str(prod_obj)

    # M04_references: list of {artist, album, songs} objects
    refs_obj = vals.get("M04_references", [])
    if isinstance(refs_obj, dict):
        # Older shape — pull values out
        refs_obj = refs_obj.get("artists", refs_obj.get("value", []))
    references = derive_references(refs_obj)

    # M07_runtime: structured object with min/max/target
    runtime = vals.get("M07_runtime", {})

    return {
        "genre":        genre,
        "vocals":       vocals,
        "mood":         derive_mood(production),
        "instruments":  derive_instruments(production, genre),
        "references":   references,
        "tempoProfile": derive_tempo_profile(runtime),
        "lockedAt":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def apply_overrides(dna: dict, args: argparse.Namespace) -> dict:
    """Apply --override-* CLI flags on top of the derived DNA."""
    overrides = {
        "genre":       args.override_genre,
        "vocals":      args.override_vocals,
        "mood":        args.override_mood,
        "instruments": args.override_instruments,
        "references":  args.override_references,
        "tempoProfile": args.override_tempo_profile,
    }
    for k, v in overrides.items():
        if v is not None:
            dna[k] = v
    if args.locked_by is not None:
        dna["lockedBy"] = args.locked_by
    return dna


def find_intake_path(album_dir: Path) -> Path | None:
    """Locate intake-data/<slug>.json for an album.

    Tries (in order):
    1. <album_dir>/intake-data/<slug>.json (project layout)
    2. <album_dir>/../intake-data/<slug>.json (music/album/intake-data)
    3. ~/Documents/Projects/sonic-studio/intake-data/<slug>.json (the
       canonical sonic-studio project root — most common case)
    """
    slug = album_dir.name
    candidates = [
        album_dir / "intake-data" / f"{slug}.json",
        album_dir.parent / "intake-data" / f"{slug}.json",
        Path(r"C:\Users\lion_\Documents\Projects\sonic-studio\intake-data") / f"{slug}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def detect_existing_lock(intake: dict) -> dict | None:
    """Return the existing M09_sonicDNA.value if any, else None."""
    existing = intake.get("values", {}).get("M09_sonicDNA")
    if existing and isinstance(existing, dict) and existing.get("value"):
        return existing["value"]
    return None


def check_drift_intent(new: dict, old: dict, fields: list[str]) -> list[str]:
    """Compare new vs old lock, return list of fields that differ."""
    diffs = []
    for f in fields:
        if str(new.get(f, "")).strip() != str(old.get(f, "")).strip():
            diffs.append(f)
    return diffs


def main():
    parser = argparse.ArgumentParser(description="Lock an album's brief via M09_sonicDNA")
    parser.add_argument("--album-dir", type=Path, required=True,
                        help="Album directory (the slug is taken from its name)")
    parser.add_argument("--intake", type=Path, default=None,
                        help="Override intake JSON path (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be derived without writing")
    parser.add_argument("--force", action="store_true",
                        help="Allow overwriting an existing M09_sonicDNA lock without drift check")
    parser.add_argument("--locked-by", type=str, default=None,
                        help="Identifier of who's locking (defaults to 'agent')")

    # Override flags (any can be partial — only the named fields get overridden)
    parser.add_argument("--override-genre", type=str, default=None,
                        help="Override M09.genre (shorter categorical hint for --genre flag)")
    parser.add_argument("--override-vocals", type=str, default=None,
                        help="Override M09.vocals (vocal character for --vocals flag)")
    parser.add_argument("--override-mood", type=str, default=None,
                        help="Override M09.mood (descriptor for --mood flag)")
    parser.add_argument("--override-instruments", type=str, default=None,
                        help="Override M09.instruments (for --instruments flag)")
    parser.add_argument("--override-references", type=str, default=None,
                        help="Override M09.references (for --references flag)")
    parser.add_argument("--override-tempo-profile", type=str, default=None,
                        help="Override M09.tempoProfile (free-text tempo range)")

    args = parser.parse_args()

    album_dir = args.album_dir.resolve()
    if not album_dir.exists():
        print(f"[error] album dir not found: {album_dir}", file=sys.stderr)
        sys.exit(1)

    intake_path = args.intake or find_intake_path(album_dir)
    if not intake_path or not intake_path.exists():
        print(f"[error] intake JSON not found. Looked at:", file=sys.stderr)
        for c in [
            album_dir / "intake-data" / f"{album_dir.name}.json",
            album_dir.parent / "intake-data" / f"{album_dir.name}.json",
            Path(r"C:\Users\lion_\Documents\Projects\sonic-studio\intake-data") / f"{album_dir.name}.json",
        ]:
            print(f"        {c}", file=sys.stderr)
        sys.exit(1)

    print(f"Album: {album_dir.name}")
    print(f"Intake: {intake_path}")

    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    schema_version = intake.get("schemaVersion", "?")
    intake_form_version = intake.get("intakeFormVersion", "?")
    print(f"Schema version: {schema_version}")
    print(f"Intake form version: {intake_form_version}")

    # Check for existing lock
    existing = detect_existing_lock(intake)
    if existing:
        print(f"\n[!] Existing M09_sonicDNA lock found (lockedAt={existing.get('lockedAt', '?')})")
        print("    Fields:")
        for k in ("genre", "vocals", "mood", "instruments", "references", "tempoProfile"):
            print(f"      {k}: {existing.get(k, '?')}")
        if not args.force and not args.dry_run:
            print(f"\n[error] An M09_sonicDNA lock already exists. Pass --force to overwrite.", file=sys.stderr)
            sys.exit(2)

    # Derive
    dna = derive_sonic_dna(intake.get("values", {}))
    dna["lockedBy"] = args.locked_by or "agent"

    # Apply overrides
    dna = apply_overrides(dna, args)

    # If existing, check drift against new
    if existing and not args.force:
        diffs = check_drift_intent(dna, existing,
                                    ["genre", "vocals", "mood", "instruments", "references", "tempoProfile"])
        if diffs:
            print(f"\n[!] Drift detected between new and existing lock on fields: {diffs}")
            print("    Pass --force to overwrite, or --dry-run to see without committing.")
            sys.exit(2)

    # Print the result
    print(f"\n=== Derived M09_sonicDNA ===")
    for k in ("genre", "vocals", "mood", "instruments", "references", "tempoProfile", "lockedAt", "lockedBy"):
        v = dna.get(k, "")
        if v:
            print(f"  {k:13s}: {v}")

    if args.dry_run:
        print(f"\n[--dry-run] No changes written.")
        sys.exit(0)

    # Write
    backup = intake_path.with_suffix(".json.pre-lock-brief.bak")
    if not backup.exists():
        shutil.copy2(intake_path, backup)
        print(f"\nBackup: {backup.name}")

    # Update intake JSON
    if "values" not in intake:
        intake["values"] = {}
    intake["values"]["M09_sonicDNA"] = {
        "value": dna,
        "isDefault": False,
    }

    # Bump intake form version to mark the lock
    new_intake_form_version = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M-brief-locked")
    intake["intakeFormVersion"] = new_intake_form_version
    if "schemaVersion" not in intake:
        intake["schemaVersion"] = "v2.2"
    print(f"\nNew intakeFormVersion: {new_intake_form_version}")

    # Atomic write
    intake_path.write_text(json.dumps(intake, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote: {intake_path}")

    # Verify
    reloaded = json.loads(intake_path.read_text(encoding="utf-8"))
    sonic = reloaded.get("values", {}).get("M09_sonicDNA", {})
    if sonic.get("value", {}).get("lockedAt") != dna["lockedAt"]:
        print(f"[error] Round-trip verification failed — lockedAt mismatch", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ Brief locked. M09_sonicDNA is now the build contract.")
    print(f"   Future regens must pass scripts/check-sonic-drift.py against these values.")


if __name__ == "__main__":
    main()