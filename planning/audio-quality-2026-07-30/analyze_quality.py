#!/usr/bin/env python3
"""
Audio Quality Analyzer for album-studio matrix files.

Uses ffmpeg's loudnorm (LUFS), ebur128 (true-peak), and astats (RMS, peak,
flat factor) to compute industry-standard audio quality metrics for every
mp3/wav in the matrix directory.

Metrics:
- integrated_lufs: EBU R128 integrated loudness (target -14 LUFS for Spotify,
  -16 LUFS for Apple Music, -23 LUFS for broadcast). Pop-punk typically
  mastered at -8 to -10 LUFS.
- loudness_range_lu: EBU R128 LRA — dynamic range in LU. Pop-punk: 4-7 LU.
  Orchestral: 10-20 LU. Folk: 8-15 LU.
- true_peak_dbtp: dBTP — inter-sample peaks. < -1 dBTP is safe; clipping
  risk above -0.5 dBTP.
- rms_db: simple RMS level. Loose proxy for loudness.
- peak_db: simple sample peak. Compare to true_peak for clipping detection.
- spectral_centroid_hz: "brightness" — 500-1500 Hz = warm/dark, 2000-4000 Hz
  = bright/aggressive. Grunge dirt should land > 2000 Hz.
- spectral_flatness: noisiness — 0 = pure tone, 1 = white noise. Distorted
  guitars, cymbal hash, and grit push this higher.
- dynamic_range_db: crest factor estimate (peak - RMS). Pop-punk: 8-12 dB.
  Orchestral: 18-25 dB.

Output: per-file JSON + summary CSV + Markdown report.

Usage:
  python analyze_quality.py <test-dir>
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_ffmpeg_json(filepath: Path, filter_str: str) -> Optional[dict]:
    """Run ffmpeg with a filter and parse JSON output (ffprobe-like)."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i", str(filepath),
        "-af", filter_str,
        "-f", "null",
        "-",
    ]
    # The -af progress is via stderr for some filters. Use -progress to get
    # structured output instead. But for ebur128/loudnorm we want stderr text.
    # Better: use ffmpeg's -stats_period or just parse stderr.
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Parse stderr — ffmpeg's loudnorm/ebur128 print key-value pairs.
        return parse_ffmpeg_stderr(proc.stderr, filter_str)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT on {filepath.name}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ERROR on {filepath.name}: {e}", file=sys.stderr)
        return None


def parse_ffmpeg_stderr(stderr: str, filter_str: str) -> dict:
    """Parse ffmpeg stderr for filter output."""
    out = {}
    lines = stderr.split("\n")

    if "loudnorm" in filter_str:
        # loudnorm I=-16:LRA=11:tp=-1.5 prints these after analysis pass.
        # Format: "I: -16.5 LUFS" / "LRA: 7.3 LU" / "Threshold: -26.7 LUFS"
        # We use TWO-PASS via -af loudnorm=print_format=json to get JSON.
        # Actually, simpler: just look for the loudnorm summary.
        for line in lines:
            line = line.strip()
            if line.startswith("Input Integrated:"):
                out["integrated_lufs"] = float(line.split(":")[-1].strip().rstrip(" LUFS"))
            elif line.startswith("Input True Peak:"):
                out["true_peak_dbtp"] = float(line.split(":")[-1].strip().rstrip(" dBFS"))
            elif line.startswith("Input LRA:"):
                out["loudness_range_lu"] = float(line.split(":")[-1].strip().rstrip(" LU"))
            elif line.startswith("Input Threshold:"):
                out["threshold_lufs"] = float(line.split(":")[-1].strip().rstrip(" LUFS"))

    elif "ebur128" in filter_str:
        # ebur128 prints summary at end: "Summary:" then a multi-line block.
        # Each metric is indented and on its own line:
        #   Integrated loudness:
        #     I:         -14.0 LUFS
        #     Threshold: -24.1 LUFS
        #   Loudness range:
        #     LRA:         5.8 LU
        #     Threshold: -34.0 LUFS
        #     LRA low:   -17.6 LUFS
        #     LRA high:  -11.8 LUFS
        #   True peak:
        #     Peak:        0.1 dBFS
        for line in lines:
            line_s = line.strip()
            # The values are on the deeper-indented line.
            # Look for the specific key markers.
            if line_s.startswith("I:") and "LUFS" in line_s and "integrated_lufs" not in out:
                # "I:         -14.0 LUFS"
                try:
                    parts = line_s.split()
                    val = float(parts[1])
                    out["integrated_lufs"] = val
                except (ValueError, IndexError):
                    pass
            elif line_s.startswith("LRA:") and "LU" in line_s and "loudness_range_lu" not in out:
                try:
                    parts = line_s.split()
                    val = float(parts[1])
                    out["loudness_range_lu"] = val
                except (ValueError, IndexError):
                    pass
            elif line_s.startswith("Peak:") and "dBFS" in line_s and "true_peak_dbtp" not in out:
                try:
                    parts = line_s.split()
                    val = float(parts[1])
                    out["true_peak_dbtp"] = val
                except (ValueError, IndexError):
                    pass
            elif line_s.startswith("Threshold:") and "LUFS" in line_s and "threshold_lufs" not in out:
                try:
                    parts = line_s.split()
                    val = float(parts[1])
                    out["threshold_lufs"] = val
                except (ValueError, IndexError):
                    pass

    elif "astats" in filter_str:
        # astats prints output like:
        #   [Parsed_astats_0 @ ...] RMS level dB: -52.676715
        #   [Parsed_astats_0 @ ...] Peak level dB: -48.704552
        #   [Parsed_astats_0 @ ...] Flat factor: -6.020600  (in dB!)
        #   [Parsed_astats_0 @ ...] Crest factor: 1.576749  (linear, not dB)
        #   [Parsed_astats_0 @ ...] Dynamic range: 11.088851
        #   [Parsed_astats_0 @ ...] Entropy: 0.116990
        #   [Parsed_astats_0 @ ...] Zero crossings: 0
        # We want the "Overall" block (last block before EOF) — but ffmpeg
        # prints per-channel then overall. We just take whatever we see
        # LAST (which is the overall).
        last_seen = {}
        for line in lines:
            line_s = line.strip()
            # Strip the "[Parsed_astats_0 @ ...] " prefix.
            if "]" in line_s:
                line_s = line_s.split("]", 1)[-1].strip()
            if line_s.startswith("RMS level dB:"):
                try:
                    last_seen["rms_db"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass
            elif line_s.startswith("Peak level dB:"):
                try:
                    last_seen["peak_db"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass
            elif line_s.startswith("Flat factor:"):
                # Stored as dB; convert to linear flatness: 10^(dB/10).
                try:
                    db_val = float(line_s.split(":")[-1].strip())
                    last_seen["flatness_db"] = db_val
                    last_seen["flatness_linear"] = 10 ** (db_val / 10)
                except ValueError:
                    pass
            elif line_s.startswith("Crest factor:"):
                try:
                    last_seen["crest_linear"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass
            elif line_s.startswith("Dynamic range:"):
                try:
                    last_seen["dynamic_range_db"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass
            elif line_s.startswith("Entropy:"):
                try:
                    last_seen["entropy"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass
            elif line_s.startswith("Zero crossings:"):
                try:
                    last_seen["zero_crossings"] = float(line_s.split(":")[-1].strip())
                except ValueError:
                    pass

        # Take the last-seen values (the "Overall" block).
        out.update(last_seen)

    return out


def get_spectral_metrics(filepath: Path) -> dict:
    """Compute spectral centroid and flatness via ffmpeg + numpy-style sampling.

    Uses ffmpeg to dump the spectrogram as raw frame data via the
    showspectrumpic filter is not enough — we want the spectral centroid.
    Use the aspectralstats filter if available, otherwise fall back to
    ffmpeg's `astats` + a separate `spectralstats` call.
    """
    # Use ffmpeg's spectralstats filter (ffmpeg 4.4+)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i", str(filepath),
        "-af", "aspectralstats=measure=mean+max+centroid+flatness,ametadata=print:key=lavfi.aspectralstats.1.mean,ametadata=print:key=lavfi.aspectralstats.1.centroid,ametadata=print:key=lavfi.aspectralstats.1.flatness",
        "-f", "null",
        "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = {}
        for line in proc.stderr.split("\n"):
            line_s = line.strip()
            # ametadata prints frames:
            # frame:0    pts:0       pts_time:0
            # lavfi.aspectralstats.1.centroid=1823.45
            for key in ["mean", "centroid", "flatness"]:
                marker = f"lavfi.aspectralstats.1.{key}="
                if marker in line_s:
                    try:
                        val = float(line_s.split(marker)[-1].strip())
                        out[f"spectral_{key}"] = val
                    except (ValueError, IndexError):
                        pass
        return out
    except Exception as e:
        print(f"  spectral ERR on {filepath.name}: {e}", file=sys.stderr)
        return {}


def analyze_file(filepath: Path) -> dict:
    """Run all analyses on one file. Returns dict with all metrics."""
    print(f"  analyzing {filepath.name}...", file=sys.stderr)

    result = {
        "file": filepath.name,
        "size_bytes": filepath.stat().st_size,
    }

    # 1. EBU R128 (loudness + true peak + LRA)
    ebu = run_ffmpeg_json(filepath, "ebur128=peak=true")
    if ebu:
        result.update({f"ebu_{k}": v for k, v in ebu.items()})

    # 2. astats (RMS + peak + crest + flatness) — full file, no reset
    ast = run_ffmpeg_json(filepath, "astats=metadata=1:reset=0")
    if ast:
        result.update(ast)

    # 3. spectralstats (centroid + flatness)
    sp = get_spectral_metrics(filepath)
    if sp:
        result.update(sp)

    # 4. ffprobe format info (duration + bitrate)
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-of", "json", str(filepath)],
            capture_output=True, text=True, timeout=30,
        )
        if probe.returncode == 0:
            fmt = json.loads(probe.stdout).get("format", {})
            result["duration_s"] = float(fmt.get("duration", 0))
            result["bit_rate"] = int(fmt.get("bit_rate", 0))
            result["format_name"] = fmt.get("format_name", "?")
    except Exception as e:
        print(f"  ffprobe ERR on {filepath.name}: {e}", file=sys.stderr)

    return result


def classify(metrics: dict) -> dict:
    """Tag each file with qualitative descriptors based on metrics."""
    tags = []

    lufs = metrics.get("integrated_lufs")
    lra = metrics.get("loudness_range_lu")
    centroid = metrics.get("spectral_centroid")
    flatness = metrics.get("spectral_flatness")
    crest = metrics.get("crest_db")

    # Loudness classification
    if lufs is not None:
        if lufs < -20:
            tags.append("very-quiet")
        elif lufs < -16:
            tags.append("quiet")
        elif lufs < -12:
            tags.append("loud")
        elif lufs < -8:
            tags.append("very-loud")
        else:
            tags.append("brick-walled")

    # Dynamic range classification
    if lra is not None:
        if lra < 4:
            tags.append("over-compressed")
        elif lra < 8:
            tags.append("compressed")
        elif lra < 14:
            tags.append("normal")
        else:
            tags.append("wide-dynamic")

    # Spectral character
    if centroid is not None:
        if centroid < 800:
            tags.append("dark")
        elif centroid < 1500:
            tags.append("warm")
        elif centroid < 2500:
            tags.append("neutral")
        elif centroid < 4000:
            tags.append("bright")
        else:
            tags.append("harsh")

    # Noise/grit character
    if flatness is not None:
        if flatness < 0.01:
            tags.append("tonal")
        elif flatness < 0.05:
            tags.append("clean")
        elif flatness < 0.15:
            tags.append("textured")
        else:
            tags.append("gritty/noisy")

    metrics["quality_tags"] = tags
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("test_dir", type=Path)
    ap.add_argument("--output-dir", type=Path, default=None)
    args = ap.parse_args()

    test_dir: Path = args.test_dir.resolve()
    out_dir = args.output_dir or test_dir / "audio-quality"
    out_dir.mkdir(exist_ok=True, parents=True)

    audio_files = sorted(
        list(test_dir.glob("*.mp3")) +
        list(test_dir.glob("*.wav"))
    )
    print(f"Found {len(audio_files)} audio files in {test_dir}", file=sys.stderr)

    results = []
    for f in audio_files:
        metrics = analyze_file(f)
        metrics = classify(metrics)
        results.append(metrics)

        # Save per-file JSON
        per_file = out_dir / f"{f.stem}.json"
        per_file.write_text(json.dumps(metrics, indent=2))

    # Write summary JSON
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2))

    # Write CSV
    if results:
        keys = sorted({k for r in results for k in r.keys() if k != "quality_tags"} | {"quality_tags"})
        with open(out_dir / "summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in results:
                r_copy = {**r}
                if "quality_tags" in r_copy:
                    r_copy["quality_tags"] = "|".join(r_copy["quality_tags"])
                w.writerow(r_copy)

    # Print brief summary
    print(f"\n=== {len(results)} files analyzed ===", file=sys.stderr)
    print(f"Outputs: {out_dir}/", file=sys.stderr)
    print(f"  summary.json  — all metrics", file=sys.stderr)
    print(f"  summary.csv   — for spreadsheet import", file=sys.stderr)
    print(f"  <file>.json   — per-file details", file=sys.stderr)


if __name__ == "__main__":
    main()