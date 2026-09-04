"""
check-sonic-drift.py — Detect sonic drift between a locked brief and a regen attempt.

Usage:
    # Compare an album's current state against its M09_sonicDNA lock:
    python scripts/check-sonic-drift.py --album-dir <path>

    # Compare a specific track's manifest against a proposed new prompt:
    python scripts/check-sonic-drift.py --album-dir <path> \\
        --track 01-razor --proposed-prompt <prompt-file>

    # Compare two manifests (e.g. for a regen diff):
    python scripts/check-sonic-drift.py --compare-manifests \\
        --manifest-a <manifest1.json> --manifest-b <manifest2.json>

Exit codes:
    0 = no drift detected (or all drift is approved-allowed)
    1 = drift detected
    2 = error (file missing, malformed, etc.)

WHAT COUNTS AS DRIFT:
    Sonic-drift is any change to the LOCKED audio-generation parameters
    that would change what the album SOUNDS like. Specifically:
        - vocals (the singer's voice descriptor)
        - genre (the --genre flag)
        - mood (the --mood flag)
        - instruments (the --instruments flag)
        - references (the --references flag, the comp artists list)
        - bpm (target tempo — out of M07_runtime range is drift)
        - key (target musical key)
        - model (music-3.0 vs music-2.6 = drift, vs music-2.5 = drift)

    What does NOT count as drift:
        - prompt body (can be reworded freely)
        - lyrics body (can be reworded freely)
        - audio output details (md5, duration — they SHOULD change per regen)
        - timestamps

WHY THIS EXISTS:
    The Twenty-Two build (2026-08-03) showed the failure mode clearly:
    the schema locked M03_genre = "90s grunge with FF melodic hooks" +
    M05_vocal = "Velvet Revolver-style (Scott Weiland)", but a regen
    silently switched to hard rock + Axl Rose vocals. The schema and the
    artifact DRIFTED without anyone noticing until the user pushed back.

    This script makes that drift visible BEFORE regeneration. The build
    pipeline must run this check on every regen attempt and abort if
    drift is detected, unless an explicit `--allow-drift-fields` flag
    is passed.

ANTI-PATTERN THIS PREVENTS:
    "I just changed one word in the prompt" → vocal style accidentally
    changed → album sounds completely different → user rejects → wasted
    quota. The drift check catches the vocal-style change before the
    quota is spent.
"""
import argparse
import json
import re
import sys
from pathlib import Path


# === Drift policy ===
DRIFT_FIELDS = [
    "vocals",
    "genre",
    "mood",
    "instruments",
    "references",
    "bpm",
    "key",
    "model",
]

# Allowed drift — fields where change is expected / benign
ALLOWED_DRIFT_FIELDS = []


def normalize(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip whitespace, collapse."""
    if not isinstance(s, str):
        return str(s)
    return re.sub(r"\s+", " ", s.lower().strip())


def extract_sonic_dna(album_dir: Path) -> dict | None:
    """Load M09_sonicDNA from intake JSON. Returns None if not set."""
    candidates = [
        album_dir.parent / "intake-data" / f"{album_dir.name}.json",
        Path(r"C:\Users\lion_\Documents\Projects\sonic-studio\intake-data") / f"{album_dir.name}.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
                sonic = data.get("values", {}).get("M09_sonicDNA", {})
                if sonic.get("value"):
                    return sonic["value"]
            except (json.JSONDecodeError, OSError):
                pass
    return None


def load_manifest(album_dir: Path, track_slug: str) -> dict | None:
    """Load a track's generation manifest."""
    manifest_path = album_dir / "music" / f"{track_slug}.generation-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def parse_prompt_md(prompt_md_path: Path) -> dict:
    """Parse a prompt markdown file into body + flags (same as generation-manifest.py)."""
    if not prompt_md_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_md_path}")
    content = prompt_md_path.read_text(encoding="utf-8")

    # Extract prompt body from ```code block```
    m = re.search(r"```\n(.*?)\n```", content, re.DOTALL)
    body = m.group(1) if m else ""

    # Extract flag-style metadata
    flags = {}
    flag_section = re.search(r"## Other flags\n\n(.*?)(?:\n## |\Z)",
                             content, re.DOTALL)
    if flag_section:
        for line in flag_section.group(1).split("\n"):
            line = line.strip()
            if not line.startswith("- `--"):
                continue
            mm = re.match(r"^-\s+`--(\w+)`\s*(.*)$", line)
            if mm:
                fname, fvalue = mm.group(1), mm.group(2).strip()
                if fname == "bpm":
                    try:
                        flags[fname] = int(fvalue)
                    except ValueError:
                        flags[fname] = fvalue
                else:
                    flags[fname] = fvalue

    # Top-level metadata
    meta = {}
    for line in content.split("\n"):
        line = line.strip()
        mm = re.match(r"^\*\*(\w+):\*\*\s*(.*)$", line)
        if mm:
            key = mm.group(1).lower()
            val = mm.group(2).strip()
            if key == "bpm":
                try:
                    meta[key] = int(val)
                except ValueError:
                    meta[key] = val
            else:
                meta[key] = val

    return {"prompt": body, "flags": flags, "metadata": meta}


def check_drift(current: dict, baseline: dict, allow_drift: list[str] = None) -> list[dict]:
    """Compare two state dicts and return a list of drift reports.

    Each drift report:
        {
            "field": "vocals",
            "baseline_value": "Velvet Revolver-style vocals (Scott Weiland)",
            "current_value": "Axl Rose-style raw high tenor, ...",
            "severity": "high" | "medium" | "low",
        }
    """
    allow = set(allow_drift or [])
    reports = []

    for field in DRIFT_FIELDS:
        if field in allow:
            continue

        base_val = baseline.get(field)
        cur_val = current.get(field)

        if base_val is None and cur_val is None:
            continue
        if base_val is None or cur_val is None:
            reports.append({
                "field": field,
                "baseline_value": base_val,
                "current_value": cur_val,
                "severity": "medium",
                "note": f"field is {'missing from current' if base_val else 'NEW in current'}",
            })
            continue

        if normalize(base_val) != normalize(cur_val):
            severity = "high"
            if field in ("bpm", "key", "model"):
                severity = "high"  # these are non-negotiable
            elif field == "mood":
                severity = "low"  # mood descriptors are loose

            reports.append({
                "field": field,
                "baseline_value": base_val,
                "current_value": cur_val,
                "severity": severity,
            })

    return reports


def report_drift(reports: list[dict], verbose: bool = False) -> None:
    """Print a human-readable drift report."""
    if not reports:
        print("✅ NO DRIFT DETECTED — current params match the locked sonic DNA.")
        return

    print(f"❌ DRIFT DETECTED — {len(reports)} field(s) changed since lock:\n")
    high = [r for r in reports if r["severity"] == "high"]
    medium = [r for r in reports if r["severity"] == "medium"]
    low = [r for r in reports if r["severity"] == "low"]

    if high:
        print(f"  HIGH SEVERITY ({len(high)}):")
        for r in high:
            print(f"    • {r['field']}:")
            print(f"        was: {r['baseline_value']!r}")
            print(f"        now: {r['current_value']!r}")
            if r.get("note"):
                print(f"        ({r['note']})")
            print()

    if medium:
        print(f"  MEDIUM SEVERITY ({len(medium)}):")
        for r in medium:
            print(f"    • {r['field']}: was={r['baseline_value']!r}, now={r['current_value']!r}")

    if low:
        if verbose:
            print(f"  LOW SEVERITY ({len(low)}):")
            for r in low:
                print(f"    • {r['field']}: was={r['baseline_value']!r}, now={r['current_value']!r}")
        else:
            print(f"  ({len(low)} low-severity drift(s) suppressed; pass --verbose to show)")


def main():
    parser = argparse.ArgumentParser(description="Detect sonic drift")
    parser.add_argument("--album-dir", type=Path, default=None,
                        help="Album directory (not required for --compare-manifests)")
    parser.add_argument("--track", type=str, default=None,
                        help="Specific track to check (default: all tracks)")
    parser.add_argument("--proposed-prompt", type=Path, default=None,
                        help="Path to a proposed NEW prompt.md file to compare against the locked M09_sonicDNA")
    parser.add_argument("--compare-manifests", action="store_true",
                        help="Compare two manifests directly (use --manifest-a and --manifest-b)")
    parser.add_argument("--manifest-a", type=Path, default=None,
                        help="First manifest for compare-manifests mode")
    parser.add_argument("--manifest-b", type=Path, default=None,
                        help="Second manifest for compare-manifests mode")
    parser.add_argument("--allow-drift-fields", type=str, default="",
                        help="Comma-separated field names that are allowed to drift (e.g. 'mood,key')")
    parser.add_argument("--verbose", action="store_true",
                        help="Show low-severity drift")
    args = parser.parse_args()

    allow_drift = [f.strip() for f in args.allow_drift_fields.split(",") if f.strip()]

    # Mode 1: compare two manifests directly
    if args.compare_manifests:
        if not args.manifest_a or not args.manifest_b:
            print("[error] --compare-manifests requires --manifest-a and --manifest-b", file=sys.stderr)
            sys.exit(2)
        try:
            a = json.loads(args.manifest_a.read_text(encoding="utf-8"))
            b = json.loads(args.manifest_b.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[error] Could not parse manifest: {e}", file=sys.stderr)
            sys.exit(2)

        # Build the state dict from each manifest's flags
        state_a = {"flags": a.get("flags", {}), "model": a.get("model", "")}
        state_b = {"flags": b.get("flags", {}), "model": b.get("model", "")}
        # Flatten: merge flags into top-level
        a_flat = {**state_a["flags"], "model": state_a["model"]}
        b_flat = {**state_b["flags"], "model": state_b["model"]}

        reports = check_drift(a_flat, b_flat, allow_drift)
        print(f"Comparing manifests:")
        print(f"  A: {args.manifest_a}")
        print(f"  B: {args.manifest_b}\n")
        report_drift(reports, args.verbose)
        sys.exit(1 if reports else 0)

    album_dir = args.album_dir.resolve()

    # Mode 2: compare proposed prompt against M09_sonicDNA
    if args.proposed_prompt:
        if not args.album_dir:
            print("[error] --proposed-prompt requires --album-dir", file=sys.stderr)
            sys.exit(2)
        album_dir = args.album_dir.resolve()
        sonic_dna = extract_sonic_dna(album_dir)
        if not sonic_dna:
            print("[warn] No M09_sonicDNA lock found in intake. Drift check has nothing to compare against.")
            print("[warn] Recommend: lock the brief first by filling M09_sonicDNA in the intake JSON.")
            sys.exit(2)

        proposed = parse_prompt_md(args.proposed_prompt)
        # Flatten: prompt.md's flags + metadata
        current_flat = {**proposed["flags"], **proposed["metadata"]}

        reports = check_drift(current_flat, sonic_dna, allow_drift)
        print(f"Comparing proposed prompt against M09_sonicDNA lock:")
        print(f"  Proposed: {args.proposed_prompt}")
        print(f"  Locked at: {sonic_dna.get('lockedAt', '?')}\n")
        report_drift(reports, args.verbose)
        sys.exit(1 if reports else 0)

    # Mode 3: compare every track's manifest against M09_sonicDNA
    if not args.album_dir:
        print("[error] --album-dir required for full-album check mode", file=sys.stderr)
        sys.exit(2)
    album_dir = args.album_dir.resolve()
    sonic_dna = extract_sonic_dna(album_dir)
    if not sonic_dna:
        print(f"[warn] No M09_sonicDNA lock found at:")
        for c in [
            album_dir.parent / "intake-data" / f"{album_dir.name}.json",
            Path(r"C:\Users\lion_\Documents\Projects\sonic-studio\intake-data") / f"{album_dir.name}.json",
        ]:
            print(f"         {c}")
        print(f"\n[hint] The drift check needs a locked M09_sonicDNA to compare against.")
        print(f"[hint] For Twenty-Two: this is expected (the album pre-dates the M09 field).")
        sys.exit(2)

    music_dir = album_dir / "music"
    if not music_dir.exists():
        print(f"[error] music/ not found at {album_dir}", file=sys.stderr)
        sys.exit(2)

    if args.track:
        tracks = [args.track]
    else:
        # Manifests are written as <slug>.generation-manifest.json
        tracks = sorted(
            p.name.replace(".generation-manifest.json", "")
            for p in music_dir.glob("*.generation-manifest.json")
        )

    if not tracks:
        print(f"[error] No generation manifests found in {music_dir}")
        print(f"[hint] Run `python scripts/generation-manifest.py --album-dir {album_dir}` first.")
        sys.exit(2)

    print(f"Comparing {len(tracks)} track manifest(s) against M09_sonicDNA lock:")
    print(f"  Album: {album_dir.name}")
    print(f"  Locked at: {sonic_dna.get('lockedAt', '?')}\n")

    total_drift = 0
    drift_per_track = {}
    for slug in tracks:
        manifest = load_manifest(album_dir, slug)
        if not manifest:
            print(f"  ⚠️  {slug}: no manifest found")
            continue

        # Flatten manifest flags + model
        current_flat = {**manifest.get("flags", {}), "model": manifest.get("model", "")}
        reports = check_drift(current_flat, sonic_dna, allow_drift)

        if reports:
            drift_per_track[slug] = reports
            total_drift += len(reports)
            high = [r for r in reports if r["severity"] == "high"]
            non_high = [r for r in reports if r["severity"] != "high"]
            print(f"  ❌ {slug}: {len(reports)} drift(s) ({len(high)} high, {len(non_high)} low)")
            for r in reports:
                if r["severity"] == "high" or args.verbose:
                    cv = r["current_value"]
                    bv = r["baseline_value"]
                    shown = str(cv)[:80] if cv is not None else "(empty)"
                    base = str(bv)[:80] if bv is not None else "(empty)"
                    print(f"      • {r['field']} ({r['severity']}): baseline={base!r}, current={shown!r}")
        else:
            print(f"  ✅ {slug}: in lock")

    print(f"\nTotal drift across all tracks: {total_drift}")
    if total_drift:
        print(f"\nTracks with drift: {len(drift_per_track)}/{len(tracks)}")
        sys.exit(1)
    else:
        print(f"\n✅ All tracks in lock with M09_sonicDNA.")
        sys.exit(0)


if __name__ == "__main__":
    main()